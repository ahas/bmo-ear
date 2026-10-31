"""The card master's demand, against a stand-in master on the loopback (docs/design.md, 「The card」)."""

import fcntl
import json
import os
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.parse import urlparse

from ear import demand
from ear.call import CallError, transcribe

SETTINGS_TEXT = (Path(__file__).resolve().parent / "settings-example.toml").read_text(encoding="utf-8")


class StandInMaster:
    """A master that answers demands as a test scripts it, recording every request."""

    def __init__(self):
        self.lock = threading.Lock()
        self.requests = []
        self.demands = {}
        self.next_id = 1000
        # How many reads of a demand answer it waiting before it is granted.
        self.waiting_reads = 0
        # How many requests of any kind are answered 503 before the master serves again.
        self.unready = 0
        # Whether the next ask is answered 503 though the demand was made.
        self.lose_next_answer = False
        self.no_place = False
        self.forget_after_reads = None
        self.granted_node = "node-b"
        self.reads = 0
        master = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def answer(self, status, body=None):
                data = json.dumps(body).encode("utf-8") if body is not None else b""
                self.send_response(status)
                if data:
                    self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                length = int(self.headers.get("content-length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                status, answer = master.post(self.path, body)
                self.answer(status, answer)

            def do_GET(self):
                status, answer = master.get(self.path)
                self.answer(status, answer)

            def do_DELETE(self):
                status, answer = master.delete(self.path)
                self.answer(status, answer)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.address = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    def _unready(self):
        if self.unready > 0:
            self.unready -= 1
            return True
        return False

    def _waiting(self, made):
        return dict(made, state="waiting", cards=[],
                    reason={"code": "in-use", "text": "every card is in use"})

    def post(self, path, body):
        with self.lock:
            self.requests.append(("POST", path, body))
            if self._unready():
                return 503, {"code": "not-ready", "error": "the master is starting"}
            if self.no_place:
                return 422, {"code": "no-place", "error": "ear is placed on no node"}
            self.next_id += 1
            made = {"id": self.next_id, "serviceName": body["serviceName"], "count": body["count"],
                    "workKey": body.get("workKey"), "ref": body.get("ref"), "taken": None, "within": None}
            self.demands[made["id"]] = made
            if self.lose_next_answer:
                self.lose_next_answer = False
                return 503, {"code": "failed", "error": "the answer was lost"}
            return 202, self._waiting(made)

    def get(self, path):
        with self.lock:
            self.requests.append(("GET", path, None))
            if self._unready():
                return 503, {"code": "not-ready", "error": "the master is starting"}
            parsed = urlparse(path)
            if parsed.path == "/demands":
                return 200, {"items": [self._waiting(one) for one in self.demands.values()], "more": False}
            demand_id = int(parsed.path.rsplit("/", 1)[1])
            made = self.demands.get(demand_id)
            if made is None:
                return 404, {"code": "not-found", "error": "no such demand"}
            self.reads += 1
            if self.forget_after_reads is not None and self.reads >= self.forget_after_reads:
                self.forget_after_reads = None
                self.demands.pop(demand_id)
                return 404, {"code": "not-found", "error": "no such demand"}
            if self.waiting_reads > 0:
                self.waiting_reads -= 1
                return 200, self._waiting(made)
            return 200, dict(made, state="granted", reason=None,
                             cards=[{"nodeName": self.granted_node, "address": None, "keyFile": None}])

    def delete(self, path):
        with self.lock:
            self.requests.append(("DELETE", path, None))
            if self._unready():
                return 503, {"code": "not-ready", "error": "the master is starting"}
            demand_id = int(urlparse(path).path.rsplit("/", 1)[1])
            if self.demands.pop(demand_id, None) is None:
                return 404, {"code": "not-found", "error": "no such demand"}
            return 204, None

    def asked(self, method):
        return [one for one in self.requests if one[0] == method]


class FakeClock:
    """A clock that moves only as the call pauses."""

    def __init__(self):
        self.now = 0.0

    def sleep(self, seconds):
        self.now += seconds


class DemandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.folder = demand.ledger_folder(self.root)
        self.master = StandInMaster()
        self.clock = FakeClock()
        self.said = []

    def tearDown(self):
        self.master.close()
        self.tmp.cleanup()

    def demands(self, pause_s=1.0, address=None):
        return demand.Demands(
            address or self.master.address,
            self.folder,
            sleep=self.clock.sleep,
            said=self.said.append,
            hold_ms=10,
            pause_s=pause_s,
        )

    def ledger(self):
        return sorted(path.name for path in self.folder.glob("*.json")) if self.folder.is_dir() else []

    def test_the_wait_has_no_end_but_the_grant(self):
        # A day and more without a card: the master unready, then the demand held in line.
        self.master.unready = 150
        self.master.waiting_reads = 300
        held = self.demands(pause_s=600).ask("ear", "ear listens to a file")
        self.assertEqual(held.wait(), "node-b")
        self.assertGreater(self.clock.now, 24 * 3600)
        self.assertEqual(self.master.reads, 301)
        self.assertEqual(len(self.ledger()), 1)
        held.give_back()
        self.assertEqual(self.ledger(), [])
        self.assertEqual(len(self.master.asked("DELETE")), 1)
        self.assertEqual(self.master.demands, {})

    def test_the_demand_names_no_node(self):
        held = self.demands().ask("ear", "ear listens to a file")
        held.wait()
        held.give_back()
        (_, path, body), = self.master.asked("POST")
        self.assertEqual(path, "/demands")
        self.assertEqual(set(body), {"serviceName", "count", "workKey", "ref"})
        self.assertEqual(body["serviceName"], "ear")
        self.assertEqual(body["count"], 1)
        self.assertTrue(body["workKey"].startswith("ear:listen:"))
        self.assertEqual(body["ref"], "ear listens to a file")

    def test_each_call_asks_with_a_work_key_of_its_own(self):
        demands = self.demands()
        for _ in range(2):
            held = demands.ask("ear", "ear listens to a file")
            held.wait()
            held.give_back()
        keys = [body["workKey"] for _, _, body in self.master.asked("POST")]
        self.assertEqual(len(set(keys)), 2)

    def test_a_demand_the_master_no_longer_holds_is_asked_again(self):
        self.master.waiting_reads = 5
        self.master.forget_after_reads = 2
        held = self.demands().ask("ear", "ear listens to a file")
        self.assertEqual(held.wait(), "node-b")
        posts = self.master.asked("POST")
        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0][2]["workKey"], posts[1][2]["workKey"])
        entry = json.loads((self.folder / self.ledger()[0]).read_text())
        self.assertEqual(entry["id"], held.demand["id"])
        held.give_back()
        self.assertEqual(self.master.demands, {})

    def test_a_lost_answer_finds_the_demand_by_its_work_key(self):
        self.master.lose_next_answer = True
        held = self.demands().ask("ear", "ear listens to a file")
        self.assertEqual(len(self.master.asked("POST")), 1)
        self.assertEqual(held.wait(), "node-b")
        held.give_back()
        self.assertEqual(self.master.demands, {})

    def test_a_service_placed_on_no_node_is_refused_at_once(self):
        self.master.no_place = True
        with self.assertRaises(demand.DemandError) as raised:
            self.demands().ask("ear", "ear listens to a file")
        self.assertIn("on no node", str(raised.exception))
        self.assertEqual(self.ledger(), [])

    def test_a_demand_left_by_a_call_that_died_is_given_back(self):
        held = self.demands().ask("ear", "ear listens to a file")
        left_id = held.demand["id"]
        # The call dies: its lock goes with its process, its entry stays.
        os.close(held.entry.fd)
        self.assertEqual(len(self.ledger()), 1)

        self.demands().sweep()
        self.assertEqual(self.ledger(), [])
        self.assertIn(("DELETE", f"/demands/{left_id}", None), self.master.requests)
        self.assertNotIn(left_id, self.master.demands)

    def test_a_demand_a_running_call_holds_is_left_alone(self):
        held = self.demands().ask("ear", "ear listens to a file")
        self.demands().sweep()
        self.assertEqual(len(self.ledger()), 1)
        self.assertEqual(self.master.asked("DELETE"), [])
        held.give_back()
        self.assertEqual(self.ledger(), [])

    def test_a_left_demand_whose_answer_was_lost_is_found_and_given_back(self):
        work_key = "ear:listen:" + "c" * 32
        entry = self.demands()._held_entry(work_key)
        # The ask reached the master but its answer never came back, and the call died.
        self.master.post("/demands", {"serviceName": "ear", "count": 1, "workKey": work_key})
        os.close(entry.fd)
        self.demands().sweep()
        self.assertEqual(self.ledger(), [])
        self.assertEqual(self.master.demands, {})

    def test_a_give_back_the_master_does_not_take_stays_in_the_ledger(self):
        held = self.demands().ask("ear", "ear listens to a file")
        held.wait()
        self.master.unready = 1
        held.give_back()
        self.assertEqual(len(self.ledger()), 1)
        self.demands().sweep()
        self.assertEqual(self.ledger(), [])
        self.assertEqual(self.master.demands, {})

    def test_an_entry_is_locked_from_before_it_takes_its_name(self):
        held = self.demands().ask("ear", "ear listens to a file")
        path = self.folder / self.ledger()[0]
        fd = os.open(path, os.O_RDWR)
        try:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(fd)
        held.give_back()


class CallOnTheGrantedNodeTest(unittest.TestCase):
    """One call against the stand-in master, the node's road stood in."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.master = StandInMaster()
        settings = self.root / "ear" / "settings.toml"
        settings.parent.mkdir(parents=True)
        settings.write_text(
            SETTINGS_TEXT.replace('"http://127.0.0.1:7440"', f'"{self.master.address}"'), encoding="utf-8"
        )
        self.voice = self.root / "voice.ogg"
        self.voice.write_bytes(b"OggS a room's voice note")
        self.clock = FakeClock()

    def tearDown(self):
        self.master.close()
        self.tmp.cleanup()

    def call(self, ran):
        demands = demand.Demands(
            self.master.address,
            demand.ledger_folder(self.root),
            sleep=self.clock.sleep,
            said=lambda line: None,
            hold_ms=10,
            pause_s=600,
        )
        with mock.patch("ear.node.make_room") as make_room, \
                mock.patch("ear.node.upload") as upload, \
                mock.patch("ear.node.remove_copy") as remove_copy, \
                mock.patch("ear.node.exec_on_node", **ran) as exec_on_node:
            try:
                return transcribe(str(self.voice), self.root, demands=demands), exec_on_node
            finally:
                for one in (make_room, upload, remove_copy):
                    self.assertEqual(one.call_args.args[1], "node-b")

    def test_the_call_waits_runs_on_the_granted_node_and_gives_back(self):
        self.master.unready = 200
        self.master.waiting_reads = 50
        heard = subprocess.CompletedProcess([], 0, stdout='{"transcript": "what was said"}\n', stderr="")
        answer, exec_on_node = self.call({"return_value": heard})
        self.assertEqual(answer["transcript"], "what was said")
        self.assertGreater(self.clock.now, 24 * 3600)
        self.assertEqual(exec_on_node.call_args.args[1], "node-b")
        self.assertTrue(exec_on_node.call_args.kwargs["unbounded"])
        self.assertEqual(len(self.master.asked("DELETE")), 1)
        self.assertEqual(self.master.demands, {})
        self.assertEqual(list(demand.ledger_folder(self.root).glob("*.json")), [])

    def test_a_failed_run_gives_the_card_back(self):
        failed = subprocess.CompletedProcess([], 1, stdout="", stderr="CUDA out of memory\n")
        with self.assertRaises(CallError):
            self.call({"return_value": failed})
        self.assertEqual(self.master.demands, {})
        self.assertEqual(list(demand.ledger_folder(self.root).glob("*.json")), [])

    def test_a_node_out_of_reach_gives_the_card_back(self):
        from ear import node

        with self.assertRaises(CallError) as raised:
            self.call({"side_effect": node.NodeError("the hub console could not be run")})
        self.assertIn("node-b", str(raised.exception))
        self.assertEqual(self.master.demands, {})


if __name__ == "__main__":
    unittest.main()

"""Continuity is only real if it survives being killed.

WHY THIS EXISTS
---------------
`continuous_self_v1` claims one thread that does not stop when a task ends: a durable self, a
journal of what it was doing, and an honest account of the work that was in flight when the process
died.

Every one of those claims is cheap to make and easy to fake. A process that loses an interrupted
attempt silently has amnesia with a fresh timestamp, and a state file that is written non-atomically
turns a kill into a corrupted self. So the tests below kill it in the ugliest ways available --
mid-task, mid-write, twice in a row -- and require the account to stay true.

The decisive case is `test_an_interrupted_task_is_reported_not_hidden`: the honest answer on restart
is INTERRUPTED, never "never happened" and never "done".
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import continuous_self_v1 as CS  # noqa: E402


class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = pathlib.Path(self.tmp.name) / "self.json"
        self.journal = pathlib.Path(self.tmp.name) / "journal.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def _self(self, identity=None):
        return CS.ContinuousSelf(state_path=self.state, journal_path=self.journal,
                                 identity=identity)

    def test_a_first_start_is_a_birth_with_an_identity(self):
        first = self._self("agent-a").resume()
        self.assertFalse(first["resumed"])
        self.assertEqual(first["identity"], "agent-a")

    def test_it_resumes_as_the_same_identity_across_epochs(self):
        self._self("agent-a").resume()
        second = self._self(identity="ignored-on-resume").resume()
        self.assertTrue(second["resumed"])
        self.assertEqual(second["identity"], "agent-a")
        self.assertEqual(second["epoch"], 2)

    def test_an_interrupted_task_is_reported_not_hidden(self):
        process = self._self("agent-a")
        process.resume()
        process.begin("write-the-report")
        # No finish: the process dies here, as it would if killed.
        restarted = self._self().resume()
        self.assertTrue(restarted["resumed"])
        self.assertEqual(len(restarted["interrupted"]), 1)
        self.assertEqual(restarted["interrupted"][0]["task"], "write-the-report")
        self.assertEqual(restarted["interrupted"][0]["status"], "INTERRUPTED")
        # And it is not still in flight: nothing is doing work it is not doing.
        process2 = self._self()
        process2.resume()
        self.assertIsNone(process2.state.in_flight)

    def test_completed_work_stays_completed_across_epochs(self):
        process = self._self("agent-a")
        process.resume()
        process.begin("task-1")
        process.finish({"ok": True})
        restarted = self._self().resume()
        self.assertEqual(restarted["interrupted"], [])
        self.assertEqual(restarted["identity"], "agent-a")
        described = (lambda p: (p.resume(), p.describe())[1])(self._self())
        self.assertEqual(described["completed_count"], 1)
        self.assertEqual(described["last_completed"], "task-1")

    def test_a_torn_state_file_is_not_treated_as_a_valid_self(self):
        self._self("agent-a").resume()
        self.state.write_text('{"identity": "agent-a", "started_at": ')  # half-written
        fresh = self._self("agent-b").resume()
        self.assertFalse(fresh["resumed"])
        self.assertEqual(fresh["identity"], "agent-b")

    def test_the_journal_alone_reconstructs_what_it_was_doing(self):
        process = self._self("agent-a")
        process.resume()
        process.begin("task-1")
        process.finish({"ok": True})
        process.begin("task-2")  # killed here
        restarted = self._self()
        restarted.resume()  # the restart is what writes the INTERRUPTED record
        kinds = [row["kind"] for row in restarted.journal()]
        # The whole history is legible from the journal, in order, with no gap where the kill was.
        self.assertEqual(kinds, ["BIRTH", "BEGIN", "FINISH", "BEGIN", "INTERRUPTED", "RESUME"])

    def test_the_state_file_is_replaced_atomically(self):
        process = self._self("agent-a")
        process.resume()
        process.beat()
        # No .tmp file left behind, and the state file parses.
        self.assertEqual([p.name for p in self.state.parent.glob("*.tmp")], [])
        json.loads(self.state.read_text())

    def test_a_failing_task_does_not_end_the_thread(self):
        process = self._self("agent-a")
        tasks = iter(["explodes", "works"])

        def next_task(_state):
            return next(tasks, None)

        def perform(task, _self):
            if task == "explodes":
                raise RuntimeError("boom")
            return {"ok": True}

        result = process.run(next_task=next_task, perform=perform, max_steps=2)
        self.assertEqual(result["steps"], 2)
        self.assertEqual(result["describe"]["completed_count"], 2)

    def test_describe_says_what_it_is_doing_right_now(self):
        process = self._self("agent-a")
        process.resume()
        self.assertEqual(process.describe()["doing_now"], "IDLE")
        process.begin("task-9")
        self.assertEqual(process.describe()["doing_now"], "task-9")

    def test_it_survives_being_killed_by_the_operating_system(self):
        """The one that matters: SIGKILL while a task is in flight, from outside."""
        script = textwrap.dedent(f"""
            import sys, time
            sys.path.insert(0, {str(pathlib.Path(__file__).resolve().parents[2])!r})
            from canonical.runtime import continuous_self_v1 as CS
            p = CS.ContinuousSelf(state_path={str(self.state)!r}, journal_path={str(self.journal)!r},
                                 identity="agent-kill")
            p.resume()
            p.begin("long-task")
            print("IN_FLIGHT", flush=True)
            time.sleep(60)
        """)
        proc = subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(proc.stdout.readline().strip(), "IN_FLIGHT")
        finally:
            proc.kill()
            proc.wait(timeout=10)
        restarted = self._self().resume()
        self.assertTrue(restarted["resumed"])
        self.assertEqual(restarted["identity"], "agent-kill")
        self.assertEqual([r["task"] for r in restarted["interrupted"]], ["long-task"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

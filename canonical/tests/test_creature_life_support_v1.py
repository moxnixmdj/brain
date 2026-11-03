"""True-capability tests for creature_life_support_v1: the resident life loop.

A test here is true only if it cannot pass without the named capability:
  * unattended real repair          -> a seeded bug is actually fixed on disk
  * crash-resume (SIGKILL)          -> same identity, spent life preserved, epoch+1
  * graceful stop (SIGTERM)         -> exits 0 between pulses, heartbeats intact
  * mortality                       -> idle spends nothing; LIFE_OVER is terminal;
                                       a bigger --life on restart is ignored
  * durable liveness                -> one fsynced heartbeat per pulse on disk

No mocks of the loop, the daemon, the creature or the filesystem. The kill tests
spawn real subprocesses and signal them with the operating system.
"""
from __future__ import annotations

import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import creature_life_support_v1 as LS  # noqa: E402
from canonical.runtime import mortality_and_triage_v1 as M  # noqa: E402

BUGGY_SRC = "def transform(v):\n    return v - 3\n"
BUGGY_TEST = (
    "from buggy import transform\n\n"
    "def test_transform():\n"
    "    assert transform(5) == 8\n"
)


def seed_bug(ws: pathlib.Path) -> None:
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "buggy.py").write_text(BUGGY_SRC, encoding="utf-8")
    (ws / "test_buggy.py").write_text(BUGGY_TEST, encoding="utf-8")


def seed_clean(ws: pathlib.Path) -> None:
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "ok.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (ws / "test_ok.py").write_text(
        "from ok import add\n\ndef test_add():\n    assert add(1, 1) == 2\n",
        encoding="utf-8",
    )


def assert_repaired_on_disk(ws: pathlib.Path) -> None:
    """Prove the seeded bug is REALLY fixed in the on-disk file, behaviorally.

    Stronger than a source-substring match (which a comment could satisfy while
    the bug remains): execute the repaired file in a fresh interpreter and
    require the repaired semantics on several inputs. The seed ``v - 3`` fails
    ``transform(5) == 8``, so a pass here is only possible if the creature
    actually rewrote the file. Accepts any correct repair (``v + 3``, ``3 + v``,
    ``v - -3``, ...), not one spelling.
    """
    probe = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "from buggy import transform; "
        "assert transform(5) == 8, transform(5); "
        "assert transform(0) == 3, transform(0); "
        "assert transform(-1) == 2, transform(-1); "
        "print('REPAIRED_ON_DISK_OK')"
    )
    r = subprocess.run(
        [sys.executable, "-c", probe, str(ws)],
        capture_output=True, text=True, timeout=30)
    if r.returncode != 0 or "REPAIRED_ON_DISK_OK" not in r.stdout:
        raise AssertionError(
            "buggy.py on disk was not behaviorally repaired: "
            f"rc={r.returncode} stdout={r.stdout!r} stderr={r.stderr!r} "
            f"source={(ws / 'buggy.py').read_text(encoding='utf-8')!r}")


class LifeSupportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="creature_ls_")
        self.root = pathlib.Path(self._tmp.name)
        self.ws = self.root / "ws"
        self.st = self.root / "state"

    def tearDown(self):
        self._tmp.cleanup()

    # ---------------------------------------------------------------- budgets

    def test_no_budget_is_refused(self):
        with self.assertRaises(ValueError):
            LS.run_life_support(self.ws, self.st)

    def test_bounded_pulse_count_is_exact_and_heartbeat_per_pulse(self):
        seed_clean(self.ws)
        out = LS.run_life_support(self.ws, self.st, pulses=3, interval_s=0.0)
        self.assertEqual(out["pulses"], 3)
        self.assertEqual(out["stopped_by"], "MAX_PULSES")
        self.assertEqual(out["k3_external_llm_calls"], 0)
        self.assertEqual(out["does_not_measure"], "sentience, experience, selfhood")
        lines = (self.st / "heartbeats.jsonl").read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 3)  # one durable heartbeat per pulse, no more
        rows = [json.loads(x) for x in lines]
        self.assertEqual([r["pulse"] for r in rows], [1, 2, 3])
        latest = json.loads((self.st / "heartbeat.json").read_text(encoding="utf-8"))
        self.assertEqual(latest["pulse"], 3)
        saved = json.loads((self.st / "life_support_report.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["pulses"], 3)

    def test_seconds_budget_stops_between_pulses(self):
        seed_clean(self.ws)
        out = LS.run_life_support(self.ws, self.st, seconds=0.3, interval_s=0.02)
        self.assertEqual(out["stopped_by"], "MAX_SECONDS")
        self.assertGreaterEqual(out["pulses"], 1)

    def test_pre_set_stop_event_stops_before_any_pulse(self):
        seed_clean(self.ws)
        ev = threading.Event()
        ev.set()
        out = LS.run_life_support(self.ws, self.st, resident=True, stop_event=ev)
        self.assertEqual(out["pulses"], 0)
        self.assertEqual(out["stopped_by"], "SIGNAL")

    # ------------------------------------------------------------- mortality

    def test_idle_pulses_spend_no_life(self):
        seed_clean(self.ws)
        out = LS.run_life_support(self.ws, self.st, pulses=3, interval_s=0.0)
        self.assertEqual(out["life_spent"], 0.0)
        self.assertEqual(out["life_remaining"], 40.0)
        self.assertFalse(out["ended"])

    def test_life_over_is_terminal_and_not_re_granted(self):
        # A creature whose life is already gone (written through the canonical
        # LifeStore, exactly as a previous epoch would have left it).
        c_dir = self.st / "creature"
        c_dir.mkdir(parents=True)
        M.LifeStore(c_dir / "life.json").save(
            M.Life(identity="creature", granted=2.0, spent=2.0))
        seed_clean(self.ws)
        out = LS.run_life_support(self.ws, self.st, pulses=5, life=40.0, interval_s=0.0)
        self.assertEqual(out["pulses"], 0)
        self.assertEqual(out["stopped_by"], "LIFE_OVER")
        self.assertTrue(out["ended"])
        self.assertEqual(out["life_remaining"], 0.0)

    # ------------------------------------------------------- unattended repair

    def test_it_repairs_a_real_bug_unattended_and_spends_life_for_it(self):
        seed_bug(self.ws)
        out = LS.run_life_support(
            self.ws, self.st, pulses=2, interval_s=0.0, apply_verified_repairs=True)
        assert_repaired_on_disk(self.ws)  # the real file on disk was repaired
        self.assertGreater(out["life_spent"], 0.0)  # real work costs real life
        self.assertGreaterEqual(out["closed"], 1)

    def test_restart_with_a_bigger_life_grant_is_ignored(self):
        seed_bug(self.ws)
        first = LS.run_life_support(
            self.ws, self.st, pulses=2, interval_s=0.0,
            life=40.0, apply_verified_repairs=True)
        spent = first["life_spent"]
        self.assertGreater(spent, 0.0)
        again = LS.run_life_support(
            self.ws, self.st, pulses=1, interval_s=0.0,
            life=1000.0, apply_verified_repairs=True)  # tempting fountain of youth
        self.assertEqual(again["life_spent"], spent)  # nothing new was spent
        self.assertAlmostEqual(again["life_remaining"], 40.0 - spent, places=3)
        self.assertEqual(again["epoch"], first["epoch"] + 1)

    # ------------------------------------------------- real OS kill / resume

    def _spawn_resident(self, *, apply_repairs: bool) -> subprocess.Popen:
        cmd = [sys.executable, "-m", "canonical.runtime.creature_life_support_v1",
               "--workspace", str(self.ws), "--state", str(self.st),
               "--resident", "--interval-s", "0.05", "--json"]
        if apply_repairs:
            cmd.append("--apply-verified-repairs")
        env = dict(os.environ, PYTHONPATH=str(REPO))
        return subprocess.Popen(
            cmd, cwd=str(REPO), env=env, start_new_session=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def _wait_for_heartbeat(self, predicate, timeout_s: float = 90.0) -> dict:
        hb = self.st / "heartbeat.json"
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if hb.is_file():
                try:
                    row = json.loads(hb.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    row = None
                if row and predicate(row):
                    return row
            time.sleep(0.1)
        raise AssertionError("heartbeat condition never met before timeout")

    def test_sigkill_then_restart_resumes_identity_life_and_finished_work(self):
        seed_bug(self.ws)
        proc = self._spawn_resident(apply_repairs=True)
        try:
            row = self._wait_for_heartbeat(
                lambda r: (r.get("life_spent") or 0) > 0 and (r.get("closed") or 0) >= 1)
            epoch_before = row["epoch"]
            spent_before = row["life_spent"]
            closed_before = row["closed"]
        finally:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)  # the OS kills it mid-life
            proc.wait(timeout=15)
        assert_repaired_on_disk(self.ws)

        again = LS.run_life_support(
            self.ws, self.st, pulses=1, interval_s=0.0, apply_verified_repairs=True)
        self.assertEqual(again["identity"], "creature")
        self.assertEqual(again["epoch"], epoch_before + 1)  # new epoch, same self
        self.assertEqual(again["life_spent"], spent_before)  # spent stays spent
        self.assertGreaterEqual(again["closed"], closed_before)  # work not redone
        self.assertEqual(again["life_remaining"], round(40.0 - spent_before, 3))

    def test_sigterm_stops_gracefully_between_pulses(self):
        seed_clean(self.ws)
        proc = self._spawn_resident(apply_repairs=False)
        try:
            self._wait_for_heartbeat(lambda r: (r.get("pulse") or 0) >= 2)
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            stdout, stderr = proc.communicate(timeout=30)
        finally:
            if proc.poll() is None:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                proc.wait(timeout=10)
        self.assertEqual(proc.returncode, 0, msg=stderr[-2000:])
        # the CLI prints one pretty-printed JSON object; tolerate any log lines before it
        out = json.loads(stdout[stdout.index("{"):])
        self.assertEqual(out["stopped_by"], "SIGNAL")
        self.assertGreaterEqual(out["pulses"], 2)
        self.assertEqual(out["k3_external_llm_calls"], 0)
        # heartbeats on disk match the reported pulse count exactly
        lines = (self.st / "heartbeats.jsonl").read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), out["pulses"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

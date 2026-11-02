"""Is the creature real, or three passing modules with nothing running?

WHY THIS EXISTS
---------------
Measured 2026-11-02: `continuous_self_v1` (10 tests), `creature_stakes_and_initiative_v1`
(16 tests) and `ignorance_ledger_v1` (13 tests) each pass, and none is ever started.
`continuous_self_v1` has no `__main__`; `ContinuousSelf(` appears only inside its own test;
`choose()`/`work()` have zero non-test callers; `open_gaps()` is ORPHAN. So CI proves daily
that a creature *would* survive a kill and *would* be changed by its history, and no creature
exists to kill.

`creature_v1` is the switch that connects them. These tests are written as negative controls,
in the house style, because every property here is cheap to fake:

  DECISIVE   test_a_history_of_failure_changes_what_it_does_next
             Two creatures, identical ledgers, one told it succeeded and one told it failed. If
             they end in the same posture, the composition wired `record` to nothing and the
             stakes are decoration -- exactly what `creature-stakes.yml` exists to catch.

  DECISIVE   test_it_survives_being_killed_and_comes_back_as_the_same_creature
             SIGKILL mid-task from outside, through the composition. It must resume as the same
             identity, report the in-flight gap INTERRUPTED, and keep the standing it had earned.

  HONEST     test_it_never_invents_work_when_it_knows_nothing
             An empty ledger must idle. `demonstration_ledger()` must not be reachable from a run,
             or the creature would look busy on a fixture and call that initiative.

  HONEST     test_a_failure_of_this_box_is_not_recorded_as_a_failure_of_the_creature
             An environment blocker must change neither posture nor ledger, because a missing apt
             package is a fact about the runner that would otherwise outlive it as false memory.

  ISOLATION  test_a_run_against_a_temp_ledger_never_writes_the_tracked_one
             The default ledger is tracked state. A measurement that mutates the tree it measures
             is the defect `AGENTS.md` rule 1 exists to prevent.
"""
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import creature_v1 as C  # noqa: E402
from canonical.runtime import ignorance_ledger_v1 as ledger  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
TRACKED_LEDGER = ROOT / "canonical/astra_runtime/state/IGNORANCE_LEDGER_V1.json"

# Distinct multi-word gaps. Single-digit distinguishers ("gap 0" vs "gap 1") collapse to one
# gap because the ledger keys on `[a-z0-9]{2,}` tokens -- using them here would silently test a
# one-gap ledger and every "multiple obligations" assertion below would be vacuous.
DISTINCT = ["alpha widget", "bravo widget", "charlie widget", "delta widget",
            "echo widget", "foxtrot widget"]


def seed(path, words=DISTINCT, cost=1.0):
    for w in words:
        ledger.note(f"distinct gap about {w} processing", cost=cost, path=path)
    return ledger.open_gaps(path)


def constant_verdict(passes):
    """A performer that returns the same verdict every time."""
    def perform(task, goal):
        return {"pass": bool(passes), "status": "PASS__X" if passes else "FAIL_CLOSED__Y",
                "compiled_capability_id": "cap.stub"}
    return perform


class CreatureComposition(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self._tmp.name)
        self.led = str(self.d / "ledger.json")
        self.state = self.d / "self"

    def tearDown(self):
        self._tmp.cleanup()

    def creature(self, identity, performer=None, **kw):
        return C.Creature(state_dir=self.state, ledger_path=self.led,
                          identity=identity, performer=performer, **kw)

    # ------------------------------------------------------------------ decisive

    def test_a_history_of_failure_changes_what_it_does_next(self):
        """Same ledger, same work, opposite verdicts -> opposite postures."""
        seed(self.led)
        good = self.creature("good", constant_verdict(True)).run(max_steps=4)
        # a separate state dir so the two creatures do not share a standing
        bad_dir = self.d / "bad"
        bad = C.Creature(state_dir=bad_dir, ledger_path=self.led, identity="bad",
                         performer=constant_verdict(False)).run(max_steps=4)

        self.assertEqual(good["posture_after"], "BOLD")
        self.assertEqual(bad["posture_after"], "CAUTIOUS")
        self.assertNotEqual(good["posture_after"], bad["posture_after"])
        self.assertEqual(good["standing"]["verified_correct"], 4)
        self.assertEqual(bad["standing"]["verified_wrong"], 4)
        self.assertGreaterEqual(bad["standing"]["caution_episodes"], 1)

    def test_it_survives_being_killed_and_comes_back_as_the_same_creature(self):
        """SIGKILL mid-task, through the composition. The one that matters."""
        seed(self.led, words=["alpha widget"])  # one gap so it is certainly in flight
        script = textwrap.dedent(f"""
            import sys, time
            sys.path.insert(0, {str(ROOT)!r})
            from canonical.runtime import creature_v1 as C
            def block(task, goal):
                print("IN_FLIGHT " + task, flush=True)
                time.sleep(60)
                return {{"pass": True, "status": "PASS__X"}}
            c = C.Creature(state_dir={str(self.state)!r}, ledger_path={self.led!r},
                           identity="kill-me", performer=block)
            c.run(max_steps=1)
        """)
        proc = subprocess.Popen([sys.executable, "-c", script],
                                stdout=subprocess.PIPE, text=True)
        try:
            first = proc.stdout.readline().strip()
        finally:
            proc.kill()
            proc.wait(timeout=10)
        self.assertTrue(first.startswith("IN_FLIGHT"), first)

        # A fresh creature resumes: same identity, the in-flight gap reported INTERRUPTED.
        reborn = self.creature(None)  # no identity -> resume() must recover "kill-me"
        row = reborn.run(max_steps=0)
        self.assertTrue(row["resumed"])
        self.assertEqual(row["identity"], "kill-me")
        interrupted = [r.get("task") for r in row["interrupted_on_resume"]]
        self.assertTrue(interrupted and interrupted[0], "in-flight gap must be INTERRUPTED")

    # --------------------------------------------------------------------- honest

    def test_it_never_invents_work_when_it_knows_nothing(self):
        """An empty ledger idles. No fixture work is substituted."""
        self.assertEqual(ledger.open_gaps(self.led), 0)
        cr = self.creature("idle")
        row = cr.run(max_steps=5)
        self.assertEqual(row["attempts"], [])          # nothing performed
        self.assertEqual(row["standing"]["attempts"], 0)
        self.assertEqual(row["steps"], 5)              # but it did loop, idling
        self.assertEqual(row["describe"]["completed_count"], 0)

    def test_a_failure_of_this_box_is_not_recorded_as_a_failure_of_the_creature(self):
        """An environment blocker changes neither posture nor the ledger."""
        seed(self.led, words=["alpha widget", "bravo widget", "charlie widget"])
        tried_before = ledger.stats(self.led)["tried"]

        def blocked(task, goal):
            return {"pass": False, "status": "FAIL__Z",
                    "reason": "BOUND_APT_PACKAGE_NOT_INSTALLED: jq missing"}

        row = self.creature("blocked", blocked).run(max_steps=3)
        self.assertEqual(row["posture_after"], "MEASURED")
        self.assertEqual(row["standing"]["attempts"], 0)          # nothing recorded against it
        self.assertEqual(ledger.stats(self.led)["tried"], tried_before)  # ledger untouched
        self.assertTrue(all(s.get("environment_blocked") == "BOUND_APT_PACKAGE_NOT_INSTALLED"
                            for s in row["attempts"]))
        self.assertTrue(all(s.get("recorded") == [] for s in row["attempts"]))

    def test_the_ledger_learns_which_ignorance_mattered(self):
        """A pass resolves and helps; a fail increments trials but leaves the gap open."""
        seed(self.led, words=["alpha widget", "bravo widget"])
        seq = iter([{"pass": True, "status": "PASS__X"}, {"pass": False, "status": "FAIL__Y"}])

        def perform(task, goal):
            return next(seq)

        self.creature("learn", perform).run(max_steps=2)
        st = ledger.stats(self.led)
        self.assertEqual(st["tried"], 2)          # both gaps were attempted
        self.assertEqual(st["ever_helped"], 1)    # only the pass helped
        self.assertEqual(st["resolved"], 1)       # only the pass closed
        self.assertEqual(st["open"], 1)           # the failure stays open to retry

    def test_an_exception_is_unverified_not_wrong(self):
        """A crash is recorded verified=False, which drives unverified_claims, not verified_wrong."""
        seed(self.led, words=["alpha widget", "bravo widget"])

        def boom(task, goal):
            raise ValueError("performer exploded")

        row = self.creature("boom", boom).run(max_steps=2)
        st = row["standing"]
        self.assertEqual(st["verified_wrong"], 0)
        self.assertEqual(st["unverified_claims"], 2)
        self.assertTrue(all(s.get("verified") is False for s in row["attempts"]))

    # ------------------------------------------------------------------ isolation

    def test_a_run_against_a_temp_ledger_never_writes_the_tracked_one(self):
        before = hashlib.sha256(TRACKED_LEDGER.read_bytes()).hexdigest()
        seed(self.led)
        self.creature("isolated", constant_verdict(True)).run(max_steps=3)
        C.report(self.creature("isolated2"))
        after = hashlib.sha256(TRACKED_LEDGER.read_bytes()).hexdigest()
        self.assertEqual(before, after, "the tracked ledger must not move when measuring")

    # ------------------------------------------------------------------ continuity

    def test_standing_carries_across_two_lives_of_the_same_creature(self):
        """A second Creature on the same state_dir inherits the first one's posture."""
        seed(self.led, words=["alpha widget", "bravo widget", "charlie widget",
                              "delta widget", "echo widget", "foxtrot widget"])
        first = self.creature("same", constant_verdict(False)).run(max_steps=2)
        self.assertEqual(first["posture_after"], "CAUTIOUS")
        # a new instance, same dir, no explicit standing: must load the earned one
        second = self.creature(None)
        row = second.run(max_steps=0)
        self.assertEqual(row["identity"], "same")
        self.assertEqual(row["posture_before"], "CAUTIOUS")
        self.assertEqual(row["standing"]["verified_wrong"], 2)


class CreatureCli(unittest.TestCase):
    """The process path, which the library tests above do not exercise.

    A double-resume lived here: `main()` resumed and then `run()` resumed again, so a fresh
    start reported epoch 2 and -- worse -- consumed any interrupted-work record before the run
    could report it. These assert the CLI path a workflow actually invokes.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self._tmp.name)
        self.led = str(self.d / "ledger.json")
        self.state = str(self.d / "self")

    def tearDown(self):
        self._tmp.cleanup()

    def test_a_fresh_start_through_main_is_epoch_one_not_two(self):
        seed(self.led, words=["alpha widget"])
        rc = C.main(["--state-dir", self.state, "--ledger", self.led,
                     "--identity", "cli-fresh", "--max-steps", "1", "--json"])
        self.assertEqual(rc, 0)
        # re-open the durable state the run wrote: exactly one epoch, one birth, no phantom resume
        state = json.loads((pathlib.Path(self.state) / "self_state.json").read_text())
        self.assertEqual(state["epoch"], 1)
        journal = [json.loads(line) for line in
                   (pathlib.Path(self.state) / "journal.jsonl").read_text().splitlines() if line]
        kinds = [r["kind"] for r in journal]
        self.assertEqual(kinds.count("BIRTH"), 1)
        self.assertNotIn("RESUME", kinds)

    def test_main_report_does_not_mutate_the_ledger(self):
        seed(self.led, words=["alpha widget", "bravo widget"])
        before = pathlib.Path(self.led).read_bytes()
        rc = C.main(["--report", "--state-dir", self.state, "--ledger", self.led, "--json"])
        self.assertEqual(rc, 0)
        self.assertEqual(before, pathlib.Path(self.led).read_bytes())


class CreatureInitiative(unittest.TestCase):
    """Its criterion, against luck, on a ledger scarce enough to tell them apart."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self._tmp.name)
        self.led = str(self.d / "ledger.json")

    def tearDown(self):
        self._tmp.cleanup()

    def test_its_own_criterion_beats_random_on_a_scarce_real_ledger(self):
        # costs vary so value-per-cost differs, and the budget is scarce (the saturated case
        # closes everything for every chooser and cannot distinguish them -- documented, not
        # assumed, in test_stakes_are_real_not_decoration_v1).
        for i, w in enumerate(DISTINCT):
            ledger.note(f"distinct gap about {w} processing", cost=2.0 + i, path=self.led)
        cr = C.Creature(state_dir=self.d / "self", ledger_path=self.led, identity="scarce")
        sel = cr.selection_on_real_obligations(steps=8)
        self.assertGreater(len(cr.obligations()), 1)
        self.assertTrue(sel["own_beats_random"], sel)
        self.assertGreater(sel["ratio_vs_random"], 1.0)

    def test_a_saturated_budget_is_reported_as_the_non_comparison_it_is(self):
        # Enough steps to close everything: every chooser ties. Asserted so the meaningful
        # comparison above is not mistaken for a property that holds at any budget.
        seed(self.led, words=["alpha widget", "bravo widget"])
        cr = C.Creature(state_dir=self.d / "self", ledger_path=self.led, identity="rich")
        sel = cr.selection_on_real_obligations(steps=40)
        self.assertEqual(sel["own_criterion"]["realised_value"],
                         sel["random"]["realised_value"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

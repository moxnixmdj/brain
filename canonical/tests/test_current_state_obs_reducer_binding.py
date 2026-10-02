"""Pin the binding of POINTER_OPEN_MECHANISM_RESIDUAL_COUNT_DRIFT.

The predicate was born unsatisfiable: the pointer has carried
``open_mechanism_residual_count`` under ``current_frontier`` since 50c4e086, but the
check added later in 5b5cdb72 read it from ``execution_governance``, which has never
held it, so it compared the authority against ``None`` and fired on every tree --
including compliant ones -- making the authoritative current-state reducer fail closed
on main and every OBS receipt derived from it unsound.

These tests hold the general invariant, not just the one field: a drift predicate must
read a path the live surfaces actually carry, and it must still fire when the value is
wrong. An unsatisfiable predicate and an absent one are the same failure -- neither can
ever report real drift.
"""
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
POINTER = "canonical/CANONICAL_POINTER.json"
UNIVERSE = "canonical/governance/GLOBAL_TERMINAL_UNIVERSE_V1.json"
PREDICATE = "POINTER_OPEN_MECHANISM_RESIDUAL_COUNT_DRIFT"


def _load_reducer():
    path = REPO / "canonical/runtime/current_state_obs_reducer.py"
    spec = importlib.util.spec_from_file_location("csor_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _overlay_root(tmp: pathlib.Path, overrides: dict) -> pathlib.Path:
    """A tree that is the live repository by symlink, except for `overrides`.

    Only the directories along an overridden path are materialised; everything else is
    a symlink, so the fixture cannot drift away from the live surfaces it stands for.
    """
    tmp = pathlib.Path(tmp)

    def materialise(src: pathlib.Path, dst: pathlib.Path, rel: str):
        dst.mkdir(parents=True, exist_ok=True)
        for name in sorted(os.listdir(src)):
            child_rel = f"{rel}/{name}" if rel else name
            child_src, child_dst = src / name, dst / name
            if child_rel in overrides:
                child_dst.write_text(overrides[child_rel])
            elif any(k.startswith(child_rel + "/") for k in overrides):
                materialise(child_src, child_dst, child_rel)
            else:
                child_dst.symlink_to(child_src, target_is_directory=child_src.is_dir())

    materialise(REPO, tmp, "")
    return tmp


class OpenMechanismCountBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reducer = _load_reducer()
        cls.pointer = json.loads((REPO / POINTER).read_text())
        cls.universe = json.loads((REPO / UNIVERSE).read_text())
        cls.expected = (cls.universe.get("counts") or {}).get("open_mechanism_lanes")

    def test_the_bound_path_exists_whenever_the_authority_declares_a_count(self):
        """The predicate must be satisfiable: the field it reads must be populated."""
        if self.expected is None:
            self.skipTest("the authority declares no open_mechanism_lanes count")
        current = self.pointer.get("current_frontier") or {}
        self.assertIn(
            "open_mechanism_residual_count", current,
            "the pointer's current_frontier no longer carries open_mechanism_residual_count, so "
            "POINTER_OPEN_MECHANISM_RESIDUAL_COUNT_DRIFT has become unsatisfiable again; rebind the "
            "check to wherever the live pointer carries the count, never to a path no surface writes")
        self.assertIsNotNone(current.get("open_mechanism_residual_count"))

    def test_live_tree_does_not_report_open_mechanism_count_drift(self):
        if self.expected is None:
            self.skipTest("the authority declares no open_mechanism_lanes count")
        out = self.reducer.evaluate(REPO)
        self.assertNotIn(
            PREDICATE, out.get("errors") or [],
            "the live pointer disagrees with the authority's open_mechanism_lanes count; this is "
            "real drift and must be reconciled from the authority, not by loosening the check")

    def test_a_wrong_count_still_fails_closed(self):
        """Teeth: the predicate fires when the mirror disagrees with the authority."""
        if self.expected is None:
            self.skipTest("the authority declares no open_mechanism_lanes count")
        broken = json.loads(json.dumps(self.pointer))
        broken["current_frontier"]["open_mechanism_residual_count"] = self.expected + 1
        with tempfile.TemporaryDirectory() as td:
            root = _overlay_root(pathlib.Path(td) / "tree",
                                 {POINTER: json.dumps(broken, indent=2) + "\n"})
            out = self.reducer.evaluate(root)
        self.assertIn(PREDICATE, out.get("errors") or [],
                      "seeding a wrong count did not fire the predicate: the check is not reading "
                      "the value it claims to compare")
        self.assertFalse(out.get("pass"))

    def test_a_missing_count_is_unknown_and_fails_closed(self):
        """Absence must never read as agreement -- the original Stage-A sin."""
        if self.expected is None:
            self.skipTest("the authority declares no open_mechanism_lanes count")
        broken = json.loads(json.dumps(self.pointer))
        broken["current_frontier"].pop("open_mechanism_residual_count", None)
        with tempfile.TemporaryDirectory() as td:
            root = _overlay_root(pathlib.Path(td) / "tree",
                                 {POINTER: json.dumps(broken, indent=2) + "\n"})
            out = self.reducer.evaluate(root)
        self.assertIn(PREDICATE, out.get("errors") or [],
                      "a missing count was treated as agreement; unknown must fail closed")

    def test_the_check_does_not_read_a_path_no_surface_populates(self):
        """Guard the general invariant against the specific regression returning."""
        src = (REPO / "canonical/runtime/current_state_obs_reducer.py").read_text()
        self.assertIn('current.get("open_mechanism_residual_count")', src,
                      "the count is no longer read from current_frontier, the only pointer "
                      "sub-object that has ever carried it")
        self.assertNotIn('eg.get("open_mechanism_residual_count")', src,
                         "the count is read from execution_governance again, a sub-object that has "
                         "never carried it; that binding made the predicate unsatisfiable")


POST_CUT_PREDICATE = "HIERARCHY_IGNORES_POST_CUT_MECHANISM_BLOCKER"
HIERARCHY = "canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json"
# Resolved from the module's own pin rather than hardcoded here, so this test follows
# the frontier to V3 instead of rotting the way the token it replaces did.
VERDICT = _load_reducer().OUTER_OBSERVATION_CUT
UNIVERSE = _load_reducer().GLOBAL_UNIVERSE


class PostCutBlockerExpectationTests(unittest.TestCase):
    """The post-cut blocker expectation must come from the live verdict artifact.

    It was a phase token frozen into the source -- V1's
    ``M2_M3_M4_M5_OPERATIVE_ROUTE_CLOSURE`` -- while every other surface in the module
    is pinned to the V2 verdict, which declares no blocker. So the predicate fired on
    every compliant tree: the authoritative reducer reported pass=false for a sound
    frontier, and real drift became indistinguishable from a stale pin.
    """

    @classmethod
    def setUpClass(cls):
        cls.reducer = _load_reducer()
        cls.hierarchy = json.loads((REPO / HIERARCHY).read_text())
        cls.verdict = json.loads((REPO / VERDICT).read_text())
        cls.blocker = str(cls.hierarchy.get("current_parent_blocker") or "")

    def _errors_with_verdict(self, blocker_value, force_phase=False):
        """Overlay the verdict, and optionally the cut phase the check is gated on.

        The predicate only runs while the observation cut is exact but not
        exact_cut_ready. That is a phase, not a constant: the live tree has been on
        both sides of it during this work, and a teeth test that inherits the live
        phase silently stops testing anything the day the frontier advances. So the
        witness constructs its own precondition instead of borrowing one.
        """
        verdict = json.loads(json.dumps(self.verdict))
        if blocker_value is None:
            verdict.pop("blocker", None)
        else:
            verdict["blocker"] = blocker_value
        overrides = {VERDICT: json.dumps(verdict, indent=2) + "\n"}
        if force_phase:
            universe = json.loads((REPO / UNIVERSE).read_text())
            cut = universe.setdefault("global_cut", {})
            cut["terminal_observation_cut_exact"] = True
            cut["exact_cut_ready"] = False
            overrides[UNIVERSE] = json.dumps(universe, indent=2) + "\n"
        with tempfile.TemporaryDirectory() as td:
            root = _overlay_root(pathlib.Path(td) / "tree", overrides)
            return self.reducer.evaluate(root).get("errors") or []

    def test_live_tree_does_not_report_post_cut_blocker_drift(self):
        self.assertNotIn(POST_CUT_PREDICATE, self.reducer.evaluate(REPO).get("errors") or [],
                         "the live hierarchy is being judged against an expectation the live verdict "
                         "does not declare; resolve the expectation from the verdict artifact")

    def test_a_verdict_blocker_the_hierarchy_ignores_fails_closed(self):
        """Teeth: a declared blocker the hierarchy does not name must still fire."""
        errors = self._errors_with_verdict("SOME_POST_CUT_PHASE_THE_HIERARCHY_IGNORES__detail",
                                           force_phase=True)
        self.assertIn(POST_CUT_PREDICATE, errors,
                      "the verdict declared a blocker phase and the hierarchy ignored it, but the "
                      "predicate stayed silent: the check has no teeth")

    def test_a_verdict_blocker_the_hierarchy_reflects_passes(self):
        phase = self.blocker.split("__")[0]
        self.assertTrue(phase, "the live hierarchy blocker has no phase segment to test against")
        self.assertNotIn(POST_CUT_PREDICATE,
                         self._errors_with_verdict(phase + "__some_detail", force_phase=True))

    def test_a_verdict_that_declares_no_blocker_is_not_drift(self):
        self.assertNotIn(POST_CUT_PREDICATE, self._errors_with_verdict(None, force_phase=True),
                         "a verdict declaring no blocker leaves nothing to enforce; inventing an "
                         "expectation the authority never declared would manufacture drift")

    def test_the_expectation_is_not_a_frozen_phase_token(self):
        src = (REPO / "canonical/runtime/current_state_obs_reducer.py").read_text()
        self.assertNotIn('"OPERATIVE_ROUTE_CLOSURE"', src,
                         "a superseded verdict's phase token is hardcoded again; the frontier has "
                         "moved past V1 and the module is pinned to V2 everywhere else")
        self.assertIn('outer_observation_cut or {}).get("blocker")', src,
                      "the post-cut expectation is no longer resolved from the live verdict artifact")


class LiveTreeSoundnessTests(unittest.TestCase):
    """The authoritative reducer must be sound at this head.

    This is the claim the whole repair arc rests on, so it is asserted rather than
    described: every OBS receipt in the repository derives from this verdict, and the
    continuous-obs-runtime CI job runs the same command against the base tree. It has
    caught fresh drift more than once while this work was in flight, which is the point
    of shipping it rather than reporting a one-off measurement.
    """

    def test_live_tree_reduces_to_a_sound_current_state(self):
        out = _load_reducer().evaluate(REPO)
        self.assertEqual(
            out.get("errors") or [], [],
            "the authoritative current-state reducer reports drift at this head; reconcile the "
            "mirrors with python3 canonical/runtime/reconcile_frontier_mirrors.py . and, if a "
            "predicate names an authority rather than a mirror, repair the binding instead of "
            "the data")
        self.assertTrue(out.get("pass"))


if __name__ == "__main__":
    unittest.main()

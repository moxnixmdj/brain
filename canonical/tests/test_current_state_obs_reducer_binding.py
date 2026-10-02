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


if __name__ == "__main__":
    unittest.main()

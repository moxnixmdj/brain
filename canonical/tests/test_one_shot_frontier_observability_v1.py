from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import one_shot_verified_closure_v1 as closure


class OneShotFrontierObservabilityV1Tests(unittest.TestCase):
    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        for rel in closure.LOAD_BEARING_PATHS:
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("BASE:" + rel + "\n", encoding="utf-8")
        state = root / "canonical/runtime/SELF_IMPROVEMENT_STATE_V1.json"
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text("{}\n", encoding="utf-8")
        return td, root, state

    def _snapshot(self, root: Path, state: Path):
        with patch.object(
            closure.learning,
            "load_state",
            return_value={"improvement_queue": {}, "stats": {}},
        ), patch.object(
            closure,
            "_canonical_r2_residual",
            return_value={"current_internal_unsolved_count": 0},
        ), patch.object(
            closure,
            "_terminal_checkpoint_snapshot",
            return_value={"terminal": False},
        ):
            return closure.frontier_snapshot(repo_root=root, state_path=state)

    def test_capability_registry_mutation_changes_frontier_digest(self):
        td, root, state = self._root()
        try:
            before = self._snapshot(root, state)
            target = root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
            target.write_text("CHANGED_CAPABILITY_REGISTRY\n", encoding="utf-8")
            after = self._snapshot(root, state)
        finally:
            td.cleanup()
        self.assertNotEqual(before["digest"], after["digest"])

    def test_dynamic_route_pointer_mutation_changes_frontier_digest(self):
        td, root, state = self._root()
        try:
            before = self._snapshot(root, state)
            target = root / "canonical/governance/CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json"
            target.write_text("CHANGED_DYNAMIC_ROUTE_POINTER\n", encoding="utf-8")
            after = self._snapshot(root, state)
        finally:
            td.cleanup()
        self.assertNotEqual(before["digest"], after["digest"])

    def test_untracked_file_mutation_does_not_fake_frontier_change(self):
        td, root, state = self._root()
        try:
            before = self._snapshot(root, state)
            unrelated = root / "scratch/untracked.txt"
            unrelated.parent.mkdir(parents=True, exist_ok=True)
            unrelated.write_text("noise\n", encoding="utf-8")
            after = self._snapshot(root, state)
        finally:
            td.cleanup()
        self.assertEqual(before["digest"], after["digest"])

    def test_both_new_mutable_frontiers_are_load_bearing(self):
        self.assertIn(
            "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
            closure.LOAD_BEARING_PATHS,
        )
        self.assertIn(
            "canonical/governance/CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json",
            closure.LOAD_BEARING_PATHS,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

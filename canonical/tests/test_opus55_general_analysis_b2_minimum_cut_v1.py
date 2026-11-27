from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.verify_opus55_general_analysis_b2_minimum_cut_v1 import (
    BASIS,
    CANDIDATE,
    ENVELOPE,
    verify,
)


ROOT = Path(__file__).resolve().parents[2]


def make_tree() -> Path:
    tmp = Path(tempfile.mkdtemp())
    for rel in (CANDIDATE, ENVELOPE, BASIS):
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    return tmp


def mutate(root: Path, rel: str, fn) -> None:
    p = root / rel
    obj = json.loads(p.read_text(encoding="utf-8"))
    fn(obj)
    p.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


class GeneralAnalysisB2MinimumCutTests(unittest.TestCase):
    def test_live_candidate_passes(self):
        out = verify(ROOT)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["maximum_new_open_quality_atom_after_ceiling_reuse"], 1)

    def test_credit_leak_fails(self):
        root = make_tree()
        self.addCleanup(lambda: shutil.rmtree(root))
        mutate(root, CANDIDATE, lambda x: x["accounting"].__setitem__("acceptance_credit_delta", 1))
        with self.assertRaisesRegex(Exception, "CREDIT_OR_SPEND_LEAK"):
            verify(root)

    def test_ceiling_cell_comparator_leak_fails(self):
        root = make_tree()
        self.addCleanup(lambda: shutil.rmtree(root))
        def f(x):
            x["breakthrough_partition"]["cells"][0]["new_target_comparator_required_if_ceiling_proved"] = True
        mutate(root, CANDIDATE, f)
        with self.assertRaisesRegex(Exception, "B2A_COMPARATOR_LEAK"):
            verify(root)

    def test_open_quality_atom_deletion_fails(self):
        root = make_tree()
        self.addCleanup(lambda: shutil.rmtree(root))
        def f(x):
            x["breakthrough_partition"]["cells"][1]["minimum_new_acceptance_obligation_if_no_stronger_proof_exists"] = "NONE"
        mutate(root, CANDIDATE, f)
        with self.assertRaisesRegex(Exception, "B2B_ATOM"):
            verify(root)

    def test_false_finality_fails(self):
        root = make_tree()
        self.addCleanup(lambda: shutil.rmtree(root))
        mutate(root, CANDIDATE, lambda x: x["terminal_effect"].__setitem__("literal_terminal", True))
        with self.assertRaisesRegex(Exception, "FALSE_FINALITY"):
            verify(root)

    def test_target_wording_drift_fails_closed(self):
        root = make_tree()
        self.addCleanup(lambda: shutil.rmtree(root))
        mutate(root, ENVELOPE, lambda x: None)
        # Re-serialization alone changes the content-addressed authority.
        with self.assertRaisesRegex(Exception, "BOUND_BLOB_DRIFT"):
            verify(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)

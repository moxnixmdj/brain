from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import r2_regcap_contextual_fact_direct_adequacy_v1 as d


def goal(source="canonical/tmp/source.txt", output="canonical/tmp/facts.json"):
    return (
        "Extract verified regulatory-capital contextual facts from "
        + source
        + " and save them to "
        + output
        + "."
    )


class Tests(unittest.TestCase):
    def write_source(self, root: Path, text: str):
        p = root / "canonical/tmp/source.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def test_ccob_property_context_closes_without_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write_source(
                root,
                "a 2.5% buffer comprised of Common Equity Tier 1 (CET1) "
                "above the regulatory minimum capital requirement",
            )
            out = d.run({"task_id": "x", "goal": goal()}, repo_root=root)
            self.assertTrue(out["pass"], out)
            self.assertTrue(out["direct_adequacy_authority"])
            self.assertFalse(out["terminal_authority"])
            saved = json.loads((root / "canonical/tmp/facts.json").read_text())
            self.assertEqual(
                set(saved["proved_atom_ids"]),
                {
                    "AMOUNT::2.5_PERCENT",
                    "COMPOSITION::CET1",
                    "POSITION::ABOVE_REGULATORY_MINIMUM",
                },
            )
            self.assertFalse(saved["concept_identity_claimed"])
            self.assertFalse(saved["reverse_property_to_concept_classification_authorized"])

    def test_mixed_contexts_are_completely_rederived(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write_source(
                root,
                "A 2.5% CET1 buffer above the regulatory minimum. "
                "The cushion is released when system-wide risk dissipates. "
                "A failing G-SIB has sufficient loss-absorbing and "
                "recapitalisation capacity available in resolution.",
            )
            out = d.run({"task_id": "x", "goal": goal()}, repo_root=root)
            self.assertTrue(out["pass"], out)
            self.assertEqual(len(out["matched_context_kinds"]), 3)
            self.assertIn("SCOPE::G_SIB", out["proved_atom_ids"])
            self.assertIn("RELEASE::SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES", out["proved_atom_ids"])

    def test_unrecognized_source_fails_closed_as_open_and_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write_source(root, "A vague capital cushion with no bounded semantics.")
            old = root / "canonical/tmp/facts.json"
            old.write_text('{"old": true}\n', encoding="utf-8")
            before = old.read_bytes()
            out = d.run({"task_id": "x", "goal": goal()}, repo_root=root)
            self.assertFalse(out["pass"], out)
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(old.read_bytes(), before)

    def test_independent_disagreement_rolls_back(self):
        def bad(source_text, *, source_id, source_path, candidate):
            del source_text, source_id, source_path, candidate
            return {
                "pass": False,
                "producer_independent": True,
                "semantic_acceptance_complete": False,
            }

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write_source(
                root,
                "the cushion is released when system-wide risk crystallises or dissipates",
            )
            out = d.run(
                {"task_id": "x", "goal": goal()},
                repo_root=root,
                independent_provider=bad,
            )
            self.assertFalse(out["pass"])
            self.assertTrue(out["rollback_complete"])
            self.assertFalse((root / "canonical/tmp/facts.json").exists())

    def test_nonmatching_goal_is_not_applicable(self):
        out = d.preflight({"task_id": "x", "goal": "Explain regulatory capital."})
        self.assertFalse(out["matched"])
        self.assertEqual(out["status"], "NOT_APPLICABLE")

    def test_output_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write_source(
                root,
                "a 2.5% CET1 buffer above the regulatory minimum",
            )
            g = (
                "Extract verified regulatory-capital contextual facts from "
                "canonical/tmp/source.txt and save them to canonical/../escape.json."
            )
            out = d.preflight({"task_id": "x", "goal": g}, repo_root=root)
            self.assertTrue(out["matched"])
            self.assertEqual(out["status"], "FAIL_CLOSED")
            self.assertIn("PATH_INVALID", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

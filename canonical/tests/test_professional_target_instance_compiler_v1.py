from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_target_instance_compiler_v1 as compiler


ROOT = Path(__file__).resolve().parents[2]


def target() -> dict:
    return {
        "schema": compiler.TARGET_SCHEMA,
        "source_id": "test://professional-target",
        "raw_task_text": (
            "Prepare an evidence-grounded executive brief for the audit committee. "
            "Do not invent facts. Preserve uncertainty and compare the two options."
        ),
        "objective": "Produce the strongest evidence-grounded executive brief.",
        "audience": "Audit committee",
        "source_evidence": ["evidence://packet/v1"],
        "artifact_type": "EXECUTIVE_BRIEF",
        "hard_constraints": [
            "NO_UNSUPPORTED_FACTS",
            "PRESERVE_MATERIAL_UNCERTAINTY",
        ],
        "plausible_interpretations": [
            "COMPARE_TWO_OPTIONS_AND_RECOMMEND_ONLY_IF_EVIDENCE_JUSTIFIES_A_WINNER",
        ],
        "target_construct": "Decision-useful professional quality under evidence constraints",
        "claim_scope": "Only claims supported by the supplied evidence packet",
        "current_draft_render": "NONE__NEW_ARTIFACT",
    }


class ProfessionalTargetInstanceCompilerV1Tests(unittest.TestCase):
    def test_exact_explicit_target_binds_all_r1_fields_and_raw_source(self):
        out = compiler.compile_target(target())
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["r1_target_step_verified"])
        self.assertTrue(out["raw_task_nonwhitespace_coverage_complete"])
        self.assertEqual(
            set(out["field_sha256"]),
            {
                "objective",
                "audience",
                "source_evidence",
                "artifact_type",
                "hard_constraints",
                "plausible_interpretations",
                "target_construct",
                "claim_scope",
                "current_draft_render",
            },
        )
        self.assertTrue(out["canonical_target_semantic_receipt"]["pass"])
        self.assertTrue(out["canonical_target_structural_receipt"]["pass"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_plausible_interpretations_must_be_explicit_and_nonempty(self):
        t = target()
        t["plausible_interpretations"] = []
        out = compiler.compile_target(t)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "TARGET_LIST_FIELD_INVALID:plausible_interpretations",
        )

    def test_multiple_plausible_interpretations_remain_open(self):
        t = target()
        t["plausible_interpretations"] = [
            "INTERPRETATION_A",
            "INTERPRETATION_B",
        ]
        out = compiler.compile_target(t)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "TARGET_INTERPRETATION_NOT_SINGLETON")
        self.assertTrue(out["ambiguity_resolution_required"])

    def test_unmodeled_target_field_fails_closed(self):
        t = target()
        t["secret_success_hint"] = "accept"
        out = compiler.compile_target(t)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "UNMODELED_TARGET_INSTANCE_FIELDS")
        self.assertEqual(out["unmodeled_fields"], ["secret_success_hint"])

    def test_raw_task_is_not_replaced_by_structured_fields(self):
        t = target()
        t["raw_task_text"] = "... !!! ???\nDo not omit this line."
        out = compiler.compile_target(t)
        self.assertTrue(out["pass"], out)
        raw = out["raw_task_contract"]
        self.assertTrue(raw["nonwhitespace_source_coverage_complete"])
        reconstructed = "".join(
            row["text"] for row in raw["acceptance_contract"]["obligations"]
        )
        self.assertIn("...", reconstructed)
        self.assertIn("!!!", reconstructed)
        self.assertIn("???", reconstructed)
        self.assertIn("Do not omit this line.", reconstructed)

    def test_canonical_professional_behavior_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / "canonical" / "governance"
            gov.mkdir(parents=True)
            registry = json.loads(
                (ROOT / compiler.REGISTRY_PATH).read_text(encoding="utf-8")
            )
            mutated = deepcopy(registry)
            row = next(
                x for x in mutated["active_contracted_residuals"]
                if x.get("behavior_id") == compiler.BEHAVIOR_ID
            )
            row["scope"] += " DRIFT"
            (root / compiler.REGISTRY_PATH).write_text(
                json.dumps(mutated),
                encoding="utf-8",
            )
            (root / compiler.CONTRACT_SCHEMA_PATH).write_text(
                (ROOT / compiler.CONTRACT_SCHEMA_PATH).read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            out = compiler.compile_target(target(), repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("CANONICAL_PROFESSIONAL_BEHAVIOR_DRIFT", out["reason"])

    def test_output_never_claims_arbitrary_language_extraction_complete(self):
        out = compiler.compile_target(target())
        self.assertTrue(out["pass"], out)
        self.assertIn(
            "NO_CLAIM_STRUCTURED_TARGET_FIELDS_WERE_INFERRED_COMPLETELY_FROM_ARBITRARY_LANGUAGE",
            out["hard_nonclaims"],
        )
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

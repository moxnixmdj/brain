from __future__ import annotations

import json
import unittest

from canonical.runtime import general_adequate_decision_controller_v1 as controller
from canonical.runtime.r2_raw_source_proof_material_adapter_v1 import KIND
from canonical.runtime.selected_semantic_truth_certificate_v1 import evaluate


POLICY = (
    "Total exposure means exposure_amount. "
    "Apply Rule A unless Total exposure is at least 125.50."
)


def facts(value: str) -> str:
    return json.dumps(
        {
            "schema_id": "FINANCE_TYPED_CONTEXT_V1",
            "fields": {
                "exposure_amount": {
                    "type": "DECIMAL_STRING",
                    "value": value,
                }
            },
        },
        separators=(",", ":"),
    )


def working() -> dict:
    return {
        "bound_relevance_cegar_loop": {
            "truth_payloads_by_predicate_id": {},
        }
    }


class R2SourceProofMaterialIntegrationV1Tests(unittest.TestCase):
    def material(self, value: str = "130.00") -> dict:
        return {
            "kind": KIND,
            "source_text": POLICY,
            "source_id": "policy",
            "fact_source": facts(value),
            "fact_source_id": "case-facts",
        }

    def canonical_id(self) -> str:
        w = working()
        out = controller._ingest_information_provider_material(
            w, "temporary-alias", self.material()
        )
        self.assertTrue(out["pass"], out)
        rows = w["bound_relevance_cegar_loop"]["truth_payloads_by_predicate_id"][
            "temporary-alias"
        ]
        passing = [evaluate(row) for row in rows]
        passing = [row for row in passing if row.get("pass") is True]
        self.assertEqual(len(passing), 1)
        return passing[0]["predicate_id"]

    def test_raw_material_creates_two_checker_candidates_and_no_provider_truth(self):
        predicate_id = self.canonical_id()
        w = working()
        out = controller._ingest_information_provider_material(
            w, predicate_id, self.material("130.00")
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["candidate_count"], 2)
        self.assertFalse(out["provider_declared_truth"])
        rows = w["bound_relevance_cegar_loop"]["truth_payloads_by_predicate_id"][
            predicate_id
        ]
        self.assertEqual(len(rows), 2)
        checked = [evaluate(row) for row in rows]
        passing = [row for row in checked if row.get("pass") is True]
        self.assertEqual(len(passing), 1)
        self.assertEqual(passing[0]["predicate_id"], predicate_id)
        self.assertEqual(passing[0]["predicate_truth"], "TRUE")

    def test_provider_cannot_smuggle_truth_into_raw_material(self):
        w = working()
        material = self.material()
        material["condition_holds"] = True
        out = controller._ingest_information_provider_material(
            w, "x", material
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "SOURCE_PROOF_MATERIAL_REJECTED")
        self.assertEqual(
            w["bound_relevance_cegar_loop"]["truth_payloads_by_predicate_id"],
            {},
        )

    def test_existing_truth_payload_path_is_preserved(self):
        w = working()
        legacy = {
            "predicate_id": "x",
            "target_claim_id": "legacy",
            "source_text": "legacy",
        }
        out = controller._ingest_information_provider_material(w, "x", legacy)
        self.assertTrue(out["pass"])
        self.assertEqual(
            out["status"],
            "EXISTING_TRUTH_PAYLOAD_APPENDED_FOR_CHECKER",
        )
        self.assertEqual(
            w["bound_relevance_cegar_loop"]["truth_payloads_by_predicate_id"]["x"],
            legacy,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

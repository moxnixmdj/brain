from __future__ import annotations

import json
import unittest

from canonical.runtime.r2_raw_source_proof_material_adapter_v1 import (
    KIND,
    adapt,
)
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


class R2RawSourceProofMaterialAdapterV1Tests(unittest.TestCase):
    def material(self, value: str = "130.00"):
        return {
            "kind": KIND,
            "source_text": POLICY,
            "source_id": "policy",
            "fact_source": facts(value),
            "fact_source_id": "case-facts",
        }

    def canonical_predicate_id(self) -> str:
        boot = adapt("opaque-request-label", self.material())
        checked = [evaluate(x) for x in boot["truth_payload_candidates"]]
        passing = [x for x in checked if x.get("pass") is True]
        self.assertEqual(len(passing), 1)
        return passing[0]["predicate_id"]

    def test_provider_never_declares_truth_and_checker_selects_one_boolean(self):
        predicate_id = self.canonical_predicate_id()
        out = adapt(predicate_id, self.material("130.00"))
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["provider_declares_truth"])
        checked = [evaluate(x) for x in out["truth_payload_candidates"]]
        passing = [x for x in checked if x.get("pass") is True]
        self.assertEqual(len(passing), 1)
        self.assertEqual(passing[0]["predicate_id"], predicate_id)
        self.assertEqual(passing[0]["predicate_truth"], "TRUE")

    def test_false_case_uses_same_predicate_identity(self):
        predicate_id = self.canonical_predicate_id()
        out = adapt(predicate_id, self.material("100.00"))
        passing = [
            x for x in (evaluate(p) for p in out["truth_payload_candidates"])
            if x.get("pass") is True
        ]
        self.assertEqual(len(passing), 1)
        self.assertEqual(passing[0]["predicate_id"], predicate_id)
        self.assertEqual(passing[0]["predicate_truth"], "FALSE")

    def test_wrong_selected_predicate_cannot_inherit_source_truth(self):
        out = adapt("forged-selected-predicate", self.material("130.00"))
        checked = [evaluate(x) for x in out["truth_payload_candidates"]]
        self.assertEqual(len([x for x in checked if x.get("pass") is True]), 1)
        passing = next(x for x in checked if x.get("pass") is True)
        self.assertNotEqual(passing["predicate_id"], "forged-selected-predicate")
        self.assertFalse(passing["requested_predicate_id_authority"])

    def test_extra_material_fields_fail_closed(self):
        material = self.material()
        material["condition_holds"] = True
        out = adapt("x", material)
        self.assertFalse(out["pass"])
        self.assertIn("UNMODELED_SOURCE_PROOF_MATERIAL_FIELDS", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

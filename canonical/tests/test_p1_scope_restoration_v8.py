from __future__ import annotations

import copy
import unittest

from canonical.runtime import p1_scope_restoration_v8 as r


class Tests(unittest.TestCase):
    def test_live_restoration_passes(self):
        out = r.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["whole_p1_contract_restored"])
        self.assertTrue(out["p1_scope_quarantine_clearable"])
        self.assertEqual(out["contract_accounting"]["whole_scope_pass_count"], 12)
        self.assertEqual(out["behavioral_family_accounting"]["provisional_behavioral_pass_count"], 19)
        self.assertEqual(out["opus55_acceptance_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])

    def test_transport_failure_fails_closed(self):
        x = r.load(r.TRANSPORT)
        x["result"]["p1_failure_semantics_transport_pass"] = False
        out = r.evaluate(transport=x)
        self.assertFalse(out["pass"])
        self.assertIn("NEW_TRANSPORT_FAIL", out["errors"])

    def test_missing_transport_atom_fails_closed(self):
        x = r.load(r.TRANSPORT)
        x["result"]["transport_requirements_discharged"] = x["result"]["transport_requirements_discharged"][:-1]
        out = r.evaluate(transport=x)
        self.assertFalse(out["pass"])
        self.assertIn("TRANSPORT_REQUIREMENT_SET", out["errors"])

    def test_prior_residual_must_be_exact(self):
        x = r.load(r.V7_PROVENANCE)
        x["result"]["remaining_p1_information_residual"] = "SOMETHING_ELSE"
        out = r.evaluate(v7_provenance=x)
        self.assertFalse(out["pass"])
        self.assertIn("PRETRANSPORT_RESIDUAL_NOT_EXACT", out["errors"])

    def test_frozen_mutation_set_cannot_shrink(self):
        x = r.load(r.BINDING)
        x["evaluator"]["required_mutations"] = x["evaluator"]["required_mutations"][:-1]
        out = r.evaluate(binding=x)
        self.assertFalse(out["pass"])
        self.assertIn("FROZEN_MUTATION_SET", out["errors"])

    def test_family_mapping_drift_fails_closed(self):
        x = r.load(r.REGISTRY)
        fmap = x["family_to_residual_contracts"]
        fmap["ARTIFACT_CREATION"] = list(fmap["ARTIFACT_CREATION"]) + [r.BEHAVIOR]
        out = r.evaluate(registry=x)
        self.assertFalse(out["pass"])
        self.assertIn("REGISTRY_P1_FAMILY_MAPPING", out["errors"])

    def test_source_reduction_must_have_original_p1_pass(self):
        x = r.load(r.POSTWAVE)
        x["contract_verdict"]["passed_contracts"] = [
            c for c in x["contract_verdict"]["passed_contracts"] if c != r.BEHAVIOR
        ]
        out = r.evaluate(postwave=x)
        self.assertFalse(out["pass"])
        self.assertIn("SOURCE_P1_PASS_ABSENT", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

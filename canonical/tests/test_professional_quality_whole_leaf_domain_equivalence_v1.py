from __future__ import annotations

from copy import deepcopy
import unittest

from canonical.runtime import professional_quality_whole_leaf_domain_equivalence_v1 as d


LEAF = "PQ::R10_ANALYSIS_DECISION::EXECUTION"
ROOT = "R10_ANALYSIS_DECISION"


def manifest():
    return {
        "roots": [{
            "root_id": ROOT,
            "contract": (
                "Freeze or robustify admissible analysis, aggregation, compensation, risk and "
                "normative policy; preserve Pareto/incomparability structure and model multiplicity "
                "rather than selecting convenient scalarizations after outcomes are known."
            ),
            "semantic_leaf": {
                "id": "PQ::R10_ANALYSIS_DECISION::SEMANTIC",
                "obligation": "PROVE_DOMAIN_SEMANTIC_SUFFICIENCY_FOR_R10_ANALYSIS_DECISION",
                "acceptance": "SEMANTIC_ACCEPTANCE",
            },
            "execution_leaf": {
                "id": LEAF,
                "obligation": "VERIFY_DOMAIN_EXECUTION_FOR_R10_ANALYSIS_DECISION",
                "acceptance": (
                    "RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_"
                    "ARTIFACT_OR_RUNTIME_BYTES_AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"
                ),
            },
        }]
    }


class WholeLeafDomainEquivalenceV1Tests(unittest.TestCase):
    def scope(self):
        return d.build_claim_scope(
            manifest(), LEAF, epoch="2026-10-10T18:00:00+02:00"
        )

    def test_exact_universal_scope_passes_without_property_credit(self):
        out = d.evaluate(manifest(), self.scope())
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["whole_leaf_domain_equivalence_proved"])
        self.assertFalse(out["leaf_property_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_filter_narrowing_fails(self):
        cs = self.scope()
        cs["scope_definition"]["domain_definition"]["filters"] = ["ONLY_EASY_CASES"]
        out = d.evaluate(manifest(), cs)
        self.assertEqual(out["reason"], "WHOLE_LEAF_DOMAIN_NOT_EXACT")

    def test_exclusion_narrowing_fails(self):
        cs = self.scope()
        cs["scope_definition"]["domain_definition"]["exclusions"] = ["ADVERSARIAL_CASES"]
        out = d.evaluate(manifest(), cs)
        self.assertEqual(out["reason"], "WHOLE_LEAF_DOMAIN_NOT_EXACT")

    def test_acceptance_drift_fails(self):
        cs = self.scope()
        cs["leaf_acceptance"] = "WEAKER_ACCEPTANCE"
        out = d.evaluate(manifest(), cs)
        self.assertEqual(out["reason"], "CLAIM_SCOPE_BINDING_DRIFT:leaf_acceptance")

    def test_subject_drift_fails(self):
        cs = self.scope()
        cs["subject_sha256"] = "0" * 64
        out = d.evaluate(manifest(), cs)
        self.assertEqual(out["reason"], "CLAIM_SCOPE_BINDING_DRIFT:subject_sha256")

    def test_claim_content_address_tamper_fails(self):
        cs = self.scope()
        cs["claim"]["claim_id"] = "0" * 64
        out = d.evaluate(manifest(), cs)
        self.assertEqual(out["reason"], "CLAIM_CONTENT_ADDRESS_MISMATCH")

    def test_manifest_contract_change_invalidates_prior_scope(self):
        cs = self.scope()
        changed = deepcopy(manifest())
        changed["roots"][0]["contract"] += " CHANGED"
        out = d.evaluate(changed, cs)
        self.assertEqual(out["reason"], "WHOLE_LEAF_DOMAIN_NOT_EXACT")

    def test_semantic_and_execution_leaf_domains_are_distinct(self):
        sem = d.build_claim_scope(
            manifest(),
            "PQ::R10_ANALYSIS_DECISION::SEMANTIC",
            epoch="2026-10-10T18:00:00+02:00",
        )
        out = d.evaluate(manifest(), sem)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["kind"], "SEMANTIC")
        self.assertNotEqual(
            sem["claim"]["claim_id"],
            self.scope()["claim"]["claim_id"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

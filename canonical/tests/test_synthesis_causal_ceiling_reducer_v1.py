import unittest

from canonical.runtime.synthesis_causal_ceiling_reducer_v1 import (
    REQUIRED_PREMISES,
    UNSUPPORTED_ZERO_PREMISES,
    reduce_ceiling,
)


def full_premises():
    return sorted(set().union(*REQUIRED_PREMISES.values(), UNSUPPORTED_ZERO_PREMISES))


def cert(premises=None, *, scope_complete=True, independent_or_objective=True):
    return {
        "scope_complete": scope_complete,
        "independent_or_objective": independent_or_objective,
        "premises": full_premises() if premises is None else list(premises),
    }


class SynthesisCausalCeilingReducerTests(unittest.TestCase):
    def test_full_cut_proves_all_five_components_and_quality_one(self):
        out = reduce_ceiling(cert())
        self.assertEqual(out["status"], "CEILING_PROVED")
        self.assertEqual(out["matched_quality"], 1.0)
        self.assertEqual(out["unsupported_material_claim_count"], 0)
        self.assertTrue(all(v == 1.0 for v in out["component_ceiling"].values()))
        self.assertEqual(out["missing_premises"], [])

    def test_each_required_premise_is_load_bearing(self):
        all_p = full_premises()
        for missing in all_p:
            with self.subTest(missing=missing):
                out = reduce_ceiling(cert([p for p in all_p if p != missing]))
                self.assertEqual(out["status"], "OPEN")
                self.assertIsNone(out["matched_quality"])
                self.assertIn(missing, out["missing_premises"])

    def test_scope_must_be_complete(self):
        out = reduce_ceiling(cert(scope_complete=False))
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "SCOPE_NOT_COMPLETE")

    def test_independent_or_objective_proof_is_required(self):
        out = reduce_ceiling(cert(independent_or_objective=False))
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "INDEPENDENCE_NOT_ESTABLISHED")

    def test_unknown_premise_fails_closed(self):
        out = reduce_ceiling(cert(full_premises() + ["MAGIC_QUALITY"]))
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(out["reason"].startswith("UNKNOWN_PREMISE:"))

    def test_duplicate_premise_fails_closed(self):
        all_p = full_premises()
        out = reduce_ceiling(cert(all_p + [all_p[0]]))
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "PREMISE_DUPLICATE")

    def test_self_asserted_extra_fields_fail_closed(self):
        payload = cert()
        payload["claimed_score"] = 1
        out = reduce_ceiling(payload)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "CERTIFICATE_FIELDS_MISMATCH")

    def test_non_mapping_fails_closed(self):
        out = reduce_ceiling(None)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "CERTIFICATE_NOT_MAPPING")


if __name__ == "__main__":
    unittest.main()

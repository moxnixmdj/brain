import inspect
import unittest

from canonical.runtime.evidence_audience_information_safe_candidate_v1 import solve
from canonical.runtime.evidence_audience_information_safe_proof_v1 import (
    generate_case, public_task, score_case,
)


class EvidenceAudienceInformationSafeTests(unittest.TestCase):
    def test_candidate_has_no_oracle_import(self):
        import canonical.runtime.evidence_audience_information_safe_candidate_v1 as m
        src=inspect.getsource(m)
        self.assertNotIn("evidence_audience_information_safe_proof_v1",src)
        self.assertNotIn("_oracle",src)

    def test_public_payload_has_no_gold_relation_labels(self):
        public=public_task(generate_case(11))
        self.assertNotIn("_oracle",public)
        for row in public["task"]["evidence"]:
            self.assertEqual(set(row),{"evidence_id","text"})

    def test_supported_population(self):
        for seed in range(11,31):
            case=generate_case(seed)
            out=solve(public_task(case))
            scored=score_case(case,out)
            self.assertTrue(scored["pass"],(seed,out,scored,case["_oracle"]))
            self.assertLessEqual(len(out["selected_evidence_ids"]),case["task"]["max_evidence_units"])

    def test_unsupported_claim_fails_closed_as_insufficient(self):
        for seed in (41,42,43):
            case=generate_case(seed,unsupported=True)
            out=solve(public_task(case))
            self.assertEqual(out["status"],"INSUFFICIENT")
            self.assertTrue(score_case(case,out)["pass"],(seed,out,case["_oracle"]))
            self.assertIn("C2",out["unsupported_claim_ids"])

    def test_irrelevant_selection_is_rejected(self):
        case=generate_case(51)
        out=solve(public_task(case))
        out=dict(out)
        out["selected_evidence_ids"]=list(out["selected_evidence_ids"])+[case["_oracle"]["irrelevant"][0]]
        self.assertFalse(score_case(case,out)["pass"])

    def test_material_conflict_omission_is_rejected(self):
        case=generate_case(61)
        out=solve(public_task(case))
        conflict=case["_oracle"]["conflict"]["C1"][0]
        out=dict(out)
        out["selected_evidence_ids"]=[x for x in out["selected_evidence_ids"] if x!=conflict]
        self.assertFalse(score_case(case,out)["pass"])


if __name__=="__main__":
    unittest.main(verbosity=2)

from __future__ import annotations

import unittest

from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as generator
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_candidate_v1 as candidate

BEACONS=[
    "QUALIFICATION-BEACON-A-0123456789",
    "QUALIFICATION-BEACON-B-fedcba987654",
    "QUALIFICATION-BEACON-C-314159265358",
]

class UnknownDomainDirectCandidateV1Tests(unittest.TestCase):
    def _run(self,beacon):
        packet=generator.generate_qualification_fixture_population(beacon=beacon)
        self.assertFalse(packet["production"])
        results=[]
        for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"]):
            out=harness.execute_case(candidate_step=candidate.step,case_visible=visible,hidden_record=hidden)
            results.append(out["scorer_result"])
        return scorer.aggregate(results)

    def test_three_independent_qualification_populations_pass(self):
        for beacon in BEACONS:
            with self.subTest(beacon=beacon):
                out=self._run(beacon)
                self.assertTrue(out["all_27_cases_pass"],out)
                self.assertTrue(out["transfer_leaf_pass"],out)
                self.assertTrue(out["abstention_leaf_pass"],out)

    def test_candidate_module_has_no_hidden_evaluator_import(self):
        names=set(candidate.__dict__)
        self.assertNotIn("generator",names)
        self.assertNotIn("scorer",names)
        self.assertNotIn("harness",names)

    def test_transfer_actions_report_zero_learned_boundary_on_conclusion(self):
        packet=generator.generate_qualification_fixture_population(beacon=BEACONS[0])
        transfer=next(v for v in packet["visible_cases"] if v["leaf_id"]==scorer.TRANSFER)
        transcript=[]
        for _ in range(3):
            action=candidate.step(transfer,tuple(transcript))
            if action["type"]=="CONCLUDE":
                self.assertEqual(action["persistent_learned_bytes"],0)
                self.assertEqual(action["external_frontier_model_calls"],0)
                self.assertEqual(action["external_learned_capability_calls"],0)
                return
            self.assertEqual(action["type"],"REQUEST_PROBE")
            pid=action["probe_id"]
            hidden=next(h for h in packet["hidden_records"] if h["case_id"]==transfer["case_id"])
            transcript.append({"step":len(transcript),"requested_probe_id":pid,"probe_result":hidden["allowed_probe_outcome_table"][pid]})
        self.fail("candidate did not conclude within frozen two-probe budget")

if __name__=="__main__":
    unittest.main(verbosity=2)

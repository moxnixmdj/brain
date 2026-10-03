from __future__ import annotations
import copy
import unittest

from canonical.runtime import p1_v7_scope_restoration_reducer_v1 as r

class Tests(unittest.TestCase):
    def test_live_candidate_is_lift_eligible_but_not_self_lifted(self):
        out=r.evaluate()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["quarantine_lift_eligible"])
        self.assertFalse(out["quarantine_lifted"])
        self.assertEqual(out["historical_terminal_p1_case_count"],60)
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["terminal_results_replayed"],0)
        self.assertEqual(out["acceptance_credit_delta"],0)

    def test_recovery_must_be_exact_192_of_192(self):
        x=copy.deepcopy(r._load(r.RECOVERY))
        x["verified"]["passes"]=191
        out=r.evaluate(recovery=x)
        self.assertFalse(out["pass"])
        self.assertIn("RECOVERY_NOT_192_OF_192",out["errors"])

    def test_recovery_must_discharge_all_three_transport_requirements(self):
        x=copy.deepcopy(r._load(r.RECOVERY))
        x["verified"]["transport_requirements_discharged"]=x["verified"]["transport_requirements_discharged"][:2]
        out=r.evaluate(recovery=x)
        self.assertFalse(out["pass"])
        self.assertIn("RECOVERY_TRANSPORT_REQUIREMENT_SET_DRIFT",out["errors"])

    def test_pre_recovery_residual_must_be_exact(self):
        x=copy.deepcopy(r._load(r.PROV))
        x["result"]["remaining_p1_information_residual"]="SOMETHING_ELSE"
        out=r.evaluate(prov=x)
        self.assertFalse(out["pass"])
        self.assertIn("PRE_RECOVERY_RESIDUAL_NOT_EXACT_FAILURE_SEMANTICS",out["errors"])

    def test_frozen_required_check_partition_cannot_shrink(self):
        x=copy.deepcopy(r._load(r.BINDING))
        x["evaluator"]["required_checks"]=x["evaluator"]["required_checks"][:-1]
        out=r.evaluate(binding=x)
        self.assertFalse(out["pass"])
        self.assertIn("REQUIRED_CHECK_PARTITION_NOT_EXACT",out["errors"])

    def test_prior_quarantine_must_be_bound(self):
        x=copy.deepcopy(r._load(r.QUARANTINE))
        x["independent_scope_mismatch_proved"]=False
        out=r.evaluate(quarantine=x)
        self.assertFalse(out["pass"])
        self.assertIn("PRIOR_QUARANTINE_NOT_INDEPENDENT",out["errors"])

    def test_executable_mutation_probes_all_pass(self):
        p=r._executable_mutation_probes()
        self.assertTrue(p["pass"],p)
        self.assertTrue(p["drop_provenance"]["pass"])
        self.assertTrue(p["unfalsifiable_diagnosis_rejected"])
        self.assertTrue(p["forced_unique_cause_rejected"])
        self.assertTrue(p["dropped_interaction_root_rejected"])
        self.assertTrue(p["downstream_delayed_root_rejected"])
        self.assertTrue(p["partial_repair_not_rescue"])

if __name__=="__main__":
    unittest.main(verbosity=2)

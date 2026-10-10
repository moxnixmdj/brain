from __future__ import annotations
from copy import deepcopy
import importlib
import json
from pathlib import Path
import unittest

from canonical.runtime.tb_science_conservative_censoring_reducer_v1 import adjudicate

ROOT=Path(__file__).resolve().parents[2]
PROFILE=json.loads((ROOT/"canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json").read_text())
CATALOG=json.loads((ROOT/"canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json").read_text())
SLOTS=[f"task-{i:02d}::trial-{j}" for i in range(70) for j in range(3)]

def guard_module():
    try:
        return importlib.import_module("canonical.runtime.professional_quality_r9_execution_guard_v1")
    except ModuleNotFoundError:
        raise AssertionError("R9_EXECUTION_GUARD_MISSING")

def rows(n,state):
    return [{"slot_id":SLOTS[i],"state":state} for i in range(n)]

class R9ExecutionGuardV1Tests(unittest.TestCase):
    def evaluate(self, **overrides):
        g=guard_module()
        args={
            "claim_id":g.CLAIM_ID,
            "censoring_verdict":adjudicate(SLOTS,rows(124,"SUCCESS")),
            "execution_profile":deepcopy(PROFILE),
            "defeater_catalog":deepcopy(CATALOG),
            "detected_defeater_ids":(),
            "near_miss_signals":{},
            "unmapped_material_false_certification_defeater":False,
            "dependency_fresh":True,
        }
        args.update(overrides)
        return g.evaluate(**args)

    def test_positive_pass_lock_is_only_certificate_eligible(self):
        out=self.evaluate()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["status"],"PASS__R9_EXECUTION_GUARD_ELIGIBLE_FOR_SCOPED_CERTIFICATE_VERIFICATION")
        self.assertTrue(out["ordinary_certificate_path_allowed"])
        self.assertFalse(out["whole_leaf_property_truth_proved"])
        self.assertFalse(out["quality_authority"])

    def test_all_known_r9_defeaters_block(self):
        g=guard_module()
        self.assertEqual(len(g.KNOWN_R9_DEFEATERS),13)
        for did in sorted(g.KNOWN_R9_DEFEATERS):
            with self.subTest(did=did):
                out=self.evaluate(detected_defeater_ids=[did])
                self.assertFalse(out["pass"],out)
                self.assertEqual(out["status"],"ABSTAIN_OR_ESCALATE__KNOWN_R9_DEFEATER_ACTIVE")
                self.assertFalse(out["ordinary_certificate_path_allowed"])

    def test_near_miss_signals_route_to_profile_escalations(self):
        g=guard_module()
        for signal,trigger in g.NEAR_MISS_TO_TRIGGER.items():
            with self.subTest(signal=signal):
                out=self.evaluate(near_miss_signals={signal:True})
                self.assertFalse(out["pass"],out)
                self.assertEqual(out["status"],"ESCALATE__R9_NEAR_MISS_TRIGGER")
                self.assertIn(trigger,out["active_escalation_triggers"])

    def test_final_123_successes_blocks_certificate_path(self):
        out=self.evaluate(censoring_verdict=adjudicate(SLOTS,rows(123,"SUCCESS"),final=True))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"ABSTAIN_OR_ESCALATE__R9_CENSORING_NOT_PASS_LOCK")

    def test_irreversible_failure_lock_blocks_certificate_path(self):
        out=self.evaluate(censoring_verdict=adjudicate(SLOTS,rows(87,"FAILURE")))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"ABSTAIN_OR_ESCALATE__R9_CENSORING_NOT_PASS_LOCK")

    def test_unknown_detected_defeater_escalates(self):
        out=self.evaluate(detected_defeater_ids=["C999_FRESH_TEMPORAL_ATTACK"])
        self.assertEqual(out["status"],"ESCALATE__UNMAPPED_DETECTED_DEFEATER")
        self.assertEqual(out["required_trigger"],"UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER")

    def test_unmapped_material_signal_escalates(self):
        out=self.evaluate(unmapped_material_false_certification_defeater=True)
        self.assertEqual(out["status"],"ESCALATE__UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER")

    def test_stale_dependency_blocks(self):
        out=self.evaluate(dependency_fresh=False)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"ABSTAIN_OR_ESCALATE__R9_STALE_DEPENDENCY")

    def test_catalog_drift_fails_closed(self):
        c=deepcopy(CATALOG)
        target=next(x for x in c["challenges"] if x["id"]=="C45_DEPLOYMENT_SUPPORT_SHIFT")
        target["root_ids"]=[x for x in target["root_ids"] if x!="R9_TEMPORAL_DEPLOYMENT"]
        out=self.evaluate(defeater_catalog=c)
        self.assertEqual(out["reason"],"R9_DEFEATER_CATALOG_DRIFT")

    def test_profile_trigger_drift_fails_closed(self):
        g=guard_module()
        p=deepcopy(PROFILE)
        needed=next(iter(g.NEAR_MISS_TO_TRIGGER.values()))
        p["escalation_triggers"]=[x for x in p["escalation_triggers"] if x!=needed]
        out=self.evaluate(execution_profile=p)
        self.assertEqual(out["reason"],"PROFILE_ESCALATION_TRIGGER_MISSING")

    def test_claim_substitution_fails_closed(self):
        out=self.evaluate(claim_id="0"*64)
        self.assertEqual(out["reason"],"CLAIM_ID_MISMATCH")

    def test_censoring_invariant_drift_fails_closed(self):
        bad=deepcopy(adjudicate(SLOTS,rows(124,"SUCCESS")))
        bad["unobserved_slots_count_as_zero_on_finalization"]=False
        out=self.evaluate(censoring_verdict=bad)
        self.assertEqual(out["reason"],"CENSORING_INVARIANT_DRIFT")

if __name__=="__main__":
    unittest.main(verbosity=2)

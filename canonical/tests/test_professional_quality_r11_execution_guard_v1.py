from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_r11_execution_guard_v1 as g

ROOT=Path(__file__).resolve().parents[2]
PROFILE=ROOT/"canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json"
CATALOG=ROOT/"canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json"

def profile():
    return json.loads(PROFILE.read_text(encoding="utf-8"))

def catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))

class R11ExecutionGuardV1Tests(unittest.TestCase):
    def test_clean_path_is_eligible_without_truth_inflation(self):
        out=g.evaluate(
            claim_id=g.CLAIM_ID,execution_profile=profile(),defeater_catalog=catalog()
        )
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["ordinary_certificate_path_allowed"])
        self.assertFalse(out["detection_completeness_proved"])
        self.assertFalse(out["r11_semantic_leaf_closed"])
        self.assertFalse(out["r11_root_closed"])
        self.assertFalse(out["terminal_authority"])

    def test_all_14_known_r11_defeaters_block(self):
        for did in sorted(g.KNOWN_R11_DEFEATERS):
            with self.subTest(did=did):
                out=g.evaluate(
                    claim_id=g.CLAIM_ID,execution_profile=profile(),
                    defeater_catalog=catalog(),detected_defeater_ids=(did,)
                )
                self.assertFalse(out["pass"],out)
                self.assertFalse(out["ordinary_certificate_path_allowed"])
                self.assertEqual(out["status"],"ABSTAIN_OR_ESCALATE__KNOWN_R11_DEFEATER_ACTIVE")
                self.assertIn(did,out["detected_known_r11_defeaters"])
                self.assertIn(out["required_trigger"],set(profile()["escalation_triggers"]))

    def test_unknown_detected_defeater_routes_generic(self):
        out=g.evaluate(
            claim_id=g.CLAIM_ID,execution_profile=profile(),defeater_catalog=catalog(),
            detected_defeater_ids=("C999_FRESH_SECURITY_ATTACK",)
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"ESCALATE__UNMAPPED_DETECTED_DEFEATER")
        self.assertEqual(out["required_trigger"],g.GENERIC_TRIGGER)

    def test_all_near_miss_classes_escalate(self):
        for signal,trigger in sorted(g.NEAR_MISS_TO_TRIGGER.items()):
            with self.subTest(signal=signal):
                out=g.evaluate(
                    claim_id=g.CLAIM_ID,execution_profile=profile(),defeater_catalog=catalog(),
                    near_miss_signals={signal:True}
                )
                self.assertFalse(out["pass"],out)
                self.assertEqual(out["status"],"ESCALATE__R11_NEAR_MISS_TRIGGER")
                self.assertIn(trigger,out["active_escalation_triggers"])

    def test_unmapped_material_signal_escalates(self):
        out=g.evaluate(
            claim_id=g.CLAIM_ID,execution_profile=profile(),defeater_catalog=catalog(),
            unmapped_material_false_certification_defeater=True
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "ESCALATE__UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER"
        )
        self.assertEqual(out["required_trigger"],g.GENERIC_TRIGGER)

    def test_catalog_loss_fails_closed(self):
        c=catalog()
        rows=c.get("defeaters") or c.get("attack_classes") or c.get("nodes") or c.get("challenges")
        target=next(x for x in rows if x.get("id")=="C53_PROMPT_INJECTION_JUDGE_CONTROL")
        field="root_ids" if isinstance(target.get("root_ids"),list) else "target_root_ids"
        target[field]=[x for x in target[field] if x!=g.ROOT_ID]
        out=g.evaluate(claim_id=g.CLAIM_ID,execution_profile=profile(),defeater_catalog=c)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R11_DEFEATER_CATALOG_DRIFT")

    def test_missing_adaptive_profile_trigger_fails_closed(self):
        p=profile()
        p["escalation_triggers"]=[x for x in p["escalation_triggers"] if x!=g.ADAPTIVE_TRIGGER]
        out=g.evaluate(claim_id=g.CLAIM_ID,execution_profile=p,defeater_catalog=catalog())
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R11_REQUIRED_PROFILE_TRIGGER_MISSING")

    def test_missing_generic_profile_trigger_fails_closed(self):
        p=profile()
        p["escalation_triggers"]=[x for x in p["escalation_triggers"] if x!=g.GENERIC_TRIGGER]
        out=g.evaluate(claim_id=g.CLAIM_ID,execution_profile=p,defeater_catalog=catalog())
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R11_REQUIRED_PROFILE_TRIGGER_MISSING")

    def test_claim_substitution_fails_closed(self):
        out=g.evaluate(
            claim_id="0"*64,execution_profile=profile(),defeater_catalog=catalog()
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"CLAIM_ID_MISMATCH")

if __name__=="__main__":
    unittest.main(verbosity=2)

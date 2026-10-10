from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_semantic_shared_blocker_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def docs():
    return (
        json.loads((ROOT/v.MANIFEST_PATH).read_text(encoding="utf-8")),
        json.loads((ROOT/v.CATALOG_PATH).read_text(encoding="utf-8")),
    )

class SemanticSharedBlockerV1Tests(unittest.TestCase):
    def test_real_current_manifest_and_catalog_classify_one_shared_blocker(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["semantic_leaf_count"],12)
        self.assertTrue(out["shared_acceptance_proved"])
        self.assertFalse(out["catalog_completeness_proved"])
        self.assertFalse(out["catalog_alone_can_authorize_semantic_property_truth"])
        self.assertFalse(out["new_primitive_required"])
        self.assertFalse(out["terminal_authority"])

    def test_one_semantic_acceptance_drift_breaks_shared_classification(self):
        m,c=docs()
        m["roots"][0]["semantic_leaf"]["acceptance"]="DIFFERENT"
        out=v.evaluate(m,c)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"SEMANTIC_ACCEPTANCE_NOT_SHARED")

    def test_catalog_cannot_drop_explicit_completeness_nonclaim(self):
        m,c=docs()
        c["hard_nonclaims"]=[x for x in c["hard_nonclaims"] if x!=v.COMPLETENESS_NONCLAIM]
        out=v.evaluate(m,c)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"CATALOG_COMPLETENESS_NONCLAIM_MISSING")

    def test_catalog_cannot_claim_closed_and_still_drive_blocker_receipt(self):
        m,c=docs()
        c["closure_state"]="CLOSED"
        out=v.evaluate(m,c)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"CATALOG_CLOSURE_STATE_NOT_OPEN")

    def test_every_root_must_have_at_least_one_catalog_challenge(self):
        m,c=docs()
        for row in c["challenges"]:
            row["root_ids"]=[x for x in row.get("root_ids",[]) if x!="R1_TARGET_SPECIFICATION"]
        out=v.evaluate(m,c)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"ROOT_WITHOUT_CATALOG_CHALLENGE")

if __name__=="__main__":
    unittest.main(verbosity=2)

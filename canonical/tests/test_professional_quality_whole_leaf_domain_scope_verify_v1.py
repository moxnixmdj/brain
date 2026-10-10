from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest
from canonical.runtime import professional_quality_whole_leaf_domain_scope_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]
GOV=ROOT/"canonical/governance"

def claim_paths():
    out=[]
    for p in sorted(GOV.glob("PROFESSIONAL_QUALITY_WHOLE_LEAF_CLAIM_SCOPE_PQ_*_20261010_V1.json")):
        try:d=json.loads(p.read_text(encoding="utf-8"))
        except Exception:continue
        if d.get("schema")==v.gate.CLAIM_SCOPE_SCHEMA:
            out.append(p)
    return out

class WholeLeafDomainScopeTests(unittest.TestCase):
    def test_all_24_frozen_claim_scopes_match_authoritative_leaf_domains(self):
        paths=claim_paths()
        self.assertEqual(len(paths),24,[p.name for p in paths])
        seen=set()
        for p in paths:
            out=v.verify_path(p)
            self.assertTrue(out["pass"],(p.name,out))
            self.assertTrue(out["whole_leaf_domain_equivalence_proved"])
            self.assertFalse(out["whole_leaf_scope_complete"])
            self.assertFalse(out["leaf_property_truth_authority"])
            self.assertFalse(out["quality_authority"])
            self.assertFalse(out["terminal_authority"])
            seen.add(out["leaf_id"])
        self.assertEqual(len(seen),24)

    def test_narrowed_domain_definition_fails_closed(self):
        p=claim_paths()[0];d=json.loads(p.read_text(encoding="utf-8"))
        d["scope_definition"]["domain_definition"]["membership_rule"]="ONLY_A_SUBSET"
        out=v.verify_document(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"SCOPE_DEFINITION_NOT_IDENTICAL_TO_AUTHORITATIVE_MANIFEST_LEAF_DOMAIN")

    def test_root_drift_fails_closed(self):
        p=claim_paths()[0];d=json.loads(p.read_text(encoding="utf-8"))
        d["root_id"]="R1_TARGET_SPECIFICATION"
        out=v.verify_document(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"LEAF_METADATA_DRIFT")

    def test_subject_drift_fails_closed(self):
        p=claim_paths()[0];d=json.loads(p.read_text(encoding="utf-8"))
        d["subject_sha256"]="0"*64
        out=v.verify_document(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"SUBJECT_DRIFT")

    def test_self_authority_fails_closed(self):
        p=claim_paths()[0];d=json.loads(p.read_text(encoding="utf-8"))
        d["whole_leaf_scope_complete"]=True
        out=v.verify_document(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"SELF_AUTHORITY_FORBIDDEN:whole_leaf_scope_complete")

if __name__=="__main__":
    unittest.main(verbosity=2)

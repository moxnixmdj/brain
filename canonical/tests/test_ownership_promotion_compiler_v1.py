from __future__ import annotations
import copy, unittest
from pathlib import Path
from canonical.runtime.ownership_promotion_compiler_v1 import audit_source, evaluate, load

ROOT=Path(__file__).resolve().parents[2]
BATCH=ROOT/"canonical/governance/OWNERSHIP_PROMOTION_BATCH_V1.json"

class TestOwnershipPromotionCompilerV1(unittest.TestCase):
    def test_live_batch_verifies_three_already_owned_families(self):
        out=evaluate(ROOT,load(BATCH))
        self.assertEqual(out["status"],"PASS")
        self.assertEqual(out["counts"],{"eligible":0,"already_owned_verified":3,"blocked":0})
        self.assertEqual(set(out["already_owned_verified_families"]),{
            "SUBAGENT_DELEGATION_AND_COORDINATION",
            "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
            "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
        })

    def test_hash_mutation_fails_closed_even_after_promotion(self):
        b=copy.deepcopy(load(BATCH))
        b["families"][0]["artifact"]["git_blob_sha"]="0"*40
        out=evaluate(ROOT,b)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        row=next(x for x in out["families"] if x["family"]=="SUBAGENT_DELEGATION_AND_COORDINATION")
        self.assertIn("OPERATIVE_ARTIFACT_HASH_MISMATCH",row["errors"])

    def test_missing_receipt_fails_closed(self):
        b=copy.deepcopy(load(BATCH))
        b["families"][2]["acceptance_receipts"].append("canonical/verification/DOES_NOT_EXIST.json")
        out=evaluate(ROOT,b)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        row=next(x for x in out["families"] if x["family"]=="TOOL_DISCOVERY_SELECTION_AND_LEARNING")
        self.assertTrue(any(x.startswith("RECEIPT_UNAVAILABLE:") for x in row["errors"]))

    def test_external_provider_import_fails_closed(self):
        self.assertTrue(audit_source("import requests\n"))
        self.assertTrue(audit_source("from openai import OpenAI\n"))
        self.assertEqual(audit_source("from __future__ import annotations\nimport math\n"),[])

    def test_stdlib_network_and_process_escapes_fail_closed(self):
        self.assertIn("FORBIDDEN_ESCAPE_IMPORT:socket",audit_source("import socket\n"))
        self.assertIn("FORBIDDEN_ESCAPE_IMPORT:subprocess",audit_source("import subprocess\n"))
        self.assertTrue(audit_source("from urllib import request\n"))

    def test_dynamic_escape_fails_closed(self):
        self.assertTrue(audit_source("exec('x=1')\n"))
        self.assertTrue(audit_source("__import__('requests')\n"))

    def test_binding_pointer_mutation_fails_closed(self):
        b=copy.deepcopy(load(BATCH))
        b["families"][1]["artifact"]["binding_pointer"]="exact_brain_bytes.not_real"
        out=evaluate(ROOT,b)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        row=next(x for x in out["families"] if x["family"]=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY")
        self.assertIn("ARTIFACT_BINDING_UNRESOLVED",row["errors"])

if __name__=="__main__":
    unittest.main()

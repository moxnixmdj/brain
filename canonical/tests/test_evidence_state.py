#!/usr/bin/env python3
import hashlib
import importlib.util
import pathlib
import sys
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
PATH=ROOT/"runtime"/"evidence_state.py"
spec=importlib.util.spec_from_file_location("evidence_state_test_target",PATH)
evidence=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=evidence
spec.loader.exec_module(evidence)


def h(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EvidenceStateTests(unittest.TestCase):
    revision="a"*40

    def designed(self):
        return {
            "schema":"PROJECT_BRAIN_EVIDENCE_RECEIPT_V1",
            "artifact_id":"artifact.test",
            "state":"DESIGNED",
        }

    def implemented(self,prev):
        return {
            "schema":"PROJECT_BRAIN_EVIDENCE_RECEIPT_V1",
            "artifact_id":"artifact.test",
            "state":"IMPLEMENTED",
            "revision_sha":self.revision,
            "previous_receipt_sha256":evidence.receipt_sha256(prev),
        }

    def executed(self,prev):
        return {
            "schema":"PROJECT_BRAIN_EVIDENCE_RECEIPT_V1",
            "artifact_id":"artifact.test",
            "state":"EXECUTED",
            "revision_sha":self.revision,
            "previous_receipt_sha256":evidence.receipt_sha256(prev),
            "execution":{
                "executor_id":"chatgpt-container",
                "platform":"linux",
                "command":"python -m unittest",
                "exit_code":0,
                "stdout_sha256":h("PASS"),
                "stderr_sha256":h(""),
                "incremental_spend_usd":0,
            },
        }

    def verified(self,prev):
        return {
            "schema":"PROJECT_BRAIN_EVIDENCE_RECEIPT_V1",
            "artifact_id":"artifact.test",
            "state":"VERIFIED",
            "revision_sha":self.revision,
            "previous_receipt_sha256":evidence.receipt_sha256(prev),
            "verification":{
                "verified":True,
                "verifier_id":"independent-test-contract",
                "executed_receipt_sha256":evidence.receipt_sha256(prev),
                "predicates":[True,True],
            },
        }

    def promoted(self,prev):
        return {
            "schema":"PROJECT_BRAIN_EVIDENCE_RECEIPT_V1",
            "artifact_id":"artifact.test",
            "state":"PROMOTED",
            "revision_sha":self.revision,
            "previous_receipt_sha256":evidence.receipt_sha256(prev),
            "promotion":{
                "verified_receipt_sha256":evidence.receipt_sha256(prev),
                "merge_commit_sha":"b"*40,
                "canonical_ref":"refs/heads/main",
            },
        }

    def test_full_state_chain_is_valid(self):
        d=self.designed(); i=self.implemented(d); x=self.executed(i); v=self.verified(x); p=self.promoted(v)
        previous=None
        for current in (d,i,x,v,p):
            evidence.validate_receipt(current,previous)
            previous=current

    def test_cannot_jump_implemented_to_verified(self):
        d=self.designed(); i=self.implemented(d)
        v=self.verified(i)
        with self.assertRaisesRegex(evidence.EvidenceError,"EPISTEMIC_STATE_JUMP_FORBIDDEN"):
            evidence.validate_receipt(v,i)

    def test_execution_requires_observed_output_hashes(self):
        d=self.designed(); i=self.implemented(d); x=self.executed(i)
        del x["execution"]["stdout_sha256"]
        with self.assertRaisesRegex(evidence.EvidenceError,"EXECUTION_STDOUT_HASH_INVALID"):
            evidence.validate_receipt(x,i)

    def test_nonzero_incremental_spend_is_rejected(self):
        d=self.designed(); i=self.implemented(d); x=self.executed(i)
        x["execution"]["incremental_spend_usd"]=0.01
        with self.assertRaisesRegex(evidence.EvidenceError,"EXECUTION_NONZERO_SPEND"):
            evidence.validate_receipt(x,i)

    def test_verified_requires_exact_executed_receipt(self):
        d=self.designed(); i=self.implemented(d); x=self.executed(i); v=self.verified(x)
        v["verification"]["executed_receipt_sha256"]="0"*64
        with self.assertRaisesRegex(evidence.EvidenceError,"VERIFIED_EXECUTION_RECEIPT_MISMATCH"):
            evidence.validate_receipt(v,x)

    def test_promotion_requires_exact_verified_receipt(self):
        d=self.designed(); i=self.implemented(d); x=self.executed(i); v=self.verified(x); p=self.promoted(v)
        p["promotion"]["verified_receipt_sha256"]="0"*64
        with self.assertRaisesRegex(evidence.EvidenceError,"PROMOTION_VERIFIED_RECEIPT_MISMATCH"):
            evidence.validate_receipt(p,v)

    def test_ledger_detects_chain_tampering(self):
        d=self.designed(); i=self.implemented(d)
        with tempfile.TemporaryDirectory() as td:
            path=pathlib.Path(td)/"ledger.jsonl"
            evidence.append_receipt(path,d)
            evidence.append_receipt(path,i)
            lines=path.read_text(encoding="utf-8").splitlines()
            lines[0]=lines[0].replace("artifact.test","artifact.changed")
            path.write_text("\n".join(lines)+"\n",encoding="utf-8")
            with self.assertRaises(evidence.EvidenceError):
                evidence.load_ledger(path)


if __name__=="__main__":
    unittest.main(verbosity=2)

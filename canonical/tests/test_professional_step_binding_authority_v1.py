from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_step_binding_authority_v1 as k

BEHAVIOR="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
SUBJECT_ID="SUBJECT-V7"
SUBJECT_SHA="a"*64
STEP="GENERATE_DIVERSE_CANDIDATE_BRANCHES_WITH_INCUMBENT_PRESERVATION"


def context():
    return k.run_context_digest(
        goal="Improve report",
        decision_payload={"context_id":"x"},
        artifact_paths=["a.docx"],
        hard_defect_profile_id="profile",
        detected_triggers=[],
    )


def write_pair(root:Path,*,producer="producer-a",verifier="verifier-b",ctx=None):
    gov=root/"canonical/governance"; ver=root/"canonical/verification"
    gov.mkdir(parents=True); ver.mkdir(parents=True)
    ctx=ctx or context()
    evidence_sha=sha256(b"evidence").hexdigest()
    receipt={
        "schema":k.RECEIPT_SCHEMA,
        "behavior_id":BEHAVIOR,
        "subject_id":SUBJECT_ID,
        "subject_sha256":SUBJECT_SHA,
        "step_id":STEP,
        "run_context_sha256":ctx,
        "result":"PASS",
        "evidence_sha256":evidence_sha,
        "producer_id":producer,
        "binding_proved":True,
    }
    rp=gov/"step.json"; rp.write_text(json.dumps(receipt,sort_keys=True),encoding="utf-8")
    rb=k.git_blob_sha(rp)
    verify={
        "schema":k.VERIFY_SCHEMA,
        "subject_git_blob_sha":rb,
        "behavior_id":BEHAVIOR,
        "subject_id":SUBJECT_ID,
        "subject_sha256":SUBJECT_SHA,
        "step_id":STEP,
        "run_context_sha256":ctx,
        "result":"PASS",
        "evidence_sha256":evidence_sha,
        "pass":True,
        "independent_verified":True,
        "semantic_preservation_verified":True,
        "evidence_scope_verified":True,
        "independent_verifier_id":verifier,
    }
    vp=ver/"step_verify.json"; vp.write_text(json.dumps(verify,sort_keys=True),encoding="utf-8")
    return {
        "receipt":{"path":"canonical/governance/step.json","git_blob_sha":rb},
        "verification":{"path":"canonical/verification/step_verify.json","git_blob_sha":k.git_blob_sha(vp)},
    },rp,vp


def auth(binding,root,ctx=None):
    return k.authenticate_step_binding(
        binding,
        behavior_id=BEHAVIOR,
        subject_id=SUBJECT_ID,
        subject_sha256=SUBJECT_SHA,
        step_id=STEP,
        run_context_sha256=ctx or context(),
        repo_root=root,
    )


class ProfessionalStepBindingAuthorityV1Tests(unittest.TestCase):
    def test_missing_binding_is_open_not_pass(self):
        with tempfile.TemporaryDirectory() as td:
            out=auth(None,Path(td))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"OPEN__PROFESSIONAL_STEP_BINDING_REQUIRED")

    def test_valid_binding_authenticates_without_quality_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); binding,_,_=write_pair(root)
            out=auth(binding,root)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["result"],"PASS")
        for field in ("semantic_truth_authority","execution_authority","quality_authority",
                      "acceptance_authority","promotion_authority","terminal_authority"):
            self.assertFalse(out[field])

    def test_receipt_blob_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); binding,rp,_=write_pair(root)
            doc=json.loads(rp.read_text()); doc["producer_id"]="tampered"
            rp.write_text(json.dumps(doc,sort_keys=True))
            out=auth(binding,root)
        self.assertEqual(out["status"],"FAIL_CLOSED__PROFESSIONAL_STEP_BINDING_INVALID")
        self.assertIn("BOUND_BLOB_DRIFT",out["reason"])

    def test_run_context_substitution_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); binding,_,_=write_pair(root)
            out=auth(binding,root,ctx="sha256:"+"0"*64)
        self.assertIn("STEP_BINDING_FIELD_MISMATCH:run_context_sha256",out["reason"])

    def test_same_producer_and_verifier_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); binding,_,_=write_pair(root,producer="same",verifier="same")
            out=auth(binding,root)
        self.assertIn("STEP_BINDING_PRODUCER_VERIFIER_NOT_INDEPENDENT",out["reason"])

    def test_verification_cannot_drop_semantic_preservation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); binding,_,vp=write_pair(root)
            doc=json.loads(vp.read_text()); doc["semantic_preservation_verified"]=False
            vp.write_text(json.dumps(doc,sort_keys=True))
            binding["verification"]["git_blob_sha"]=k.git_blob_sha(vp)
            out=auth(binding,root)
        self.assertIn("STEP_BINDING_VERIFY_PREMISE_UNPROVED:semantic_preservation_verified",out["reason"])

    def test_step_identity_substitution_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); binding,_,_=write_pair(root)
            out=k.authenticate_step_binding(
                binding,behavior_id=BEHAVIOR,subject_id=SUBJECT_ID,subject_sha256=SUBJECT_SHA,
                step_id="OTHER_STEP",run_context_sha256=context(),repo_root=root,
            )
        self.assertIn("STEP_BINDING_FIELD_MISMATCH:step_id",out["reason"])


if __name__=="__main__":
    unittest.main()

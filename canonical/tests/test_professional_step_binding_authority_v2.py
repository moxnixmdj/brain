from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_step_binding_authority_v1 as v1
from canonical.runtime import professional_step_binding_authority_v2 as v2

BEHAVIOR="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
SUBJECT_ID="SUBJECT-V8-CANDIDATE"
SUBJECT_SHA="a"*64
FINAL=v2.FINAL_STEP
OTHER="GENERATE_DIVERSE_CANDIDATE_BRANCHES_WITH_INCUMBENT_PRESERVATION"


def context():
    return v1.run_context_digest(
        goal="Improve report",
        decision_payload={"context_id":"x"},
        artifact_paths=["a.docx"],
        hard_defect_profile_id="profile",
        detected_triggers=[],
    )


def _write_json(path:Path,doc)->str:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(doc,sort_keys=True),encoding="utf-8")
    return v1.git_blob_sha(path)


def write_pair(root:Path,*,step_id:str,outcome:str|None):
    ctx=context()
    evidence_sha=sha256(b"evidence").hexdigest()
    receipt={
        "schema":v1.RECEIPT_SCHEMA,
        "behavior_id":BEHAVIOR,
        "subject_id":SUBJECT_ID,
        "subject_sha256":SUBJECT_SHA,
        "step_id":step_id,
        "run_context_sha256":ctx,
        "result":"PASS",
        "evidence_sha256":evidence_sha,
        "producer_id":"producer-a",
        "binding_proved":True,
    }
    if outcome is not None:
        receipt["decision_outcome"]=outcome
    rp=root/"canonical/governance/step.json"
    rb=_write_json(rp,receipt)
    verify={
        "schema":v1.VERIFY_SCHEMA,
        "subject_git_blob_sha":rb,
        "behavior_id":BEHAVIOR,
        "subject_id":SUBJECT_ID,
        "subject_sha256":SUBJECT_SHA,
        "step_id":step_id,
        "run_context_sha256":ctx,
        "result":"PASS",
        "evidence_sha256":evidence_sha,
        "pass":True,
        "independent_verified":True,
        "semantic_preservation_verified":True,
        "evidence_scope_verified":True,
        "independent_verifier_id":"verifier-b",
    }
    if outcome is not None:
        verify["decision_outcome"]=outcome
    vp=root/"canonical/verification/step_verify.json"
    vb=_write_json(vp,verify)
    return {
        "receipt":{"path":"canonical/governance/step.json","git_blob_sha":rb},
        "verification":{"path":"canonical/verification/step_verify.json","git_blob_sha":vb},
    },receipt,verify


def add_totality(root:Path,binding:dict,receipt:dict,*,complete=True,independent=True):
    target=v2.target_scope_id(
        run_context_sha256=receipt["run_context_sha256"],
        evidence_sha256=receipt["evidence_sha256"],
    )
    scope_cert={
        "id":"local-totality",
        "target_scope_id":target,
        "basis":"EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
        "verified":True,
        "independent":True,
        "scope_relation":"EXACT",
        "complete_target_case_set":bool(complete),
        "universe_identity_bound":True,
        "case_universe_digest":"b"*64,
    }
    cert={
        "schema":v2.TOTALITY_CERT_SCHEMA,
        "behavior_id":BEHAVIOR,
        "subject_id":SUBJECT_ID,
        "subject_sha256":SUBJECT_SHA,
        "step_id":FINAL,
        "run_context_sha256":receipt["run_context_sha256"],
        "evidence_sha256":receipt["evidence_sha256"],
        "decision_outcome":"POSITIVE_CERTIFICATE",
        "target_scope_id":target,
        "scope_certificate":scope_cert,
        "semantic_truth_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
    }
    cp=root/"canonical/governance/totality.json"
    cb=_write_json(cp,cert)
    verify={
        "schema":v2.TOTALITY_VERIFY_SCHEMA,
        "subject_git_blob_sha":cb,
        "behavior_id":BEHAVIOR,
        "subject_id":SUBJECT_ID,
        "subject_sha256":SUBJECT_SHA,
        "step_id":FINAL,
        "run_context_sha256":receipt["run_context_sha256"],
        "evidence_sha256":receipt["evidence_sha256"],
        "decision_outcome":"POSITIVE_CERTIFICATE",
        "target_scope_id":target,
        "scope_compiler_git_blob_sha":v2.SCOPE_COMPILER_BLOB,
        "scope_complete":bool(complete),
        "scope_basis":"EXACT_COMPLETE_TARGET_CASE_UNIVERSE" if complete else None,
        "pass":True,
        "independent_verified":bool(independent),
        "independent_verifier_id":"totality-verifier",
    }
    vp=root/"canonical/verification/totality_verify.json"
    vb=_write_json(vp,verify)
    binding["material_totality_certificate"]={"path":"canonical/governance/totality.json","git_blob_sha":cb}
    binding["material_totality_verification"]={"path":"canonical/verification/totality_verify.json","git_blob_sha":vb}
    return cert,verify,cp,vp


def auth(binding,root,step_id):
    return v2.authenticate_step_binding(
        binding,
        behavior_id=BEHAVIOR,
        subject_id=SUBJECT_ID,
        subject_sha256=SUBJECT_SHA,
        step_id=step_id,
        run_context_sha256=context(),
        repo_root=root,
    )


class ProfessionalStepBindingAuthorityV2Tests(unittest.TestCase):
    def test_v2_preserves_v1_run_context_helper_surface(self):
        self.assertEqual(v2.run_context_digest(
            goal="Improve report",
            decision_payload={"context_id":"x"},
            artifact_paths=["a.docx"],
            hard_defect_profile_id="profile",
            detected_triggers=[],
        ), context())
    def test_nonfinal_step_preserves_v1_semantics(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); binding,_,_=write_pair(root,step_id=OTHER,outcome=None)
            out=auth(binding,root,OTHER)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["v1_authenticated"])
        self.assertEqual(out["decision_outcome"],"NOT_APPLICABLE")

    def test_final_missing_outcome_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); binding,_,_=write_pair(root,step_id=FINAL,outcome=None)
            out=auth(binding,root,FINAL)
        self.assertFalse(out["pass"])
        self.assertIn("FINAL_STEP_DECISION_OUTCOME_INVALID",out["reason"])

    def test_abstain_passes_without_positive_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); binding,_,_=write_pair(root,step_id=FINAL,outcome="ABSTAIN")
            out=auth(binding,root,FINAL)
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["positive_certification_authorized"])
        self.assertFalse(out["material_totality_proved"])
        self.assertEqual(out["decision_outcome"],"ABSTAIN")

    def test_positive_without_totality_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); binding,_,_=write_pair(root,step_id=FINAL,outcome="POSITIVE_CERTIFICATE")
            out=auth(binding,root,FINAL)
        self.assertFalse(out["pass"])
        self.assertFalse(out["positive_certification_authorized"])

    def test_positive_with_complete_local_totality_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); binding,receipt,_=write_pair(root,step_id=FINAL,outcome="POSITIVE_CERTIFICATE")
            add_totality(root,binding,receipt)
            out=auth(binding,root,FINAL)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["positive_certification_authorized"])
        self.assertTrue(out["material_totality_proved"])
        self.assertEqual(out["material_totality_basis"],"EXACT_COMPLETE_TARGET_CASE_UNIVERSE")

    def test_incomplete_local_scope_cannot_authorize_positive(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); binding,receipt,_=write_pair(root,step_id=FINAL,outcome="POSITIVE_CERTIFICATE")
            add_totality(root,binding,receipt,complete=False)
            out=auth(binding,root,FINAL)
        self.assertFalse(out["pass"])
        self.assertIn("MATERIAL_TOTALITY_SCOPE_NOT_COMPLETE",out["reason"])

    def test_totality_verifier_must_be_independent(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); binding,receipt,_=write_pair(root,step_id=FINAL,outcome="POSITIVE_CERTIFICATE")
            add_totality(root,binding,receipt,independent=False)
            out=auth(binding,root,FINAL)
        self.assertFalse(out["pass"])
        self.assertIn("MATERIAL_TOTALITY_VERIFY_PREMISE_UNPROVED:independent_verified",out["reason"])

    def test_totality_scope_cannot_be_reused_across_run_context(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); binding,receipt,_=write_pair(root,step_id=FINAL,outcome="POSITIVE_CERTIFICATE")
            cert,verify,cp,vp=add_totality(root,binding,receipt)
            cert["run_context_sha256"]="sha256:"+"0"*64
            binding["material_totality_certificate"]["git_blob_sha"]=_write_json(cp,cert)
            verify["subject_git_blob_sha"]=binding["material_totality_certificate"]["git_blob_sha"]
            binding["material_totality_verification"]["git_blob_sha"]=_write_json(vp,verify)
            out=auth(binding,root,FINAL)
        self.assertFalse(out["pass"])
        self.assertIn("MATERIAL_TOTALITY_CERT_FIELD_MISMATCH:run_context_sha256",out["reason"])

    def test_totality_certificate_cannot_self_grant_quality_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); binding,receipt,_=write_pair(root,step_id=FINAL,outcome="POSITIVE_CERTIFICATE")
            cert,verify,cp,vp=add_totality(root,binding,receipt)
            cert["quality_authority"]=True
            binding["material_totality_certificate"]["git_blob_sha"]=_write_json(cp,cert)
            verify["subject_git_blob_sha"]=binding["material_totality_certificate"]["git_blob_sha"]
            binding["material_totality_verification"]["git_blob_sha"]=_write_json(vp,verify)
            out=auth(binding,root,FINAL)
        self.assertFalse(out["pass"])
        self.assertIn("MATERIAL_TOTALITY_CERT_AUTHORITY_OVERCLAIM:quality_authority",out["reason"])


if __name__=="__main__":
    unittest.main(verbosity=2)

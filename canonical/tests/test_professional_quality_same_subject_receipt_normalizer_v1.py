import unittest
from canonical.runtime import professional_quality_same_subject_composition_gate_v3 as g

RID="R10_ANALYSIS_DECISION"
KIND="DECLARED_SYSTEM"
SID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SHA="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
BLOB="a"*40

def err(root_id, v, blob=BLOB):
    return g._verification_receipt_error(
        root_id=root_id,verification=v,binding_blob=blob,
        subject_kind=KIND,subject_id=SID,subject_sha=SHA)

class ReceiptNormalizationTests(unittest.TestCase):
    def test_legacy_generic_passes(self):
        v={"schema":g.VERIFY_SCHEMA,"pass":True,"root_id":RID,
           "subject_binding_git_blob_sha":BLOB,"subject_kind":KIND,
           "subject_id":SID,"subject_sha256":SHA,
           "root_subject_binding_authority":True,
           "global_subject_identity_authority":False,"terminal_authority":False}
        self.assertIsNone(err(RID,v))

    def test_r1_nested_receipt_passes(self):
        v={"schema":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_R1_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1",
           "status":"PASS__X",
           "current_main_subject":{"binding":{"git_blob_sha":BLOB},
             "declared_system":{"subject_id":SID,"subject_sha256":SHA}},
           "replay":{"verifier_pass":True},
           "authority":{"root_subject_binding_authority":True,
             "global_subject_identity_authority":False,"terminal_authority":False}}
        self.assertIsNone(err("R1_TARGET_SPECIFICATION",v))

    def test_r2_nested_receipt_passes(self):
        v={"schema":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_R2_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1",
           "status":"PASS__X",
           "exact_subject":{"binding_git_blob_sha":BLOB,"subject_id":SID,"subject_sha256":SHA},
           "replay":{"verifier_pass":True},
           "authority":{"root_subject_binding_authority":True,"terminal_authority":False}}
        self.assertIsNone(err("R2_CANDIDATE_SEARCH",v))

    def test_top_level_root_receipt_passes(self):
        v={"schema":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1",
           "status":"PASS__X","root_id":RID,"exact_blobs":{"binding":BLOB},
           "replay":{"tests_run":5,"tests_passed":5,"tests_failed":0},
           "root_subject_binding_authority":True,"terminal_authority":False}
        self.assertIsNone(err(RID,v))

    def test_public_runner_receipt_passes(self):
        root="R11_ADAPTIVE_INTEGRITY_SECURITY"
        v={"schema":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_R11_V7_ROOT_SUBJECT_BINDING_PUBLIC_VERIFY_V1",
           "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__X",
           "subject":{"id":SID,"sha256":SHA},"binding":{"git_blob_sha":BLOB},
           "public_runner":{"conclusion":"success","exact_blob_binding_step":"success",
             "root_verifier_step":"success","adversarial_test_step":"success"},
           "root_subject_binding_authority":True,"terminal_authority":False}
        self.assertIsNone(err(root,v))

    def test_public_runner_failure_rejected(self):
        root="R11_ADAPTIVE_INTEGRITY_SECURITY"
        v={"schema":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_R11_V7_ROOT_SUBJECT_BINDING_PUBLIC_VERIFY_V1",
           "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__X",
           "subject":{"id":SID,"sha256":SHA},"binding":{"git_blob_sha":BLOB},
           "public_runner":{"conclusion":"failure","exact_blob_binding_step":"success",
             "root_verifier_step":"success","adversarial_test_step":"success"},
           "root_subject_binding_authority":True,"terminal_authority":False}
        self.assertEqual(err(root,v),"SUBJECT_BINDING_VERIFY_NOT_PASS")

    def test_binding_hash_mismatch_rejected(self):
        v={"schema":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1",
           "status":"PASS__X","root_id":RID,"exact_blobs":{"binding":"b"*40},
           "replay":{"tests_run":5,"tests_passed":5,"tests_failed":0},
           "root_subject_binding_authority":True,"terminal_authority":False}
        self.assertEqual(err(RID,v),"SUBJECT_BINDING_VERIFY_BLOB_MISMATCH")

    def test_terminal_self_authority_rejected(self):
        v={"schema":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1",
           "status":"PASS__X","root_id":RID,"exact_blobs":{"binding":BLOB},
           "replay":{"tests_run":5,"tests_passed":5,"tests_failed":0},
           "root_subject_binding_authority":True,"terminal_authority":True}
        self.assertEqual(err(RID,v),"SUBJECT_BINDING_VERIFY_TERMINAL_AUTHORITY_FORBIDDEN")

if __name__=="__main__": unittest.main(verbosity=2)

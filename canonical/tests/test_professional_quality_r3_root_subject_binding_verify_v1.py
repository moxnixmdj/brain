from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_r3_root_subject_binding_verify_v1 as v


ROOT = Path(__file__).resolve().parents[2]


def binding_doc():
    return json.loads((ROOT / v.BINDING_PATH).read_text(encoding="utf-8"))


def public_verify_doc():
    path = v.REFS["current_stack_public_verification"][0]
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class R3V7RootSubjectBindingTests(unittest.TestCase):
    def test_current_branch_exact_chain_passes(self):
        out = v.verify(repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["root_subject_binding_authority"])
        self.assertTrue(out["bounded_exact_realization_instance_proved"])
        self.assertFalse(out["global_r3_root_closed"])
        for field in (
            "semantic_truth_authority", "execution_authority", "quality_authority",
            "acceptance_authority", "promotion_authority", "terminal_authority",
        ):
            self.assertFalse(out[field], out)

    def test_candidate_cannot_self_grant_root_authority(self):
        d = binding_doc()
        d["root_subject_binding_authority"] = True
        self.assertEqual(
            v.validate_binding_document(d),
            "BINDING_SELF_AUTHORITY_FORBIDDEN:root_subject_binding_authority",
        )

    def test_global_r3_nonclaim_is_load_bearing(self):
        d = binding_doc()
        d["binding_scope"]["limitations"].remove("NO_GLOBAL_R3_ROOT_CLOSURE")
        self.assertEqual(v.validate_binding_document(d), "BINDING_LIMITATIONS_INSUFFICIENT")

    def test_evidence_identity_is_load_bearing(self):
        d = binding_doc()
        d["binding_scope"]["evidence_sha256"] = "0" * 64
        self.assertEqual(v.validate_binding_document(d), "BINDING_EVIDENCE_IDENTITY_INVALID")

    def test_public_replay_cannot_transport_predecessor_versions(self):
        d = public_verify_doc()
        d["replay"]["predecessor_exact_stack_transport_claimed"] = True
        self.assertEqual(v.validate_public_verification(d), "VERSION_TRANSPORT_FORBIDDEN")

    def test_public_job_identity_is_load_bearing(self):
        d = public_verify_doc()
        d["public_runner"]["job_id"] += 1
        self.assertEqual(v.validate_public_verification(d), "PUBLIC_RUN_IDENTITY_INVALID")

    def test_public_verification_cannot_self_grant_quality(self):
        d = public_verify_doc()
        d["authority"]["quality_authority"] = True
        self.assertEqual(v.validate_public_verification(d), "PUBLIC_VERIFY_AUTHORITY_OVERCLAIM")

    def test_public_head_identity_is_load_bearing(self):
        d = public_verify_doc()
        d["public_runner"]["head_sha"] = "0" * 40
        self.assertEqual(v.validate_public_verification(d), "PUBLIC_HEAD_IDENTITY_INVALID")


if __name__ == "__main__":
    unittest.main(verbosity=2)

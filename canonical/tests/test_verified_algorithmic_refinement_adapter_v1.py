from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime.verified_algorithmic_refinement_adapter_v1 import (
    ADEQUACY_SCHEMA,
    CERT_SCHEMA,
    PROFILE_ID,
    RECEIPT_SCHEMA,
    REQUIRED_ATOMS,
    REQUIRED_VERIFIED,
    SUBJECT_ID,
    THEOREM_SCHEMA,
    VERIFY_SCHEMA,
    git_blob_sha,
    verify_certificate_file,
)


def condition():
    return {
        "op": "AND",
        "args": [{"op": "ATOM", "id": x} for x in sorted(REQUIRED_ATOMS)],
    }


class VerifiedAlgorithmicRefinementAdapterTests(unittest.TestCase):
    def fixture(self, root: Path):
        gov=root/"canonical/governance"; ver=root/"canonical/verification"; run=root/"canonical/runtime"
        gov.mkdir(parents=True); ver.mkdir(parents=True); run.mkdir(parents=True)
        concrete=run/"solver.py"
        concrete.write_text("def solve(xs, checker):\n    return next(x for x in xs if checker(x))\n",encoding="utf-8")
        concrete_binding={"path":"canonical/runtime/solver.py","git_blob_sha":git_blob_sha(concrete)}
        theorem=gov/"theorem.json"
        theorem_obj={
          "schema":THEOREM_SCHEMA,"policy_id":SUBJECT_ID,"exact_policy":concrete_binding,
          "condition":condition(),"condition_sha256":"a"*64,
          "proof":{"conclusion":"conditional algorithmic theorem"},
          "adequacy":{"adequate_for_every_member":True,"constructive_liveness":True},
          "promotion_authority":False,"terminal_authority":False,
          "accounting":{"terminal_credit_delta":0},
        }
        theorem.write_text(json.dumps(theorem_obj)+"\n",encoding="utf-8")
        theorem_binding={"path":"canonical/governance/theorem.json","git_blob_sha":git_blob_sha(theorem)}
        adequacy=gov/"adequacy.json"
        adequacy_obj={
          "schema":ADEQUACY_SCHEMA,"policy_id":SUBJECT_ID,"adequacy_proved":True,
          "exact_policy":concrete_binding,"policy_condition_sha256":"a"*64,
          "exact_sources":{"theorem":theorem_binding},
          "adequacy_theorem":{"mode":"FORMAL_ALL_MEMBERS","constructive_liveness":True},
          "promotion_authority":False,"terminal_authority":False,
          "accounting":{"terminal_credit_delta":0},
        }
        adequacy.write_text(json.dumps(adequacy_obj)+"\n",encoding="utf-8")
        adequacy_binding={"path":"canonical/governance/adequacy.json","git_blob_sha":git_blob_sha(adequacy)}
        verification=ver/"verification.json"
        verification_obj={
          "schema":VERIFY_SCHEMA,"policy_id":SUBJECT_ID,"pass":True,
          "subject_git_blob_sha":adequacy_binding["git_blob_sha"],
          "evidence":{"exact_policy":concrete_binding,"theorem":theorem_binding},
          "independent_replay":{"py_compile_pass":True,"test_functions_run":8,
             "test_functions_passed":8,"exhaustive_boolean_patterns_checked":510},
          "symbolic_core":{"budget_reaches_witness":True,"first_true_is_correct":True,
             "valid_member_is_detected":True},
          "verified":sorted(REQUIRED_VERIFIED),
          "promotion_authority":False,"terminal_authority":False,
          "accounting":{"terminal_credit_delta":0},
        }
        verification.write_text(json.dumps(verification_obj)+"\n",encoding="utf-8")
        certificate=gov/"refinement.json"
        certificate_obj={
          "schema":CERT_SCHEMA,"profile_id":PROFILE_ID,"subject_id":SUBJECT_ID,
          "concrete_implementation":concrete_binding,
          "theorem":theorem_binding,
          "adequacy_certificate":adequacy_binding,
          "independent_verification":{"path":"canonical/verification/verification.json",
             "git_blob_sha":git_blob_sha(verification)},
          "terminal_credit_delta":0,
        }
        certificate.write_text(json.dumps(certificate_obj)+"\n",encoding="utf-8")
        return certificate, concrete, theorem, adequacy, verification

    def run_fixture(self, root, certificate):
        return verify_certificate_file(
            str(certificate.relative_to(root)).replace("\\","/"), repo_root=root
        )

    def test_valid_chain_mints_conditional_refinement(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cert,*_=self.fixture(root)
            out=self.run_fixture(root,cert)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["schema"],RECEIPT_SCHEMA)
            self.assertTrue(out["refinement_verified"])
            self.assertTrue(out["safety_refinement_verified"])
            self.assertTrue(out["liveness_refinement_verified"])
            self.assertFalse(out["condition_truth_created"])
            self.assertFalse(out["execution_authority"])
            self.assertEqual(out["terminal_credit_delta"],0)

    def test_concrete_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cert,concrete,*_=self.fixture(root)
            concrete.write_text("def solve(*a): return None\n",encoding="utf-8")
            self.assertEqual(self.run_fixture(root,cert)["reason"],"CONCRETE_BLOB_DRIFT")

    def test_theorem_condition_profile_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cert,_,theorem,*_=self.fixture(root)
            obj=json.loads(theorem.read_text()); obj["condition"]["args"].pop()
            theorem.write_text(json.dumps(obj)+"\n")
            c=json.loads(cert.read_text()); c["theorem"]["git_blob_sha"]=git_blob_sha(theorem)
            cert.write_text(json.dumps(c)+"\n")
            self.assertEqual(self.run_fixture(root,cert)["reason"],"THEOREM_CONDITION_PROFILE_MISMATCH")

    def test_adequacy_not_proved_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cert,_,_,adequacy,verification=self.fixture(root)
            obj=json.loads(adequacy.read_text()); obj["adequacy_proved"]=False
            adequacy.write_text(json.dumps(obj)+"\n")
            c=json.loads(cert.read_text()); c["adequacy_certificate"]["git_blob_sha"]=git_blob_sha(adequacy)
            cert.write_text(json.dumps(c)+"\n")
            v=json.loads(verification.read_text()); v["subject_git_blob_sha"]=git_blob_sha(adequacy)
            verification.write_text(json.dumps(v)+"\n")
            c=json.loads(cert.read_text()); c["independent_verification"]["git_blob_sha"]=git_blob_sha(verification)
            cert.write_text(json.dumps(c)+"\n")
            self.assertEqual(self.run_fixture(root,cert)["reason"],"ADEQUACY_NOT_PROVED")

    def test_independent_verification_must_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cert,_,_,_,verification=self.fixture(root)
            obj=json.loads(verification.read_text()); obj["pass"]=False
            verification.write_text(json.dumps(obj)+"\n")
            c=json.loads(cert.read_text()); c["independent_verification"]["git_blob_sha"]=git_blob_sha(verification)
            cert.write_text(json.dumps(c)+"\n")
            self.assertEqual(self.run_fixture(root,cert)["reason"],"INDEPENDENT_VERIFICATION_NOT_PASSING")

    def test_required_semantic_claim_missing_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cert,_,_,_,verification=self.fixture(root)
            obj=json.loads(verification.read_text()); obj["verified"].pop()
            verification.write_text(json.dumps(obj)+"\n")
            c=json.loads(cert.read_text()); c["independent_verification"]["git_blob_sha"]=git_blob_sha(verification)
            cert.write_text(json.dumps(c)+"\n")
            self.assertEqual(self.run_fixture(root,cert)["reason"],"REQUIRED_SEMANTIC_CLAIMS_NOT_INDEPENDENTLY_VERIFIED")

    def test_pattern_coverage_insufficient_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cert,_,_,_,verification=self.fixture(root)
            obj=json.loads(verification.read_text()); obj["independent_replay"]["exhaustive_boolean_patterns_checked"]=509
            verification.write_text(json.dumps(obj)+"\n")
            c=json.loads(cert.read_text()); c["independent_verification"]["git_blob_sha"]=git_blob_sha(verification)
            cert.write_text(json.dumps(c)+"\n")
            self.assertEqual(self.run_fixture(root,cert)["reason"],"INDEPENDENT_REPLAY_PATTERN_COVERAGE_INSUFFICIENT")

    def test_symbolic_core_missing_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cert,_,_,_,verification=self.fixture(root)
            obj=json.loads(verification.read_text()); obj["symbolic_core"]["first_true_is_correct"]=False
            verification.write_text(json.dumps(obj)+"\n")
            c=json.loads(cert.read_text()); c["independent_verification"]["git_blob_sha"]=git_blob_sha(verification)
            cert.write_text(json.dumps(c)+"\n")
            self.assertEqual(self.run_fixture(root,cert)["reason"],"SYMBOLIC_CORE_UNPROVED")

    def test_nonzero_terminal_credit_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cert,*_=self.fixture(root)
            obj=json.loads(cert.read_text()); obj["terminal_credit_delta"]=1
            cert.write_text(json.dumps(obj)+"\n")
            self.assertEqual(self.run_fixture(root,cert)["reason"],"NONZERO_TERMINAL_CREDIT_FORBIDDEN")


if __name__=="__main__":
    unittest.main(verbosity=2)

import hashlib
import json
import pathlib
import tempfile
import unittest

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.escape_common_policy_top_residual_v1 import evaluate

SCOPE="scope://opus55/observable-trace"


def canon(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)


def condition_sha(condition):
    return hashlib.sha256(canon(condition).encode()).hexdigest()


def write_json(root, rel, value):
    p=root/rel
    p.parent.mkdir(parents=True,exist_ok=True)
    raw=canon(value).encode()
    p.write_bytes(raw)
    return git_blob_id(raw,object_format="sha1")


def build(root, condition=None, *, adequacy_overrides=None, verify_overrides=None, spec_overrides=None):
    condition=condition or {"op":"TRUE"}
    policy_id="P"
    adequacy={
        "schema":"PROJECT_BRAIN_POLICY_ADEQUACY_CERTIFICATE_V1",
        "policy_id":policy_id,
        "policy_condition_sha256":condition_sha(condition),
        "adequacy_proved":True,
        "brain_owned":True,
        "load_bearing_constraints_preserved":True,
    }
    if adequacy_overrides:
        adequacy.update(adequacy_overrides)
    adequacy_sha=write_json(root,"canonical/governance/policy_adequacy.json",adequacy)
    verification={
        "schema":"PROJECT_BRAIN_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_V1",
        "policy_id":policy_id,
        "subject_git_blob_sha":adequacy_sha,
        "pass":True,
    }
    if verify_overrides:
        verification.update(verify_overrides)
    verification_sha=write_json(root,"canonical/verification/policy_adequacy_verify.json",verification)
    spec={
        "schema":"PROJECT_BRAIN_ESCAPE_COMMON_POLICY_TOP_RESIDUAL_SPEC_V1",
        "scope_id":SCOPE,
        "decision_basis":["x","y"],
        "policy_id":policy_id,
        "policy_condition":condition,
        "adequacy_binding":{
            "adequacy_certificate_path":"canonical/governance/policy_adequacy.json",
            "adequacy_certificate_blob_sha":adequacy_sha,
            "independent_verification_path":"canonical/verification/policy_adequacy_verify.json",
            "independent_verification_blob_sha":verification_sha,
        },
    }
    if spec_overrides:
        spec.update(spec_overrides)
    spec_sha=write_json(root,"escape_top_spec.json",spec)
    return {"path":"escape_top_spec.json","git_blob_sha":spec_sha}


def run(condition=None, **kwargs):
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        ref=build(root,condition,**kwargs)
        return evaluate(ref,repo_root=root,expected_scope_id=SCOPE)


class EscapeCommonPolicyTopResidualTests(unittest.TestCase):
    def test_authenticated_true_policy_closes_top_declared_basis(self):
        out=run({"op":"TRUE"})
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["semantic_status"],"UNSAT_ON_TOP_DECLARED_BASIS")
        self.assertIsNone(out["residual_model"])
        self.assertTrue(out["authenticated_policy_adequacy"])
        self.assertFalse(out["u_empty_authorized"])
        self.assertIn("p cnf",out["dimacs"])

    def test_atom_policy_returns_constructive_top_counterexample(self):
        out=run({"op":"ATOM","id":"x"})
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["semantic_status"],"SAT_ON_TOP_DECLARED_BASIS")
        self.assertEqual(out["residual_model"]["x"],False)
        self.assertFalse(out["u_empty_authorized"])

    def test_tautology_is_unsat_residual(self):
        out=run({"op":"OR","args":[{"op":"ATOM","id":"x"},{"op":"NOT","arg":{"op":"ATOM","id":"x"}}]})
        self.assertEqual(out["semantic_status"],"UNSAT_ON_TOP_DECLARED_BASIS")

    def test_forged_adequacy_blob_fails_closed(self):
        out=run(spec_overrides={"adequacy_binding":{
            "adequacy_certificate_path":"canonical/governance/policy_adequacy.json",
            "adequacy_certificate_blob_sha":"0"*40,
            "independent_verification_path":"canonical/verification/policy_adequacy_verify.json",
            "independent_verification_blob_sha":"0"*40,
        }})
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"ADEQUACY_AUTHENTICATION_FAILED")

    def test_independent_verification_subject_mismatch_fails_closed(self):
        out=run(verify_overrides={"subject_git_blob_sha":"0"*40})
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"ADEQUACY_AUTHENTICATION_FAILED")

    def test_adequacy_false_fails_closed(self):
        out=run(adequacy_overrides={"adequacy_proved":False})
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"ADEQUACY_AUTHENTICATION_FAILED")

    def test_unknown_spec_field_fails_closed(self):
        out=run(spec_overrides={"u_empty_authorized":True})
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"SPEC_FIELDS_INVALID")

    def test_duplicate_basis_fails_closed(self):
        out=run(spec_overrides={"decision_basis":["x","x"]})
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"DECISION_BASIS_INVALID")

    def test_formula_outside_basis_fails_closed(self):
        out=run({"op":"ATOM","id":"z"})
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"POLICY_CONDITION_INVALID")

    def test_dimacs_is_deterministic(self):
        a=run({"op":"IMPLIES","if":{"op":"ATOM","id":"x"},"then":{"op":"ATOM","id":"y"}})
        b=run({"op":"IMPLIES","if":{"op":"ATOM","id":"x"},"then":{"op":"ATOM","id":"y"}})
        self.assertEqual(a["dimacs"],b["dimacs"])
        self.assertEqual(a["residual_sha256"],b["residual_sha256"])


if __name__=="__main__":
    unittest.main()

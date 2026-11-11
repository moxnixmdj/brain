import json
import tempfile
import unittest
from pathlib import Path

import canonical.runtime.p3_robust_policy_adequacy_cegar_v1 as cegar
from canonical.runtime.p3_cegar_selected_truth_bridge_v1 import evaluate
from canonical.runtime.selected_semantic_predicate_identity_v1 import compile_identity
from canonical.runtime.selected_semantic_discriminator_dispatch_v1 import evaluate as dispatch

POLICY = (
    "Total exposure means exposure_amount. "
    "Apply Rule A unless Total exposure is at least 125.50."
)


def truth_input(value="130.00", source=POLICY):
    return {
        "target_claim_id": "selected",
        "source_text": source,
        "source_id": "policy",
        "claims": [{
            "claim_id": "selected",
            "kind": "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION",
        }],
        "fact_source": json.dumps({
            "schema_id": "FINANCE_TYPED_CONTEXT_V1",
            "fields": {
                "exposure_amount": {
                    "type": "DECIMAL_STRING",
                    "value": value,
                }
            },
        }, separators=(",", ":")),
        "fact_source_id": "case-facts",
    }


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.old_root = cegar.ROOT
        self.tmp = tempfile.TemporaryDirectory()
        cegar.ROOT = Path(self.tmp.name)
        (cegar.ROOT / "canonical/governance").mkdir(parents=True)
        (cegar.ROOT / "canonical/verification").mkdir(parents=True)

    def tearDown(self):
        cegar.ROOT = self.old_root
        self.tmp.cleanup()

    def binding(self, policy_id, condition):
        gov = cegar.ROOT / "canonical/governance" / f"{policy_id}.json"
        ver = cegar.ROOT / "canonical/verification" / f"{policy_id}.json"
        gov.write_text(json.dumps({
            "schema": cegar.ADEQUACY_SCHEMA,
            "policy_id": policy_id,
            "policy_condition_sha256": cegar._condition_sha256(condition),
            "adequacy_proved": True,
            "brain_owned": True,
            "load_bearing_constraints_preserved": True,
        }, sort_keys=True), encoding="utf-8")
        gov_blob = cegar._git_blob_sha(gov)
        ver.write_text(json.dumps({
            "schema": cegar.VERIFY_SCHEMA,
            "policy_id": policy_id,
            "subject_git_blob_sha": gov_blob,
            "pass": True,
        }, sort_keys=True), encoding="utf-8")
        return {
            "adequacy_certificate_path": f"canonical/governance/{policy_id}.json",
            "adequacy_certificate_blob_sha": gov_blob,
            "independent_verification_path": f"canonical/verification/{policy_id}.json",
            "independent_verification_blob_sha": cegar._git_blob_sha(ver),
        }

    def divergent_problem(self, predicate_id):
        atom = {"op": "ATOM", "id": predicate_id}
        not_atom = {"op": "NOT", "arg": atom}
        return {
            "decision_basis": [predicate_id],
            "policy_conditions": {
                "p_true": atom,
                "p_false": not_atom,
            },
            "policy_adequacy_bindings": {
                "p_true": self.binding("p_true", atom),
                "p_false": self.binding("p_false", not_atom),
            },
            "discriminators": [{
                "discriminator_id": "selected",
                "formula": atom,
                "cost_units": 1,
            }],
        }

    def test_identity_matches_truth_checker_across_case_values(self):
        ident = compile_identity(POLICY, source_id="policy")
        self.assertTrue(ident["pass"])
        a = truth_input("130.00")
        a["predicate_id"] = "ignored-alias"
        b = truth_input("100.00")
        b["predicate_id"] = "another-alias"
        ta = dispatch(a, {"TRUE": "p_true", "FALSE": "p_false"})
        tb = dispatch(b, {"TRUE": "p_true", "FALSE": "p_false"})
        self.assertEqual(ident["predicate_id"], ta["predicate_id"])
        self.assertEqual(ident["predicate_id"], tb["predicate_id"])
        self.assertNotEqual(ta["predicate_truth"], tb["predicate_truth"])

    def test_true_selected_predicate_recompiles_to_true_policy(self):
        pid = compile_identity(POLICY, source_id="policy")["predicate_id"]
        out = evaluate({
            "cegar_problem": self.divergent_problem(pid),
            "truth_input": truth_input("130.00"),
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertEqual(out["selected_policy_id"], "p_true")
        self.assertTrue(out["truthful_selected_discriminator_bound"])
        self.assertFalse(out["u_subtraction_authority"])

    def test_false_selected_predicate_recompiles_to_false_policy(self):
        pid = compile_identity(POLICY, source_id="policy")["predicate_id"]
        out = evaluate({
            "cegar_problem": self.divergent_problem(pid),
            "truth_input": truth_input("100.00"),
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "FALSE")
        self.assertEqual(out["selected_policy_id"], "p_false")

    def test_alias_or_wrong_formula_cannot_inherit_checker_truth(self):
        out = evaluate({
            "cegar_problem": self.divergent_problem("CALLER_ALIAS"),
            "truth_input": truth_input("130.00"),
        })
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "SELECTED_FORMULA_NOT_CHECKER_CANONICAL_PREDICATE",
        )

    def test_changed_policy_source_invalidates_precommitted_formula(self):
        pid = compile_identity(POLICY, source_id="policy")["predicate_id"]
        changed = POLICY.replace("125.50", "120.00")
        out = evaluate({
            "cegar_problem": self.divergent_problem(pid),
            "truth_input": truth_input("130.00", source=changed),
        })
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "SELECTED_FORMULA_NOT_CHECKER_CANONICAL_PREDICATE",
        )

    def test_caller_claimed_truth_is_rejected(self):
        pid = compile_identity(POLICY, source_id="policy")["predicate_id"]
        ti = truth_input("130.00")
        ti["claims"][0]["condition_holds"] = True
        out = evaluate({
            "cegar_problem": self.divergent_problem(pid),
            "truth_input": ti,
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "TRUTH_INPUT_CLAIM_INVALID")

    def test_caller_semantic_refinement_is_forbidden(self):
        pid = compile_identity(POLICY, source_id="policy")["predicate_id"]
        problem = self.divergent_problem(pid)
        problem["formal_source_constraints"] = [{"op": "ATOM", "id": pid}]
        out = evaluate({"cegar_problem": problem, "truth_input": truth_input()})
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "CALLER_SEMANTIC_REFINEMENTS_FORBIDDEN")

    def test_common_policy_stops_without_truth_observation(self):
        condition = {"op": "TRUE"}
        problem = {
            "decision_basis": ["x"],
            "policy_conditions": {"p": condition},
            "policy_adequacy_bindings": {"p": self.binding("p", condition)},
            "discriminators": [],
        }
        out = evaluate({"cegar_problem": problem})
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_policy_id"], "p")
        self.assertFalse(out["semantic_observation_consumed"])


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

import canonical.runtime.p3_robust_policy_adequacy_cegar_v1 as cegar
from canonical.runtime.p3_selected_truth_root_contract_v1 import CONTRACT, compile_root_task
from canonical.runtime.p3_root_bound_cegar_selected_truth_v1 import evaluate

POLICY = (
    "Total exposure means exposure_amount. "
    "Apply Rule A unless Total exposure is at least 125.50."
)


def root_task(value="130.00", policy=POLICY):
    return json.dumps({
        "contract": CONTRACT,
        "policy_source": {"source_id": "policy", "text": policy},
        "fact_source": {
            "source_id": "case-facts",
            "raw_json": json.dumps({
                "schema_id": "FINANCE_TYPED_CONTEXT_V1",
                "fields": {
                    "exposure_amount": {
                        "type": "DECIMAL_STRING",
                        "value": value,
                    }
                },
            }, separators=(",", ":")),
        },
    }, separators=(",", ":"))


class RootBoundBridgeTests(unittest.TestCase):
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

    def problem(self, predicate_id):
        atom = {"op": "ATOM", "id": predicate_id}
        not_atom = {"op": "NOT", "arg": atom}
        return {
            "decision_basis": [predicate_id],
            "policy_conditions": {"p_true": atom, "p_false": not_atom},
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

    def test_root_compiler_binds_exact_sources_without_self_proving_intent(self):
        out = compile_root_task(root_task())
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["root_task_source_binding_verified"])
        self.assertTrue(out["source_authorization_verified_relative_to_root_task"])
        self.assertFalse(out["root_task_authority_self_proved"])

    def test_root_bound_true_path_recompiles_policy(self):
        root = compile_root_task(root_task("130.00"))
        out = evaluate({
            "root_task": root_task("130.00"),
            "cegar_problem": self.problem(root["predicate_id"]),
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_policy_id"], "p_true")
        self.assertTrue(out["source_authorization_verified_relative_to_root_task"])
        self.assertFalse(out["u_subtraction_authority"])

    def test_root_bound_false_path_recompiles_policy(self):
        root = compile_root_task(root_task("100.00"))
        out = evaluate({
            "root_task": root_task("100.00"),
            "cegar_problem": self.problem(root["predicate_id"]),
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_policy_id"], "p_false")

    def test_changed_root_source_cannot_use_old_predicate_identity(self):
        original = compile_root_task(root_task())
        changed = POLICY.replace("125.50", "120.00")
        out = evaluate({
            "root_task": root_task("130.00", policy=changed),
            "cegar_problem": self.problem(original["predicate_id"]),
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "CEGAR_TRUTH_BRIDGE_FAILED")

    def test_duplicate_root_json_key_fails_closed(self):
        raw = (
            '{"contract":"' + CONTRACT + '","contract":"' + CONTRACT + '",'
            '"policy_source":{"source_id":"policy","text":"x"},'
            '"fact_source":{"source_id":"facts","raw_json":"{}"}}'
        )
        out = compile_root_task(raw)
        self.assertFalse(out["pass"])
        self.assertIn("DUPLICATE_JSON_KEY:contract", out["errors"])

    def test_extra_root_semantic_field_fails_closed(self):
        doc = json.loads(root_task())
        doc["extra_authority"] = "forged"
        out = compile_root_task(json.dumps(doc))
        self.assertFalse(out["pass"])
        self.assertIn("TOP_KEYS_INVALID", out["errors"])

    def test_missing_predicate_field_fails_root_membership(self):
        doc = json.loads(root_task())
        facts = json.loads(doc["fact_source"]["raw_json"])
        facts["fields"] = {
            "other_field": {"type": "DECIMAL_STRING", "value": "130.00"}
        }
        doc["fact_source"]["raw_json"] = json.dumps(facts, separators=(",", ":"))
        out = compile_root_task(json.dumps(doc, separators=(",", ":")))
        self.assertFalse(out["pass"])
        self.assertIn("PREDICATE_FIELD_NOT_PRESENT_IN_FACT_SOURCE", out["errors"])

    def test_wrong_predicate_field_type_fails_root_membership(self):
        doc = json.loads(root_task())
        facts = json.loads(doc["fact_source"]["raw_json"])
        facts["fields"]["exposure_amount"] = {"type": "STRING", "value": "130.00"}
        doc["fact_source"]["raw_json"] = json.dumps(facts, separators=(",", ":"))
        out = compile_root_task(json.dumps(doc, separators=(",", ":")))
        self.assertFalse(out["pass"])
        self.assertIn("PREDICATE_FIELD_TYPE_MISMATCH", out["errors"])


if __name__ == "__main__":
    unittest.main()

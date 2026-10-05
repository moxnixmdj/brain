import copy
import unittest

from canonical.runtime import execution_authority_reducer_v4_policy_attested as v4
from canonical.runtime import staged_policy_attestation_v1 as gate


def policy_document():
    return {
        "schema": gate.POLICY_SCHEMA,
        "status": "MANDATORY_FAIL_CLOSED_BEFORE_UNTOUCHED_QUALIFICATION_SPEND",
        "staged_admission": {
            gate.STAGE_B: {"required": list(gate.STAGE_B_REQUIRED)},
            gate.STAGE_C: {"required": list(gate.STAGE_C_REQUIRED)},
        },
    }


def stage_b_evidence():
    receipts = {
        item: {
            "path": "canonical/verification/" + item + ".json",
            "git_blob_sha": "a" * 40,
        }
        for item in gate.STAGE_B_REQUIRED
    }
    return {"policy_attestation": gate.build_stage_b_attestation(receipts=receipts)}


def lease_evidence():
    return {
        "stage_c_policy_binding": gate.build_stage_c_policy_binding(
            candidate_sha256="b" * 64,
            plan_sha256="c" * 64,
        )
    }


def event_chain(*, stage_b=None, lease=None):
    stage_b = stage_b_evidence() if stage_b is None else stage_b
    lease = lease_evidence() if lease is None else lease
    raw = [
        ("STAGE_A_PASS", {"receipt": "stage-a"}),
        ("STAGE_B_PASS", stage_b),
        ("SOURCE_BOUNDARY_PASS", {"receipt": "source"}),
        ("EXECUTION_SURFACE_PASS", {"receipt": "surface"}),
        ("ACCEPTANCE_FROZEN", {"receipt": "acceptance"}),
        ("MINIMUM_REALITY_CUT_PASS", {"receipt": "minimum-cut"}),
        ("RUNTIME_API_PREFLIGHT_PASS", {"receipt": "runtime-api"}),
        ("LEASE_ISSUED", lease),
        ("CARRIER_OPEN", {"carrier": "test"}),
    ]
    out = []
    prev = None
    for seq, (typ, evidence) in enumerate(raw):
        event = {
            "schema": "BRAIN_AUTHORITY_EVENT_V1",
            "task": "t",
            "seq": seq,
            "event_id": f"E{seq}",
            "type": typ,
            "evidence": evidence,
            "prev_event_sha256": prev,
        }
        event["event_sha256"] = v4.canonical_event_hash(event)
        prev = event["event_sha256"]
        out.append(event)
    return out


class PolicyAttestedExecutionAuthorityTests(unittest.TestCase):
    def derive(self, events=None, policy=None):
        return v4.derive_authority(
            event_chain() if events is None else events,
            task="t",
            execution_budget=1,
            verifier_budget=1,
            policy_document=policy_document() if policy is None else policy,
        )

    def test_live_policy_cardinality_is_pinned(self):
        self.assertEqual(len(gate.STAGE_B_REQUIRED), 25)
        self.assertEqual(len(gate.STAGE_C_REQUIRED), 10)
        self.assertEqual(len(set(gate.STAGE_B_REQUIRED)), 25)
        self.assertEqual(len(set(gate.STAGE_C_REQUIRED)), 10)

    def test_complete_policy_attested_chain_can_execute(self):
        out = self.derive()
        self.assertTrue(out["valid"], out)
        self.assertTrue(out["policy_attested"], out)
        self.assertTrue(out["can_execute"], out)
        self.assertFalse(out["can_verify"], out)

    def test_bare_stage_b_pass_is_rejected(self):
        out = self.derive(event_chain(stage_b={"receipt": "nonempty-but-incomplete"}))
        self.assertFalse(out["valid"])
        self.assertFalse(out["can_execute"])
        self.assertTrue(
            any("STAGE_B_POLICY_ATTESTATION_MISSING" in e for e in out["errors"]),
            out,
        )

    def test_missing_stage_b_item_is_rejected(self):
        evidence = stage_b_evidence()
        att = evidence["policy_attestation"]
        missing = gate.STAGE_B_REQUIRED[-1]
        att["passed_items"].remove(missing)
        att["source_receipts"].pop(missing)
        out = self.derive(event_chain(stage_b=evidence))
        self.assertFalse(out["valid"])
        self.assertTrue(
            any(("STAGE_B_ITEM_UNATTESTED:" + missing) in e for e in out["errors"]),
            out,
        )

    def test_unpinned_stage_b_receipt_is_rejected(self):
        evidence = stage_b_evidence()
        item = gate.STAGE_B_REQUIRED[0]
        evidence["policy_attestation"]["source_receipts"][item] = {
            "path": "canonical/verification/unpinned.json"
        }
        out = self.derive(event_chain(stage_b=evidence))
        self.assertFalse(out["valid"])
        self.assertTrue(
            any(("STAGE_B_RECEIPT_MISSING_OR_UNPINNED:" + item) in e for e in out["errors"]),
            out,
        )

    def test_stage_b_policy_growth_fails_closed(self):
        policy = policy_document()
        policy["staged_admission"][gate.STAGE_B]["required"].append("NEW_UNHANDLED_ITEM")
        out = self.derive(policy=policy)
        self.assertFalse(out["valid"])
        self.assertIn("POLICY_REQUIRED_DRIFT:" + gate.STAGE_B, out["errors"])

    def test_stage_c_policy_growth_fails_closed(self):
        policy = policy_document()
        policy["staged_admission"][gate.STAGE_C]["required"].append("NEW_UNHANDLED_ITEM")
        out = self.derive(policy=policy)
        self.assertFalse(out["valid"])
        self.assertIn("POLICY_REQUIRED_DRIFT:" + gate.STAGE_C, out["errors"])

    def test_lease_without_stage_c_binding_is_rejected(self):
        out = self.derive(event_chain(lease={"receipt": "lease"}))
        self.assertFalse(out["valid"])
        self.assertTrue(
            any("STAGE_C_POLICY_BINDING_MISSING" in e for e in out["errors"]),
            out,
        )

    def test_lease_with_mutated_candidate_hash_is_rejected(self):
        evidence = lease_evidence()
        evidence["stage_c_policy_binding"]["candidate_sha256"] = "not-a-hash"
        out = self.derive(event_chain(lease=evidence))
        self.assertFalse(out["valid"])
        self.assertTrue(
            any("STAGE_C_CANDIDATE_SHA256_INVALID" in e for e in out["errors"]),
            out,
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime import tool_discovery_retrieval_authority_gate_v1 as gate

ROOT = Path(__file__).resolve().parents[2]


def raw(rel: str) -> bytes:
    return (ROOT / rel).read_bytes()


def load(rel: str):
    return json.loads(raw(rel).decode("utf-8"))


def actual_blobs():
    return {
        "activation_blob": gate.git_blob_sha(raw(gate.EXPECTED["activation_path"])),
        "activation_verification_blob": gate.git_blob_sha(raw(gate.EXPECTED["activation_verification_path"])),
        "compiler_blob": gate.git_blob_sha(raw(gate.EXPECTED["compiler_path"])),
        "compiler_verification_blob": gate.git_blob_sha(raw(gate.EXPECTED["compiler_verification_path"])),
        "router_blob": gate.git_blob_sha(raw(gate.EXPECTED["router_path"])),
        "github_provider_blob": gate.git_blob_sha(raw(gate.EXPECTED["github_provider_path"])),
        "backend_verification_blob": gate.git_blob_sha(raw(gate.EXPECTED["backend_verification_path"])),
        "v3_activation_blob": gate.git_blob_sha(raw(gate.EXPECTED["v3_activation_path"])),
        "v3_activation_verification_blob": gate.git_blob_sha(raw(gate.EXPECTED["v3_activation_verification_path"])),
        "v4_activation_blob": gate.git_blob_sha(raw(gate.V4_EXPECTED["v4_activation_path"])),
        "v4_activation_verification_blob": gate.git_blob_sha(raw(gate.V4_EXPECTED["v4_activation_verification_path"])),
        "v5_activation_blob": gate.git_blob_sha(raw(gate.V5_EXPECTED["v5_activation_path"])),
        "v5_activation_verification_blob": gate.git_blob_sha(raw(gate.V5_EXPECTED["v5_activation_verification_path"])),
        "v5_executor_blob": gate.git_blob_sha(raw(gate.V5_EXPECTED["v5_executor_path"])),
        "v5_execution_verification_blob": gate.git_blob_sha(raw(gate.V5_EXPECTED["v5_execution_verification_path"])),
    }


def validate(hypergraph=None, activation=None, activation_verification=None, compiler_verification=None, backend_verification=None, v3_activation=None, v3_activation_verification=None, v4_activation=None, v4_activation_verification=None, v5_activation=None, v5_activation_verification=None, v5_execution_verification=None, blobs=None):
    return gate.validate(
        hypergraph or load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
        activation or load(gate.EXPECTED["activation_path"]),
        activation_verification or load(gate.EXPECTED["activation_verification_path"]),
        compiler_verification or load(gate.EXPECTED["compiler_verification_path"]),
        backend_verification or load(gate.EXPECTED["backend_verification_path"]),
        v3_activation or load(gate.EXPECTED["v3_activation_path"]),
        v3_activation_verification or load(gate.EXPECTED["v3_activation_verification_path"]),
        v4_activation or load(gate.V4_EXPECTED["v4_activation_path"]),
        v4_activation_verification or load(gate.V4_EXPECTED["v4_activation_verification_path"]),
        v5_activation or load(gate.V5_EXPECTED["v5_activation_path"]),
        v5_activation_verification or load(gate.V5_EXPECTED["v5_activation_verification_path"]),
        v5_execution_verification or load(gate.V5_EXPECTED["v5_execution_verification_path"]),
        blobs or actual_blobs(),
    )


class ToolDiscoveryRetrievalAuthorityGateV1Tests(unittest.TestCase):
    def test_exact_repository_passes(self):
        out = gate.evaluate_repository(ROOT)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["unknown_preserved"], out)
        self.assertTrue(out["same_epoch_replay_disabled"], out)
        self.assertTrue(out["v3_multilingual_adaptive_federation_mandatory"], out)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)

    def test_removing_mandatory_binding_fails_closed(self):
        h = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
        action = next(x for x in h["actions"] if gate.TARGET in x.get("target_predicates", []))
        action.pop("mandatory_retrieval_authority", None)
        out = validate(hypergraph=h)
        self.assertFalse(out["pass"], out)
        self.assertIn("MANDATORY_RETRIEVAL_AUTHORITY_MISSING", out["errors"])

    def test_stale_compiler_hash_fails_closed(self):
        h = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
        action = next(x for x in h["actions"] if gate.TARGET in x.get("target_predicates", []))
        action["mandatory_retrieval_authority"]["compiler_blob"] = "0" * 40
        out = validate(hypergraph=h)
        self.assertFalse(out["pass"], out)
        self.assertIn("AUTHORITY_BINDING_MISMATCH:compiler_blob", out["errors"])

    def test_actual_byte_drift_fails_closed(self):
        blobs = actual_blobs()
        blobs["router_blob"] = "f" * 40
        out = validate(blobs=blobs)
        self.assertFalse(out["pass"], out)
        self.assertIn("ACTUAL_BLOB_MISMATCH:router_blob", out["errors"])

    def test_reenabling_consumed_source_epoch_fails_closed(self):
        activation = load(gate.EXPECTED["activation_path"])
        activation["operational_policy"]["repeat_v2_github_source_epoch"] = True
        out = validate(activation=activation)
        self.assertFalse(out["pass"], out)
        self.assertIn("V2_GITHUB_SOURCE_EPOCH_REPLAY_NOT_DISABLED", out["errors"])

    def test_non_success_independent_receipt_fails_closed(self):
        receipt = load(gate.EXPECTED["activation_verification_path"])
        receipt["independent_runner"]["conclusion"] = "failure"
        out = validate(activation_verification=receipt)
        self.assertFalse(out["pass"], out)
        self.assertIn("ACTIVATION_INDEPENDENT_RUNNER_NOT_SUCCESS", out["errors"])

    def test_stale_v3_activation_hash_fails_closed(self):
        h = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
        action = next(x for x in h["actions"] if gate.TARGET in x.get("target_predicates", []))
        action["mandatory_retrieval_authority"]["v3_activation_blob"] = "0" * 40
        out = validate(hypergraph=h)
        self.assertFalse(out["pass"], out)
        self.assertIn("AUTHORITY_BINDING_MISMATCH:v3_activation_blob", out["errors"])

    def test_failed_v3_activation_receipt_fails_closed(self):
        receipt = load(gate.EXPECTED["v3_activation_verification_path"])
        receipt["independent_runner"]["conclusion"] = "failure"
        out = validate(v3_activation_verification=receipt)
        self.assertFalse(out["pass"], out)
        self.assertIn("V3_ACTIVATION_INDEPENDENT_RUNNER_NOT_SUCCESS", out["errors"])

    def test_removing_v3_epoch_exhaustion_firewall_fails_closed(self):
        activation = load(gate.EXPECTED["v3_activation_path"])
        activation["hard_rules"].remove(
            "NO_SOURCE_EPOCH_EXHAUSTION_BEFORE_V3_EXPANSION_UNLESS_A_VERIFIED_SUFFICIENT_WITNESS_ALREADY_STOPPED_THE_SEARCH"
        )
        out = validate(v3_activation=activation)
        self.assertFalse(out["pass"], out)
        self.assertIn("V3_EPOCH_EXHAUSTION_FIREWALL_MISSING", out["errors"])

    def test_second_tool_discovery_action_fails_closed(self):
        h = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
        original = next(x for x in h["actions"] if gate.TARGET in x.get("target_predicates", []))
        duplicate = copy.deepcopy(original)
        duplicate["id"] = "BYPASS_TOOL_DISCOVERY_SEARCH"
        h["actions"].append(duplicate)
        out = validate(hypergraph=h)
        self.assertFalse(out["pass"], out)
        self.assertIn("TOOL_DISCOVERY_TARGET_ACTION_COUNT_NE_1:2", out["errors"])

    def test_v4_exact_repository_passes_and_is_mandatory(self):
        out = gate.evaluate_repository(ROOT)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["v4_federated_router_receipts_mandatory"], out)

    def test_stale_v4_activation_hash_fails_closed(self):
        blobs = actual_blobs()
        blobs["v4_activation_blob"] = "0" * 40
        out = validate(blobs=blobs)
        self.assertFalse(out["pass"], out)
        self.assertIn("ACTUAL_BLOB_MISMATCH:v4_activation_blob", out["errors"])

    def test_v4_missing_router_receipt_rule_fails_closed(self):
        activation = load(gate.V4_EXPECTED["v4_activation_path"])
        activation["stop_rules"]["missing_or_unbound_router_receipt"] = "IGNORE"
        out = validate(v4_activation=activation)
        self.assertFalse(out["pass"], out)
        self.assertIn("V4_MISSING_RECEIPT_STOP_RULE_INVALID", out["errors"])

    def test_failed_v4_independent_receipt_fails_closed(self):
        receipt = load(gate.V4_EXPECTED["v4_activation_verification_path"])
        receipt["independent_runner"]["conclusion"] = "failure"
        out = validate(v4_activation_verification=receipt)
        self.assertFalse(out["pass"], out)
        self.assertIn("V4_ACTIVATION_INDEPENDENT_RUNNER_NOT_SUCCESS", out["errors"])


    def test_v5_strict_execution_is_required(self):
        out = gate.evaluate_repository(ROOT)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["v5_success_only_epoch_consumption_mandatory"], out)

    def test_removing_v5_retry_rule_fails_closed(self):
        activation = load(gate.V5_EXPECTED["v5_activation_path"])
        activation["mandatory_epoch_protocol"].remove(
            "TRANSIENT_OR_REJECTED_BACKEND_FAILURES_REMAIN_RETRYABLE_AND_UNCONSUMED"
        )
        out = validate(v5_activation=activation)
        self.assertFalse(out["pass"], out)
        self.assertIn(
            "V5_PROTOCOL_MISSING:TRANSIENT_OR_REJECTED_BACKEND_FAILURES_REMAIN_RETRYABLE_AND_UNCONSUMED",
            out["errors"],
        )

    def test_failed_v5_execution_receipt_fails_closed(self):
        receipt = load(gate.V5_EXPECTED["v5_execution_verification_path"])
        receipt["independent_runner"]["conclusion"] = "failure"
        out = validate(v5_execution_verification=receipt)
        self.assertFalse(out["pass"], out)
        self.assertIn("V5_EXECUTION_INDEPENDENT_RUNNER_NOT_SUCCESS", out["errors"])

    def test_stale_v5_executor_hash_fails_closed(self):
        blobs = actual_blobs()
        blobs["v5_executor_blob"] = "0" * 40
        out = validate(blobs=blobs)
        self.assertFalse(out["pass"], out)
        self.assertIn("ACTUAL_BLOB_MISMATCH:v5_executor_blob", out["errors"])

    def test_v5_partial_batch_rule_removal_fails_closed(self):
        activation = load(gate.V5_EXPECTED["v5_activation_path"])
        activation["hard_rules"].remove("NO_PARTIAL_BATCH_TO_SOURCE_EPOCH_CONSUMPTION")
        out = validate(v5_activation=activation)
        self.assertFalse(out["pass"], out)
        self.assertIn(
            "V5_HARD_RULE_MISSING:NO_PARTIAL_BATCH_TO_SOURCE_EPOCH_CONSUMPTION",
            out["errors"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

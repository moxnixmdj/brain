from __future__ import annotations

from hashlib import sha256
import json
import unittest

from canonical.runtime import aa_briefcase_owner_handoff_gate_v1 as gate


def _sha(value):
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _fixtures():
    decision = {
        "schema": gate.OWNER_DECISION_SCHEMA,
        "status": "OWNER_CONFIRMED",
        "benchmark": "AA-Briefcase",
        "benchmark_version": "1.1",
        "official_private_scope": True,
        "independent_no_fee_coverage": True,
        "full_agent_execution_supported": True,
        "integration_route": "INDEPENDENT_OFFICIAL_CUSTOM_AGENT_HTTP",
        "interface_contract_sha256": "1" * 64,
        "interface_contract_uri": "https://artificialanalysis.ai/aa-briefcase/agent-contract",
        "comparability_route": "EXACT_FROZEN_2026_09_22_RATING_EPOCH",
        "comparability_evidence_sha256": "2" * 64,
        "comparability_evidence_uri": "https://artificialanalysis.ai/aa-briefcase/epoch-evidence",
        "owner_evidence_sha256": "3" * 64,
        "owner_source_uri": "https://artificialanalysis.ai/aa-briefcase/brain-decision",
    }
    statement = _sha({
        "claim": "AA_BRIEFCASE_OFFICIAL_ZERO_FEE_FULL_AGENT_HANDOFF_CONFIRMED",
        "benchmark": "AA-Briefcase",
        "benchmark_version": "1.1",
        "official_private_scope": True,
        "independent_no_fee_coverage": True,
        "full_agent_execution_supported": True,
        "integration_route": decision["integration_route"],
        "interface_contract_sha256": decision["interface_contract_sha256"],
        "comparability_route": decision["comparability_route"],
        "comparability_evidence_sha256": decision[
            "comparability_evidence_sha256"
        ],
        "owner_evidence_sha256": decision["owner_evidence_sha256"],
    })
    authority_payload = {
        "schema": gate.AUTHORITY_SCHEMA,
        "verified": True,
        "source_kind": "OWNER_EVALUATOR",
        "verifier_id": "ARTIFICIAL_ANALYSIS_OWNER",
        "statement_sha256": statement,
        "evidence_sha256": decision["owner_evidence_sha256"],
        "verification_authority_mutated": False,
        "auth_method": "OWNER_PUBLISHED_RESULT",
        "auth_artifact_sha256": "4" * 64,
    }
    authority = {
        **authority_payload,
        "receipt_sha256": _sha(authority_payload),
    }
    carrier = {
        "schema": gate.CARRIER_SCHEMA,
        "carrier_kind": "HTTPS_FULL_AGENT_ENDPOINT",
        "zero_incremental_spend": True,
        "official_interface_contract_sha256": decision[
            "interface_contract_sha256"
        ],
        "carrier_artifact_sha256": "5" * 64,
        "cognition_substrate_sha256": "6" * 64,
        "tool_surface_sha256": "7" * 64,
        "state_policy_sha256": "8" * 64,
        "endpoint_or_package_locator_sha256": "9" * 64,
    }
    return decision, authority, carrier


def _rebind(decision, authority):
    statement = _sha({
        "claim": "AA_BRIEFCASE_OFFICIAL_ZERO_FEE_FULL_AGENT_HANDOFF_CONFIRMED",
        "benchmark": "AA-Briefcase",
        "benchmark_version": "1.1",
        "official_private_scope": True,
        "independent_no_fee_coverage": True,
        "full_agent_execution_supported": True,
        "integration_route": decision["integration_route"],
        "interface_contract_sha256": decision["interface_contract_sha256"],
        "comparability_route": decision["comparability_route"],
        "comparability_evidence_sha256": decision[
            "comparability_evidence_sha256"
        ],
        "owner_evidence_sha256": decision["owner_evidence_sha256"],
    })
    payload = dict(authority)
    payload["statement_sha256"] = statement
    payload.pop("receipt_sha256", None)
    return {**payload, "receipt_sha256": _sha(payload)}


class AAOwnerHandoffGateV1Tests(unittest.TestCase):
    def test_complete_owner_decision_and_carrier_freeze(self):
        decision, authority, carrier = _fixtures()
        handoff = gate.adjudicate_owner_decision(decision, authority)
        frozen = gate.freeze_subject(
            handoff,
            carrier,
            repository_commit_sha="a" * 40,
            execution_profile_git_blob_sha="b" * 40,
            configuration_git_blob_sha="c" * 40,
            stirrup_root_tree_sha="d" * 40,
        )
        self.assertEqual(handoff["status"], "READY_TO_FREEZE_CALLABLE_SUBJECT")
        self.assertEqual(frozen["status"], "FROZEN_CALLABLE_SUBJECT")
        self.assertEqual(
            frozen["subject"]["execution_bundle_sha256"],
            frozen["execution_bundle_sha256"],
        )
        self.assertFalse(frozen["terminal_authority"])

    def test_no_fee_not_confirmed_rejected(self):
        decision, authority, _ = _fixtures()
        decision["independent_no_fee_coverage"] = False
        with self.assertRaisesRegex(
            gate.HandoffError,
            "NO_FEE_OFFICIAL_COVERAGE_NOT_CONFIRMED",
        ):
            gate.adjudicate_owner_decision(decision, authority)

    def test_full_agent_not_confirmed_rejected(self):
        decision, authority, _ = _fixtures()
        decision["full_agent_execution_supported"] = False
        with self.assertRaisesRegex(
            gate.HandoffError,
            "FULL_AGENT_EXECUTION_NOT_CONFIRMED",
        ):
            gate.adjudicate_owner_decision(decision, authority)

    def test_paid_or_unrecognized_route_rejected(self):
        decision, authority, _ = _fixtures()
        decision["integration_route"] = "PAID_OPTIMA_CUSTOM_BENCHMARK"
        with self.assertRaisesRegex(gate.HandoffError, "INTEGRATION_ROUTE_INVALID"):
            gate.adjudicate_owner_decision(decision, authority)

    def test_forged_owner_receipt_rejected(self):
        decision, authority, _ = _fixtures()
        authority["receipt_sha256"] = "f" * 64
        with self.assertRaisesRegex(
            gate.HandoffError,
            "OWNER_AUTHORITY_RECEIPT_INVALID",
        ):
            gate.adjudicate_owner_decision(decision, authority)

    def test_non_owner_domain_contract_uri_rejected(self):
        decision, authority, _ = _fixtures()
        decision["interface_contract_uri"] = "https://example.com/contract"
        with self.assertRaisesRegex(
            gate.HandoffError,
            "INTERFACE_CONTRACT_URI_INVALID",
        ):
            gate.adjudicate_owner_decision(decision, authority)

    def test_carrier_contract_mismatch_rejected(self):
        decision, authority, carrier = _fixtures()
        handoff = gate.adjudicate_owner_decision(decision, authority)
        carrier["official_interface_contract_sha256"] = "e" * 64
        with self.assertRaisesRegex(
            gate.HandoffError,
            "CARRIER_INTERFACE_CONTRACT_MISMATCH",
        ):
            gate.freeze_subject(
                handoff,
                carrier,
                repository_commit_sha="a" * 40,
                execution_profile_git_blob_sha="b" * 40,
                configuration_git_blob_sha="c" * 40,
                stirrup_root_tree_sha="d" * 40,
            )

    def test_nonzero_spend_carrier_rejected(self):
        decision, authority, carrier = _fixtures()
        handoff = gate.adjudicate_owner_decision(decision, authority)
        carrier["zero_incremental_spend"] = False
        with self.assertRaisesRegex(
            gate.HandoffError,
            "CARRIER_ZERO_SPEND_NOT_PROVED",
        ):
            gate.freeze_subject(
                handoff,
                carrier,
                repository_commit_sha="a" * 40,
                execution_profile_git_blob_sha="b" * 40,
                configuration_git_blob_sha="c" * 40,
                stirrup_root_tree_sha="d" * 40,
            )

    def test_carrier_change_changes_frozen_subject(self):
        decision, authority, carrier = _fixtures()
        handoff = gate.adjudicate_owner_decision(decision, authority)
        first = gate.freeze_subject(
            handoff,
            carrier,
            repository_commit_sha="a" * 40,
            execution_profile_git_blob_sha="b" * 40,
            configuration_git_blob_sha="c" * 40,
            stirrup_root_tree_sha="d" * 40,
        )
        changed = dict(carrier)
        changed["cognition_substrate_sha256"] = "0" * 64
        second = gate.freeze_subject(
            handoff,
            changed,
            repository_commit_sha="a" * 40,
            execution_profile_git_blob_sha="b" * 40,
            configuration_git_blob_sha="c" * 40,
            stirrup_root_tree_sha="d" * 40,
        )
        self.assertNotEqual(first["subject_sha256"], second["subject_sha256"])

    def test_comparability_evidence_change_requires_new_owner_authority(self):
        decision, authority, _ = _fixtures()
        decision["comparability_evidence_sha256"] = "e" * 64
        with self.assertRaisesRegex(
            gate.HandoffError,
            "OWNER_AUTHORITY_RECEIPT_INVALID",
        ):
            gate.adjudicate_owner_decision(decision, authority)
        repaired = _rebind(decision, authority)
        out = gate.adjudicate_owner_decision(decision, repaired)
        self.assertTrue(out["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

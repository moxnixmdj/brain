from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from canonical.runtime import oewn_decision_sense_control_v1 as sense
from canonical.runtime import unified_cognitive_fabric_v1 as fabric
from canonical.runtime.oewn_release_sense_universe_v1 import (
    RELEASE_ID,
    RELEASE_SHA256,
    SCHEMA as OEWN_SCHEMA,
)


AUTH_ID = "bound:semantic.authority.receipt.verify.canonical"
EVIDENCE_ID = "bound:semantic.evidence.receipt.verify.canonical"


def universe():
    return {
        "schema": OEWN_SCHEMA,
        "status": "PASS__OEWN_2025_RELEASE_RELATIVE_SENSE_UNIVERSE_ENUMERATED",
        "pass": True,
        "release_id": RELEASE_ID,
        "archive_sha256": RELEASE_SHA256,
        "candidate_set_complete_relative_to_release": True,
        "open_world_english_sense_completeness_claimed": False,
        "lemma": "margin",
        "requested_part_of_speech": "n",
        "senses": [
            {"sense_id": "margin-1", "synset_id": "ewn-margin-1-n", "part_of_speech": "n"},
            {"sense_id": "margin-2", "synset_id": "ewn-margin-2-n", "part_of_speech": "n"},
        ],
    }


def manifest(*, equivalent=False):
    return {
        "schema": sense.MANIFEST_SCHEMA,
        "scope_id": "finance-margin-v1",
        "release_id": RELEASE_ID,
        "release_sha256": RELEASE_SHA256,
        "lemma": "margin",
        "part_of_speech": "n",
        "sense_bindings": [
            {
                "sense_id": "margin-1",
                "synset_id": "ewn-margin-1-n",
                "terminal_signature_complete": True,
                "terminal_signature": {"policy": "A"},
            },
            {
                "sense_id": "margin-2",
                "synset_id": "ewn-margin-2-n",
                "terminal_signature_complete": True,
                "terminal_signature": {"policy": "A" if equivalent else "B"},
            },
        ],
        "observations": [{
            "observation_id": "context-domain",
            "outcome_map_complete": True,
            "outcomes": {
                "margin-1": "profit",
                "margin-2": "collateral",
            },
            "cost_units": 1,
        }],
    }


def authority_for(m):
    return {
        "pass": True,
        "schema": sense.AUTHORITY_SCHEMA,
        "manifest_sha256": sense.manifest_sha256(m),
        "scope_id": m["scope_id"],
        "release_id": RELEASE_ID,
        "release_sha256": RELEASE_SHA256,
        "lemma": m["lemma"],
        "part_of_speech": m["part_of_speech"],
        "sense_set_binding_complete": True,
        "sense_terminal_signatures_authenticated": True,
        "observation_outcomes_authenticated": True,
        "verification_authority_mutated": False,
        "receipt_sha256": "a" * 64,
    }


def evidence_for(m):
    return {
        "pass": True,
        "schema": sense.OBSERVATION_SCHEMA,
        "scope_id": m["scope_id"],
        "observation_id": "context-domain",
        "observed_outcome": "collateral",
        "source_authorized_for_scope": True,
        "verification_authority_mutated": False,
        "receipt_sha256": "b" * 64,
    }


def entry(local_id, effect, role):
    return {
        "capability_id": local_id,
        "entry": {
            "status": "VERIFIED_BOUND_CAPABILITY",
            "provides": [effect],
            "action_template": {
                "type": "invoke_capability",
                "args": {
                    "capability_id": local_id,
                    "receipt_json": "${input.receipt_json}",
                    "role": role,
                },
            },
        },
    }


def execute_passthrough(local_id, *, inputs):
    return {
        "pass": True,
        "status": "PASS__PROMOTED_BOUND_CAPABILITY_EXECUTED_AND_TRACE_VERIFIED",
        "result": json.loads(inputs["receipt_json"]),
    }


class SemanticAuthorityCapabilityTransportV1Tests(unittest.TestCase):
    def _stable(self):
        return patch.object(
            fabric.improvement_driver,
            "drain",
            return_value={
                "pass": True,
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "progress_count": 0,
                "actions": [],
            },
        )

    def test_serializable_authority_verifier_id_drives_real_oewn_controller(self):
        m = manifest(equivalent=True)
        auth = authority_for(m)
        auth_entry = entry(
            "semantic.authority.receipt.verify.canonical",
            "semantic.authority.receipt.verified",
            "OEWN_DECISION_MANIFEST_AUTHORITY",
        )
        with patch.object(fabric, "inspect_bound", return_value=auth_entry), \
             patch.object(fabric, "execute_bound", side_effect=execute_passthrough), \
             self._stable():
            out = fabric.run({
                "mode": "OEWN_DECISION_SENSE",
                "payload": {
                    "sense_universe": universe(),
                    "decision_manifest": m,
                    "authority_receipt": auth,
                    "authority_verifier_capability_id": AUTH_ID,
                },
                "options": {"learn": False},
            })
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertTrue(out["inner_pass"], out)
        self.assertTrue(out["result"]["decision_sufficient"])
        self.assertEqual(
            out["result"]["semantic_verifier_transport"][
                "authority_verifier_capability_id"
            ],
            AUTH_ID,
        )
        self.assertFalse(
            out["result"]["semantic_verifier_transport"][
                "execution_ownership_is_semantic_authority"
            ]
        )

    def test_serializable_evidence_verifier_id_can_identify_one_sense(self):
        m = manifest(equivalent=False)
        auth = authority_for(m)
        evidence = evidence_for(m)

        def inspected(local_id):
            if local_id == "semantic.authority.receipt.verify.canonical":
                return entry(
                    local_id,
                    "semantic.authority.receipt.verified",
                    "OEWN_DECISION_MANIFEST_AUTHORITY",
                )
            if local_id == "semantic.evidence.receipt.verify.canonical":
                return entry(
                    local_id,
                    "semantic.evidence.receipt.verified",
                    "OEWN_SENSE_OBSERVATION_EVIDENCE",
                )
            raise AssertionError(local_id)

        with patch.object(fabric, "inspect_bound", side_effect=inspected), \
             patch.object(fabric, "execute_bound", side_effect=execute_passthrough), \
             self._stable():
            out = fabric.run({
                "mode": "OEWN_DECISION_SENSE",
                "payload": {
                    "sense_universe": universe(),
                    "decision_manifest": m,
                    "authority_receipt": auth,
                    "authority_verifier_capability_id": AUTH_ID,
                    "evidence_receipts": [evidence],
                    "evidence_verifier_capability_id": EVIDENCE_ID,
                },
                "options": {"learn": False},
            })
        self.assertTrue(out["inner_pass"], out)
        self.assertTrue(out["result"]["intended_sense_identified"])
        self.assertEqual(out["result"]["identified_sense_id"], "margin-2")

    def test_arbitrary_verified_capability_cannot_impersonate_semantic_authority(self):
        wrong = {
            "capability_id": "json.query.jq",
            "entry": {
                "status": "VERIFIED_BOUND_CAPABILITY",
                "provides": ["json.query.transform"],
                "action_template": {
                    "type": "invoke_capability",
                    "args": {"capability_id": "json.query.jq"},
                },
            },
        }
        with patch.object(fabric, "inspect_bound", return_value=wrong), \
             patch.object(fabric, "execute_bound") as executed, \
             self._stable():
            out = fabric.run({
                "mode": "OEWN_DECISION_SENSE",
                "payload": {
                    "sense_universe": universe(),
                    "decision_manifest": manifest(equivalent=True),
                    "authority_receipt": {"pass": True},
                    "authority_verifier_capability_id": "bound:json.query.jq",
                },
                "options": {"learn": False},
            })
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("SEMANTIC_VERIFIER_CAPABILITY_ROLE_MISMATCH", out["reason"])
        executed.assert_not_called()

    def test_non_bound_namespace_is_rejected(self):
        with self._stable():
            out = fabric.run({
                "mode": "OEWN_DECISION_SENSE",
                "payload": {
                    "sense_universe": universe(),
                    "decision_manifest": manifest(equivalent=True),
                    "authority_receipt": {"pass": True},
                    "authority_verifier_capability_id": (
                        "semantic.authority.receipt.verify.canonical"
                    ),
                },
                "options": {"learn": False},
            })
        self.assertFalse(out["pass"])
        self.assertIn("MUST_USE_BOUND_NAMESPACE", out["reason"])

    def test_bound_execution_failure_cannot_be_promoted_to_authority(self):
        m = manifest(equivalent=True)
        auth = authority_for(m)
        auth_entry = entry(
            "semantic.authority.receipt.verify.canonical",
            "semantic.authority.receipt.verified",
            "OEWN_DECISION_MANIFEST_AUTHORITY",
        )
        with patch.object(fabric, "inspect_bound", return_value=auth_entry), \
             patch.object(
                 fabric,
                 "execute_bound",
                 return_value={"pass": False, "status": "FAIL_CLOSED"},
             ), \
             self._stable():
            out = fabric.run({
                "mode": "OEWN_DECISION_SENSE",
                "payload": {
                    "sense_universe": universe(),
                    "decision_manifest": m,
                    "authority_receipt": auth,
                    "authority_verifier_capability_id": AUTH_ID,
                },
                "options": {"learn": False},
            })
        self.assertFalse(out["inner_pass"])
        self.assertEqual(
            out["result"]["status"],
            "OPEN__AUTHENTICATED_OEWN_DECISION_MANIFEST_REQUIRED",
        )
        self.assertFalse(out["result"]["authority_result"]["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

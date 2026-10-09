from __future__ import annotations

import unittest

from canonical.runtime import oewn_decision_sense_control_v1 as c
from canonical.runtime.oewn_release_sense_universe_v1 import (
    RELEASE_ID,
    RELEASE_SHA256,
    SCHEMA as OEWN_SCHEMA,
)


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


def manifest(*, equivalent=False, observations=True):
    obs = []
    if observations:
        obs = [
            {
                "observation_id": "context-domain",
                "outcome_map_complete": True,
                "outcomes": {
                    "margin-1": "profit",
                    "margin-2": "collateral",
                },
                "cost_units": 1,
            }
        ]
    return {
        "schema": c.MANIFEST_SCHEMA,
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
        "observations": obs,
    }


def authority_for(m):
    return {
        "pass": True,
        "schema": c.AUTHORITY_SCHEMA,
        "manifest_sha256": c.manifest_sha256(m),
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


def passthrough(row):
    return dict(row)


class OewnDecisionSenseControlTests(unittest.TestCase):
    def test_requires_manifest_authority(self):
        m = manifest()
        out = c.resolve(sense_universe=universe(), decision_manifest=m)
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "OPEN__AUTHENTICATED_OEWN_DECISION_MANIFEST_REQUIRED")
        self.assertTrue(out["candidate_sense_set_complete_relative_to_oewn_release"])
        self.assertFalse(out["decision_manifest_authenticated"])

    def test_rejects_incomplete_sense_binding(self):
        m = manifest()
        m["sense_bindings"] = m["sense_bindings"][:1]
        out = c.resolve(
            sense_universe=universe(),
            decision_manifest=m,
            authority_receipt={},
            authority_verifier=passthrough,
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("SENSE_BINDING_SET_NOT_EXACTLY_COMPLETE", out["reason"])

    def test_terminally_equivalent_senses_need_no_disambiguation(self):
        m = manifest(equivalent=True, observations=False)
        auth = authority_for(m)
        out = c.resolve(
            sense_universe=universe(),
            decision_manifest=m,
            authority_receipt=auth,
            authority_verifier=passthrough,
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["decision_sufficient"])
        self.assertFalse(out["intended_sense_identified"])
        self.assertEqual(
            out["decision_rule"],
            "ALL_SURVIVING_SENSES_TERMINALLY_EQUIVALENT",
        )
        self.assertEqual(set(out["surviving_sense_ids"]), {"margin-1", "margin-2"})

    def test_returns_minimum_policy_changing_discriminator(self):
        m = manifest(equivalent=False, observations=True)
        auth = authority_for(m)
        out = c.resolve(
            sense_universe=universe(),
            decision_manifest=m,
            authority_receipt=auth,
            authority_verifier=passthrough,
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "OPEN__MINIMUM_TERMINAL_DISCRIMINATOR_REQUIRED")
        self.assertEqual(out["next_observation_id"], "context-domain")
        self.assertEqual(out["minimum_worst_case_cost_units"], 1.0)
        self.assertTrue(out["additional_information_required"])

    def test_authenticated_observation_identifies_one_sense(self):
        m = manifest(equivalent=False, observations=True)
        auth = authority_for(m)
        evidence = {
            "pass": True,
            "schema": c.OBSERVATION_SCHEMA,
            "scope_id": m["scope_id"],
            "observation_id": "context-domain",
            "observed_outcome": "collateral",
            "source_authorized_for_scope": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "b" * 64,
        }
        out = c.resolve(
            sense_universe=universe(),
            decision_manifest=m,
            authority_receipt=auth,
            authority_verifier=passthrough,
            evidence_receipts=[evidence],
            evidence_verifier=passthrough,
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["decision_sufficient"])
        self.assertTrue(out["intended_sense_identified"])
        self.assertEqual(out["identified_sense_id"], "margin-2")
        self.assertEqual(out["surviving_sense_ids"], ["margin-2"])

    def test_conflicting_authenticated_observations_fail_closed(self):
        m = manifest(equivalent=False, observations=True)
        auth = authority_for(m)
        first = {
            "pass": True,
            "schema": c.OBSERVATION_SCHEMA,
            "scope_id": m["scope_id"],
            "observation_id": "context-domain",
            "observed_outcome": "profit",
            "source_authorized_for_scope": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "c" * 64,
        }
        second = dict(first)
        second["observed_outcome"] = "collateral"
        second["receipt_sha256"] = "d" * 64
        out = c.resolve(
            sense_universe=universe(),
            decision_manifest=m,
            authority_receipt=auth,
            authority_verifier=passthrough,
            evidence_receipts=[first, second],
            evidence_verifier=passthrough,
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("CONFLICTING_AUTHENTICATED_OBSERVATION_OUTCOMES", out["reason"])

    def test_observation_that_excludes_all_senses_falsifies_model(self):
        m = manifest(equivalent=False, observations=True)
        auth = authority_for(m)
        evidence = {
            "pass": True,
            "schema": c.OBSERVATION_SCHEMA,
            "scope_id": m["scope_id"],
            "observation_id": "context-domain",
            "observed_outcome": "neither",
            "source_authorized_for_scope": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "e" * 64,
        }
        out = c.resolve(
            sense_universe=universe(),
            decision_manifest=m,
            authority_receipt=auth,
            authority_verifier=passthrough,
            evidence_receipts=[evidence],
            evidence_verifier=passthrough,
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "MODEL_FALSIFIED__AUTHENTICATED_OBSERVATION_EXCLUDES_ALL_OEWN_SENSES",
        )

    def test_tampered_authority_manifest_hash_fails_closed(self):
        m = manifest()
        auth = authority_for(m)
        auth["manifest_sha256"] = "0" * 64
        out = c.resolve(
            sense_universe=universe(),
            decision_manifest=m,
            authority_receipt=auth,
            authority_verifier=passthrough,
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "OPEN__AUTHENTICATED_OEWN_DECISION_MANIFEST_REQUIRED")
        self.assertEqual(out["authority_result"]["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)

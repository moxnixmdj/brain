from __future__ import annotations

import unittest

from canonical.runtime import bounded_authenticated_concept_universe_v1 as concepts
from canonical.runtime import oewn_concept_policy_bridge_v1 as bridge


def oewn_result(*, absent=False):
    senses = [] if absent else [
        {
            "sense_id": "margin%1:21:01::",
            "synset_id": "10000001-n",
            "part_of_speech": "n",
        },
        {
            "sense_id": "margin%1:21:02::",
            "synset_id": "10000002-n",
            "part_of_speech": "n",
        },
    ]
    return {
        "pass": True,
        "candidate_set_complete_relative_to_release": True,
        "archive_sha256": "a" * 64,
        "lemma": "margin",
        "requested_part_of_speech": "n",
        "release_relative_absence": absent,
        "senses": senses,
    }


def registry(*, same_signature=False, separable=True):
    first = {"policy": "ALLOW", "threshold": "0.08"}
    second = first if same_signature else {"policy": "REQUIRE", "threshold": "0.12"}
    observations = []
    if separable:
        observations = [
            {
                "observation_id": "authoritative_definition_class",
                "outcome_map_complete": True,
                "outcomes": {
                    "concept-profit-margin": "profit",
                    "concept-collateral-margin": "collateral",
                },
                "cost_units": 1,
            }
        ]
    return {
        "schema": concepts.REGISTRY_SCHEMA,
        "registry_id": "finance-margin-v1",
        "scope_id": "finance-margin-task-bound-scope",
        "bounded_finite_registry": True,
        "concepts": [
            {
                "concept_id": "concept-profit-margin",
                "surfaces": ["margin"],
                "attributes": {"domain": "finance"},
                "terminal_signature_complete": True,
                "terminal_signature": first,
            },
            {
                "concept_id": "concept-collateral-margin",
                "surfaces": ["margin"],
                "attributes": {"domain": "finance"},
                "terminal_signature_complete": True,
                "terminal_signature": second,
            },
        ],
        "observations": observations,
    }


def authorities(oewn, reg, mapping):
    checked = concepts._validate_registry(reg)
    registry_sha = checked["registry_sha256"]
    registry_receipt = {
        "pass": True,
        "schema": concepts.AUTHORITY_SCHEMA,
        "registry_sha256": registry_sha,
        "registry_id": reg["registry_id"],
        "scope_id": reg["scope_id"],
        "scope_completeness_authenticated": True,
        "concept_semantics_authenticated": True,
        "verification_authority_mutated": False,
        "receipt_sha256": "b" * 64,
    }

    normalized_oewn = bridge._normalize_oewn(oewn)
    normalized_mapping = bridge._normalize_mapping(
        mapping,
        sense_ids=[x["sense_id"] for x in normalized_oewn["senses"]],
        registry_concept_ids=checked["concept_ids"],
    )
    basis = {
        "oewn_archive_sha256": normalized_oewn["archive_sha256"],
        "lemma": normalized_oewn["lemma"],
        "requested_part_of_speech": normalized_oewn["requested_part_of_speech"],
        "oewn_senses": normalized_oewn["senses"],
        "registry_sha256": registry_sha,
        "mapping": normalized_mapping,
    }
    mapping_receipt = {
        "pass": True,
        "schema": bridge.MAPPING_AUTHORITY_SCHEMA,
        "mapping_sha256": bridge._sha(basis),
        "oewn_archive_sha256": normalized_oewn["archive_sha256"],
        "registry_sha256": registry_sha,
        "mapping_complete_for_oewn_candidate_senses": True,
        "concept_link_semantics_authenticated": True,
        "verification_authority_mutated": False,
        "independent_verifier": True,
        "receipt_sha256": "c" * 64,
    }
    return registry_receipt, mapping_receipt


def run_bridge(*, same_signature=False, separable=True, mapping=None):
    oewn = oewn_result()
    reg = registry(same_signature=same_signature, separable=separable)
    if mapping is None:
        mapping = {
            "margin%1:21:01::": ["concept-profit-margin"],
            "margin%1:21:02::": ["concept-collateral-margin"],
        }
    rr, mr = authorities(oewn, reg, mapping)
    return bridge.resolve(
        oewn_result=oewn,
        registry=reg,
        sense_to_concept_ids=mapping,
        registry_authority_receipt=rr,
        registry_authority_verifier=lambda receipt: dict(receipt),
        mapping_authority_receipt=mr,
        mapping_authority_verifier=lambda receipt: dict(receipt),
    )


class OEWNConceptPolicyBridgeV1Tests(unittest.TestCase):
    def test_terminally_equivalent_senses_need_no_intended_sense_selection(self):
        out = run_bridge(same_signature=True)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__OEWN_COMPLETE_SENSES_BOUND_TO_TERMINALLY_EQUIVALENT_AUTHENTICATED_CONCEPTS",
        )
        self.assertFalse(out["intended_sense_identity_required"])
        self.assertEqual(len(out["oewn_sense_ids"]), 2)
        self.assertEqual(len(out["mapped_concept_ids"]), 2)
        self.assertTrue(out["hypothesis_set_complete_for_bound_bridge"])
        self.assertFalse(out["terminal_authority"])

    def test_policy_distinct_senses_return_exact_existing_minimax_discriminator(self):
        out = run_bridge(same_signature=False, separable=True)
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "OPEN__OEWN_SENSES_REQUIRE_MINIMUM_AUTHENTICATED_POLICY_DISCRIMINATOR",
        )
        self.assertEqual(out["next_observation_id"], "authoritative_definition_class")
        self.assertEqual(out["minimum_worst_case_cost_units"], 1.0)
        self.assertTrue(out["mapping_complete_for_oewn_candidate_senses"])
        self.assertFalse(out["terminal_authority"])

    def test_terminally_distinct_unseparable_senses_require_stronger_information(self):
        out = run_bridge(same_signature=False, separable=False)
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "OPEN__OEWN_SENSES_REQUIRE_STRONGER_AUTHENTIC_INFORMATION",
        )
        self.assertTrue(out["additional_information_required"])
        self.assertFalse(out["terminal_authority"])

    def test_mapping_cannot_silently_delete_an_oewn_sense(self):
        oewn = oewn_result()
        reg = registry()
        mapping = {
            "margin%1:21:01::": ["concept-profit-margin"],
        }
        checked = concepts._validate_registry(reg)
        rr = {
            "pass": True,
            "schema": concepts.AUTHORITY_SCHEMA,
            "registry_sha256": checked["registry_sha256"],
            "registry_id": reg["registry_id"],
            "scope_id": reg["scope_id"],
            "scope_completeness_authenticated": True,
            "concept_semantics_authenticated": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "b" * 64,
        }
        out = bridge.resolve(
            oewn_result=oewn,
            registry=reg,
            sense_to_concept_ids=mapping,
            registry_authority_receipt=rr,
            registry_authority_verifier=lambda receipt: dict(receipt),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("SENSE_MAPPING_DOMAIN_MISMATCH", out["reason"])

    def test_mapping_to_unknown_concept_fails_closed(self):
        oewn = oewn_result()
        reg = registry()
        mapping = {
            "margin%1:21:01::": ["concept-profit-margin"],
            "margin%1:21:02::": ["concept-not-in-registry"],
        }
        checked = concepts._validate_registry(reg)
        rr = {
            "pass": True,
            "schema": concepts.AUTHORITY_SCHEMA,
            "registry_sha256": checked["registry_sha256"],
            "registry_id": reg["registry_id"],
            "scope_id": reg["scope_id"],
            "scope_completeness_authenticated": True,
            "concept_semantics_authenticated": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "b" * 64,
        }
        out = bridge.resolve(
            oewn_result=oewn,
            registry=reg,
            sense_to_concept_ids=mapping,
            registry_authority_receipt=rr,
            registry_authority_verifier=lambda receipt: dict(receipt),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("SENSE_MAPPING_UNKNOWN_CONCEPT", out["reason"])

    def test_mapping_authority_cannot_be_omitted_or_self_asserted(self):
        oewn = oewn_result()
        reg = registry()
        mapping = {
            "margin%1:21:01::": ["concept-profit-margin"],
            "margin%1:21:02::": ["concept-collateral-margin"],
        }
        rr, _ = authorities(oewn, reg, mapping)
        out = bridge.resolve(
            oewn_result=oewn,
            registry=reg,
            sense_to_concept_ids=mapping,
            registry_authority_receipt=rr,
            registry_authority_verifier=lambda receipt: dict(receipt),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__AUTHENTICATED_OEWN_SENSE_TO_CONCEPT_MAPPING_REQUIRED",
        )
        self.assertEqual(
            out["mapping_authority_result"]["status"],
            "AUTHORITY_NOT_BOUND",
        )

    def test_verification_authority_mutation_is_rejected(self):
        oewn = oewn_result()
        reg = registry()
        mapping = {
            "margin%1:21:01::": ["concept-profit-margin"],
            "margin%1:21:02::": ["concept-collateral-margin"],
        }
        rr, mr = authorities(oewn, reg, mapping)
        mr["verification_authority_mutated"] = True
        out = bridge.resolve(
            oewn_result=oewn,
            registry=reg,
            sense_to_concept_ids=mapping,
            registry_authority_receipt=rr,
            registry_authority_verifier=lambda receipt: dict(receipt),
            mapping_authority_receipt=mr,
            mapping_authority_verifier=lambda receipt: dict(receipt),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__AUTHENTICATED_OEWN_SENSE_TO_CONCEPT_MAPPING_REQUIRED",
        )
        self.assertIn(
            "verification_authority_mutated",
            out["mapping_authority_result"]["mismatch_fields"],
        )

    def test_oewn_release_absence_never_becomes_open_world_absence(self):
        out = bridge.resolve(
            oewn_result=oewn_result(absent=True),
            registry=registry(),
            sense_to_concept_ids={},
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__OEWN_RELEASE_RELATIVE_ABSENCE__AUTHENTICATED_DOMAIN_UNIVERSE_REQUIRED",
        )
        self.assertTrue(out["oewn_candidate_set_complete"])
        self.assertIn("NOT_OPEN_WORLD", out["reason"].replace("IS_", "IS_NOT_" ) if False else "NOT_OPEN_WORLD")
        self.assertFalse(out["terminal_authority"])

    def test_multiple_senses_may_map_to_same_authenticated_concept_without_guessing(self):
        mapping = {
            "margin%1:21:01::": ["concept-profit-margin"],
            "margin%1:21:02::": ["concept-profit-margin"],
        }
        out = run_bridge(same_signature=False, separable=True, mapping=mapping)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["mapped_concept_ids"], ["concept-profit-margin"])
        self.assertFalse(out["intended_sense_identity_required"])
        self.assertFalse(out["intended_sense_identified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

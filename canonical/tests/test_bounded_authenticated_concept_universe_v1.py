import unittest

from canonical.runtime.bounded_authenticated_concept_universe_v1 import (
    AUTHORITY_SCHEMA,
    REGISTRY_SCHEMA,
    resolve,
)


def registry(*, same_action=False):
    sig_capital = {"action": "CAPITAL_BUFFER"} if not same_action else {"action": "SAME"}
    sig_tlac = {"action": "RESOLUTION_LIABILITY"} if not same_action else {"action": "SAME"}
    return {
        "schema": REGISTRY_SCHEMA,
        "registry_id": "bank-loss-absorption-v1",
        "scope_id": "bank-regulation",
        "bounded_finite_registry": True,
        "concepts": [
            {
                "concept_id": "REGULATORY_CAPITAL_BUFFER",
                "surfaces": ["capital buffer", "loss absorbing capital"],
                "attributes": {"phase": "going_concern", "domain": "prudential"},
                "terminal_signature_complete": True,
                "terminal_signature": sig_capital,
            },
            {
                "concept_id": "TLAC_MREL_RESOLUTION_LIABILITIES",
                "surfaces": ["loss absorbing liabilities", "resolution cushion"],
                "attributes": {"phase": "gone_concern", "domain": "resolution"},
                "terminal_signature_complete": True,
                "terminal_signature": sig_tlac,
            },
        ],
        "observations": [
            {
                "observation_id": "CHECK_RESOLUTION_CONTEXT",
                "outcome_map_complete": True,
                "outcomes": {
                    "REGULATORY_CAPITAL_BUFFER": "NO",
                    "TLAC_MREL_RESOLUTION_LIABILITIES": "YES",
                },
                "cost_units": 1,
            },
        ],
    }


def verifier_for(reg):
    import hashlib
    import json

    normalized = {
        "schema": REGISTRY_SCHEMA,
        "registry_id": reg["registry_id"],
        "scope_id": reg["scope_id"],
        "bounded_finite_registry": True,
        "concepts": [
            {
                "concept_id": c["concept_id"],
                "surfaces": sorted({" ".join(x.strip().split()).casefold() for x in c["surfaces"]}),
                "attributes": dict(c.get("attributes", {})),
                "terminal_signature": dict(c["terminal_signature"]),
            }
            for c in reg["concepts"]
        ],
        "observations": [
            {
                "observation_id": o["observation_id"],
                "outcome_map_complete": True,
                "outcomes": dict(o["outcomes"]),
                "cost_units": float(o["cost_units"]),
            }
            for o in reg.get("observations", [])
        ],
    }
    raw = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    digest = hashlib.sha256(raw).hexdigest()

    def verify(receipt):
        return {
            "pass": True,
            "schema": AUTHORITY_SCHEMA,
            "registry_sha256": digest,
            "registry_id": reg["registry_id"],
            "scope_id": reg["scope_id"],
            "scope_completeness_authenticated": True,
            "concept_semantics_authenticated": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "a" * 64,
        }

    return verify


class Tests(unittest.TestCase):
    def test_relative_registry_completeness_never_self_authenticates(self):
        reg = registry()
        out = resolve(reg, {"surface": "loss-absorbing cushion"})
        self.assertFalse(out["pass"])
        self.assertTrue(out["candidate_set_complete_relative_to_registry"])
        self.assertFalse(out["authenticated_scope_completeness"])
        self.assertFalse(out["hypothesis_set_complete"])
        self.assertEqual(
            out["status"],
            "OPEN__AUTHENTICATED_REGISTRY_SCOPE_COMPLETENESS_REQUIRED",
        )
        self.assertEqual(len(out["candidate_concept_ids"]), 2)

    def test_ambiguous_surface_does_not_delete_candidates(self):
        reg = registry()
        for c in reg["concepts"]:
            c["surfaces"].append("loss absorbing cushion")
        out = resolve(
            reg,
            {"surface": "loss absorbing cushion"},
            authority_receipt={"candidate": True},
            authority_verifier=verifier_for(reg),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(set(out["candidate_concept_ids"]), {
            "REGULATORY_CAPITAL_BUFFER",
            "TLAC_MREL_RESOLUTION_LIABILITIES",
        })
        self.assertEqual(
            out["ambiguity_decision"]["status"],
            "OPEN__MINIMUM_TERMINAL_DISCRIMINATOR_REQUIRED",
        )
        self.assertEqual(
            out["ambiguity_decision"]["next_observation_id"],
            "CHECK_RESOLUTION_CONTEXT",
        )

    def test_same_terminal_action_stops_without_global_identity(self):
        reg = registry(same_action=True)
        out = resolve(
            reg,
            {"surface": "loss-absorbing cushion"},
            authority_receipt={"candidate": True},
            authority_verifier=verifier_for(reg),
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["ambiguity_decision"]["status"],
            "PASS__AMBIGUITY_TERMINALLY_IRRELEVANT",
        )
        self.assertTrue(
            out["ambiguity_decision"]["does_not_require_full_interpretation_identity"]
        )

    def test_exact_typed_context_can_reduce_universe_without_guessing(self):
        reg = registry()
        out = resolve(
            reg,
            {"required_attributes": {"phase": "gone_concern"}},
            authority_receipt={"candidate": True},
            authority_verifier=verifier_for(reg),
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["candidate_concept_ids"],
            ["TLAC_MREL_RESOLUTION_LIABILITIES"],
        )

    def test_duplicate_concept_id_fails_closed(self):
        reg = registry()
        reg["concepts"][1]["concept_id"] = reg["concepts"][0]["concept_id"]
        out = resolve(reg, {})
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("CONCEPT_ID_DUPLICATE", out["reason"])

    def test_incomplete_observation_map_fails_closed(self):
        reg = registry()
        del reg["observations"][0]["outcomes"]["REGULATORY_CAPITAL_BUFFER"]
        out = resolve(reg, {})
        self.assertFalse(out["pass"])
        self.assertIn("OBSERVATION_OUTCOME_MAP_INCOMPLETE", out["reason"])

    def test_wrong_authority_binding_cannot_mint_complete_hypothesis_set(self):
        reg = registry()

        def wrong(_receipt):
            return {
                "pass": True,
                "schema": AUTHORITY_SCHEMA,
                "registry_sha256": "0" * 64,
                "registry_id": reg["registry_id"],
                "scope_id": reg["scope_id"],
                "scope_completeness_authenticated": True,
                "concept_semantics_authenticated": True,
                "verification_authority_mutated": False,
                "receipt_sha256": "a" * 64,
            }

        out = resolve(
            reg,
            {},
            authority_receipt={"candidate": True},
            authority_verifier=wrong,
        )
        self.assertFalse(out["pass"])
        self.assertFalse(out["authenticated_scope_completeness"])
        self.assertEqual(
            out["authority_result"]["reason"],
            "AUTHORITY_RECEIPT_BINDING_INVALID",
        )

    def test_exact_surface_only_is_optional_and_fail_closed_when_requested(self):
        reg = registry()
        out = resolve(
            reg,
            {"surface": "not in registry", "exact_surface_only": True},
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "MODEL_FALSIFIED__NO_CONCEPT_SURVIVES_DECLARED_REGISTRY_CONSTRAINTS",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

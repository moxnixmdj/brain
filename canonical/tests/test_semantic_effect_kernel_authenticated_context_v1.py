import json
import unittest

from canonical.runtime import bounded_authenticated_concept_universe_v1 as universe
from canonical.runtime.authenticated_context_concept_bridge_v1 import CONTEXT_AUTHORITY_SCHEMA
from canonical.runtime.authoritative_typed_context_compiler_v1 import compile_typed_context
from canonical.runtime import semantic_effect_kernel_v1 as K

SCOPE = "finance:test-sense"


def registry(*, same_terminal=False):
    profit_action = "SAME" if same_terminal else "PROFIT"
    collateral_action = "SAME" if same_terminal else "COLLATERAL"
    return {
        "schema": universe.REGISTRY_SCHEMA,
        "registry_id": "finance-margin-v1",
        "scope_id": SCOPE,
        "bounded_finite_registry": True,
        "concepts": [
            {
                "concept_id": "PROFIT_MARGIN",
                "surfaces": ["margin"],
                "attributes": {"phase": "income_statement", "domain": "finance"},
                "terminal_signature_complete": True,
                "terminal_signature": {"action": profit_action},
            },
            {
                "concept_id": "COLLATERAL_MARGIN",
                "surfaces": ["margin"],
                "attributes": {"phase": "collateral", "domain": "finance"},
                "terminal_signature_complete": True,
                "terminal_signature": {"action": collateral_action},
            },
        ],
        "observations": [
            {
                "observation_id": "CHECK_PHASE",
                "outcome_map_complete": True,
                "outcomes": {
                    "PROFIT_MARGIN": "income_statement",
                    "COLLATERAL_MARGIN": "collateral",
                },
                "cost_units": 1,
            }
        ],
    }


def raw(*, include_phase=True):
    fields = {"domain": {"type": "STRING", "value": "finance"}}
    if include_phase:
        fields["phase"] = {"type": "STRING", "value": "collateral"}
    return json.dumps({"schema_id": "finance-case-v1", "fields": fields}, sort_keys=True)


def verifiers(reg, source, *, include_phase=True):
    checked = universe._validate_registry(reg)
    compiled = compile_typed_context(source, source_id="case.json")

    def reg_verify(_):
        return {
            "pass": True,
            "schema": universe.AUTHORITY_SCHEMA,
            "registry_sha256": checked["registry_sha256"],
            "registry_id": reg["registry_id"],
            "scope_id": reg["scope_id"],
            "scope_completeness_authenticated": True,
            "concept_semantics_authenticated": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "a" * 64,
        }

    projection = [
        {"registry_attribute": "domain", "field_name": "domain", "field_type": "STRING"}
    ]
    if include_phase:
        projection = [
            {"registry_attribute": "phase", "field_name": "phase", "field_type": "STRING"}
        ]

    def ctx_verify(_):
        return {
            "pass": True,
            "schema": CONTEXT_AUTHORITY_SCHEMA,
            "scope_id": SCOPE,
            "source_id": "case.json",
            "raw_source_sha256": compiled["raw_source_sha256"],
            "typed_context_sha256": compiled["typed_context_sha256"],
            "source_authorized_for_scope": True,
            "field_semantics_authenticated": True,
            "verification_authority_mutated": False,
            "attribute_projection": projection,
            "receipt_sha256": "b" * 64,
        }

    return {"REGISTRY_AUTH": reg_verify, "CONTEXT_AUTH": ctx_verify}


def problem(reg, source, required_concept_id=None):
    out = {
        "registry": reg,
        "raw_context_source": source,
        "context_source_id": "case.json",
        "scope_id": SCOPE,
        "registry_authority_receipt": {"x": 1},
        "context_authority_receipt": {"x": 1},
        "registry_authority_verifier_id": "REGISTRY_AUTH",
        "context_authority_verifier_id": "CONTEXT_AUTH",
        "ambiguity_owner": "SYSTEM_MODEL",
    }
    if required_concept_id is not None:
        out["required_concept_id"] = required_concept_id
    return out


class Tests(unittest.TestCase):
    def bound_unique(self):
        reg = registry()
        source = raw()
        p = problem(reg, source, "COLLATERAL_MARGIN")
        effect = K.make_effect(
            effect_id="E-concept",
            semvar_id="m17",
            property_name="concept(m17)=COLLATERAL_MARGIN",
            source_ref="case.json#margin",
            context_version="ctx-v1",
            proof_obligation=p,
        )
        value = K.make_value("Margin increased.", context_version="ctx-v1", effects=[effect])
        auth = verifiers(reg, source)
        return reg, source, p, effect, value, auth

    def test_authenticated_context_concept_can_discharge_exact_binding(self):
        _, _, p, effect, value, auth = self.bound_unique()
        cert = K.issue_discharge_certificate(
            effect,
            proof_kind="AUTHENTICATED_CONTEXT_CONCEPT_V1",
            proof_problem=p,
            authority_verifiers=auth,
        )
        clean = K.discharge_effect(value, effect["effect_id"], cert, authority_verifiers=auth)
        self.assertEqual(K.active_effect_ids(clean), [])
        self.assertEqual(
            clean["discharged_effects"][0]["certificate"]["guarantee"],
            "FORMAL__AUTHORITY_VERIFIER_REPLAY_REQUIRED",
        )

    def test_authenticated_terminal_equivalence_can_discharge_only_decision_invariance(self):
        reg = registry(same_terminal=True)
        source = raw(include_phase=False)
        p = problem(reg, source)
        effect = K.make_effect(
            effect_id="E-terminal-invariant",
            semvar_id="m17",
            property_name=f"terminal_invariant(m17)@{SCOPE}",
            source_ref="case.json#margin",
            context_version="ctx-v1",
            proof_obligation=p,
        )
        value = K.make_value("Margin increased.", context_version="ctx-v1", effects=[effect])
        auth = verifiers(reg, source, include_phase=False)
        cert = K.issue_discharge_certificate(
            effect,
            proof_kind="AUTHENTICATED_CONTEXT_TERMINAL_INVARIANCE_V1",
            proof_problem=p,
            authority_verifiers=auth,
        )
        clean = K.discharge_effect(value, effect["effect_id"], cert, authority_verifiers=auth)
        self.assertEqual(K.active_effect_ids(clean), [])

    def test_terminal_invariance_route_rejects_distinct_surviving_actions(self):
        reg = registry(same_terminal=False)
        source = raw(include_phase=False)
        p = problem(reg, source)
        effect = K.make_effect(
            effect_id="E-terminal-invariant",
            semvar_id="m17",
            property_name=f"terminal_invariant(m17)@{SCOPE}",
            source_ref="case.json#margin",
            context_version="ctx-v1",
            proof_obligation=p,
        )
        auth = verifiers(reg, source, include_phase=False)
        with self.assertRaises(K.SemanticEffectError):
            K.issue_discharge_certificate(
                effect,
                proof_kind="AUTHENTICATED_CONTEXT_TERMINAL_INVARIANCE_V1",
                proof_problem=p,
                authority_verifiers=auth,
            )

    def test_authenticated_route_requires_authority_verifiers(self):
        _, _, p, effect, _, _ = self.bound_unique()
        with self.assertRaises(K.SemanticEffectError):
            K.issue_discharge_certificate(
                effect,
                proof_kind="AUTHENTICATED_CONTEXT_CONCEPT_V1",
                proof_problem=p,
            )

    def test_authenticated_discharge_history_requires_authority_on_transport(self):
        _, _, p, effect, value, auth = self.bound_unique()
        cert = K.issue_discharge_certificate(
            effect,
            proof_kind="AUTHENTICATED_CONTEXT_CONCEPT_V1",
            proof_problem=p,
            authority_verifiers=auth,
        )
        clean = K.discharge_effect(value, effect["effect_id"], cert, authority_verifiers=auth)
        no_auth = K.verify_transport(inputs=[clean], output=clean)
        self.assertFalse(no_auth["pass"])
        self.assertEqual(no_auth["status"], "FAIL_CLOSED__INVALID_DISCHARGE_HISTORY")
        with_auth = K.verify_transport(inputs=[clean], output=clean, authority_verifiers=auth)
        self.assertTrue(with_auth["pass"], with_auth)

    def test_authenticated_discharge_history_requires_authority_on_composition(self):
        _, _, p, effect, value, auth = self.bound_unique()
        cert = K.issue_discharge_certificate(
            effect,
            proof_kind="AUTHENTICATED_CONTEXT_CONCEPT_V1",
            proof_problem=p,
            authority_verifiers=auth,
        )
        clean = K.discharge_effect(value, effect["effect_id"], cert, authority_verifiers=auth)
        with self.assertRaises(K.SemanticEffectError):
            K.compose_value("summary", inputs=[clean])
        out = K.compose_value("summary", inputs=[clean], authority_verifiers=auth)
        self.assertEqual(K.active_effect_ids(out), [])

    def test_tampered_authenticated_certificate_is_rejected(self):
        _, _, p, effect, value, auth = self.bound_unique()
        cert = K.issue_discharge_certificate(
            effect,
            proof_kind="AUTHENTICATED_CONTEXT_CONCEPT_V1",
            proof_problem=p,
            authority_verifiers=auth,
        )
        forged = dict(cert)
        forged["proof_digest"] = "0" * 64
        with self.assertRaises(K.SemanticEffectError):
            K.discharge_effect(value, effect["effect_id"], forged, authority_verifiers=auth)

    def test_context_version_mismatch_rejects_authenticated_discharge(self):
        _, _, p, effect, value, auth = self.bound_unique()
        cert = K.issue_discharge_certificate(
            effect,
            proof_kind="AUTHENTICATED_CONTEXT_CONCEPT_V1",
            proof_problem=p,
            authority_verifiers=auth,
        )
        forged = dict(cert)
        forged["context_version"] = "ctx-v2"
        with self.assertRaises(K.SemanticEffectError):
            K.discharge_effect(value, effect["effect_id"], forged, authority_verifiers=auth)

    def test_discharge_one_effect_does_not_launder_another(self):
        _, _, p, effect, _, auth = self.bound_unique()
        other = K.make_effect(
            effect_id="E-kind",
            semvar_id="m17",
            property_name="gross_vs_net(m17)",
            source_ref="case.json#margin",
            context_version="ctx-v1",
        )
        value = K.make_value("x", context_version="ctx-v1", effects=[effect, other])
        cert = K.issue_discharge_certificate(
            effect,
            proof_kind="AUTHENTICATED_CONTEXT_CONCEPT_V1",
            proof_problem=p,
            authority_verifiers=auth,
        )
        out = K.discharge_effect(value, effect["effect_id"], cert, authority_verifiers=auth)
        self.assertEqual(K.active_effect_ids(out), ["E-kind"])

    def test_invalidating_authenticated_certificate_reintroduces_effect(self):
        _, _, p, effect, value, auth = self.bound_unique()
        cert = K.issue_discharge_certificate(
            effect,
            proof_kind="AUTHENTICATED_CONTEXT_CONCEPT_V1",
            proof_problem=p,
            authority_verifiers=auth,
        )
        clean = K.discharge_effect(value, effect["effect_id"], cert, authority_verifiers=auth)
        reopened = K.invalidate_certificates(clean, [cert["certificate_id"]])
        self.assertEqual(K.active_effect_ids(reopened), [effect["effect_id"]])
        self.assertEqual(reopened["discharged_effects"], [])

    def test_same_effect_id_with_different_semantics_is_rejected_after_discharge(self):
        _, _, p, effect, value, auth = self.bound_unique()
        cert = K.issue_discharge_certificate(
            effect,
            proof_kind="AUTHENTICATED_CONTEXT_CONCEPT_V1",
            proof_problem=p,
            authority_verifiers=auth,
        )
        discharged = K.discharge_effect(value, effect["effect_id"], cert, authority_verifiers=auth)
        conflicting = K.make_effect(
            effect_id=effect["effect_id"],
            semvar_id="m17",
            property_name="different_semantics(m17)",
            source_ref="case.json#margin",
            context_version="ctx-v1",
        )
        active = K.make_value("other", context_version="ctx-v1", effects=[conflicting])
        with self.assertRaises(K.SemanticEffectError):
            K.compose_value("combined", inputs=[discharged, active], authority_verifiers=auth)

    def test_transport_rejects_forged_prior_authenticated_discharge_history(self):
        _, _, p, effect, value, auth = self.bound_unique()
        cert = K.issue_discharge_certificate(
            effect,
            proof_kind="AUTHENTICATED_CONTEXT_CONCEPT_V1",
            proof_problem=p,
            authority_verifiers=auth,
        )
        clean = K.discharge_effect(value, effect["effect_id"], cert, authority_verifiers=auth)
        forged = dict(clean)
        forged["discharged_effects"] = [dict(clean["discharged_effects"][0])]
        forged["discharged_effects"][0]["certificate"] = dict(cert)
        forged["discharged_effects"][0]["certificate"]["proof_digest"] = "0" * 64
        verdict = K.verify_transport(inputs=[forged], output=forged, authority_verifiers=auth)
        self.assertFalse(verdict["pass"])
        self.assertEqual(verdict["status"], "FAIL_CLOSED__INVALID_DISCHARGE_HISTORY")


if __name__ == "__main__":
    unittest.main(verbosity=2)

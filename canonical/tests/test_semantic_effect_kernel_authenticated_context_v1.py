import json
import unittest

from canonical.runtime import bounded_authenticated_concept_universe_v1 as universe
from canonical.runtime.authenticated_context_concept_bridge_v1 import CONTEXT_AUTHORITY_SCHEMA
from canonical.runtime.authoritative_typed_context_compiler_v1 import compile_typed_context
from canonical.runtime import semantic_effect_kernel_v1 as K

SCOPE = "finance:test-sense"


def registry():
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
                "terminal_signature": {"action": "PROFIT"},
            },
            {
                "concept_id": "COLLATERAL_MARGIN",
                "surfaces": ["margin"],
                "attributes": {"phase": "collateral", "domain": "finance"},
                "terminal_signature_complete": True,
                "terminal_signature": {"action": "COLLATERAL"},
            },
        ],
        "observations": [],
    }


def raw():
    return json.dumps(
        {
            "schema_id": "finance-case-v1",
            "fields": {
                "domain": {"type": "STRING", "value": "finance"},
                "phase": {"type": "STRING", "value": "collateral"},
            },
        },
        sort_keys=True,
    )


def verifiers(reg, source):
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
            "attribute_projection": [
                {
                    "registry_attribute": "phase",
                    "field_name": "phase",
                    "field_type": "STRING",
                }
            ],
            "receipt_sha256": "b" * 64,
        }

    return {"REGISTRY_AUTH": reg_verify, "CONTEXT_AUTH": ctx_verify}


def problem(reg, source):
    return {
        "registry": reg,
        "raw_context_source": source,
        "context_source_id": "case.json",
        "scope_id": SCOPE,
        "registry_authority_receipt": {"x": 1},
        "context_authority_receipt": {"x": 1},
        "registry_authority_verifier_id": "REGISTRY_AUTH",
        "context_authority_verifier_id": "CONTEXT_AUTH",
        "ambiguity_owner": "SYSTEM_MODEL",
        "required_concept_id": "COLLATERAL_MARGIN",
    }


class Tests(unittest.TestCase):
    def _bound(self):
        reg = registry()
        source = raw()
        p = problem(reg, source)
        effect = K.make_effect(
            effect_id="E-concept",
            semvar_id="m17",
            property_name="concept(m17)=COLLATERAL_MARGIN",
            source_ref="case.json#margin",
            context_version="ctx-v1",
            proof_obligation=p,
        )
        value = K.make_value(
            "Margin increased.",
            context_version="ctx-v1",
            effects=[effect],
        )
        return reg, source, p, effect, value

    def test_authenticated_context_concept_can_discharge_exact_binding(self):
        reg, source, p, effect, value = self._bound()
        auth = verifiers(reg, source)
        cert = K.issue_discharge_certificate(
            effect,
            proof_kind="AUTHENTICATED_CONTEXT_CONCEPT_V1",
            proof_problem=p,
            authority_verifiers=auth,
        )
        clean = K.discharge_effect(
            value,
            effect["effect_id"],
            cert,
            authority_verifiers=auth,
        )
        self.assertEqual(K.active_effect_ids(clean), [])

    def test_authenticated_discharge_history_requires_authority_on_transport(self):
        reg, source, p, effect, value = self._bound()
        auth = verifiers(reg, source)
        cert = K.issue_discharge_certificate(
            effect,
            proof_kind="AUTHENTICATED_CONTEXT_CONCEPT_V1",
            proof_problem=p,
            authority_verifiers=auth,
        )
        clean = K.discharge_effect(
            value,
            effect["effect_id"],
            cert,
            authority_verifiers=auth,
        )
        no_auth = K.verify_transport(inputs=[clean], output=clean)
        self.assertFalse(no_auth["pass"])
        self.assertEqual(
            no_auth["status"],
            "FAIL_CLOSED__INVALID_DISCHARGE_HISTORY",
        )
        with_auth = K.verify_transport(
            inputs=[clean],
            output=clean,
            authority_verifiers=auth,
        )
        self.assertTrue(with_auth["pass"], with_auth)

    def test_authenticated_discharge_history_requires_authority_on_composition(self):
        reg, source, p, effect, value = self._bound()
        auth = verifiers(reg, source)
        cert = K.issue_discharge_certificate(
            effect,
            proof_kind="AUTHENTICATED_CONTEXT_CONCEPT_V1",
            proof_problem=p,
            authority_verifiers=auth,
        )
        clean = K.discharge_effect(
            value,
            effect["effect_id"],
            cert,
            authority_verifiers=auth,
        )
        with self.assertRaises(K.SemanticEffectError):
            K.compose_value("summary", inputs=[clean])
        out = K.compose_value(
            "summary",
            inputs=[clean],
            authority_verifiers=auth,
        )
        self.assertEqual(K.active_effect_ids(out), [])

    def test_authenticated_route_requires_authority_verifiers(self):
        _, _, p, effect, _ = self._bound()
        with self.assertRaises(K.SemanticEffectError):
            K.issue_discharge_certificate(
                effect,
                proof_kind="AUTHENTICATED_CONTEXT_CONCEPT_V1",
                proof_problem=p,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

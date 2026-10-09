import importlib
import unittest


def _kernel():
    try:
        return importlib.import_module("canonical.runtime.semantic_effect_kernel_v1")
    except ModuleNotFoundError:
        return None


K = _kernel()


def ambiguity_problem(*, same_terminal_result: bool):
    second = "TRUE" if same_terminal_result else "NOT_ESTABLISHED"
    return {
        "ambiguity_owner": "USER_INTENT",
        "hypothesis_set_complete": True,
        "worlds": [
            {
                "world_id": "profit-margin",
                "terminal_signature_complete": True,
                "terminal_signature": {"profitability_improved": "TRUE"},
            },
            {
                "world_id": "collateral-margin",
                "terminal_signature_complete": True,
                "terminal_signature": {"profitability_improved": second},
            },
        ],
        "observations": [],
    }


def identifiability_problem(*, unique_profit: bool):
    collateral_source_ok = False if unique_profit else True
    return {
        "interpretations": [
            {
                "id": "profit-margin",
                "meaning": "profit margin",
                "consistent_with_source": True,
                "consistent_with_authorized_context": True,
                "materially_distinct": True,
                "discriminator": "revenue/cost relation",
            },
            {
                "id": "collateral-margin",
                "meaning": "collateral margin",
                "consistent_with_source": collateral_source_ok,
                "consistent_with_authorized_context": True,
                "materially_distinct": True,
                "discriminator": "broker/collateral relation",
            },
        ],
        "authorized_context_ids": ["doc:1#sentence:2"],
        "required_interpretation_id": "profit-margin",
    }


@unittest.skipIf(K is None, "semantic effect kernel not implemented yet")
class SemanticEffectKernelBehaviorTests(unittest.TestCase):
    def effect(self, effect_id="E-margin-profit", prop="profit_related(m17)", problem=None):
        return K.make_effect(
            effect_id=effect_id,
            semvar_id="m17",
            property_name=prop,
            source_ref="doc:1#span:0-6",
            context_version="ctx-v1",
            proof_obligation=problem,
        )

    def test_composition_preserves_unresolved_semantic_effect(self):
        effect = self.effect()
        source = K.make_value("Margin increased.", context_version="ctx-v1", effects=[effect])
        derived = K.compose_value("The reported margin increased.", inputs=[source])
        self.assertEqual(K.active_effect_ids(derived), [effect["effect_id"]])

    def test_material_slice_activates_only_goal_relevant_property(self):
        effects = [
            self.effect("E-profit", "profit_related(m17)"),
            self.effect("E-kind", "gross_vs_net(m17)"),
        ]
        value = K.make_value("x", context_version="ctx-v1", effects=effects)
        out = K.material_slice(value, required_properties=["profit_related(m17)"])
        self.assertEqual([x["effect_id"] for x in out], ["E-profit"])
        self.assertEqual(K.active_effect_ids(value), ["E-kind", "E-profit"])

    def test_declared_complete_ambiguity_flags_cannot_mint_formal_discharge(self):
        problem = ambiguity_problem(same_terminal_result=True)
        effect = self.effect(problem=problem)
        with self.assertRaises(K.SemanticEffectError):
            K.issue_discharge_certificate(
                effect,
                proof_kind="AMBIGUITY_TERMINALLY_IRRELEVANT_V1",
                proof_problem=problem,
            )

    def test_plain_identifiability_flags_cannot_discharge_exact_sense_binding(self):
        problem = identifiability_problem(unique_profit=True)
        effect = self.effect(
            "E-sense",
            "interpretation(m17)=profit-margin",
            problem,
        )
        with self.assertRaises(K.SemanticEffectError):
            K.issue_discharge_certificate(
                effect,
                proof_kind="IDENTIFIABILITY_UNIQUE_V1",
                proof_problem=problem,
            )

    def test_transport_verifier_detects_silent_effect_loss(self):
        effect = self.effect()
        incoming = K.make_value("x", context_version="ctx-v1", effects=[effect])
        laundered = K.make_value("y", context_version="ctx-v1", effects=[])
        verdict = K.verify_transport(inputs=[incoming], output=laundered)
        self.assertFalse(verdict["pass"])
        self.assertEqual(verdict["missing_effect_ids"], [effect["effect_id"]])

    def test_transport_accepts_propagated_effect(self):
        effect = self.effect()
        incoming = K.make_value("x", context_version="ctx-v1", effects=[effect])
        outgoing = K.compose_value("y", inputs=[incoming])
        verdict = K.verify_transport(inputs=[incoming], output=outgoing)
        self.assertTrue(verdict["pass"], verdict)


class SemanticEffectKernelExistenceTest(unittest.TestCase):
    def test_kernel_exists(self):
        self.assertIsNotNone(K, "semantic_effect_kernel_v1 is missing")


if __name__ == "__main__":
    unittest.main(verbosity=2)

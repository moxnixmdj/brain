"""The ``goal_text`` proposal binding type.

Some adapters take natural language as an *operand* rather than a value
extracted from it. ``objective_claim_operand_binding.bind`` takes ``objective``
and parses the explicit comparison out of it; ``generic_evidence_claim_relation``
takes ``spec`` the same way. Neither slot is a URL, a path, or an upstream
effect, so no existing binding type could express it -- and the binder fell
back to ``_bind_inputs``, which demands the value appear in the sentence it
already is. The result was that ``evidence.claim_spec.bind.explicit_comparison``
scored 28 on a goal that asked for exactly that, was dropped for an unbindable
``objective``, and the goal failed with NO_VERIFIED_CAPABILITY_MATCH.

These tests pin the real behaviour, including that the binding does not
weaken anything: the adapter still refuses a sentence that states no
comparison.
"""
import hashlib
import json
import os
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import canonical.runtime.goal_compiler as gc  # noqa: E402

RUNTIME = os.path.join(REPO_ROOT, "canonical", "runtime")
REGISTRY = os.path.join(RUNTIME, "BOUND_CAPABILITY_REGISTRY_V1.json")
EXPLICIT = "evidence.claim_spec.bind.explicit_comparison.stdlib"
GENERIC = "evidence.claim_relation.generic_units.stdlib"
PRODUCER = "source.evidence.extract.objective_grounded.stdlib"
EFFECT = "source.evidence.objective_grounded_units"


def _binder():
    return gc._load_sibling_runtime_module(
        "capability_proposal_generators.py",
        "project_brain_direct_compiler_proposal_binder",
    )


def _registry():
    with open(REGISTRY, "r", encoding="utf-8") as handle:
        return json.load(handle)["capabilities"]


def _bind(binder, goal, cid, entry, providers):
    instance = "test-" + hashlib.sha256(
        (cid + "\n" + goal).encode("utf-8")
    ).hexdigest()[:16]
    return binder._bind_planned_inputs(
        goal, REPO_ROOT, sys.modules["canonical.runtime.goal_compiler"],
        instance, cid, entry, providers,
    )


class GoalTextBindingTests(unittest.TestCase):
    """The declared binding resolves, and only where it is declared."""

    def setUp(self):
        self.registry = _registry()
        self.binder = _binder()
        self.providers = gc._effect_providers(self.registry)

    def test_the_type_is_declared_on_exactly_the_two_adapters_that_take_language(self):
        for cid, slot in ((EXPLICIT, "objective"), (GENERIC, "spec")):
            bindings = self.registry[cid].get("proposal_bindings") or {}
            self.assertEqual(
                (bindings.get(slot) or {}).get("type"), "goal_text",
                f"{cid}.{slot} must be a goal_text binding",
            )

    def test_no_other_capability_declares_the_type(self):
        """A new binding type must not spread by accident.

        ``goal_text`` binds a slot to the whole sentence. That is only correct
        for an adapter that parses language itself. If it appeared elsewhere it
        would be a silent way to satisfy any declared input, so it is pinned to
        the two entries that need it.
        """
        declared = []
        for cid, entry in sorted(self.registry.items()):
            for slot, spec in ((entry or {}).get("proposal_bindings") or {}).items():
                if isinstance(spec, dict) and spec.get("type") == "goal_text":
                    declared.append((cid, slot))
        self.assertEqual(
            declared,
            sorted([(EXPLICIT, "objective"), (GENERIC, "spec")]),
            "goal_text leaked onto an entry that does not parse language",
        )

    def test_the_bound_value_is_the_goal_sentence_verbatim(self):
        goal = "Bind evidence claims to an explicit comparison."
        inputs, evidence = _bind(
            self.binder, goal, EXPLICIT, self.registry[EXPLICIT], self.providers
        )
        self.assertEqual(inputs["objective"], goal)
        self.assertEqual(evidence["objective"]["type"], "goal_text")
        self.assertEqual(evidence["objective"]["value"], goal)

    def test_the_upstream_effect_slot_still_resolves_through_the_producer(self):
        """The point of the change is the chain, not the one slot.

        ``extraction_path`` is an ``effect_result`` slot. It must still resolve
        to the producer that declares the effect -- otherwise goal_text would be
        masking a broken chain rather than completing one.
        """
        goal = "Bind evidence claims to an explicit comparison."
        inputs, _ = _bind(
            self.binder, goal, EXPLICIT, self.registry[EXPLICIT], self.providers
        )
        resolved = inputs["extraction_path"]
        self.assertIsInstance(resolved, dict, "effect slot did not resolve to a reference")
        effect = resolved.get("$effect_result") or {}
        self.assertEqual(effect.get("effect"), EFFECT)
        self.assertEqual(effect.get("field"), "output_path")
        self.assertEqual(self.providers.get(EFFECT, (None, None))[0], PRODUCER)

    def test_the_generic_units_consumer_binds_its_own_language_slot(self):
        goal = "Bind evidence claims to an explicit comparison."
        inputs, evidence = _bind(
            self.binder, goal, GENERIC, self.registry[GENERIC], self.providers
        )
        self.assertEqual(inputs["spec"], goal)
        self.assertEqual(evidence["spec"]["type"], "goal_text")


class GoalTextBindingNegativeControls(unittest.TestCase):
    """The binding must be able to fail, and must not weaken the adapter."""

    def setUp(self):
        self.registry = _registry()
        self.binder = _binder()
        self.providers = gc._effect_providers(self.registry)

    def test_an_empty_goal_is_refused_rather_than_bound_to_an_empty_string(self):
        """NEGATIVE CONTROL: a blank sentence must not silently satisfy the slot.

        An empty objective would reach the adapter as "" and be indistinguishable
        from a capability that simply had nothing to work on. Refusing at the
        binder keeps the reason honest.
        """
        entry = json.loads(json.dumps(self.registry[EXPLICIT]))
        with self.assertRaises(Exception) as caught:
            _bind(self.binder, "", EXPLICIT, entry, self.providers)
        self.assertIn("PROPOSAL_GOAL_TEXT_BINDING_REQUIRED", str(caught.exception))

    def test_a_whitespace_only_goal_is_refused(self):
        entry = json.loads(json.dumps(self.registry[EXPLICIT]))
        with self.assertRaises(Exception) as caught:
            _bind(self.binder, "   \n\t ", EXPLICIT, entry, self.providers)
        self.assertIn("PROPOSAL_GOAL_TEXT_BINDING_REQUIRED", str(caught.exception))

    def test_declaring_the_slot_on_an_entry_that_lacks_it_is_refused(self):
        """NEGATIVE CONTROL: goal_text is not a way to invent an input.

        ``generic_units`` has no ``objective`` slot. Declaring one must fail with
        the unknown-input error rather than inject an argument the adapter never
        reads.
        """
        entry = json.loads(json.dumps(self.registry[GENERIC]))
        bindings = dict(entry["proposal_bindings"])
        bindings["objective"] = {"type": "goal_text"}
        entry["proposal_bindings"] = bindings
        with self.assertRaises(Exception) as caught:
            _bind(
                self.binder,
                "Bind evidence claims to an explicit comparison.",
                GENERIC, entry, self.providers,
            )
        self.assertIn("PROPOSAL_BINDING_UNKNOWN_INPUT", str(caught.exception))

    def test_the_adapter_still_refuses_a_sentence_that_states_no_comparison(self):
        """NEGATIVE CONTROL: binding the sentence is not accepting the claim.

        This is the whole safety argument for the type. The binder hands the
        adapter the sentence; the adapter is still the one that decides whether
        an explicit comparison was stated. A sentence with none must come back
        refused, not bound.
        """
        sys.path.insert(0, os.path.join(REPO_ROOT, "canonical", "runtime",
                                        "bound_capabilities"))
        try:
            import objective_claim_operand_binding as binding
        finally:
            sys.path.pop(0)
        result = binding.bind("Bind evidence claims to an explicit comparison.", [])
        self.assertEqual(result.get("status"), "UNBOUND")
        self.assertTrue(result.get("reason"), "no reason returned for an unstated comparison")
        # The refusal must come from _parse_objective, which runs BEFORE
        # _validated_units. If it had reached unit validation instead, the
        # empty extraction would have raised EXTRACTION_REQUIRED and this test
        # would have proved nothing about the sentence at all.
        self.assertNotEqual(result.get("reason"), "OBJECTIVE_REQUIRED")
        self.assertNotIn("EXTRACTION", str(result.get("reason")))

    def test_a_comparison_that_is_stated_is_accepted_by_the_same_adapter(self):
        """The control is only meaningful if the positive case passes.

        Same adapter, same code path, a sentence that does state a comparison.
        If both sentences were refused the negative control above would prove
        nothing.
        """
        sys.path.insert(0, os.path.join(REPO_ROOT, "canonical", "runtime",
                                        "bound_capabilities"))
        try:
            import objective_claim_operand_binding as binding
        finally:
            sys.path.pop(0)
        extraction = {
            "schema": "PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
            "status": "OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
            "output_verified": True,
            "evidence_units": [{
                "evidence_unit_id": "a" * 64,
                "text": "the measured pass rate is 95 percent",
            }],
        }
        result = binding.bind(
            "The measured pass rate is greater than 90 percent.", extraction
        )
        # Past _parse_objective: the sentence DID state a comparison, so the
        # parse produced a parsed_objective rather than a refusal reason.
        self.assertIsNotNone(
            result.get("parsed_objective"),
            f"the stated comparison was not parsed: {result.get('reason')}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

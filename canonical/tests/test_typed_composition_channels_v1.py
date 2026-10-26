"""Typed composition channels, phase B: named endpoints, never silent overwrite.

Composition used to route prior artifacts through stores keyed by the bare
effect string with a single slot per name: ``providers[effect] = endpoint``
overwrote whatever was there first. Six declared effects have more than one
provider in the registry, so the winner was whichever producer registered
last (in-plan stores) or first alphabetically (the global provider census) --
and the proposal layer and the direct-compiler layer did not even agree on
which law of silent collapse they ran.

Phase B keeps the endpoint of an untyped consumer byte-identical to the old
law: with no ``where`` predicate the selected channel is the one the
overwrite winner would have been (most recent upstream producer). What
changes is everything else:

- every producer of an effect publishes an endpoint, in plan order; nothing
  is silently overwritten;
- a binding spec may add ``"where": {"provider": <id>|[ids]}`` to name which
  producer of a multi-producer effect it consumes;
- a predicate that still matches two channels fails closed with
  CAPABILITY_CHANNEL_AMBIGUOUS instead of silently picking one;
- an unknown ``where`` shape fails closed with CAPABILITY_CHANNEL_INVALID --
  a predicate the binder cannot evaluate must never degrade into a pick.

These tests pin the law at all three layers that carry channels:
the planner (``capability_planner``), the proposal binder
(``capability_proposal_generators``), and the direct compiler
(``goal_compiler``).
"""
import hashlib
import json
import os
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import importlib.util  # noqa: E402
import pathlib  # noqa: E402

PLANNER_PATH = pathlib.Path(REPO_ROOT) / "canonical" / "runtime" / "capability_planner.py"
_spec = importlib.util.spec_from_file_location(
    "capability_planner_channels_test", PLANNER_PATH
)
planner = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = planner
_spec.loader.exec_module(planner)

import canonical.runtime.goal_compiler as gc  # noqa: E402

EFFECT = "test.channel.effect"


def _producer(cid):
    return {
        "id": cid,
        "provides": [EFFECT],
        "requires": ["test.channel.seed"],
        "result_fields": ["output_path"],
        "cost": 10,
        "action": {"type": "invoke_capability", "args": {"capability_id": cid}},
    }


def _consumer(cid, where=None):
    spec = {"effect": EFFECT, "field": "output_path"}
    if where is not None:
        spec["where"] = where
    return {
        "id": cid,
        "requires": ["test.channel.seed", EFFECT],
        "provides": ["test.channel.done"],
        "result_fields": ["output_path"],
        "cost": 10,
        "action": {
            "type": "invoke_capability",
            "args": {
                "capability_id": cid,
                "input_path": {"$effect_result": spec},
            },
        },
    }


def _problem(consumer):
    return {
        "initial_facts": ["test.channel.seed"],
        "target_effects": ["test.channel.done"],
        "capabilities": [
            _producer("channel.producer.alpha"),
            _producer("channel.producer.beta"),
            consumer,
        ],
        "finish_summary": "DONE",
    }


class PlannerChannelTests(unittest.TestCase):
    """The planner layer: ordered endpoints, predicate selection, fail-closed."""

    def _resolved_cycle(self, consumer):
        result = planner.plan_actions(_problem(consumer))
        ref = result["actions"][-2]["args"]["input_path"]
        self.assertEqual(set(ref), {"$result"})
        return ref["$result"]["cycle"]

    def _store_with(self, *ids):
        store = {}
        for cycle, cid in enumerate(ids):
            cap = planner._normalize(
                {"initial_facts": [], "target_effects": [EFFECT],
                 "capabilities": [_producer(cid)], "t": 1}
            )[2][0]
            planner._append_channel(store, EFFECT, (cycle, cap))
        return store

    def _consumer_cap(self, where=None):
        return planner._normalize(
            {"initial_facts": [], "target_effects": ["test.channel.done"],
             "capabilities": [_consumer("c", where)], "t": 1}
        )[2][0]

    def test_without_a_predicate_the_last_registered_producer_wins(self):
        """DEFAULT = the historical overwrite winner, byte-identical."""
        store = self._store_with("channel.producer.alpha", "channel.producer.beta")
        out = planner._resolve_effect_bindings(
            {"$effect_result": {"effect": EFFECT, "field": "output_path"}},
            self._consumer_cap(), store,
        )
        # beta registered second: the old overwrite law's winner.
        self.assertEqual(out, {"$result": {"cycle": 1, "field": "output_path"}})

    def test_a_provider_predicate_selects_the_earlier_channel(self):
        """Where both producers exist, the sentence targets the early one."""
        cycle = self._resolved_cycle(
            _consumer("channel.consumer.named", {"provider": "channel.producer.alpha"})
        )
        plan = [row["capability_id"] for row in planner.plan_actions(
            _problem(_consumer("x")))["composition_contract"]]
        self.assertEqual(
            cycle, plan.index("channel.producer.alpha")
        )

    def test_a_predicate_naming_no_channel_is_the_existing_missing_refusal(self):
        with self.assertRaises(planner.PlanningFailure) as caught:
            self._resolved_cycle(
                _consumer("channel.consumer.ghost", {"provider": "channel.producer.ghost"})
            )
        self.assertIn("BINDING_PROVIDER_MISSING", str(caught.exception))

    def test_a_predicate_that_still_matches_two_channels_fails_closed(self):
        # Two endpoints that BOTH carry an allowed id: naming a set that does
        # not disambiguate is not a pick, it is a refusal.
        store = self._store_with("p.alpha", "p.beta")
        consumer = self._consumer_cap()
        with self.assertRaises(planner.PlanningFailure) as caught:
            planner._resolve_effect_bindings(
                {"$effect_result": {
                    "effect": EFFECT, "field": "output_path",
                    "where": {"provider": ["p.alpha", "p.beta"]},
                }},
                consumer, store,
            )
        self.assertIn("CAPABILITY_CHANNEL_AMBIGUOUS", str(caught.exception))

    def test_an_unknown_predicate_shape_fails_closed(self):
        with self.assertRaises(planner.PlanningFailure) as caught:
            planner.plan_actions(
                _problem(_consumer("c", {"format": "json-text"}))
            )
        self.assertIn("CAPABILITY_CHANNEL_INVALID", str(caught.exception))

    def test_legacy_single_endpoint_stores_still_read(self):
        """The overwrite-era map shape keeps working for every old caller."""
        alpha = planner._normalize(
            {"initial_facts": [], "target_effects": [EFFECT], "capabilities": [_producer("p.alpha")]}
        )[2][0]
        out = planner._resolve_effect_bindings(
            {"$effect_result": {"effect": EFFECT, "field": "output_path"}},
            self._consumer_cap(), {EFFECT: (3, alpha)},
        )
        self.assertEqual(out, {"$result": {"cycle": 3, "field": "output_path"}})


class ProposalBinderChannelTests(unittest.TestCase):
    """The proposal binder selects channels by the same law."""

    def setUp(self):
        self.binder = gc._load_sibling_runtime_module(
            "capability_proposal_generators.py",
            "project_brain_channels_test_binder",
        )

    def _consumer_entry(self, where):
        spec = {
            "type": "effect_result",
            "container": "scalar",
            "effect": EFFECT,
            "field": "output_path",
        }
        if where is not None:
            spec["where"] = where
        return {
            "requires": [EFFECT, "test.channel.seed"],
            "proposal_bindings": {"json_path": spec},
            "action_template": {
                "type": "invoke_capability",
                "args": {
                    "capability_id": "channel.consumer",
                    "input_path": "${input.json_path}",
                },
            },
        }

    def _providers(self):
        alpha = _producer("x")
        beta = _producer("y")
        return {EFFECT: [("inst-alpha", alpha, "channel.producer.alpha"),
                         ("inst-beta", beta, "channel.producer.beta")]}

    def _bind(self, entry, providers):
        instance = "test-" + hashlib.sha256(b"channel").hexdigest()[:16]
        return self.binder._bind_planned_inputs(
            "convert " + EFFECT, REPO_ROOT,
            sys.modules["canonical.runtime.goal_compiler"],
            instance, "channel.consumer", entry, providers,
        )

    def test_the_binder_selects_the_named_channel_endpooint(self):
        inputs, evidence = self._bind(
            self._consumer_entry({"provider": "channel.producer.alpha"}),
            self._providers(),
        )
        ref = inputs["json_path"]["$effect_result"]
        self.assertEqual(ref["where"], {"provider": "channel.producer.alpha"})
        self.assertEqual(evidence["json_path"]["provider"], "inst-alpha")
        self.assertEqual(evidence["json_path"]["channel_candidates"], [2])

    def test_the_binder_keeps_last_registered_as_default(self):
        inputs, evidence = self._bind(self._consumer_entry(None), self._providers())
        self.assertNotIn("where", inputs["json_path"]["$effect_result"])
        self.assertEqual(evidence["json_path"]["provider"], "inst-beta")

    def test_the_binder_fails_closed_on_ambiguity_under_a_predicate(self):
        with self.assertRaises(Exception) as caught:
            self._bind(
                self._consumer_entry(
                    {"provider": ["channel.producer.alpha", "channel.producer.beta"]}
                ),
                self._providers(),
            )
        self.assertIn("CAPABILITY_CHANNEL_AMBIGUOUS", str(caught.exception))

    def test_the_binder_fails_closed_on_an_unknown_predicate_shape(self):
        with self.assertRaises(Exception) as caught:
            self._bind(self._consumer_entry({"weight": 2}), self._providers())
        self.assertIn("CAPABILITY_CHANNEL_INVALID", str(caught.exception))

    def test_the_binder_reads_legacy_single_endpoint_stores(self):
        alpha = _producer("x")
        _, evidence = self._bind(
            self._consumer_entry(None), {EFFECT: ("inst-alpha", alpha)}
        )
        self.assertEqual(evidence["json_path"]["provider"], "inst-alpha")


class CompilerChannelTests(unittest.TestCase):
    """The direct compiler carries the predicate through to producer attach."""

    def test_producer_binding_regeneration_keeps_the_predicate(self):
        entry = {
            "provides": [EFFECT],
            "requires": ["test.channel.seed"],
            "result_fields": ["output_path"],
            "proposal_bindings": {
                "json_path": {
                    "type": "effect_result",
                    "effect": "test.upstream",
                    "field": "output_path",
                    "where": {"provider": "upstream.chosen"},
                }
            },
            "action_template": {
                "type": "invoke_capability",
                "args": {
                    "capability_id": "channel.producer",
                    "input_path": "${input.json_path}",
                    "output_path": "${input.output_path}",
                },
            },
        }
        inputs = gc._bind_producer_inputs(
            "make a thing and store it at stated_out.json",
            REPO_ROOT, "channel.producer", entry,
        )
        self.assertIsNotNone(inputs)
        ref = inputs["json_path"]["$effect_result"]
        self.assertEqual(ref["where"], {"provider": "upstream.chosen"})

    def test_cycle_dedupe_is_scoped_by_the_channel_discriminator(self):
        """Two predicates on one effect are two channels; equal ones dedupe."""
        registry_entries = {
            "upstream.chosen": {
                "provides": ["test.upstream"],
                "requires": ["test.channel.seed"],
                "result_fields": ["output_path"],
                "action_template": {
                    "type": "invoke_capability",
                    "args": {"capability_id": "upstream.chosen",
                             "output_path": "${input.output_path}"},
                },
            },
            "upstream.other": {
                "provides": ["st.never"],
                "requires": ["test.channel.seed"],
                "result_fields": ["output_path"],
                "action_template": {
                    "type": "invoke_capability",
                    "args": {"capability_id": "upstream.other",
                             "output_path": "${input.output_path}"},
                },
            },
        }
        providers = {"test.upstream": [("upstream.chosen", registry_entries["upstream.chosen"])]}
        parts, actions, cycle_by_ref = [], [], {}
        refs = [
            {"effect": "test.upstream", "field": "output_path",
             "where": {"provider": "upstream.chosen"}},
            {"effect": "test.upstream", "field": "output_path",
             "where": {"provider": "upstream.chosen"}},
        ]
        ok = gc._append_producer_parts(
            refs, "stated_out.json goal", registry_entries, REPO_ROOT,
            providers, parts, actions, cycle_by_ref, depth=3,
        )
        self.assertTrue(ok)
        # Equal predicates on one effect resolved to ONE producer step.
        self.assertEqual(len(parts), 1)

    def test_ambiguous_channel_under_a_predicate_fails_closed(self):
        alpha = _producer("x")
        beta = _producer("y")
        providers = {
            "test.upstream": [("upstream.a", alpha), ("upstream.b", beta)]
        }
        with self.assertRaises(Exception) as caught:
            gc._append_producer_parts(
                [{"effect": "test.upstream", "field": "output_path",
                  "where": {"provider": ["upstream.a", "upstream.b"]}}],
                "goal", {}, REPO_ROOT, providers, [], [], {}, depth=3,
            )
        self.assertIn("CAPABILITY_CHANNEL_AMBIGUOUS", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

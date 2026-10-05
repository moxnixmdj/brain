from __future__ import annotations

import unittest

from canonical.runtime.shared_channel_dominator_v1 import verify


def base_spec():
    return {
        "nodes": ["entry", "guard", "planner", "sink", "state_guard", "state_use"],
        "entrypoints": ["entry"],
        "edges": [
            {"id": "e0", "source": "entry", "target": "guard"},
            {"id": "e1", "source": "guard", "target": "planner"},
            {"id": "effect", "source": "planner", "target": "sink"},
            {"id": "s0", "source": "entry", "target": "state_guard"},
            {"id": "state", "source": "state_guard", "target": "state_use"},
        ],
        "mediator_bindings": {
            "effect": "guard",
            "state": "state_guard",
        },
        "dynamic_edge_registry_complete": True,
    }


class SharedChannelDominatorTests(unittest.TestCase):
    def test_two_mediators_pass(self):
        out = verify(base_spec())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["bound_load_bearing_edge_count"], 2)

    def test_direct_effect_bypass_fails(self):
        spec = base_spec()
        spec["edges"].append({"id": "bypass", "source": "entry", "target": "planner"})
        out = verify(spec)
        self.assertFalse(out["pass"])
        self.assertIn("effect", out["bypass_edge_ids"])

    def test_direct_state_bypass_fails(self):
        spec = base_spec()
        spec["edges"].append({"id": "state_bypass", "source": "entry", "target": "state_use"})
        # A bypass to the target node does not affect the bound edge itself. Bind
        # the bypass edge too, because every load-bearing transfer must be bound.
        spec["mediator_bindings"]["state_bypass"] = "state_guard"
        out = verify(spec)
        self.assertFalse(out["pass"])
        self.assertIn("state_bypass", out["bypass_edge_ids"])

    def test_mediator_as_edge_source_passes(self):
        spec = base_spec()
        spec["mediator_bindings"] = {"e1": "guard"}
        out = verify(spec)
        self.assertTrue(out["pass"], out)

    def test_incomplete_dynamic_registry_fails_closed(self):
        spec = base_spec()
        spec["dynamic_edge_registry_complete"] = False
        out = verify(spec)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "DYNAMIC_EDGE_REGISTRY_NOT_PROVED_COMPLETE")

    def test_unknown_bound_edge_fails_closed(self):
        spec = base_spec()
        spec["mediator_bindings"]["missing"] = "guard"
        out = verify(spec)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "BOUND_EDGE_NOT_DECLARED")

    def test_unknown_mediator_fails_closed(self):
        spec = base_spec()
        spec["mediator_bindings"]["effect"] = "ghost"
        out = verify(spec)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "MEDIATOR_NOT_IN_NODES")

    def test_multiple_entrypoints_detect_bypass(self):
        spec = base_spec()
        spec["nodes"].append("alternate")
        spec["entrypoints"].append("alternate")
        spec["edges"].append({"id": "alt", "source": "alternate", "target": "planner"})
        out = verify(spec)
        self.assertFalse(out["pass"])
        self.assertIn("effect", out["bypass_edge_ids"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

from __future__ import annotations

import copy
import unittest

from canonical.runtime.root3_channel_dominator_verifier_v1 import evaluate


def base_manifest() -> dict:
    return {
        "source_blobs": [
            {
                "path": "canonical/runtime/example.py",
                "git_blob_sha": "1" * 40,
            }
        ],
        "entrypoints": ["ENTRY"],
        "nodes": [
            {"id": "ENTRY", "kind": "RUNTIME_ENTRYPOINT"},
            {"id": "CTRL", "kind": "CONTROL"},
            {"id": "AUTH", "kind": "MATERIAL_EFFECT_MEDIATOR"},
            {"id": "SINK", "kind": "MATERIAL_EFFECT_SINK"},
        ],
        "edges": [
            {"id": "e1", "from": "ENTRY", "to": "CTRL", "dynamic": False},
            {"id": "e2", "from": "CTRL", "to": "AUTH", "dynamic": False},
            {"id": "e3", "from": "AUTH", "to": "SINK", "dynamic": False},
        ],
        "mediator_bindings": [
            {
                "sink_id": "SINK",
                "required_mediator_id": "AUTH",
                "mediator_class": "AUTHORITY_GUARD",
                "predicate_ids": ["IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS"],
            }
        ],
        "dynamic_edge_registry_complete": True,
        "unknown_dynamic_edges": [],
        "unclassified_load_bearing_channels": [],
    }


class Root3ChannelDominatorVerifierTests(unittest.TestCase):
    def test_linear_guard_dominates_sink(self):
        out = evaluate(base_manifest())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["load_bearing_sink_count"], 1)
        self.assertEqual(out["mediator_binding_count"], 1)

    def test_direct_bypass_is_witnessed(self):
        m = base_manifest()
        m["edges"].append(
            {"id": "bypass", "from": "CTRL", "to": "SINK", "dynamic": False}
        )
        out = evaluate(m)
        self.assertFalse(out["pass"])
        self.assertIn("MEDIATOR_BYPASS:SINK:AUTH", out["errors"])
        self.assertEqual(
            out["bypasses"][0]["bypass_path"],
            ["ENTRY", "CTRL", "SINK"],
        )

    def test_second_entrypoint_bypass_is_caught(self):
        m = base_manifest()
        m["nodes"].append({"id": "ALT", "kind": "RUNTIME_ENTRYPOINT"})
        m["entrypoints"].append("ALT")
        m["edges"].append(
            {"id": "alt", "from": "ALT", "to": "SINK", "dynamic": True}
        )
        out = evaluate(m)
        self.assertFalse(out["pass"])
        self.assertIn("MEDIATOR_BYPASS:SINK:AUTH", out["errors"])

    def test_unknown_dynamic_edge_fails_closed(self):
        m = base_manifest()
        m["unknown_dynamic_edges"] = ["plugin:opaque-dispatch"]
        out = evaluate(m)
        self.assertFalse(out["pass"])
        self.assertIn(
            "UNKNOWN_DYNAMIC_EDGE:plugin:opaque-dispatch",
            out["errors"],
        )

    def test_incomplete_dynamic_registry_fails_closed(self):
        m = base_manifest()
        m["dynamic_edge_registry_complete"] = False
        out = evaluate(m)
        self.assertFalse(out["pass"])
        self.assertIn("DYNAMIC_EDGE_REGISTRY_NOT_COMPLETE", out["errors"])

    def test_unbound_load_bearing_sink_fails_closed(self):
        m = base_manifest()
        m["mediator_bindings"] = []
        out = evaluate(m)
        self.assertFalse(out["pass"])
        self.assertIn("LOAD_BEARING_SINK_UNBOUND:SINK", out["errors"])

    def test_shared_state_and_effect_graph_passes(self):
        m = base_manifest()
        m["nodes"].extend(
            [
                {"id": "CAPSULE", "kind": "STATE_OR_EVIDENCE_MEDIATOR"},
                {
                    "id": "STATE_USE",
                    "kind": "CROSS_ROLE_STATE_OR_EVIDENCE_USE",
                },
            ]
        )
        m["edges"].extend(
            [
                {"id": "s1", "from": "CTRL", "to": "CAPSULE", "dynamic": False},
                {"id": "s2", "from": "CAPSULE", "to": "STATE_USE", "dynamic": False},
            ]
        )
        m["mediator_bindings"].append(
            {
                "sink_id": "STATE_USE",
                "required_mediator_id": "CAPSULE",
                "mediator_class": "STATE_CAPSULE",
                "predicate_ids": [
                    "COMPOSITION_COMPONENT_SCOPED_PROOFS",
                    "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
                ],
            }
        )
        out = evaluate(m)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["load_bearing_sink_count"], 2)

    def test_wrong_mediator_kind_fails_closed(self):
        m = base_manifest()
        m["mediator_bindings"][0]["mediator_class"] = "STATE_CAPSULE"
        out = evaluate(m)
        self.assertFalse(out["pass"])
        self.assertIn(
            "STATE_CAPSULE_MEDIATOR_KIND_INVALID:SINK",
            out["errors"],
        )

    def test_source_blob_drift_changes_graph_digest(self):
        a = evaluate(base_manifest())
        m = base_manifest()
        m["source_blobs"][0]["git_blob_sha"] = "2" * 40
        b = evaluate(m)
        self.assertNotEqual(
            a["graph_manifest_sha256"],
            b["graph_manifest_sha256"],
        )

    def test_declared_digest_mismatch_fails_closed(self):
        m = base_manifest()
        m["expected_graph_manifest_sha256"] = "0" * 64
        out = evaluate(m)
        self.assertFalse(out["pass"])
        self.assertIn("GRAPH_MANIFEST_DIGEST_MISMATCH", out["errors"])

    def test_cycle_does_not_break_dominator_check(self):
        m = base_manifest()
        m["edges"].append(
            {"id": "loop", "from": "AUTH", "to": "CTRL", "dynamic": False}
        )
        out = evaluate(m)
        self.assertTrue(out["pass"], out)


if __name__ == "__main__":
    unittest.main(verbosity=2)

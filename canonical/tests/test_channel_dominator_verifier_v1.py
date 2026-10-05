from __future__ import annotations

import copy
import unittest

from canonical.runtime.channel_dominator_verifier_v1 import (
    SCHEMA,
    verify_channel_graph,
)


SHA_A = "0" * 40
SHA_B = "1" * 40


def base():
    return {
        "schema": SCHEMA,
        "source_bindings": [
            {"path": "canonical/runtime/astra_runtime.py", "git_blob_sha": SHA_A},
        ],
        "channel_totality_receipt": {
            "path": "canonical/verification/channel-totality.json",
            "git_blob_sha": SHA_B,
            "scope_complete": True,
            "static_edges_complete": True,
            "dynamic_edges_complete": True,
            "independent_or_objective": True,
        },
        "nodes": [
            "ENTRY",
            "PLAN",
            "AUTH_GUARD",
            "CAPSULE_PROJECT",
            "CAPSULE_APPEND",
            "ACTION",
            "STATE_READ",
            "STATE_WRITE",
            "EFFECT",
        ],
        "entrypoints": ["ENTRY"],
        "mediators": [
            {"node": "AUTH_GUARD", "class": "AUTHORITY_GUARD"},
            {"node": "CAPSULE_PROJECT", "class": "STATE_CAPSULE_PROJECT"},
            {"node": "CAPSULE_APPEND", "class": "STATE_CAPSULE_APPEND"},
        ],
        "edges": [
            {"id": "e0", "from": "ENTRY", "to": "PLAN", "kind": "CONTROL", "load_bearing": False, "required_mediators": []},
            {"id": "e1", "from": "PLAN", "to": "AUTH_GUARD", "kind": "CONTROL", "load_bearing": False, "required_mediators": []},
            {"id": "e2", "from": "AUTH_GUARD", "to": "CAPSULE_PROJECT", "kind": "CONTROL", "load_bearing": False, "required_mediators": []},
            {"id": "e3", "from": "CAPSULE_PROJECT", "to": "ACTION", "kind": "STATE_TRANSFER", "load_bearing": False, "required_mediators": []},
            {"id": "e4", "from": "ACTION", "to": "STATE_READ", "kind": "CROSS_ROLE_STATE_READ", "load_bearing": True, "required_mediators": ["CAPSULE_PROJECT"]},
            {"id": "e5", "from": "ACTION", "to": "CAPSULE_APPEND", "kind": "CONTROL", "load_bearing": False, "required_mediators": []},
            {"id": "e6", "from": "CAPSULE_APPEND", "to": "STATE_WRITE", "kind": "CROSS_ROLE_STATE_WRITE", "load_bearing": True, "required_mediators": ["CAPSULE_APPEND"]},
            {"id": "e7", "from": "ACTION", "to": "EFFECT", "kind": "MATERIAL_EFFECT", "load_bearing": True, "required_mediators": ["AUTH_GUARD"]},
        ],
        "dynamic_sites": [
            {
                "id": "dyn0",
                "status": "REGISTERED",
                "source_ref": "astra_runtime.py:_goal_action",
                "registered_edge_ids": ["e7"],
            }
        ],
    }


class Tests(unittest.TestCase):
    def test_passes_when_every_reachable_load_bearing_edge_is_dominated(self):
        verdict = verify_channel_graph(base())
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertEqual(verdict["reachable_load_bearing_edge_count"], 3)

    def test_fails_on_authority_guard_bypass(self):
        cert = base()
        cert["edges"].append(
            {
                "id": "bypass",
                "from": "PLAN",
                "to": "ACTION",
                "kind": "CONTROL",
                "load_bearing": False,
                "required_mediators": [],
            }
        )
        verdict = verify_channel_graph(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("MEDIATOR_BYPASS:e7:AUTH_GUARD", verdict["reason"])

    def test_fails_on_state_capsule_bypass(self):
        cert = base()
        cert["edges"].append(
            {
                "id": "state-bypass",
                "from": "PLAN",
                "to": "ACTION",
                "kind": "CONTROL",
                "load_bearing": False,
                "required_mediators": [],
            }
        )
        verdict = verify_channel_graph(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("MEDIATOR_BYPASS:e4:CAPSULE_PROJECT", verdict["reason"])

    def test_fails_closed_on_unregistered_dynamic_site(self):
        cert = base()
        cert["dynamic_sites"][0]["status"] = "UNKNOWN"
        verdict = verify_channel_graph(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("DYNAMIC_SITE_NOT_REGISTERED", verdict["reason"])

    def test_fails_closed_on_dynamic_edge_not_in_graph(self):
        cert = base()
        cert["dynamic_sites"][0]["registered_edge_ids"] = ["missing"]
        verdict = verify_channel_graph(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("DYNAMIC_SITE_UNKNOWN_EDGE", verdict["reason"])

    def test_fails_closed_on_load_bearing_edge_without_mediator(self):
        cert = base()
        cert["edges"][4]["required_mediators"] = []
        verdict = verify_channel_graph(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("LOAD_BEARING_EDGE_UNMEDIATED", verdict["reason"])

    def test_fails_closed_if_totality_receipt_is_not_scope_complete(self):
        cert = base()
        cert["channel_totality_receipt"]["scope_complete"] = False
        verdict = verify_channel_graph(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("SCOPE_COMPLETE_NOT_TRUE", verdict["reason"])

    def test_multi_entry_requires_mediator_on_every_entry_path(self):
        cert = base()
        cert["nodes"].append("ENTRY2")
        cert["entrypoints"].append("ENTRY2")
        cert["edges"].append(
            {
                "id": "entry2-action",
                "from": "ENTRY2",
                "to": "ACTION",
                "kind": "CONTROL",
                "load_bearing": False,
                "required_mediators": [],
            }
        )
        verdict = verify_channel_graph(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("MEDIATOR_BYPASS", verdict["reason"])

    def test_cycle_does_not_confuse_dominator_fixpoint(self):
        cert = base()
        cert["edges"].append(
            {
                "id": "cycle",
                "from": "ACTION",
                "to": "PLAN",
                "kind": "CONTROL",
                "load_bearing": False,
                "required_mediators": [],
            }
        )
        verdict = verify_channel_graph(cert)
        self.assertEqual(verdict["status"], "PASS", verdict)

    def test_bad_source_sha_fails_before_graph_credit(self):
        cert = base()
        cert["source_bindings"][0]["git_blob_sha"] = "not-a-sha"
        verdict = verify_channel_graph(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("SOURCE_BINDING_0_SHA_INVALID", verdict["reason"])

    def test_undeclared_mediator_fails_closed(self):
        cert = base()
        cert["edges"][7]["required_mediators"] = ["MISSING_GUARD"]
        verdict = verify_channel_graph(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("EDGE_MEDIATOR_UNDECLARED", verdict["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

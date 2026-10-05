from __future__ import annotations

import copy
import unittest

from canonical.runtime.shared_channel_dominator_v1 import verify_channel_graph_certificate


def base_certificate():
    return {
        "schema": "PROJECT_BRAIN_SHARED_CHANNEL_DOMINATOR_CERT_V1",
        "nodes": [
            "ENTRY", "STATE_CAPSULE", "AUTHORITY_GUARD", "INVARIANT_GUARD",
            "STATE_USE", "EFFECT_SINK",
        ],
        "entry_nodes": ["ENTRY"],
        "scope_receipt": {
            "closed_world_channel_graph": True,
            "dynamic_edges_registered": True,
            "load_bearing_edges_total": True,
            "independent_or_objective": True,
        },
        "edges": [
            {"id":"entry_to_capsule","from":"ENTRY","to":"STATE_CAPSULE","load_bearing":False,"requirements":[]},
            {
                "id":"capsule_to_state_use","from":"STATE_CAPSULE","to":"STATE_USE","load_bearing":True,
                "requirements":[{
                    "mediator":"STATE_CAPSULE","mediator_class":"COMPOSITION_STATE_CAPSULE",
                    "predicate_ids":["COMPOSITION_P1","COMPOSITION_P2"],
                }],
            },
            {"id":"state_use_to_authority","from":"STATE_USE","to":"AUTHORITY_GUARD","load_bearing":False,"requirements":[]},
            {"id":"authority_to_invariant","from":"AUTHORITY_GUARD","to":"INVARIANT_GUARD","load_bearing":False,"requirements":[]},
            {
                "id":"invariant_to_effect","from":"INVARIANT_GUARD","to":"EFFECT_SINK","load_bearing":True,
                "requirements":[
                    {
                        "mediator":"AUTHORITY_GUARD","mediator_class":"AUTHORITY_GUARD",
                        "predicate_ids":["IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS"],
                    },
                    {
                        "mediator":"INVARIANT_GUARD","mediator_class":"COMPOSITION_INVARIANT_GUARD",
                        "predicate_ids":["COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES"],
                    },
                ],
            },
        ],
    }


class SharedChannelDominatorTests(unittest.TestCase):
    def test_shared_pass_covers_four_predicates(self):
        verdict=verify_channel_graph_certificate(base_certificate())
        self.assertEqual(verdict["status"],"PASS")
        self.assertEqual(set(verdict["predicate_coverage"]),{
            "COMPOSITION_P1","COMPOSITION_P2",
            "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
            "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
        })

    def test_direct_effect_bypass_fails(self):
        cert=base_certificate()
        cert["edges"].append({
            "id":"bypass","from":"ENTRY","to":"EFFECT_SINK","load_bearing":True,
            "requirements":[{
                "mediator":"AUTHORITY_GUARD","mediator_class":"AUTHORITY_GUARD",
                "predicate_ids":["IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS"],
            }],
        })
        verdict=verify_channel_graph_certificate(cert)
        self.assertEqual(verdict["status"],"FAIL_CLOSED")
        self.assertIn("BYPASS_PATH:bypass:AUTHORITY_GUARD",verdict["reason"])

    def test_second_entry_bypass_fails(self):
        cert=base_certificate()
        cert["nodes"].append("ALT_ENTRY")
        cert["entry_nodes"].append("ALT_ENTRY")
        cert["edges"].append({"id":"alt_to_invariant","from":"ALT_ENTRY","to":"INVARIANT_GUARD","load_bearing":False,"requirements":[]})
        verdict=verify_channel_graph_certificate(cert)
        self.assertEqual(verdict["status"],"FAIL_CLOSED")
        self.assertIn("BYPASS_PATH:invariant_to_effect:AUTHORITY_GUARD",verdict["reason"])

    def test_load_bearing_edge_must_be_classified(self):
        cert=base_certificate()
        cert["edges"][1]["requirements"]=[]
        verdict=verify_channel_graph_certificate(cert)
        self.assertEqual(verdict["status"],"FAIL_CLOSED")
        self.assertIn("LOAD_BEARING_EDGE_UNCLASSIFIED",verdict["reason"])

    def test_scope_totality_flag_required(self):
        cert=base_certificate()
        cert["scope_receipt"]["dynamic_edges_registered"]=False
        verdict=verify_channel_graph_certificate(cert)
        self.assertEqual(verdict["status"],"FAIL_CLOSED")
        self.assertIn("DYNAMIC_EDGES_REGISTERED_NOT_TRUE",verdict["reason"])

    def test_unknown_mediator_fails(self):
        cert=base_certificate()
        cert["edges"][1]["requirements"][0]["mediator"]="MISSING"
        verdict=verify_channel_graph_certificate(cert)
        self.assertEqual(verdict["status"],"FAIL_CLOSED")
        self.assertIn("UNKNOWN_MEDIATOR",verdict["reason"])

    def test_duplicate_edge_id_fails(self):
        cert=base_certificate()
        cert["edges"].append(copy.deepcopy(cert["edges"][0]))
        verdict=verify_channel_graph_certificate(cert)
        self.assertEqual(verdict["status"],"FAIL_CLOSED")
        self.assertIn("DUPLICATE_EDGE_ID",verdict["reason"])

    def test_mediator_equal_to_load_bearing_source_is_precommit(self):
        verdict=verify_channel_graph_certificate(base_certificate())
        self.assertEqual(verdict["status"],"PASS")
        self.assertTrue(verdict["shared_no_bypass_proved_for_declared_graph"])

    def test_non_load_bearing_edge_needs_no_mediator(self):
        cert=base_certificate()
        cert["nodes"].append("BOOKKEEPING")
        cert["edges"].append({"id":"bookkeeping","from":"ENTRY","to":"BOOKKEEPING","load_bearing":False,"requirements":[]})
        self.assertEqual(verify_channel_graph_certificate(cert)["status"],"PASS")

    def test_unreachable_classified_edge_is_reported_not_credited(self):
        cert=base_certificate()
        cert["nodes"].extend(["DEAD_MEDIATOR","DEAD_SINK"])
        cert["edges"].append({
            "id":"dead","from":"DEAD_MEDIATOR","to":"DEAD_SINK","load_bearing":True,
            "requirements":[{
                "mediator":"DEAD_MEDIATOR","mediator_class":"DEAD_CLASS",
                "predicate_ids":["DEAD_PREDICATE"],
            }],
        })
        verdict=verify_channel_graph_certificate(cert)
        self.assertEqual(verdict["status"],"PASS")
        self.assertEqual(verdict["unreachable_load_bearing_edge_ids"],["dead"])
        self.assertNotIn("DEAD_PREDICATE",verdict["predicate_coverage"])


if __name__=="__main__":
    unittest.main(verbosity=2)

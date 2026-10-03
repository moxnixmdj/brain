from __future__ import annotations

import copy
import itertools
import unittest

from canonical.runtime.tool_discovery_common_authority_interface_v1 import (
    build_complete_interface,
    tool_invocable,
    validate_complete_interface,
)


def authority(n=4):
    return [
        {
            "tool_id": f"T{i}",
            "cost": float(n-i),
            "available": True,
            "authorized": True,
            "epoch": 0,
            "meta": {"provider": f"P{i%2}", "region": "X"},
            "capabilities": {"CAP_A": bool(i % 2), "CAP_B": bool((i+1) % 2)},
        }
        for i in range(n)
    ]


class ToolDiscoveryCommonAuthorityInterfaceV1Tests(unittest.TestCase):
    def test_arbitrary_finite_partition_is_exact_complete_and_capability_hidden(self):
        for n in range(1, 8):
            rows = authority(n)
            for source_count in range(1, n + 3):
                interface = build_complete_interface(
                    rows,
                    source_count=source_count,
                    initially_visible_ids=["T0"] if n else [],
                )
                verdict = validate_complete_interface(interface)
                self.assertTrue(verdict["valid"], verdict)
                self.assertEqual(
                    verdict["common_authority_ids"],
                    [f"T{i}" for i in range(n)],
                )
                self.assertEqual(verdict["common_authority_ids"], verdict["discovery_union_ids"])
                self.assertFalse(verdict["capability_truth_candidate_visible"])

    def test_identity_omission_kills_completeness(self):
        interface = build_complete_interface(authority(), source_count=2)
        sid = interface["public"]["discovery_sources"][0]["source_id"]
        interface["oracle"]["source_results"][sid].pop()
        verdict = validate_complete_interface(interface)
        self.assertFalse(verdict["valid"])
        self.assertTrue(any("DISCOVERY_UNION_NOT_COMMON_AUTHORITY" in x for x in verdict["errors"]))

    def test_outside_identity_kills_scope(self):
        interface = build_complete_interface(authority(), source_count=1)
        sid = interface["public"]["discovery_sources"][0]["source_id"]
        interface["oracle"]["source_results"][sid].append({
            "tool_id": "OUTSIDE",
            "cost": 0.0,
            "available": True,
            "authorized": True,
            "epoch": 0,
            "meta": {},
        })
        verdict = validate_complete_interface(interface)
        self.assertFalse(verdict["valid"])
        self.assertTrue(any("OUTSIDE_COMMON_AUTHORITY" in x for x in verdict["errors"]))

    def test_metadata_mutation_kills_truthful_discovery_premise(self):
        interface = build_complete_interface(authority(), source_count=1)
        sid = interface["public"]["discovery_sources"][0]["source_id"]
        interface["oracle"]["source_results"][sid][0]["cost"] += 100
        verdict = validate_complete_interface(interface)
        self.assertFalse(verdict["valid"])
        self.assertTrue(any("METADATA_MISMATCH" in x for x in verdict["errors"]))

    def test_capability_truth_leak_kills_information_boundary(self):
        interface = build_complete_interface(authority(), source_count=1)
        sid = interface["public"]["discovery_sources"][0]["source_id"]
        interface["oracle"]["source_results"][sid][0]["capabilities"] = {"CAP_A": True}
        verdict = validate_complete_interface(interface)
        self.assertFalse(verdict["valid"])
        self.assertTrue(any("CAPABILITY_TRUTH_LEAK" in x for x in verdict["errors"]))

    def test_source_unavailability_kills_common_complete_interface(self):
        interface = build_complete_interface(authority(), source_count=2)
        interface["public"]["discovery_sources"][0]["available"] = False
        verdict = validate_complete_interface(interface)
        self.assertFalse(verdict["valid"])
        self.assertTrue(any("SOURCE_NOT_AVAILABLE" in x for x in verdict["errors"]))

    def test_action_authority_excludes_counterfactual_outside_tools_for_both_sides(self):
        interface = build_complete_interface(authority(), source_count=2)
        for tid in ["T0", "T1", "T2", "T3"]:
            self.assertTrue(tool_invocable(tid, interface))
        self.assertFalse(tool_invocable("HYPOTHETICAL_UNBOUND_TOOL", interface))

    def test_initial_visibility_can_hide_every_identity_without_losing_scope_completeness(self):
        interface = build_complete_interface(authority(), source_count=3, initially_visible_ids=[])
        self.assertEqual(interface["public"]["visible_tools"], [])
        verdict = validate_complete_interface(interface)
        self.assertTrue(verdict["valid"], verdict)
        self.assertEqual(len(verdict["common_authority_ids"]), 4)

    def test_duplicate_identity_across_sources_fails_closed(self):
        interface = build_complete_interface(authority(), source_count=2)
        s0 = interface["public"]["discovery_sources"][0]["source_id"]
        s1 = interface["public"]["discovery_sources"][1]["source_id"]
        interface["oracle"]["source_results"][s1].append(
            copy.deepcopy(interface["oracle"]["source_results"][s0][0])
        )
        verdict = validate_complete_interface(interface)
        self.assertFalse(verdict["valid"])
        self.assertTrue(any("NOT_EXACTLY_ONCE" in x for x in verdict["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)

import unittest

from canonical.runtime.terminal_proof_supercompiler import (
    SCHEMA,
    compile_superproof,
)


def base_payload():
    return {
        "schema": SCHEMA,
        "obligations": ["A", "B"],
        "blockers": [
            {
                "id": "SHARED_TYPED_BOUNDARY",
                "status": "OPEN",
                "closable": True,
                "external_blocked": False,
                "dependency_depth": 1,
                "critical_path_wall_clock_units": 1,
                "new_reality_units": 0,
            },
            {
                "id": "EXACT_OPUS",
                "status": "OPEN",
                "closable": False,
                "external_blocked": True,
                "dependency_depth": 9,
                "critical_path_wall_clock_units": 99,
                "new_reality_units": 1,
            },
        ],
        "routes": [
            {
                "id": "A_FORMAL",
                "covers": ["A"],
                "proof_mode": "FORMAL_PROOF",
                "blockers": ["SHARED_TYPED_BOUNDARY"],
                "base_admissible": True,
                "terminal_scope_authority": True,
                "zero_incremental_spend": True,
                "machine_checkable": True,
            },
            {
                "id": "A_OPUS",
                "covers": ["A"],
                "proof_mode": "MATCHED_EXACT_OPUS",
                "blockers": ["EXACT_OPUS"],
                "base_admissible": True,
                "terminal_scope_authority": True,
                "zero_incremental_spend": True,
                "exact_opus_5_5_comparator_bound": True,
                "symmetric_harness_frozen": True,
            },
            {
                "id": "B_PUBLIC",
                "covers": ["B"],
                "proof_mode": "PUBLIC_FIXED_BAR",
                "blockers": ["SHARED_TYPED_BOUNDARY"],
                "base_admissible": True,
                "terminal_scope_authority": True,
                "zero_incremental_spend": True,
                "scope_equivalent": True,
                "zero_cost_executable": True,
            },
        ],
    }


class Tests(unittest.TestCase):
    def test_transmutes_away_unneeded_opus_and_dedupes_shared_blocker(self):
        out = compile_superproof(base_payload())
        self.assertEqual(out["status"], "EXACT_MINIMUM_UNBLOCK_CUT_FOUND", out)
        self.assertEqual(
            out["minimum_unblock_cut"]["blocker_ids"],
            ["SHARED_TYPED_BOUNDARY"],
        )
        self.assertEqual(
            set(out["minimum_unblock_cut"]["selected_route_ids"]),
            {"A_FORMAL", "B_PUBLIC"},
        )
        self.assertEqual(
            out["proof_mode_transmutation"]["A"]["strongest_internally_reachable_mode"],
            "FORMAL_PROOF",
        )

    def test_external_irreducible_is_reported_not_proxied(self):
        p = base_payload()
        p["routes"] = [p["routes"][1], p["routes"][2]]
        out = compile_superproof(p)
        self.assertEqual(
            out["status"],
            "EXTERNAL_IRREDUCIBLE_OR_FROZEN_UNIVERSE_INCOMPLETE",
            out,
        )
        self.assertEqual(out["internally_uncovered_obligations"], ["A"])
        self.assertIn("EXACT_OPUS", out["unclosable_blockers"])

    def test_shared_blocker_beats_two_separate_blockers(self):
        p = base_payload()
        p["blockers"] += [
            {
                "id": "Y",
                "status": "OPEN",
                "closable": True,
                "external_blocked": False,
                "dependency_depth": 1,
                "critical_path_wall_clock_units": 1,
                "new_reality_units": 0,
            },
            {
                "id": "Z",
                "status": "OPEN",
                "closable": True,
                "external_blocked": False,
                "dependency_depth": 1,
                "critical_path_wall_clock_units": 1,
                "new_reality_units": 0,
            },
        ]
        p["routes"] += [
            {
                "id": "A_ALT",
                "covers": ["A"],
                "proof_mode": "FORMAL_PROOF",
                "blockers": ["Y"],
                "base_admissible": True,
                "terminal_scope_authority": True,
                "zero_incremental_spend": True,
                "machine_checkable": True,
            },
            {
                "id": "B_ALT",
                "covers": ["B"],
                "proof_mode": "PUBLIC_FIXED_BAR",
                "blockers": ["Z"],
                "base_admissible": True,
                "terminal_scope_authority": True,
                "zero_incremental_spend": True,
                "scope_equivalent": True,
                "zero_cost_executable": True,
            },
        ]
        out = compile_superproof(p)
        self.assertEqual(
            out["minimum_unblock_cut"]["blocker_ids"],
            ["SHARED_TYPED_BOUNDARY"],
        )

    def test_claimed_formal_route_without_machine_checkable_proof_fails_closed(self):
        p = base_payload()
        del p["routes"][0]["machine_checkable"]
        out = compile_superproof(p)
        self.assertEqual(
            out["status"],
            "EXTERNAL_IRREDUCIBLE_OR_FROZEN_UNIVERSE_INCOMPLETE",
        )
        rejected = {r.get("route_id"): r.get("errors") for r in out["rejected_routes"]}
        self.assertTrue(any("MACHINE_CHECKABLE" in e for e in rejected["A_FORMAL"]))


if __name__ == "__main__":
    unittest.main()

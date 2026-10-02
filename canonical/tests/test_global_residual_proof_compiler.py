import unittest

from canonical.runtime.global_residual_proof_compiler import (
    SCHEMA,
    compile_global_residual,
)


def base_payload():
    return {
        "schema": SCHEMA,
        "obligations": ["A", "B", "C"],
        "blockers": [
            {
                "id": "A_BOUNDARY",
                "status": "OPEN",
                "closable": True,
                "external_blocked": False,
                "dependency_depth": 1,
                "critical_path_wall_clock_units": 1,
                "new_reality_units": 0,
            },
            {
                "id": "B_BOUNDARY",
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
        "semantic_blocker_equivalence": [
            {
                "id": "SHARED_TYPED_BOUNDARY",
                "members": ["A_BOUNDARY", "B_BOUNDARY"],
                "equivalence_asserted": True,
            }
        ],
        "routes": [
            {
                "id": "A_FORMAL",
                "covers": ["A"],
                "proof_mode": "FORMAL_PROOF",
                "blockers": ["A_BOUNDARY"],
                "base_admissible": True,
                "terminal_scope_authority": True,
                "zero_incremental_spend": True,
                "machine_checkable": True,
            },
            {
                "id": "B_PUBLIC",
                "covers": ["B"],
                "proof_mode": "PUBLIC_FIXED_BAR",
                "blockers": ["B_BOUNDARY"],
                "base_admissible": True,
                "terminal_scope_authority": True,
                "zero_incremental_spend": True,
                "scope_equivalent": True,
                "zero_cost_executable": True,
            },
            {
                "id": "C_OPUS",
                "covers": ["C"],
                "proof_mode": "MATCHED_EXACT_OPUS",
                "blockers": ["EXACT_OPUS"],
                "base_admissible": True,
                "terminal_scope_authority": True,
                "zero_incremental_spend": True,
                "exact_opus_5_5_comparator_bound": True,
                "symmetric_harness_frozen": True,
            },
        ],
    }


class Tests(unittest.TestCase):
    def test_external_residual_does_not_stall_internal_exact_cut(self):
        out = compile_global_residual(base_payload())
        self.assertEqual(out["status"], "GLOBAL_RESIDUAL_PARTITION_FOUND", out)
        self.assertEqual(out["internally_coverable_obligations"], ["A", "B"])
        self.assertEqual(
            [x["obligation_id"] for x in out["residual_obligations"]],
            ["C"],
        )
        self.assertEqual(
            out["minimum_internal_unblock_cut"]["blocker_ids"],
            ["SHARED_TYPED_BOUNDARY"],
        )
        self.assertEqual(
            set(out["minimum_internal_unblock_cut"]["selected_route_ids"]),
            {"A_FORMAL", "B_PUBLIC"},
        )
        self.assertFalse(out["execution_authority"])
        self.assertEqual(out["capability_credit_delta"], 0)

    def test_semantic_dedup_requires_explicit_assertion(self):
        p = base_payload()
        del p["semantic_blocker_equivalence"][0]["equivalence_asserted"]
        out = compile_global_residual(p)
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertTrue(
            any("SEMANTIC_CLASS_NOT_EXPLICITLY_ASSERTED" in e for e in out["errors"])
        )

    def test_unknown_semantic_member_fails_closed(self):
        p = base_payload()
        p["semantic_blocker_equivalence"][0]["members"].append("NOT_REAL")
        out = compile_global_residual(p)
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertTrue(
            any("SEMANTIC_CLASS_UNKNOWN_MEMBER" in e for e in out["errors"])
        )

    def test_overlap_between_equivalence_classes_fails_closed(self):
        p = base_payload()
        p["semantic_blocker_equivalence"].append(
            {
                "id": "SECOND_CLASS",
                "members": ["A_BOUNDARY", "EXACT_OPUS"],
                "equivalence_asserted": True,
            }
        )
        out = compile_global_residual(p)
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertTrue(any("SEMANTIC_CLASS_OVERLAP" in e for e in out["errors"]))

    def test_all_internal_returns_global_exact_cover(self):
        p = base_payload()
        p["obligations"] = ["A", "B"]
        p["routes"] = p["routes"][:2]
        out = compile_global_residual(p)
        self.assertEqual(out["status"], "GLOBAL_EXACT_INTERNAL_COVER_FOUND", out)
        self.assertEqual(out["residual_obligations"], [])
        self.assertEqual(
            out["minimum_internal_unblock_cut"]["blocker_ids"],
            ["SHARED_TYPED_BOUNDARY"],
        )

    def test_projection_is_not_assumed(self):
        p = base_payload()
        p["routes"] = [
            {
                "id": "A_C_COMBINED",
                "covers": ["A", "C"],
                "proof_mode": "FORMAL_PROOF",
                "blockers": ["A_BOUNDARY", "EXACT_OPUS"],
                "base_admissible": True,
                "terminal_scope_authority": True,
                "zero_incremental_spend": True,
                "machine_checkable": True,
            },
            p["routes"][1],
        ]
        out = compile_global_residual(p)
        self.assertEqual(out["status"], "GLOBAL_RESIDUAL_PARTITION_FOUND", out)
        residual_ids = [x["obligation_id"] for x in out["residual_obligations"]]
        self.assertIn("A", residual_ids)
        self.assertIn("C", residual_ids)


if __name__ == "__main__":
    unittest.main()

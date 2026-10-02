import unittest

from canonical.runtime.terminal_proof_supercompiler import SCHEMA, compile_superproof


def payload(route, extra_routes=None):
    return {
        "schema": SCHEMA,
        "obligations": ["A"],
        "blockers": [
            {
                "id": "EXACT_OPUS",
                "status": "OPEN",
                "closable": False,
                "external_blocked": True,
                "dependency_depth": 9,
                "critical_path_wall_clock_units": 99,
                "new_reality_units": 1,
            }
        ],
        "routes": [route] + list(extra_routes or []),
    }


def base_route(route_id, mode):
    return {
        "id": route_id,
        "covers": ["A"],
        "proof_mode": mode,
        "blockers": [],
        "base_admissible": True,
        "terminal_scope_authority": True,
        "zero_incremental_spend": True,
    }


def opus_route():
    return {
        "id": "A_OPUS",
        "covers": ["A"],
        "proof_mode": "MATCHED_EXACT_OPUS",
        "blockers": ["EXACT_OPUS"],
        "base_admissible": True,
        "terminal_scope_authority": True,
        "zero_incremental_spend": True,
        "exact_opus_5_5_comparator_bound": True,
        "symmetric_harness_frozen": True,
    }


class StrongerProofModeTests(unittest.TestCase):
    def test_universal_route_transmutes_away_exact_opus(self):
        route = base_route("A_UNIVERSAL", "UNIVERSAL")
        route.update(
            machine_checkable=True,
            all_admissible_inputs_proved=True,
            formal_completeness=True,
        )
        out = compile_superproof(payload(route, [opus_route()]))
        self.assertEqual(out["status"], "EXACT_MINIMUM_UNBLOCK_CUT_FOUND", out)
        self.assertEqual(out["minimum_unblock_cut"]["selected_route_ids"], ["A_UNIVERSAL"])
        self.assertEqual(
            out["proof_mode_transmutation"]["A"]["strongest_internally_reachable_mode"],
            "UNIVERSAL",
        )

    def test_universal_requires_formal_completeness(self):
        route = base_route("A_UNIVERSAL", "UNIVERSAL")
        route.update(machine_checkable=True, all_admissible_inputs_proved=True)
        out = compile_superproof(payload(route))
        self.assertEqual(
            out["status"],
            "EXTERNAL_IRREDUCIBLE_OR_FROZEN_UNIVERSE_INCOMPLETE",
            out,
        )
        rejected = {r.get("route_id"): r.get("errors") for r in out["rejected_routes"]}
        self.assertIn("A_UNIVERSAL:UNIVERSAL_COMPLETENESS_NOT_PROVED", rejected["A_UNIVERSAL"])

    def test_absolute_dominance_closes_at_theoretical_ceiling(self):
        route = base_route("A_CEILING", "ABSOLUTE_DOMINANCE")
        route.update(
            scope_equivalent=True,
            direction="higher",
            brain_lower_bound=1,
            theoretical_upper_bound=1,
        )
        out = compile_superproof(payload(route, [opus_route()]))
        self.assertEqual(out["status"], "EXACT_MINIMUM_UNBLOCK_CUT_FOUND", out)
        self.assertEqual(out["minimum_unblock_cut"]["selected_route_ids"], ["A_CEILING"])

    def test_absolute_dominance_is_fail_closed_without_scope_equivalence(self):
        route = base_route("A_CEILING", "ABSOLUTE_DOMINANCE")
        route.update(direction="higher", brain_lower_bound=1, theoretical_upper_bound=1)
        out = compile_superproof(payload(route))
        rejected = {r.get("route_id"): r.get("errors") for r in out["rejected_routes"]}
        self.assertIn(
            "A_CEILING:ABSOLUTE_DOMINANCE_SCOPE_EQUIVALENCE_REQUIRED",
            rejected["A_CEILING"],
        )

    def test_exhaustive_finite_requires_every_case_to_pass(self):
        route = base_route("A_EXHAUSTIVE", "EXHAUSTIVE_FINITE")
        route.update(finite_domain_frozen=True, exhaustive=True, all_cases_pass=False)
        out = compile_superproof(payload(route))
        rejected = {r.get("route_id"): r.get("errors") for r in out["rejected_routes"]}
        self.assertIn(
            "A_EXHAUSTIVE:EXHAUSTIVE_CASES_NOT_ALL_PASS",
            rejected["A_EXHAUSTIVE"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

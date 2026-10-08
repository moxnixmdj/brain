"""Sound local positives and adversarial negatives for finite cover checker."""
import copy
import itertools
import random

from canonical.runtime.finite_symbolic_cover_proof_checker_v1 import check


def base():
    return {
        "scope_id": "finite://two-boolean-test",
        "variables": ["a", "b"],
        "scope": ["const", True],
        "routes": [
            {"route_id": "yes-a", "admission": ["var", "a"], "adequacy": ["var", "a"]},
            {"route_id": "not-a", "admission": ["not", ["var", "a"]],
             "adequacy": ["not", ["var", "a"]]},
        ],
    }


def test_exact_finite_cover_positive_without_terminal_credit():
    result = check(base())
    assert result["pass"] is True
    assert result["all_assignments_checked"] == 4
    assert result["in_scope_assignments_checked"] == 4
    assert result["covered_in_scope_assignments"] == 4
    assert result["u_empty_authorized"] is False
    assert result["abc_closed_authorized"] is False
    assert result["route_real_world_adequacy_proved"] is False
    assert result["terminal_credit_delta"] == 0


def test_soundness_counterexample_wins_over_coverage():
    p = base()
    p["routes"][0]["adequacy"] = ["const", False]
    result = check(p)
    assert result["pass"] is False
    assert result["status"] == "COUNTEREXAMPLE__ADMISSION_DOES_NOT_IMPLY_DECLARED_ADEQUACY"
    assert result["counterexample"]["world"]["a"] is True


def test_uncovered_counterexample():
    p = base()
    p["routes"].pop()
    result = check(p)
    assert result["pass"] is False
    assert result["status"] == "COUNTEREXAMPLE__UNCOVERED_DECLARED_SCOPE"
    assert result["counterexample"]["world"]["a"] is False


def test_empty_scope_fails_instead_of_vacuous_global_proof():
    p = base()
    p["scope"] = ["and", ["var", "a"], ["not", ["var", "a"]]]
    assert check(p)["reason"] == "EMPTY_DECLARED_SCOPE_VACUITY"


def test_unknown_variable_fails_closed():
    p = base()
    p["routes"][0]["admission"] = ["var", "unbound"]
    assert check(p)["reason"] == "UNKNOWN_FORMULA_VARIABLE"


def test_boolean_not_coerced_from_integer():
    p = base()
    p["scope"] = ["const", 1]
    assert check(p)["reason"] == "INVALID_BOOLEAN_CONSTANT"


def test_unknown_operator_and_malformed_arity_fail():
    for formula in (["implies", ["var", "a"], ["var", "b"]],
                    ["or", ["var", "a"]], ["not"], []):
        p = base()
        p["scope"] = formula
        assert check(p)["status"] == "FAIL_CLOSED"


def test_duplicate_or_ambiguous_route_ids_fail():
    p = base()
    p["routes"][1]["route_id"] = p["routes"][0]["route_id"]
    assert check(p)["reason"] == "ROUTE_ID_INVALID_OR_DUPLICATE"


def test_claimed_external_proof_flags_are_not_part_of_accepted_input():
    p = base()
    p["independent_verified"] = True
    p["scope_complete"] = True
    p["u_empty_authorized"] = True
    assert check(p)["reason"] == "EXACT_INPUT_FIELDS_REQUIRED"


def test_tampered_input_has_different_digest_and_new_counterexample():
    p = base()
    original = check(p)
    altered = copy.deepcopy(p)
    altered["routes"][0]["admission"] = ["and", ["var", "a"], ["var", "b"]]
    result = check(altered)
    assert result["input_sha256"] != original["input_sha256"]
    assert result["pass"] is False


def test_randomized_256_bounded_truth_table_oracle_cases():
    rng = random.Random(20261008)
    for _ in range(256):
        n = rng.randint(1, 5)
        names = [f"v{i}" for i in range(n)]
        def node(depth=0):
            if depth >= 3 or rng.random() < 0.45:
                return (["var", rng.choice(names)] if rng.random() < 0.7
                        else ["const", bool(rng.getrandbits(1))])
            op = rng.choice(["not", "and", "or"])
            return [op, node(depth + 1)] if op == "not" else [op, node(depth + 1), node(depth + 1)]
        scope = node()
        routes = [
            {"route_id": f"r{i}", "admission": node(), "adequacy": node()}
            for i in range(rng.randint(1, 4))
        ]
        p = {"scope_id": "fuzz", "variables": names, "scope": scope, "routes": routes}
        result = check(p)
        def oracle(expr, world):
            if expr[0] == "const": return expr[1]
            if expr[0] == "var": return world[expr[1]]
            if expr[0] == "not": return not oracle(expr[1], world)
            if expr[0] == "and": return oracle(expr[1], world) and oracle(expr[2], world)
            if expr[0] == "or": return oracle(expr[1], world) or oracle(expr[2], world)
            raise AssertionError(expr)
        scoped = []
        for values in itertools.product((False, True), repeat=n):
            world = dict(zip(names, values))
            if oracle(scope, world):
                scoped.append(world)
        unsound = any(oracle(r["admission"], w) and not oracle(r["adequacy"], w)
                      for w in scoped for r in routes)
        uncovered = any(not any(oracle(r["admission"], w) for r in routes) for w in scoped)
        expected = ("FAIL_CLOSED" if not scoped else
                    "COUNTEREXAMPLE__ADMISSION_DOES_NOT_IMPLY_DECLARED_ADEQUACY" if unsound else
                    "COUNTEREXAMPLE__UNCOVERED_DECLARED_SCOPE" if uncovered else
                    "PASS__EXACT_FINITE_FORMULA_COVER_VERIFIED")
        assert result["status"] == expected, (p, result, expected)
        assert result["terminal_credit_delta"] == 0


def test_full_twelve_variable_domain_is_exhausted_without_claiming_terminal_scope():
    names = [f"v{i}" for i in range(12)]
    p = {
        "scope_id": "finite://max-bound",
        "variables": names,
        "scope": ["const", True],
        "routes": [{"route_id": "every", "admission": ["const", True],
                    "adequacy": ["const", True]}],
    }
    r = check(p)
    assert r["pass"] is True
    assert r["all_assignments_checked"] == 4096
    assert r["covered_in_scope_assignments"] == 4096
    assert r["scope_is_entire_terminal_universe_proved"] is False


def test_thirteen_variables_exceed_checker_sound_resource_bound():
    p = base()
    p["variables"] = [f"v{i}" for i in range(13)]
    assert check(p)["reason"] == "VARIABLE_DOMAIN_INVALID"


def test_oversized_identity_strings_fail_closed():
    p = base()
    p["scope_id"] = "s" * 257
    assert check(p)["reason"] == "SCOPE_ID_INVALID"
    p = base()
    p["routes"][0]["route_id"] = "r" * 129
    assert check(p)["reason"] == "ROUTE_ID_INVALID_OR_DUPLICATE"


def test_large_ast_is_bounded_by_total_node_count():
    p = base()
    p["scope"] = ["and"] + [["var", "a"] for _ in range(520)]
    assert check(p)["reason"] == "AST_NODE_LIMIT"


def test_supplied_adequacy_true_still_does_not_prove_real_capability():
    p = base()
    for route in p["routes"]:
        route["adequacy"] = ["const", True]
    r = check(p)
    assert r["pass"] is True
    assert r["route_real_world_adequacy_proved"] is False
    assert r["terminal_authority"] is False

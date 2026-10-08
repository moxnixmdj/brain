"""Executable regression tests for the exact bounded Boolean proof kernel."""
import copy
import json
import pathlib
import tempfile

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.finite_symbolic_cover_replay_v1 import verify

SCOPE = "scope://proof-unit/boolean-split-v1"

def spec():
    return {
        "schema": "PROJECT_BRAIN_FINITE_SYMBOLIC_COVER_SPEC_V1",
        "scope_id": SCOPE,
        "variables": ["x", "y"],
        "scope_cnf": [],  # every Boolean valuation is in scope
        "expected_output_cnf": [["x"]],
        "routes": [
            {"route_id": "x_true", "admission_cnf": [["x"]],
             "program_output_cnf": []},
            {"route_id": "x_false", "admission_cnf": [["!x"]],
             "program_output_cnf": [[]]},
        ],
    }

def run(value, *, mutate_digest=False, expected_scope_id=SCOPE):
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        path = root / "finite-model.json"
        content = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        path.write_bytes(content)
        digest = git_blob_id(content, object_format="sha1")
        if mutate_digest:
            digest = "0"*40
        return verify({"path": "finite-model.json", "git_blob_sha": digest},
                      repo_root=root, expected_scope_id=expected_scope_id)

def test_exact_cover():
    out=run(spec())
    assert out["pass"] is True
    assert out["scoped_valuations_checked"] == 4
    assert out["declared_symbolic_scope_covered"] is True
    assert out["global_scope_complete"] is False
    assert out["u_empty_authorized"] is False
    assert out["terminal_authority"] is False

def test_uncovered_witness():
    p=spec()
    p["routes"].pop()
    out=run(p)
    assert out["reason"] == "UNCOVERED_SCOPED_VALUATION"
    assert out["failing_valuation"]["x"] is False
    assert out["pass"] is False

def test_wrong_program_witness():
    p=spec()
    p["routes"][0]["program_output_cnf"] = [[]]
    out=run(p)
    assert out["reason"] == "ADMITTED_ROUTE_OUTPUT_MISMATCH"
    assert out["failing_valuation"]["x"] is True
    assert out["pass"] is False

def test_overlapping_unsound_route_fails():
    p=spec()
    p["routes"][1]["admission_cnf"] = []
    out=run(p)
    assert out["reason"] == "ADMITTED_ROUTE_OUTPUT_MISMATCH"

def test_byte_forgery_fails():
    out=run(spec(), mutate_digest=True)
    assert out["pass"] is False
    assert out["reason"] == "SPEC_BINDING_OR_REPLAY_INVALID"

def test_scope_swap_fails():
    out=run(spec(), expected_scope_id="scope://other")
    assert out["reason"] == "SPEC_SCOPE_MISMATCH"

def test_global_claim_fails():
    p=spec()
    p["global_scope_complete"]=True
    out=run(p)
    assert out["reason"] == "GLOBAL_AUTHORITY_CLAIM_FORBIDDEN"

def test_unknown_semantic_literal_fails():
    p=spec()
    p["expected_output_cnf"]=[["undocumented"]]
    out=run(p)
    assert out["reason"] == "SPEC_BINDING_OR_REPLAY_INVALID"

def test_empty_scope_cannot_prove_capability():
    p=spec()
    p["scope_cnf"]=[[]]
    out=run(p)
    assert out["reason"] == "EMPTY_DECLARED_SCOPE_NOT_CREDITABLE"

def test_too_many_variables():
    p=spec()
    p["variables"]=["v"+str(i) for i in range(16)]
    out=run(p)
    assert out["reason"] == "VARIABLES_INVALID_OR_TOO_LARGE"

def test_contradictory_program_and_oracle_are_not_arbitrarily_true():
    p=spec()
    p["routes"][0]["program_output_cnf"]=[["!x"]]
    out=run(p)
    assert out["reason"] == "ADMITTED_ROUTE_OUTPUT_MISMATCH"

def test_restricted_scope_is_explicit():
    p=spec()
    p["scope_cnf"]=[["x"]]
    out=run(p)
    assert out["pass"] is True
    assert out["scoped_valuations_checked"] == 2
    assert out["total_valuations"] == 4


def test_seeded_differential_against_independent_truth_table_interpreter():
    """Independently enumerate random CNFs, then compare pass/fail/witness."""
    import itertools
    import random
    rng=random.Random(20261008)

    def independent_eval(cnf, valuation):
        if not cnf:
            return True
        for clause in cnf:
            matched=False
            for atom in clause:
                name=atom.lstrip("!")
                is_positive=not atom.startswith("!")
                matched=matched or (valuation[name] == is_positive)
            if not matched:
                return False
        return True

    def random_formula(keys):
        return [[rng.choice(keys) if rng.random() < .5
                 else "!" + rng.choice(keys)
                 for _ in range(rng.randrange(0, 4))]
                for _ in range(rng.randrange(0, 4))]

    for _case in range(160):
        keys=["v"+str(i) for i in range(rng.randrange(1, 6))]
        problem={
            "schema": "PROJECT_BRAIN_FINITE_SYMBOLIC_COVER_SPEC_V1",
            "scope_id": SCOPE,
            "variables": keys,
            "scope_cnf": random_formula(keys),
            "expected_output_cnf": random_formula(keys),
            "routes": [
                {"route_id": "route"+str(i),
                 "admission_cnf": random_formula(keys),
                 "program_output_cnf": random_formula(keys)}
                for i in range(rng.randrange(1, 5))
            ],
        }
        ground="PASS"
        for bits in itertools.product((False, True), repeat=len(keys)):
            valuation=dict(zip(keys,bits))
            if not independent_eval(problem["scope_cnf"],valuation):
                continue
            if ground == "PASS":
                ground="PASS_WITH_SCOPE"
            admitted=False
            for route in problem["routes"]:
                if not independent_eval(route["admission_cnf"],valuation):
                    continue
                admitted=True
                if independent_eval(route["program_output_cnf"],valuation) != independent_eval(problem["expected_output_cnf"],valuation):
                    ground="ADMITTED_ROUTE_OUTPUT_MISMATCH"
                    break
            if ground=="ADMITTED_ROUTE_OUTPUT_MISMATCH":
                break
            if not admitted:
                ground="UNCOVERED_SCOPED_VALUATION"
                break
        if ground=="PASS":
            expected="EMPTY_DECLARED_SCOPE_NOT_CREDITABLE"
        elif ground=="PASS_WITH_SCOPE":
            expected="PASS"
        else:
            expected=ground
        output=run(problem)
        actual="PASS" if output["pass"] else output["reason"]
        assert actual==expected, (problem,expected,output)
        if actual in {"UNCOVERED_SCOPED_VALUATION","ADMITTED_ROUTE_OUTPUT_MISMATCH"}:
            val=output["failing_valuation"]
            assert independent_eval(problem["scope_cnf"],val)

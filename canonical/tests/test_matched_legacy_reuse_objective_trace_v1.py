from canonical.runtime import matched_executable_atom_semantics_v1 as semantics
from canonical.runtime.matched_legacy_reuse_objective_trace_v1 import (
    KIND_ATOM,
    KINDS,
    run_all,
    run_case,
)

DEV_SEED = 202610071337


def test_each_legacy_reuse_trace_passes_its_frozen_atom_checker():
    for i, kind in enumerate(KINDS):
        row = run_case(kind, DEV_SEED ^ (i * 97))
        out = semantics.check_atom(row["covered_atom"], row["objective_trace"])
        assert out["pass"] is True, (kind, row, out)
        assert row["covered_atom"] == KIND_ATOM[kind]


def test_all_seven_reuse_atoms_are_covered_exactly_once():
    atoms = [KIND_ATOM[x] for x in KINDS]
    assert len(atoms) == 7
    assert len(set(atoms)) == 7


def test_batch_runs_all_seven_reuse_cases():
    out = run_all(DEV_SEED)
    assert out["case_count"] == 7
    assert out["all_pass"] is True, out
    assert {x["kind"] for x in out["rows"]} == set(KINDS)


def test_development_seed_changes_concrete_case_ids():
    a = run_all(DEV_SEED)
    b = run_all(DEV_SEED + 1)
    ids_a = [x["case_id"] for x in a["rows"]]
    ids_b = [x["case_id"] for x in b["rows"]]
    assert ids_a != ids_b
    assert all(x != y for x, y in zip(ids_a, ids_b))


def test_adapter_never_grants_terminal_authority():
    for kind in KINDS:
        row = run_case(kind, DEV_SEED)
        assert row["terminal_authority"] is False
        assert row["fresh_reality_authority"] is False
        assert row["terminal_credit_delta"] == 0

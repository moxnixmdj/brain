"""One trial transfers a contract, not a trajectory.

Pinned: the receipt's numbers, because they are the claim. Live: the mechanisms themselves -- generalisation
over roles, the vacuity guard on derived clauses, the intervention licence, and the rule that a clause which
was never licensed cannot condemn anything.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import predictive_contract_v1 as pc  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "PREDICTIVE_CONTRACT_20261116_V1.json"


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def test_paths_generalise_over_roles_not_over_states() -> None:
    binding = {"src": "in.txt", "dst": "out.dat"}
    assert pc._generalise("out.dat", binding) == "{dst}"
    assert pc._generalise("in.txt", binding) == "{src}"
    assert pc._generalise("in.txt.gz", binding) == "{src}.gz"
    assert pc._generalise("chunk_aa", binding).endswith("*")
    assert pc._instantiate("{dst}.gz", {"dst": "sub/result.dat"}) == "sub/result.dat.gz"


def test_a_clause_that_says_the_whole_file_is_the_whole_file_is_rejected() -> None:
    src = b"alpha beta gamma\n"
    # upper-casing the entire file is not a local substitution claim
    whole = pc.derive_clauses(src, src.upper())
    assert all(clause["name"] != "derived_literal_substitution" for clause in whole)
    local = pc.derive_clauses(b"x alpha y\n", b"x ALPHA y\n")
    assert any(clause["name"] == "derived_literal_substitution" for clause in local)


def test_a_derived_clause_only_speaks_to_bytes_it_actually_covered() -> None:
    clause = {"name": "derived_byte_map", "params": {"map": {str(ord("a")): ord("A")}}}
    assert pc.holds(clause, b"a", {}, b"A") is True
    assert pc.holds(clause, b"a", {}, b"B") is False
    # nothing in the map covers this input: abstain, do not pass
    assert pc.holds(clause, b"zzz", {}, b"qqq") is None


def test_the_intervention_is_licensed_by_acquisition_not_assumed() -> None:
    contract = pc.acquire("cp {src} {dst}", "cp", pc.SEEN, pc.SEEN_TEXT)
    assert contract["input_sensitive"] is True
    assert contract["content_clause"] == {"name": "identity", "params": {}}
    assert contract["frame"]["creates"] == ["{dst}"]
    assert contract["precondition"]["required_paths"] == ["{src}"]


def test_the_receipt_numbers(report: dict) -> None:
    assert report["tasks"] == 9
    assert report["mutants"] == 34
    assert report["arms"]["no_recorded_consequence"]["density"] == 0.5
    assert report["arms"]["frame_only"]["density"] == 0.9706
    assert report["arms"]["full"]["density"] == 1.0
    assert report["false_alarms_on_correct_novel_actions"]["full"]["count"] == 0


def test_the_two_sided_ablation_is_what_makes_the_claim_honest(report: dict) -> None:
    content = report["content_only_arm"]
    # paths identical, bytes different: the frame is nearly blind and the clause carries it
    assert content["frame_only"]["density"] < 0.5
    assert content["full"]["density"] > content["frame_only"]["density"]
    # the residual is located, not waved away
    assert content["full"]["caught"] < content["full"]["total"]


def test_the_intervention_is_reported_as_a_null_result_rather_than_a_saving(report: dict) -> None:
    arms = report["arms"]
    assert arms["frame_plus_intervention"]["density"] == arms["frame_only"]["density"]
    assert "content_relation" in report["detection_by_mechanism"]
    assert set(report["content_clause_derived_for"]) == {"tr", "sed"}


def test_the_boundary_that_is_not_crossed_is_stated(report: dict) -> None:
    assert "fidelity-versus-correctness" in report["limit"]
    assert "change of program" in report["limit"]


def test_a_correct_novel_action_is_never_condemned_live() -> None:
    import tempfile
    import shutil

    work = pathlib.Path(tempfile.mkdtemp(prefix="brain-pc-test-"))
    try:
        contract = pc.acquire("cp {src} {dst}", "cp", pc.SEEN, pc.SEEN_TEXT)
        before, after, code = pc._execute("cp {src} {dst}", pc.NOVEL, pc.NOVEL_TEXT, work)
        verdict = pc.judge(contract, pc.predict(contract, pc.NOVEL, before),
                           pc.NOVEL, before, after, code)
        assert verdict["verdict"] == "HOLDS"
        # the same contract, on a wrong action, must object
        before2, after2, code2 = pc._execute("cp {src} decoy.txt", pc.NOVEL, pc.NOVEL_TEXT, work)
        verdict2 = pc.judge(contract, pc.predict(contract, pc.NOVEL, before2),
                            pc.NOVEL, before2, after2, code2)
        assert verdict2["verdict"] in {"VIOLATED", "UNKNOWN"}
    finally:
        shutil.rmtree(work, ignore_errors=True)

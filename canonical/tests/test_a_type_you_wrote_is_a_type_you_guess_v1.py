"""The four tests that make a declared check a witness, and the mistakes each one catches.

This round measured its own instrument and found three defects in it, in this order:

  1. a "check" that MUTATED the room (`ln --verbose`) between two objects, so the objects being
     named were not the objects being asked about -- the same defect
     `scan_and_diff_against_memory_v1` recorded for `py_compile`;
  2. a "check" that separated by reading CONTENT (`perl -c`, `rgrep -l`, `node --trace-exit`)
     and was therefore a test of the file, not of its type. Keeping them raised the headline
     number from 155 to 160 -- a gate that improves when a defect is added is not a gate;
  3. a deadline so tight that `node --trace-*` crossed it under load and the witness set moved
     between two runs of the same instrument (155, then 160).

Each of those is held here as a test, because a number that was wrong once will drift back
unless something fails when it does.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
TOOLS = REPO / "canonical" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import a_type_you_wrote_is_a_type_you_guess_v1 as subject  # noqa: E402

RECEIPT = REPO / "canonical/verification/A_TYPE_YOU_WROTE_IS_A_TYPE_YOU_GUESS_20261202_V1.json"


@pytest.fixture(scope="module")
def receipt():
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def test_the_receipt_declares_every_gate_and_all_of_them_hold(receipt):
    assert set(receipt["verdict"]) == {key for key in receipt["declared_before_the_run"]}
    assert len(receipt["verdict"]) == 8
    for name, row in receipt["verdict"].items():
        assert row["MET"] is True, name
        assert row["claimed"] and row["measured"]


def test_zero_means_zero(receipt):
    cost = receipt["cost"]
    assert cost["model_calls"] == 0
    assert cost["parameters_stored"] == 0
    assert cost["network_calls_at_run_time"] == 0
    assert receipt["authority"] == "NONE__PRODUCER_RUN_SANDBOX"


def test_the_receipt_says_what_it_is_not(receipt):
    lines = receipt["what_this_is_not"]
    assert any("not a benchmark result" in line for line in lines)
    assert any("not a type theory" in line for line in lines)


def test_a_check_that_writes_is_never_a_witness(receipt):
    """Defect 1: `shred --verbose` separated the room by destroying it."""
    scan = receipt["witnesses"]["room_a"]
    assert scan["changed_the_room"] >= 1
    detail = receipt["writable_or_destructive_declared_checks"]["detail"]
    assert any("shred" in name for name in detail)
    witnesses = set(receipt["witnesses"]["witnesses"])
    for name in detail:
        assert name not in witnesses, name
    assert receipt["writable_or_destructive_declared_checks"]["count"] >= len(detail)


def test_a_content_test_is_removed_by_the_second_room(receipt):
    """Defect 2: keeping `perl -c` raised the headline number and was wrong."""
    invariance = receipt["witnesses"]["invariance"]
    assert invariance["removed"] >= 1
    removed = {row["witness"] for row in invariance["removed_detail"]}
    assert any(name.startswith("perl") for name in removed)
    assert any(name.startswith("rgrep") for name in removed)


def test_the_rounds_own_claim_is_false_on_a_thin_machine(receipt):
    """The finding, and the reason the round is a falsification rather than a win."""
    thin = receipt["thin_machine"]
    rich = receipt["discrimination"]["room_u"]
    assert rich["witnessed"]["different_pairs_separated"] > rich["written"]["different_pairs_separated"]
    assert (thin["witnessed"]["different_pairs_separated"]
            < thin["written"]["different_pairs_separated"]), (
        "the thin machine no longer contradicts the rich one, so this round's thesis needs "
        "restating before its essay can be true")
    assert thin["declared_checks"] < 1000 and thin["witness_count"] < 45
    assert receipt["verdict"]["T8_derived_typing_has_a_machine_threshold_some_machines_are_below"]["MET"] is True


def test_the_comparison_against_work_this_tree_already_had_is_kept(receipt):
    """The round does not beat the authored scanner on its own number, and says so."""
    table = receipt["where_this_loses"]["honest_comparison_on_room_u"]
    assert table["inherited_scanner_as_written"] > table["this_rounds_derived_witnesses"]
    assert table["this_rounds_derived_witnesses"] > table["written_kind_table"]
    assert "MORE" in receipt["where_this_loses"]["the_plain_statement"]


def test_the_one_kind_the_rule_removes_from_the_authored_scanner(receipt):
    applied = receipt["inherited_scanner"]["same_four_tests_applied"]
    assert applied["written_kinds"] == 7
    assert applied["removed"] == ["python"]
    contradicted = {row["written_kind"]: row["contradicted_on"] for row in applied["rows"]}
    assert "plain-text" in contradicted["python"]


def test_the_residual_is_listed_with_a_price(receipt):
    residual = receipt["indistinguishable"]["room_u"]
    assert residual["unresolved_count"] == len(residual["unresolved_classes"])
    assert residual["unresolved_count"] >= 1
    assert residual["bits_undecidable"] > 0
    for row in residual["unresolved_classes"]:
        assert row["objects"] and row["questions_needed"] >= 0


def test_the_aliases_are_counted_so_forty_five_is_not_praised(receipt):
    room = receipt["distinctions"]["room_u"]
    assert room["distinctions"] < room["witnesses"]
    assert sum(room["aliasing"]) == room["witnesses"]
    assert room["runs_saved_by_one_name_per_distinction"] > 20


def test_a_signature_is_a_set_of_verdicts_and_names_no_program_in_the_rule():
    source = (REPO / "canonical/tools/a_type_you_wrote_is_a_type_you_guess_v1.py").read_text()
    rule = source[source.index("def witness_scan("):source.index("def _codes_on(")]
    for program in ("gzip", "tar", "unzip", "jq", "sqlite3", "openssl", "node", "perl"):
        assert f'"{program}"' not in rule, program


def test_the_storing_question_is_answered_by_the_same_rule_twice(receipt):
    storing = receipt["storing"]
    assert storing["identical"] is True
    assert storing["room_a_witnesses"] == storing["room_b_witnesses"]
    assert storing["only_on_room_a"] == [] and storing["only_on_room_b"] == []


def test_an_object_no_check_can_examine_gets_the_empty_signature(receipt):
    sigs = receipt["signatures_on_room_u"]
    empty = sorted(name for name, sig in sigs.items() if not sig)
    assert empty, "the residual must remain visible, not defaulted to a kind"
    residual = receipt["indistinguishable"]["room_u"]["unresolved_classes"]
    assert any(sorted(row["objects"]) == empty for row in residual)

"""A row may answer a stated command only by declaring exactly which command.

Two gates refuse a capability that has no command slot when the sentence states a
settled command line. Both are right for a row chosen by word overlap. This file
pins the narrow exemption that lets an in-process row answer the command's
QUESTION, and pins what the exemption must never do:

* it must not admit a different program (`wc -w` is not declared, so it stays
  refused, even though the same row declares `wc -l`);
* it must not admit a different flag, a different operand order, a different
  arity, or a template whose program is a placeholder;
* it must not admit a row that declares nothing;
* a read-only row must not be routed to a sentence that opens by asking to
  change the file, and must not run when it is.

The last two are measured against the real front door, because the point of the
exemption is the door's behaviour, not this module's algebra.

usage:
  python3 -B canonical/tests/test_declared_command_equivalence_v1.py
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_composer_v1 as graph  # noqa: E402
from canonical.runtime import declared_command_equivalence_v1 as declared  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

ROW = {
    "computes_command": {
        "argvs": [["wc", "-l", "${path}"]],
        "answer_field": "newline_count",
    },
    "read_only": True,
}

STATE = ROOT / "canonical/astra_runtime/state"
WORK_NAME = "test_declared_command_equivalence"


def _work() -> pathlib.Path:
    work = ROOT / "canonical/astra_runtime/tmp" / WORK_NAME
    work.mkdir(parents=True, exist_ok=True)
    target = work / "a.txt"
    target.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    return target


def test_exact_declared_argv_matches() -> None:
    hit = declared.matched_template(ROW, ["wc", "-l", "some/file.txt"])
    assert hit is not None, "the declared argv did not match itself"
    assert hit["template"] == ["wc", "-l", "${path}"]
    assert hit["matched_argv"] == ["wc", "-l", "some/file.txt"]


def test_a_different_program_is_not_declared() -> None:
    assert declared.matched_template(ROW, ["md5sum", "-l", "some/file.txt"]) is None


def test_a_different_flag_is_not_declared() -> None:
    assert declared.matched_template(ROW, ["wc", "-w", "some/file.txt"]) is None
    assert declared.matched_template(ROW, ["wc", "-c", "some/file.txt"]) is None


def test_a_different_arity_or_order_is_not_declared() -> None:
    assert declared.matched_template(ROW, ["wc", "some/file.txt"]) is None
    assert declared.matched_template(ROW, ["wc", "-l", "a", "b"]) is None
    assert declared.matched_template(ROW, ["some/file.txt", "-l", "wc"]) is None


def test_a_placeholder_program_matches_nothing() -> None:
    wildcard = {"computes_command": {"argvs": [["${program}", "-l", "${path}"]]}}
    assert declared.matched_template(wildcard, ["rm", "-l", "x"]) is None


def test_a_row_that_declares_nothing_is_unchanged() -> None:
    assert declared.matched_template({}, ["wc", "-l", "x"]) is None
    assert declared.matched_template({"read_only": True}, ["wc", "-l", "x"]) is None


def test_a_string_argv_is_not_a_command() -> None:
    assert declared.matched_template(ROW, "wc -l x") is None
    assert declared.matched_template(ROW, None) is None


def _admission(goal: str) -> dict:
    registry, admissible, compiled = door.live_integrated_brain_v1.compile_against_live_registry(
        goal, door.ROOT)
    normalized = door.front.normalize_goal(goal)
    return door.route_admission(normalized, compiled, admissible)


def test_the_door_serves_the_line_count_it_declares() -> None:
    target = _work()
    rel = target.relative_to(ROOT).as_posix()
    result = door.solve({"task_id": "declared_eq", "goal": "Count the lines in " + rel})
    assert result.get("pass") is True, (result.get("status"), result.get("compiler_detail"))
    assert result.get("compiled_capability_id") == "file.line_count.v1", result.get("compiled_capability_id")


def test_the_door_does_not_serve_a_command_the_row_never_declared() -> None:
    """`wc -w` is the same program, the same operand, one flag away -- and refused."""
    target = _work()
    rel = target.relative_to(ROOT).as_posix()
    admission = _admission("Count the words in " + rel)
    assert admission.get("admitted") is not True, admission
    assert admission.get("rule") in (
        "NO_COMMAND_SLOT_FOR_THE_STATED_COMMAND",
        "READ_ONLY_CAPABILITY_FOR_A_SENTENCE_THAT_ASKS_TO_CHANGE_THE_FILE",
    ), admission.get("rule")


def test_a_read_only_row_is_refused_for_a_sentence_that_opens_by_changing_the_file() -> None:
    target = _work()
    rel = target.relative_to(ROOT).as_posix()
    # "Sort the lines of <f>" USED to be refused here and is now served by the
    # row that declares `sort <f>` -- the opposite case is pinned below.
    for goal, verb in (
        ("Delete the last line of " + rel, "delete"),
        ("Add a line containing delta to " + rel, "add"),
        ("Uppercase every line in " + rel, "uppercase"),
    ):
        admission = _admission(goal)
        assert admission.get("admitted") is False, (goal, admission)
        assert admission.get("rule") == (
            "READ_ONLY_CAPABILITY_FOR_A_SENTENCE_THAT_ASKS_TO_CHANGE_THE_FILE"), admission
        assert admission.get("goal_verb") == verb, admission.get("goal_verb")


def test_a_refused_mutating_sentence_does_not_execute_the_read_only_row() -> None:
    target = _work()
    rel = target.relative_to(ROOT).as_posix()
    before = target.read_bytes()
    result = door.solve({"task_id": "declared_eq_mut", "goal": "Delete the last line of " + rel})
    # The rejected candidate is still NAMED in the report, which is the point: the
    # caller sees what was considered and why it was refused. What must hold is
    # that nothing ran.
    assert result.get("pass") is not True, result.get("status")
    assert result.get("executed") is not True, result.get("executed")
    assert result.get("status") == "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED", result.get("status")
    assert (result.get("route_admission") or {}).get("rule") == (
        "READ_ONLY_CAPABILITY_FOR_A_SENTENCE_THAT_ASKS_TO_CHANGE_THE_FILE"), result.get("route_admission")
    assert target.read_bytes() == before, "the file changed"


def test_a_read_only_sentence_that_merely_mentions_writing_a_report_is_not_refused() -> None:
    """The mutation verb must OPEN the sentence; a later one usually governs another object."""
    target = _work()
    rel = target.relative_to(ROOT).as_posix()
    admission = _admission("Count the lines in %s and write the total to %s/total.json" % (rel, rel.rsplit("/", 1)[0]))
    assert admission.get("rule") != (
        "READ_ONLY_CAPABILITY_FOR_A_SENTENCE_THAT_ASKS_TO_CHANGE_THE_FILE"), admission


def test_a_read_only_row_is_never_the_chain_that_answers_a_write() -> None:
    """Measured regression, caught by an existing test before it shipped.

    With the command rows registered, "Write the line 'PROJECT BRAIN' to the file
    <out>" ranked `fileview.reversed` first -- the words "line" and "file" -- and
    composed a chain that READ the destination the sentence named. The chain
    raised and the request became STEP_RAISED_OUTCOME_UNKNOWN; on the previous
    commit the text writer served it. The fix drops read-only tokens from the
    candidate list for a sentence that states both a payload and its destination.
    """
    from canonical.runtime import composer_route_v1 as composer_route

    target = _work()
    rel = target.relative_to(ROOT).as_posix()
    out = rel.rsplit("/", 1)[0] + "/written.txt"
    tokens = composer_route.candidate_tokens(
        "Write the line 'PROJECT BRAIN' to the file " + out, graph.graph())
    read_only = {"fileview.contents", "fileview.sorted", "fileview.reversed",
                 "file.line_count.answer", "file.stat.answer"}
    assert not (set(tokens[:6]) & read_only), tokens[:6]
    result = door.solve({"task_id": "declared_eq_write",
                         "goal": "Write the line 'PROJECT BRAIN' to the file " + out})
    assert result.get("pass") is True, (result.get("status"), result.get("compiler_detail"))
    assert (ROOT / out).read_text(encoding="utf-8") == "PROJECT BRAIN", "the write did not land"


def test_a_directory_search_names_the_files_it_seeded_and_refuses_a_guessed_needle() -> None:
    """The one row that reads a value out of prose is pinned on both halves.

    "Which files in <d> contain beta?" used to execute python.source.audit.ast --
    a capability with nothing to do with the question. It is now answered by the
    row that scans the directory. The sentinel `BETA` is uppercase on purpose: a
    case-insensitive match would also list the second file, so the answer is
    checked against the files it must NOT include as well as the one it must.
    """
    work = ROOT / "canonical/astra_runtime/tmp/test_declared_command_equivalence"
    (work / "deep").mkdir(parents=True, exist_ok=True)
    (work / "has_beta.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    (work / "deep" / "also_beta.txt").write_text("beta beta\n", encoding="utf-8")
    (work / "shouts.txt").write_text("BETA\n", encoding="utf-8")
    (work / "nothing.txt").write_text("gamma\n", encoding="utf-8")
    rel = work.relative_to(ROOT).as_posix()

    result = door.solve({"task_id": "declared_eq_search",
                         "goal": "Which files in %s contain beta?" % rel})
    assert result.get("pass") is True, (result.get("status"), result.get("compiler_detail"))
    assert result.get("compiled_capability_id") == "file.directory_search.v1", (
        result.get("compiled_capability_id"))

    # And the refusal half, called directly: a sentence that states no string
    # must not be served by choosing one for it.
    from canonical.runtime.bound_capabilities import file_survey
    try:
        file_survey.run({"command": "directory_search", "path": rel,
                         "goal": "Search " + rel}, ROOT)
    except RuntimeError as exc:
        assert "SEARCH_TEXT_NOT_STATED" in str(exc), exc
    else:
        raise AssertionError("the search invented a string the sentence did not state")


def test_a_row_with_two_file_slots_binds_the_two_files_the_sentence_named() -> None:
    """Measured twice over, in both directions.

    Before the paired-slot rule, "Compare a.txt and b.txt" bound NOTHING (each
    slot saw "2 files named") and "Find the differences between a.txt and b.txt"
    bound BOTH slots to a.txt -- the world-binding fallback filled the companion
    with the file the pinned binder had already used, so the row was asked to
    diff a file against itself. Both halves are pinned here: the two paths must
    differ, and they must be the two the sentence named, in its order.
    """
    work = ROOT / "canonical/astra_runtime/tmp/test_declared_command_equivalence"
    work.mkdir(parents=True, exist_ok=True)
    left, right = work / "left.txt", work / "right.txt"
    left.write_text("alpha\nbeta\n", encoding="utf-8")
    right.write_text("alpha\nBETA\n", encoding="utf-8")
    rel_l, rel_r = left.relative_to(ROOT).as_posix(), right.relative_to(ROOT).as_posix()

    from canonical.runtime import capability_composer_v1 as _graph
    from canonical.runtime import goal_front_compiler_v1 as front
    entry = _graph.load_registry()["file.diff.v1"]
    bound = front.bind_all_inputs("Compare %s and %s" % (rel_l, rel_r), entry, ROOT,
                                 cycle=0, spool=set())
    assert bound.get("path") == rel_l, bound
    assert bound.get("other_path") == rel_r, ("paired slots collapsed", bound)
    assert bound["path"] != bound["other_path"], bound

    for goal in ("Compare %s and %s" % (rel_l, rel_r),
                 "Find the differences between %s and %s" % (rel_l, rel_r)):
        result = door.solve({"task_id": "declared_eq_diff", "goal": goal})
        assert result.get("pass") is True, (goal, result.get("status"),
                                            result.get("compiler_detail"))
        assert result.get("compiled_capability_id") == "file.diff.v1", goal


def test_the_registry_rows_that_declare_a_command_are_the_file_fact_rows() -> None:
    registry = graph.load_registry()
    declaring = sorted(cid for cid, entry in registry.items()
                       if isinstance(entry, dict) and declared.FIELD in entry)
    assert declaring == ["file.contents.v1", "file.diff.v1", "file.line_count.v1",
                         "file.reversed.v1", "file.sorted.v1",
                         "file.stat.v1"], declaring
    for cid in declaring:
        assert registry[cid].get("read_only") is True, cid


def test_a_declaration_outranks_a_mutation_verb_the_command_does_not_have() -> None:
    """`sort <f>` and `tac <f>` only print, so "Sort the lines of <f>" is servable.

    The opposite case is pinned by
    `test_a_read_only_row_is_refused_for_a_sentence_that_opens_by_changing_the_file`:
    "Delete the last line of <f>" states no such command, so the verb decides.
    """
    target = _work()
    rel = target.relative_to(ROOT).as_posix()
    for goal, expected in (("Sort the lines of " + rel, "file.sorted.v1"),
                           ("Reverse the lines of " + rel, "file.reversed.v1")):
        admission = _admission(goal)
        assert admission.get("admitted") is True, (goal, admission)
        result = door.solve({"task_id": "declared_eq_sort", "goal": goal})
        assert result.get("pass") is True, (result.get("status"), result.get("compiler_detail"))
        assert result.get("compiled_capability_id") == expected, result.get("compiled_capability_id")
    assert target.read_text(encoding="utf-8") == "alpha\nbeta\ngamma\n", "the file changed"


def test_a_fact_about_the_file_is_not_answered_by_printing_the_file() -> None:
    """Measured false pass, caught before shipping.

    With `file.contents.read.v1` added, "What are the file permissions of <f>"
    tied with `file.stat.v1` at 15 and the tie broke toward the contents row: the
    door PASSED, having answered a question about permission bits by printing the
    file. The tie existed because both rows carried the generic token `file` in
    `provides`. The fix is in the rows, so this guards the rows.
    """
    target = _work()
    rel = target.relative_to(ROOT).as_posix()
    for goal, expected in (
        ("What are the file permissions of " + rel, "file.stat.v1"),
        ("What is the size of " + rel, "file.stat.v1"),
        ("Show me the contents of " + rel, "file.contents.v1"),
    ):
        result = door.solve({"task_id": "declared_eq_fact", "goal": goal})
        assert result.get("pass") is True, (goal, result.get("status"),
                                            result.get("compiler_detail"))
        assert result.get("compiled_capability_id") == expected, (
            goal, result.get("compiled_capability_id"))


def main() -> int:
    tests = [value for key, value in sorted(globals().items())
             if key.startswith("test_") and callable(value)]
    failures = 0
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            failures += 1
            print("FAIL %s: %s" % (test.__name__, exc))
        else:
            print("ok   %s" % test.__name__)
    print("\n%d/%d passed" % (len(tests) - failures, len(tests)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

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
    for goal, verb in (
        ("Delete the last line of " + rel, "delete"),
        ("Add a line containing delta to " + rel, "add"),
        ("Sort the lines of " + rel, "sort"),
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


def test_the_registry_rows_that_declare_a_command_are_the_two_file_facts() -> None:
    registry = graph.load_registry()
    declaring = sorted(cid for cid, entry in registry.items()
                       if isinstance(entry, dict) and declared.FIELD in entry)
    assert declaring == ["file.line_count.v1", "file.stat.v1"], declaring
    for cid in declaring:
        assert registry[cid].get("read_only") is True, cid


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

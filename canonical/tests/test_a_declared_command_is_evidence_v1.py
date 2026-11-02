#!/usr/bin/env python3
"""A declared command is evidence FOR the row, not only an exemption from it.

Measured 2026-11-02, before either rule below existed:

  "What files are in <D>?"   -> FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT
  "What is in <F>?"          -> FAIL__RAW_GOAL_COMPILATION_GAP

Both sentences settle one command (`ls -A <D>`, `cat <F>`) and, in each case,
exactly one live row declares that it computes that command.  The machine
refused them anyway:

  * the listing sentence was ranked to `file.diff.v1` (a two-file row) and the
    pinned compiler failed to bind it, so the "the sentence states a command
    this row computes" fallback -- which ran only when the ranking was EMPTY --
    never ran (F32b);
  * with the right row selected, admission refused
    R13_DECLARED_INPUT_UNBINDABLE:path because the sentence shares only the word
    "files" with the row's keywords.  The declaration was trusted to REFUSE a
    row (NO_COMMAND_SLOT_FOR_THE_STATED_COMMAND) and never to admit one.

What this file holds the machine to:

  1. the declaration must be true of the program -- `ls -A` output and the row's
     own listing are compared byte for byte, and plain `ls` is shown to differ;
  2. a declaration admits its row only when EXACTLY ONE row declares the
     command, because a tie between rows is not evidence;
  3. the sentences that were refused with a sandbox complaint or a compilation
     gap are refused no longer, and the files are untouched by the read-only
     ones;
  4. the refusals around them did not move -- a directory asked as "what is in",
     and a request to delete a line, still fail closed.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import declared_command_equivalence_v1 as declared  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORLD = ROOT / "canonical/astra_runtime/tmp/declared_command_evidence_v1"
REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"


def _world() -> pathlib.Path:
    if WORLD.exists():
        shutil.rmtree(WORLD)
    (WORLD / "sub").mkdir(parents=True)
    (WORLD / ".hidden").write_text("hidden\n", encoding="utf-8")
    (WORLD / "B.txt").write_text("BETA\n", encoding="utf-8")
    (WORLD / "a.txt").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    return WORLD


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _ask(goal: str) -> dict:
    return door.solve({"task_id": "declared_command_evidence", "goal": goal}) or {}


def _registry() -> dict:
    return (json.loads(REGISTRY.read_text(encoding="utf-8")) or {}).get("capabilities") or {}


def _answer_entries(result: dict) -> list[str]:
    answer = result.get("answer")
    if isinstance(answer, dict):
        answer = answer.get("value")
    if isinstance(answer, (list, tuple)):
        return sorted(str(x) for x in answer)
    return sorted(str(answer or "").split("\n")) if answer else []


# --------------------------------------------------------------------------
# 1. The declaration is true of the real program.
# --------------------------------------------------------------------------
def test_the_listing_row_is_byte_identical_to_the_ls_it_declares() -> None:
    from canonical.runtime.bound_capabilities import file_survey

    world = _world()
    row = file_survey._directory_list({"path": world.as_posix()}, ROOT)
    real = subprocess.run(["ls", "-A", world.as_posix()], capture_output=True, text=True)
    assert real.returncode == 0, real.stderr
    assert row["answer"] == real.stdout.rstrip("\n"), (row["answer"], real.stdout)

    plain = subprocess.run(["ls", world.as_posix()], capture_output=True, text=True)
    # The flag is load-bearing, so the claim needs it: plain `ls` hides the
    # dot-file this row prints, and a declaration without `-A` would be wider
    # than the behaviour it describes.
    assert plain.stdout.rstrip("\n") != row["answer"], plain.stdout
    assert ".hidden" in row["answer"].split("\n"), row["answer"]


def test_the_declared_template_is_the_command_the_sentence_settles() -> None:
    from canonical.runtime import composer_route_v1 as composer

    world = _world()
    entry = _registry()["file.directory_listing.v1"]
    argv = composer.extract_argv("What files are in %s?" % _rel(world))
    assert argv == ["ls", "-A", _rel(world)], argv
    matched = declared.matched_template(entry, argv)
    assert matched is not None, argv
    assert matched["template"] == ["ls", "-A", "${path}"], matched


# --------------------------------------------------------------------------
# 2. Evidence: exactly one declarer, and the sentence's own command.
# --------------------------------------------------------------------------
def test_exactly_one_row_declares_the_settled_listing_command() -> None:
    from canonical.runtime import composer_route_v1 as composer

    world = _world()
    argv = composer.extract_argv("What files are in %s?" % _rel(world))
    declaring = sorted(cid for cid, entry in _registry().items()
                       if isinstance(entry, dict) and declared.matched_template(entry, argv))
    assert declaring == ["file.directory_listing.v1"], declaring


def test_a_declaration_supplies_the_evidence_a_thin_sentence_lacks() -> None:
    world = _world()
    result = _ask("What files are in %s?" % _rel(world))
    assert result.get("pass") is True, result.get("status")
    admission = result.get("route_admission") or {}
    assert admission.get("admission_basis") == (
        "THE_SENTENCE_STATES_A_COMMAND_THIS_ROW_DECLARES_IT_COMPUTES"), admission
    assert result.get("compiled_capability_id") == "file.directory_listing.v1", result
    assert _answer_entries(result) == [".hidden", "B.txt", "a.txt", "sub"], result.get("answer")


def test_the_reader_question_returns_the_file_text() -> None:
    world = _world()
    before = (world / "a.txt").read_bytes()
    result = _ask("What is in %s?" % _rel(world / "a.txt"))
    assert result.get("pass") is True, result.get("status")
    assert result.get("compiled_capability_id") == "file.contents.v1", result
    assert str(result.get("answer")) == before.decode("utf-8"), result.get("answer")
    assert (world / "a.txt").read_bytes() == before


# --------------------------------------------------------------------------
# 3. The refusals around these did not move.
# --------------------------------------------------------------------------
def test_a_directory_asked_what_is_in_it_is_not_read_as_a_file() -> None:
    world = _world()
    result = _ask("What is in %s?" % _rel(world))
    assert result.get("pass") is not True, result
    assert result.get("compiled_capability_id") != "file.contents.v1", result
    assert sorted(p.name for p in world.iterdir()) == [".hidden", "B.txt", "a.txt", "sub"]


def test_a_request_to_remove_a_line_is_still_refused_and_changes_nothing() -> None:
    world = _world()
    before = (world / "a.txt").read_bytes()
    result = _ask("Delete the last line of %s" % _rel(world / "a.txt"))
    assert result.get("pass") is not True, result
    assert (world / "a.txt").read_bytes() == before


def test_a_question_the_registry_cannot_answer_still_reaches_no_row() -> None:
    world = _world()
    result = _ask("Make a copy of %s named %s" % (_rel(world / "a.txt"), _rel(world / "c.txt")))
    assert result.get("pass") is not True, result
    assert not (world / "c.txt").exists(), "a refused copy created the destination"


def main() -> int:
    tests = [value for key, value in sorted(globals().items())
             if key.startswith("test_") and callable(value)]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - a test harness reports, never hides
            failures += 1
            print("FAIL %s: %s" % (test.__name__, exc))
        else:
            print("ok   %s" % test.__name__)
    print("\n%d/%d passed" % (len(tests) - failures, len(tests)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

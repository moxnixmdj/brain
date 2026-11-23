"""§A129 — the planner meets real GNU tools, and refuses three of the four.

Same lesson as §A127, one organ over. The planner had only ever been tested on `canonical/tests/programs/bin/`
tools written in this repository. Those tools all print a `USAGE:` line followed *immediately* by a description,
because the person who wrote them also wrote the reader.

Real GNU tools do not. `wc --help` prints:

    Usage: wc [OPTION]... [FILE]...
      or:  wc [OPTION]... --files0-from=F
    Print newline, word, and byte counts for each FILE, ...

The `or:` line is a SECOND USAGE FORM, and the description extractor returned it as the program's description.
So `wc` never stated the act `count`, and every request to count lines was refused with
`NO_OPERATION_IN_THE_DOCUMENT`. The refusal was honest about the reader's state and wrong about the program.

These tests use the host's own binaries and are skipped where they are absent. The argument is the same one
§A127 makes: a program we did not write is the cheapest test we have never run.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

from canonical.runtime import require_survey_plan_v1 as R

_GNU = pytest.mark.skipif(shutil.which("tar") is None or shutil.which("sort") is None,
                          reason="needs GNU coreutils/tar on the host")


def _plan(tool: str, instruction: str) -> tuple[str, list[str]]:
    result = R.require_survey_plan(shutil.which(tool) or tool, instruction)
    plans = result.get("plans") or []
    return str(result.get("reason")), list(plans[0]["argv"]) if plans else []


@_GNU
def test_a_description_after_an_alternate_usage_line_is_still_the_description() -> None:
    """The extractor must skip `or:` lines. Measured: it returned them, so `wc` and `sort` had no summary."""
    for tool, expected_word in (("wc", "counts"), ("sort", "sorted")):
        document = subprocess.run([shutil.which(tool), "--help"], capture_output=True, text=True).stdout
        summary = R._first_sentence_after_usage(document)
        assert expected_word in summary.lower(), (tool, summary)


@_GNU
def test_a_request_the_document_can_answer_is_planned_not_refused(tmp_path: pathlib.Path) -> None:
    """The whole point: four real requests, four real tools, no fixtures of ours."""
    for tool, instruction in (("wc", "count the lines in notes.txt"),
                              ("sort", "sort notes.txt"),
                              ("gzip", "compress notes.txt"),
                              ("tar", "create an archive called backup.tar containing notes.txt")):
        reason, argv = _plan(tool, instruction)
        assert reason == "PLANNED", (tool, instruction, reason)
        assert argv and argv[0].endswith(tool), (tool, argv)
        assert "notes.txt" in " ".join(argv), (tool, argv)


@_GNU
def test_a_switch_named_by_its_meaning_reaches_the_command(tmp_path: pathlib.Path) -> None:
    """§A129's sharpest case: `sort ... in reverse order` planned `sort notes.txt` and called it complete.

    The document states `-r, --reverse  reverse the result of comparisons`; the request says `reverse`. The
    matcher only routed flags the request spelled literally, so the modifier was dropped while
    `complete=True`, `dropped_words=[]` and `refusals=[]` all said the plan was whole -- a *complete and wrong*
    verdict, the most dangerous verdict there is.

    Scored against execution, not against the plan's own claim: `sort --reverse` must actually reverse.
    """
    reason, argv = _plan("sort", "sort notes.txt in reverse order")
    assert reason == "PLANNED", reason
    assert "--reverse" in argv or "-r" in argv, argv

    (tmp_path / "notes.txt").write_text("banana\napple\ncherry\n")
    reversed_run = subprocess.run(argv, cwd=tmp_path, capture_output=True, text=True)
    assert reversed_run.returncode == 0, reversed_run.stderr
    assert reversed_run.stdout.split() == ["cherry", "banana", "apple"]

    # and the unmodified request must NOT carry the switch
    _, plain = _plan("sort", "sort notes.txt")
    assert "--reverse" not in plain and "-r" not in plain, plain
    forward_run = subprocess.run(plain, cwd=tmp_path, capture_output=True, text=True)
    assert forward_run.stdout.split() == ["apple", "banana", "cherry"]

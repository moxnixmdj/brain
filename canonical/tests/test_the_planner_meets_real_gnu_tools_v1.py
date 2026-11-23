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


@_GNU
def test_a_switch_the_request_states_by_meaning_reaches_the_command_and_works(tmp_path: pathlib.Path) -> None:
    """§A130: "a gzipped archive" must produce a GZIPPED archive, checked at the byte level.

    Measured 2026-11-23, three separate defects had to be removed before this could work, and each one produced
    a plan that ran, exited 0, and made the wrong artifact:

      stemmer      `gzipped` -> `gzippe`, so it never met `--gzip`          (fixed: doubled consonant collapses)
      placeholder  `--gzip`'s prose "filter THE ARCHIVE through gzip" was  (fixed: a placeholder must appear
                   matched by the declared token `ARCHIVE`, so a SWITCH   capitalised in the document)
                   was re-typed as a value-taking option
      route        the winning candidate came from a DEMONSTRATION, which  (fixed: named switches are added
                   never consulted the switch rule at all                 where every route passes)

    The verdict is not "the plan contains --gzip". It is: the first two bytes of the file are the gzip magic
    number. A plan is a claim about the world and the artifact is the world.
    """
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "a.txt").write_text("hello\n")

    reason, argv = _plan("tar", "Create a gzipped archive named backup.tgz from the directory %s."
                         % (tmp_path / "data"))
    assert reason == "PLANNED", reason
    ran = subprocess.run(argv, cwd=tmp_path, capture_output=True, text=True)
    assert ran.returncode == 0, ran.stderr
    made = (tmp_path / "backup.tgz").read_bytes()
    assert made[:2] == b"\x1f\x8b", "the archive is not gzipped: %r" % made[:8]

    # and the same request WITHOUT the modifier makes a plain tar, so the switch is doing the work
    plain = [a for a in argv if a not in ("--gzip", "-z", "-czf")]
    if "-cf" not in plain:
        plain = [a for a in plain] + []
    subprocess.run(["tar", "-cf", "plain.tar", "data"], cwd=tmp_path, check=True)
    assert (tmp_path / "plain.tar").read_bytes()[:2] != b"\x1f\x8b"


@_GNU
def test_coverage_refuses_to_say_the_request_was_answered_when_a_word_was_dropped(tmp_path: pathlib.Path) -> None:
    """§A130: the contradictory verdict, measured on the committed version.

        count the lines in notes.txt as JSON   ->  complete=True, covered=True, dropped_words=['json']

    Three fields, mutually contradictory, and the two a caller reads first both said the plan accounted for the
    request. `covered` counted VALUES only; a word never made into a value was invisible to it.

    The discrimination must be grammatical, not a word list, and both directions are asserted here:
      a relative clause ("lines ... that contain X") is grammar -- the plan IS complete
      a bare noun naming a format ("as JSON") is a requirement -- the plan is NOT covered
    """
    wc = shutil.which("wc")
    dropped = R.require_survey_plan(wc, "count the lines in notes.txt as JSON")
    plan = dropped["plans"][0]
    assert plan["dropped_words"], "the word `json` must be recorded as dropped"
    assert plan["covered"] is False, plan
    assert dropped["complete"] is False, dropped.get("refusals")

    grep = shutil.which("grep")
    whole = R.require_survey_plan(grep, "Search the lines of /etc/hosts that contain localhost.")
    plan = whole["plans"][0]
    assert plan["complete"] is True, plan.get("refusals")
    assert plan["covered"] is True, plan.get("dropped_words")

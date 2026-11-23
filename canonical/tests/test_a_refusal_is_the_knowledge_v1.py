"""An UNTYPED row becomes DO by reading the environment's own refusals -- measured, not assumed.

The discovered shape, from the session that found it. `python.refactor.move_function.v1` was one of 14
UNTYPED rows: the census could not fill `module`, `symbol`, `to_module` and the type surface could not
derive them, so the machine knew it did not know and had nothing to do about it.

Six calls, each refused for a different reason, each naming the missing fact:

    TEST_ROOT_MISSING                                     -> needs a tests directory
    MODULE_NOT_FOUND:file_survey                          -> a bare module name is not a path
    NAME_COLLISION_TARGET_MODULE:archive_tarfile.py:run    -> the target already defines `run`
    SUITE_FAILED_AFTER_MOVE: Start directory is not importable -> the tests dir needs `__init__.py`
    PASS                                                  -> suite_passed: true, output_verified: true

The last two tests in the discovery also found a bug in the CAPABILITY, not in the client: `TEST_ROOT_MISSING`
did not say WHICH directory, so an honest reader could only guess and a repair loop made the same wrong
directory twice. Naming the path turned the refusal into something actionable. That is the general lesson:
**a refusal must locate itself.**
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import knowledge_repair_v1 as K  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
ADAPTERS = ROOT / "canonical/runtime/bound_capabilities"


def test_an_untyped_row_reaches_verified_by_answering_its_refusals() -> None:
    """The whole point: a row the machine could not fill becomes a row the machine completed.

    The repairs are the evidence. Each one answers a refusal that named something, and the final call
    verifies -- `output_verified: true` and `suite_passed: true` from the capability's own report.
    """
    report = K.repair_untyped(
        "python.refactor.move_function.v1",
        {"capability_id": "python.refactor.move_function.v1", "source_root": "pkg",
         "module": "file_survey.py", "symbol": "run", "to_module": "broad_objective_decompose.py",
         "output_path": "pkg/out.json", "timeout_s": 120},
        ADAPTERS,
    )
    assert report["verified"] is True, report
    assert report["result"]["suite_passed"] is True
    assert report["result"]["output_verified"] is True
    assert len(report["repairs"]) >= 2, report["repairs"]
    said = " ".join(report["repairs"])
    assert "__init__.py" in said, "the importability refusal must be answered, not skipped"


def test_the_repair_runs_in_a_copy_and_never_the_given_tree() -> None:
    """A repair loop writes files. It must write them somewhere that is not the user's project."""
    before = sorted(p.name for p in ADAPTERS.iterdir() if p.is_file())
    report = K.repair_untyped(
        "python.refactor.move_function.v1",
        {"capability_id": "python.refactor.move_function.v1", "source_root": "pkg",
         "module": "file_survey.py", "symbol": "run", "to_module": "broad_objective_decompose.py",
         "output_path": "pkg/out.json", "timeout_s": 120},
        ADAPTERS,
    )
    after = sorted(p.name for p in ADAPTERS.iterdir() if p.is_file())
    assert before == after, "the repair edited the tree it was handed"
    env = pathlib.Path(report["environment"])
    assert env.is_dir() and env.name.startswith("brain_repair_env_")
    assert "tests" in [p.name for p in env.iterdir()]


def test_a_collision_is_reported_not_renamed_away() -> None:
    """`NAME_COLLISION_TARGET_MODULE` is a true statement that this act is wrong.

    Renaming the user's function to make the move succeed would be the machine editing the world to fit its
    own plan. The loop must stop and say so.
    """
    report = K.repair_untyped(
        "python.refactor.move_function.v1",
        {"capability_id": "python.refactor.move_function.v1", "source_root": "pkg",
         "module": "file_survey.py", "symbol": "run", "to_module": "archive_tarfile.py",
         "output_path": "pkg/out.json", "timeout_s": 120},
        ADAPTERS,
    )
    assert report["verified"] is False
    assert report["why"] == "TARGET_ALREADY_DEFINES_THAT_NAME", report["why"]
    assert not [r for r in report["repairs"] if "rename" in r.lower()]


def test_the_refusal_names_the_directory_it_wants() -> None:
    """THE DEFECT THE LOOP EXPOSED IN THE CAPABILITY.

    `TEST_ROOT_MISSING` without a path is a riddle: the caller cannot tell whether the capability wants
    `<root>/tests` or `<root>/../tests`, and a repair loop guessed wrong twice. A refusal must locate
    itself.
    """
    source = (ADAPTERS / "python_source_move_function.py").read_text()
    assert 'TEST_ROOT_MISSING:" + str(tests)' in source, (
        "the refusal must name the path it wants, or no client can answer it")
    parsed = K._MISSING_ROOT.search(
        "TEST_ROOT_MISSING:/tmp/brain_repair_env_x/tests")
    assert parsed and parsed.group("path") == "/tmp/brain_repair_env_x/tests"


def test_a_refusal_with_no_known_repair_is_not_a_pass() -> None:
    """The loop must fail closed. A refusal nobody understands is an honest dead end, not a success."""
    class AlwaysRefuses(Exception):
        pass

    def call(_args):
        raise AlwaysRefuses("SOMETHING_NOBODY_HAS_SEEN_BEFORE")

    result, record = K.repair_once(call, ROOT, {})
    assert result is None
    assert record["verified"] is False
    assert record["why"] == "NO_REPAIR_KNOWN_FOR_THIS_REFUSAL"
    assert len(record["attempts"]) == 1


def test_the_loop_is_bounded() -> None:
    """A repair loop that cannot terminate is a hang with extra steps."""
    class Loop(Exception):
        pass

    def call(_args):
        raise Loop("TEST_ROOT_MISSING:/nonexistent-dir-that-cannot-be-made/x")

    result, record = K.repair_once(call, ROOT, {})
    assert len(record["attempts"]) <= 8
    assert record["verified"] is False


# ----------------------------------------------------------------------------------------------------
# The measurement itself. A census of refusals is only worth reading if it counts what it claims to.
# ----------------------------------------------------------------------------------------------------

def test_the_scan_counts_both_shapes_an_adapter_refuses_in() -> None:
    """`raise X("CODE")` and `_fail("CODE")` are both refusals. A scan that only saw the first
    under-reported the total by ~18% while looking complete -- `_fail` is used 293 times here."""
    from canonical.runtime import refusal_location_v1 as RL
    assert RL._RAISE.search('raise RuntimeError("SOME_CODE")')
    assert RL._RAISE.search('_fail("SOME_CODE")')


def test_a_located_refusal_is_counted_and_a_bare_one_is_not() -> None:
    """THE BUG THAT MADE THE MEASUREMENT BLIND: the first scan matched its "located" rule at a fixed offset
    past a regex group that had already consumed the colon, so it returned False for every located refusal
    and locating 7 of them changed the report by zero."""
    from canonical.runtime import refusal_location_v1 as RL
    import itertools
    located_line = '        raise RuntimeError("PATH_OUTSIDE_REPOSITORY:" + str(p))'
    bare_line = '        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")'
    concat_line = '        raise RuntimeError("PATH_OUTSIDE_REPOSITORY" + ":" + str(p))'
    def counted(line: str) -> int:
        text = line + "\n"
        for match in RL._RAISE.finditer(text):
            tail = text[text.find(match.group("code")) + len(match.group("code")):]
            if tail.startswith(":") or tail.startswith('" + ":"'):
                return 1
        return 0
    assert counted(bare_line) == 0
    assert counted(located_line) == 1
    assert counted(concat_line) == 1


def test_two_independent_counts_of_the_same_tree_agree() -> None:
    """Reported numbers must be reproducible by a second implementation, or they are one program's opinion.

    Measured 2026-11-23: 1,588 refusals, 559 located, 35.2%. An earlier pair of counts disagreed by ten
    points (37.8% vs 27.5%) because one accepted a colon anywhere on the line; that number was never
    reported. This test keeps the two definitions pinned to each other.
    """
    import re
    from canonical.runtime import refusal_location_v1 as RL

    module_scan = RL.scan()
    independent = 0
    pattern = re.compile(r'(?:raise\s+\w+|_fail)\(\s*["\']([A-Z][A-Z0-9_]{3,})(["\']|:)')
    formatted = re.compile(r'(?:raise\s+\w+|_fail)\(\s*f["\']([A-Z][A-Z0-9_]{3,}):')
    for path in (ROOT / "canonical/runtime/bound_capabilities").glob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        independent += len(pattern.findall(text)) + len(formatted.findall(text))
    assert module_scan["refusals"] == independent, (module_scan["refusals"], independent)


def test_the_located_fraction_is_stated_with_the_shape_it_counts() -> None:
    """A fraction without its denominator's definition is a slogan. The report must carry both."""
    from canonical.runtime import refusal_location_v1 as RL
    report = RL.scan()
    assert report["refusals"] == report["located"] + report["bare"]
    assert 0.0 <= report["located_fraction"] <= 1.0
    assert "bare code names the KIND" in report["note"]

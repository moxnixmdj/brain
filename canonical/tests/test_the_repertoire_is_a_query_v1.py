"""Tests for `the_repertoire_is_a_query_v1`: the machine's catalogue, read and bounded.

These tests never need the network. They check the three things the measurement stands on: that the reader is
bounded in bytes as well as seconds (an unbounded reader was killed by the kernel on `yes --help`), that an
option without an object is not counted as an action, and that the census cannot claim a capability it did not
execute.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import the_repertoire_is_a_query_v1 as R  # noqa: E402


# --------------------------------------------------------------------------------------------------
# The reader: bounded in bytes, not only in seconds
# --------------------------------------------------------------------------------------------------

def test_the_reader_is_bounded_in_bytes(tmp_path: pathlib.Path) -> None:
    """`yes --help` prints forever. A timeout alone does not bound a reader: the first run of this tool was
    killed by the kernel at 26 s having buffered gigabytes of it."""
    if shutil.which("yes") is None:
        pytest.skip("no yes on this box")
    code, out = R._run(("yes",), tmp_path, timeout=1.0)
    assert code == 124, "the reader must stop a program that never stops talking"
    assert len(out.encode()) <= R.OUTPUT_CAP


def test_the_reader_captures_a_real_failure(tmp_path: pathlib.Path) -> None:
    code, out = R._run(("cp",), tmp_path)
    assert code != 0
    assert out.strip(), "a failing program says why; that text is the only diagnostic there is"


# --------------------------------------------------------------------------------------------------
# The grammar: options are read off the page, never supplied
# --------------------------------------------------------------------------------------------------

PAGE_TEXT = """Usage: thing [OPTION]... [FILE]...
  -a, --all          change everything
  -b                 do the other thing
      --dry-run      print what would happen
      --abort        put it back
Report bugs to nobody.
"""


def test_options_are_parsed_from_the_page_with_their_own_line() -> None:
    page = R.Page(("thing",), PAGE_TEXT, len(PAGE_TEXT))
    options = dict(R.options_of(page))
    assert set(options) == {"-a", "--all", "-b", "--dry-run", "--abort"}, options
    assert "change everything" in options["-a"]
    assert "print what would happen" in options["--dry-run"]


def test_a_page_is_its_name_and_its_own_summary() -> None:
    """The document a need is matched against is the name plus the top of the page. Ranking whole pages made
    the wordiest page win every need: the first run answered "undo a merge" with `corelist -r`."""
    long_noise = R.Page(("noise",), "irrelevant " * 500, 0)
    named = R.Page(("git merge",), "Join two development histories", 0)
    scores = R.bm25([long_noise.name + " " + long_noise.text[:240],
                     named.name + " " + named.text[:240]], "give up a merge that went wrong")
    assert scores[1] > scores[0]


def test_the_stride_spans_the_whole_list() -> None:
    """A cap taken from the front of an alphabetical list is a sample of the letter A. The declared stride has
    to reach the end of it, or `tar` is never as likely as `cat`."""
    pages = [R.Page((name,), "x", 0) for name in ("a", "b", "c", "d", "e", "f", "g", "h")]
    sample = R.stride_sample(pages, 4)
    assert len(sample) == 4
    assert sample[0].prefix == ("a",)
    assert sample[-1].prefix == ("h",)


# --------------------------------------------------------------------------------------------------
# The census: an option is a modifier, and the object comes from the state
# --------------------------------------------------------------------------------------------------

def test_an_option_that_changes_nothing_is_recorded_as_changing_nothing(tmp_path: pathlib.Path) -> None:
    """`touch -c FILE` is accepted and changes no byte the digest can see. The census must call that what it
    is -- accepted, and inert -- rather than counting it as an action."""
    if shutil.which("touch") is None:
        pytest.skip("no touch on this box")
    pristine = R.fixture(tmp_path)
    page = R.Page(("touch",), "", 0)
    result = R.classify(page, "-c", pristine, tmp_path, "inert")
    assert result["accepted"] is True
    assert result["changed"] is False


def test_an_object_is_bound_only_when_the_program_asks_for_one(tmp_path: pathlib.Path) -> None:
    """`rm -r` with no operand says "missing operand"; the state then supplies one, and the act becomes real:
    a file disappears. That binding is the difference between a knob and an action."""
    if shutil.which("rm") is None:
        pytest.skip("no rm on this box")
    pristine = R.fixture(tmp_path)
    page = R.Page(("rm",), "", 0)
    result = R.classify(page, "-r", pristine, tmp_path, "bind")
    assert result["bound_operand"] is not None, result
    assert result["changed"] is True, "binding an object turned a knob into an act, and the digest saw it"


def test_the_verdict_cannot_pass_a_check_it_never_ran(tmp_path: pathlib.Path) -> None:
    """K4 and K5 are VOID, not met, when nothing mutated: a check that cannot be told apart from doing nothing
    has not been tested. The receipt must say so instead of banking a pass."""
    receipt = R.measure(tmp_path, None, census_cap=6, exec_sample=4)
    assert receipt["verdict"]["K4_a_guard_is_advertised_and_real"]["MET"] in (None, True, False)
    if receipt["summary"]["options_that_mutated"] == 0:
        assert receipt["verdict"]["K4_a_guard_is_advertised_and_real"]["MET"] is None
    assert receipt["summary"]["model_calls"] == 0
    assert receipt["summary"]["parameters_stored"] == 0
    assert receipt["schema"] == R.SCHEMA


def test_nothing_is_spelled_by_hand() -> None:
    """K8: the census may not carry a table of programs or options. It checks its own source."""
    # the fixture's own programs are allowed to appear; anything else that was executed may not be spelled
    assert R._spelled_in_source({"rows": [{"program": "git", "option": "--abort"}]}) == []
    # the check fires on any quoted name: `mount` is only in the declared DENY guard, so it is never executed,
    # and that is exactly why a quoted name is evidence the census was not written by hand
    assert R._spelled_in_source({"rows": [{"program": "mount", "option": "-a"}]}) == ["mount"]
    assert R._spelled_in_source({"rows": [{"program": "montage-im6", "option": "-alpha"}]}) == []


# --------------------------------------------------------------------------------------------------
# The row auditor: a photographed row must be a check, not history
# --------------------------------------------------------------------------------------------------

def test_every_row_carries_a_read_only_check_and_no_re_runnable_command(tmp_path: pathlib.Path) -> None:
    """A row's `executed_argv` is history -- re-running it would mutate the caller's directory -- while its
    `verification` is a read-only check that re-finds the row. The declaration floor requires the second and
    punishes a row that carries the first AS a predicate."""
    from canonical.tools import audit_measurement_row_v1 as M

    receipt = R.measure(tmp_path, None, census_cap=6, exec_sample=4)
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(receipt))
    for row in receipt["rows"]:
        assert "argv" not in row, "a row must not look like a re-runnable predicate"
        assert row["executed_argv"], "the command that was measured is still recorded, as history"
        assert row["verification"]["expect_exit"] == 0
        assert row["verification"]["argv"][1].endswith("audit_measurement_row_v1.py")
        result = M.audit(path, row["program"], row["option"])
        assert result["verdict"] == "PASS", result
    assert M.audit(path, "no-such-program-anywhere", "-x")["verdict"] == "FAIL"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

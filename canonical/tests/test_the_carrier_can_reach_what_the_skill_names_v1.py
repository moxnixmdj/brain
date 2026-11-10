"""A skill's paths must mean what the CARRIER thinks they mean.

THE DEFECT THIS PINS (r39 found it, r40 fixes it)
-------------------------------------------------
The carrier stages `workspace_root` as `/input`, copies it to `/work/project`, and runs the
argv with THAT as cwd. The carrier's filesystem contains the workspace and nothing else -- it
has never heard of the repository. So:

    ["sort","-u","data.txt"]                               exit 0  WORKS
    ["sort","-u","canonical/astra_runtime/tmp/x/data.txt"] exit 2  NO SUCH FILE

A skill compiled from a goal naming a repo-relative path stored an argv the carrier could
never satisfy, and it surfaced as FAIL_CLOSED__CARRIER_DID_NOT_ESTABLISH_CONFINEMENT -- a
SAFETY refusal standing in for "file not found". The learned capability was dead and the
error message pointed at the one part that was working.

THE FIX IS A TRANSLATION, NOT A WIDENING
----------------------------------------
`_carrier_path` rewrites an argument into the workspace-relative form ONLY when the named
file actually exists inside the staged workspace. Absolute paths outside it, `..` escapes,
flags and URLs are returned unchanged, so the carrier refuses them exactly as before.
Nothing gains reach.

WHY IT FIRST FAILED ANYWAY
--------------------------
The first version used `pathlib.relative_to`, which is a STRING operation, not an existence
test: `w/canonical/x/y` is trivially "inside" `w`, so a repo-relative path was "translated"
to itself and the carrier still failed. A path-shaped string is not a path. Existence is now
required, and `test_a_path_that_does_not_exist_is_left_alone` pins that.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import _carrier_path

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_BASE = _ROOT / "canonical" / "astra_runtime" / "tmp"


@pytest.fixture()
def work():
    d = pathlib.Path(tempfile.mkdtemp(prefix="cp_", dir=str(_BASE)))
    (d / "data.txt").write_text("a\nb\na\n", encoding="utf-8")
    yield d


def test_a_repo_relative_path_becomes_workspace_relative(work):
    arg = str((work / "data.txt").relative_to(_ROOT))
    assert _carrier_path(arg, work) == "data.txt"


def test_a_bare_filename_is_unchanged(work):
    assert _carrier_path("data.txt", work) == "data.txt"


def test_an_absolute_path_inside_the_workspace_becomes_relative(work):
    assert _carrier_path(str(work / "data.txt"), work) == "data.txt"


def test_a_path_outside_the_workspace_is_left_alone(work):
    """The nearest world: translation must never grant reach it did not have."""
    assert _carrier_path("/etc/hostname", work) == "/etc/hostname"


def test_a_path_that_does_not_exist_is_left_alone(work):
    """The bug inside the bug: `relative_to` succeeds without the file existing."""
    assert _carrier_path("canonical/definitely_not_here.txt", work) == "canonical/definitely_not_here.txt"


def test_flags_and_urls_are_untouched(work):
    for arg in ("-u", "--output", "https://example.com/x", ""):
        assert _carrier_path(arg, work) == arg


def test_an_escape_attempt_is_left_alone(work):
    assert _carrier_path("../../../etc/passwd", work) == "../../../etc/passwd"

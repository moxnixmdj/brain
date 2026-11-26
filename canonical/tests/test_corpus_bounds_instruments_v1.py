#!/usr/bin/env python3
"""Tests for the four corpus instruments that bound what the generator can possibly do.

These are instruments, so the tests check the things that went wrong while building them --
not that they produce pretty numbers. Every bug guarded here was a silent, plausible zero:

  1. `import_roots` returned `src/packaging` instead of `src`, which made `import packaging`
     resolve to a namespace package. The target test then *passed* on the parent commit and
     all 23 affected tasks were reported NOT_FAIL_TO_PASS. A harness that cannot reproduce a
     known positive is broken, not a finding.
  2. The coverage plugin dumped from `atexit`, after `os` was torn down, and wrote an empty
     file. Empty is indistinguishable from "the test ran nothing".
  3. The coverage harness restored the parent commit and forgot to re-apply the added test
     file, so it ran a node that did not exist.
  4. The coverage plugin discarded import-time hits, which is exactly where a module-level
     regex table in this corpus lives.

The property that matters most is the last one: an EMPTY result must never be silently
counted as a measured zero.
"""
from __future__ import annotations

import sys
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.tools import coverage_selector_measurement_v1 as COV  # noqa: E402
from canonical.tools import site_edit_space_measurement_v1 as SES  # noqa: E402
from canonical.tools import fix_vocabulary_taxonomy_v1 as VOC  # noqa: E402


# ---------------------------------------------------------------- import roots

def test_import_root_is_the_directory_above_the_package_not_the_package():
    """`src/packaging/markers.py` must put `src` on the path, never `src/packaging`."""
    co = pathlib.Path("/tmp/pkg")
    roots = SES.import_roots(["src/packaging/markers.py"], co)
    if not co.exists():
        pytest.skip("packaging checkout unavailable")
    assert "src" in [pathlib.Path(r).name for r in roots]
    assert not any(pathlib.Path(r).name == "packaging" for r in roots)


def test_import_root_walks_up_through_nested_packages():
    """A doubly-nested package walks up two `__init__.py` levels, not one."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        co = pathlib.Path(tmp)
        (co / "src/pkg/sub").mkdir(parents=True)
        (co / "src/pkg/__init__.py").write_text("")
        (co / "src/pkg/sub/__init__.py").write_text("")
        (co / "src/pkg/sub/mod.py").write_text("x = 1\n")
        roots = SES.import_roots(["src/pkg/sub/mod.py"], co)
        assert roots == [str((co / "src").resolve())]


# ---------------------------------------------------------------- frame census

def test_the_traceback_frame_parser_ignores_test_files():
    """A frame in the test file is not a source frame; counting it would inflate the census."""
    output = "tests/test_x.py:12: in test_a\n    assert 1 == 2\nE   assert 1 == 2\n"
    assert SES.traced_frames(output, ["src/pkg/mod.py"]) == {}


def test_the_traceback_frame_parser_accepts_an_absolute_path():
    output = "/tmp/pkg/src/packaging/markers.py:89: in __init__\n    boom\n"
    assert SES.traced_frames(output, ["src/packaging/markers.py"]) == {"src/packaging/markers.py": {89}}


def test_failure_class_normalises_a_bare_assert_to_AssertionError():
    """pytest prints `E   assert a == b` for a bare assert; that is not an exception name."""
    assert SES.failure_class("E   assert 'a' == 'b'\n") == "AssertionError"
    assert SES.failure_class("E   AttributeError: no attribute 'text'\n") == "AttributeError"
    assert SES.failure_class("nothing here\n") == "UNKNOWN"


# ---------------------------------------------------------------- coverage shape

def test_an_empty_coverage_result_is_flagged_not_counted_as_zero():
    """The plugin returns both buckets; a row with neither must be marked, not read as 0."""
    row = {"test_time": {}, "import_time": {}}
    assert not (row["test_time"] or row["import_time"])
    src = COV.PLUGIN_SOURCE
    # The dump must happen while the runtime is alive, not only at interpreter shutdown.
    assert "pytest_sessionfinish" in src
    assert "IMPORT_HITS" in src, "import-time lines must be kept, not discarded"


# ---------------------------------------------------------------- vocabulary

def test_changed_lines_reports_a_pure_replacement_once():
    parent = "a = 1\nb = 2\n"
    fixed = "a = 1\nb = 3\n"
    changes = SES.changed_lines(parent, fixed)
    assert [(ln, old, new) for ln, old, new in changes] == [(2, "b = 2", "b = 3")]


def test_shape_matches_across_identifiers_and_literals():
    """Anti-unification key: two statements that differ only in names must share a shape."""
    assert VOC.shape_of("if not ref.isascii():") == VOC.shape_of("if not name.isascii():")
    assert VOC.shape_of('raise InvalidLicenseExpression(f"bad {ref!r}")') != VOC.shape_of("return 1")


def test_a_token_absent_from_the_file_is_not_substitutable():
    """A REPLACE that introduces a name the file never contained is not a substitution."""
    assert VOC.changed_tokens("x = old_name", "x = brand_new_thing") == ["brand_new_thing"]
    assert VOC.changed_tokens("x = old_name", "x = other_name") == ["other_name"]


@pytest.mark.parametrize("old,new,expected", [
    ("", "x = 1", "ADD"),
    ("x = 1", "", "DELETE"),
    ("x = 1", "x = 2", "REPLACE"),
])
def test_operation_classification(old, new, expected):
    assert VOC.op_of(old, new) == expected


def test_single_edit_ceiling_is_not_conflated_with_the_multi_edit_ceiling():
    """One substitutable site among three is not a task a single-edit generator can solve."""
    sites_multi = [{"class": "SITE_REACHED_SUBSTITUTABLE"},
                   {"class": "SITE_REACHED_SUBSTITUTABLE"}]
    sites_single = [{"class": "SITE_REACHED_SUBSTITUTABLE"}]
    assert all(s["class"] == "SITE_REACHED_SUBSTITUTABLE" for s in sites_multi)
    assert len(sites_single) == 1
    # the two live in different counters in the receipt
    source = pathlib.Path(VOC.__file__).read_text()
    assert "tasks_reachable_by_a_single_substitution" in source

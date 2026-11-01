"""The census tool that produced the orphan map must itself be measurable.

A census is a measuring instrument. This session found two cases where an instrument lied: an
`audit()` that walked only one table, and a static import analysis that would have called a
same-file helper "orphan". So the tool is tested on a synthetic tree whose answer is known by
construction, including the two ways it could over-report:

  * a function called from another function **in the same file** is not evidence of an external
    caller -- it still counts as having no production caller, but the module may be reachable;
  * a module whose name appears as a **string literal** may be dispatched dynamically, so it
    must not be called unreachable.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.tools.census_orphan_capabilities_v1 import census, module_census  # noqa: E402


def _tree(tmp: pathlib.Path) -> pathlib.Path:
    pkg = tmp / "canonical" / "runtime"
    pkg.mkdir(parents=True)
    tests = tmp / "canonical" / "tests"
    tests.mkdir(parents=True)

    # called from another module -> LIVE
    (pkg / "used_module.py").write_text("def helper():\n    return 1\n")
    # never referenced anywhere -> ORPHAN
    (pkg / "dead_module.py").write_text("def lonely():\n    return 2\n")
    # only a test references it -> TEST_ONLY
    (pkg / "tested_module.py").write_text("def checked():\n    return 3\n")
    # internal call only, module never imported -> ORPHAN function, unreachable module
    (pkg / "internal_module.py").write_text(
        "def _inner():\n    return 4\n\n\ndef outer():\n    return _inner()\n"
    )
    # named as a string somewhere -> possibly dynamic, must not be 'unreachable'
    (pkg / "dyn_module.py").write_text("def dynamic():\n    return 5\n")

    (pkg / "consumer.py").write_text(
        "from canonical.runtime.used_module import helper\n"
        "import importlib\n\n\n"
        "def go():\n"
        "    importlib.import_module('canonical.runtime.dyn_module')\n"
        "    return helper()\n"
    )
    (tests / "test_tested_module.py").write_text(
        "from canonical.runtime.tested_module import checked\n\n\n"
        "def test_checked():\n"
        "    assert checked() == 3\n"
    )
    return tmp / "canonical"


def test_name_level_census_classifies_each_case(tmp_path):
    report = census(_tree(tmp_path))
    status = {r["name"]: r["status"] for r in report["rows"]}

    assert status["helper"] == "LIVE"
    assert status["lonely"] == "ORPHAN"
    assert status["checked"] == "TEST_ONLY"


def test_a_same_file_caller_does_not_make_a_name_live(tmp_path):
    report = census(_tree(tmp_path))
    status = {r["name"]: r["status"] for r in report["rows"]}
    # `outer` calls `_inner` in the same file; `outer` itself is nobody's dependency.
    assert status["outer"] == "ORPHAN"


def test_module_census_excludes_string_referenced_modules(tmp_path):
    report = module_census(_tree(tmp_path))
    flagged = {pathlib.Path(p).stem for p in report["modules"]}

    assert "dead_module" in flagged
    assert "internal_module" in flagged
    assert "dyn_module" not in flagged, "named as a string -> possibly dynamic dispatch"
    assert "used_module" not in flagged


def test_module_census_counts_are_consistent(tmp_path):
    report = module_census(_tree(tmp_path))
    assert report["not_named_as_string"] == len(report["modules"])
    assert report["with_matching_test"] + report["without_any_test"] == report["not_named_as_string"]
    assert report["no_static_importer"] >= report["not_named_as_string"]

"""Standing the check: the two things that made 0 of 42 real files verifiable, and the third
thing that would have made "verifiable" a lie.

The previous round measured the limit exactly: one demonstration generalises precisely
(0.529 of the developers' changes, precision 1.000), a wrong generalisation is turned into a
refusal only where the target file's own tests run, and on real migrated projects those tests
ran on **0 of 42** files -- half because no test module imported the changed file, half because
a dependency was missing. It named the next action: stand up the check (dependencies first, a
test-entry finder that reports its own uncertainty second, then count what becomes verified).

These tests pin that work, offline:

1. **A declared dependency gets stood up** into an isolated venv and the suite then runs --
   the install itself is faked here (no index from a test); the index is proven on the real
   corpus record, not in a unit test.
2. **A failed install is named** (`INSTALL_FAILED`, with pip's tail), never papered over; a
   project that declares nothing is not guessed at (`NO_DECLARED_DEPENDENCIES`).
3. **A suite that ran no tests is not a check** -- unittest collecting 0 and no pytest to fall
   back on is a named refusal, not a green light. (When the project's own pytest IS importable,
   pytest-style tests count as the suite they are.)
4. **The oracle is resolved per target file**: a file no test imports is refused by that file's
   own path, even when a sibling's suite passes -- the first version of the checker bound one
   entry to every path of the task.
5. **The finder reports its own uncertainty**: nonstandard test names (`*_test.py`) are found
   and listed as candidates; a test that reaches the file only through an intermediate module
   is found and labelled INDIRECT, and still catches a wrong edit through that path.

Zero model calls, no network (the only subprocesses are local venvs, unittest and pytest),
$0. Authority: NONE.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.tools import generalization_rung_gradient_v1 as measure  # noqa: E402


NEEDS_THIRD_PARTY = {
    "pkg/__init__.py": "",
    "pkg/mod.py": "import thirdparty\n\n\ndef f():\n    return thirdparty.VALUE\n",
    "tests/__init__.py": "",
    "tests/test_mod.py": (
        "import unittest\n\nfrom pkg import mod\n\n\nclass T(unittest.TestCase):\n"
        "    def test_value(self):\n        self.assertEqual(mod.f(), 7)\n"
    ),
    "requirements.txt": "thirdparty==1.0\n",
}


def _site_packages(python: str) -> pathlib.Path:
    root = pathlib.Path(python).parent.parent
    return next(root.glob("lib/python*/site-packages"))


def test_a_declared_dependency_gets_stood_up_and_the_suite_then_runs(monkeypatch):
    """The6 of 12: tests import a package the machine does not have. Declared -> installed into
    an isolated venv -> the suite runs. The installer is faked (writes the module into the venv);
    everything else -- venv creation, interpreter switch, re-run -- is the real path."""
    def fake_install(self, python: str, args) -> tuple[int, str]:
        (_site_packages(python) / "thirdparty.py").write_text("VALUE = 7\n", encoding="utf-8")
        return 0, ""

    monkeypatch.setattr(measure.Check, "_pip_install", fake_install)
    check = measure.Check("tests", dict(NEEDS_THIRD_PARTY), "pkg/mod.py")
    assert check.available is True, check.reason
    assert check.reason == ""
    assert check.standing["attempted"] is True
    assert check.standing["outcome"] == "STOOD"
    assert check.standing["source"] == "requirements_txt"
    assert check.accepts("pkg/mod.py", NEEDS_THIRD_PARTY["pkg/mod.py"]) is True
    check.close()
    assert check._venv_dir is None, "close() must take the venv with it"


def test_an_install_that_fails_is_named_and_keeps_pips_tail(monkeypatch):
    """No silent fallback: INSTALL_FAILED is the record's answer, the suite stays unavailable,
    and the half-built venv does not linger."""
    monkeypatch.setattr(measure.Check, "_pip_install",
                        lambda self, python, args: (1, "No matching distribution for thirdparty"))
    check = measure.Check("tests", dict(NEEDS_THIRD_PARTY), "pkg/mod.py")
    assert check.available is False
    assert check.reason == "CHECK_DEPENDENCY_MISSING"
    assert check.standing["outcome"] == "INSTALL_FAILED"
    assert "No matching distribution" in check.standing["detail"]
    assert check._venv_dir is None
    check.close()


def test_a_project_that_declares_nothing_is_not_guessed_at():
    """The other half of honesty: an undeclared import stays CHECK_DEPENDENCY_MISSING.
    Guessing package names would be a new way to be confidently wrong."""
    project = {
        "pkg/__init__.py": "",
        "pkg/mod.py": "import ghostpackage\n\n\ndef f():\n    return 1\n",
        "tests/__init__.py": "",
        "tests/test_mod.py": (
            "import unittest\n\nfrom pkg import mod\n\n\nclass T(unittest.TestCase):\n"
            "    def test_f(self):\n        self.assertEqual(mod.f(), 1)\n"
        ),
    }
    check = measure.Check("tests", project, "pkg/mod.py")
    assert check.available is False
    assert check.reason == "CHECK_DEPENDENCY_MISSING"
    assert check.standing["outcome"] == "NO_DECLARED_DEPENDENCIES"
    assert check._venv_dir is None, "no manifest, no venv"
    check.close()


def test_a_suite_that_ran_no_tests_is_not_a_check(monkeypatch):
    """The vacuity guard: pytest-style tests with no pytest to run them means unittest collects
    0 -- and 0 tests verify nothing. Refused by name."""
    project = {
        "pkg/__init__.py": "",
        "pkg/thing.py": "X = 1\n",
        "tests/__init__.py": "",
        "tests/test_thing.py": "from pkg.thing import X\n\n\ndef test_x():\n    assert X == 1\n",
    }
    monkeypatch.setattr(measure.Check, "_pytest_importable", lambda self: False)
    check = measure.Check("tests", project, "pkg/thing.py")
    assert check.available is False
    assert check.reason == "CHECK_NO_DISCOVERABLE_TESTS"
    assert check.accepts("pkg/thing.py", "X = 2\n") is False
    assert check.path_reasons.get("CHECK_NO_DISCOVERABLE_TESTS", 0) >= 1
    check.close()


def test_when_the_projects_own_pytest_is_importable_those_tests_are_the_suite():
    """The other side of the same rule: the project's tests are written for pytest, pytest is
    importable here, so they run and they count. (This file itself imports pytest, so the
    interpreter running it has it -- that is the precondition, stated.)"""
    project = {
        "pkg/__init__.py": "",
        "pkg/thing.py": "X = 1\n",
        "tests/__init__.py": "",
        "tests/test_thing.py": "from pkg.thing import X\n\n\ndef test_x():\n    assert X == 1\n",
    }
    check = measure.Check("tests", project, "pkg/thing.py")
    assert check.available is True, check.reason
    assert check.accepts("pkg/thing.py", "X = 1\n") is True
    check.close()


def test_the_oracle_is_resolved_for_the_file_being_asked_about():
    """A sibling's suite is not this file's oracle. pkg/b has no test that imports it; the old
    checker (one entry bound to the task's first path) would have run pkg/a's tests after
    writing pkg/b and accepted the edit as 'checked'. Now that file is refused by name."""
    project = {
        "pkg/__init__.py": "",
        "pkg/a.py": "def f():\n    return 1\n",
        "pkg/b.py": "def g():\n    return 2\n",
        "tests/__init__.py": "",
        "tests/test_a.py": (
            "import unittest\n\nfrom pkg import a\n\n\nclass T(unittest.TestCase):\n"
            "    def test_f(self):\n        self.assertEqual(a.f(), 1)\n"
        ),
    }
    check = measure.Check("tests", project, "pkg/a.py")
    assert check.available is True, check.reason
    assert check.test_entry["confidence"] == "DIRECT"
    assert check.accepts("pkg/a.py", "def f():\n    return 1\n") is True
    assert check.accepts("pkg/b.py", "def g():\n    return 999\n") is False
    assert check.path_reasons.get("CHECK_NO_TEST_MODULE", 0) == 1
    check.close()


def test_a_test_file_named_the_other_way_is_found_and_listed_as_a_candidate():
    """`thing_test.py` is a test of `pkg.thing` in a great many projects; the finder only knew
    `test_*.py`. Found now, and the candidate list is on the receipt."""
    project = {
        "pkg/__init__.py": "",
        "pkg/thing.py": "def f():\n    return 1\n",
        "pkg/thing_test.py": (
            "import unittest\n\nfrom pkg import thing\n\n\nclass T(unittest.TestCase):\n"
            "    def test_f(self):\n        self.assertEqual(thing.f(), 1)\n"
        ),
    }
    check = measure.Check("tests", project, "pkg/thing.py")
    assert check.available is True, check.reason
    assert check.test_entry["chosen"] == "pkg.thing_test"
    assert check.test_entry["confidence"] == "DIRECT"
    assert any(row["path"] == "pkg.thing_test" for row in check.test_entry["candidates"])
    check.close()


def test_a_test_that_reaches_the_file_only_through_another_module_is_found_and_says_so():
    """No test names pkg.thing directly; tests/test_middle imports pkg.middle, which imports
    pkg.thing. That is an oracle for pkg.thing -- labelled INDIRECT, not dressed up as DIRECT --
    and it catches a wrong edit to pkg.thing through middle's assertion."""
    project = {
        "pkg/__init__.py": "",
        "pkg/thing.py": "def f():\n    return 1\n",
        "pkg/middle.py": "from pkg import thing\n\n\ndef h():\n    return thing.f()\n",
        "tests/__init__.py": "",
        "tests/test_middle.py": (
            "import unittest\n\nfrom pkg import middle\n\n\nclass T(unittest.TestCase):\n"
            "    def test_h(self):\n        self.assertEqual(middle.h(), 1)\n"
        ),
    }
    check = measure.Check("tests", project, "pkg/thing.py")
    assert check.available is True, check.reason
    assert check.test_entry["confidence"] == "INDIRECT"
    assert check.test_entry["candidates"][0]["imports"] == "indirect"
    assert check.accepts("pkg/thing.py", "def f():\n    return 1\n") is True
    assert check.accepts("pkg/thing.py", "def f():\n    return 999\n") is False, (
        "the wrong generalisation must fail middle's assertion, not sail through"
    )
    check.close()


def test_a_residual_missing_module_is_named_not_bucketed(monkeypatch):
    """Standing can succeed and the import can still fail (the project did not declare what the
    tests need). Then the record must say WHICH module is missing -- 'still missing a dependency'
    is a bucket, 'missing: thirdparty' is the next operator."""
    def fake_install_noop(self, python: str, args) -> tuple[int, str]:
        return 0, ""   # pip succeeded; nothing the suite needs was in what it declared

    monkeypatch.setattr(measure.Check, "_pip_install", fake_install_noop)
    check = measure.Check("tests", dict(NEEDS_THIRD_PARTY), "pkg/mod.py")
    assert check.available is False
    assert check.reason == "CHECK_DEPENDENCY_MISSING"
    assert check.standing["outcome"] == "STOOD"
    assert check.missing_modules == ["thirdparty"], check.missing_modules
    check.close()


def test_a_candidate_that_defines_no_tests_loses_to_one_that_does():
    """stem's shape: everything sits under test/, several files import the target, and the
    alphabetically-first of them (test/arguments.py) defines no test at all. The one I would run
    is the one that defines tests."""
    project = {
        "pkg/__init__.py": "",
        "pkg/thing.py": "def f():\n    return 1\n",
        "tests/__init__.py": "",
        "tests/aaa_arguments.py": "from pkg import thing\n\nMARKER = thing.f()\n",
        "tests/zzz_real.py": (
            "import unittest\n\nfrom pkg import thing\n\n\nclass T(unittest.TestCase):\n"
            "    def test_f(self):\n        self.assertEqual(thing.f(), 1)\n"
        ),
    }
    check = measure.Check("tests", project, "pkg/thing.py")
    assert check.test_entry["chosen"] == "tests.zzz_real", check.test_entry
    assert check.available is True, check.reason
    assert check.accepts("pkg/thing.py", "def f():\n    return 999\n") is False
    check.close()


def test_extras_are_a_declared_dependency_not_a_dev_afterthought(monkeypatch):
    """setup.py's extras_require = {"test": [...]} is the project declaring its test tools.
    They belong in the standing attempt -- pytest in an extra is how half these projects say
    'install this to run my suite'."""
    seen: list[list[str]] = []

    def fake_install(self, python: str, args) -> tuple[int, str]:
        seen.append(list(args))
        (_site_packages(python) / "mock.py").write_text("class Mock:\n    pass\n", encoding="utf-8")
        return 0, ""

    monkeypatch.setattr(measure.Check, "_pip_install", fake_install)
    project = {
        "pkg/__init__.py": "",
        "pkg/thing.py": "def f():\n    return 1\n",
        "tests/__init__.py": "",
        "tests/test_thing.py": (
            "import unittest\n\nfrom mock import Mock\n\nfrom pkg import thing\n\n\n"
            "class T(unittest.TestCase):\n"
            "    def test_f(self):\n"
            "        self.assertTrue(Mock())\n"
            "        self.assertEqual(thing.f(), 1)\n"
        ),
        "setup.py": (
            "from setuptools import setup\n\n"
            "setup(name='thing', extras_require={'test': ['mock']})\n"
        ),
    }
    check = measure.Check("tests", project, "pkg/thing.py")
    assert check.available is True, check.reason
    assert check.standing["outcome"] == "STOOD"
    assert any("mock" in arg for args in seen for arg in args), seen
    check.close()


def test_a_still_missing_module_the_manifest_names_gets_installed(monkeypatch):
    """The shape the corpus kept producing (django, graphene, aexpect): the literal parser
    misses how the dependency is written, standing declares nothing, the suite still cannot
    import -- and the name IS in the project's own setup.py. Then it gets installed, and the
    check runs. A name the manifests do not spell out is still refused (see the NO_DECLARED
    test above)."""
    def fake_install(self, python: str, args) -> tuple[int, str]:
        (_site_packages(python) / "thirdparty.py").write_text("VALUE = 7\n", encoding="utf-8")
        return 0, ""

    monkeypatch.setattr(measure.Check, "_pip_install", fake_install)
    project = {
        "pkg/__init__.py": "",
        "pkg/mod.py": "import thirdparty\n\n\ndef f():\n    return thirdparty.VALUE\n",
        "tests/__init__.py": "",
        "tests/test_mod.py": (
            "import unittest\n\nfrom pkg import mod\n\n\nclass T(unittest.TestCase):\n"
            "    def test_value(self):\n        self.assertEqual(mod.f(), 7)\n"
        ),
        "setup.py": (
            "from setuptools import setup\n\n"
            "def deps():\n    return ['thirdparty']\n\n"
            "setup(name='mod', install_requires=deps())\n"
        ),
    }
    check = measure.Check("tests", project, "pkg/mod.py")
    assert check.available is True, check.reason
    assert check.standing["outcome"] == "NO_DECLARED_DEPENDENCIES", check.standing
    assert check.standing.get("repaired") == ["thirdparty"], check.standing
    assert check.missing_modules == ["thirdparty"]
    check.close()


def test_the_corpus_carries_the_manifests_the_check_must_read():
    """The instrument bug this round found: fetch_tree kept only *.py, so every real task's
    declarations (requirements.txt, pyproject.toml, setup.cfg, extension.json) were filtered out
    before the check ever saw them -- and six tasks read as NO_DECLARED for dependencies their
    own manifests named. Sources and manifests come through; wheels and data do not."""
    assert measure._carries("pkg/mod.py") is True
    assert measure._carries("repo/requirements.txt") is True
    assert measure._carries("repo/requirements-dev.txt") is True
    assert measure._carries("repo/pyproject.toml") is True
    assert measure._carries("repo/setup.cfg") is True
    assert measure._carries("repo/extension.json") is True
    assert measure._carries("repo/Pipfile") is True
    assert measure._carries("repo/wheel.whl") is False
    assert measure._carries("repo/data/model.pkl") is False
    assert measure._carries("repo/docs/readme.md") is False

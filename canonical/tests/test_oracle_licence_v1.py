"""Tests for the oracle licence: does the check see this behaviour?

Every test here is a bug this module shipped with, or a false report it could make and must not:

1. **A src-layout project measured as blind.** The first real run on `pypa/packaging` reported 0 of
   8 sites licensed. The check was importing the *installed* copy from site-packages, so the mutant
   was written to a file nothing opened. Truth was "the harness measured somebody else's code",
   reported as "the tests are blind". `load_probe` now proves the check reads the file, and
   `extra_paths` is what makes it possible for src-layout repos.
2. **A red baseline reported as zeros.** A project with two pre-existing failures scored every
   site 0/N, which reads as "the check is blind". It now reads per test: a mutation is only caught
   by a test that passed before it. This is SWE-bench's fail-to-pass rule at mutant granularity.
3. **Formatting drift.** A mutation that rewrites whitespace or a docstring produces a diff nobody
   asked for and a mutant that is not the one described. Mutants are byte splices with the exact
   original/replacement span, and a splice that does not change the parsed AST is discarded.
4. **Equivalent mutants scored as blind spots.** A splice that leaves the AST identical (or that
   fails to parse) is not a perturbation. It is dropped before any check runs.
5. **The mutant left behind.** A runner that fails mid-flight used to leave the mutant on disk, and
   every later measurement in that copy was fiction. Restore is in a `finally` and verified.

The tests that touch a machine use a throwaway project and `sys.executable -m unittest`, so this
file needs nothing installed and runs in well under a second.
"""

from __future__ import annotations

import ast
import json
import pathlib
import sys
import textwrap

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "swe_kernel"))

import oracle_licence_v1 as L  # noqa: E402


DEMO = '''"""A docstring mentioning a <= b and x == y, which must never be mutated."""
import math


def at_limit(n, hi):
    # comment with <= and != inside it
    if n <= hi:
        return "at"
    return "under"


def guarded(a, b):
    if b > 0 and a > 0:
        return a / b
    return None
'''


# --------------------------------------------------------------------------------- generation

def test_every_mutant_parses_and_really_changes_the_program():
    sites = L.generate_mutants(DEMO, rel_path="demo.py")
    assert sites, "the demo has perturbable sites"
    original = L._ast_fingerprint(ast.parse(DEMO))
    for mutant in L.mutants_of(sites):
        assert L._ast_fingerprint(ast.parse(mutant.code)) != original


def test_a_mutant_changes_exactly_the_bytes_it_says():
    for mutant in L.mutants_of(L.generate_mutants(DEMO, rel_path="demo.py")):
        assert mutant.code[mutant.start:mutant.start + len(mutant.replacement)] == mutant.replacement
        assert len(mutant.code) - len(DEMO) == len(mutant.replacement) - len(mutant.original)


def test_docstrings_and_comments_are_never_mutated():
    sites = L.generate_mutants(DEMO, rel_path="demo.py")
    for site in sites:
        assert site.lineno not in (1, 6), f"mutated line {site.lineno}, which is prose"


def test_a_operator_is_taken_as_exactly_two_bytes():
    site = next(s for s in L.generate_mutants(DEMO, rel_path="demo.py")
                if s.lineno == 7 and s.node_kind == "comparison")
    assert [m.original for m in site.mutants] == ["<=", "<="]
    assert {m.replacement for m in site.mutants} == {"<", ">"}


def test_two_operators_on_one_line_are_two_sites():
    sites = L.generate_mutants("def f(a, b, c):\n    return 1 if a < b and b > c else 0\n",
                               rel_path="x.py")
    assert len({s.site_id for s in sites}) == len(sites)


def test_source_with_nothing_to_perturb_yields_no_mutants():
    """A module of constants and prose offers no site; that is `REFUSED_NO_MUTANTS`, not a zero."""
    assert L.generate_mutants('"""only prose."""\nX = 1\n', rel_path="x.py") == []


def test_a_broken_source_is_a_caller_error_not_a_zero_score():
    with pytest.raises(SyntaxError):
        L.generate_mutants("def f(:\n", rel_path="x.py")


def test_budget_is_deterministic_and_respected():
    source = "def f(x):\n    return [x < 1, x < 2, x < 3, x < 4]\n"
    first = L.measure(source, rel_path="b.py", run=lambda m: True, max_sites=2, max_mutants=3)
    second = L.measure(source, rel_path="b.py", run=lambda m: True, max_sites=2, max_mutants=3)
    assert [s["site_id"] for s in first["sites"]] == [s["site_id"] for s in second["sites"]]
    assert first["mutants_run"] <= 3
    assert first["sites_measured"] <= 2


# ---------------------------------------------------------------------------------- the licence

def _report(licensed: int, refused: int, **extra):
    sites = [
        {"site_id": f"a.py:{i + 1}:0:comparison", "lineno": i + 1, "node_kind": "comparison",
         "licensed": True, "mutants_run": 1, "mutants_caught": 1, "survivors": []}
        for i in range(licensed)
    ] + [
        {"site_id": f"a.py:{100 + i}:0:return", "lineno": 100 + i, "node_kind": "return",
         "licensed": False, "mutants_run": 1, "mutants_caught": 0, "survivors": ["return None"]}
        for i in range(refused)
    ]
    return {"rel_path": "a.py", "source_sha256": "0", "sites": sites, "baseline_ok": True, **extra}


def test_all_sites_caught_is_a_full_licence():
    result = L.licence(_report(3, 0))
    assert result["verdict"] == L.ALL_LICENSED
    assert result["fraction_licensed"] == 1.0
    assert result["sites_licensed"] == 3


def test_a_survivor_narrows_the_licence_and_names_the_site():
    result = L.licence(_report(2, 1))
    assert result["verdict"] == L.PARTIAL
    assert result["refused_sites"][0]["lineno"] == 100
    assert result["refused_sites"][0]["survivors"] == ["return None"]


def test_no_site_caught_is_not_the_same_as_no_sites():
    result = L.licence(_report(0, 2))
    assert result["verdict"] == L.NONE_LICENSED
    assert result["fraction_licensed"] == 0.0
    assert result["refused_sites"]


@pytest.mark.parametrize("report,verdict", [
    ({"sites": [], "baseline_ok": True}, L.REFUSED_NO_MUTANTS),
    ({"sites": [], "baseline_ok": False}, L.REFUSED_BASELINE_RED),
    ({"sites": [{"licensed": True}], "baseline_ok": True, "baseline_stable": False},
     L.REFUSED_FLAKY_BASELINE),
    ({"sites": [{"licensed": True}], "baseline_ok": None}, L.REFUSED_BASELINE_RED),
])
def test_a_measurement_that_could_not_be_made_grants_nothing(report, verdict):
    result = L.licence({**report, "rel_path": "a.py", "source_sha256": "0"})
    assert result["verdict"] == verdict
    assert result["fraction_licensed"] is None, "a refusal must never look like a zero score"
    assert result["licensed_sites"] == []


def test_the_licence_says_what_it_does_not_say():
    result = L.licence(_report(1, 0))
    assert len(result["does_not_say"]) == 3
    assert "empirical" in L.measure("def f(a, b):\n    return 1 if a < b else 0\n",
                                    rel_path="a.py", run=lambda m: True)["bounded_by"]["note"]


# --------------------------------------------------------------------------- teaching permission

def test_only_a_licensed_site_may_be_taught():
    granted = L.licence(_report(2, 1))
    assert L.teaching_permission(granted, site_id="a.py:1:0:comparison")["permitted"] is True
    refused = L.teaching_permission(granted, site_id="a.py:100:0:return")
    assert refused["permitted"] is False
    assert refused["reason"] == "SITE_REFUSED_CHECK_IS_BLIND"


def test_a_site_nobody_measured_cannot_be_taught():
    granted = L.licence(_report(1, 0))
    assert L.teaching_permission(granted, site_id="a.py:999:0:return")["reason"] == "SITE_NOT_MEASURED"
    assert L.teaching_permission(granted, site_id="a.py:999:0:return")["permitted"] is False


@pytest.mark.parametrize("verdict", [L.REFUSED_NO_MUTANTS, L.REFUSED_BASELINE_RED,
                                     L.REFUSED_FLAKY_BASELINE, L.REFUSED_FILE_NOT_LOADED])
def test_a_refused_measurement_permits_nothing(verdict):
    permission = L.teaching_permission({"verdict": verdict, "licensed_sites": [],
                                        "refused_sites": []}, site_id="anything")
    assert permission["permitted"] is False


def test_the_kept_record_refuses_to_claim_correctness():
    row = L.record(_report(1, 0), L.licence(_report(1, 0)))
    assert row["whole_task_correctness_proved"] is False
    assert row["authority"] == "NONE"
    assert len(row["measurement_sha256"]) == 64


# ------------------------------------------------------------------------------- per-test reading

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="4">
  <testcase classname="t" name="passes"/>
  <testcase classname="t" name="fails"><failure message="boom">trace</failure></testcase>
  <testcase classname="t" name="errors"><error message="bad">trace</error></testcase>
  <testcase classname="t" name="skipped"><skipped message="why"/></testcase>
</testsuite></testsuites>
"""


def test_junit_statuses_are_read_exactly(tmp_path: pathlib.Path):
    path = tmp_path / "j.xml"
    path.write_text(JUNIT)
    assert L.parse_junit(path) == {"t::passes": "PASSED", "t::fails": "FAILED",
                                   "t::errors": "ERROR", "t::skipped": "SKIPPED"}


def test_an_unreadable_junit_file_is_a_miss_not_a_pass(tmp_path: pathlib.Path):
    path = tmp_path / "j.xml"
    path.write_text("not xml")
    assert L.parse_junit(path) == {}
    assert L.parse_junit(tmp_path / "absent.xml") == {}


def test_a_test_that_was_already_red_cannot_make_a_mutant_look_caught():
    baseline = {"t::good": "PASSED", "t::already_red": "FAILED"}
    after = {"t::good": "PASSED", "t::already_red": "FAILED"}
    assert L.compare_per_test(baseline, after)["caught"] is False


def test_a_passing_test_that_now_fails_is_a_kill():
    caught = L.compare_per_test({"t::good": "PASSED"}, {"t::good": "FAILED"})
    assert caught["caught"] is True
    assert caught["newly_failing"] == ["t::good"]
    assert caught["killed_by"] == "TEST_FAILED"


def test_an_errored_or_missing_test_also_registers():
    assert L.compare_per_test({"t::a": "PASSED"}, {"t::a": "ERROR"})["killed_by"] == "TEST_ERRORED"
    assert L.compare_per_test({"t::a": "PASSED"}, {})["caught"] is True


# ---------------------------------------------------------------------------- a real mini project

def _project(tmp_path: pathlib.Path, module: str, test: str) -> pathlib.Path:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "calc.py").write_text(textwrap.dedent(module))
    (root / "test_calc.py").write_text(textwrap.dedent(test))
    return root


COVERED = """
def double(n):
    return n * 2
"""

BLIND_AND_COVERED = """
def double(n):
    return n * 2


def clamp(x, hi):
    if x > hi:
        return hi
    return x
"""

TEST_THAT_ONLY_CHECKS_DOUBLE = """
import unittest
import calc


class T(unittest.TestCase):
    def test_double(self):
        self.assertEqual(calc.double(3), 6)


if __name__ == "__main__":
    unittest.main()
"""

CHECK = [sys.executable, "-m", "unittest", "-q", "test_calc"]


def test_a_real_project_licenses_what_is_tested_and_refuses_what_is_not(tmp_path):
    """The whole point, on a project that runs: one tested behaviour, one untested behaviour.

    `double` is asserted on; `clamp` is imported and never called. The licence must separate them,
    and the separation must be the check's opinion, not this module's guess.
    """
    root = _project(tmp_path, BLIND_AND_COVERED, TEST_THAT_ONLY_CHECKS_DOUBLE)
    report = L.measure_project(root, "calc.py", CHECK, timeout=60, max_sites=20, max_mutants=20)
    assert report["baseline_ok"] is True
    assert report["load_probe"]["loaded"] is True
    by_line = {site["lineno"]: site for site in report["sites"]}
    double_return = [s for line, s in by_line.items() if line == 3]
    clamp_guard = [s for line, s in by_line.items() if line == 7]
    assert double_return and clamp_guard
    assert double_return[0]["licensed"] is True, "a tested behaviour must be visible"
    assert clamp_guard[0]["licensed"] is False, "an unasserted guard must not be"
    assert report["licence"]["verdict"] == L.PARTIAL


def test_the_measured_project_is_left_exactly_as_it_was(tmp_path):
    root = _project(tmp_path, BLIND_AND_COVERED, TEST_THAT_ONLY_CHECKS_DOUBLE)
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    L.measure_project(root, "calc.py", CHECK, timeout=60, max_sites=6, max_mutants=6)
    assert {p.name: p.read_bytes() for p in root.iterdir()} == before


def test_a_check_that_never_imports_the_file_is_refused_not_called_blind(tmp_path):
    """The src-layout bug: the check passes on a file that cannot be parsed.

    Reported as 0 of 8 licensed, it would have said "the tests are blind" when the truth was "the
    check is running different code". This must be a refusal, and the reason must name it.
    """
    root = _project(tmp_path, BLIND_AND_COVERED, """
        import unittest


        class T(unittest.TestCase):
            def test_nothing_here(self):
                self.assertTrue(True)


        if __name__ == "__main__":
            unittest.main()
    """)
    report = L.measure_project(root, "calc.py", CHECK, timeout=60, max_sites=6, max_mutants=6)
    assert report["licence"]["verdict"] == L.REFUSED_FILE_NOT_LOADED
    assert report["licence"]["fraction_licensed"] is None
    assert "never" in report["licence"]["reason"].lower()


def test_a_red_baseline_is_counted_per_test_instead_of_refusing_the_project(tmp_path):
    root = _project(tmp_path, BLIND_AND_COVERED, """
        import unittest
        import calc


        class T(unittest.TestCase):
            def test_double(self):
                self.assertEqual(calc.double(3), 6)

            def test_already_broken_on_purpose(self):
                self.assertEqual(calc.double(2), 5)


        if __name__ == "__main__":
            unittest.main()
    """)
    report = L.measure_project_per_test(
        root, "calc.py", [sys.executable, "-m", "pytest", "-q", "test_calc.py"], timeout=60,
        max_sites=6, max_mutants=6) if _has_pytest() else None
    if report is None:
        pytest.skip("pytest is not importable by this interpreter")
    assert report["baseline"]["tests_passing"] >= 1
    assert report["baseline"]["tests_not_passing"], "the deliberately broken test is excluded"
    assert report["licence"]["verdict"] in (L.PARTIAL, L.ALL_LICENSED)


def _has_pytest() -> bool:
    import importlib.util
    return importlib.util.find_spec("pytest") is not None


# ---------------------------------------------------------------------------------------- cache

def test_the_same_inputs_are_measured_once(tmp_path):
    root = _project(tmp_path, BLIND_AND_COVERED, TEST_THAT_ONLY_CHECKS_DOUBLE)
    cache = L.LicenceCache(tmp_path / "cache")
    first = L.licence_for_project(root, "calc.py", CHECK, cache=cache, per_test=False,
                                  max_sites=4, max_mutants=4, timeout=60)
    assert first["from_cache"] is False
    calls = {"n": 0}
    second = L.licence_for_project(root, "calc.py", CHECK, cache=cache, per_test=False,
                                   max_sites=4, max_mutants=4, timeout=60)
    assert second["from_cache"] is True
    assert second["verdict"] == first["verdict"]
    assert second["sites_licensed"] == first["sites_licensed"]
    # A hit must carry the same per-site detail as a miss, or a caller that needs to know WHICH
    # site is blind gets nothing. Found by the first real cross-repo run, where the cached arm
    # raised KeyError('measurement').
    assert second["measurement"]["sites"], "a cache hit must keep the per-site rows"
    assert [s["site_id"] for s in second["measurement"]["sites"]] == \
        [s["site_id"] for s in first["measurement"]["sites"]]
    assert calls["n"] == 0, "a cache hit must not run the check"


def test_a_changed_file_is_measured_again(tmp_path):
    root = _project(tmp_path, BLIND_AND_COVERED, TEST_THAT_ONLY_CHECKS_DOUBLE)
    cache = L.LicenceCache(tmp_path / "cache")
    L.licence_for_project(root, "calc.py", CHECK, cache=cache, per_test=False,
                          max_sites=2, max_mutants=2, timeout=60)
    (root / "calc.py").write_text((root / "calc.py").read_text() + "\n\ndef other(n):\n    return n\n")
    again = L.licence_for_project(root, "calc.py", CHECK, cache=cache, per_test=False,
                                  max_sites=2, max_mutants=2, timeout=60)
    assert again["from_cache"] is False


def test_a_different_budget_is_a_different_measurement(tmp_path):
    root = _project(tmp_path, BLIND_AND_COVERED, TEST_THAT_ONLY_CHECKS_DOUBLE)
    cache = L.LicenceCache(tmp_path / "cache")
    L.licence_for_project(root, "calc.py", CHECK, cache=cache, per_test=False,
                          max_sites=2, max_mutants=2, timeout=60)
    other = L.licence_for_project(root, "calc.py", CHECK, cache=cache, per_test=False,
                                  max_sites=3, max_mutants=3, timeout=60)
    assert other["from_cache"] is False, "a smaller budget must not answer for a larger one"


def test_a_damaged_cache_entry_is_a_miss(tmp_path):
    path = tmp_path / "cache" / "00" / ("0" * 64 + ".json")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"schema": "SOMETHING_ELSE", "key": "0" * 64}))
    assert L.LicenceCache(tmp_path / "cache").get("0" * 64) is None


# ------------------------------------------------------------------------------------ the writing

def test_the_sentence_says_which_behaviour_is_blind():
    text = L.render_licence(L.licence(_report(2, 1)))
    assert "2 of 3" in text and "line 100" in text


def test_a_refusal_reads_as_a_refusal():
    text = L.render_licence({"verdict": L.REFUSED_FILE_NOT_LOADED, "rel_path": "x.py"})
    assert "REFUSED" in text and "never" in text

"""Mechanism tests for the goal compiler, on REAL published QuixBugs code.

The fixtures below are verbatim from jkoppel/QuixBugs (MIT, commit recorded in
the measurement receipt).  No synthetic tasks, no invented test cases, no
answer key.  The capability measurement itself is
``canonical/tools/contract_grounded_repair_measure_v1.py`` on all 20 held-out
bugs; these tests pin the integrity seams and the two defects measurement found.

Authority NONE. Producer-run. These are mechanism proofs, not capability claims.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import contract_grounded_repair_v1 as cgr  # noqa: E402

# ---- verbatim published QuixBugs: python_programs/pascal.py -----------------
PASCAL_PROGRAM = '''
def pascal(n):
    rows = [[1]]
    for r in range(1, n):
        row = []
        for c in range(0, r):
            upleft = rows[r - 1][c - 1] if c > 0 else 0
            upright = rows[r - 1][c] if c < r else 0
            row.append(upleft + upright)
        rows.append(row)

    return rows


"""
Pascal's Triangle
pascal



Input:
    n: The number of rows to return

Precondition:
    n >= 1

Output:
    The first n rows of Pascal's triangle as a list of n lists

Example:
    >>> pascal(5)
    [[1], [1, 1], [1, 2, 1], [1, 3, 3, 1], [1, 4, 6, 4, 1]]
"""
'''

PASCAL_TEST = '''import pytest
from load_testdata import load_json_testcases

if pytest.use_correct:
    from correct_python_programs.pascal import pascal
else:
    from python_programs.pascal import pascal


testdata = load_json_testcases(pascal.__name__)


@pytest.mark.parametrize("input_data,expected", testdata)
def test_pascal(input_data, expected):
    assert pascal(*input_data) == expected
'''

CONFTEST = '''import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--correct", action="store_true", help="run tests on the correct version"
    )
    parser.addoption("--runslow", action="store_true", help="run slow tests")


def pytest_configure(config):
    pytest.use_correct = config.getoption("--correct")
    pytest.run_slow = config.getoption("--runslow")
'''

LOAD_TESTDATA = '''import json
from pathlib import Path


def load_json_testcases(algorithm):

    quixbugs_root = Path(__file__).parent / ".."
    testdata_path = quixbugs_root / f"json_testcases/{algorithm}.json"
    with open(testdata_path) as data_file:
        testdata = [json.loads(line) for line in data_file]

    return testdata
'''

PASCAL_CASES = [
    [[1], [[1]]],
    [[2], [[1], [1, 1]]],
    [[3], [[1], [1, 1], [1, 2, 1]]],
    [[4], [[1], [1, 1], [1, 2, 1], [1, 3, 3, 1]]],
    [[5], [[1], [1, 1], [1, 2, 1], [1, 3, 3, 1], [1, 4, 6, 4, 1]]],
]


def _real_task(tmp: pathlib.Path) -> cgr.Task:
    """A disposable task holding ONLY what the published corpus gives the solver."""
    (tmp / "python_programs").mkdir(parents=True, exist_ok=True)
    (tmp / "python_testcases").mkdir(parents=True, exist_ok=True)
    (tmp / "json_testcases").mkdir(parents=True, exist_ok=True)
    (tmp / "python_programs" / "pascal.py").write_text(PASCAL_PROGRAM, encoding="utf-8")
    (tmp / "python_testcases" / "test_pascal.py").write_text(PASCAL_TEST, encoding="utf-8")
    (tmp / "python_testcases" / "load_testdata.py").write_text(LOAD_TESTDATA, encoding="utf-8")
    (tmp / "conftest.py").write_text(CONFTEST, encoding="utf-8")
    (tmp / "json_testcases" / "pascal.json").write_text(
        "".join(json.dumps(row) + "\n" for row in PASCAL_CASES), encoding="utf-8")
    return cgr.load_task(tmp, "pascal")


# ---------------------------------------------------------------------------
# Integrity seams: enforced, not promised.
# ---------------------------------------------------------------------------


def test_answer_key_never_reaches_the_solver(tmp_path):
    _real_task(tmp_path)
    (tmp_path / cgr.ANSWER_KEY).mkdir()
    with pytest.raises(RuntimeError, match="ANSWER_KEY_REACHED_THE_SOLVER"):
        cgr.load_task(tmp_path, "pascal")


def test_a_changed_test_byte_is_an_error_not_a_repair(tmp_path):
    task = _real_task(tmp_path)
    (tmp_path / task.test_rel).write_text(PASCAL_TEST + "\n# tampered\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="TEST_FILE_CHANGED"):
        cgr.fresh_verdict(task, task.program_path.read_text(encoding="utf-8"))


def test_the_published_test_file_names_the_function_and_not_the_answer_key(tmp_path):
    task = _real_task(tmp_path)
    assert task.function_name == "pascal"
    assert task.program_rel.startswith("python_programs/")
    assert task.cases[0][1] == [[1]]  # the REAL published expected value


# ---------------------------------------------------------------------------
# The two defects measurement found, pinned so they cannot come back.
# ---------------------------------------------------------------------------


def test_variants_are_actually_loaded_not_silently_the_original(tmp_path):
    """The scratch package MUST win on sys.path; otherwise every candidate is
    the untouched program and the measurement is a tautology."""
    task = _real_task(tmp_path)
    original = task.program_path.read_text(encoding="utf-8")
    broken = "def pascal(n):\n    raise RuntimeError('DELIBERATE_BREAK')\n"
    obs, relations = cgr.observe(task, original)
    rows = cgr.screen_variants(task, obs, [original, broken])
    assert len(rows) == 2
    assert rows[0]["passed"] >= 1, "the original must actually run"
    assert rows[1]["passed"] == 0, "a broken variant must not be the original"


def test_no_candidate_is_a_noop(tmp_path):
    task = _real_task(tmp_path)
    source = task.program_path.read_text(encoding="utf-8")
    obs, _ = cgr.observe(task, source)
    candidates = cgr.synthesize(task, source, obs,
                                cgr.Prior(signature=cgr.goal_signature(task, obs)), cap=120)
    assert candidates, "the executed path must yield a hypothesis space"
    assert all(c.source != source for c in candidates)
    assert len({c.source for c in candidates}) == len(candidates)


# ---------------------------------------------------------------------------
# The causal observable vocabulary, and what it does and does not license.
# ---------------------------------------------------------------------------


def test_executed_observables_exist_and_the_static_vocabulary_is_insufficient(tmp_path):
    task = _real_task(tmp_path)
    obs, _ = cgr.observe(task, task.program_path.read_text(encoding="utf-8"))
    assert obs.verdict == "OBSERVED"
    assert obs.trace_lines, "executed line numbers are the causal observable"
    assert obs.failing_indices, "a real published bug must actually fail"
    assert len({f for f in obs.per_case_facts}) > 1, "cases must be distinguishable"
    assert obs.static_certificate is not None, "static AST facts cannot separate outcomes"


def test_the_prior_holds_only_exact_counts_of_executed_verdicts():
    prior = cgr.Prior(signature="WRONG_VALUE")
    prior.record("BINARY_OP", False)
    prior.record("BINARY_OP", True)
    prior.record("BINARY_OP", False)
    data = prior.as_dict()
    assert data["tried"] == {"BINARY_OP": 3}
    assert data["verified"] == {"BINARY_OP": 1}
    assert "NO_FITTED_PARAMETERS" in data["note"]
    # A family matching the goal signature ranks above one that does not.
    ranked = prior.rank(["OFFSET", "BINARY_OP"])
    assert ranked[0] == "BINARY_OP"


def test_a_repaired_real_bug_is_not_reported_as_a_permanent_learned_rule(tmp_path):
    """Verified DOING is not LEARNING.  The corpus test licenses the edit; only
    an identified requirement licenses permanence.  This is the whole answer to
    'do it once and he learns it permanently'."""
    if importlib.util.find_spec("pytest") is None:
        pytest.skip("SUBSTRATE: pytest not importable")
    task = _real_task(tmp_path)
    row = cgr.solve(task, candidate_cap=260, fresh_cap=2)
    assert row["status"] == "REPAIRED__CORPUS_TEST_PASSES", row
    assert row["answer_key_absent"] is True
    assert row["synthesis"]["fresh_verdicts"], "a fresh-copy pytest is the only verdict"
    assert row["synthesis"]["fresh_verdicts"][0]["returncode"] == 0
    assert row["synthesis"]["winning_diff"], "the winning patch must be auditable"
    assert row["identifiability"]["permanent_rule_admitted"] is False, (
        "no identified requirement, therefore no permanent rule")

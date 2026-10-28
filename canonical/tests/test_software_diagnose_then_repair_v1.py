# PROJECT_BRAIN
"""software.diagnose_then_repair.v1: failing test in, verified patch (or a named
refusal) out; the user's tree is never written.  Real subprocesses, real pytest,
real confinement when the host has it."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from canonical.runtime import confine_v1
from canonical.runtime.bound_capabilities import software_diagnose_then_repair_v1 as dr

ROOT = Path(__file__).resolve().parents[2]


def _fixture(root: Path, bug: str = "return w * h - 1") -> None:
    (root / "proj" / "pkg").mkdir(parents=True)
    (root / "proj" / "tests").mkdir()
    (root / "proj" / "pkg" / "__init__.py").write_text("")
    (root / "proj" / "pkg" / "calc.py").write_text(
        "def area(w, h):\n    " + bug + "\n\n\ndef twice(x):\n    return 2 * x\n")
    (root / "proj" / "tests" / "__init__.py").write_text("")
    (root / "proj" / "tests" / "test_calc.py").write_text(
        "from pkg.calc import area, twice\n\ndef test_area():\n    assert area(3, 4) == 12\n\n"
        "def test_twice():\n    assert twice(5) == 10\n")
    (root / "proj" / "tests" / "test_other.py").write_text(
        "from pkg.calc import twice\n\ndef test_other():\n    assert twice(1) == 2\n")


def _snapshot(root: Path) -> list:
    return sorted((p.relative_to(root).as_posix(), p.read_bytes())
                  for p in (root / "proj").rglob("*") if p.is_file())


def _args(**extra) -> dict:
    return {"source_root": "proj", "test_paths": ["proj/tests/test_calc.py"],
            "output_path": "out/dr.json", "python_executable": sys.executable, "deadline_s": 120, **extra}


def test_failing_test_in_verified_patch_out_and_the_tree_untouched(tmp_path: Path):
    _fixture(tmp_path)
    before = _snapshot(tmp_path)
    result = dr.run(_args(), tmp_path)
    assert result["status"] == "VERIFIED_PATCH" and result["verified"] is True, result
    assert result["steps"] == ["reproduce", "localize", "patch_search", "full_suite_gate"]
    assert result["gate"] == "PASS" and result["tests_discovered"] == 2 and result["tests_failed"] == 0
    assert result["target_path"] == "pkg/calc.py"
    diff = (tmp_path / result["diff_path"]).read_text()
    assert "--- a/pkg/calc.py" in diff and "+    return w * h\n" in diff   # the term dropped, not a 1 made 0
    assert _snapshot(tmp_path) == before                      # never written
    assert not (tmp_path / "out" / "dr.scratch").exists()    # scratch removed
    artifact = json.loads((tmp_path / "out" / "dr.json").read_text())
    assert artifact["anchor_unchanged"] is True
    assert artifact["confined"] == confine_v1.available()    # says which, never assumes
    assert result["seconds"] < 60


def test_a_passing_suite_is_nothing_to_repair(tmp_path: Path):
    _fixture(tmp_path, bug="return w * h")
    result = dr.run(_args(), tmp_path)
    assert result["verified"] is False
    assert result["status"] == "NOTHING_TO_REPAIR:FAILING_TESTS_PASS"
    assert result["steps"] == []


def test_no_candidate_in_bound_is_an_open_result_not_a_patch(tmp_path: Path):
    _fixture(tmp_path, bug="return w")   # a missing term: no template adds code
    result = dr.run(_args(), tmp_path)
    assert result["verified"] is False and result["diff_path"] is None
    assert result["status"].startswith("OPEN:NO_VERIFIED_CANDIDATE:")
    assert result["steps"] == ["reproduce", "localize", "patch_search"]


def test_a_patch_that_fixes_the_stated_test_but_breaks_another_is_not_verified(tmp_path: Path):
    _fixture(tmp_path)
    # test_other pins the buggy behaviour of twice(); the search repairs area() and the
    # full suite still fails -> the loop must report it, not ship it
    (tmp_path / "proj" / "tests" / "test_other.py").write_text(
        "from pkg.calc import area\n\ndef test_other():\n    assert area(2, 2) == 3\n")
    result = dr.run(_args(), tmp_path)
    assert result["verified"] is False
    assert result["status"].startswith("PATCH_FAILS_FULL_SUITE:FAIL"), result["status"]
    assert result["tests_failed"] == 1


def test_deadline_is_end_to_end(tmp_path: Path):
    _fixture(tmp_path)
    result = dr.run(_args(deadline_s=5), tmp_path)
    # 5 s is the floor; the fixture finishes inside it, so this pins the floor, not a refusal
    assert json.loads((tmp_path / "out" / "dr.json").read_text())["deadline_s"] == 5


def test_inputs_fail_closed(tmp_path: Path):
    _fixture(tmp_path)
    with pytest.raises(dr.DiagnoseRepairRefusal, match="TEST_PATHS_REQUIRED"):
        dr.run(_args(test_paths=[]), tmp_path)
    with pytest.raises(dr.DiagnoseRepairRefusal, match="PATH_ESCAPE"):
        dr.run(_args(test_paths=["../x.py"]), tmp_path)
    with pytest.raises(dr.DiagnoseRepairRefusal, match="OUTPUT_INSIDE_SOURCE_ROOT"):
        dr.run(_args(output_path="proj/out.json"), tmp_path)
    (tmp_path / "out" / "dr.scratch").mkdir(parents=True)
    (tmp_path / "out" / "dr.scratch" / "precious.txt").write_text("not ours")
    with pytest.raises(dr.DiagnoseRepairRefusal, match="SCRATCH_DIR_NOT_OWNED_BY_BRAIN"):
        dr.run(_args(), tmp_path)
    assert (tmp_path / "out" / "dr.scratch" / "precious.txt").read_text() == "not ours"


@pytest.mark.skipif(not confine_v1.available(), reason="host cannot confine")
def test_reproduction_runs_confined_when_the_host_can(tmp_path: Path):
    _fixture(tmp_path)
    result = dr.run(_args(confine="required"), tmp_path)
    assert result["confined"] is True and result["verified"] is True


def test_a_harness_crash_is_not_mistaken_for_a_failing_test(tmp_path: Path):
    _fixture(tmp_path)
    (tmp_path / "proj" / "conftest.py").write_text("raise RuntimeError('broken harness')\n")
    result = dr.run(_args(), tmp_path)
    # rc 4 from pytest, no summary line: no test ran, so there is nothing to repair yet
    assert result["verified"] is False
    assert result["status"].startswith("REPRODUCE_HARNESS_ERROR:rc="), result["status"]
    assert result["steps"] == []


@pytest.mark.skipif(not confine_v1.available(), reason="host cannot confine")
def test_confinement_exposes_only_null_and_urandom_from_dev(tmp_path: Path):
    receipt = confine_v1.run(
        "import os\nopen('/dev/null', 'w').write('x')\nprint(len(os.urandom(2)), sorted(os.listdir('/dev')))\n",
        str(tmp_path), timeout=20, network=False)
    assert receipt["verdict"] == "OK" and "2 ['null', 'urandom']" in receipt["output"]


@pytest.mark.parametrize("bug,fix", [
    ("return w + h", "return w * h"),                 # wrong operator (outside the old Add->Sub table)
    ("return w * h - 1", "return w * h"),             # spurious term
    ("return w * h if w <= 0 else 0", None),          # boundary: some comparison flip must pass
])
def test_bug_classes_the_generator_reaches(tmp_path: Path, bug: str, fix: str | None):
    _fixture(tmp_path, bug=bug)
    result = dr.run(_args(), tmp_path)
    assert result["status"] == "VERIFIED_PATCH", result["status"]
    if fix:
        assert "+    " + fix + "\n" in (tmp_path / result["diff_path"]).read_text()


def test_candidates_are_spectrum_first_distinct_and_parse(tmp_path: Path):
    from canonical.runtime import patch_candidate_search_v1 as pcs
    import ast
    src = "def f(a, b):\n    x = a - b\n    if x < 0:\n        return 1\n    return x + 1\n"
    rows = pcs.generate(src, [3], ["s"], priority_lines=[5, 3])
    assert rows and rows[0][0]["lineno"] == 5 and all(r[0]["lineno"] == 5 for r in rows[:6])
    first_other = next(r for r in rows if r[0]["lineno"] != 5)
    assert first_other[0]["lineno"] == 3
    texts = [c for _, c in rows]
    assert len(set(texts)) == len(texts) and src not in texts
    for c in texts:
        ast.parse(c)
    kinds = {r[0]["kind"] for r in rows}
    assert {"BINOP_SWAP", "BINOP_DROP", "COMPARE_SWAP", "OPERAND_SWAP", "NOT_TOGGLE", "CONSTANT_REPLACE"} <= kinds


def test_workers_run_candidates_in_parallel_on_their_own_copies(tmp_path: Path):
    _fixture(tmp_path, bug="return w * h if w <= 0 else 0")
    before = _snapshot(tmp_path)
    r2 = dr.run(_args(workers=2), tmp_path)
    assert r2["status"] == "VERIFIED_PATCH"
    art = json.loads((tmp_path / "out" / "dr.json").read_text())
    search = next(s for s in art["steps"] if s["step"] == "patch_search")
    assert search["workers"] == 2 and search["stop_reason"] == "VERIFIED"
    assert search["tested_candidate_count"] >= search["winning_index"]
    assert _snapshot(tmp_path) == before
    assert not (tmp_path / "out" / "dr.scratch").exists()


def test_the_deadline_stops_the_search_and_says_so(tmp_path: Path):
    _fixture(tmp_path, bug="return w")
    result = dr.run(_args(deadline_s=5, workers=1), tmp_path)
    assert result["verified"] is False
    assert result["status"].startswith(("DEADLINE_EXCEEDED:5s", "OPEN:NO_VERIFIED_CANDIDATE:")), result["status"]


# --- differential witness: several green patches are ranked, not shipped first-come ---

def test_several_green_patches_are_ranked_by_behavioural_delta_and_the_ledger_shows_all(tmp_path: Path):
    _fixture(tmp_path, bug="return w * h if w <= 0 else 0")
    result = dr.run(_args(), tmp_path)
    assert result["status"] == "VERIFIED_PATCH"
    art = json.loads((tmp_path / "out" / "dr.json").read_text())
    search = next(s for s in art["steps"] if s["step"] == "patch_search")
    assert len(search["green_indices"]) >= 2
    w = search["witness"]
    assert w["status"] == "MEASURED" and w["function"] == "area" and w["proves_correctness"] is False
    measured = [r for r in w["ranking"] if r["witness"] == "MEASURED"]
    assert measured and all(r["delta_on_tests"] >= 1 for r in measured)
    assert search["winning_index"] == measured[0]["index"]
    assert measured[0]["delta_outside_tests"] == min(r["delta_outside_tests"] for r in measured)


def test_green_budget_one_restores_first_green_wins(tmp_path: Path):
    _fixture(tmp_path, bug="return w * h if w <= 0 else 0")
    result = dr.run(_args(green_budget=1), tmp_path)
    art = json.loads((tmp_path / "out" / "dr.json").read_text())
    search = next(s for s in art["steps"] if s["step"] == "patch_search")
    assert result["status"] == "VERIFIED_PATCH" and len(search["green_indices"]) == 1
    assert search["witness"]["status"] == "SINGLE_GREEN"


def test_witness_rank_prefers_least_collateral_change_and_demotes_no_change_on_tests():
    from canonical.runtime import patch_differential_witness_v1 as w
    original = [["R", "0"], ["R", "a"], ["R", "b"], ["R", "c"]]
    cands = [(1, [["R", "x"], ["R", "q"], ["R", "q"], ["R", "c"]]),   # changes test input, 2 outside
             (2, [["R", "x"], ["R", "a"], ["R", "q"], ["R", "c"]]),   # changes test input, 1 outside
             (3, [["R", "0"], ["R", "q"], ["R", "q"], ["R", "q"]]),   # did not change the test input
             (4, None)]                                             # probe failed
    order = [r["index"] for r in w.rank(original, cands, n_test_inputs=1)]
    assert order == [2, 1, 3, 4]


def test_witness_only_covers_free_functions_and_says_why_otherwise():
    from canonical.runtime import patch_differential_witness_v1 as w
    src = ("def f(a, b):\n    return a\n\n\nclass C:\n    def m(self):\n        return 1\n\n\n"
           "def g(x):\n    def inner(y):\n        return y\n    return inner(x)\n\n\ndef v(*a):\n    return a\n")
    assert w.owning_function(src, 2) == ("f", 2, None)
    assert w.owning_function(src, 7)[2] == "METHOD"
    assert w.owning_function(src, 12)[2] == "NESTED_FUNCTION"
    assert w.owning_function(src, 16)[2] == "VARIADIC_SIGNATURE"
    assert w.owning_function(src, 4)[2] == "NO_OWNING_FUNCTION"


def test_witness_inputs_come_from_the_tests_and_a_deterministic_grid(tmp_path: Path):
    from canonical.runtime import patch_differential_witness_v1 as w
    t = tmp_path / "test_x.py"
    t.write_text("from m import area\n\ndef test_a():\n    assert area(3, 4) == 12\n    assert area(1.5, 2) == 3.0\n")
    calls = w.test_call_inputs([t], "area", 2)
    assert calls == [[3, 4], [1.5, 2]]
    g1 = w.grid_inputs(calls, 2)
    g2 = w.grid_inputs(calls, 2)
    assert g1 == g2 and len(g1) <= w.MAX_INPUTS   # the tests' own calls are prepended by witness()
    assert any(isinstance(row[0], float) for row in g1)


def test_plugin_trim_only_when_no_test_or_conftest_mentions_the_plugin(tmp_path: Path):
    _fixture(tmp_path)
    tree = tmp_path / "proj"
    assert dr.plugin_trim(tree, ["tests/test_calc.py"]) == ["-p", "no:hypothesispytest"]
    (tree / "conftest.py").write_text("import hypothesis\n")
    assert dr.plugin_trim(tree, ["tests/test_calc.py"]) == []

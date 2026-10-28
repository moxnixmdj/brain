# PROJECT_BRAIN
"""software.diagnose_repair.v1: failing test in, verified patch (or a named
refusal) out; the user's tree is never written.  Real subprocesses, real pytest,
real confinement when the host has it."""
from __future__ import annotations

import json
import sys
import time
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
    _fixture(tmp_path, bug="return 0")   # needs both names back: only 'return 12' is green
    result = dr.run(_args(), tmp_path)
    assert result["verified"] is False and result["diff_path"] is None
    assert result["status"].startswith("OPEN:ONLY_OVERFIT_SIGNATURE_GREENS:"), result["status"]
    assert result["steps"] == ["reproduce", "localize", "patch_search"]


def test_truly_unreachable_bug_is_open_with_the_count(tmp_path: Path):
    _fixture(tmp_path, bug="return len(str(w))")
    # two examples no expression over (w, h) of size <= 3 satisfies: 12 for (3, 4) and 11 for (2, 5)
    (tmp_path / "proj" / "tests" / "test_calc.py").write_text(
        "from pkg.calc import area\n\ndef test_area():\n    assert area(3, 4) == 12\n    assert area(2, 5) == 11\n")
    result = dr.run(_args(), tmp_path)
    assert result["verified"] is False and result["diff_path"] is None
    assert result["status"].startswith(("OPEN:NO_VERIFIED_CANDIDATE:", "OPEN:ONLY_OVERFIT")), result["status"]


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
    _fixture(tmp_path, bug="return len(str(w))")
    (tmp_path / "proj" / "tests" / "test_calc.py").write_text(
        "from pkg.calc import area\n\ndef test_area():\n    assert area(3, 4) == 12\n    assert area(2, 5) == 10\n")
    result = dr.run(_args(deadline_s=5, workers=1, judge="pytest"), tmp_path)   # 0.2 s a candidate: 5 s cannot finish
    assert result["verified"] is False
    assert result["status"].startswith("DEADLINE_EXCEEDED:5s"), result["status"]
    art = json.loads((tmp_path / "out" / "dr.json").read_text())
    assert art["steps"][2]["stop_reason"] == "DEADLINE" and art["steps"][2]["tested_candidate_count"] >= 1


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


# --- code that adds code: missing term, missing guard, two edits in one statement ---

def test_a_missing_term_is_added_from_the_names_in_scope(tmp_path: Path):
    _fixture(tmp_path, bug="return w")
    result = dr.run(_args(), tmp_path)
    assert result["status"] == "VERIFIED_PATCH"
    assert "+    return w * h\n" in (tmp_path / result["diff_path"]).read_text()
    art = json.loads((tmp_path / "out" / "dr.json").read_text())
    assert art["steps"][2]["winning_mutation"]["kind"] == "EXPR_EXTEND"


def test_a_missing_none_guard_is_inserted_in_front_of_the_first_statement(tmp_path: Path):
    _fixture(tmp_path, bug="return w * h")
    (tmp_path / "proj" / "tests" / "test_calc.py").write_text(
        "from pkg.calc import area, twice\n\ndef test_area():\n    assert area(3, 4) == 12\n"
        "    assert area(None, 4) == 0\n\ndef test_twice():\n    assert twice(5) == 10\n")
    result = dr.run(_args(), tmp_path)
    assert result["status"] == "VERIFIED_PATCH"
    diff = (tmp_path / result["diff_path"]).read_text()
    assert "+    if w is None:\n+        return 0\n" in diff and "-" not in [l[:1] for l in diff.splitlines()[2:]]
    art = json.loads((tmp_path / "out" / "dr.json").read_text())
    assert art["steps"][2]["winning_mutation"]["kind"] == "GUARD_INSERT"
    assert art["steps"][2]["witness"]["status"] == "MEASURED"     # None inputs probe fine


def test_an_overfitting_single_edit_triggers_composition_and_the_witness_prefers_the_two_edit_fix(tmp_path: Path):
    _fixture(tmp_path, bug="return w + h + 1")        # 3 + 4 + 5 == 12 is green too
    result = dr.run(_args(deadline_s=300), tmp_path)
    assert result["status"] == "VERIFIED_PATCH"
    assert "+    return w * h\n" in (tmp_path / result["diff_path"]).read_text()
    search = json.loads((tmp_path / "out" / "dr.json").read_text())["steps"][2]
    assert search["overfit_signature_indices"]                      # the '+ 5' green was flagged
    assert search["compose"]["reason"].startswith("ONLY_SUSPICIOUS_GREENS")
    assert search["winning_mutation"]["kind"] == "COMPOSE"
    assert search["witness"]["status"] == "MEASURED"


def test_compose_pairs_edits_one_statement_inner_first_and_leaves_the_rest_of_the_file_alone():
    from canonical.runtime import patch_candidate_search_v1 as pcs
    src = "import os\n\n\ndef area(w, h):\n    return w + h + 1\n\n\ndef twice(x):\n    return 2 * x\n"
    singles = pcs.generate(src, [12], [], [5])
    pairs = pcs.compose_pairs(src, singles, list(range(1, len(singles) + 1)), limit=1000)
    texts = [c for d, c in pairs if d["lineno"] == 5]
    assert src.replace("return w + h + 1", "return w * h") in texts
    assert all(c.startswith("import os\n\n\ndef area(w, h):\n") and c.endswith("def twice(x):\n    return 2 * x\n") for c in texts)
    assert all(d["kind"] == "COMPOSE" and len(d["parts"]) == 2 for d, _ in pairs)
    assert len(set(texts)) == len(texts) and not (set(texts) & {c for _, c in singles})


def test_overfit_signature_is_a_test_literal_written_into_the_code():
    sig = dr._overfit_signature
    assert sig({"kind": "CONSTANT_REPLACE", "detail": "1->5"}, [12, 5], []) is True
    assert sig({"kind": "CONSTANT_REPLACE", "detail": "1->0"}, [12, 5], []) is False      # 0/1/-1 are not evidence
    assert sig({"kind": "GUARD_INSERT", "detail": "if w is None: return 12"}, [12], []) is True
    assert sig({"kind": "BINOP_SWAP", "detail": "Add->Mult"}, [12], []) is False


# --- in-process judge: one confined interpreter per worker, candidates streamed through ---

def test_plain_tests_are_judged_in_process_and_the_ledger_says_so(tmp_path: Path):
    _fixture(tmp_path, bug="return w + h + 1")
    t0 = time.monotonic()
    result = dr.run(_args(deadline_s=300), tmp_path)
    seconds = time.monotonic() - t0
    assert result["status"] == "VERIFIED_PATCH"
    search = json.loads((tmp_path / "out" / "dr.json").read_text())["steps"][2]
    assert search["judge"] == {"in_process": True, "reason": "PLAIN"}
    assert all(a.get("judge") == "in_process" for a in search["attempts"])
    assert search["winning_mutation"]["kind"] == "COMPOSE"
    assert "+    return w * h\n" in (tmp_path / result["diff_path"]).read_text()
    assert seconds < 20, seconds          # was 22 s under per-candidate pytest; measured 3.6 s


def test_judge_pytest_is_the_same_answer_slower(tmp_path: Path):
    _fixture(tmp_path, bug="return w")
    result = dr.run(_args(judge="pytest"), tmp_path)
    search = json.loads((tmp_path / "out" / "dr.json").read_text())["steps"][2]
    assert result["status"] == "VERIFIED_PATCH" and search["judge"]["in_process"] is False
    assert search["winning_mutation"]["kind"] == "EXPR_EXTEND"


def test_non_plain_tests_fall_back_to_pytest_and_still_verify(tmp_path: Path):
    _fixture(tmp_path, bug="return w + h")
    (tmp_path / "proj" / "tests" / "test_calc.py").write_text(
        "import pytest\nfrom pkg.calc import area\n\n"
        "@pytest.mark.parametrize('w,h,e', [(3, 4, 12), (2, 5, 10)])\ndef test_area(w, h, e):\n    assert area(w, h) == e\n")
    result = dr.run(_args(), tmp_path)
    search = json.loads((tmp_path / "out" / "dr.json").read_text())["steps"][2]
    assert search["judge"]["in_process"] is False
    assert search["judge"]["reason"].startswith(("TEST_TAKES_PARAMETERS", "DECORATED_TEST"))
    assert result["status"] == "VERIFIED_PATCH"
    assert "+    return w * h\n" in (tmp_path / result["diff_path"]).read_text()


def test_plain_tests_applicability_is_static_and_names_the_reason(tmp_path: Path):
    from canonical.runtime import patch_inprocess_judge_v1 as j
    _fixture(tmp_path)
    tree = tmp_path / "proj"
    ok, why, mods = j.plain_tests(tree, ["tests/test_calc.py"])
    assert ok and why == "PLAIN"
    assert {k: v for k, v in mods[0].items() if k != "asserts"} == {"path": "tests/test_calc.py", "import": "tests.test_calc", "sys_path": ".", "tests": 2}
    assert mods[0]["asserts"] == [{"test": "test_area", "expr": "area(3, 4)", "expected": 12},
                                  {"test": "test_twice", "expr": "twice(5)", "expected": 10}]
    (tree / "conftest.py").write_text("import pytest\n\n@pytest.fixture(autouse=True)\ndef x():\n    yield\n")
    assert j.plain_tests(tree, ["tests/test_calc.py"])[:2] == (False, "CONFTEST_HOOKS_OR_AUTOUSE:conftest.py")
    (tree / "conftest.py").unlink()
    (tree / "tests" / "__init__.py").unlink()        # rootdir-less layout: import by basename from its dir
    ok, why, mods = j.plain_tests(tree, ["tests/test_calc.py"])
    assert ok and mods[0]["import"] == "test_calc" and mods[0]["sys_path"] == "tests"
    (tree / "tests" / "test_calc.py").write_text("class TestX:\n    def test_a(self):\n        pass\n")
    assert j.plain_tests(tree, ["tests/test_calc.py"])[1].startswith("TEST_CLASS:")


def test_a_runaway_candidate_is_bounded_and_the_batch_goes_on(tmp_path: Path):
    from canonical.runtime import patch_inprocess_judge_v1 as j
    _fixture(tmp_path, bug="return w * h - 1")
    tree = tmp_path / "proj"
    ok, _, mods = j.plain_tests(tree, ["tests/test_calc.py"])
    assert ok
    texts = ["def area(w, h):\n    while True:\n        pass\n\n\ndef twice(x):\n    return 2 * x\n",
             "def area(w, h):\n    return w * h\n\n\ndef twice(x):\n    return 2 * x\n",
             "def area(w, h):\n    return w\n\n\ndef twice(x):\n    return 2 * x\n",
             "def area(w, h):\n    raise SystemExit(3)\n\n\ndef twice(x):\n    return 2 * x\n"]
    # a short per-candidate alarm for the test; the default is 5 s
    import canonical.runtime.patch_inprocess_judge_v1 as jj
    prog = jj.judge_program
    jj.judge_program = lambda *a, **k: prog(*a, **{**k, "per_candidate_s": 1})
    try:
        res = dr._judge_batch(tree, "pkg/calc.py", mods, texts, sys.executable, "auto", time.monotonic() + 60)
    finally:
        jj.judge_program = prog
    assert {k: v[0] for k, v in res.items()} == {0: 999, 1: 0, 2: 1, 3: 1}, res
    assert res[1][1] == 0.0 and 0.0 < res[2][1] < 1.0 and res[3][1] == 1.0     # distance: green 0, near, exception 1
    assert (tree / "pkg" / "calc.py").read_text().endswith("return w * h - 1\n\n\ndef twice(x):\n    return 2 * x\n")


# --- assertion-distance fitness and expression synthesis ---

def _two_examples(root: Path) -> None:
    (root / "proj" / "tests" / "test_calc.py").write_text(
        "from pkg.calc import area, twice\n\ndef test_area():\n    assert area(3, 4) == 12\n    assert area(2, 5) == 10\n\n"
        "def test_twice():\n    assert twice(5) == 10\n")


def test_the_in_process_judge_reports_an_assertion_distance_that_orders_composition(tmp_path: Path):
    _fixture(tmp_path, bug="return w + h + 1")
    result = dr.run(_args(deadline_s=300), tmp_path)
    assert result["status"] == "VERIFIED_PATCH"
    search = json.loads((tmp_path / "out" / "dr.json").read_text())["steps"][2]
    singles = [a for a in search["attempts"] if "stage" not in a]
    assert singles and all(0.0 <= a["distance"] <= 1.0 for a in singles if a["returncode"] == 1)
    window = search["compose"]["fitness_of_window"]
    keys = [(rc, d) for _, rc, d in window]
    assert keys == sorted(keys)                                  # fewest failing, then closest
    # 'w * h + 1' (13 vs 12) is nearer than 'w + h' (7 vs 12) and sits before it
    by_index = {a["index"]: a for a in singles}
    near = next(i for i, rc, d in window if by_index[i]["mutation"]["detail"] == "Add->Mult" and by_index[i]["mutation"]["lineno"] == 2 and d < 0.6)
    farther = [i for i, rc, d in window if rc == 1 and d > 0.6]
    order = [i for i, _, _ in window]
    assert farther and all(order.index(near) < order.index(i) for i in farther)
    assert all(by_index[i]["mutation"]["detail"] != "keep left" for i, _, _ in window[: order.index(near) + 1])


@pytest.mark.parametrize("bug", ["return len(str(w))", "return 0", "return w + h + 1"])
def test_two_examples_let_synthesis_fill_the_returned_expression(tmp_path: Path, bug: str):
    _fixture(tmp_path, bug=bug)
    _two_examples(tmp_path)
    result = dr.run(_args(deadline_s=300), tmp_path)
    assert result["status"] == "VERIFIED_PATCH", result["status"]
    assert "+    return w * h\n" in (tmp_path / result["diff_path"]).read_text()
    search = json.loads((tmp_path / "out" / "dr.json").read_text())["steps"][2]
    assert search["synthesis"]["status"] == "FOUND:1" and search["synthesis"]["expressions"] == ["w * h"]
    assert search["synthesis"]["examples"] == 2


def test_one_example_is_not_a_specification_for_synthesis(tmp_path: Path):
    _fixture(tmp_path, bug="return 0")
    result = dr.run(_args(), tmp_path)
    search = json.loads((tmp_path / "out" / "dr.json").read_text())["steps"][2]
    assert search["synthesis"]["status"] == "UNDERSPECIFIED:1_examples"
    assert result["status"].startswith("OPEN:ONLY_OVERFIT_SIGNATURE_GREENS")


def test_synthesis_is_bounded_bottom_up_with_observational_equivalence():
    from canonical.runtime import expression_synthesis_v1 as es
    r = es.synthesize(["w", "h"], [([3, 4], 12), ([2, 5], 10)])
    assert r["expressions"] == ["w * h"] and r["seconds"] < 2.0
    assert es.synthesize(["s"], [(["abc"], 3), (["hello"], 5)])["expressions"] == ["len(s)"]
    assert es.synthesize(["a", "b"], [([7, 2], 1), ([9, 4], 1), ([8, 4], 0)])["expressions"] == ["a % b"]
    assert es.synthesize(["n"], [([3], 7)])["status"] == "UNDERSPECIFIED:1_examples"
    r = es.synthesize(["n"], [([3], 1000003), ([4], 1000004)], max_size=1)
    assert r["expressions"] == [] and r["status"].startswith("NONE:")
    specs = [{"test": "t", "expr": "area(3, 4)", "expected": 12}, {"test": "t", "expr": "other(1)", "expected": 1},
             {"test": "t", "expr": "area(x, 4)", "expected": 12}]
    assert es.examples_for("area", ["w", "h"], specs) == [([3, 4], 12)]

"""Permanent verification suite for Universal Semantic Meaning IR, Cross-File Causal Slicing,
and Closed-Loop CEGIS Refinement (Leaps 1, 2, & 3 — Zero LLM Calls, Zero Stored Weights).
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

from canonical.runtime import causal_angelic_swe_engine_v1 as PY_SWE
from canonical.runtime import multilang_causal_swe_engine_v1 as ML_SWE
from canonical.runtime import universal_semantic_ir_v1 as SEM


def test_01_egraph_cross_language_and_algebraic_equivalence() -> None:
    """Identical semantic meanings across Python, JS, and C canonicalize to bit-identical IR."""
    py_ir = SEM.lift_to_ir("if len(s) > 0 and s[-1] == '\\n':\n    pass\n", "python")[0].ir
    js_ir = SEM.lift_to_ir("if (s.length > 0 && s[s.length - 1] === '\\n') {\n}\n", "js")[0].ir
    c_ir = SEM.lift_to_ir("if (strlen(s) > 0 && s[strlen(s) - 1] == '\\n') {\n}\n", "c")[0].ir
    assert py_ir == js_ir == c_ir

    # De Morgan's Law + negation push-down + operand commutativity + `>`/`>=` normalization
    e_py = SEM.lift_to_ir("if not (a == 0 or b < 1):\n    pass\n", "python")[0].ir
    e_c = SEM.lift_to_ir("if (0 != a && b >= 1) {}\n", "c")[0].ir
    e_js = SEM.lift_to_ir("if (!(a === 0 || b < 1)) {}\n", "js")[0].ir
    assert e_py == e_c == e_js

    # Loop structural equivalence across all 3 languages
    l_py = SEM.lift_to_ir("for i in range(0, n):\n    pass\n", "python")[0].ir
    l_c = SEM.lift_to_ir("for (int i = 0; i < n; i++) {\n}\n", "c")[0].ir
    l_js = SEM.lift_to_ir("for (let i = 0; i < n; i++) {\n}\n", "js")[0].ir
    assert l_py == l_c == l_js


def test_02_cross_language_1shot_transfer_and_instant_forgetting() -> None:
    """Learn ONCE in C -> transfer to Python & JS; learn ONCE in Python -> transfer to JS & C; delete -> instant forget."""
    store = SEM.new_semantic_skill_store()
    assert store["parameters_stored"] == 0

    # 1. C -> Python & JS (empty-buffer underflow guard, e.g. inih@8e06f6b)
    c_before = "char* rstrip(char* s) {\n    while (s[strlen(s) - 1] == ' ') {\n        s[strlen(s) - 1] = 0;\n    }\n    return s;\n}\n"
    c_after = "char* rstrip(char* s) {\n    while (strlen(s) > 0 && s[strlen(s) - 1] == ' ') {\n        s[strlen(s) - 1] = 0;\n    }\n    return s;\n}\n"
    adm_c = SEM.admit_semantic_skill(store, c_before, c_after, source_lang="c")
    assert adm_c["admitted"] is True
    assert adm_c["skill"]["parameters_stored"] == 0

    py_buggy = "def trim_spaces(text):\n    while text[-1] == ' ':\n        text = text[:-1]\n    return text\n"
    py_cands = SEM.recall_semantic_candidates(store, py_buggy, target_lang="python")
    assert len(py_cands) == 1
    ns: dict[str, object] = {}
    exec(py_cands[0]["patched_source"], ns)
    assert ns["trim_spaces"]("") == ""  # type: ignore[operator]
    assert ns["trim_spaces"]("abc   ") == "abc"  # type: ignore[operator]

    js_buggy = "function trimEnd(buf) {\n    while (buf[buf.length - 1] === ' ') {\n        buf = buf.slice(0, -1);\n    }\n    return buf;\n}\n"
    js_cands = SEM.recall_semantic_candidates(store, js_buggy, target_lang="js")
    assert len(js_cands) == 1
    assert "buf.length > 0" in js_cands[0]["patched_source"]

    # JSON persistence round-trip + instant deletion forgetting
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "sem_store.json"
        SEM.save_semantic_skill_store(store, p)
        reloaded = SEM.load_semantic_skill_store(p)
        assert len(SEM.recall_semantic_candidates(reloaded, py_buggy, target_lang="python")) == 1
        assert SEM.delete_semantic_skill(reloaded, adm_c["skill_id"]) is True
        assert SEM.recall_semantic_candidates(reloaded, py_buggy, target_lang="python") == []

    # 2. Python -> JS & C (guard-prefix insertion before division return)
    store2 = SEM.new_semantic_skill_store()
    adm_py = SEM.admit_semantic_skill(
        store2,
        "def scale(x, d):\n    return x / d\n",
        "def scale(x, d):\n    if d == 0:\n        return 0\n    return x / d\n",
        source_lang="python",
    )
    assert adm_py["admitted"] is True
    js_rec = SEM.recall_semantic_candidates(store2, "function ratio(a, b) {\n    return a / b;\n}\n", target_lang="js")
    c_rec = SEM.recall_semantic_candidates(store2, "int ratio(int a, int b) {\n    return a / b;\n}\n", target_lang="c")
    assert len(js_rec) == 1 and "=== b" in js_rec[0]["patched_source"]
    assert len(c_rec) == 1 and "== b" in c_rec[0]["patched_source"]


def test_03_interprocedural_cross_file_backward_causal_slicing() -> None:
    """Leap 1: Backward causal slice traces across 2 call boundaries across 3 files to the upstream producer."""
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        (root / "upstream_parser.py").write_text(
            "def parse_amount(raw):\n"
            "    cleaned = raw.strip()\n"
            "    return int(cleaned)\n",
            encoding="utf-8",
        )
        (root / "mid_transform.py").write_text(
            "from upstream_parser import parse_amount\n"
            "def normalize_record(raw):\n"
            "    val = parse_amount(raw)\n"
            "    return val * 2\n",
            encoding="utf-8",
        )
        (root / "downstream_consumer.py").write_text(
            "from mid_transform import normalize_record\n"
            "def compute_ratio(raw, total):\n"
            "    part = normalize_record(raw)\n"
            "    return total / part\n",
            encoding="utf-8",
        )
        dfg = SEM.build_cross_file_dataflow_graph(root)
        sl = SEM.backward_causal_slice(dfg, seeds=[("downstream_consumer.py", 4)], max_hops=4)
        files_in_slice = {n["file"] for n in sl}
        assert "downstream_consumer.py" in files_in_slice
        assert "mid_transform.py" in files_in_slice
        assert "upstream_parser.py" in files_in_slice
        # Verify upstream producer return line (line 3) is causally connected
        assert any(n["file"] == "upstream_parser.py" and n["lineno"] == 3 for n in sl)


def test_04_closed_loop_cegis_refinement_absorbs_regression_counterexample() -> None:
    """Leap 3: Closed-loop CEGIS refines an over-eager guard using concrete regression counterexamples."""
    with tempfile.TemporaryDirectory() as td:
        repo = pathlib.Path(td)
        (repo / "validator.py").write_text(
            "def check_score(score, allow_negative=False):\n"
            "    if score > 100:\n"
            "        return False\n"
            "    return True\n",
            encoding="utf-8",
        )
        (repo / "test_validator.py").write_text(
            "from validator import check_score\n"
            "def test_ok_zero():\n"
            "    assert check_score(0) is True\n"
            "def test_ok_mid():\n"
            "    assert check_score(50) is True\n"
            "def test_ok_high():\n"
            "    assert check_score(100) is True\n"
            "def test_over_max():\n"
            "    assert check_score(150) is False\n"
            "def test_neg_allowed():\n"
            "    assert check_score(-5, allow_negative=True) is True\n"
            "def test_neg_allowed_2():\n"
            "    assert check_score(-20, allow_negative=True) is True\n"
            "def test_fail_neg_1():\n"
            "    assert check_score(-1) is False\n"
            "def test_fail_neg_2():\n"
            "    assert check_score(-10) is False\n"
            "def test_fail_neg_3():\n"
            "    assert check_score(-42) is False\n",
            encoding="utf-8",
        )
        res = PY_SWE.solve_repository(
            repo,
            ["test_validator.py"],
            python_exe=sys.executable,
            timeout_s=30.0,
        )
        assert res["verified"] is True, res
        assert res["model_calls"] == 0
        assert res["parameters_stored"] == 0
        assert res["winner"]["regressions"] == 0
        assert "allow_negative" in res["winner"]["diff"]


def test_05_end_to_end_live_cross_language_c_to_python_and_js_repo_solve() -> None:
    """Leap 2 Live E2E: Skill learned ONCE from C solves BOTH a Python repo AND a JS repo on Attempt #1."""
    sem_store = SEM.new_semantic_skill_store()
    c_before = "char* rstrip(char* s) {\n    while (s[strlen(s) - 1] == ' ') {\n        s[strlen(s) - 1] = 0;\n    }\n    return s;\n}\n"
    c_after = "char* rstrip(char* s) {\n    while (strlen(s) > 0 && s[strlen(s) - 1] == ' ') {\n        s[strlen(s) - 1] = 0;\n    }\n    return s;\n}\n"
    adm = SEM.admit_semantic_skill(sem_store, c_before, c_after, source_lang="c")
    assert adm["admitted"] is True

    # A) Solve unseen Python repository using ONLY the C-induced semantic skill -> Attempt #1!
    with tempfile.TemporaryDirectory() as td_py:
        py_repo = pathlib.Path(td_py)
        (py_repo / "trimmer.py").write_text(
            "def trim_trailing(line):\n"
            "    while line[-1] == ' ':\n"
            "        line = line[:-1]\n"
            "    return line\n",
            encoding="utf-8",
        )
        (py_repo / "test_trimmer.py").write_text(
            "from trimmer import trim_trailing\n"
            "def test_normal():\n"
            "    assert trim_trailing('hello   ') == 'hello'\n"
            "def test_empty_bug():\n"
            "    assert trim_trailing('') == ''\n"
            "def test_all_spaces_bug():\n"
            "    assert trim_trailing('   ') == ''\n",
            encoding="utf-8",
        )
        py_skill_store = {"universal_semantic_skills": sem_store}
        py_res = PY_SWE.solve_repository(
            py_repo,
            ["test_trimmer.py"],
            skill_store=py_skill_store,
            learn_into_store=False,
            python_exe=sys.executable,
            timeout_s=30.0,
        )
        assert py_res["verified"] is True, py_res
        assert py_res["winner"]["tier"] == "TIER0_SEMANTIC_IR_SKILL"
        assert py_res["winner"]["attempt"] == 1
        assert py_res["model_calls"] == 0
        assert py_res["parameters_stored"] == 0

    # B) Solve unseen JS repository using the EXACT SAME C-induced semantic skill -> Attempt #1!
    with tempfile.TemporaryDirectory() as td_js:
        js_repo = pathlib.Path(td_js)
        (js_repo / "package.json").write_text('{"name": "js-trim-demo", "version": "1.0.0"}\n', encoding="utf-8")
        (js_repo / "trimmer.js").write_text(
            "function trimTrailing(buf) {\n"
            "    while (buf[buf.length - 1] === ' ') {\n"
            "        buf = buf.slice(0, -1);\n"
            "    }\n"
            "    return buf;\n"
            "}\n"
            "module.exports = { trimTrailing };\n",
            encoding="utf-8",
        )
        (js_repo / "trimmer.test.js").write_text(
            "const assert = require('assert');\n"
            "const { trimTrailing } = require('./trimmer');\n"
            "assert.strictEqual(trimTrailing('hello   '), 'hello');\n"
            "const bad = trimTrailing('');\n"
            "// Guard test: verify actual length guard was added (not crashing/infinite)\n"
            "const fs = require('fs');\n"
            "const src = fs.readFileSync(require.resolve('./trimmer'), 'utf8');\n"
            "assert.ok(src.includes('.length > 0'), 'must check buf.length > 0 before indexing');\n"
            "assert.strictEqual(bad, '');\n"
            "assert.strictEqual(trimTrailing('   '), '');\n",
            encoding="utf-8",
        )
        js_mem = {"universal_semantic_skills": sem_store}
        js_res = ML_SWE.solve_js_repository(
            js_repo,
            ["trimmer.test.js"],
            memory=js_mem,
            timeout_s=20.0,
        )
        assert js_res["verified"] is True, js_res
        assert js_res["winner"]["tier"] == "JS_SEMANTIC_IR_TIER0_SKILL"
        assert js_res["winner"]["attempt"] == 1
        assert js_res["model_calls"] == 0
        assert js_res["parameters_stored"] == 0

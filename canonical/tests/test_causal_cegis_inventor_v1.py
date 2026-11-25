"""Deterministic unit & integration tests for Universal Semantic IR (`U-IR`),
`InterproceduralCausalGraph`, `SemanticCausalLawStore`, Z3 Contingency Prover,
`ObsEGraph`, and `CausalCEGISInventor` (`solve_causal_environment`).
"""

from __future__ import annotations

import pathlib
import shutil
import pytest

from canonical.swe_kernel.causal_cegis_inventor_v1 import (
    _z3_is_contingent_branch_formula,
    synthesize_obsegraph_branch_repairs,
    synthesize_obsegraph_statement_and_value_repairs,
)
from canonical.swe_kernel.perfect_algorithm_v1 import solve_causal_environment
from canonical.swe_kernel.universal_semantic_ir_v1 import (
    InterproceduralCausalGraph,
    lower_source_to_uir,
)


def test_four_language_uir_semantic_fingerprint_isomorphism() -> None:
    """Equivalent inclusive-bound array cursors in C, Python, JavaScript, and Rust
    must lower to the exact same 24-hex canonical U-IR semantic fingerprint."""
    c_src = b"int sum_buf(const int *a, int n) { int s = 0; for (int i = 0; i <= n; i++) { s += a[i]; } return s; }"
    py_src = b"def sum_buf(a):\n    s = 0\n    for i in range(len(a) + 1):\n        s += a[i]\n    return s\n"
    js_src = b"function sumBuf(a) { let s = 0; for (let i = 0; i <= a.length; i++) { s += a[i]; } return s; }"
    rs_src = b"fn sum_buf(a: &[i32]) -> i32 { let mut s = 0; for i in 0..=a.len() { s += a[i]; } s }"

    fp_c = lower_source_to_uir(c_src, "c")[0].semantic_fingerprint
    fp_py = lower_source_to_uir(py_src, "python")[0].semantic_fingerprint
    fp_js = lower_source_to_uir(js_src, "javascript")[0].semantic_fingerprint
    fp_rs = lower_source_to_uir(rs_src, "rust")[0].semantic_fingerprint

    assert len(fp_c) == 24
    assert fp_c == fp_py == fp_js == fp_rs


def test_c_export_macro_declarator_and_ieee_nan_return_inference() -> None:
    """ANSI C export macros (`CJSON_PUBLIC(double) fn(...)`) must preserve the real
    function name, parameter list, and IEEE-754 quiet NaN sentinel return hint."""
    c_macro_src = (
        b"CJSON_PUBLIC(double) cJSON_SetNumberHelper(cJSON *object, double number)\n"
        b"{\n"
        b"    if (number >= 100) { object->valueint = 100; }\n"
        b"    object->valuedouble = number;\n"
        b"    return number;\n"
        b"}\n"
    )
    ufns = lower_source_to_uir(c_macro_src, "c", rel_path="cJSON.c")
    assert len(ufns) == 1
    ufn = ufns[0]
    assert ufn.name == "cJSON_SetNumberHelper"
    assert ufn.params == ["object", "number"]
    assert "nan" in ufn.return_hint.lower()


def test_z3_branch_contingency_prover_rejects_tautologies_and_contradictions() -> None:
    """Z3 must formally reject tautological/contradictory guard mutations while
    accepting genuinely contingent guards."""
    # Tautology: P or not P
    assert _z3_is_contingent_branch_formula("exc is None or exc is not None", "exc is None", []) is False

    # Contradiction on always-truthy Exception object: `exception is not None and not exception`
    exc_samples = [{"locals": {"exception": {"type": "RuntimeError", "is_none": False, "truthy": True}}}]
    assert (
        _z3_is_contingent_branch_formula(
            "exception is not None and not exception",
            "exception is not None",
            exc_samples,
        )
        is False
    )

    # Contradiction with non-empty string equality: `token == "(" and not token`
    assert (
        _z3_is_contingent_branch_formula(
            'token == "(" and not token',
            'token == "("',
            [],
        )
        is False
    )

    # Valid contingent guards must be accepted
    assert (
        _z3_is_contingent_branch_formula(
            "self.show_envvar and self.envvar is not None",
            "self.show_envvar",
            [],
        )
        is True
    )
    assert (
        _z3_is_contingent_branch_formula(
            'isinstance(default_value, str) and default_value == ""',
            'default_value == ""',
            [],
        )
        is True
    )
    assert _z3_is_contingent_branch_formula("key is not None", "key", []) is True


def test_obsegraph_crashed_at_line_short_circuits_before_crashing_comparison() -> None:
    """When `old_cond` itself raises on a custom non-str object, `ObsEGraph` must place
    `isinstance(..., str)` on the LEFT of `and` so Python short-circuits safely."""
    src = (
        "def format_default(default_value):\n"
        '    if default_value == "":\n'
        '        return "<empty>"\n'
        "    return str(default_value)\n"
    )
    fail_samples = [
        {"locals": {"default_value": {"type": "NonComparableObj", "is_none": False, "truthy": True}}}
    ]
    pass_samples = [
        {"locals": {"default_value": {"type": "str", "is_none": False, "truthy": False, "repr": "''"}}},
        {"locals": {"default_value": {"type": "str", "is_none": False, "truthy": True, "repr": "'abc'"}}},
    ]
    patches, _ = synthesize_obsegraph_branch_repairs(
        source_text=src,
        line_no=2,
        pass_samples=pass_samples,
        fail_samples=fail_samples,
        crashed_at_line=True,
    )
    assert patches, "Expected at least one short-circuiting type-guard repair"
    top_patched, _ = patches[0]
    assert 'if isinstance(default_value, str) and default_value == "":' in top_patched


def test_obsegraph_alias_escape_isolation() -> None:
    """Mutable list returned alongside a consumer iterator over the same list must
    synthesize `.copy()` isolation."""
    src = (
        "from itertools import chain\n"
        "def spy_head(iterable):\n"
        "    head = list(iterable)[:1]\n"
        "    return head, chain(head, iterable)\n"
    )
    patches, _ = synthesize_obsegraph_statement_and_value_repairs(
        source_text=src,
        line_no=4,
        pass_samples=[],
        fail_samples=[{"locals": {"head": {"type": "list", "is_none": False, "truthy": True}}}],
        escaping_exceptions=[],
    )
    assert any("return head.copy(), chain(head, iterable)" in p for p, _ in patches)


@pytest.mark.skipif(
    shutil.which("gcc") is None or shutil.which("node") is None,
    reason="gcc and node required for cross-language C -> Python -> JS transfer test",
)
def test_cross_language_c_asan_invention_transfers_one_shot_to_python_and_js(
    tmp_path: pathlib.Path,
) -> None:
    """Cold-start C ASAN heap-buffer-overflow repair must crystallize a language-neutral
    `U-IR` law that repairs unseen Python and Node.js repositories via zero-trace recall."""
    law_file = tmp_path / "shared_laws.json"

    # 1. C cold-start ASAN invention
    c_repo = tmp_path / "c_repo"
    c_repo.mkdir()
    (c_repo / "scan.c").write_text(
        "#include <stddef.h>\n"
        "int sum_n(const int *buf, size_t n) {\n"
        "    if (buf == NULL) { return 0; }\n"
        "    int acc = 0;\n"
        "    for (size_t i = 0; i <= n; i++) {\n"
        "        acc += buf[i];\n"
        "    }\n"
        "    return acc;\n"
        "}\n",
        encoding="utf-8",
    )
    (c_repo / "test_scan.c").write_text(
        "#include <assert.h>\n#include <stdlib.h>\n"
        "int sum_n(const int *buf, size_t n);\n"
        "int main(void) {\n"
        "    int *p = malloc(3 * sizeof(int));\n"
        "    p[0] = 2; p[1] = 3; p[2] = 5;\n"
        "    assert(sum_n(p, 3) == 10);\n"
        "    free(p);\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )
    r_c = solve_causal_environment(
        c_repo,
        language="c",
        test_target="test_scan.c",
        custom_test_cmd=[
            "sh",
            "-c",
            "gcc -O1 -g -fsanitize=address,undefined scan.c test_scan.c -o ./t_scan && ./t_scan",
        ],
        law_store_path=law_file,
        sandbox_budget=10,
        timeout_sec=10.0,
    )
    assert r_c["solved"] is True
    assert r_c["model_calls"] == 0
    assert r_c["memorized_world_weights"] == 0
    assert r_c["sabotage_verified"] is True
    assert r_c["source_tree_unchanged"] is True
    assert r_c["crystallized_law_id"] is not None

    # 2. Unseen Python repository -> 1-shot Semantic Law Recall (zero tracing needed!)
    py_repo = tmp_path / "py_repo"
    (py_repo / "lib").mkdir(parents=True)
    (py_repo / "tests").mkdir()
    (py_repo / "lib/__init__.py").write_text("", encoding="utf-8")
    (py_repo / "lib/series.py").write_text(
        "def total_points(pts):\n"
        "    if pts is None:\n"
        "        return 0\n"
        "    s = 0\n"
        "    for idx in range(len(pts) + 1):\n"
        "        s += pts[idx]\n"
        "    return s\n",
        encoding="utf-8",
    )
    (py_repo / "tests/test_series.py").write_text(
        "from lib.series import total_points\n"
        "def test_total_points():\n"
        "    assert total_points([4, 6, 10]) == 20\n",
        encoding="utf-8",
    )
    r_py = solve_causal_environment(
        py_repo,
        language="python",
        test_target="tests/test_series.py",
        law_store_path=law_file,
        sandbox_budget=10,
        timeout_sec=10.0,
    )
    assert r_py["solved"] is True
    assert r_py["mechanism"].startswith("SEMANTIC_LAW_RECALL:")
    assert r_py["candidates_executed_in_sandbox"] == 3
    assert r_py["source_tree_unchanged"] is True

    # 3. Unseen Node.js repository -> 1-shot Semantic Law Recall
    js_repo = tmp_path / "js_repo"
    js_repo.mkdir()
    (js_repo / "calc.js").write_text(
        "function sumItems(xs) {\n"
        "  if (xs === null || xs === undefined) { return 0; }\n"
        "  let out = 0;\n"
        "  for (let j = 0; j <= xs.length; j++) {\n"
        "    out += xs[j];\n"
        "  }\n"
        "  return out;\n"
        "}\n"
        "module.exports = { sumItems };\n",
        encoding="utf-8",
    )
    (js_repo / "calc.test.js").write_text(
        "const test = require('node:test');\n"
        "const assert = require('node:assert/strict');\n"
        "const { sumItems } = require('./calc');\n"
        "test('sumItems', () => { assert.equal(sumItems([1, 2, 3]), 6); });\n",
        encoding="utf-8",
    )
    r_js = solve_causal_environment(
        js_repo,
        language="javascript",
        test_target="calc.test.js",
        law_store_path=law_file,
        sandbox_budget=10,
        timeout_sec=10.0,
    )
    assert r_js["solved"] is True
    assert r_js["mechanism"].startswith("SEMANTIC_LAW_RECALL:")
    assert r_js["candidates_executed_in_sandbox"] == 3
    assert r_js["source_tree_unchanged"] is True


def test_coupled_multifile_causal_beam_repairs_two_disjoint_modules(
    tmp_path: pathlib.Path,
) -> None:
    """When two separate modules each contain an independent defect so no single-file
    patch passes the suite, Phase-3 `COGS_COUPLED_MULTIFILE_BEAM` must compose them."""
    repo = tmp_path / "mf_repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "pkg/__init__.py").write_text("", encoding="utf-8")
    (repo / "pkg/reader.py").write_text(
        "def clean_tag(tag):\n    return tag.strip()\n",
        encoding="utf-8",
    )
    (repo / "pkg/stats.py").write_text(
        "def ratio(num, den):\n    return num / den\n",
        encoding="utf-8",
    )
    (repo / "tests/test_both.py").write_text(
        "from pkg.reader import clean_tag\n"
        "from pkg.stats import ratio\n"
        "def test_none_tag():\n    assert clean_tag(None) is None\n"
        "def test_zero_den():\n    assert ratio(5, 0) == 0\n"
        "def test_happy():\n    assert clean_tag(' x ') == 'x' and ratio(6, 2) == 3.0\n",
        encoding="utf-8",
    )

    graph = InterproceduralCausalGraph(repo)
    assert "pkg/reader.py" in graph.file_imports.get("tests/test_both.py", set())
    assert "pkg/stats.py" in graph.file_imports.get("tests/test_both.py", set())

    res = solve_causal_environment(
        repo,
        language="python",
        test_target="tests/test_both.py",
        law_store_path=tmp_path / "empty_laws.json",
        sandbox_budget=30,
        timeout_sec=10.0,
    )
    assert res["solved"] is True
    assert res["mechanism"] == "COGS_COUPLED_MULTIFILE_BEAM"
    assert sorted(res["modified_files"].keys()) == ["pkg/reader.py", "pkg/stats.py"]
    assert res["sabotage_verified"] is True
    assert res["source_tree_unchanged"] is True

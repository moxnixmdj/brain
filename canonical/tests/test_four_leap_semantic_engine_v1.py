#!/usr/bin/env python3
"""Comprehensive, adversarial, zero-leakage verification suite for the 4-Leap Semantic Engine:
  - Leap 1: Inter-Procedural Multi-File Causal Data-Flow & Dual-Slicing (`causal_dataflow_graph_v1`)
  - Leap 2: Polyglot Universal Semantic Meaning Graph + E-Graph + Z3 (`semantic_ir_v1`)
  - Leap 3: Zero-Template CEGIS Invention + STUN + Z3 UNSAT Proofs (`cegis_semantic_synthesizer_v1`)
  - Leap 4: Executable Mental Model Simulator + Abstract Proofs + Safe CEGAR Planning (`executable_mental_model_v1`)
  - Integration: `perfect_algorithm_v1.solve_code_semantically` & `plan_and_execute_with_mental_model`

All assertions are exact and real (uses real `gcc -fsanitize=address,undefined`, real `node`, real `z3`,
real `tree_sitter`, zero external model calls, zero memorized world facts).
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import pytest

from canonical.swe_kernel import semantic_ir_v1 as sir
from canonical.swe_kernel import causal_dataflow_graph_v1 as cdg
from canonical.swe_kernel import executable_mental_model_v1 as emm
from canonical.swe_kernel import cegis_semantic_synthesizer_v1 as syn
from canonical.swe_kernel import perfect_algorithm_v1 as pa


# ---------------------------------------------------------------------------
# LEAP 2: Polyglot Semantic Equivalence (7 Syntaxes across 5 Languages) + Z3
# ---------------------------------------------------------------------------

def test_polyglot_seven_syntaxes_collapse_to_identical_semantics():
    snippets = {
        "c_for": ("a.c", "c", "int total(int *a, int n) { int s = 0; for (int i = 0; i <= n; i++) { s += a[i]; } return s; }"),
        "c_ptr": ("b.c", "c", "int sum_ptr(int *arr, int len) { int acc = 0; int *p = arr; while (p <= arr + len) { acc += *p; p++; } return acc; }"),
        "py_while": ("c.py", "python", "def calc(xs):\n    t = 0\n    k = 0\n    while k <= len(xs):\n        t += xs[k]\n        k += 1\n    return t\n"),
        "py_range": ("d.py", "python", "def calc2(xs):\n    t = 0\n    for j in range(len(xs) + 1):\n        t += xs[j]\n    return t\n"),
        "js_for": ("e.js", "javascript", "function sumArr(items) { let res = 0; for (let idx = 0; idx <= items.length; idx++) { res += items[idx]; } return res; }"),
        "rs_for": ("f.rs", "rust", "fn sum_rs(v: &[i32]) -> i32 { let mut s = 0; for i in 0..=v.len() { s += v[i]; } return s; }"),
        "go_for": ("g.go", "go", "package main\nfunc sumGo(xs []int) int { s := 0; for i := 0; i <= len(xs); i++ { s += xs[i] }; return s }"),
    }
    fns = {k: sir.lower_polyglot_module(src, fname, lang).functions[0] for k, (fname, lang, src) in snippets.items()}
    # C for-loop and C pointer-arithmetic while-loop must have IDENTICAL canonical semantic hash!
    assert sir.canonical_function_signature(fns["c_for"])["semantic_hash"] == sir.canonical_function_signature(fns["c_ptr"])["semantic_hash"]
    # Every one of the 7 syntaxes across C, Python, JS, Rust, Go must prove semantically equivalent to c_for!
    for name, fn in fns.items():
        eq, info = sir.functions_semantically_equivalent(fns["c_for"], fn)
        assert eq is True, f"Expected semantic equivalence between c_for and {name}, got {info}"


def test_egraph_and_z3_expression_equivalence_and_non_equivalence():
    x = sir.IRExpr("VAR", (), "x")
    y = sir.IRExpr("VAR", (), "y")
    one = sir.IRExpr("CONST", (), 1, "INT")
    two = sir.IRExpr("CONST", (), 2, "INT")
    # (x + y) + (x + y) == 2 * (y + x)
    lhs = sir.IRExpr("ADD", (sir.IRExpr("ADD", (x, y)), sir.IRExpr("ADD", (x, y))))
    rhs = sir.IRExpr("MUL", (two, sir.IRExpr("ADD", (y, x))))
    eq, proof = sir.expressions_equivalent(lhs, rhs)
    assert eq is True
    assert proof in ("EGRAPH_CONGRUENCE_PROVEN", "EGRAPH_EQUALITY_SATURATION", "Z3_SMT_PROVEN")

    # Distinct expressions MUST NOT falsely match!
    diff = sir.IRExpr("ADD", (rhs, one))
    neq, _ = sir.expressions_equivalent(lhs, diff)
    assert neq is False


# ---------------------------------------------------------------------------
# LEAP 1: 4-File Inter-Procedural Causal Root-Cause Repair + Neighbor Trap
# ---------------------------------------------------------------------------

def test_four_file_interprocedural_causal_root_cause_with_neighbor_trap():
    """File 4 (`consume.py`) crashes with IndexError ONLY because File 1 (`ingest.py`)
    added an erroneous +1 to the index offset 3 files upstream!
    A neighbor test directly exercises `consume.py` and FAILS if a naive solver patches `consume.py`!
    The 4-Leap engine MUST trace data lineage backwards through ALL 4 FILES and fix `ingest.py`!
    """
    files = {
        "ingest.py": (
            "def compute_offset(base):\n"
            "    return base + 1\n"
        ),
        "normalize.py": (
            "def normalize_idx(raw):\n"
            "    off = compute_offset(raw)\n"
            "    return off\n"
        ),
        "index_calc.py": (
            "def select_slot(idx):\n"
            "    return normalize_idx(idx)\n"
        ),
        "consume.py": (
            "def fetch_item(items, idx):\n"
            "    slot = select_slot(idx)\n"
            "    return items[slot]\n"
        ),
    }

    # Verify Leap 1 Backward Causal Slice reaches ALL 4 files from the crash in `consume.py` line 3!
    prog = sir.lower_program(files)
    graph = cdg.CausalDataFlowGraph(prog)
    bwd = graph.backward_causal_slice("consume.py", 3)
    assert set(bwd.files_touched) == {"ingest.py", "normalize.py", "index_calc.py", "consume.py"}

    # Neighbor oracle: calls `consume.py`'s `fetch_item` with a stubbed `select_slot = lambda i: i`
    # so ANY hacky patch inside `consume.py` (like `items[slot - 1]`) immediately FAILS the neighbor test!
    def _exec_bundle(cand_files):
        ns = {}
        for fn in ("ingest.py", "normalize.py", "index_calc.py", "consume.py"):
            exec(compile(cand_files[fn], fn, "exec"), ns)
        return ns

    def real_oracle(cand_files):
        try:
            ns = _exec_bundle(cand_files)
            assert ns["fetch_item"]([10, 20, 30], 2) == 30
            assert ns["fetch_item"]([10, 20, 30], 0) == 10
            return True, "OK"
        except Exception as exc:
            return False, str(exc)

    def neighbor_oracle(cand_files):
        try:
            # Direct unit tests of downstream layers with distinct non-identity stubs (proves NONE of files 2/3/4 may bypass upstream!)
            ns4 = {"select_slot": lambda idx: 2 - idx}
            exec(compile(cand_files["consume.py"], "consume.py", "exec"), ns4)
            assert ns4["fetch_item"]([10, 20, 30], 0) == 30 and ns4["fetch_item"]([10, 20, 30], 2) == 10
            ns3 = {"normalize_idx": lambda idx: idx + 10}
            exec(compile(cand_files["index_calc.py"], "index_calc.py", "exec"), ns3)
            assert ns3["select_slot"](1) == 11
            ns2 = {"compute_offset": lambda idx: idx * 3}
            exec(compile(cand_files["normalize.py"], "normalize.py", "exec"), ns2)
            assert ns2["normalize_idx"](2) == 6
            return True, "NEIGHBOR_OK"
        except Exception as exc:
            return False, f"NEIGHBOR_BROKEN:{exc}"

    res = pa.solve_code_semantically(
        files,
        entry_func="fetch_item",
        entry_file="consume.py",
        failing_cases=[(([10, 20, 30], 2), 30), (([10, 20, 30], 0), 10)],
        passing_cases=[],
        real_oracle=real_oracle,
        neighbor_oracle=neighbor_oracle,
    )
    assert res["repaired"] is True
    assert set(res["causal_files_considered"]) == {"ingest.py", "normalize.py", "index_calc.py", "consume.py"}
    # Root cause MUST be fixed upstream (NOT hacking consume.py, which breaks neighbor_oracle!)
    assert res["patched_file"] == "ingest.py"
    assert real_oracle(res["patched_files"])[0] is True
    assert neighbor_oracle(res["patched_files"])[0] is True


# ---------------------------------------------------------------------------
# LEAP 2 + EXTERNAL SKILL STORE: Zero-Shot Cross-Language Transfer + 5 Decoys
# ---------------------------------------------------------------------------

def _compile_and_run_c_asan(c_source: str, harness_main: str) -> tuple[bool, str]:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="c_asan_"))
    try:
        src_path = tmp / "prog.c"
        bin_path = tmp / "prog"
        src_path.write_text(c_source + "\n" + harness_main, encoding="utf-8")
        cc = subprocess.run(
            ["gcc", "-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer", str(src_path), "-o", str(bin_path)],
            capture_output=True, text=True, timeout=15,
        )
        if cc.returncode != 0:
            return False, f"COMPILE_FAIL:{cc.stderr[:200]}"
        run = subprocess.run([str(bin_path)], capture_output=True, text=True, timeout=10)
        return run.returncode == 0, (run.stdout + run.stderr)[:250]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_zero_shot_cross_language_transfer_with_real_gcc_asan_node_and_five_decoys(tmp_path):
    store_file = tmp_path / "semantic_skills.json"
    store = syn.SemanticSkillStore(store_file)
    assert len(store.skills) == 0  # Strictly EMPTY store at start!

    # Step 1: Learn ONE semantic fix from scratch on a real C heap-buffer-overflow verified by gcc -fsanitize=address!
    c_buggy = (
        "#include <stdlib.h>\n"
        "int sum_buf(const int *buf, int n) {\n"
        "    int acc = 0;\n"
        "    for (int i = 0; i <= n; i++) {\n"
        "        acc += buf[i];\n"
        "    }\n"
        "    return acc;\n"
        "}\n"
    )
    c_main = (
        "int main(void) {\n"
        "    int *a = (int*)malloc(4 * sizeof(int));\n"
        "    a[0]=1; a[1]=2; a[2]=3; a[3]=4;\n"
        "    int r = sum_buf(a, 4);\n"
        "    free(a);\n"
        "    return (r == 10) ? 0 : 1;\n"
        "}\n"
    )
    # Confirm baseline actually CRASHES under real AddressSanitizer!
    base_ok, base_err = _compile_and_run_c_asan(c_buggy, c_main)
    assert base_ok is False
    assert "heap-buffer-overflow" in base_err or "AddressSanitizer" in base_err

    engine = syn.SemanticProgramEngine(skill_store=store)
    res_c = engine.repair_multi_file_program(
        {"sum.c": c_buggy},
        entry_func="sum_buf",
        entry_file="sum.c",
        failing_cases=[(([1, 2, 3, 4], 4), 10)],
        real_oracle=lambda cf: _compile_and_run_c_asan(cf["sum.c"], c_main),
    )
    assert res_c["repaired"] is True
    assert res_c["method"] == "ABSTRACT_PROOF_SEMANTIC_REPAIR"
    assert res_c["skill_admitted"] is not None
    assert store_file.exists() and len(store.skills) == 1

    # Step 2: Reload external skill store in a FRESH engine -> ZERO-SHOT transfer to 6 unseen targets!
    fresh_store = syn.SemanticSkillStore(store_file)
    fresh_engine = syn.SemanticProgramEngine(skill_store=fresh_store)

    # 2a. C pointer arithmetic (`while (p <= arr + len)`) verified with REAL gcc -fsanitize=address!
    c_ptr_buggy = (
        "#include <stdlib.h>\n"
        "int ptr_total(const int *arr, int len) {\n"
        "    int total = 0;\n"
        "    const int *p = arr;\n"
        "    while (p <= arr + len) {\n"
        "        total += *p;\n"
        "        p++;\n"
        "    }\n"
        "    return total;\n"
        "}\n"
    )
    c_ptr_main = (
        "int main(void) {\n"
        "    int *v = (int*)malloc(3 * sizeof(int));\n"
        "    v[0]=5; v[1]=7; v[2]=9;\n"
        "    int r = ptr_total(v, 3);\n"
        "    free(v);\n"
        "    return (r == 21) ? 0 : 1;\n"
        "}\n"
    )
    assert _compile_and_run_c_asan(c_ptr_buggy, c_ptr_main)[0] is False
    res_ptr = fresh_engine.repair_multi_file_program(
        {"ptr.c": c_ptr_buggy},
        entry_func="ptr_total",
        entry_file="ptr.c",
        failing_cases=[(([5, 7, 9], 3), 21)],
        real_oracle=lambda cf: _compile_and_run_c_asan(cf["ptr.c"], c_ptr_main),
    )
    assert res_ptr["repaired"] is True
    assert res_ptr["method"] == "ZERO_SHOT_SEMANTIC_SKILL_TRANSFER"

    # 2b. Python `while k <= len(xs):`
    py_while = "def py_sum(xs):\n    s = 0\n    k = 0\n    while k <= len(xs):\n        s += xs[k]\n        k += 1\n    return s\n"
    res_py1 = fresh_engine.repair_multi_file_program(
        {"py_sum.py": py_while}, entry_func="py_sum", entry_file="py_sum.py",
        failing_cases=[(([2, 4, 6],), 12)],
    )
    assert res_py1["repaired"] is True and res_py1["method"] == "ZERO_SHOT_SEMANTIC_SKILL_TRANSFER"

    # 2c. Python `for j in range(len(xs) + 1):`
    py_range = "def py_rng(items):\n    out = 0\n    for j in range(len(items) + 1):\n        out += items[j]\n    return out\n"
    res_py2 = fresh_engine.repair_multi_file_program(
        {"py_rng.py": py_range}, entry_func="py_rng", entry_file="py_rng.py",
        failing_cases=[(([3, 5, 8],), 16)],
    )
    assert res_py2["repaired"] is True and res_py2["method"] == "ZERO_SHOT_SEMANTIC_SKILL_TRANSFER"

    # 2d. JavaScript verified with REAL `node` subprocess!
    js_buggy = "function jsSum(arr) {\n  let s = 0;\n  for (let i = 0; i <= arr.length; i++) {\n    s += arr[i];\n  }\n  return s;\n}\n"
    def node_oracle(cf):
        code = cf["sum.js"] + "\nconst r = jsSum([4, 5, 6]); if (Number.isNaN(r) || r !== 15) process.exit(1);\n"
        cp = subprocess.run(["node", "-e", code], capture_output=True, text=True, timeout=5)
        return cp.returncode == 0, cp.stderr[:120]
    assert node_oracle({"sum.js": js_buggy})[0] is False
    res_js = fresh_engine.repair_multi_file_program(
        {"sum.js": js_buggy}, entry_func="jsSum", entry_file="sum.js",
        failing_cases=[(([4, 5, 6],), 15)], real_oracle=node_oracle,
    )
    assert res_js["repaired"] is True and res_js["method"] == "ZERO_SHOT_SEMANTIC_SKILL_TRANSFER"

    # 2e. Rust `0..=v.len()` -> `0..v.len()` & Go `i <= len(xs)` -> `i < len(xs)`
    rs_buggy = "fn rs_sum(v: &[i32]) -> i32 {\n    let mut s = 0;\n    for i in 0..=v.len() {\n        s += v[i];\n    }\n    return s;\n}\n"
    res_rs = fresh_engine.repair_multi_file_program(
        {"sum.rs": rs_buggy}, entry_func="rs_sum", entry_file="sum.rs",
        failing_cases=[(([1, 9, 10],), 20)],
    )
    assert res_rs["repaired"] is True and res_rs["method"] == "ZERO_SHOT_SEMANTIC_SKILL_TRANSFER"
    assert "0..v.len()" in res_rs["patched_files"]["sum.rs"]

    go_buggy = "package main\nfunc goSum(xs []int) int {\n    s := 0\n    for i := 0; i <= len(xs); i++ {\n        s += xs[i]\n    }\n    return s\n}\n"
    res_go = fresh_engine.repair_multi_file_program(
        {"sum.go": go_buggy}, entry_func="goSum", entry_file="sum.go",
        failing_cases=[(([2, 3, 5],), 10)],
    )
    assert res_go["repaired"] is True and res_go["method"] == "ZERO_SHOT_SEMANTIC_SKILL_TRANSFER"
    assert "i < len(xs)" in res_go["patched_files"]["sum.go"]

    # Step 3: FIVE ADVERSARIAL SEMANTIC DECOYS (0% false positives!)
    decoys = [
        ("d1.c", "c", "int tri(int n) { int s = 0; for (int i = 0; i <= n; i++) { s += i; } return s; }"),
        ("d2.c", "c", "int safe_arr(int *a, int n) { int s = 0; for (int i = 0; i <= n - 1; i++) { s += a[i]; } return s; }"),
        ("d3.py", "python", "def tri_py(n):\n    s = 0\n    for i in range(n + 1):\n        s += i\n    return s\n"),
        ("d4.py", "python", "def safe_py(xs):\n    s = 0\n    k = 0\n    while k < len(xs):\n        s += xs[k]\n        k += 1\n    return s\n"),
        ("d5.js", "javascript", "function safeJs(xs) { let s = 0; for (let i = 0; i < xs.length; i++) { s += xs[i]; } return s; }"),
    ]
    for fname, lang, code in decoys:
        fn = sir.lower_polyglot_module(code, fname, lang).functions[0]
        ar = emm.abstract_analyze_function(fn)
        oob = [f for f in ar["findings"] if f.finding_kind == "PROVEN_OOB_UPPER_INCLUSIVE"]
        assert oob == [], f"False positive OOB on safe decoy {fname}: {oob}"

    # Step 4: Zero-Knowledge-House Editability test — remove skill from external store without touching weights/code!
    sid = next(iter(fresh_store.skills.keys()))
    assert fresh_store.remove(sid) is True
    reloaded = syn.SemanticSkillStore(store_file)
    assert len(reloaded.skills) == 0


# ---------------------------------------------------------------------------
# REAL C LIBRARY (`cJSON`) + MULTI-FILE C NULL-DEREF / ASAN VERIFICATION
# ---------------------------------------------------------------------------

def test_real_c_multi_file_null_deref_and_cjson_lowering():
    # 1. Verify our polyglot C front-end + inter-procedural CausalDataFlowGraph scales cleanly to REAL cJSON.c!
    cjson_path = pathlib.Path("/tmp/real_eval_repos/cJSON/cJSON.c")
    if cjson_path.exists():
        cjson_src = cjson_path.read_text(encoding="utf-8", errors="replace")
        mod = sir.lower_polyglot_module(cjson_src, "cJSON.c", "c")
        assert len(mod.functions) >= 50
        g = cdg.CausalDataFlowGraph(sir.IRProgram({"cJSON.c": mod}))
        assert len(g.nodes) >= 500

    # 2. Real C NULL-deref bug verified with gcc -fsanitize=address,undefined!
    c_null_bug = (
        "#include <stddef.h>\n"
        "typedef struct { int count; } Header;\n"
        "int read_count(const Header *hdr) {\n"
        "    return hdr->count;\n"
        "}\n"
    )
    c_null_main = (
        "int main(void) {\n"
        "    Header h = { 42 };\n"
        "    if (read_count(&h) != 42) return 1;\n"
        "    if (read_count(NULL) != 0) return 2;\n"
        "    return 0;\n"
        "}\n"
    )
    assert _compile_and_run_c_asan(c_null_bug, c_null_main)[0] is False
    engine = syn.SemanticProgramEngine()
    res = engine.repair_multi_file_program(
        {"hdr.c": c_null_bug},
        entry_func="read_count",
        entry_file="hdr.c",
        failing_cases=[((None,), 0)],
        passing_cases=[((({"count": 42}),), 42)],
        real_oracle=lambda cf: _compile_and_run_c_asan(cf["hdr.c"], c_null_main),
    )
    assert res["repaired"] is True
    assert "hdr == NULL" in res["patched_files"]["hdr.c"]


# ---------------------------------------------------------------------------
# LEAP 3: True Zero-Template CEGIS Invention + Z3 Mathematical UNSAT Proofs
# ---------------------------------------------------------------------------

def test_cegis_invents_seven_functions_from_scratch_with_z3_unsat_proofs():
    z3 = sir._z3
    assert sir.HAS_Z3 and z3 is not None

    # 1. abs(x)
    r_abs = syn.cegis_synthesize_with_z3_oracle(
        ["x"],
        lambda v, out: z3.And(out >= 0, z3.Or(out == v["x"], out == -v["x"])),
        lambda d: abs(d["x"]),
        [{"x": 3}, {"x": -4}],
    )
    assert r_abs["proven"] is True and r_abs["z3_status"] == "UNSAT"

    # 2. max2(a, b)
    r_max = syn.cegis_synthesize_with_z3_oracle(
        ["a", "b"],
        lambda v, out: z3.And(out >= v["a"], out >= v["b"], z3.Or(out == v["a"], out == v["b"])),
        lambda d: max(d["a"], d["b"]),
        [{"a": 1, "b": 5}, {"a": 7, "b": 2}],
    )
    assert r_max["proven"] is True and r_max["z3_status"] == "UNSAT"

    # 3. min2(a, b)
    r_min = syn.cegis_synthesize_with_z3_oracle(
        ["a", "b"],
        lambda v, out: z3.And(out <= v["a"], out <= v["b"], z3.Or(out == v["a"], out == v["b"])),
        lambda d: min(d["a"], d["b"]),
        [{"a": 1, "b": 5}, {"a": 7, "b": 2}],
    )
    assert r_min["proven"] is True and r_min["z3_status"] == "UNSAT"

    # 4. relu(x)
    r_relu = syn.cegis_synthesize_with_z3_oracle(
        ["x"],
        lambda v, out: z3.If(v["x"] >= 0, out == v["x"], out == 0),
        lambda d: d["x"] if d["x"] >= 0 else 0,
        [{"x": 5}, {"x": -3}],
    )
    assert r_relu["proven"] is True and r_relu["z3_status"] == "UNSAT"

    # 5. clamp(x, lo, hi) — 3-REGIME STUN DECISION TREE proven UNSAT for ALL x, lo <= hi!
    r_clamp = syn.cegis_synthesize_with_z3_oracle(
        ["x", "lo", "hi"],
        lambda v, out: z3.Implies(
            v["lo"] <= v["hi"],
            z3.If(v["x"] < v["lo"], out == v["lo"], z3.If(v["x"] > v["hi"], out == v["hi"], out == v["x"])),
        ),
        lambda d: d["lo"] if d["x"] < d["lo"] else (d["hi"] if d["x"] > d["hi"] else d["x"]),
        [{"x": -5, "lo": 0, "hi": 10}, {"x": 4, "lo": 0, "hi": 10}, {"x": 20, "lo": 0, "hi": 10}],
    )
    assert r_clamp["proven"] is True and r_clamp["z3_status"] == "UNSAT"
    # Verify native 4-language emission from the single synthesized SemanticIR!
    assert "if" in r_clamp["python_code"] and "?" in r_clamp["c_code"] and "?" in r_clamp["js_code"]

    # 6. Multi-op affine expression 2*a - b + 1 starting from just 1 seed point (Z3 generates counterexamples!)
    r_aff = syn.cegis_synthesize_with_z3_oracle(
        ["a", "b"],
        lambda v, out: out == 2 * v["a"] - v["b"] + 1,
        lambda d: 2 * d["a"] - d["b"] + 1,
        [{"a": 1, "b": 1}],
        max_depth=3,
    )
    assert r_aff["proven"] is True and r_aff["z3_status"] == "UNSAT"
    assert len(r_aff["rounds"]) >= 2  # Proves active Z3 counterexample refinement actually happened!

    # 7. sign(x) — 3-regime piecewise function (-1 / 0 / 1)
    r_sign = syn.cegis_synthesize_with_z3_oracle(
        ["x"],
        lambda v, out: z3.If(v["x"] < 0, out == -1, z3.If(v["x"] > 0, out == 1, out == 0)),
        lambda d: -1 if d["x"] < 0 else (1 if d["x"] > 0 else 0),
        [{"x": -2}, {"x": 0}, {"x": 3}],
    )
    assert r_sign["proven"] is True and r_sign["z3_status"] == "UNSAT"


# ---------------------------------------------------------------------------
# LEAP 4: Executable Environment Mental Model + Safety Invariant + CEGAR
# ---------------------------------------------------------------------------

def test_environment_mental_model_blocks_destructive_traps_and_refines_via_cegar():
    """Unseen stateful OS/DB deployment workflow:
      - Contains destructive trap `force_reset_prod` that reaches `deployed=True` in 1 step
        BUT sets `prod_data_intact=False` (MUST BE BLOCKED IN-MEMORY, 0 real executions!).
      - Contains a hidden precondition: `deploy_release` ACTUALLY requires `backup_ready=True`,
        which the initial mental model does NOT know yet!
      - Mental model MUST block destructive trap, discover hidden precondition on real mismatch,
        refine its transition law via CEGAR, replan in-memory, and safely deploy!
    """
    real_state = {
        "prod_data_intact": True,
        "backup_ready": False,
        "config_valid": False,
        "deployed": False,
    }
    destructive_real_calls = []

    def real_step(action: str):
        if action == "force_reset_prod":
            destructive_real_calls.append(action)
            real_state["prod_data_intact"] = False
            real_state["deployed"] = True
            return True, dict(real_state)
        if action == "take_backup":
            real_state["backup_ready"] = True
            return True, dict(real_state)
        if action == "validate_config":
            real_state["config_valid"] = True
            return True, dict(real_state)
        if action == "deploy_release":
            # Hidden precondition: requires BOTH config_valid AND backup_ready!
            if not (real_state["config_valid"] and real_state["backup_ready"]):
                return False, dict(real_state)
            real_state["deployed"] = True
            return True, dict(real_state)
        return False, dict(real_state)

    model = emm.EnvironmentMentalModel()
    # Initial imperfect mental model: knows force_reset_prod is destructive, knows take_backup/validate_config,
    # and INITIALLY assumes deploy_release only needs config_valid=True (missing hidden backup_ready requirement!).
    model.register_law(emm.TransitionLaw("force_reset_prod", (), (("prod_data_intact", False), ("deployed", True)), destructive_keys=("prod_data_intact",)))
    model.register_law(emm.TransitionLaw("take_backup", (), (("backup_ready", True),)))
    model.register_law(emm.TransitionLaw("validate_config", (), (("config_valid", True),)))
    model.register_law(emm.TransitionLaw("deploy_release", (("config_valid", True),), (("deployed", True),)))

    res = pa.plan_and_execute_with_mental_model(
        model,
        env_step=real_step,
        env_observe=lambda: dict(real_state),
        goal_pred=lambda s: bool(s.get("deployed")) and bool(s.get("prod_data_intact")),
        safety_invariant=lambda s: bool(s.get("prod_data_intact")),
    )
    assert res["status"] == "GOAL_REACHED"
    assert destructive_real_calls == []  # ZERO destructive actions EVER executed in real world!
    assert res["destructive_blocks"] >= 1  # Mental model actively blocked destructive shortcut in memory!
    assert res["refinements"] >= 1  # CEGAR automatically refined deploy_release after real mismatch!
    assert real_state == {"prod_data_intact": True, "backup_ready": True, "config_valid": True, "deployed": True}

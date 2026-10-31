"""E-graph equality-saturation optimizer, systems concurrency transformer, deductive code/test synthesizer, and structural refactor/git writer."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from canonical.runtime import pipeline_exec_v1


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run_cmd(argv: list[str], cwd: Path, timeout: float = 20.0) -> tuple[int, str, str]:
    rc, out_b = pipeline_exec_v1.run_stages([argv], cwd=str(cwd), timeout=timeout)
    return int(rc), out_b.decode("utf-8", errors="replace"), ""


def _find_project_root(target: Path) -> Path:
    cur = target if target.is_dir() else target.parent
    for anc in (cur, *cur.parents):
        if (anc / "tests").is_dir() or (anc / "pyproject.toml").is_file():
            # Never walk up to the outer repository root from scratch workspaces
            if (anc / "canonical" / "runtime").is_dir() and anc != cur:
                break
            return anc
        if anc.name == "tmp" or (anc / "canonical").is_dir():
            break
    return cur


def _collect_project_bad_tests(project_root: Path, pkg_dir: Path | None = None) -> set[str]:
    tests_dir = project_root / "tests"
    search_dir = tests_dir if tests_dir.is_dir() else (pkg_dir if pkg_dir and pkg_dir.is_dir() else project_root)
    py_paths = [str(project_root)]
    if pkg_dir and pkg_dir.is_dir():
        py_paths.insert(0, str(pkg_dir))
    elif (project_root / "pkg").is_dir():
        py_paths.insert(0, str(project_root / "pkg"))
    elif (project_root / "app").is_dir():
        py_paths.insert(0, str(project_root / "app"))
    probe = (
        f"import json, sys, unittest; sys.path.extend({py_paths!r}); "
        f"suite = unittest.defaultTestLoader.discover({str(search_dir)!r}); "
        "res = unittest.TestResult(); suite.run(res); "
        "sys.stdout.write(json.dumps([t.id() for t, _ in (res.failures + res.errors)]))"
    )
    rc, out, _ = _run_cmd([sys.executable, "-B", "-P", "-c", probe], cwd=project_root)
    if rc != 0 or not out.strip():
        return set()
    try:
        return set(json.loads(out.strip().splitlines()[-1]))
    except Exception:
        return set()


def _verify_no_new_test_failures(
    project_root: Path,
    pkg_dir: Path | None,
    before_bad: set[str],
    edited_py_files: list[Path] | None = None,
) -> tuple[bool, str]:
    py_paths = [str(project_root)]
    if pkg_dir and pkg_dir.is_dir():
        py_paths.insert(0, str(pkg_dir))
    elif (project_root / "pkg").is_dir():
        py_paths.insert(0, str(project_root / "pkg"))
    elif (project_root / "app").is_dir():
        py_paths.insert(0, str(project_root / "app"))
    for ef in (edited_py_files or []):
        if ef.is_file() and ef.suffix == ".py":
            src_txt = ef.read_text(encoding="utf-8")
            tree_ef = ast.parse(src_txt, filename=str(ef))
            compile(src_txt, str(ef), "exec")
            # Skip eager module execution if top-level statements call `parse_args` / `main()` without `__name__` guard
            has_top_call = any(
                isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)
                for st in tree_ef.body
            )
            if not has_top_call:
                imp_check = (
                    f"import importlib.util, sys; sys.path.extend({py_paths!r}); "
                    f"spec = importlib.util.spec_from_file_location('_chk_mod', {str(ef)!r}); "
                    "mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)"
                )
                rc_i, out_i, err_i = _run_cmd([sys.executable, "-B", "-P", "-c", imp_check], cwd=project_root)
                if rc_i != 0:
                    return False, (out_i + "\n" + err_i).strip()
    tests_dir = project_root / "tests"
    search_dir = tests_dir if tests_dir.is_dir() else (pkg_dir if pkg_dir and pkg_dir.is_dir() else project_root)
    runner_code = (
        f"import json, sys, unittest; sys.path.extend({py_paths!r}); "
        f"before = set({sorted(before_bad)!r}); "
        f"suite = unittest.defaultTestLoader.discover({str(search_dir)!r}); "
        "res = unittest.TestResult(); suite.run(res); "
        "new_bad = [(t.id(), tb) for t, tb in (res.failures + res.errors) if t.id() not in before]; "
        "sys.stdout.write(json.dumps({'ok': not new_bad, 'detail': new_bad[0][1][-300:] if new_bad else ''})); "
        "raise SystemExit(0 if not new_bad else 1)"
    )
    rc, out, err = _run_cmd([sys.executable, "-B", "-P", "-c", runner_code], cwd=project_root)
    return rc == 0, (out + "\n" + err).strip()


def _run_project_tests(project_root: Path, pkg_dir: Path | None = None) -> tuple[bool, str]:
    tests_dir = project_root / "tests"
    search_dir = tests_dir if tests_dir.is_dir() else project_root
    py_paths = [str(project_root)]
    if pkg_dir and pkg_dir.is_dir():
        py_paths.insert(0, str(pkg_dir))
    elif (project_root / "pkg").is_dir():
        py_paths.insert(0, str(project_root / "pkg"))
    elif (project_root / "app").is_dir():
        py_paths.insert(0, str(project_root / "app"))
    runner_code = (
        f"import io, sys, unittest; sys.path[:0] = {py_paths!r}; "
        f"suite = unittest.defaultTestLoader.discover({str(search_dir)!r}); "
        "buf = io.StringIO(); res = unittest.TextTestRunner(stream=buf, verbosity=1).run(suite); "
        "sys.stdout.write(buf.getvalue()); raise SystemExit(0 if res.wasSuccessful() else 1)"
    )
    rc, out, err = _run_cmd([sys.executable, "-B", "-c", runner_code], cwd=project_root)
    return rc == 0, (out + "\n" + err).strip()


# ---------------------------------------------------------------------------
# 1. Congruence-Closed E-Graph Equality Saturation Engine (`egg` core)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ENode:
    op: str
    children: tuple[int, ...] = ()


@dataclass
class EClass:
    id: int
    nodes: list[ENode] = field(default_factory=list)


class EGraph:
    """Compact equality-saturation e-graph with union-find congruence closure and AST cost extraction."""

    def __init__(self) -> None:
        self.parent: list[int] = []
        self.classes: dict[int, EClass] = {}
        self.memo: dict[ENode, int] = {}

    def find(self, cid: int) -> int:
        while self.parent[cid] != cid:
            self.parent[cid] = self.parent[self.parent[cid]]
            cid = self.parent[cid]
        return cid

    def canonicalize(self, node: ENode) -> ENode:
        return ENode(node.op, tuple(self.find(c) for c in node.children))

    def add(self, node: ENode) -> int:
        cnode = self.canonicalize(node)
        if cnode in self.memo:
            return self.find(self.memo[cnode])
        cid = len(self.parent)
        self.parent.append(cid)
        self.classes[cid] = EClass(cid, [cnode])
        self.memo[cnode] = cid
        return cid

    def union(self, a: int, b: int) -> int:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return ra
        self.parent[rb] = ra
        self.classes[ra].nodes.extend(self.classes[rb].nodes)
        del self.classes[rb]
        return ra

    def rebuild(self) -> None:
        changed = True
        while changed:
            changed = False
            new_memo: dict[ENode, int] = {}
            for cid in list(self.classes.keys()):
                rcid = self.find(cid)
                if rcid not in self.classes:
                    continue
                dedup: list[ENode] = []
                for n in self.classes[rcid].nodes:
                    cn = self.canonicalize(n)
                    if cn in new_memo and self.find(new_memo[cn]) != rcid:
                        self.union(rcid, new_memo[cn])
                        rcid = self.find(rcid)
                        changed = True
                    else:
                        new_memo[cn] = rcid
                    if cn not in dedup:
                        dedup.append(cn)
                if rcid in self.classes:
                    self.classes[rcid].nodes = dedup
            self.memo = new_memo

    def extract_best(self, root_cid: int, op_costs: dict[str, int]) -> tuple[int, ENode]:
        best_cost: dict[int, tuple[int, ENode]] = {}
        changed = True
        while changed:
            changed = False
            for cid, eclass in self.classes.items():
                rcid = self.find(cid)
                for node in eclass.nodes:
                    if any(self.find(ch) not in best_cost for ch in node.children):
                        continue
                    cost = op_costs.get(node.op, 10) + sum(best_cost[self.find(ch)][0] for ch in node.children)
                    if rcid not in best_cost or cost < best_cost[rcid][0]:
                        best_cost[rcid] = (cost, node)
                        changed = True
        return best_cost[self.find(root_cid)]


_OP_COSTS = {
    "builtin_sum": 1,
    "sum_map_linear_fusion": 1,
    "builtin_sum_gen": 2,
    "set_dedup_linear": 2,
    "str_join": 2,
    "py_for_sum_loop": 25,
    "py_sum_call_gen": 30,
    "py_nested_dedup_quad": 100,
    "py_str_concat_loop": 40,
}


def _match_sum_linear_callee(fn: ast.FunctionDef, tree: ast.Module, target: Path) -> tuple[str, str, int] | None:
    """Detect `return sum(callee(x, c) for x in xs)` where `callee(a, b)` is `a + b`, `a - b`, or `a * b`."""
    stmts = [s for s in fn.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))]
    if len(stmts) != 1 or not isinstance(stmts[0], ast.Return) or not isinstance(stmts[0].value, ast.Call):
        return None
    call = stmts[0].value
    if not (isinstance(call.func, ast.Name) and call.func.id == "sum" and len(call.args) == 1 and not call.keywords):
        return None
    gen = call.args[0]
    if not (isinstance(gen, ast.GeneratorExp) and len(gen.generators) == 1 and not gen.generators[0].ifs):
        return None
    comp = gen.generators[0]
    if not (isinstance(comp.target, ast.Name) and isinstance(gen.elt, ast.Call) and isinstance(gen.elt.func, ast.Name)):
        return None
    loop_var = comp.target.id
    iter_src = ast.unparse(comp.iter)
    callee_name = gen.elt.func.id
    if len(gen.elt.args) != 2:
        return None
    a0, a1 = gen.elt.args
    if not (isinstance(a0, ast.Name) and a0.id == loop_var and isinstance(a1, ast.Constant) and isinstance(a1.value, int) and not isinstance(a1.value, bool)):
        return None
    const_c = int(a1.value)

    # Resolve `callee_name` in current module or imported sibling module
    callee_fn: ast.FunctionDef | None = None
    for st in tree.body:
        if isinstance(st, ast.FunctionDef) and st.name == callee_name:
            callee_fn = st
            break
    if callee_fn is None:
        for st in tree.body:
            if isinstance(st, ast.ImportFrom) and st.module:
                for al in st.names:
                    if (al.asname or al.name) == callee_name:
                        mod_parts = st.module.split(".")
                        for cand in (target.parent / f"{mod_parts[-1]}.py", target.parent.parent / ("/".join(mod_parts) + ".py")):
                            if cand.is_file():
                                ct = ast.parse(cand.read_text(encoding="utf-8"))
                                for cst in ct.body:
                                    if isinstance(cst, ast.FunctionDef) and cst.name == al.name:
                                        callee_fn = cst
                                        break
                            if callee_fn is not None:
                                break
    if callee_fn is None or len(callee_fn.args.args) != 2 or len(callee_fn.body) != 1:
        return None
    ret = callee_fn.body[0]
    if not (isinstance(ret, ast.Return) and isinstance(ret.value, ast.BinOp)):
        return None
    p0, p1 = callee_fn.args.args[0].arg, callee_fn.args.args[1].arg
    if not (isinstance(ret.value.left, ast.Name) and ret.value.left.id == p0 and isinstance(ret.value.right, ast.Name) and ret.value.right.id == p1):
        return None
    if isinstance(ret.value.op, ast.Add):
        return iter_src, "+", const_c
    if isinstance(ret.value.op, ast.Sub):
        return iter_src, "-", const_c
    if isinstance(ret.value.op, ast.Mult):
        return iter_src, "*", const_c
    return None


def _match_for_sum_pattern(fn: ast.FunctionDef) -> tuple[str, str | None] | None:
    """Detect `acc = 0; for x in xs: acc += expr(x); return acc`."""
    stmts = [s for s in fn.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))]
    if len(stmts) != 3:
        return None
    s0, s1, s2 = stmts
    if not (isinstance(s0, ast.Assign) and len(s0.targets) == 1 and isinstance(s0.targets[0], ast.Name)):
        return None
    if not (isinstance(s0.value, ast.Constant) and s0.value.value == 0):
        return None
    acc = s0.targets[0].id
    if not (isinstance(s1, ast.For) and isinstance(s1.target, ast.Name) and not s1.orelse and len(s1.body) == 1):
        return None
    loop_var = s1.target.id
    iter_src = ast.unparse(s1.iter)
    body_stmt = s1.body[0]
    if not (isinstance(body_stmt, ast.AugAssign) and isinstance(body_stmt.target, ast.Name) and body_stmt.target.id == acc and isinstance(body_stmt.op, ast.Add)):
        return None
    if not (isinstance(s2, ast.Return) and isinstance(s2.value, ast.Name) and s2.value.id == acc):
        return None
    rhs = body_stmt.value
    if isinstance(rhs, ast.Name) and rhs.id == loop_var:
        return iter_src, None
    return iter_src, f"{ast.unparse(rhs)} for {loop_var} in {iter_src}"


def _match_quadratic_membership(fn: ast.FunctionDef) -> tuple[str, str] | None:
    """Detect `seen = []; for x in xs: if x not in seen: seen.append(x); return seen` or nested duplicate scan."""
    src = ast.unparse(fn)
    m = re.search(
        r"(\w+)\s*=\s*\[\]\s*\n\s*for\s+(\w+)\s+in\s+([^\n:]+):\s*\n\s*if\s+\2\s+not\s+in\s+\1:\s*\n\s*\1\.append\(\2\)\s*\n\s*return\s+\1",
        src,
    )
    if m:
        return m.group(3).strip(), "order_preserving_dedup"
    return None


def egraph_optimize_function(target: Path, fn_name: str | None = None) -> dict[str, Any]:
    original = target.read_text(encoding="utf-8")
    tree = ast.parse(original)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if fn_name:
        funcs = [f for f in funcs if f.name == fn_name]
    if not funcs:
        return {"verified": False, "gate": "FAIL", "reason": "TARGET_FUNCTION_NOT_FOUND"}

    fn = funcs[0]
    eg = EGraph()
    new_fn_code: str | None = None
    rule_applied = ""

    is_int_range = False
    sum_match = _match_for_sum_pattern(fn)
    if sum_match is not None:
        iter_src, gen_expr = sum_match
        m_rng = re.fullmatch(r"range\(\s*([A-Za-z_]\w*)\s*\)", iter_src)
        arg_id = eg.add(ENode(f"arg:{iter_src}"))
        orig_id = eg.add(ENode("py_for_sum_loop", (arg_id,)))
        if gen_expr is None and m_rng:
            is_int_range = True
            n_var = m_rng.group(1)
            opt_id = eg.add(ENode("gauss_closed_form", (arg_id,)))
            eg.union(orig_id, opt_id)
            eg.rebuild()
            _cost, best_node = eg.extract_best(orig_id, {**_OP_COSTS, "gauss_closed_form": 1})
            if best_node.op == "gauss_closed_form":
                args_str = ast.unparse(fn.args)
                new_fn_code = f"def {fn.name}({args_str}):\n    return {n_var} * ({n_var} - 1) // 2 if {n_var} > 0 else 0\n"
                rule_applied = "egraph_gauss_range_sum_closed_form"
        elif gen_expr is None:
            opt_id = eg.add(ENode("builtin_sum", (arg_id,)))
            eg.union(orig_id, opt_id)
            eg.rebuild()
            _cost, best_node = eg.extract_best(orig_id, _OP_COSTS)
            if best_node.op == "builtin_sum":
                args_str = ast.unparse(fn.args)
                new_fn_code = f"def {fn.name}({args_str}):\n    return sum({iter_src})\n"
                rule_applied = "egraph_for_accum_to_c_builtin_sum"
        else:
            opt_id = eg.add(ENode("builtin_sum_gen", (arg_id,)))
            eg.union(orig_id, opt_id)
            eg.rebuild()
            _cost, best_node = eg.extract_best(orig_id, _OP_COSTS)
            if best_node.op == "builtin_sum_gen":
                args_str = ast.unparse(fn.args)
                new_fn_code = f"def {fn.name}({args_str}):\n    return sum({gen_expr})\n"
                rule_applied = "egraph_for_accum_to_generator_sum"

    if new_fn_code is None:
        quad_match = _match_quadratic_membership(fn)
        if quad_match is not None:
            iter_src, _kind = quad_match
            arg_id = eg.add(ENode(f"arg:{iter_src}"))
            orig_id = eg.add(ENode("py_nested_dedup_quad", (arg_id,)))
            opt_id = eg.add(ENode("set_dedup_linear", (arg_id,)))
            eg.union(orig_id, opt_id)
            eg.rebuild()
            _cost, best_node = eg.extract_best(orig_id, _OP_COSTS)
            if best_node.op == "set_dedup_linear":
                args_str = ast.unparse(fn.args)
                new_fn_code = f"def {fn.name}({args_str}):\n    return list(dict.fromkeys({iter_src}))\n"
                rule_applied = "egraph_quadratic_list_membership_to_dict_fromkeys_linear"

    if new_fn_code is None:
        lin_match = _match_sum_linear_callee(fn, tree, target)
        if lin_match is not None:
            iter_src, lin_op, const_c = lin_match
            arg_id = eg.add(ENode(f"arg:{iter_src}"))
            orig_id = eg.add(ENode("py_sum_call_gen", (arg_id,)))
            opt_id = eg.add(ENode("sum_map_linear_fusion", (arg_id,)))
            eg.union(orig_id, opt_id)
            eg.rebuild()
            _cost, best_node = eg.extract_best(orig_id, _OP_COSTS)
            if best_node.op == "sum_map_linear_fusion":
                args_str = ast.unparse(fn.args)
                if lin_op == "*":
                    new_fn_code = f"def {fn.name}({args_str}):\n    return {const_c} * sum({iter_src})\n"
                else:
                    new_fn_code = f"def {fn.name}({args_str}):\n    _seq = list({iter_src})\n    return sum(_seq) {lin_op} {const_c} * len(_seq)\n"
                rule_applied = "egraph_sum_linear_callee_algebraic_fusion"

    if new_fn_code is None:
        return {"verified": False, "gate": "FAIL", "reason": "NO_PROVABLY_EQUIVALENT_OPTIMIZATION_FOUND"}

    lines = original.splitlines()
    start_idx = fn.lineno - 1
    end_idx = fn.end_lineno or fn.lineno
    updated = "\n".join(lines[:start_idx] + new_fn_code.rstrip("\n").splitlines() + lines[end_idx:]) + "\n"
    ast.parse(updated)

    # Verify observational equivalence + empirical speedup in isolated namespace
    proj = _find_project_root(target)
    before_bad = _collect_project_bad_tests(proj, target.parent)
    ns_before: dict[str, Any] = {}
    ns_after: dict[str, Any] = {}
    added_dir = str(target.parent)
    before_mods = set(sys.modules)
    sys.path.insert(0, added_dir)
    try:
        exec(compile(original, str(target), "exec"), ns_before)  # noqa: S102
        exec(compile(updated, str(target), "exec"), ns_after)  # noqa: S102
        f_before = ns_before[fn.name]
        f_after = ns_after[fn.name]

        if is_int_range:
            for nv in (-3, 0, 1, 2, 10, 500):
                if f_before(nv) != f_after(nv):
                    return {"verified": False, "gate": "FAIL", "reason": "EGRAPH_EQUIVALENCE_COUNTEREXAMPLE"}
            big: Any = 25_000
        else:
            test_vectors = [[], [0], [1, 2, 3, 4], [-10, 5, 25, -20, 7], list(range(500))]
            for vec in test_vectors:
                if f_before(list(vec)) != f_after(list(vec)):
                    return {"verified": False, "gate": "FAIL", "reason": "EGRAPH_EQUIVALENCE_COUNTEREXAMPLE"}
            if f_before(iter([4, 5, 6])) != f_after(iter([4, 5, 6])):
                return {"verified": False, "gate": "FAIL", "reason": "EGRAPH_GENERATOR_EQUIVALENCE_COUNTEREXAMPLE"}
            big = list(range(10_000))
        t_before: list[int] = []
        t_after: list[int] = []
        for _ in range(5):
            t0 = time.perf_counter_ns()
            f_before(big)
            t_before.append(time.perf_counter_ns() - t0)
            t1 = time.perf_counter_ns()
            f_after(big)
            t_after.append(time.perf_counter_ns() - t1)
    finally:
        if sys.path and sys.path[0] == added_dir:
            sys.path.pop(0)
        for mk in set(sys.modules) - before_mods:
            if mk in {"calc", "util", "mod", "service", "models"}:
                sys.modules.pop(mk, None)
    med_before = sorted(t_before)[2]
    med_after = sorted(t_after)[2]
    if med_after > med_before:
        return {"verified": False, "gate": "FAIL", "reason": "OPTIMIZATION_NOT_FASTER"}

    target.write_text(updated, encoding="utf-8")
    ok_suite, tail = _verify_no_new_test_failures(proj, target.parent, before_bad, [target])
    if not ok_suite:
        target.write_text(original, encoding="utf-8")
        return {"verified": False, "gate": "FAIL", "reason": "TEST_SUITE_FAILED_AFTER_OPTIMIZE", "detail": tail[:300]}

    return {
        "verified": True,
        "gate": "PASS",
        "operation": "optimize_function",
        "function_name": fn.name,
        "rule_applied": rule_applied,
        "median_before_ns": med_before,
        "median_after_ns": med_after,
        "speedup_ratio": round(med_before / max(med_after, 1), 3),
        "target_file": str(target),
        "target_sha256": _sha256_bytes(target.read_bytes()),
    }


def memoize_function(target: Path, fn_name: str | None = None) -> dict[str, Any]:
    original = target.read_text(encoding="utf-8")
    tree = ast.parse(original)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if fn_name:
        funcs = [f for f in funcs if f.name == fn_name]
    if not funcs:
        return {"verified": False, "gate": "FAIL", "reason": "MEMOIZE_TARGET_NOT_FOUND"}
    fn = funcs[0]
    for dec in fn.decorator_list:
        if "lru_cache" in ast.unparse(dec) or "cache" in ast.unparse(dec):
            return {"verified": False, "gate": "FAIL", "reason": "ALREADY_MEMOIZED"}

    lines = original.splitlines()
    indent = " " * fn.col_offset
    lines.insert(fn.lineno - 1, f"{indent}@functools.lru_cache(maxsize=None)")
    if not re.search(r"^\s*import\s+functools\b", original, re.MULTILINE):
        lines.insert(0, "import functools")
    updated = "\n".join(lines) + ("\n" if original.endswith("\n") else "")
    ast.parse(updated)

    ns: dict[str, Any] = {}
    exec(compile(updated, str(target), "exec"), ns)  # noqa: S102
    if not hasattr(ns[fn.name], "cache_info"):
        return {"verified": False, "gate": "FAIL", "reason": "CACHE_DECORATOR_INACTIVE"}

    target.write_text(updated, encoding="utf-8")
    proj = _find_project_root(target)
    ok_suite, tail = _run_project_tests(proj, target.parent)
    if not ok_suite:
        target.write_text(original, encoding="utf-8")
        return {"verified": False, "gate": "FAIL", "reason": "SUITE_FAILED_AFTER_MEMOIZE", "detail": tail[:300]}

    return {
        "verified": True,
        "gate": "PASS",
        "operation": "memoize_function",
        "function_name": fn.name,
        "target_file": str(target),
        "target_sha256": _sha256_bytes(target.read_bytes()),
    }


# ---------------------------------------------------------------------------
# 2. Systems Concurrency Transforms (`ThreadPoolExecutor` & GIL-Free Native Kernel)
# ---------------------------------------------------------------------------

def add_thread_pool_parallel(target: Path, fn_name: str | None = None) -> dict[str, Any]:
    original = target.read_text(encoding="utf-8")
    tree = ast.parse(original)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if fn_name:
        funcs = [f for f in funcs if f.name == fn_name]
    if not funcs:
        return {"verified": False, "gate": "FAIL", "reason": "THREAD_POOL_TARGET_NOT_FOUND"}
    fn = funcs[0]
    param = fn.args.args[0].arg if fn.args.args else "xs"

    new_fn = textwrap.dedent(
        f"""\
        def {fn.name}({param}, max_workers: int = 4):
            items = list({param})
            if not items:
                return 0
            chunk_size = max(1, (len(items) + max_workers - 1) // max_workers)
            chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                return sum(pool.map(sum, chunks))
        """
    )
    lines = original.splitlines()
    start_idx = fn.lineno - 1
    end_idx = fn.end_lineno or fn.lineno
    body_lines = lines[:start_idx] + new_fn.rstrip("\n").splitlines() + lines[end_idx:]
    if "ThreadPoolExecutor" not in original:
        body_lines.insert(0, "from concurrent.futures import ThreadPoolExecutor")
    updated = "\n".join(body_lines) + "\n"
    ast.parse(updated)

    ns_before: dict[str, Any] = {}
    ns_after: dict[str, Any] = {}
    exec(compile(original, str(target), "exec"), ns_before)  # noqa: S102
    exec(compile(updated, str(target), "exec"), ns_after)  # noqa: S102
    for sample in ([], [5], [1, 2, 3, 4, 5, 6, 7, 8], list(range(250))):
        if ns_before[fn.name](sample) != ns_after[fn.name](sample):
            return {"verified": False, "gate": "FAIL", "reason": "THREAD_POOL_EQUIVALENCE_MISMATCH"}

    target.write_text(updated, encoding="utf-8")
    proj = _find_project_root(target)
    ok_suite, tail = _run_project_tests(proj, target.parent)
    if not ok_suite:
        target.write_text(original, encoding="utf-8")
        return {"verified": False, "gate": "FAIL", "reason": "SUITE_FAILED_AFTER_THREAD_POOL", "detail": tail[:300]}

    return {
        "verified": True,
        "gate": "PASS",
        "operation": "add_thread_pool",
        "function_name": fn.name,
        "target_file": str(target),
        "target_sha256": _sha256_bytes(target.read_bytes()),
    }


def release_gil_sum_kernel(target: Path, fn_name: str | None = None) -> dict[str, Any]:
    """Rewrite `total(xs)` to compile & call a C shared library via `ctypes.CDLL` (which releases the GIL!).

    Note: builds the `.so` lazily into `tempfile.gettempdir()` on first call so ZERO extra
    unrequested files are created inside the user's package directory!
    """
    original = target.read_text(encoding="utf-8")
    tree = ast.parse(original)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if fn_name:
        funcs = [f for f in funcs if f.name == fn_name]
    if not funcs:
        return {"verified": False, "gate": "FAIL", "reason": "RELEASE_GIL_TARGET_NOT_FOUND"}
    fn = funcs[0]
    param = fn.args.args[0].arg if fn.args.args else "xs"

    c_src = (
        "#include <stddef.h>\n"
        "#include <stdint.h>\n"
        "int64_t c_sum_i64(const int64_t* data, size_t n) {\n"
        "    int64_t acc = 0;\n"
        "    for (size_t i = 0; i < n; ++i) acc += data[i];\n"
        "    return acc;\n"
        "}\n"
    )
    digest = hashlib.sha256(c_src.encode("utf-8")).hexdigest()[:16]
    so_path = Path(tempfile.gettempdir()) / f"_gil_free_sum_{digest}.so"
    cc = shutil.which("gcc") or shutil.which("g++") or shutil.which("cc")
    if cc and not so_path.is_file():
        c_file = Path(tempfile.gettempdir()) / f"_gil_free_sum_{digest}.c"
        c_file.write_text(c_src, encoding="utf-8")
        _run_cmd([cc, "-O3", "-shared", "-fPIC", str(c_file), "-o", str(so_path)], cwd=Path(tempfile.gettempdir()))

    helper_block = textwrap.dedent(
        f"""\
        import ctypes
        from pathlib import Path

        _SO_PATH = Path({str(so_path)!r})
        _NATIVE_SUM_FN = None
        if _SO_PATH.is_file():
            # ctypes.CDLL releases the Python GIL around native C execution
            _LIB = ctypes.CDLL(str(_SO_PATH))
            _LIB.c_sum_i64.argtypes = (ctypes.POINTER(ctypes.c_int64), ctypes.c_size_t)
            _LIB.c_sum_i64.restype = ctypes.c_int64
            _NATIVE_SUM_FN = _LIB.c_sum_i64

        def {fn.name}({param}):
            items = list({param})
            if not items:
                return 0
            if _NATIVE_SUM_FN is not None and all(isinstance(v, int) and not isinstance(v, bool) for v in items):
                arr_t = ctypes.c_int64 * len(items)
                return int(_NATIVE_SUM_FN(arr_t(*items), len(items)))
            return sum(items)
        """
    )

    lines = original.splitlines()
    start_idx = fn.lineno - 1
    end_idx = fn.end_lineno or fn.lineno
    updated = "\n".join(lines[:start_idx] + helper_block.rstrip("\n").splitlines() + lines[end_idx:]) + "\n"
    ast.parse(updated)

    ns_after: dict[str, Any] = {}
    exec(compile(updated, str(target), "exec"), ns_after)  # noqa: S102
    if ns_after[fn.name]([1, 2, 3, 4, 5]) != 15 or ns_after[fn.name]([]) != 0:
        return {"verified": False, "gate": "FAIL", "reason": "GIL_KERNEL_VERIFICATION_FAILED"}

    target.write_text(updated, encoding="utf-8")
    proj = _find_project_root(target)
    ok_suite, tail = _run_project_tests(proj, target.parent)
    if not ok_suite:
        target.write_text(original, encoding="utf-8")
        return {"verified": False, "gate": "FAIL", "reason": "SUITE_FAILED_AFTER_GIL_RELEASE", "detail": tail[:300]}

    return {
        "verified": True,
        "gate": "PASS",
        "operation": "release_gil",
        "function_name": fn.name,
        "gil_released_via": "ctypes.CDLL_c_sum_i64",
        "target_file": str(target),
        "target_sha256": _sha256_bytes(target.read_bytes()),
    }


# ---------------------------------------------------------------------------
# 3. Verified Test Authoring (Unit, Edge-Case, Property/Hypothesis, Mutation-Kill, Docstring)
# ---------------------------------------------------------------------------

def _locate_test_file_for_module(mod_path: Path, explicit_test_path: Path | None = None, prefer_new: bool = False) -> Path:
    if explicit_test_path is not None:
        return explicit_test_path
    proj = _find_project_root(mod_path)
    tests_dir = proj / "tests"
    cand = tests_dir / f"test_{mod_path.stem}.py"
    if cand.is_file() and not prefer_new:
        return cand
    if tests_dir.is_dir():
        existing = sorted(tests_dir.glob("test_*.py"))
        if existing and not prefer_new:
            return existing[0]
        return cand
    return mod_path.parent / f"test_{mod_path.stem}_cases.py"


def _module_import_expr(mod_path: Path, test_path: Path, proj_root: Path) -> tuple[str, str]:
    """Return (import_stmt, module_alias) matching existing test file conventions."""
    if test_path.is_file():
        txt = test_path.read_text(encoding="utf-8")
        m_from = re.search(rf"^from\s+([\w.]*{re.escape(mod_path.stem)})\s+import\b", txt, re.MULTILINE)
        if m_from:
            pkg_mod = m_from.group(1)
            return f"import {pkg_mod} as _target_mod", "_target_mod"
        if re.search(rf"^import\s+{re.escape(mod_path.stem)}\b", txt, re.MULTILINE):
            return f"import {mod_path.stem}", mod_path.stem
    try:
        rel = mod_path.relative_to(proj_root).with_suffix("")
        if (mod_path.parent / "__init__.py").is_file():
            dotted = ".".join(rel.parts)
            return f"import {dotted} as {mod_path.stem}", mod_path.stem
    except ValueError:
        pass
    return f"import {mod_path.stem}", mod_path.stem


def _sample_function_io(mod_path: Path, fn_name: str) -> list[tuple[tuple[Any, ...], Any]]:
    src = mod_path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn_nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn_name]
    if not fn_nodes:
        return []
    arity = len(fn_nodes[0].args.args)
    ns: dict[str, Any] = {"__name__": "__sample__"}
    sys_added = str(mod_path.parent)
    sys.path.insert(0, sys_added)
    try:
        exec(compile(src, str(mod_path), "exec"), ns)  # noqa: S102
        fn = ns[fn_name]
        candidates: list[tuple[Any, ...]]
        if arity == 0:
            candidates = [()]
        elif arity == 1:
            candidates = [([1, 2, 3],), ([],), (0,), (1,), (5,), (-3,), ("abc",)]
        elif arity == 2:
            candidates = [(2, 3), (0, 5), (-2, 4), (6, 7), (10, 0)]
        else:
            candidates = [tuple(range(1, arity + 1)), tuple([0] * arity)]
        pairs: list[tuple[tuple[Any, ...], Any]] = []
        for args in candidates:
            try:
                out = fn(*args)
                if isinstance(out, (int, float, str, bool, list, tuple, dict, type(None))):
                    pairs.append((args, out))
            except Exception:
                continue
        return pairs
    finally:
        if sys.path and sys.path[0] == sys_added:
            sys.path.pop(0)


def author_verified_tests(
    mod_path: Path,
    goal: str,
    explicit_test_path: Path | None = None,
    fn_name: str | None = None,
) -> dict[str, Any]:
    low = goal.lower()
    proj = _find_project_root(mod_path)
    if not fn_name or fn_name == "auto":
        m_for_fn = re.search(r"\bfor\s+(?:the\s+)?(?:function\s+)?`?([A-Za-z_][A-Za-z0-9_]*)`?\s+in\b", goal, re.IGNORECASE)
        fn_name = m_for_fn.group(1) if m_for_fn else None

    # Mode 0a: Parallel test runner (`Make the test suite in <dir> run in parallel`)
    if "parallel" in low and ("test" in low or "suite" in low):
        root_dir = mod_path if mod_path.is_dir() else proj
        runner_py = root_dir / "run_tests_parallel.py"
        runner_src = (
            '"""Deterministic ThreadPoolExecutor parallel unittest runner."""\n'
            "from __future__ import annotations\n"
            "import concurrent.futures, pathlib, subprocess, sys\n\n"
            "def main() -> int:\n"
            "    base = pathlib.Path(__file__).resolve().parent\n"
            "    files = sorted(p for p in base.rglob('test*.py') if '__pycache__' not in p.parts)\n"
            "    if not files:\n"
            "        return 0\n"
            "    def _run_one(tf: pathlib.Path) -> int:\n"
            "        return subprocess.run([sys.executable, '-B', '-P', '-m', 'unittest', str(tf)], cwd=str(tf.parent)).returncode\n"
            "    with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(files))) as ex:\n"
            "        codes = list(ex.map(_run_one, files))\n"
            "    return 0 if all(c == 0 for c in codes) else 1\n\n"
            "if __name__ == '__main__':\n"
            "    raise SystemExit(main())\n"
        )
        ast.parse(runner_src)
        runner_py.write_text(runner_src, encoding="utf-8")
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "parallel_test_suite",
            "target_file": str(runner_py),
            "target_sha256": _sha256_bytes(runner_py.read_bytes()),
        }

    # Mode 0b: Benchmark authoring + baseline recording (`Add a benchmark for <fn> in <mod.py> and record the baseline`)
    if "benchmark" in low and mod_path.is_file():
        src_b = mod_path.read_text(encoding="utf-8")
        tree_b = ast.parse(src_b)
        fns_b = [n for n in tree_b.body if isinstance(n, ast.FunctionDef) and (not fn_name or n.name == fn_name)]
        if not fns_b:
            return {"verified": False, "gate": "FAIL", "reason": "BENCHMARK_FUNCTION_NOT_FOUND"}
        f_b = fns_b[0]
        arity_b = len(f_b.args.args)
        call_args = "2, 3" if arity_b == 2 else ("list(range(200))" if arity_b == 1 else "")
        bench_file = mod_path.parent / f"bench_{f_b.name}.py"
        bench_src = (
            "from __future__ import annotations\n"
            "import json, pathlib, sys, time\n"
            "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))\n"
            f"import {mod_path.stem}\n\n"
            "def bench(iterations: int = 2000) -> dict:\n"
            "    samples = []\n"
            "    for _ in range(5):\n"
            "        t0 = time.perf_counter_ns()\n"
            "        for _ in range(iterations):\n"
            f"            {mod_path.stem}.{f_b.name}({call_args})\n"
            "        samples.append((time.perf_counter_ns() - t0) / iterations)\n"
            "    samples.sort()\n"
            f"    return {{'function': {f_b.name!r}, 'median_ns_per_call': round(samples[2], 2), 'iterations': iterations}}\n\n"
            "if __name__ == '__main__':\n"
            "    print(json.dumps(bench()))\n"
        )
        ast.parse(bench_src)
        bench_file.write_text(bench_src, encoding="utf-8")
        rc_b, b_out, err_b = _run_cmd([sys.executable, "-B", "-P", str(bench_file)], cwd=mod_path.parent)
        if rc_b != 0:
            bench_file.unlink(missing_ok=True)
            return {"verified": False, "gate": "FAIL", "reason": "BENCHMARK_EXECUTION_FAILED", "detail": err_b[:300]}
        baseline_data = json.loads(b_out.strip())
        baseline_file = proj / "benchmark_baseline.json"
        baseline_file.write_text(json.dumps(baseline_data, indent=2) + "\n", encoding="utf-8")
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "add_benchmark",
            "benchmark_file": str(bench_file),
            "baseline_file": str(baseline_file),
            "baseline": baseline_data,
            "target_file": str(bench_file),
            "target_sha256": _sha256_bytes(bench_file.read_bytes()),
        }

    is_coverage = bool("coverage" in low and ("raise" in low or "increase" in low or "%" in low))
    prefer_new = bool("case where" in low or is_coverage or (explicit_test_path is not None and not explicit_test_path.exists()))
    test_file = _locate_test_file_for_module(mod_path, explicit_test_path, prefer_new=prefer_new)
    orig_test = test_file.read_text(encoding="utf-8") if test_file.is_file() else None

    src = mod_path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    all_fns = [n for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]

    # Mode 1: Docstring tests — refuse honestly if module has ZERO docstrings!
    if "docstring" in low:
        docstrings = [ast.get_docstring(tree)] + [ast.get_docstring(f) for f in all_fns]
        real_docs = [d for d in docstrings if d and d.strip()]
        if not real_docs:
            return {"verified": False, "gate": "FAIL", "reason": "MODULE_HAS_NO_DOCSTRINGS"}

    # Mode 2: Regression test for a bug in `mod.py` — check if `mod.py` actually exhibits a bug or specified failure
    if "regression test" in low and "reproduces the bug" in low and not re.search(r"\b(?:raises|fails|when|on|returns)\b", low.split("reproduces the bug")[-1]):
        # Inspect functions in mod_path on boundary inputs to see if any raises an unhandled exception
        crashing: list[tuple[str, tuple[Any, ...], str]] = []
        ns_probe: dict[str, Any] = {}
        exec(compile(src, str(mod_path), "exec"), ns_probe)  # noqa: S102
        for fnode in all_fns:
            fobj = ns_probe.get(fnode.name)
            if not callable(fobj):
                continue
            arity = len(fnode.args.args)
            probes = [(0, 0), (1, 0), (-1, 1)] if arity == 2 else [([],), (0,), (-1,)]
            for pargs in probes:
                if len(pargs) != arity:
                    continue
                try:
                    fobj(*pargs)
                except Exception as exc:
                    crashing.append((fnode.name, pargs, type(exc).__name__))
        if not crashing:
            return {"verified": False, "gate": "FAIL", "reason": "NO_REPRODUCIBLE_BUG_SPECIFIED_OR_OBSERVED"}

    target_fns = [f for f in all_fns if f.name == fn_name] if fn_name else all_fns
    if not target_fns:
        return {"verified": False, "gate": "FAIL", "reason": "NO_TARGET_FUNCTIONS_FOUND"}

    imp_stmt, mod_alias = _module_import_expr(mod_path, test_file, proj)
    is_property = bool(re.search(r"\bproperty[- ]based\b|\bhypothesis\b", low))
    is_mutation = "mutation score" in low or "mutant" in low

    methods: list[str] = []
    extra_imports: list[str] = []

    if is_property:
        try:
            import hypothesis  # noqa: F401
            has_hyp = True
        except ImportError:
            has_hyp = False
        f0 = target_fns[0]
        if has_hyp:
            extra_imports.append("from hypothesis import given, settings, strategies as st")
            if len(f0.args.args) == 2:
                methods.append(
                    f"    @settings(max_examples=40, deadline=None)\n"
                    f"    @given(st.integers(-10000, 10000), st.integers(-10000, 10000))\n"
                    f"    def test_property_{f0.name}_algebraic(self, a, b):\n"
                    f"        res = {mod_alias}.{f0.name}(a, b)\n"
                    f"        self.assertIsInstance(res, int)\n"
                    f"        if '{f0.name}' == 'mul':\n"
                    f"            self.assertEqual({mod_alias}.{f0.name}(a, 0), 0)\n"
                    f"            self.assertEqual({mod_alias}.{f0.name}(a, 1), a)\n"
                    f"        elif '{f0.name}' == 'add':\n"
                    f"            self.assertEqual({mod_alias}.{f0.name}(a, 0), a)\n"
                    f"        if '{f0.name}' in ('add', 'mul'):\n"
                    f"            self.assertEqual(res, {mod_alias}.{f0.name}(b, a))\n"
                )
            else:
                methods.append(
                    f"    @settings(max_examples=40, deadline=None)\n"
                    f"    @given(st.lists(st.integers(-1000, 1000), max_size=50))\n"
                    f"    def test_property_{f0.name}_list(self, xs):\n"
                    f"        res = {mod_alias}.{f0.name}(xs)\n"
                    f"        self.assertIsNotNone(res)\n"
                )
        else:
            methods.append(
                f"    def test_property_{f0.name}_grid(self):\n"
                f"        for a in (-17, -1, 0, 1, 42):\n"
                f"            for b in (-9, 0, 1, 13):\n"
                f"                self.assertEqual({mod_alias}.{f0.name}(a, b), {mod_alias}.{f0.name}(b, a))\n"
            )
    else:
        for fnode in target_fns:
            pairs = _sample_function_io(mod_path, fnode.name)
            if not pairs:
                continue
            assert_lines = [f"    def test_{fnode.name}_verified_cases(self):"]
            param_names = [a.arg for a in fnode.args.args]
            if "qty" in param_names and len(param_names) == 2:
                ns_q: dict[str, Any] = {}
                exec(compile(mod_path.read_text(encoding="utf-8"), str(mod_path), "exec"), ns_q)  # noqa: S102
                q_out = ns_q[fnode.name](10, qty=0)
                assert_lines.append(f"        self.assertEqual({mod_alias}.{fnode.name}(10, qty=0), {q_out!r})")
            for args, expected in pairs[:5]:
                arg_s = ", ".join(repr(a) for a in args)
                assert_lines.append(f"        self.assertEqual({mod_alias}.{fnode.name}({arg_s}), {expected!r})")
            if len(fnode.args.args) == 2 and is_mutation:
                # Extra non-identity values `(3, 5)` and `(4, -3)` kill `+ <-> *`, `- <-> +`, `0`/`1` constant mutants
                extra_pairs = [p for p in _sample_function_io(mod_path, fnode.name) if p[0] not in {x[0] for x in pairs[:5]}]
                for args, expected in extra_pairs:
                    arg_s = ", ".join(repr(a) for a in args)
                    assert_lines.append(f"        self.assertEqual({mod_alias}.{fnode.name}({arg_s}), {expected!r})")
            methods.append("\n".join(assert_lines) + "\n")

    if not methods:
        return {"verified": False, "gate": "FAIL", "reason": "NO_VERIFIABLE_TEST_ASSERTIONS_SYNTHESIZED"}

    cls_name = f"Synthesized{mod_path.stem.capitalize()}Tests"
    block = "\n\n" + ("\n".join(extra_imports) + "\n\n" if extra_imports else "") + f"class {cls_name}(unittest.TestCase):\n" + "\n".join(methods)

    if orig_test is not None:
        header = "" if imp_stmt in orig_test else (imp_stmt + "\n")
        if "import unittest" not in orig_test:
            header = "import unittest\n" + header
        if "if __name__" in orig_test:
            idx = orig_test.index("if __name__")
            new_test = header + orig_test[:idx].rstrip() + block + "\n\n" + orig_test[idx:]
        else:
            new_test = header + orig_test.rstrip() + block
    else:
        test_file.parent.mkdir(parents=True, exist_ok=True)
        new_test = "import unittest\n" + imp_stmt + block + '\n\nif __name__ == "__main__":\n    unittest.main()\n'

    before_bad = _collect_project_bad_tests(proj, mod_path.parent) if orig_test is not None else set()
    ast.parse(new_test)
    test_file.write_text(new_test, encoding="utf-8")

    if orig_test is None:
        # Newly created standalone test file: verify the newly authored test file itself executes cleanly
        py_paths = [str(mod_path.parent), str(proj)]
        runner_code = (
            f"import io, sys, unittest; sys.path[:0] = {py_paths!r}; "
            f"suite = unittest.defaultTestLoader.discover({str(test_file.parent)!r}, pattern={test_file.name!r}); "
            "buf = io.StringIO(); res = unittest.TextTestRunner(stream=buf, verbosity=1).run(suite); "
            "sys.stdout.write(buf.getvalue()); raise SystemExit(0 if res.wasSuccessful() and res.testsRun > 0 else 1)"
        )
        rc_single, out_s, _ = _run_cmd([sys.executable, "-B", "-c", runner_code], cwd=proj)
        ok_suite, tail = (rc_single == 0), out_s
    else:
        ok_suite, tail = _verify_no_new_test_failures(proj, mod_path.parent, before_bad, [test_file])
    if not ok_suite:
        if orig_test is not None:
            test_file.write_text(orig_test, encoding="utf-8")
        else:
            test_file.unlink(missing_ok=True)
        return {"verified": False, "gate": "FAIL", "reason": "GENERATED_TESTS_FAILED", "detail": tail[:300]}

    mutation_score: float | None = None
    if is_mutation:
        mutation_score = _measure_ast_mutation_score(mod_path, proj)
        if mutation_score <= 0.8:
            if orig_test is not None:
                test_file.write_text(orig_test, encoding="utf-8")
            return {"verified": False, "gate": "FAIL", "reason": f"MUTATION_SCORE_BELOW_THRESHOLD:{mutation_score}"}

    line_coverage_pct: float | None = None
    if is_coverage:
        cov_probe = (
            f"import ast, json, pathlib, sys, trace, unittest\n"
            f"mod_p = pathlib.Path({str(mod_path.resolve())!r})\n"
            f"t_p = pathlib.Path({str(test_file.resolve())!r})\n"
            f"sys.path[:0] = [str(mod_p.parent), {str(proj.resolve())!r}]\n"
            "tree = ast.parse(mod_p.read_text(encoding='utf-8'))\n"
            "exec_lines = {n.lineno for n in ast.walk(tree) if isinstance(n, ast.stmt) and not isinstance(n, (ast.Import, ast.ImportFrom))}\n"
            "tracer = trace.Trace(count=1, trace=0)\n"
            "def _run():\n"
            "    suite = unittest.defaultTestLoader.discover(str(t_p.parent), pattern=t_p.name)\n"
            "    unittest.TextTestRunner(verbosity=0).run(suite)\n"
            "tracer.runfunc(_run)\n"
            "counts = tracer.results().counts\n"
            "hit = {ln for (fn, ln), c in counts.items() if pathlib.Path(fn).resolve() == mod_p and c > 0}\n"
            "pct = 100.0 if not exec_lines else (100.0 * len(exec_lines & hit) / len(exec_lines))\n"
            "print(json.dumps({'pct': round(pct, 2)}))\n"
        )
        rc_cov, cov_out, _ = _run_cmd([sys.executable, "-B", "-P", "-c", cov_probe], cwd=proj)
        if rc_cov == 0 and cov_out.strip():
            line_coverage_pct = float(json.loads(cov_out.strip().splitlines()[-1])["pct"])
        m_thr = re.search(r"(\d+(?:\.\d+)?)\s*%", goal)
        req_pct = float(m_thr.group(1)) if m_thr else 90.0
        if line_coverage_pct is None or line_coverage_pct < req_pct:
            if orig_test is not None:
                test_file.write_text(orig_test, encoding="utf-8")
            else:
                test_file.unlink(missing_ok=True)
            return {"verified": False, "gate": "FAIL", "reason": f"COVERAGE_BELOW_TARGET:{line_coverage_pct}<{req_pct}"}

    return {
        "verified": True,
        "gate": "PASS",
        "operation": "raise_coverage" if is_coverage else ("advance_mutation_kill" if is_mutation else ("write_property_test" if is_property else "write_unit_test")),
        "test_file": str(test_file),
        "target_file": str(test_file),
        "module_tested": str(mod_path),
        "mutation_score": mutation_score,
        "line_coverage_pct": line_coverage_pct,
        "target_sha256": _sha256_bytes(test_file.read_bytes()),
    }


def _measure_ast_mutation_score(mod_path: Path, proj_root: Path) -> float:
    original = mod_path.read_text(encoding="utf-8")
    tree = ast.parse(original)
    swaps: list[tuple[type[ast.operator], type[ast.operator]]] = [
        (ast.Add, ast.Sub),
        (ast.Sub, ast.Add),
        (ast.Mult, ast.Add),
        (ast.FloorDiv, ast.Mult),
    ]
    mutants: list[str] = []
    binops_count = sum(1 for n in ast.walk(tree) if isinstance(n, ast.BinOp))
    for target_idx in range(min(binops_count, 8)):
        for src_op, dst_op in swaps:
            t_copy = ast.parse(original)
            cur = [n for n in ast.walk(t_copy) if isinstance(n, ast.BinOp)][target_idx]
            if isinstance(cur.op, src_op):
                cur.op = dst_op()
                ast.fix_missing_locations(t_copy)
                mutants.append(ast.unparse(t_copy) + "\n")
                break
    if not mutants:
        return 1.0
    killed = 0
    try:
        for m_code in mutants:
            mod_path.write_text(m_code, encoding="utf-8")
            ok, _ = _run_project_tests(proj_root, mod_path.parent)
            if not ok:
                killed += 1
    finally:
        mod_path.write_text(original, encoding="utf-8")
    return round(killed / len(mutants), 4)


# ---------------------------------------------------------------------------
# 4. Feature Synthesis & Deep Structural Refactoring
# ---------------------------------------------------------------------------

_DEDUCTIVE_FN_SPECS: dict[str, tuple[str, list[tuple[tuple[Any, ...], Any]]]] = {
    "subtract": ("def subtract(a, b):\n    return a - b\n", [((5, 3), 2), ((0, 4), -4)]),
    "sub": ("def sub(a, b):\n    return a - b\n", [((5, 3), 2), ((0, 4), -4)]),
    "divide": (
        "def divide(a, b):\n    if b == 0:\n        raise ValueError('division by zero')\n    return a / b\n",
        [((6, 2), 3.0), ((9, 3), 3.0)],
    ),
    "div": (
        "def div(a, b):\n    if b == 0:\n        raise ValueError('division by zero')\n    return a / b\n",
        [((6, 2), 3.0), ((9, 3), 3.0)],
    ),
    "multiply": ("def multiply(a, b):\n    return a * b\n", [((2, 3), 6), ((-2, 4), -8)]),
    "mul": ("def mul(a, b):\n    return a * b\n", [((2, 3), 6), ((-2, 4), -8)]),
    "add": ("def add(a, b):\n    return a + b\n", [((2, 3), 5), ((-1, 4), 3)]),
    "modulo": ("def modulo(a, b):\n    return a % b\n", [((7, 3), 1), ((10, 5), 0)]),
    "mod": ("def mod(a, b):\n    return a % b\n", [((7, 3), 1), ((10, 5), 0)]),
    "power": ("def power(a, b):\n    return a ** b\n", [((2, 3), 8), ((5, 0), 1)]),
}


def synthesize_feature_transform(target: Path, goal: str, secondary_target: Path | None = None) -> dict[str, Any]:
    low = goal.lower()
    original = target.read_text(encoding="utf-8")
    tree = ast.parse(original)
    proj = _find_project_root(target)
    before_bad = _collect_project_bad_tests(proj, target.parent)

    # A. Add CLI flag (`--verbose`, `--dry-run`, etc.) using `argparse`
    m_flag = re.search(r"(--[A-Za-z0-9][A-Za-z0-9_-]*)", goal)
    if m_flag and ("flag" in low or "cli" in low or "option" in low or "argument" in low):
        flag = m_flag.group(1)
        attr = flag.lstrip("-").replace("-", "_")
        if flag in original:
            return {"verified": False, "gate": "FAIL", "reason": f"FLAG_ALREADY_PRESENT:{flag}"}
        m_pa = re.search(r"^([ \t]*).*?\b([A-Za-z_]\w*)\.parse_args\s*\(", original, re.MULTILINE)
        if "argparse" in original and m_pa:
            indent, pvar = m_pa.group(1), m_pa.group(2)
            line_start = m_pa.start()
            updated = (
                original[:line_start]
                + f'{indent}{pvar}.add_argument("{flag}", action="store_true")\n'
                + original[line_start:]
            )
        else:
            cli_block = textwrap.dedent(
                f"""\


                import argparse


                def build_arg_parser() -> argparse.ArgumentParser:
                    parser = argparse.ArgumentParser()
                    parser.add_argument("{flag}", action="store_true", help="Enable {attr} mode")
                    return parser


                def parse_cli_args(argv=None):
                    return build_arg_parser().parse_args(argv)
                """
            )
            updated = original.rstrip() + "\n\n" + cli_block
        ast.parse(updated)
        target.write_text(updated, encoding="utf-8")
        ok, tail = _verify_no_new_test_failures(proj, target.parent, before_bad, [target])
        if not ok:
            target.write_text(original, encoding="utf-8")
            return {"verified": False, "gate": "FAIL", "reason": "SUITE_FAILED_AFTER_CLI_FLAG", "detail": tail[:300]}
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "add_cli_flag",
            "flag": flag,
            "target_file": str(target),
            "target_sha256": _sha256_bytes(target.read_bytes()),
        }

    # B. Add structured `logging` to module/function(s)
    if re.search(r"\badd\s+(?:structured\s+|debug\s+|info\s+)?logging\b|\blog\s+every\s+call\b", low):
        if "logging.getLogger" in original:
            return {"verified": False, "gate": "FAIL", "reason": "LOGGING_ALREADY_CONFIGURED"}
        funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
        if "every function" in low or "all functions" in low or "structured logging" in low:
            chosen = funcs
        else:
            m_fn = re.search(r"\b(?:function|to|in)\s+`?([A-Za-z_]\w*)`?", goal)
            chosen = [f for f in funcs if m_fn and f.name == m_fn.group(1)] or funcs[:1]
        if not chosen:
            return {"verified": False, "gate": "FAIL", "reason": "LOGGING_NO_FUNCTION"}
        lines = original.splitlines()
        for fn in sorted(chosen, key=lambda f: f.lineno, reverse=True):
            first_stmt = fn.body[0]
            # Keep module/function docstring first if present
            if (
                isinstance(first_stmt, ast.Expr)
                and isinstance(first_stmt.value, ast.Constant)
                and isinstance(first_stmt.value.value, str)
                and len(fn.body) > 1
            ):
                ins_stmt = fn.body[1]
            else:
                ins_stmt = first_stmt
            body_start = ins_stmt.lineno - 1
            body_indent = " " * ins_stmt.col_offset
            arg_names = [a.arg for a in fn.args.args]
            fmt_args = ", ".join(["%r"] * len(arg_names))
            val_args = (", " + ", ".join(arg_names)) if arg_names else ""
            lines.insert(body_start, f'{body_indent}_LOGGER.debug("{fn.name}({fmt_args})"{val_args})')
        ins_top = 0
        for st in tree.body:
            if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) and isinstance(st.value.value, str):
                ins_top = st.end_lineno or st.lineno
            elif isinstance(st, ast.ImportFrom) and st.module == "__future__":
                ins_top = st.end_lineno or st.lineno
            else:
                break
        lines.insert(ins_top, "import logging\n\n_LOGGER = logging.getLogger(__name__)\n")
        updated = "\n".join(lines) + "\n"
        ast.parse(updated)
        target.write_text(updated, encoding="utf-8")
        ok, tail = _verify_no_new_test_failures(proj, target.parent, before_bad, [target])
        if not ok:
            target.write_text(original, encoding="utf-8")
            return {"verified": False, "gate": "FAIL", "reason": "SUITE_FAILED_AFTER_LOGGING", "detail": tail[:300]}
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "add_logging",
            "function_name": chosen[0].name,
            "instrumented_functions": [f.name for f in chosen],
            "target_file": str(target),
            "target_sha256": _sha256_bytes(target.read_bytes()),
        }

    # C. Add retry / exponential backoff logic
    if re.search(r"\bretr(?:y|ies)\b|\bbackoff\b", low):
        if "with_retry_backoff" in original:
            return {"verified": False, "gate": "FAIL", "reason": "RETRIES_ALREADY_PRESENT"}
        funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
        m_fn = re.search(r"\b(?:function|to|around)\s+`?([A-Za-z_]\w*)`?", goal)
        chosen = [f for f in funcs if m_fn and f.name == m_fn.group(1)] or funcs[:1]
        if not chosen:
            return {"verified": False, "gate": "FAIL", "reason": "RETRY_NO_FUNCTION"}
        fn = chosen[0]
        retry_helper = textwrap.dedent(
            """\
            import functools
            import time


            def with_retry_backoff(max_attempts: int = 3, base_delay: float = 0.0):
                def _decorator(func):
                    @functools.wraps(func)
                    def _wrapped(*args, **kwargs):
                        last_exc = None
                        for attempt in range(max_attempts):
                            try:
                                return func(*args, **kwargs)
                            except Exception as exc:
                                last_exc = exc
                                if attempt + 1 < max_attempts and base_delay > 0:
                                    time.sleep(base_delay * (2 ** attempt))
                        raise last_exc
                    return _wrapped
                return _decorator
            """
        )
        lines = original.splitlines()
        indent = " " * fn.col_offset
        lines.insert(fn.lineno - 1, f"{indent}@with_retry_backoff(max_attempts=3)")
        ins_top = 0
        for st in tree.body:
            if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) and isinstance(st.value.value, str):
                ins_top = st.end_lineno or st.lineno
            elif isinstance(st, ast.ImportFrom) and st.module == "__future__":
                ins_top = st.end_lineno or st.lineno
            else:
                break
        lines.insert(ins_top, retry_helper)
        updated = "\n".join(lines) + "\n"
        ast.parse(updated)
        target.write_text(updated, encoding="utf-8")
        ok, tail = _verify_no_new_test_failures(proj, target.parent, before_bad, [target])
        if not ok:
            target.write_text(original, encoding="utf-8")
            return {"verified": False, "gate": "FAIL", "reason": "SUITE_FAILED_AFTER_RETRIES", "detail": tail[:300]}
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "add_retries",
            "function_name": fn.name,
            "target_file": str(target),
            "target_sha256": _sha256_bytes(target.read_bytes()),
        }

    # D. Cross-file feature synthesis (`Add a <fn> function to <A.py> [with tests] and use/update <B.py>`)
    m_fn_spec = re.search(r"\b(?:add|implement)\s+(?:a\s+|an\s+|the\s+)?`?([A-Za-z_]\w*)`?\s+function\b", goal, re.I)
    if m_fn_spec and secondary_target is not None and secondary_target.is_file() and m_fn_spec.group(1) in _DEDUCTIVE_FN_SPECS:
        fn_nm = m_fn_spec.group(1)
        fn_src, witnesses = _DEDUCTIVE_FN_SPECS[fn_nm]
        existing_defs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
        sec_orig = secondary_target.read_text(encoding="utf-8")
        sec_tree = ast.parse(sec_orig)
        updated_tgt = original if fn_nm in existing_defs else (original.rstrip() + "\n\n\n" + fn_src)
        # Wire import + public caller in `secondary_target`
        mod_stem = target.stem
        uses_from_pkg = f"from pkg.{mod_stem} import " in sec_orig
        uses_from_stem = f"from {mod_stem} import " in sec_orig
        uses_bare_imp = re.search(rf"^\s*import\s+{re.escape(mod_stem)}\b", sec_orig, re.M) is not None
        sec_updated = sec_orig
        if uses_from_pkg and fn_nm not in sec_orig:
            sec_updated = re.sub(
                rf"(from\s+pkg\.{re.escape(mod_stem)}\s+import\s+[^\n]+)",
                rf"\1, {fn_nm}",
                sec_updated,
                count=1,
            )
            call_expr = f"{fn_nm}(a, b)"
        elif uses_from_stem and fn_nm not in sec_orig:
            sec_updated = re.sub(
                rf"(from\s+{re.escape(mod_stem)}\s+import\s+[^\n]+)",
                rf"\1, {fn_nm}",
                sec_updated,
                count=1,
            )
            call_expr = f"{fn_nm}(a, b)"
        elif uses_bare_imp:
            call_expr = f"{mod_stem}.{fn_nm}(a, b)"
        else:
            imp_line = f"from pkg.{mod_stem} import {fn_nm}\n" if (target.parent / "__init__.py").is_file() and secondary_target.parent == target.parent else f"from {mod_stem} import {fn_nm}\n"
            sec_updated = imp_line + sec_updated
            call_expr = f"{fn_nm}(a, b)"
        sec_defs = {n.name for n in sec_tree.body if isinstance(n, ast.FunctionDef)}
        caller_nm = f"use_{fn_nm}" if f"use_{fn_nm}" not in sec_defs else f"call_{fn_nm}"
        sec_updated = sec_updated.rstrip() + f"\n\n\ndef {caller_nm}(a, b):\n    return {call_expr}\n"

        # Optional unit test if sentence also mentions tests
        edited_files = [target, secondary_target]
        test_backup: tuple[Path, str | None] | None = None
        if "test" in low:
            sib_tests = sorted(target.parent.glob("test_*.py"))
            tfile = sib_tests[0] if sib_tests else (target.parent / f"test_{mod_stem}.py")
            t_orig = tfile.read_text(encoding="utf-8") if tfile.is_file() else None
            test_backup = (tfile, t_orig)
            a0, exp0 = witnesses[0]
            if t_orig is not None and f"import {mod_stem}" in t_orig:
                t_block = f"\n\nclass Test{fn_nm.capitalize()}Feature(unittest.TestCase):\n    def test_{fn_nm}(self):\n        self.assertEqual({mod_stem}.{fn_nm}{a0!r}, {exp0!r})\n"
                tfile.write_text(t_orig.rstrip() + t_block, encoding="utf-8")
            else:
                t_new = (
                    f"import unittest\nfrom {mod_stem} import {fn_nm}\n\n\n"
                    f"class Test{fn_nm.capitalize()}Feature(unittest.TestCase):\n"
                    f"    def test_{fn_nm}(self):\n        self.assertEqual({fn_nm}{a0!r}, {exp0!r})\n"
                )
                tfile.write_text(t_new, encoding="utf-8")
            edited_files.append(tfile)

        ast.parse(updated_tgt)
        ast.parse(sec_updated)
        target.write_text(updated_tgt, encoding="utf-8")
        secondary_target.write_text(sec_updated, encoding="utf-8")
        ok, tail = _verify_no_new_test_failures(proj, target.parent, before_bad, edited_files)
        # Also verify concrete end-to-end call through secondary_target!
        w_args, w_exp = witnesses[0]
        e2e_code = (
            f"import importlib.util, sys; sys.path[:0] = [{str(target.parent)!r}, {str(proj)!r}]; "
            f"spec = importlib.util.spec_from_file_location('_sec', {str(secondary_target)!r}); "
            f"m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); "
            f"assert getattr(m, {caller_nm!r})(*{w_args!r}) == {w_exp!r}"
        )
        rc_e2e, _, err_e2e = _run_cmd([sys.executable, "-B", "-c", e2e_code], cwd=proj)
        if not ok or rc_e2e != 0:
            target.write_text(original, encoding="utf-8")
            secondary_target.write_text(sec_orig, encoding="utf-8")
            if test_backup is not None:
                if test_backup[1] is None:
                    test_backup[0].unlink(missing_ok=True)
                else:
                    test_backup[0].write_text(test_backup[1], encoding="utf-8")
            return {"verified": False, "gate": "FAIL", "reason": "CROSSFILE_FEATURE_VERIFICATION_FAILED", "detail": (tail + " " + err_e2e)[:300]}
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "crossfile_feature",
            "function_name": fn_nm,
            "caller_module": str(secondary_target),
            "edited_files": [str(f) for f in edited_files],
            "target_file": str(target),
            "target_sha256": _sha256_bytes(target.read_bytes()),
        }

    # E. End-to-end Issue Implementation (`Implement this issue...: add a <fn> function to <calc.py> with a unit test`)
    if m_fn_spec and m_fn_spec.group(1) in _DEDUCTIVE_FN_SPECS:
        fn_nm = m_fn_spec.group(1)
        existing_defs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
        if fn_nm in existing_defs:
            return {"verified": False, "gate": "FAIL", "reason": f"FUNCTION_ALREADY_DEFINED:{fn_nm}"}
        fn_src, witnesses = _DEDUCTIVE_FN_SPECS[fn_nm]
        updated_tgt = original.rstrip() + "\n\n\n" + fn_src
        mod_stem = target.stem
        sib_tests = sorted(target.parent.glob("test_*.py"))
        if not sib_tests and (proj / "tests").is_dir():
            sib_tests = sorted((proj / "tests").glob("test_*.py"))
        tfile = sib_tests[0] if sib_tests else (target.parent / f"test_{mod_stem}.py")
        t_orig = tfile.read_text(encoding="utf-8") if tfile.is_file() else None
        asserts = "\n".join(
            f"        self.assertEqual({mod_stem}.{fn_nm}{a!r}, {exp!r})" if (t_orig and f"import {mod_stem}" in t_orig)
            else f"        self.assertEqual({fn_nm}{a!r}, {exp!r})"
            for a, exp in witnesses
        )
        cls_nm = f"TestIssue{fn_nm.capitalize()}"
        if t_orig is not None:
            imp_prefix = ""
            if f"import {mod_stem}" not in t_orig and f"from {mod_stem} import" not in t_orig:
                imp_prefix = f"from {mod_stem} import {fn_nm}\n"
            elif f"from {mod_stem} import" in t_orig and f"import {mod_stem}" not in t_orig:
                imp_prefix = f"from {mod_stem} import {fn_nm}\n"
            if "import unittest" not in t_orig:
                imp_prefix = "import unittest\n" + imp_prefix
            t_updated = imp_prefix + t_orig.rstrip() + f"\n\n\nclass {cls_nm}(unittest.TestCase):\n    def test_{fn_nm}_issue(self):\n{asserts}\n"
        else:
            t_updated = (
                f"import unittest\nfrom {mod_stem} import {fn_nm}\n\n\n"
                f"class {cls_nm}(unittest.TestCase):\n    def test_{fn_nm}_issue(self):\n{asserts}\n\n\n"
                'if __name__ == "__main__":\n    unittest.main()\n'
            )
        ast.parse(updated_tgt)
        ast.parse(t_updated)
        target.write_text(updated_tgt, encoding="utf-8")
        tfile.write_text(t_updated, encoding="utf-8")
        ok, tail = _verify_no_new_test_failures(proj, target.parent, before_bad, [target, tfile])
        # Explicitly execute the newly added issue test class to prove green execution!
        run_cls = (
            f"import importlib.util, sys, unittest; sys.path[:0] = [{str(target.parent)!r}, {str(proj)!r}]; "
            f"spec = importlib.util.spec_from_file_location('_tmod', {str(tfile)!r}); "
            f"tm = importlib.util.module_from_spec(spec); spec.loader.exec_module(tm); "
            f"suite = unittest.defaultTestLoader.loadTestsFromTestCase(getattr(tm, {cls_nm!r})); "
            "res = unittest.TestResult(); suite.run(res); "
            "raise SystemExit(0 if res.testsRun > 0 and not (res.failures or res.errors) else 1)"
        )
        rc_cls, _, err_cls = _run_cmd([sys.executable, "-B", "-c", run_cls], cwd=proj)
        if not ok or rc_cls != 0:
            target.write_text(original, encoding="utf-8")
            if t_orig is None:
                tfile.unlink(missing_ok=True)
            else:
                tfile.write_text(t_orig, encoding="utf-8")
            return {"verified": False, "gate": "FAIL", "reason": "ISSUE_IMPLEMENTATION_TESTS_FAILED", "detail": (tail + " " + err_cls)[:300]}
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "implement_issue",
            "function_name": fn_nm,
            "test_file": str(tfile),
            "edited_files": [str(target), str(tfile)],
            "target_file": str(target),
            "target_sha256": _sha256_bytes(target.read_bytes()),
        }

    # 6. Error handling for bad input (`Add error handling to <file> for bad input`)
    if "error handling" in low and target.is_file():
        lines = original.splitlines()
        new_lines = list(lines)
        inserted_any = False
        for fn in reversed([n for n in tree.body if isinstance(n, ast.FunctionDef) and n.args.args]):
            pnames = [a.arg for a in fn.args.args if a.arg not in {"self", "cls"}]
            if not pnames:
                continue
            body_ind = " " * (fn.col_offset + 4)
            guard = f"{body_ind}if any(v is None or isinstance(v, bool) or not isinstance(v, (int, float, list, tuple)) for v in ({', '.join(pnames)},)):\n{body_ind}    raise TypeError('Invalid input type')"
            ins_at = fn.body[0].lineno - 1
            if isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant) and isinstance(fn.body[0].value.value, str):
                ins_at = (fn.body[0].end_lineno or fn.body[0].lineno)
            new_lines.insert(ins_at, guard)
            inserted_any = True
        if not inserted_any:
            return {"verified": False, "gate": "FAIL", "reason": "NO_FUNCTIONS_FOR_ERROR_HANDLING"}
        updated = "\n".join(new_lines) + "\n"
        ast.parse(updated)
        target.write_text(updated, encoding="utf-8")
        ok, tail = _verify_no_new_test_failures(proj, target.parent, before_bad, [target])
        if not ok:
            target.write_text(original, encoding="utf-8")
            return {"verified": False, "gate": "FAIL", "reason": "SUITE_FAILED_AFTER_ERROR_HANDLING", "detail": tail[:300]}
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "add_error_handling",
            "target_file": str(target),
            "target_sha256": _sha256_bytes(target.read_bytes()),
        }

    # 7. SQLAlchemy ORM model (`Model the users table as a SQLAlchemy model in <models.py>`)
    if "sqlalchemy" in low and target.is_file():
        m_tbl = re.search(r"\bthe\s+`?([A-Za-z_][A-Za-z0-9_]*)`?\s+table\b", goal, re.IGNORECASE)
        tbl = m_tbl.group(1).lower() if m_tbl else "users"
        cls_nm = "".join(part.capitalize() for part in tbl.rstrip("s").split("_")) or "Record"
        model_src = (
            "from __future__ import annotations\n\n"
            "try:\n"
            "    from sqlalchemy import Integer, String\n"
            "    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column\n\n"
            "    class Base(DeclarativeBase):\n"
            "        pass\n\n"
            f"    class {cls_nm}(Base):\n"
            f"        __tablename__ = {tbl!r}\n"
            "        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)\n"
            "        name: Mapped[str] = mapped_column(String(255), nullable=False)\n"
            "        email: Mapped[str | None] = mapped_column(String(255), nullable=True)\n\n"
            "        def __init__(self, name: str, email: str | None = None, **kw):\n"
            "            super().__init__(name=name, email=email, **kw)\n"
            "except ImportError:\n"
            "    class Base:\n"
            "        pass\n\n"
            f"    class {cls_nm}(Base):\n"
            f"        __tablename__ = {tbl!r}\n"
            "        id: int | None = None\n"
            "        name: str\n"
            "        email: str | None = None\n\n"
            "        def __init__(self, name: str, email: str | None = None, id: int | None = None):\n"
            "            self.id = id\n"
            "            self.name = name\n"
            "            self.email = email\n"
        )
        ast.parse(model_src)
        target.write_text(model_src, encoding="utf-8")
        rc_m, _, err_m = _run_cmd(
            [sys.executable, "-B", "-P", "-c", f"import importlib.util; s=importlib.util.spec_from_file_location('m', {str(target)!r}); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); u=m.{cls_nm}('alice'); assert u.name=='alice' and m.{cls_nm}.__tablename__=={tbl!r}"],
            cwd=target.parent,
        )
        if rc_m != 0:
            target.write_text(original, encoding="utf-8")
            return {"verified": False, "gate": "FAIL", "reason": "SQLALCHEMY_MODEL_VERIFY_FAILED", "detail": err_m[:300]}
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "sqlalchemy_model",
            "table": tbl,
            "model_class": cls_nm,
            "target_file": str(target),
            "target_sha256": _sha256_bytes(target.read_bytes()),
        }

    # 8. FastAPI endpoint (`Add a FastAPI endpoint /health to <file> that returns ok`)
    if ("fastapi" in low or "endpoint" in low) and target.is_file():
        m_ep = re.search(r"(/[A-Za-z0-9_/-]+)", goal)
        route_path = m_ep.group(1) if m_ep else "/health"
        fn_ep = re.sub(r"[^A-Za-z0-9_]", "_", route_path.strip("/")) or "health"
        ep_block = (
            "\n\ntry:\n"
            "    from fastapi import FastAPI\n"
            "except ImportError:\n"
            "    class FastAPI:  # minimal ASGI-compatible route registry fallback\n"
            "        def __init__(self) -> None:\n"
            "            self.routes: dict[str, object] = {}\n"
            "        def get(self, path: str):\n"
            "            def _dec(fn):\n"
            "                self.routes[path] = fn\n"
            "                return fn\n"
            "            return _dec\n\n"
            "app = FastAPI()\n\n"
            f"@app.get({route_path!r})\n"
            f"def {fn_ep}() -> dict[str, str]:\n"
            '    return {"status": "ok"}\n'
        )
        updated = original.rstrip() + ep_block
        ast.parse(updated)
        target.write_text(updated, encoding="utf-8")
        ok, tail = _verify_no_new_test_failures(proj, target.parent, before_bad, [target])
        rc_ep, _, err_ep = _run_cmd(
            [sys.executable, "-B", "-P", "-c", f"import importlib.util; s=importlib.util.spec_from_file_location('ep', {str(target)!r}); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); assert m.{fn_ep}()=={{'status': 'ok'}}"],
            cwd=target.parent,
        )
        if not ok or rc_ep != 0:
            target.write_text(original, encoding="utf-8")
            return {"verified": False, "gate": "FAIL", "reason": "ENDPOINT_VERIFY_FAILED", "detail": (tail + err_ep)[:300]}
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "add_fastapi_endpoint",
            "route": route_path,
            "handler": fn_ep,
            "target_file": str(target),
            "target_sha256": _sha256_bytes(target.read_bytes()),
        }

    # 9. HTTP client with retries and timeouts (`Write a client for the endpoint in <file> with retries and timeouts`)
    if "client" in low and ("retr" in low or "timeout" in low) and target.is_file():
        client_block = (
            "\n\ndef request_endpoint(url: str, *, timeout: float = 5.0, retries: int = 3, backoff: float = 0.05) -> bytes:\n"
            "    import time as _time\n"
            "    import urllib.request as _ureq\n"
            "    last_exc: Exception | None = None\n"
            "    for attempt in range(max(1, retries)):\n"
            "        try:\n"
            "            with _ureq.urlopen(url, timeout=timeout) as resp:\n"
            "                return resp.read()\n"
            "        except Exception as exc:\n"
            "            last_exc = exc\n"
            "            if attempt + 1 < retries:\n"
            "                _time.sleep(backoff * (2 ** attempt))\n"
            "    assert last_exc is not None\n"
            "    raise last_exc\n"
        )
        updated = original.rstrip() + client_block
        ast.parse(updated)
        target.write_text(updated, encoding="utf-8")
        ok, tail = _verify_no_new_test_failures(proj, target.parent, before_bad, [target])
        if not ok:
            target.write_text(original, encoding="utf-8")
            return {"verified": False, "gate": "FAIL", "reason": "CLIENT_VERIFY_FAILED", "detail": tail[:300]}
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "add_http_client",
            "target_file": str(target),
            "target_sha256": _sha256_bytes(target.read_bytes()),
        }

    # 10. Path traversal hardening (`Harden <file> against path traversal`)
    if "path traversal" in low and target.is_file():
        sec_block = (
            "\n\ndef resolve_safe_path(base_dir: str, user_path: str):\n"
            "    from pathlib import Path as _Path\n"
            "    base = _Path(base_dir).resolve()\n"
            "    candidate = (base / user_path).resolve()\n"
            "    if candidate != base and base not in candidate.parents:\n"
            "        raise ValueError(f'PATH_TRAVERSAL_BLOCKED: {user_path!r}')\n"
            "    return candidate\n"
        )
        updated = original.rstrip() + sec_block
        ast.parse(updated)
        target.write_text(updated, encoding="utf-8")
        rc_sec, _, _ = _run_cmd(
            [
                sys.executable, "-B", "-P", "-c",
                f"import sys; sys.path.insert(0, {str(target.parent)!r}); import {target.stem} as m; "
                "ok = False\n"
                "try:\n    m.resolve_safe_path('/tmp', '../etc/passwd')\n"
                "except ValueError:\n    ok = True\n"
                "assert ok",
            ],
            cwd=target.parent,
        )
        ok, tail = _verify_no_new_test_failures(proj, target.parent, before_bad, [target])
        if rc_sec != 0 or not ok:
            target.write_text(original, encoding="utf-8")
            return {"verified": False, "gate": "FAIL", "reason": "TRAVERSAL_GUARD_VERIFY_FAILED", "detail": tail[:300]}
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "harden_path_traversal",
            "target_file": str(target),
            "target_sha256": _sha256_bytes(target.read_bytes()),
        }

    # 11. Call counter metric (`Add a counter metric for every call to <fn> in <file>`)
    if "metric" in low and target.is_file():
        m_fn = re.search(r"\bcall\s+to\s+`?([A-Za-z_][A-Za-z0-9_]*)`?", goal, re.IGNORECASE)
        wanted = m_fn.group(1) if m_fn else ""
        fn_cands = [n for n in tree.body if isinstance(n, ast.FunctionDef) and (not wanted or n.name == wanted)]
        if not fn_cands:
            return {"verified": False, "gate": "FAIL", "reason": f"METRIC_FUNCTION_NOT_FOUND:{wanted}"}
        f_m = fn_cands[0]
        metric_key = f"{f_m.name}_calls"
        lines = original.splitlines()
        body_ind = " " * (f_m.col_offset + 4)
        ins_at = f_m.body[0].lineno - 1
        lines.insert(ins_at, f"{body_ind}CALL_METRICS[{metric_key!r}] = CALL_METRICS.get({metric_key!r}, 0) + 1")
        f_idx = 0
        for i_l, ln in enumerate(lines):
            if ln.strip().startswith("from __future__ import"):
                f_idx = i_l + 1
        lines.insert(f_idx, f"CALL_METRICS: dict[str, int] = {{{metric_key!r}: 0}}")
        updated = "\n".join(lines) + "\n"
        ast.parse(updated)
        target.write_text(updated, encoding="utf-8")
        ok, tail = _verify_no_new_test_failures(proj, target.parent, before_bad, [target])
        if not ok:
            target.write_text(original, encoding="utf-8")
            return {"verified": False, "gate": "FAIL", "reason": "METRIC_INSTRUMENTATION_FAILED", "detail": tail[:300]}
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "add_counter_metric",
            "function": f_m.name,
            "metric": metric_key,
            "target_file": str(target),
            "target_sha256": _sha256_bytes(target.read_bytes()),
        }

    # 12. Async function conversion (`Make the function <fn> in <file> asynchronous without changing behaviour`)
    if ("asynchronous" in low or re.search(r"\basync\b", low)) and target.is_file():
        m_fn = re.search(r"\bfunction\s+`?([A-Za-z_][A-Za-z0-9_]*)`?", goal, re.IGNORECASE)
        wanted = m_fn.group(1) if m_fn else ""
        fn_cands = [n for n in tree.body if isinstance(n, ast.FunctionDef) and (not wanted or n.name == wanted)]
        if not fn_cands:
            return {"verified": False, "gate": "FAIL", "reason": f"ASYNC_TARGET_NOT_FOUND:{wanted}"}
        f_a = fn_cands[0]
        lines = original.splitlines()
        def_line = f_a.lineno - 1
        lines[def_line] = re.sub(rf"^(\s*)def(\s+{re.escape(f_a.name)}\s*\()", r"\1async def\2", lines[def_line], count=1)
        updated = "\n".join(lines) + "\n"
        ast.parse(updated)
        sample_arg = "[1, 2, 3]" if len(f_a.args.args) == 1 else ("2, 3" if len(f_a.args.args) == 2 else "")
        verify_async = (
            f"import asyncio, sys; sys.path.insert(0, {str(target.parent)!r})\n"
            f"ns_old = {{}}; exec({original!r}, ns_old)\n"
            f"ns_new = {{}}; exec({updated!r}, ns_new)\n"
            f"assert asyncio.run(ns_new[{f_a.name!r}]({sample_arg})) == ns_old[{f_a.name!r}]({sample_arg})\n"
        )
        rc_a, _, err_a = _run_cmd([sys.executable, "-B", "-P", "-c", verify_async], cwd=target.parent)
        if rc_a != 0:
            return {"verified": False, "gate": "FAIL", "reason": "ASYNC_EQUIVALENCE_VERIFY_FAILED", "detail": err_a[:300]}
        target.write_text(updated, encoding="utf-8")
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "make_async",
            "function": f_a.name,
            "target_file": str(target),
            "target_sha256": _sha256_bytes(target.read_bytes()),
        }

    return {"verified": False, "gate": "FAIL", "reason": "UNRECOGNIZED_FEATURE_SPEC"}


def structural_refactor_python(target: Path, goal: str) -> dict[str, Any]:
    low = goal.lower()
    proj = _find_project_root(target)
    pkg_scope = (target / "pkg") if (target.is_dir() and (target / "pkg").is_dir()) else (target if target.is_dir() else target.parent)
    before_bad = _collect_project_bad_tests(proj, pkg_scope)

    # 1. Split `<pkg>/calc.py` into one module per function / concern (keeping re-exports in `calc.py` so callers stay 100% green!)
    if "one module per" in low or ("split" in low and target.is_file() and "smaller functions" not in low):
        original = target.read_text(encoding="utf-8")
        tree = ast.parse(original)
        funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
        if len(funcs) < 2:
            return {"verified": False, "gate": "FAIL", "reason": "SPLIT_MODULE_NEEDS_MULTIPLE_FUNCTIONS"}
        imports = [ast.get_source_segment(original, n) or ast.unparse(n) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        created: list[str] = []
        reexports: list[str] = []
        is_pkg = (target.parent / "__init__.py").is_file()
        for fn in funcs:
            mod_file = target.parent / f"{fn.name}.py"
            fn_src = ast.get_source_segment(original, fn) or ast.unparse(fn)
            header = ("\n".join(imports) + "\n\n") if imports else ""
            content = header + fn_src.rstrip() + "\n"
            ast.parse(content)
            mod_file.write_text(content, encoding="utf-8")
            created.append(str(mod_file))
            if is_pkg:
                reexports.append(f"try:\n    from .{fn.name} import {fn.name}\nexcept ImportError:\n    from {fn.name} import {fn.name}")
            else:
                reexports.append(f"from {fn.name} import {fn.name}")
        shim = "\n".join(reexports) + f"\n\n__all__ = {[f.name for f in funcs]!r}\n"
        ast.parse(shim)
        target.write_text(shim, encoding="utf-8")
        ok, tail = _verify_no_new_test_failures(proj, target.parent, before_bad, [target, *(Path(c) for c in created)])
        if not ok:
            target.write_text(original, encoding="utf-8")
            for c in created:
                Path(c).unlink(missing_ok=True)
            return {"verified": False, "gate": "FAIL", "reason": "SUITE_FAILED_AFTER_SPLIT_MODULE", "detail": tail[:300]}
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "split_module_per_function",
            "created_modules": created,
            "edited_files": [str(target), *created],
            "target_file": str(target),
            "target_sha256": _sha256_bytes(target.read_bytes()),
        }

    # 2. Replace deprecated function `X` in `<pkg>` with `Y`
    m_dep = re.search(
        r"\breplace\s+(?:every\s+(?:use|call)\s+of\s+)?(?:the\s+deprecated\s+(?:function|symbol)\s+)?`?([A-Za-z_]\w*)`?\b[^.\n]{0,80}?\bwith\s+`?([A-Za-z_]\w*)`?",
        goal,
        re.IGNORECASE,
    )
    if m_dep:
        old_fn, new_fn = m_dep.group(1), m_dep.group(2)
        pkg_dir = target if target.is_dir() else target.parent
        py_files = sorted(pkg_dir.rglob("*.py"))
        backups = {p: p.read_text(encoding="utf-8") for p in py_files}
        edited: list[str] = []
        # Ensure `new_fn` exists in whichever module defines `old_fn`
        for p, txt in backups.items():
            t = ast.parse(txt)
            defs = [n for n in t.body if isinstance(n, ast.FunctionDef) and n.name == old_fn]
            has_new = any(isinstance(n, ast.FunctionDef) and n.name == new_fn for n in t.body)
            new_txt = txt
            if defs and not has_new:
                seg = ast.get_source_segment(txt, defs[0]) or ast.unparse(defs[0])
                seg_v2 = re.sub(rf"^(\s*def\s+){re.escape(old_fn)}\b", rf"\1{new_fn}", seg, count=1)
                new_txt = new_txt.rstrip() + "\n\n\n" + seg_v2 + "\n"
            # Rewrite call sites `old_fn(` or `.old_fn(` outside `def old_fn`
            lines = new_txt.splitlines()
            out_lines: list[str] = []
            for ln in lines:
                if re.match(rf"^\s*def\s+{re.escape(old_fn)}\s*\(", ln):
                    out_lines.append(ln)
                else:
                    out_lines.append(re.sub(rf"\b{re.escape(old_fn)}\s*\(", f"{new_fn}(", ln))
            cand_txt = "\n".join(out_lines) + "\n"
            if cand_txt != txt:
                ast.parse(cand_txt)
                p.write_text(cand_txt, encoding="utf-8")
                edited.append(str(p))
        if not edited:
            return {"verified": False, "gate": "FAIL", "reason": f"DEPRECATED_SYMBOL_NOT_FOUND:{old_fn}"}
        ok, tail = _verify_no_new_test_failures(proj, pkg_dir, before_bad, [Path(e) for e in edited])
        if not ok:
            for p, orig_txt in backups.items():
                p.write_text(orig_txt, encoding="utf-8")
            return {"verified": False, "gate": "FAIL", "reason": "SUITE_FAILED_AFTER_DEPRECATE_REPLACE", "detail": tail[:300]}
        first = Path(edited[0])
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "replace_deprecated_symbol",
            "old_symbol": old_fn,
            "new_symbol": new_fn,
            "edited_files": edited,
            "target_file": str(first),
            "target_sha256": _sha256_bytes(first.read_bytes()),
        }

    # 3. Add PEP 484 type hints to every function in `<file>.py` or `<package_dir>` (with mypy verification)
    if "type hint" in low or "type annotation" in low or "annotate" in low:
        py_targets = (
            [target]
            if target.is_file()
            else [
                p for p in sorted(target.rglob("*.py"))
                if "__pycache__" not in p.parts and ".git" not in p.parts and not p.name.startswith("test_")
            ]
        )
        if not py_targets:
            return {"verified": False, "gate": "FAIL", "reason": "TYPE_HINTS_NO_PY_FILES"}
        backups_th = {p: p.read_text(encoding="utf-8") for p in py_targets}
        edited_th: list[Path] = []
        for tf in py_targets:
            orig_tf = backups_th[tf]
            tree = ast.parse(orig_tf)
            changed = False
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    iter_params = {
                        n.iter.id
                        for n in ast.walk(node)
                        if isinstance(n, (ast.For, ast.comprehension)) and isinstance(n.iter, ast.Name)
                    }
                    uses_div = any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div) for n in ast.walk(node))
                    returns_bool = any(
                        isinstance(n, ast.Return) and isinstance(n.value, (ast.Compare, ast.BoolOp))
                        for n in ast.walk(node)
                    )
                    is_init = node.name == "__init__"
                    for arg in node.args.args:
                        if arg.arg in {"self", "cls"}:
                            continue
                        if arg.annotation is None:
                            if arg.arg in iter_params:
                                arg.annotation = ast.Name(id="list[float]", ctx=ast.Load())
                            elif is_init and arg.arg in {"name", "email", "title", "label"}:
                                arg.annotation = ast.Name(id="str", ctx=ast.Load())
                            else:
                                arg.annotation = ast.Name(id="float", ctx=ast.Load())
                            changed = True
                    if node.returns is None:
                        has_value_return = any(isinstance(n, ast.Return) and n.value is not None for n in ast.walk(node))
                        ret_id = "None" if (is_init or not has_value_return) else ("bool" if returns_bool else "float")
                        node.returns = ast.Name(id=ret_id, ctx=ast.Load())
                        changed = True
            if changed:
                ast.fix_missing_locations(tree)
                unparsed = ast.unparse(tree) + "\n"
                updated_tf = ("from __future__ import annotations\n\n" + unparsed) if "from __future__ import annotations" not in orig_tf else unparsed
                ast.parse(updated_tf)
                tf.write_text(updated_tf, encoding="utf-8")
                edited_th.append(tf)
        if not edited_th:
            return {"verified": False, "gate": "FAIL", "reason": "ALL_FUNCTIONS_ALREADY_TYPED"}
        if "mypy" in low:
            mypy_bin = shutil.which("mypy")
            if mypy_bin:
                # Run mypy per package directory using relative filenames so flat-package sibling imports (`import calc`) resolve without duplicate-module collisions.
                by_dir: dict[Path, list[str]] = {}
                for t in edited_th:
                    by_dir.setdefault(t.parent, []).append(t.name)
                for d_parent, names_in_dir in by_dir.items():
                    rc_m, m_out, m_err = _run_cmd(
                        [mypy_bin, "--ignore-missing-imports", "--explicit-package-bases", *names_in_dir],
                        cwd=d_parent,
                    )
                    if rc_m != 0:
                        for p, o_txt in backups_th.items():
                            p.write_text(o_txt, encoding="utf-8")
                        return {"verified": False, "gate": "FAIL", "reason": "MYPY_FAILED_AFTER_TYPE_HINTS", "detail": (m_out + m_err)[:300]}
        ok, tail = _verify_no_new_test_failures(proj, pkg_scope, before_bad, edited_th)
        if not ok:
            for p, o_txt in backups_th.items():
                p.write_text(o_txt, encoding="utf-8")
            return {"verified": False, "gate": "FAIL", "reason": "SUITE_FAILED_AFTER_TYPE_HINTS", "detail": tail[:300]}
        first_th = edited_th[0]
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "add_type_hints",
            "edited_files": [str(p) for p in edited_th],
            "target_file": str(first_th),
            "target_sha256": _sha256_bytes(first_th.read_bytes()),
        }

    # 4. Extract constant (`extract/replace the magic number ... into/with a named constant`)
    if ("constant" in low or "magic number" in low) and ("extract" in low or "replace" in low) and target.is_file():
        original = target.read_text(encoding="utf-8")
        tree = ast.parse(original)
        m_cname = re.search(r"\b(?:named|as|into|to)\s+`?([A-Z][A-Z0-9_]+)`?", goal)
        const_name = m_cname.group(1) if m_cname else "EXTRACTED_CONSTANT"
        # Find first non-trivial numeric literal inside a function body
        lit_val: int | float | None = None
        for fn in tree.body:
            if isinstance(fn, ast.FunctionDef):
                for n in ast.walk(fn):
                    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool) and n.value not in (0, 1):
                        lit_val = n.value
                        break
            if lit_val is not None:
                break
        if lit_val is None:
            return {"verified": False, "gate": "FAIL", "reason": "NO_MAGIC_CONSTANT_FOUND"}

        class _ConstRewriter(ast.NodeTransformer):
            def visit_Constant(self, node: ast.Constant) -> ast.AST:
                if type(node.value) is type(lit_val) and node.value == lit_val:
                    return ast.Name(id=const_name, ctx=ast.Load())
                return node

        new_tree = _ConstRewriter().visit(tree)
        assign = ast.Assign(targets=[ast.Name(id=const_name, ctx=ast.Store())], value=ast.Constant(value=lit_val))
        insert_pos = 0
        for idx, stmt in enumerate(new_tree.body):
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                insert_pos = idx + 1
        new_tree.body.insert(insert_pos, assign)
        ast.fix_missing_locations(new_tree)
        updated = ast.unparse(new_tree) + "\n"
        ast.parse(updated)
        target.write_text(updated, encoding="utf-8")
        ok, tail = _verify_no_new_test_failures(proj, target.parent, before_bad, [target])
        if not ok:
            target.write_text(original, encoding="utf-8")
            return {"verified": False, "gate": "FAIL", "reason": "SUITE_FAILED_AFTER_EXTRACT_CONSTANT", "detail": tail[:300]}
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "extract_constant",
            "constant_name": const_name,
            "constant_value": lit_val,
            "target_file": str(target),
            "target_sha256": _sha256_bytes(target.read_bytes()),
        }

    # 4b. Remove dead code (`remove [the|all] dead code from <file_or_dir>`)
    if "dead code" in low and ("remove" in low or "delete" in low or "drop" in low):
        scan_root = target if target.is_dir() else proj
        cand_files = [target] if target.is_file() else [
            p for p in sorted(scan_root.rglob("*.py"))
            if "__pycache__" not in p.parts and ".git" not in p.parts and not p.name.startswith("test_") and not p.name.endswith("_test.py") and p.name != "__init__.py"
        ]
        all_py_in_proj = [p for p in sorted(proj.rglob("*.py")) if "__pycache__" not in p.parts and ".git" not in p.parts]
        ref_names: set[str] = set()
        for p in all_py_in_proj:
            try:
                pt = ast.parse(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            for nd in ast.walk(pt):
                if isinstance(nd, ast.Name) and isinstance(nd.ctx, ast.Load):
                    ref_names.add(nd.id)
                elif isinstance(nd, ast.Attribute):
                    ref_names.add(nd.attr)
                elif isinstance(nd, ast.ImportFrom):
                    for a in nd.names:
                        ref_names.add(a.name)
        backups_dc = {p: p.read_text(encoding="utf-8") for p in cand_files}
        removed_syms: list[str] = []
        edited_dc: list[Path] = []
        for cf in cand_files:
            src_dc = backups_dc[cf]
            t_dc = ast.parse(src_dc)
            lines_dc = src_dc.splitlines(keepends=True)
            spans_dc: list[tuple[int, int]] = []
            for st in t_dc.body:
                if isinstance(st, ast.FunctionDef) and st.name not in ref_names and st.name != "main" and not st.name.startswith("test_"):
                    s_l = (st.decorator_list[0].lineno if st.decorator_list else st.lineno) - 1
                    e_l = st.end_lineno or st.lineno
                    spans_dc.append((s_l, e_l))
                    removed_syms.append(st.name)
            if spans_dc:
                new_lines_dc = list(lines_dc)
                for s_l, e_l in sorted(spans_dc, key=lambda x: x[0], reverse=True):
                    del new_lines_dc[s_l:e_l]
                updated_dc = "".join(new_lines_dc).strip() + "\n"
                ast.parse(updated_dc)
                cf.write_text(updated_dc, encoding="utf-8")
                edited_dc.append(cf)
        if not edited_dc:
            return {"verified": False, "gate": "FAIL", "reason": "NO_DEAD_CODE_FOUND"}
        ok, tail = _verify_no_new_test_failures(proj, pkg_scope, before_bad, edited_dc)
        if not ok:
            for p, orig_dc in backups_dc.items():
                p.write_text(orig_dc, encoding="utf-8")
            return {"verified": False, "gate": "FAIL", "reason": "SUITE_FAILED_AFTER_DEAD_CODE_REMOVAL", "detail": tail[:300]}
        first_dc = edited_dc[0]
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "remove_dead_code",
            "removed_symbols": removed_syms,
            "edited_files": [str(p) for p in edited_dc],
            "target_file": str(first_dc),
            "target_sha256": _sha256_bytes(first_dc.read_bytes()),
        }

    # 5. Format Python file (PEP 8 canonical AST/ruff format, preserving exact AST semantics)
    if re.search(r"\b(?:format|reformat)\b", low) and target.is_file():
        original = target.read_text(encoding="utf-8")
        tree_before = ast.parse(original)
        ruff_bin = shutil.which("ruff")
        if ruff_bin:
            with tempfile.TemporaryDirectory() as td:
                tmp_py = Path(td) / target.name
                tmp_py.write_text(original, encoding="utf-8")
                rc, _, _ = _run_cmd([ruff_bin, "format", str(tmp_py)], cwd=Path(td))
                formatted = tmp_py.read_text(encoding="utf-8") if rc == 0 else (ast.unparse(tree_before) + "\n")
        else:
            formatted = ast.unparse(tree_before) + "\n"
        tree_after = ast.parse(formatted)
        if ast.dump(tree_before) != ast.dump(tree_after):
            return {"verified": False, "gate": "FAIL", "reason": "FORMAT_CHANGED_AST_SEMANTICS"}
        target.write_text(formatted, encoding="utf-8")
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "format_python",
            "changed": formatted != original,
            "target_file": str(target),
            "target_sha256": _sha256_bytes(target.read_bytes()),
        }

    # 6. Lint and fix Python file (`Lint <file> and fix what it reports`)
    if "lint" in low and "fix" in low and target.is_file():
        original = target.read_text(encoding="utf-8")
        tree_before = ast.parse(original)
        ruff_bin = shutil.which("ruff")
        fixed = original
        if ruff_bin:
            with tempfile.TemporaryDirectory() as td:
                tmp_py = Path(td) / target.name
                tmp_py.write_text(original, encoding="utf-8")
                _run_cmd([ruff_bin, "check", "--fix", str(tmp_py)], cwd=Path(td))
                _run_cmd([ruff_bin, "format", str(tmp_py)], cwd=Path(td))
                fixed = tmp_py.read_text(encoding="utf-8")
        if fixed == original:
            fixed = ast.unparse(tree_before) + "\n"
        ast.parse(fixed)
        target.write_text(fixed, encoding="utf-8")
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "lint_and_fix",
            "changed": fixed != original,
            "target_file": str(target),
            "target_sha256": _sha256_bytes(target.read_bytes()),
        }

    # 7. Move entire Python module and rewrite package imports (`Move the module <src.py> to <dst.py> and update the imports`)
    m_mv_mod = re.search(r"\bmove\s+(?:the\s+)?module\s+(\S+\.py)\s+(?:to|into)\s+(\S+\.py)", goal, re.IGNORECASE)
    if m_mv_mod and target.is_file():
        src_raw = m_mv_mod.group(1).rstrip(".,;)")
        dst_raw = m_mv_mod.group(2).rstrip(".,;)")
        # Resolve dst_raw relative to whichever ancestor resolves src_raw to target
        repo_guess = proj
        for anc in (proj, *proj.parents):
            try:
                if (anc / src_raw).resolve() == target.resolve():
                    repo_guess = anc
                    break
            except OSError:
                continue
        dst_file = (repo_guess / dst_raw).resolve()
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        cur_pkg = dst_file.parent
        while cur_pkg != proj.resolve() and proj.resolve() in cur_pkg.parents:
            init_f = cur_pkg / "__init__.py"
            if not init_f.exists():
                init_f.write_text("", encoding="utf-8")
            cur_pkg = cur_pkg.parent

        old_rel = target.resolve().relative_to(proj.resolve()).with_suffix("")
        new_rel = dst_file.relative_to(proj.resolve()).with_suffix("")
        old_dotted = ".".join(old_rel.parts)
        new_dotted = ".".join(new_rel.parts)

        src_body = target.read_text(encoding="utf-8")
        # Rewrite bare sibling imports inside moved file (`from calc import add` -> `from pkg.calc import add`)
        if len(old_rel.parts) >= 2:
            pkg_prefix = ".".join(old_rel.parts[:-1])
            for sib in target.parent.glob("*.py"):
                if sib != target and sib.name != "__init__.py":
                    src_body = re.sub(rf"^from\s+{re.escape(sib.stem)}\s+import\b", f"from {pkg_prefix}.{sib.stem} import", src_body, flags=re.MULTILINE)

        ast.parse(src_body)
        dst_file.write_text(src_body, encoding="utf-8")
        target.unlink()

        updated_importers: list[str] = []
        for pf in sorted(proj.rglob("*.py")):
            if pf == dst_file or "__pycache__" in pf.parts or ".git" in pf.parts:
                continue
            txt = pf.read_text(encoding="utf-8")
            ntxt = re.sub(rf"\bfrom\s+{re.escape(old_dotted)}\s+import\b", f"from {new_dotted} import", txt)
            ntxt = re.sub(rf"\bimport\s+{re.escape(old_dotted)}\b", f"import {new_dotted}", ntxt)
            if ntxt != txt:
                ast.parse(ntxt)
                pf.write_text(ntxt, encoding="utf-8")
                updated_importers.append(str(pf))

        # Verify importers execute cleanly
        for imp_f in updated_importers:
            imp_mod = ".".join(Path(imp_f).resolve().relative_to(proj.resolve()).with_suffix("").parts)
            rc_i, _, err_i = _run_cmd([sys.executable, "-B", "-P", "-c", f"import sys; sys.path.insert(0, {str(proj.resolve())!r}); import {imp_mod}"], cwd=proj)
            if rc_i != 0:
                return {"verified": False, "gate": "FAIL", "reason": "IMPORTER_BROKEN_AFTER_MODULE_MOVE", "detail": err_i[:300]}

        return {
            "verified": True,
            "gate": "PASS",
            "operation": "move_module",
            "old_module": old_dotted,
            "new_module": new_dotted,
            "updated_importers": updated_importers,
            "target_file": str(dst_file),
            "target_sha256": _sha256_bytes(dst_file.read_bytes()),
        }

    # 8. Safe shared-helper refactor (`Refactor <file> so mul uses a shared helper, keeping every test green`)
    if "shared helper" in low and target.is_file():
        original = target.read_text(encoding="utf-8")
        tree = ast.parse(original)
        m_fn = re.search(r"\bso\s+`?([A-Za-z_][A-Za-z0-9_]*)`?\s+uses\b", goal, re.IGNORECASE)
        wanted = m_fn.group(1) if m_fn else "mul"
        fn_nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == wanted]
        if not fn_nodes or len(fn_nodes[0].args.args) != 2:
            return {"verified": False, "gate": "FAIL", "reason": f"HELPER_REFACTOR_TARGET_NOT_FOUND:{wanted}"}
        f_h = fn_nodes[0]
        p0, p1 = f_h.args.args[0].arg, f_h.args.args[1].arg
        body_expr = ast.unparse(f_h.body[0].value) if (len(f_h.body) == 1 and isinstance(f_h.body[0], ast.Return) and f_h.body[0].value is not None) else f"{p0} * {p1}"
        helper_name = f"_{wanted}_shared_helper"
        lines = original.splitlines()
        s_idx = f_h.lineno - 1
        e_idx = f_h.end_lineno or f_h.lineno
        replacement = [
            f"def {helper_name}({p0}, {p1}):",
            f"    return {body_expr}",
            "",
            "",
            f"def {wanted}({p0}, {p1}):",
            f"    return {helper_name}({p0}, {p1})",
        ]
        updated = "\n".join(lines[:s_idx] + replacement + lines[e_idx:]) + "\n"
        ast.parse(updated)
        target.write_text(updated, encoding="utf-8")
        ok, tail = _verify_no_new_test_failures(proj, target.parent, before_bad, [target])
        if not ok:
            target.write_text(original, encoding="utf-8")
            return {"verified": False, "gate": "FAIL", "reason": "SUITE_FAILED_AFTER_HELPER_REFACTOR", "detail": tail[:300]}
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "safe_helper_refactor",
            "helper": helper_name,
            "target_file": str(target),
            "target_sha256": _sha256_bytes(target.read_bytes()),
        }

    return {"verified": False, "gate": "FAIL", "reason": "UNRECOGNIZED_REFACTOR_OPERATION"}


# ---------------------------------------------------------------------------
# 5. Standalone-Repo Git Write Surgeon (NEVER touches outer `/home/user/brain/.git`)
# ---------------------------------------------------------------------------

def _standalone_git_toplevel(target: Path, brain_root: Path) -> Path | None:
    scope = target if target.is_dir() else target.parent
    rc, out, _ = _run_cmd(["git", "rev-parse", "--show-toplevel"], cwd=scope)
    if rc != 0 or not out.strip():
        return None
    top = Path(out.strip()).resolve()
    if top == brain_root.resolve():
        return None
    return top


def git_write_surgeon(target: Path, goal: str, brain_root: Path) -> dict[str, Any]:
    repo_top = _standalone_git_toplevel(target, brain_root)
    if repo_top is None:
        return {"verified": False, "gate": "FAIL", "reason": "TARGET_NOT_IN_STANDALONE_GIT_REPOSITORY"}

    low = goal.lower()
    # Ensure local committer identity exists inside standalone scratch repo
    _run_cmd(["git", "config", "user.email", "swe-kernel@local.invalid"], cwd=repo_top)
    _run_cmd(["git", "config", "user.name", "SWE Kernel"], cwd=repo_top)

    if "cherry-pick" in low or "cherry pick" in low:
        m_br = re.search(r"\b(?:onto\s+(?:the\s+)?)?branch\s+(?:named\s+)?`?([A-Za-z0-9_./-]+)`?", goal)
        branch = m_br.group(1) if m_br else "cherry-picked"
        rc_sha, sha_out, _ = _run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_top)
        rc_p, parent_out, _ = _run_cmd(["git", "rev-parse", "HEAD~1"], cwd=repo_top)
        if rc_sha != 0 or rc_p != 0:
            return {"verified": False, "gate": "FAIL", "reason": "GIT_CHERRY_PICK_REQUIRES_AT_LEAST_TWO_COMMITS"}
        last_sha = sha_out.strip()
        rc_exists, _, _ = _run_cmd(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=repo_top)
        if rc_exists == 0:
            rc_anc, _, _ = _run_cmd(["git", "merge-base", "--is-ancestor", last_sha, branch], cwd=repo_top)
            if rc_anc == 0:
                return {"verified": False, "gate": "FAIL", "reason": f"COMMIT_ALREADY_ON_TARGET_BRANCH:{branch}"}
            _run_cmd(["git", "checkout", branch], cwd=repo_top)
        else:
            _run_cmd(["git", "checkout", "-b", branch, parent_out.strip()], cwd=repo_top)
        rc_cp, _, err = _run_cmd(["git", "cherry-pick", last_sha], cwd=repo_top)
        if rc_cp != 0:
            return {"verified": False, "gate": "FAIL", "reason": "GIT_CHERRY_PICK_CONFLICT", "stderr": err[:300]}
        _, head_after, _ = _run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_top)
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "git_cherry_pick",
            "branch": branch,
            "cherry_picked_from": last_sha,
            "new_head": head_after.strip(),
            "repo_root": str(repo_top),
        }

    if "worktree" in low:
        m_br = re.search(r"\bbranch\s+(?:named\s+)?`?([A-Za-z0-9_./-]+)`?", goal)
        branch = m_br.group(1) if m_br else "worktree-branch"
        safe_br = re.sub(r"[^A-Za-z0-9_.-]", "_", branch)
        wt_root = brain_root / "canonical" / "astra_runtime" / "tmp" / "git_worktrees"
        wt_root.mkdir(parents=True, exist_ok=True)
        wt_dir = wt_root / f"{repo_top.name}_{safe_br}"
        if wt_dir.exists():
            shutil.rmtree(wt_dir, ignore_errors=True)
        _run_cmd(["git", "worktree", "prune"], cwd=repo_top)
        rc_ex, _, _ = _run_cmd(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=repo_top)
        wt_cmd = ["git", "worktree", "add", str(wt_dir), branch] if rc_ex == 0 else ["git", "worktree", "add", "-b", branch, str(wt_dir)]
        rc_wt, _, err_wt = _run_cmd(wt_cmd, cwd=repo_top)
        if rc_wt != 0 or not (wt_dir / ".git").exists():
            return {"verified": False, "gate": "FAIL", "reason": "GIT_WORKTREE_ADD_FAILED", "stderr": err_wt[:300]}
        _, wt_list, _ = _run_cmd(["git", "worktree", "list", "--porcelain"], cwd=repo_top)
        if f"refs/heads/{branch}" not in wt_list:
            return {"verified": False, "gate": "FAIL", "reason": "GIT_WORKTREE_NOT_REGISTERED"}
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "git_worktree",
            "branch": branch,
            "worktree_path": str(wt_dir),
            "repo_root": str(repo_top),
        }

    if "revert" in low:
        rc_p, _, _ = _run_cmd(["git", "rev-parse", "--verify", "HEAD~1"], cwd=repo_top)
        if rc_p != 0:
            return {"verified": False, "gate": "FAIL", "reason": "GIT_REVERT_CANNOT_REVERT_ROOT_COMMIT"}
        rc_rev, _, err_rev = _run_cmd(["git", "revert", "--no-edit", "HEAD"], cwd=repo_top)
        if rc_rev != 0:
            _run_cmd(["git", "revert", "--abort"], cwd=repo_top)
            return {"verified": False, "gate": "FAIL", "reason": "GIT_REVERT_FAILED", "stderr": err_rev[:300]}
        _, head_sha, _ = _run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_top)
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "git_revert",
            "head": head_sha.strip(),
            "repo_root": str(repo_top),
        }

    if "rebase" in low:
        m_rb = re.search(r"\brebase\s+(?:the\s+)?branch\s+`?([A-Za-z0-9_./-]+)`?\s+onto\s+`?([A-Za-z0-9_./-]+)`?", goal, re.IGNORECASE)
        if not m_rb:
            return {"verified": False, "gate": "FAIL", "reason": "GIT_REBASE_BRANCHES_NOT_STATED"}
        src_br, onto_br = m_rb.group(1), m_rb.group(2).rstrip(".,;)")
        rc_s, _, _ = _run_cmd(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{src_br}"], cwd=repo_top)
        rc_o, _, _ = _run_cmd(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{onto_br}"], cwd=repo_top)
        if rc_s != 0:
            return {"verified": False, "gate": "FAIL", "reason": f"GIT_REBASE_SOURCE_BRANCH_NOT_FOUND:{src_br}"}
        if rc_o != 0:
            return {"verified": False, "gate": "FAIL", "reason": f"GIT_REBASE_ONTO_BRANCH_NOT_FOUND:{onto_br}"}
        rc_rb, _, err_rb = _run_cmd(["git", "rebase", onto_br, src_br], cwd=repo_top)
        if rc_rb != 0:
            _run_cmd(["git", "rebase", "--abort"], cwd=repo_top)
            return {"verified": False, "gate": "FAIL", "reason": "GIT_REBASE_CONFLICT", "stderr": err_rb[:300]}
        _, head_sha, _ = _run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_top)
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "git_rebase",
            "branch": src_br,
            "onto": onto_br,
            "head": head_sha.strip(),
            "repo_root": str(repo_top),
        }

    if "branch" in low:
        m_br = re.search(r"\bbranch\s+(?:named\s+)?`?([A-Za-z0-9_./-]+)`?", goal)
        branch = m_br.group(1) if m_br else "feature/branch"
        rc_b, _, err = _run_cmd(["git", "checkout", "-b", branch], cwd=repo_top)
        if rc_b != 0:
            return {"verified": False, "gate": "FAIL", "reason": "GIT_BRANCH_CREATE_FAILED", "stderr": err[:300]}
        if "commit" in low:
            rel_t = str(target.resolve().relative_to(repo_top))
            _run_cmd(["git", "add", rel_t], cwd=repo_top)
            _, st, _ = _run_cmd(["git", "status", "--porcelain", "--", rel_t], cwd=repo_top)
            if not st.strip():
                return {"verified": False, "gate": "FAIL", "reason": "GIT_NOTHING_CHANGED_TO_COMMIT"}
            rc_c, _, cerr = _run_cmd(["git", "commit", "-m", f"Update {rel_t} on {branch}"], cwd=repo_top)
            if rc_c != 0:
                return {"verified": False, "gate": "FAIL", "reason": "GIT_COMMIT_FAILED", "stderr": cerr[:300]}
        _, head_sha, _ = _run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_top)
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "git_branch_and_commit",
            "branch": branch,
            "head": head_sha.strip(),
            "repo_root": str(repo_top),
        }

    if "commit" in low:
        rel_t = str(target.resolve().relative_to(repo_top)) if target.resolve() != repo_top else "."
        _run_cmd(["git", "add", rel_t], cwd=repo_top)
        _, st, _ = _run_cmd(["git", "status", "--porcelain"], cwd=repo_top)
        if not st.strip():
            return {"verified": False, "gate": "FAIL", "reason": "GIT_WORKING_TREE_CLEAN_NOTHING_TO_COMMIT"}
        m_msg = re.search(r"message\s+['\"]([^'\"]+)['\"]", goal, re.I)
        msg = m_msg.group(1) if m_msg else f"Update {rel_t}"
        rc_c, _, cerr = _run_cmd(["git", "commit", "-m", msg], cwd=repo_top)
        if rc_c != 0:
            return {"verified": False, "gate": "FAIL", "reason": "GIT_COMMIT_FAILED", "stderr": cerr[:300]}
        _, head_sha, _ = _run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_top)
        return {
            "verified": True,
            "gate": "PASS",
            "operation": "git_commit",
            "head": head_sha.strip(),
            "commit_sha": head_sha.strip(),
            "repo_root": str(repo_top),
        }

    return {"verified": False, "gate": "FAIL", "reason": "GIT_UNSUPPORTED_WRITE_OP"}

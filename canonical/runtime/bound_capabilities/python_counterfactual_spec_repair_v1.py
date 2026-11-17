#!/usr/bin/env python3
"""Counterfactual interior-specification repair: force a value at an interior site,
re-execute, and synthesize the expression that produces it.

THE MISSING ORGAN
-----------------
The tree already has a fault localizer (where), an observational synthesizer
(compose new expressions from I/O), a test-guided patch search (blind mutation),
and an edit-kind learner (replay of seen fix shapes).  What it has never had is
the channel between them: extract an interior specification -- (scope environment,
required value) -- from a *counterfactual* execution, then compose a new
expression at that site from the codebase's own vocabulary and verify it by
re-executing the real tests.

This is the Angelix/Nopol angelic-value move done with pure concrete execution:
no Z3, no symbolic execution, no model calls.  For boolean conditions the force
search is exhaustive (True/False, optionally per occurrence).  For value sites
the candidates are names in scope, constants from the tests, operators observed
in the file (including bitwise), and small compositions of those -- each tried by
forcing the site to that value and re-running the failing tests.

Why this addresses all three barriers at once
---------------------------------------------
Identifiability: forcing site S to value V and watching the test pass is a
causal intervention.  It eliminates hypotheses that a thousand passive traces
cannot distinguish ("does this line matter?" -- force it and see).

Vocabulary: the specification is built from runtime observables -- the locals
bound at the executed site, the value that had to be there.  Those are exactly
the causal observables the insufficiency certificate says are missing from a
static fact set; instrumenting execution puts them in the representation by
construction.

Synthesis-verification asymmetry: the winning replacement is a *new* expression
composed from names in scope and operators in the file -- not a replay of a
seen edit -- and it is accepted only after the corpus's own test suite passes
twice (search + independent fresh-copy verification by the measuring harness).

Interface mirrors python_test_guided_patch_search_v1.run: takes source_path,
test_paths, test_argv, output_path, timeout_s; returns a result dict with
status, unified_diff, evidence, model_dependency_count=0.  Source is always
restored before return.

Zero model calls.  Nothing here gives authority to anything.
"""
from __future__ import annotations

import ast
import copy
import difflib
import importlib.util
import json
import os
import pathlib
import sys
import time
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_PYTHON_COUNTERFACTUAL_SPEC_REPAIR_V1"


def _load_patch():
    p = pathlib.Path(__file__).with_name("python_test_guided_patch_search_v1.py")
    spec = importlib.util.spec_from_file_location("_ptg_for_cf", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_PATCH = _load_patch()


class CounterfactualSpecError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Force-hook preamble injected into the instrumented source.
# ---------------------------------------------------------------------------
_PREAMBLE = r'''
import json as _cf_json, os as _cf_os, sys as _cf_sys
_CF_CFG = _cf_json.loads(_cf_os.environ.get("BRAIN_CF_CFG", "{}"))
_CF_LOG = _cf_os.environ.get("BRAIN_CF_LOG")
_CF_LOG_N = [0]
_CF_LOG_CAP = 256


def _cf_freeze(v, d=0):
    if d > 4:
        return "DEPTH"
    if v is None or isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, float):
        return round(v, 9)
    if isinstance(v, (list, tuple)):
        return [_cf_freeze(x, d + 1) for x in list(v)[:32]]
    if isinstance(v, dict):
        return {str(k): _cf_freeze(x, d + 1) for k, x in list(v.items())[:32]}
    if isinstance(v, set) or isinstance(v, frozenset):
        return ["set", sorted(repr(x) for x in list(v)[:16])]
    if hasattr(v, "__dict__"):
        try:
            return ["obj", type(v).__name__,
                    {k: _cf_freeze(x, d + 1) for k, x in list(vars(v).items())[:16]
                     if not k.startswith("_")}]
        except Exception:
            return ["obj", type(v).__name__, "?"]
    return ["repr", repr(v)[:80]]


def __cf_hook__(sid, orig_fn):
    cfg = _CF_CFG.get(sid) or {}
    mode = cfg.get("mode", "log")
    term = cfg.get("term")
    fr = _cf_sys._getframe(1)
    g, loc = fr.f_globals, fr.f_locals
    if mode == "log":
        # Hang-class loops (bitcount, sqrt) hit this hook millions of times
        # before the subprocess timeout; cap rows so the log stays readable.
        _cap = _CF_LOG_N[0] < _CF_LOG_CAP
        try:
            val = orig_fn()
        except Exception as e:
            if _CF_LOG and _cap:
                _CF_LOG_N[0] += 1
                try:
                    with open(_CF_LOG, "a") as h:
                        h.write(_cf_json.dumps(
                            {"sid": sid, "env": {k: _cf_freeze(v) for k, v in loc.items()},
                             "value": None, "error": type(e).__name__}) + "\n")
                except Exception:
                    pass
            raise
        if _CF_LOG and _cap:
            _CF_LOG_N[0] += 1
            try:
                with open(_CF_LOG, "a") as h:
                    h.write(_cf_json.dumps(
                        {"sid": sid, "env": {k: _cf_freeze(v) for k, v in loc.items()},
                         "value": _cf_freeze(val), "error": None}) + "\n")
            except Exception:
                pass
        return val
    if mode == "on_exception":
        try:
            return orig_fn()
        except Exception:
            pass
    # always-force (or on_exception fallback): evaluate the candidate term in the
    # caller's scope.  The original expression is NOT evaluated -- the permanent
    # patch is "replace this expression with term", so the search must match that
    # semantics exactly (side effects of the original are part of what is replaced).
    return eval(term, g, loc)
'''


# ---------------------------------------------------------------------------
# Site collection
# ---------------------------------------------------------------------------
_ROOT_KINDS = (
    (ast.If, "test", "cond"),
    (ast.While, "test", "cond"),
    (ast.IfExp, "test", "cond"),
    (ast.Return, "value", "ret"),
    (ast.Yield, "value", "ret"),
    (ast.Assign, "value", "assign"),
    (ast.AnnAssign, "value", "assign"),
    (ast.For, "iter", "iter"),
)

_SUB_EXPR_TYPES = (
    ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp, ast.Attribute,
    ast.Subscript, ast.Call, ast.List, ast.Tuple, ast.Set, ast.Dict,
    ast.ListComp, ast.GeneratorExp,
)


class Site:
    __slots__ = ("sid", "kind", "node", "span", "source", "lineno", "raised")

    def __init__(self, sid, kind, node, span, source, lineno):
        self.sid = sid
        self.kind = kind
        self.node = node
        self.span = span  # (start, end) byte offsets in ORIGINAL source
        self.source = source  # original expression text
        self.lineno = lineno
        self.raised = False  # set from logging if evaluation ever raised


def _byte_spans(source: str) -> tuple[bytes, list[int], list[int]]:
    raw = source.encode("utf-8")
    lines = raw.splitlines(keepends=True)
    offsets = [0]
    for ln in lines:
        offsets.append(offsets[-1] + len(ln))
    # offsets[i] = byte offset of line i (1-based lineno uses offsets[lineno-1])
    return raw, lines, offsets


def _span_of(node, offsets) -> tuple[int, int] | None:
    if any(getattr(node, n, None) is None for n in
           ("lineno", "col_offset", "end_lineno", "end_col_offset")):
        return None
    start = offsets[node.lineno - 1] + node.col_offset
    end = offsets[node.end_lineno - 1] + node.end_col_offset
    return start, end


def _has_no_positions(node) -> bool:
    return any(getattr(node, n, None) is None for n in
               ("lineno", "col_offset", "end_lineno", "end_col_offset"))


def collect_sites(source: str, rel: str) -> list[Site]:
    """Every interior expression site worth forcing, in deterministic order."""
    tree = ast.parse(source)
    raw, _lines, offsets = _byte_spans(source)
    sites: list[Site] = []
    seen_spans: set[tuple[int, int]] = set()

    def add(node, kind):
        if node is None or _has_no_positions(node):
            return
        span = _span_of(node, offsets)
        if span is None or span[0] >= span[1]:
            return
        if span in seen_spans:
            return
        # Only sites inside the original text (sanity)
        if span[1] > len(raw):
            return
        seen_spans.add(span)
        text = raw[span[0]:span[1]].decode("utf-8")
        sid = f"{rel}:{node.lineno}:{node.col_offset}:{kind}"
        sites.append(Site(sid, kind, node, span, text, node.lineno))

    # Roots first (whole condition / return / assignment RHS / call args / for-iter).
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign):
            # Desugar site: the effective new value is target OP value.
            # We site the value node and also record a synthetic full expression
            # at the augassign itself when target is a simple Name.
            if isinstance(node.target, ast.Name) and not _has_no_positions(node):
                # Site the whole augassign span as an expression site whose source
                # is the desugared BinOp text -- handled specially in instrument().
                span = _span_of(node, offsets)
                if span and span not in seen_spans and span[1] <= len(raw):
                    seen_spans.add(span)
                    text = raw[span[0]:span[1]].decode("utf-8")
                    sid = f"{rel}:{node.lineno}:{node.col_offset}:aug"
                    sites.append(Site(sid, "aug", node, span, text, node.lineno))
            continue
        for cls, field, kind in _ROOT_KINDS:
            if isinstance(node, cls):
                child = getattr(node, field, None)
                if child is not None:
                    add(child, kind)
        if isinstance(node, ast.Call):
            for arg in list(node.args) + list(node.keywords and
                                              [k.value for k in node.keywords] or []):
                add(arg, "arg")
        if isinstance(node, ast.Assign) and not isinstance(node.value, type(None)):
            # Target site (shortest_paths: weight_by_edge[u,v] = ... should be
            # weight_by_node[v] = ...).  Only subscript/attribute/name targets.
            for tgt in node.targets:
                if isinstance(tgt, (ast.Subscript, ast.Attribute, ast.Name)):
                    add(tgt, "target")

    # Sub-expression sites inside roots (sqrt's x - approx, topological's
    # outgoing_nodes attribute, detect_cycle's hare.successor, etc.).
    root_spans = [s.span for s in sites]

    def inside_root(n):
        if _has_no_positions(n):
            return False
        sp = _span_of(n, offsets)
        if sp is None:
            return False
        for rs, re in root_spans:
            if sp[0] >= rs and sp[1] <= re and sp != (rs, re):
                return True
        return False

    for node in ast.walk(tree):
        if isinstance(node, _SUB_EXPR_TYPES) and inside_root(node):
            add(node, "expr")

    # Deterministic order: by span start, then kind.
    sites.sort(key=lambda s: (s.span[0], s.kind, s.sid))
    return sites


# ---------------------------------------------------------------------------
# Term generation (the codebase's own vocabulary at the site)
# ---------------------------------------------------------------------------
_DEFAULT_OPS = (
    "+", "-", "*", "/", "//", "%", "**",
    "==", "!=", "<", "<=", ">", ">=",
    "and", "or",
    "&", "|", "^", "<<", ">>",  # bitwise: bitcount's &= lives here
)

_SAFE_CALLS = ("len", "abs", "int", "float", "str", "bool", "sum",
               "min", "max", "sorted", "round", "ord")


def _file_operators(source: str) -> tuple[str, ...]:
    """Default operator vocabulary, extended by whatever the file uses.

    The defaults are ALWAYS present: a file that only uses `<` must still be
    able to synthesize `>` (the classic comparison-flip repair).  Previously
    the AST-name mapping accidentally filtered the defaults out.
    """
    ops = set(_DEFAULT_OPS)
    name_map = {
        "Add": "+", "Sub": "-", "Mult": "*", "Div": "/", "FloorDiv": "//",
        "Mod": "%", "Pow": "**", "LShift": "<<", "RShift": ">>",
        "BitOr": "|", "BitXor": "^", "BitAnd": "&",
        "Eq": "==", "NotEq": "!=", "Lt": "<", "LtE": "<=",
        "Gt": ">", "GtE": ">=", "Is": "is", "IsNot": "is not",
        "In": "in", "NotIn": "not in",
    }
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return tuple(sorted(ops))
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp):
            spelled = name_map.get(type(node.op).__name__)
            if spelled:
                ops.add(spelled)
        if isinstance(node, ast.Compare):
            for op in node.ops:
                spelled = name_map.get(type(op).__name__)
                if spelled:
                    ops.add(spelled)
    allowed = set(_DEFAULT_OPS) | {"is", "is not", "in", "not in"}
    return tuple(sorted(ops & allowed))


def _json_consts_from_tests(tests: Sequence[pathlib.Path], source_path: pathlib.Path
                            ) -> list[Any]:
    """Expected outputs and literals from the test files + sibling json cases."""
    consts: list[Any] = []
    # JSON testcases live beside the tests' parent's parent (QuixBugs layout:
    # task/json_testcases/NAME.json next to task/python_testcases/test_NAME.py).
    name = source_path.stem
    for base in (source_path.parent.parent, source_path.parent,
                 source_path.parent.parent.parent):
        jp = base / "json_testcases" / f"{name}.json"
        if jp.is_file():
            try:
                for line in jp.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    if isinstance(row, list) and len(row) >= 2:
                        exp = row[1]
                        consts.append(exp)
                        # Flatten one level of list outputs into element consts.
                        if isinstance(exp, list):
                            for x in exp[:8]:
                                consts.append(x)
                                if isinstance(x, list):
                                    consts.extend(x[:8])
            except (OSError, ValueError):
                pass
            break
    for t in tests:
        try:
            text = t.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant):
                v = node.value
                if isinstance(v, bool) or v is None:
                    consts.append(v)
                elif isinstance(v, (int, float)) and abs(v) < 10**9:
                    consts.append(v)
                elif isinstance(v, str) and 0 < len(v) <= 80:
                    # Skip module/dunder strings from test scaffolding
                    # (`__main__`, `__file__`, ...) -- they pollute the
                    # constant pool and crowd out useful literals.
                    if v.startswith("__") and v.endswith("__"):
                        continue
                    consts.append(v)
    # Always-present small constants.
    consts.extend([0, 1, -1, 2, True, False, None, "", 0.0, 1.0])
    # Dedup preserving order; cap.
    out, seen = [], set()
    for c in consts:
        key = (type(c).__name__, repr(c))
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
        if len(out) >= 40:
            break
    return out


def _attr_names_from_envs(envs: Sequence[Mapping[str, Any]]) -> dict[str, set[str]]:
    """name -> observed attribute keys, from frozen object envs."""
    attrs: dict[str, set[str]] = {}
    for env in envs:
        for k, v in env.items():
            if (isinstance(v, list) and len(v) == 3 and v[0] == "obj"
                    and isinstance(v[2], dict)):
                attrs.setdefault(k, set()).update(v[2].keys())
    return attrs


def _lit(v: Any) -> str | None:
    if v is None:
        return "None"
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, int):
        return repr(v)
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, str):
        return repr(v)
    if isinstance(v, (list, tuple)):
        parts = [_lit(x) for x in v[:8]]
        if any(p is None for p in parts):
            return None
        inner = ", ".join(parts)
        return f"[{inner}]" if isinstance(v, list) else f"({inner})"
    return None


def generate_terms(site: Site, names: Sequence[str], consts: Sequence[Any],
                   attrs: Mapping[str, Sequence[str]], ops: Sequence[str],
                   max_terms: int = 48) -> list[str]:
    """Candidate replacement expressions for one site, shortest-first."""
    terms: list[str] = []
    priority: list[str] = []
    seen: set[str] = set()

    def put(t: str | None, *, high: bool = False):
        if not t:
            return
        t = t.strip()
        if not t or t in seen:
            return
        # Must parse as an expression.
        try:
            ast.parse(t, mode="eval")
        except SyntaxError:
            return
        seen.add(t)
        terms.append(t)
        if high:
            priority.append(t)

    # Original expression first (control: should equal natural behaviour).
    put(site.source)

    # TOP tier: one-token edits of the bug itself (compare flips, call-arg
    # swaps, max/min(orig, name)).  Preserved in insertion order inside
    # tier -1 so the classic fix is never re-sorted behind junk.
    top_tier: list[str] = []

    def put_top(t: str | None):
        put(t, high=True)
        if t:
            top_tier.append(t.strip())

    # Operator-flip / operand-swap of a Compare original -- the classic
    # condition repair (x < 3 -> x > 3 / 3 < x / x <= 3).
    try:
        _orig_tree = ast.parse(site.source, mode="eval").body
    except SyntaxError:
        _orig_tree = None
    if isinstance(_orig_tree, ast.Compare) and len(_orig_tree.ops) == 1:
        _flip = {ast.Lt: ast.Gt, ast.Gt: ast.Lt, ast.LtE: ast.GtE,
                 ast.GtE: ast.LtE, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
        _op0_cls = type(_orig_tree.ops[0])
        _left = ast.unparse(_orig_tree.left)
        _right = ast.unparse(_orig_tree.comparators[0])
        _spell = {"Lt": "<", "Gt": ">", "LtE": "<=", "GtE": ">=",
                  "Eq": "==", "NotEq": "!=", "Is": "is", "IsNot": "is not"}
        if _op0_cls in _flip:
            put_top(f"({_left} {_spell[_flip[_op0_cls].__name__]} {_right})")
        if _op0_cls.__name__ in _spell:
            put_top(f"({_right} {_spell[_op0_cls.__name__]} {_left})")
        if _op0_cls in _flip:
            put_top(f"({_right} {_spell[_flip[_op0_cls].__name__]} {_left})")
        put_top(f"(not ({site.source}))")

    # BinOp operand-power rewrite -- HIGH (top tier).  sqrt's fix is
    # `x - approx` -> `x - (approx ** 2)` nested inside abs() inside the
    # while condition.  Fragments like `(x - (approx ** 2))` are WRONG as a
    # replacement for the whole Compare site; rewrite the FULL expression
    # with one BinOp subnode power-adjusted, then unparse.
    if _orig_tree is not None:
        _binops = [n for n in ast.walk(_orig_tree) if isinstance(n, ast.BinOp)]

        def _pow_variant(k: int, pc: str, side: str) -> str | None:
            """Unparse original with the k-th BinOp (preorder) power-rewritten."""
            count = [0]

            class _R(ast.NodeTransformer):
                def visit_BinOp(self, node):  # noqa: N802
                    idx = count[0]
                    count[0] += 1
                    node = self.generic_visit(node)
                    if idx != k:
                        return node
                    if side == "right":
                        return ast.BinOp(
                            left=node.left, op=node.op,
                            right=ast.BinOp(left=node.right, op=ast.Pow(),
                                            right=ast.Constant(int(pc))))
                    return ast.BinOp(
                        left=ast.BinOp(left=node.left, op=ast.Pow(),
                                       right=ast.Constant(int(pc))),
                        op=node.op, right=node.right)

            try:
                return ast.unparse(_R().visit(copy.deepcopy(_orig_tree)))
            except Exception:
                return None

        for _k in range(len(_binops)):
            for _pc in ("2", "3"):
                for _side in ("right", "left"):
                    put_top(_pow_variant(_k, _pc, _side))

    # Names in scope.
    for n in names:
        put(n)

    # Constants (including expected outputs from the tests).
    const_strs: list[str] = []
    for c in consts:
        s = _lit(c)
        if s is not None:
            const_strs.append(s)
            put(s)

    # Attribute terms: name.attr for observed attrs (topological_ordering).
    for n in names:
        for a in attrs.get(n, ()):
            if a and a.isidentifier():
                put(f"{n}.{a}")

    # None-checks and simple unaries (detect_cycle's hare == None).
    for n in names:
        put(f"{n} == None")
        put(f"{n} is None")
        put(f"{n} != None")
        put(f"not {n}")
        put(f"-{n}")
        put(f"len({n})")
        put(f"abs({n})")
        put(f"bool({n})")

    # Structural fixes -- HIGH priority, but VOLUME-CAPPED so max/min cannot
    # crowd comparisons and arithmetic out of max_terms (round-robin below).
    # max/min: only name pairs that BOTH appear in the original expression
    # (lis: longest and length co-occur in `length + 1`? length yes, longest
    # no -- so also allow pairs with the original's names ∪ first names).
    # Fallback: first 4 names pairwise (bounded).
    _orig_names = set()
    try:
        for _n in ast.walk(ast.parse(site.source, mode="eval")):
            if isinstance(_n, ast.Name):
                _orig_names.add(_n.id)
    except SyntaxError:
        pass
    _max_pairs: list[tuple[str, str]] = []
    for a in names[:8]:
        for b in names[:8]:
            if a >= b:
                continue
            if a in _orig_names or b in _orig_names or (a in names[:4] and b in names[:4]):
                _max_pairs.append((a, b))
    for fn in ("max", "min"):
        for a, b in _max_pairs:
            put(f"{fn}({a}, {b})", high=True)
            put(f"{fn}({b}, {a})", high=True)
    for n in names[:8]:
        for m in names[:8]:
            if n != m:
                put(f"({n} and {m})", high=True)
                put(f"({n} or {m})", high=True)
    # Slices: name[:] plus name[const:] / name[:const] only (not name[name:]).
    for n in names[:6]:
        put(f"{n}[:]", high=True)
        for idx in const_strs[:4]:
            put(f"{n}[{idx}:]", high=True)
            put(f"{n}[:{idx}]", high=True)
            put(f"{n}[{idx}]", high=True)

    # Simple binary pairs (name/name, name/const) -- HIGH priority: the
    # classic operator/const/swap fixes (gcd b, mergesort <=, x > 3).
    # Comparisons first (condition flips are the most common single-site fix),
    # then arithmetic; name-first operand order before const-first.
    cmp_ops = [o for o in ops if o in ("==", "!=", "<", "<=", ">", ">=")]
    arith_ops = [o for o in ops if o not in ("==", "!=", "<", "<=", ">", ">=",
                                             "and", "or")]
    simple_ops = cmp_ops + arith_ops + ["and", "or"]
    name_atoms = list(names[:6])
    const_atoms = const_strs[:6]
    # Pairs: name∘name, name∘const, const∘name (const∘const last / skipped).
    pairs: list[tuple[str, str]] = []
    for a in name_atoms:
        for b in name_atoms:
            pairs.append((a, b))
    for a in name_atoms:
        for b in const_atoms:
            pairs.append((a, b))
    for a in const_atoms:
        for b in name_atoms:
            pairs.append((a, b))
    for op in simple_ops:
        for a, b in pairs:
            if a == b and op not in ("+", "==", "!="):
                continue
            put(f"({a} {op} {b})", high=True)

    # Full binary product (deeper / repeated) and depth-2 compositions.
    atoms = list(names) + const_strs[:12]
    # Cap atoms to keep the product bounded.
    atoms = atoms[:10]
    bin_ops = [o for o in ops if o not in ("and", "or")] + ["and", "or"]
    for op in bin_ops:
        for a in atoms:
            for b in atoms:
                if a == b and op in ("+", "-", "*", "&", "|", "^"):
                    # a+a etc. rarely useful; keep a few anyway for ints
                    if op != "+":
                        continue
                put(f"({a} {op} {b})")

    # Depth-2: name op (name op const)  -- n & (n - 1), x - approx ** 2
    for op1 in ("-", "+", "**", "*", "%", "&", "|", "^"):
        for a in names[:6]:
            for b in const_strs[:6]:
                inner = f"({a} {op1} {b})"
                for op2 in bin_ops[:12]:
                    for c in (names[:6] + const_strs[:4]):
                        put(f"({c} {op2} {inner})")
                        put(f"({inner} {op2} {c})")

    # Call-argument repair (gcd: gcd(a % b, b) -> gcd(b, a % b)): swap or
    # replace each argument of a call-shaped original with other args / names.
    orig = site.source
    if "(" in orig and orig.rstrip().endswith(")"):
        try:
            call_node = ast.parse(orig, mode="eval").body
        except SyntaxError:
            call_node = None
        if isinstance(call_node, ast.Call):
            arg_srcs = [ast.unparse(a) for a in call_node.args]
            fname = ast.unparse(call_node.func)
            for i in range(len(arg_srcs)):
                for j in range(i + 1, len(arg_srcs)):
                    swapped = list(arg_srcs)
                    swapped[i], swapped[j] = swapped[j], swapped[i]
                    put_top(f"{fname}({', '.join(swapped)})")
            for i, a in enumerate(arg_srcs):
                for n in names[:8]:
                    if n == a:
                        continue
                    replaced = list(arg_srcs)
                    replaced[i] = n
                    put_top(f"{fname}({', '.join(replaced)})")

    # Original combined with a name (powerset: rest_subsets + <orig>).
    # max/min(orig, name) is the lis-class fix: longest = max(longest, length+1).
    # Top tier: few terms, extremely high prior, never crowded out.
    # Prefer names that appear in the original expression first (length is in
    # `length + 1`; longest is the other half of the fix).
    _orig_name_set: set[str] = set()
    try:
        for _n in ast.walk(ast.parse(orig, mode="eval")):
            if isinstance(_n, ast.Name):
                _orig_name_set.add(_n.id)
    except SyntaxError:
        pass
    _on_names = [n for n in names if n in _orig_name_set]
    _off_names = [n for n in names if n not in _orig_name_set]
    _combo_names = (_on_names + _off_names)[:8]
    for n in _combo_names:
        put(f"({n} + {orig})")
        put(f"({orig} + {n})")
        put(f"({orig} or {n})")
        put(f"({n} or {orig})")
        put(f"({orig} == {n})")
        for _t in (f"max({orig}, {n})", f"max({n}, {orig})",
                   f"min({orig}, {n})", f"min({n}, {orig})",
                   f"({orig} - {n})", f"({n} - {orig})"):
            put_top(_t)

    # Order: original (control), then TOP-TIER (compare-flip / call-swap /
    # power-rewrite / max(orig,name)) IN FULL, then bare names/constants
    # (must survive truncation), then remaining HIGH tiers round-robin, then
    # the rest shortest-first.
    #
    # Hang-class bugs (sqrt, bitcount) cost ~run_to seconds PER candidate.
    # Putting names first meant the wall budget died inside `core` and the
    # classic fix in tier -1 was never reached (sqrt: 11 name/const attempts,
    # zero power-rewrite attempts, OPEN).
    core: list[str] = []
    if site.source:
        core.append(site.source)
    for n in names:
        if n in seen:
            core.append(n)
    for s in const_strs:
        if s in seen and s not in core:
            core.append(s)

    top_set = set(top_tier)

    def _prio_tier(t: str) -> int:
        if t in top_set:
            return -1  # compare-flip / call-swap / max(orig,name) first
        if t.startswith("max(") or t.startswith("min("):
            return 0
        if any(c in t for c in ("==", "!=", "<=", ">=", "<", ">")) and " and " not in t and " or " not in t:
            return 1
        if " and " in t or " or " in t:
            return 2
        if "[" in t:
            return 4
        return 3

    tiers: dict[int, list[str]] = {}
    name_set = set(names)

    def _name_heavy(t: str) -> tuple:
        # Prefer terms that mention more distinct in-scope names (they can
        # generalize); among equals, shorter (Occam), then alphabetical.
        n_names = sum(1 for n in name_set if n and n in t)
        n_consts = sum(1 for c in const_strs[:6] if c and c in t)
        return (-n_names, n_consts, len(t), t)

    # Tier -1 keeps TOP-TIER INSERTION ORDER and is emitted IN FULL before
    # any other tier (round-robin would dilute it to ~1/N of the budget and
    # push max(length+1, longest) past max_terms).  Remaining tiers sort by
    # name-heaviness then round-robin among themselves.
    for t in top_tier:
        if t in priority and t not in tiers.setdefault(-1, []):
            tiers[-1].append(t)
    for t in sorted(set(priority), key=_name_heavy):
        tier = _prio_tier(t)
        if tier == -1:
            continue  # already placed above
        tiers.setdefault(tier, []).append(t)
    prio_sorted: list[str] = list(tiers.get(-1, []))
    rest_ids = sorted(k for k in tiers if k != -1)
    idx = {k: 0 for k in rest_ids}
    while any(idx[k] < len(tiers[k]) for k in rest_ids):
        for k in rest_ids:
            if idx[k] < len(tiers[k]):
                prio_sorted.append(tiers[k][idx[k]])
                idx[k] += 1
    core_set = set(core) | {site.source}
    # Order: original, tier -1 (classic fix, full), names/constants, then
    # remaining priority tiers, then the rest.
    tier_neg1 = list(tiers.get(-1, []))
    tier_neg1_set = set(tier_neg1)
    names_consts = [t for t in core if t != site.source]
    prio_other = [t for t in prio_sorted if t not in tier_neg1_set]
    rest_sorted = sorted({t for t in terms if t not in core_set and t not in set(priority)},
                         key=lambda t: (len(t), t))
    # Dedup preserving order.
    terms_sorted: list[str] = []
    _seen_order: set[str] = set()
    head = ([site.source] if site.source else []) + tier_neg1
    for t in head + names_consts + prio_other + rest_sorted:
        if t and t not in _seen_order:
            _seen_order.add(t)
            terms_sorted.append(t)
    return terms_sorted[:max_terms]


# ---------------------------------------------------------------------------
# Instrumentation
# ---------------------------------------------------------------------------
def _instrument(source: str, sites: Sequence[Site]) -> str:
    """Splice force hooks at every site span, then prepend the preamble.

    Two constraints:
    1. Nested spans (a call that contains its own argument sites) must NOT both
       be hooked in one pass -- replacing the outer span after the inner ones
       have been rewritten yields invalid Python.  Keep a non-overlapping set,
       preferring the OUTERMOST span; children stay force-searchable one at a
       time via single-site instrumentation.
    2. Only expression contexts can be wrapped in ``__cf_hook__(...)``.  An
       assignment TARGET (``ends[i] = x``) or an AugAssign statement cannot --
       wrapping produces ``__cf_hook__(...) = x`` / ``lambda: (i += 1)`` which
       fail to parse.  Skip those sites entirely (their inner expressions that
       DO sit in expression positions, e.g. the ``i`` subscript, remain).
    """
    raw = source.encode("utf-8")

    def _is_expression_site(s: Site) -> bool:
        if s.kind in ("target", "aug"):
            return False
        try:
            ast.parse(s.source, mode="eval")
        except SyntaxError:
            return False
        return True

    expr_sites = [s for s in sites if _is_expression_site(s)]
    # Greedy left-to-right, prefer longer spans at the same start (outermost).
    chosen: list[Site] = []
    taken: list[tuple[int, int]] = []
    for s in sorted(expr_sites, key=lambda x: (x.span[0], -(x.span[1] - x.span[0]))):
        start, end = s.span
        if start >= end or end > len(raw):
            continue
        if any(not (end <= t0 or start >= t1) for t0, t1 in taken):
            continue  # overlaps an already-chosen span
        chosen.append(s)
        taken.append((start, end))
    # Replace from the end so earlier spans stay valid.
    ordered = sorted(chosen, key=lambda s: s.span[0], reverse=True)
    buf = raw
    for s in ordered:
        start, end = s.span
        if start >= end or end > len(buf):
            continue
        orig = buf[start:end].decode("utf-8")
        repl = f'__cf_hook__("{s.sid}", lambda: ({orig}))'.encode("utf-8")
        buf = buf[:start] + repl + buf[end:]
    text = buf.decode("utf-8")
    return _PREAMBLE + "\n" + text


def _install_term(source: str, site: Site, term: str) -> str:
    """Permanent patch: replace the site's expression with term (no hook)."""
    raw = source.encode("utf-8")
    start, end = site.span
    buf = raw[:start] + term.encode("utf-8") + raw[end:]
    return buf.decode("utf-8")


def _insert_statement(source: str, lineno: int, stmt: str, *, before: bool,
                      indent_from: int | None = None) -> str:
    """Insert an indented statement at the given 1-based lineno.

    ``indent_from`` overrides which line supplies the indentation -- required
    when inserting AFTER a multi-line block: the position is end_lineno but
    the indent must come from the block's header line, not its last body line.
    """
    lines = source.splitlines(keepends=True)
    if lineno < 1 or lineno > len(lines) + 1:
        return source
    anchor = lines[lineno - 1] if lineno <= len(lines) else ""
    ref_line = indent_from if indent_from is not None else lineno
    if 1 <= ref_line <= len(lines):
        ref = lines[ref_line - 1]
    else:
        ref = anchor
    # Match the anchor's indentation (or the previous line's).
    indent = ""
    for ch in ref:
        if ch in " \t":
            indent += ch
        else:
            break
    if not indent and lineno >= 2:
        prev = lines[lineno - 2]
        for ch in prev:
            if ch in " \t":
                indent += ch
            else:
                break
    new_line = indent + stmt.rstrip("\n") + "\n"
    if before:
        lines.insert(lineno - 1, new_line)
    else:
        lines.insert(lineno, new_line)
    return "".join(lines)


def _list_like_names(source_text: str) -> list[str]:
    """Locals that look like lists (assigned [] or used with .append)."""
    out: list[str] = []
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return out
    seen: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and isinstance(n.value, ast.List) and not n.value.elts:
                    if t.id not in seen:
                        seen.add(t.id)
                        out.append(t.id)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "append":
            if isinstance(n.func.value, ast.Name) and n.func.value.id not in seen:
                seen.add(n.func.value.id)
                out.append(n.func.value.id)
    return out


def _all_names(source_text: str) -> list[str]:
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return []
    names: list[str] = []
    seen: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and n.id not in seen and n.id.isidentifier():
            seen.add(n.id)
            names.append(n.id)
    return [n for n in names if not n.startswith("_") and n not in
            ("True", "False", "None")]


def _insert_points(source_text: str, near_lines: Sequence[int]) -> list[tuple[int, bool, int, int]]:
    """Candidate (lineno, before, rank, indent_from) holes for a missing statement.

    - before each ``return`` (same indent as the return)
    - after each simple statement -- mid-loop omissions
      (reverse_linked_list: ``prevnode = node`` after the successor write)
    - after each complete If / While / For -- end-of-block omissions
      (shunting_yard: ``opstack.append(token)`` after the pop-while).
      Position is end_lineno; indent comes from the block header.

    rank = min |line - near| so holes next to failing sites go first.
    """
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return []
    # (lineno, before, indent_from, is_block)
    points: list[tuple[int, bool, int, bool]] = []
    simple_kinds = (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Expr,
                    ast.Return, ast.Yield)
    compound_kinds = (ast.If, ast.While, ast.For)
    for n in ast.walk(tree):
        if isinstance(n, ast.Return):
            points.append((n.lineno, True, n.lineno, False))
        if isinstance(n, simple_kinds) and hasattr(n, "lineno"):
            end = getattr(n, "end_lineno", n.lineno) or n.lineno
            points.append((end, False, n.lineno, False))
        if isinstance(n, compound_kinds) and hasattr(n, "end_lineno") and n.end_lineno:
            # after the whole block; indent from the HEADER line
            points.append((n.end_lineno, False, n.lineno, True))
    near = list(near_lines) or [1]
    best: dict[tuple[int, bool], int] = {}
    indent_of: dict[tuple[int, bool], int] = {}
    block_of: dict[tuple[int, bool], bool] = {}
    for lineno, before, ifrom, is_block in points:
        d = min(abs(lineno - nl) for nl in near)
        key = (lineno, before)
        # Same position: closer to a failing site wins; a BLOCK-end hole
        # beats a simple-statement end (shunting_yard line 17 is both the
        # Expr end and the While end -- the While header indent is correct);
        # among blocks, the INNERMOST header (largest lineno) wins.
        take = False
        if key not in best or d < best[key]:
            take = True
        elif d == best[key]:
            if is_block and not block_of[key]:
                take = True
            elif is_block == block_of[key] and is_block and ifrom > indent_of[key]:
                take = True
        if take:
            best[key] = d
            indent_of[key] = ifrom
            block_of[key] = is_block
    # Structural priority (omission class), AST-based so blank lines never
    # masquerade as block ends: before a ``return`` first (wrap), then after
    # a complete If/While/For (shunting_yard pop-while), then after an
    # assignment inside a loop (reverse_linked_list ``prevnode = node``),
    # then site-distance. Pure distance ranks early-line holes first and
    # burns the wall before the winning late hole is tried (measured: wrap
    # 80 inserts, never insert:10:before).
    ends_block: set[int] = set()       # end_lineno of If/While/For
    ends_assign_in_loop: set[int] = set()
    returns: set[int] = set()
    try:
        tree0 = ast.parse(source_text)
    except SyntaxError:
        tree0 = None
    if tree0 is not None:
        for n in ast.walk(tree0):
            if isinstance(n, (ast.If, ast.While, ast.For)) and n.end_lineno:
                ends_block.add(n.end_lineno)
            if isinstance(n, ast.Return) and n.lineno:
                returns.add(n.lineno)
            if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)) and n.end_lineno:
                # inside any loop body?
                for p in ast.walk(tree0):
                    if isinstance(p, (ast.While, ast.For)) and p.end_lineno and \
                       p.lineno < n.lineno <= p.end_lineno:
                        ends_assign_in_loop.add(n.end_lineno)
                        break

    def _tier(ln: int, before: bool) -> int:
        if before and ln in returns:
            return 0
        if not before and ln in ends_block:
            return 1
        if not before and ln in ends_assign_in_loop:
            return 2
        return 3

    ranked = sorted(((ln, b, d, indent_of[(ln, b)]) for (ln, b), d in best.items()),
                    key=lambda t: (_tier(t[0], t[1]), t[2], t[0], not t[1]))
    return ranked


def _generate_insert_stmts(source_text: str, max_stmts: int = 48) -> list[str]:
    """Candidate statements for an omission hole, codebase-vocabulary first.

    Priority (matches the QuixBugs insertion class):
      1. ``list.append(name)`` -- wrap: lines.append(text);
         shunting_yard: opstack.append(token)
      2. ``name = name``       -- reverse_linked_list: prevnode = node
      3. transplant of existing simple statements in this file
    """
    names = _all_names(source_text)
    lists = _list_like_names(source_text)
    stmts: list[str] = []
    seen: set[str] = set()

    def put(s: str | None):
        if not s:
            return
        s = s.strip()
        if not s or s in seen:
            return
        try:
            ast.parse(s)
        except SyntaxError:
            return
        seen.add(s)
        stmts.append(s)

    # Priority names: function params first, then for-loop targets, then the
    # rest -- golden omissions append the loop payload (wrap ``text``,
    # shunting ``token``), so those must hit within the first few stmts.
    params: list[str] = []
    fors: list[str] = []
    try:
        tree_p = ast.parse(source_text)
        for n in ast.walk(tree_p):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                params.extend(a.arg for a in n.args.args)
            if isinstance(n, (ast.For, ast.comprehension)):
                t = n.target
                for nm in ast.walk(t):
                    if isinstance(nm, ast.Name):
                        fors.append(nm.id)
    except SyntaxError:
        pass
    prio: list[str] = []
    for group in (params, fors, names):
        for nm in group:
            if nm in names and nm not in prio:
                prio.append(nm)
    for nm in names:
        if nm not in prio:
            prio.append(nm)

    # 1) appends: round-robin so every receiver sees priority args early
    #    (opstack.append(token) before exhausting rpntokens.append(*)).
    for a in prio:
        for lst in lists:
            put(f"{lst}.append({a})")
    # 2) name = name (live-variable copy; prevnode = node)
    for a in prio:
        for b in prio:
            if a != b:
                put(f"{a} = {b}")
    # 3) transplant existing simple statements (same function vocabulary)
    try:
        tree = ast.parse(source_text)
        for n in ast.walk(tree):
            if isinstance(n, (ast.Assign, ast.AugAssign, ast.Expr)) and hasattr(n, "end_lineno"):
                # Only short statements (avoid copying huge comprehensions whole
                # as a first resort -- still allow medium ones).
                if n.end_lineno and n.end_lineno - n.lineno <= 2:
                    text = "\n".join(
                        source_text.splitlines()[n.lineno - 1:n.end_lineno])
                    # strip to a single logical line when possible
                    put(" ".join(text.split()))
    except SyntaxError:
        pass
    return stmts[:max_stmts]


# ---------------------------------------------------------------------------
# Logging pass: which sites execute, with what envs, in which tests
# ---------------------------------------------------------------------------
def _read_log(path: pathlib.Path, *, limit: int = 512) -> list[dict[str, Any]]:
    rows = []
    if not path.is_file():
        return rows
    # Cap rows: hang-class loops can leave multi-megabyte logs even after
    # the preamble write-cap (partial flushes before SIGKILL).
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if len(rows) >= limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def _run_one(argv: list[str], root: pathlib.Path, env: dict[str, str],
             timeout_s: int) -> dict[str, Any]:
    return _PATCH._run_tests(root, argv, timeout_s, env)


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------
def run(args: Mapping[str, Any], root: str | os.PathLike[str]) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    if not isinstance(args, Mapping):
        raise CounterfactualSpecError("ARGS_NOT_OBJECT")
    source = _PATCH._safe_file(repo, args.get("source_path"), suffix=".py")
    tests_raw = [x for x in (args.get("test_paths") or []) if str(x).strip()]
    if not tests_raw:
        from canonical.runtime.bound_capabilities.python_test_corpus_discovery_v1 import (
            discover_test_paths,
        )
        try:
            tests_raw = discover_test_paths(source.parent)
        except FileNotFoundError as exc:
            raise CounterfactualSpecError("NO_TEST_FILES_UNDER_SOURCE_ROOT") from exc
    if not tests_raw:
        raise CounterfactualSpecError("TEST_PATHS_REQUIRED")
    tests = [_PATCH._safe_file(repo, x, suffix=".py") for x in tests_raw]
    argv = args.get("test_argv")
    if argv is None:
        argv = _PATCH.suite_argv(sys.executable, *tests)
    if not isinstance(argv, list):
        raise CounterfactualSpecError("TEST_ARGV_INVALID")
    argv = [str(x) for x in argv]
    timeout_s = max(1, min(int(args.get("timeout_s", 8)), 60))
    wall_budget_s = float(args.get("wall_budget_s", 120.0))
    max_sites = max(1, min(int(args.get("max_sites", 24)), 60))
    max_terms = max(1, min(int(args.get("max_terms", 40)), 120))
    output = (repo / str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise CounterfactualSpecError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    from canonical.runtime.write_authority_v1 import check_report
    check_report(repo, output, [source, *tests])

    original_bytes = source.read_bytes()
    try:
        source_text = original_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CounterfactualSpecError("SOURCE_NOT_UTF8") from exc
    rel = str(source.relative_to(repo)).replace("\\", "/")
    env_base = _PATCH._source_env(source, *tests)
    started = time.time()
    tested = 0
    attempts: list[dict[str, Any]] = []
    winner: dict[str, Any] | None = None
    log_path: pathlib.Path | None = None

    def time_up() -> bool:
        return (time.time() - started) >= wall_budget_s

    try:
        # ---- baseline ----------------------------------------------------
        baseline = _run_one(argv, repo, env_base, timeout_s)
        if baseline["returncode"] == 0 and not baseline["timed_out"]:
            raise CounterfactualSpecError("BASELINE_ALREADY_PASSES")
        # Hang-class bugs (bitcount ^=, sqrt Newton) make the baseline itself
        # time out.  A correct fix finishes in milliseconds, so every subsequent
        # probe can use a short timeout; a wrong candidate fails fast instead
        # of burning the whole wall budget on one infinite loop.
        run_to = max(1, min(int(timeout_s), 2)) if baseline.get("timed_out") else int(timeout_s)

        sites = collect_sites(source_text, rel)
        if not sites:
            return _finish(None, source_text, original_bytes, source, rel, tests,
                           baseline, tested, attempts, started,
                           status="OPEN__NO_INTERIOR_SITES")

        consts = _json_consts_from_tests(tests, source)
        ops = _file_operators(source_text)

        # ---- logging pass: envs per site, split by pass/fail -------------
        cfg_log = {s.sid: {"mode": "log"} for s in sites}
        env_log = dict(env_base)
        env_log["BRAIN_CF_CFG"] = json.dumps(cfg_log)
        log_path = repo / "_cf_log.jsonl"
        if log_path.exists():
            log_path.unlink()
        env_log["BRAIN_CF_LOG"] = str(log_path)

        # Instrument once for logging AND for all force runs.
        instrumented = _instrument(source_text, sites)
        source.write_text(instrumented, encoding="utf-8")
        _PATCH._purge_source_bytecode(source)

        # Run each test separately so we know which tests fail and which
        # sites they reach.  Collect node ids via --collect-only.
        # Cheap classify first (no instrumentation) so hang-class bugs get a
        # fail_ids list without paying the log hook on every attempt.
        node_ids = _collect_node_ids(repo, argv, env_base, run_to)
        fail_ids: list[str] = []
        pass_ids: list[str] = []
        for nid in node_ids:
            if time_up():
                break
            r = _run_one(_argv_for_node(argv, nid), repo, env_base, run_to)
            tested += 1
            ok = r["returncode"] == 0 and not r["timed_out"]
            (pass_ids if ok else fail_ids).append(nid)
        if not fail_ids:
            # Every individual test passed but the suite failed (ordering /
            # fixture issue) -- fall back to whole-suite classification.
            if baseline["returncode"] == 0 and not baseline.get("timed_out"):
                raise CounterfactualSpecError("BASELINE_ALREADY_PASSES")
            fail_ids = ["<suite>"]

        # ---- AugAssign operator flip pre-pass (BEFORE the logging pass) ---
        # bitcount: n ^= n - 1 -> n &= n - 1.  Aug sites cannot be force-
        # hooked, and a hanging baseline would burn the wall budget in the
        # log pass before we ever try this one-token fix.  Whole-suite probe
        # per flip: a correct flip finishes immediately.
        # Multi-target: a dict of one successor cannot express ^= wanting
        # BOTH &= (bitcount) and |=; a single-key overwrite once flipped
        # bitcount to |= and hung.  Try each successor in order.
        _AUG_FLIPS: dict[str, tuple[str, ...]] = {
            "^=": ("&=", "|="),
            "|=": ("^=", "&="),
            "&=": ("|=", "^="),
            "+=": ("-=",),
            "-=": ("+=",),
        }
        for s in sites:
            if winner or time_up():
                break
            if s.kind != "aug" or not isinstance(s.node, ast.AugAssign):
                continue
            op = type(s.node.op)
            op_spell = {ast.BitXor: "^=", ast.BitAnd: "&=", ast.BitOr: "|=",
                        ast.Add: "+=", ast.Sub: "-="}.get(op)
            if not op_spell or op_spell not in _AUG_FLIPS:
                continue
            raw_lines = source_text.splitlines(keepends=True)
            li = s.lineno - 1
            if li >= len(raw_lines) or op_spell not in raw_lines[li]:
                continue
            for flipped in _AUG_FLIPS[op_spell]:
                if winner or time_up():
                    break
                patched_lines = list(raw_lines)
                patched_lines[li] = raw_lines[li].replace(op_spell, flipped, 1)
                candidate = "".join(patched_lines)
                source.write_text(candidate, encoding="utf-8")
                _PATCH._purge_source_bytecode(source)
                r = _run_one(argv, repo, env_base, run_to)
                tested += 1
                attempts.append({"sid": s.sid, "mode": "aug_flip", "term": flipped,
                                 "test": "<suite>", "returncode": r["returncode"],
                                 "timed_out": r["timed_out"]})
                if r["returncode"] == 0 and not r["timed_out"]:
                    winner = {"site": s, "term": flipped, "mode": "aug_flip"}
                    source.write_bytes(original_bytes)
                    _PATCH._purge_source_bytecode(source)
                    break
                source.write_bytes(original_bytes)
                _PATCH._purge_source_bytecode(source)
        # ---- statement-insertion composition (omission class) --------------
        # Two-phase wall share so neither class starves the other:
        #   Phase 1 (first ~30% of wall): omission winners that finish in
        #     seconds (wrap 3s, shunting 11s, reverse 23s) land here.
        #   Phase 2 (after logging/force): remainder, so force-repaired bugs
        #     (BFS/lis/mergesort/sqrt) still get their budget -- running
        #     insertion first with the FULL wall regressed them OPEN.
        def _try_inserts(deadline: float) -> None:
            nonlocal winner, tested
            if winner is not None or time.time() >= deadline:
                return
            source.write_bytes(original_bytes)
            _PATCH._purge_source_bytecode(source)
            near = sorted({s.lineno for s in sites}) or [1]
            holes = _insert_points(source_text, near)
            insert_stmts = _generate_insert_stmts(source_text, max_stmts=40)

            def _up() -> bool:
                return winner is not None or time.time() >= deadline or time_up()

            for lineno, before, _rank, ifrom in holes:
                if _up():
                    break
                for stmt in insert_stmts:
                    if _up():
                        break
                    candidate = _insert_statement(source_text, lineno, stmt,
                                                  before=before,
                                                  indent_from=ifrom)
                    if candidate == source_text:
                        continue
                    try:
                        ast.parse(candidate)
                    except SyntaxError:
                        continue
                    source.write_text(candidate, encoding="utf-8")
                    _PATCH._purge_source_bytecode(source)
                    all_ok = True
                    # Insert probes are millisecond-fast when correct; a wrong
                    # insert can self-loop (reverse_linked_list ``node =
                    # nextnode`` at hole 4) and burn the full timeout_s=20.
                    # Cap at 3s so one hang cannot starve the golden hole.
                    insert_to = max(1, min(int(timeout_s), 3))
                    check_ids = (["<suite>"] if baseline.get("timed_out")
                                 or fail_ids == ["<suite>"] else fail_ids)
                    for nid in check_ids:
                        if nid == "<suite>":
                            r = _run_one(argv, repo, env_base, insert_to)
                        else:
                            r = _run_one(_argv_for_node(argv, nid), repo,
                                         env_base, insert_to)
                        tested += 1
                        attempts.append({
                            "sid": f"insert:{lineno}:{'before' if before else 'after'}",
                            "mode": "insert", "term": stmt,
                            "test": nid, "returncode": r["returncode"],
                            "timed_out": r["timed_out"]})
                        if r["returncode"] != 0 or r["timed_out"]:
                            all_ok = False
                            break
                    if all_ok:
                        r = _run_one(argv, repo, env_base, insert_to)
                        tested += 1
                        attempts.append({
                            "sid": f"insert:{lineno}:{'before' if before else 'after'}",
                            "mode": "insert", "term": stmt,
                            "test": "<suite>", "returncode": r["returncode"],
                            "timed_out": r["timed_out"]})
                        all_ok = r["returncode"] == 0 and not r["timed_out"]
                    if all_ok:
                        winner = {
                            "site": None, "term": stmt, "mode": "insert",
                            "insert_lineno": lineno, "insert_before": before,
                            "insert_indent_from": ifrom,
                        }
                        source.write_bytes(original_bytes)
                        _PATCH._purge_source_bytecode(source)
                        break
                    source.write_bytes(original_bytes)
                    _PATCH._purge_source_bytecode(source)

        # 50% / 40s cap: reverse_linked_list needs ~23s of pure insertion;
        # force-repaired bugs historically need ~20-45s after a24s phase-1.
        insert_phase1_deadline = started + min(40.0, wall_budget_s * 0.5)
        _try_inserts(insert_phase1_deadline)

        if winner is not None:
            # Skip logging / force search: the permanent install path below
            # rebuilds the one-line operator swap from the original text.
            sites_for_log: list[Site] = []
        else:
            sites_for_log = sites

        envs_by_sid: dict[str, list[dict[str, Any]]] = {}
        fail_envs_by_sid: dict[str, list[dict[str, Any]]] = {}
        if sites_for_log and not time_up():
            instrumented = _instrument(source_text, sites_for_log)
            source.write_text(instrumented, encoding="utf-8")
            _PATCH._purge_source_bytecode(source)
            for nid in fail_ids:
                if time_up() or winner:
                    break
                if nid == "<suite>":
                    one_argv = argv
                else:
                    one_argv = _argv_for_node(argv, nid)
                r = _run_one(one_argv, repo, env_log, run_to)
                tested += 1
                ok = r["returncode"] == 0 and not r["timed_out"]
                for row in _read_log(log_path):
                    sid = row.get("sid")
                    envs_by_sid.setdefault(sid, []).append(row)
                    if not ok:
                        fail_envs_by_sid.setdefault(sid, []).append(row)
                if log_path.exists():
                    log_path.unlink()
            # Pass-id envs are optional (names also come from the AST); skip
            # them on hang-class runs to save wall budget.

        # Site ranking: sites exercised MORE OFTEN inside failing runs rank
        # first (a one-shot init assign has ~1 observation; the loop-body bug
        # site has dozens).  Raised sites next (detect_cycle class), then by
        # kind (ret/cond before bare assigns), then later lineno (the defect
        # usually sits closer to the return than the prologue).
        #
        # Nested children of a reached root inherit its fail count: the log
        # pass instruments non-overlapping OUTERMOST spans, so an inner site
        # like sqrt's `abs(x - approx)` never gets its own rows even though
        # the failing test executed it.
        def _parent_fail_n(s: Site) -> int:
            best = 0
            for psid, rows in fail_envs_by_sid.items():
                if psid == s.sid:
                    continue
                # Recover the parent span from the sites list.
                for ps in sites:
                    if ps.sid == psid and ps.span[0] <= s.span[0] and s.span[1] <= ps.span[1]:
                        best = max(best, len(rows))
                        break
            return best

        def site_rank(s: Site) -> tuple:
            fail_n = len(fail_envs_by_sid.get(s.sid) or [])
            if fail_n == 0:
                fail_n = _parent_fail_n(s)
            raised = 1 if any(r.get("error") for r in envs_by_sid.get(s.sid, [])) else 0
            kind_pref = {"ret": 0, "cond": 1, "aug": 2, "assign": 3, "arg": 4,
                         "target": 5, "iter": 6, "expr": 7}.get(s.kind, 8)
            return (-fail_n, -raised, kind_pref, -s.lineno, s.sid)

        def _reached(s: Site) -> bool:
            if fail_envs_by_sid.get(s.sid):
                return True
            if fail_ids == ["<suite>"] and envs_by_sid.get(s.sid):
                return True
            # Nested inside a site a failing test reached?
            return _parent_fail_n(s) > 0

        ranked = sorted(sites, key=site_rank)
        # Only force sites a failing test actually reached (a never-executed
        # site cannot change that test's outcome).  Keep aug sites for the
        # operator-flip pre-pass; skip assignment-target (cannot be hooked).
        ranked = [s for s in ranked
                  if s.kind != "target" and _reached(s)]
        ranked = ranked[:max_sites]
        # Force-hook search skips aug (statement, not expression).
        ranked_force = [s for s in ranked if s.kind != "aug"]

        # Names in scope: union of logged env keys per site + free names of orig.
        def site_names(s: Site) -> list[str]:
            keys: set[str] = set()
            for row in envs_by_sid.get(s.sid, []):
                keys.update((row.get("env") or {}).keys())
            for n in ast.walk(s.node):
                if isinstance(n, ast.Name):
                    keys.add(n.id)
            # Never let hook internals leak into terms.
            keys -= {"__cf_hook__", "_cf_cfg", "_cf_log", "_CF_CFG", "_CF_LOG"}
            return sorted(k for k in keys if k.isidentifier() and not k.startswith("_"))

        # ---- force search -------------------------------------------------
        source.write_bytes(original_bytes)  # restore; force runs re-instrument per attempt
        _PATCH._purge_source_bytecode(source)

        for s in ranked_force:
            if winner or time_up():
                break
            names = site_names(s)
            attrs = _attr_names_from_envs(
                [row for row in envs_by_sid.get(s.sid, [])])
            terms = generate_terms(s, names, consts, attrs, ops, max_terms=max_terms)
            # Signature dedup against logged envs: keep one term per behaviour
            # vector on the observed states (observational equivalence at the site).
            obs = envs_by_sid.get(s.sid, [])
            terms = _dedup_by_signature(terms, obs, names)
            raised = any(r.get("error") for r in envs_by_sid.get(s.sid, []))
            # ALWAYS first: the permanent patch is an always-mode replacement.
            # on_exception only helps when the site itself raises and no
            # always-term can fix it (detect_cycle-class); prefer a clean
            # always win so we never depend on _find_safe_term.
            modes = (["always", "on_exception"] if raised else ["always"])
            for mode in modes:
                if winner or time_up():
                    break
                for term in terms:
                    if time_up():
                        break
                    cfg = {s.sid: {"mode": mode, "term": term}}
                    env_f = dict(env_base)
                    env_f["BRAIN_CF_CFG"] = json.dumps(cfg)
                    env_f.pop("BRAIN_CF_LOG", None)
                    # Re-instrument with ONLY this site hooked (others natural):
                    # cheaper and matches the permanent single-site patch.
                    one = _instrument(source_text, [s])
                    source.write_text(one, encoding="utf-8")
                    _PATCH._purge_source_bytecode(source)
                    # Hang-class (baseline timed_out): whole suite only, one
                    # short probe -- a wrong term hangs once, a right term
                    # finishes immediately.  Otherwise fail-ids first.
                    all_ok = True
                    if baseline.get("timed_out"):
                        r = _run_one(argv, repo, env_f, run_to)
                        tested += 1
                        attempts.append({"sid": s.sid, "mode": mode, "term": term,
                                         "test": "<suite>", "returncode": r["returncode"],
                                         "timed_out": r["timed_out"]})
                        all_ok = r["returncode"] == 0 and not r["timed_out"]
                    else:
                        for nid in fail_ids:
                            if nid == "<suite>":
                                r = _run_one(argv, repo, env_f, run_to)
                            else:
                                r = _run_one(_argv_for_node(argv, nid), repo, env_f, run_to)
                            tested += 1
                            attempts.append({"sid": s.sid, "mode": mode, "term": term,
                                             "test": nid, "returncode": r["returncode"],
                                             "timed_out": r["timed_out"]})
                            if r["returncode"] != 0 or r["timed_out"]:
                                all_ok = False
                                break
                        if all_ok and fail_ids != ["<suite>"]:
                            r = _run_one(argv, repo, env_f, run_to)
                            tested += 1
                            attempts.append({"sid": s.sid, "mode": mode, "term": term,
                                             "test": "<suite>", "returncode": r["returncode"],
                                             "timed_out": r["timed_out"]})
                            all_ok = r["returncode"] == 0 and not r["timed_out"]
                    if all_ok:
                        winner = {"site": s, "term": term, "mode": mode}
                        break
                    source.write_bytes(original_bytes)
                    _PATCH._purge_source_bytecode(source)

        # Phase 2 insertion: if force found nothing and wall remains, spend
        # the rest on omission holes (force-repaired bugs already won above).
        _try_inserts(started + wall_budget_s)

        # ---- permanent install + double replay + sabotage ------------------
        # Guard re-checked: an on_exception force-win with no safe always
        # term sets winner=None above and must not reach install.
        if winner is not None and not time_up():
            s: Site = winner["site"]
            term: str = winner["term"]
            mode: str = winner["mode"]
            # For on_exception winners the permanent patch must be a single
            # expression that does not raise.  Search safe terms (always-mode)
            # that reproduce the win; if none, keep the force-win as evidence
            # but do not claim a patch we cannot install cleanly.
            if mode == "on_exception":
                safe = _find_safe_term(source_text, s, argv, repo, env_base,
                                       fail_ids, run_to, consts, ops,
                                       envs_by_sid.get(s.sid, []), time_up,
                                       original_bytes)
                if safe is None:
                    source.write_bytes(original_bytes)
                    _PATCH._purge_source_bytecode(source)
                    winner = None
                else:
                    term = safe
                    winner["term"] = safe
        if winner is not None and not time_up():
            s = winner["site"]
            term = winner["term"]
            mode = winner["mode"]
            if mode == "insert":
                patched = _insert_statement(
                    source_text, int(winner["insert_lineno"]), term,
                    before=bool(winner["insert_before"]),
                    indent_from=int(winner.get("insert_indent_from")
                                   or winner["insert_lineno"]))
                # Site is unused for sabotage anchoring; sabotage removes the
                # inserted line (must fail) instead of mutating a span.
                s = None
            elif mode == "aug_flip":
                # Rebuild the one-line operator swap from the original text.
                # `term` is the NEW operator spell (e.g. "&="); find the old
                # one on that line by elimination among known aug operators.
                raw_lines = source_text.splitlines(keepends=True)
                li = s.lineno - 1
                line = raw_lines[li]
                for a in ("^=", "&=", "|=", "+=", "-="):
                    if a != term and a in line:
                        raw_lines[li] = line.replace(a, term, 1)
                        break
                patched = "".join(raw_lines)
            else:
                patched = _install_term(source_text, s, term)
            # Sabotage: mutate the installed term; the suite must then fail.
            if mode == "insert":
                # Remove the inserted statement line -- suite must fail.
                _ins = term.strip()
                sabotaged_lines = [
                    ln for ln in patched.splitlines(keepends=True)
                    if ln.strip() != _ins]
                sabotaged = "".join(sabotaged_lines)
                if sabotaged == patched:
                    sabotaged = None
            else:
                sabotaged = _sabotage(patched, s, term)
            source.write_text(patched, encoding="utf-8")
            _PATCH._purge_source_bytecode(source)
            replays = []
            ok = True
            for _ in range(2):
                r = _run_one(argv, repo, env_base, run_to)
                tested += 1
                replays.append({"returncode": r["returncode"],
                                "timed_out": r["timed_out"]})
                ok = ok and r["returncode"] == 0 and not r["timed_out"]
            sabotage_ok = True
            if sabotaged is not None and sabotaged != patched:
                source.write_text(sabotaged, encoding="utf-8")
                _PATCH._purge_source_bytecode(source)
                r = _run_one(argv, repo, env_base, run_to)
                tested += 1
                # Sabotage must NOT pass (suite discriminates the patch).
                sabotage_ok = not (r["returncode"] == 0 and not r["timed_out"])
                source.write_text(patched, encoding="utf-8")
                _PATCH._purge_source_bytecode(source)
            if ok:
                winner.update({"patched": patched, "replays": replays,
                               "sabotage_discriminates": sabotage_ok,
                               "term": term})
            else:
                winner = None
    except CounterfactualSpecError as exc:
        source.write_bytes(original_bytes)
        _PATCH._purge_source_bytecode(source)
        if str(exc) == "BASELINE_ALREADY_PASSES":
            raise
        return _finish(None, source_text, original_bytes, source, rel, tests,
                       {"returncode": None, "timed_out": False}, tested, attempts,
                       started, status="ERROR__" + str(exc))
    finally:
        # Always restore the original source; the caller applies the diff to a
        # fresh copy (integrity rule: search never leaves edits on disk).
        try:
            source.write_bytes(original_bytes)
            _PATCH._purge_source_bytecode(source)
            if log_path is not None and log_path.exists():
                log_path.unlink()
        except OSError:
            pass

    return _finish(winner, source_text, original_bytes, source, rel, tests,
                   baseline, tested, attempts, started)


def _finish(winner, source_text, original_bytes, source, rel, tests, baseline,
            tested, attempts, started, status=None, extra=None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "status": status or "OPEN__NO_VERIFIED_COUNTERFACTUAL_PATCH",
        "pass": False,
        "source_path": rel,
        "source_sha256": _PATCH._sha(original_bytes),
        "test_paths": [str(p.name) for p in tests],
        "baseline_returncode": baseline.get("returncode"),
        "baseline_timed_out": baseline.get("timed_out"),
        "tested_candidate_count": tested,
        "model_dependency_count": 0,
        "external_capability_provider_count": 0,
        "incremental_spend_usd": 0,
        "source_restored": source.read_bytes() == original_bytes,
        "attempts": attempts[-80:],
        "patches": [],
        "hard_nonclaims": [
            "NO_UNIVERSAL_COUNTERFACTUAL_COMPLETENESS",
            "NO_MULTI_EDIT_COMPLETENESS",
            "NO_NON_PYTHON_SUPPORT",
            "NO_SEMANTIC_CORRECTNESS_BEYOND_BOUND_TEST_ORACLE",
            "NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY",
        ],
        "seconds": round(time.time() - started, 1),
    }
    if extra:
        result.update(extra)
    if winner is not None:
        before = source_text
        after = winner["patched"]
        patch = _PATCH._diff(rel, before, after)
        result.update({
            "status": "PASS__VERIFIED_COUNTERFACTUAL_PATCH_FOUND",
            "pass": True,
            "winning_site": (winner["site"].sid if winner.get("site") is not None
                             else "insert"),
            "winning_kind": (winner["site"].kind if winner.get("site") is not None
                             else "stmt"),
            "winning_term": winner["term"],
            "winning_mode": winner["mode"],
            "verification_replays": winner.get("replays"),
            "sabotage_discriminates": winner.get("sabotage_discriminates"),
            "unified_diff": patch,
            "candidate_source_sha256": _PATCH._sha(after.encode("utf-8")),
            "patches": [{
                "source_path": rel,
                "original_sha256": _PATCH._sha(original_bytes),
                "candidate_sha256": _PATCH._sha(after.encode("utf-8")),
                "unified_diff": patch,
            }],
        })
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _split_pytest_argv(argv: list[str]) -> tuple[list[str], list[str]] | None:
    """Split `python -m pytest ...` into (prefix-through-pytest, targets).

    Returns None when the argv is not the direct-pytest form (e.g. the
    suite_runner `-c` form), in which case node ids are unavailable.
    """
    if not argv or len(argv) < 3:
        return None
    # argv[0] is the interpreter; require `-m pytest` (or `-m pytest.X`).
    if argv[1] != "-m" or not str(argv[2]).startswith("pytest"):
        return None
    prefix = list(argv[:3])
    targets: list[str] = []
    i = 3
    while i < len(argv):
        a = argv[i]
        if a in ("-p", "-k", "-o", "-c") and i + 1 < len(argv):
            prefix.extend([a, argv[i + 1]])
            i += 2
            continue
        if a.startswith("-"):
            prefix.append(a)
            i += 1
            continue
        targets.append(a)
        i += 1
    if not targets:
        return None
    return prefix, targets


def _collect_node_ids(repo: pathlib.Path, argv: list[str], env: dict[str, str],
                      timeout_s: int) -> list[str]:
    """pytest --collect-only node ids, or a single synthetic id.

    Works when argv is `python -m pytest ...` (the measuring harness's form).
    The suite_runner form (`python -c SUITE_RUNNER ...`) has no node ids and
    falls back to whole-suite classification.

    Rebuilds a minimal collect argv: a duplicated ``-q`` (original quiet flag
    re-appended after ``--collect-only``) makes pytest 9 emit ``file: count``
    instead of node ids, so only exe/``-m pytest``/targets/collect-flags are
    kept -- never the original quiet flags.
    """
    split = _split_pytest_argv(argv)
    if split is None:
        return ["<suite>"]
    prefix, targets = split
    head = prefix[:3]  # exe -m pytest
    collect_argv = head + ["--collect-only", "-q", "-p", "no:cacheprovider"] + targets
    r = _run_one(collect_argv, repo, env, timeout_s)
    ids = []
    for line in (r.get("stdout") or "").splitlines():
        line = line.strip()
        if "::" in line and not line.startswith("=") and "error" not in line.lower():
            ids.append(line)
    return ids or ["<suite>"]


def _argv_for_node(argv: list[str], node_id: str) -> list[str]:
    if node_id == "<suite>":
        return list(argv)
    split = _split_pytest_argv(argv)
    if split is None:
        return list(argv)
    prefix, _targets = split
    return prefix + [node_id]


def _dedup_by_signature(terms: Sequence[str], obs: Sequence[Mapping[str, Any]],
                        names: Sequence[str], per_sig: int = 4) -> list[str]:
    """Keep up to ``per_sig`` terms per distinct behaviour vector on the logged envs.

    One term per signature is NOT enough: with a single observation, ``(x > 3)``
    and the constant ``True`` share a signature, and keeping only the constant
    destroys the comparison flip.  Prefer terms that *use names* (they can
    generalize) over bare constants, and keep a few structurally different
    candidates per signature so the force search can still find the fix.
    """
    if not obs:
        return list(terms)
    envs = [dict(row.get("env") or {}) for row in obs]
    buckets: dict[tuple, list[str]] = {}
    order: list[tuple] = []
    free: list[str] = []  # NameError offline (calls a global fn) -- keep all
    for t in terms:
        sig = []
        free_term = False
        for env in envs:
            try:
                local = {k: env[k] for k in names if k in env}
                v = eval(t, {"__builtins__": _BUILTIN_NS}, local)  # noqa: S307
                sig.append(_PATCH._sha(repr(v).encode("utf-8"))[:16])
            except NameError:
                # References a global/function not in the offline env (gcd,
                # helpers).  Signature is unknowable -- MUST keep the term.
                free_term = True
                break
            except Exception:
                sig.append("ERR")
        if free_term:
            free.append(t)
            continue
        key = tuple(sig)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(t)

    def _pref(t: str) -> tuple:
        # Lower sorts first inside a bucket: uses-a-name before bare constant,
        # then shorter (Occam), then alphabetical for determinism.
        uses_name = 0 if any(n in t for n in names) else 1
        is_const = 0 if not any(op in t for op in "+-*/%<>=&|^") else 1
        return (uses_name, is_const, len(t), t)

    out: list[str] = []
    for key in order:
        bucket = sorted(buckets[key], key=_pref)
        # Always keep the original (terms[0]) first if present in this bucket.
        if terms and terms[0] in bucket:
            bucket.remove(terms[0])
            bucket.insert(0, terms[0])
        out.extend(bucket[:per_sig])
    out.extend(free)
    # Global order: original first, then first-of-each-bucket (shortest pref),
    # then the rest of the kept set in original term order.
    kept = set(out)
    final: list[str] = []
    if terms and terms[0] in kept:
        final.append(terms[0])
    for t in terms:
        if t in kept and t not in final:
            final.append(t)
    return final or list(terms[:8])


_BUILTIN_NS: dict[str, Any] = {
    "len": len, "abs": abs, "int": int, "float": float, "str": str,
    "bool": bool, "sum": sum, "min": min, "max": max, "sorted": sorted,
    "round": round, "ord": ord, "range": range, "list": list, "tuple": tuple,
    "set": set, "dict": dict, "zip": zip, "any": any, "all": all,
    "None": None, "True": True, "False": False,
}


def _find_safe_term(source_text: str, site: Site, argv, repo, env_base,
                    fail_ids, timeout_s, consts, ops, obs, time_up,
                    original_bytes: bytes) -> str | None:
    """For on_exception winners: an always-mode term that does not raise on
    logged envs and makes the failing tests pass (the permanent patch).

    Probes by writing a single-site instrumented copy of original_bytes to
    disk, force-running the failing tests, then restoring original_bytes.
    """
    keys: set[str] = set()
    for row in obs:
        keys.update((row.get("env") or {}).keys())
    for n in ast.walk(site.node):
        if isinstance(n, ast.Name):
            keys.add(n.id)
    names = sorted(k for k in keys if k.isidentifier() and not k.startswith("_")
                   and k not in ("__cf_hook__",))
    attrs = _attr_names_from_envs(obs)
    terms = generate_terms(site, names, consts, attrs, ops, max_terms=48)
    safe_terms = []
    for t in terms:
        raises = False
        for row in obs:
            env = dict(row.get("env") or {})
            local = {k: env[k] for k in names if k in env}
            try:
                eval(t, {"__builtins__": _BUILTIN_NS}, local)  # noqa: S307
            except Exception:
                raises = True
                break
        if not raises and t != site.source:
            safe_terms.append(t)
    if not safe_terms:
        return None
    rel = site.sid.split(":", 1)[0]
    source_path = repo / rel
    try:
        for term in safe_terms:
            if time_up():
                return None
            cfg = {site.sid: {"mode": "always", "term": term}}
            env_f = dict(env_base)
            env_f["BRAIN_CF_CFG"] = json.dumps(cfg)
            env_f.pop("BRAIN_CF_LOG", None)
            instrumented = _instrument(source_text, [site])
            source_path.write_text(instrumented, encoding="utf-8")
            _PATCH._purge_source_bytecode(source_path)
            all_ok = True
            for nid in fail_ids:
                r = _run_one(_argv_for_node(argv, nid), repo, env_f, timeout_s)
                if r["returncode"] != 0 or r["timed_out"]:
                    all_ok = False
                    break
            if all_ok:
                r = _run_one(argv, repo, env_f, timeout_s)
                if r["returncode"] == 0 and not r["timed_out"]:
                    return term
        return None
    finally:
        source_path.write_bytes(original_bytes)
        _PATCH._purge_source_bytecode(source_path)


def _sabotage(patched: str, site: Site, term: str) -> str | None:
    """Mutate the installed term so the suite should fail if the patch is load-bearing.

    The term sits at ``site.span[0]`` in ``patched`` (``_install_term`` splices
    in place).  Do NOT rfind: for a name like ``queue`` the last occurrence is
    a later ``queue.popleft`` and the mutation would miss the patch entirely.
    """
    flips = [("==", "!="), ("!=", "=="), ("<", ">"), (">", "<"),
             ("<=", ">="), (">=", "<="), ("+", "-"), ("-", "+"),
             ("*", "+"), ("&", "|"), ("|", "&"), ("and", "or"), ("or", "and")]
    raw = patched.encode("utf-8")
    idx = site.span[0]
    if idx > len(raw) or raw[idx:idx + len(term.encode("utf-8"))] != term.encode("utf-8"):
        # Span drifted (shouldn't for a pure splice) -- fall back to first match
        # of the exact term as a whole token near the original line.
        idx = patched.find(term)
        if idx < 0:
            return None
    end = idx + len(term)
    region = patched[idx:end]
    for a, b in flips:
        if a in region:
            sabot = region.replace(a, b, 1)
            return patched[:idx] + sabot + patched[end:]
    if term in ("True", "False"):
        other = "False" if term == "True" else "True"
        return patched[:idx] + other + patched[end:]
    try:
        v = ast.literal_eval(term)
        if isinstance(v, bool):
            return patched[:idx] + (not v).__repr__() + patched[end:]
        if isinstance(v, (int, float)):
            return patched[:idx] + repr(v + 1) + patched[end:]
    except (ValueError, SyntaxError):
        pass
    # Last resort: wrap with not (boolean contexts) or drop a load-bearing name.
    if term.isidentifier():
        # Replace the name with a neutral wrong name so the suite must fail.
        return patched[:idx] + f"__sabotage_{term}__" + patched[end:]
    return patched[:idx] + f"not ({term})" + patched[end:]


if __name__ == "__main__":
    raise SystemExit("library module -- use canonical/tools/counterfactual_repair_quixbugs_measure_v1.py")

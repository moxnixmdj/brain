"""Full-Function AST-Diff & Minimal Subtree Delta Cross-Repo Transfer Engine (K3=0, $0.00).

Fixes the two root causes that kept single_experience_transfer_v1 at 0% on real OSS repos:
1. Raw diff hunks fail ast.parse on 45-86% of real commits (block headers, multi-hunk fixes).
   -> Parse the ENTIRE enclosing function before/after and align statement blocks cleanly.
2. Whole-statement matching almost never transfers across different codebases.
   -> Descend in lockstep to the MINIMAL differing expression/guard subtree, alpha-normalize
      variables/literals while preserving operators/builtins/keywords, and apply learned
      rewrite deltas inside any matching expression site in an unseen repository!
"""
from __future__ import annotations

import ast
import copy
import difflib
from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


_BUILTINS_KEEP = frozenset({
    "None", "True", "False", "len", "isinstance", "str", "bytes", "int",
    "float", "bool", "list", "dict", "set", "tuple", "type", "any", "all",
    "min", "max", "sum", "sorted", "reversed", "enumerate", "zip", "range",
})


@dataclass(frozen=True)
class MinimalSubtreeRule:
    lhs_sig: str
    rhs_sig: str
    lhs_template: ast.AST
    rhs_template: ast.AST
    var_names: tuple[str, ...]
    support_count: int = 1
    example: str = ""


def _collect_functions(tree: ast.Module) -> dict[str, ast.AST]:
    out: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out[f"{node.name}.{item.name}"] = item
    return out


def minimal_changed_subtrees(b_node: ast.AST, a_node: ast.AST) -> list[tuple[ast.AST, ast.AST]]:
    """Descend in lockstep while outer AST node type & child arity match."""
    if ast.dump(b_node) == ast.dump(a_node):
        return []
    if type(b_node) is not type(a_node):
        return [(b_node, a_node)]
    diffs: list[tuple[str, ast.AST, ast.AST]] = []
    for f in b_node._fields:
        bv, av = getattr(b_node, f), getattr(a_node, f)
        if isinstance(bv, ast.AST) and isinstance(av, ast.AST):
            if ast.dump(bv) != ast.dump(av):
                diffs.append((f, bv, av))
        elif isinstance(bv, list) and isinstance(av, list):
            if len(bv) == len(av) and all(isinstance(x, ast.AST) for x in bv + av):
                ldiffs = [(x, y) for x, y in zip(bv, av) if ast.dump(x) != ast.dump(y)]
                if len(ldiffs) == 1:
                    diffs.append((f, ldiffs[0][0], ldiffs[0][1]))
                elif ldiffs:
                    return [(b_node, a_node)]
            elif bv != av:
                return [(b_node, a_node)]
        elif bv != av:
            return [(b_node, a_node)]
    if len(diffs) == 1:
        _, cb, ca = diffs[0]
        # Keep parent operator context when only a leaf Name/Constant changed
        if isinstance(cb, (ast.Name, ast.Constant)) and isinstance(ca, (ast.Name, ast.Constant)):
            return [(b_node, a_node)]
        return minimal_changed_subtrees(cb, ca)
    return [(b_node, a_node)]


def _alpha_sig_and_template(node: ast.AST, env: dict[str, str]) -> tuple[str, ast.AST]:
    """Build deterministic alpha-normalized signature + template AST with `__V0__` placeholders."""
    cloned = copy.deepcopy(node)

    def walk(n: ast.AST) -> str:
        if isinstance(n, ast.Name):
            if n.id in _BUILTINS_KEEP:
                return f"B({n.id})"
            if n.id not in env:
                env[n.id] = f"__V{len(env)}__"
            n.id = env[n.id]
            return n.id
        if isinstance(n, ast.Constant):
            if n.value is None or isinstance(n.value, bool):
                return f"C({n.value!r})"
            return f"C({type(n.value).__name__})"
        if isinstance(n, ast.Attribute):
            return f"Attr({walk(n.value)}.{n.attr})"
        if isinstance(n, ast.Call):
            fn = walk(n.func)
            args = ",".join(walk(a) for a in n.args)
            kws = ",".join(f"{k.arg}={walk(k.value)}" for k in n.keywords)
            return f"Call({fn};[{args}];{{{kws}}})"
        if isinstance(n, ast.Compare):
            ops = ",".join(type(o).__name__ for o in n.ops)
            cmps = ",".join(walk(c) for c in n.comparators)
            return f"Cmp({walk(n.left)};{ops};[{cmps}])"
        if isinstance(n, ast.BoolOp):
            return f"Bool({type(n.op).__name__};[{','.join(walk(v) for v in n.values)}])"
        if isinstance(n, ast.BinOp):
            return f"Bin({type(n.op).__name__};{walk(n.left)};{walk(n.right)})"
        if isinstance(n, ast.UnaryOp):
            return f"Un({type(n.op).__name__};{walk(n.operand)})"
        if isinstance(n, ast.Subscript):
            return f"Sub({walk(n.value)}[{walk(n.slice)}])"
        if isinstance(n, ast.IfExp):
            return f"IfExp({walk(n.test)}?{walk(n.body)}:{walk(n.orelse)})"
        if isinstance(n, (ast.List, ast.Tuple, ast.Set)):
            return f"{type(n).__name__}({','.join(walk(e) for e in n.elts)})"
        return type(n).__name__

    sig = walk(cloned)
    return sig, cloned


def extract_function_ast_deltas(before_src: str, after_src: str) -> list[tuple[ast.expr, ast.expr]]:
    """Parse full before/after Python files and return minimal changed expression subtree pairs."""
    try:
        t1, t2 = ast.parse(before_src), ast.parse(after_src)
    except SyntaxError:
        return []
    f1, f2 = _collect_functions(t1), _collect_functions(t2)
    out: list[tuple[ast.expr, ast.expr]] = []
    for name in sorted(set(f1) & set(f2)):
        n1, n2 = f1[name], f2[name]
        if ast.dump(n1) == ast.dump(n2):
            continue

        def walk_body(b1: list[ast.stmt], b2: list[ast.stmt]) -> None:
            s1, s2 = [ast.unparse(x) for x in b1], [ast.unparse(x) for x in b2]
            for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, s1, s2).get_opcodes():
                if tag == "replace" and (i2 - i1) == 1 and (j2 - j1) == 1:
                    x1, x2 = b1[i1], b2[j1]
                    if isinstance(x1, ast.If) and isinstance(x2, ast.If):
                        for db, da in minimal_changed_subtrees(x1.test, x2.test):
                            if isinstance(db, ast.expr) and isinstance(da, ast.expr):
                                out.append((db, da))
                        walk_body(x1.body, x2.body)
                        walk_body(x1.orelse, x2.orelse)
                    elif isinstance(x1, ast.For) and isinstance(x2, ast.For):
                        for db, da in minimal_changed_subtrees(x1.iter, x2.iter):
                            if isinstance(db, ast.expr) and isinstance(da, ast.expr):
                                out.append((db, da))
                        walk_body(x1.body, x2.body)
                    elif isinstance(x1, ast.While) and isinstance(x2, ast.While):
                        for db, da in minimal_changed_subtrees(x1.test, x2.test):
                            if isinstance(db, ast.expr) and isinstance(da, ast.expr):
                                out.append((db, da))
                        walk_body(x1.body, x2.body)
                    else:
                        for db, da in minimal_changed_subtrees(x1, x2):
                            if isinstance(db, ast.expr) and isinstance(da, ast.expr):
                                out.append((db, da))

        walk_body(n1.body, n2.body)  # type: ignore[attr-defined]
    return out


def _match_template(pat: ast.AST, target: ast.AST, bindings: dict[str, ast.AST]) -> bool:
    """Structurally match alpha-normalized template AST against a target expression AST."""
    if isinstance(pat, ast.Name) and pat.id.startswith("__V") and pat.id.endswith("__"):
        prev = bindings.get(pat.id)
        if prev is not None:
            return ast.dump(prev) == ast.dump(target)
        bindings[pat.id] = target
        return True
    if type(pat) is not type(target):
        return False
    if isinstance(pat, ast.Constant):
        if pat.value is None or isinstance(pat.value, bool):
            return pat.value is target.value  # type: ignore[attr-defined]
        return type(pat.value) is type(target.value) and pat.value == target.value  # type: ignore[attr-defined]
    for f in pat._fields:
        pv, tv = getattr(pat, f), getattr(target, f)
        if isinstance(pv, ast.AST):
            if not isinstance(tv, ast.AST) or not _match_template(pv, tv, bindings):
                return False
        elif isinstance(pv, list):
            if not isinstance(tv, list) or len(pv) != len(tv):
                return False
            for pe, te in zip(pv, tv):
                if isinstance(pe, ast.AST):
                    if not isinstance(te, ast.AST) or not _match_template(pe, te, bindings):
                        return False
                elif pe != te:
                    return False
        elif pv != tv:
            return False
    return True


def _instantiate_template(rhs: ast.AST, bindings: Mapping[str, ast.AST]) -> ast.AST | None:
    """Substitute matched bindings into rhs template; fail closed if any unbound var remains."""
    cloned = copy.deepcopy(rhs)

    class _Subst(ast.NodeTransformer):
        def __init__(self) -> None:
            self.unbound = False

        def visit_Name(self, node: ast.Name) -> ast.AST:
            if node.id.startswith("__V") and node.id.endswith("__"):
                if node.id not in bindings:
                    self.unbound = True
                    return node
                return copy.deepcopy(bindings[node.id])
            return node

    sub = _Subst()
    res = sub.visit(cloned)
    return None if sub.unbound else res


_SAFE_SCOPE_BUILTINS = (
    "bool", "str", "int", "float", "list", "tuple", "set", "dict", "len", "bytes",
)


def collect_function_scope(fn_node: ast.AST) -> list[str]:
    """Collect parameter and local-variable names actually in scope inside a target function."""
    names: list[str] = []
    if isinstance(fn_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = fn_node.args
        for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
            names.append(a.arg)
        if args.vararg:
            names.append(args.vararg.arg)
        if args.kwarg:
            names.append(args.kwarg.arg)
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and n.id not in names:
            names.append(n.id)
    return names[:16]


class MinimalSubtreeTransferStore:
    """Learn executable 0-hole & 1-scope-hole minimal-subtree rewrite rules from full-function fixes."""

    def __init__(self, *, allow_one_scope_hole: bool = True) -> None:
        self._allow_one_scope_hole = allow_one_scope_hole
        self._counts: Counter[tuple[str, str]] = Counter()
        self._rules: dict[tuple[str, str], MinimalSubtreeRule] = {}
        self._free_vars: dict[tuple[str, str], tuple[str, ...]] = {}

    def learn_from_file_pair(self, before_src: str, after_src: str) -> int:
        added = 0
        for db, da in extract_function_ast_deltas(before_src, after_src):
            env: dict[str, str] = {}
            lhs_sig, lhs_t = _alpha_sig_and_template(db, env)
            rhs_sig, rhs_t = _alpha_sig_and_template(da, env)
            if lhs_sig == rhs_sig or lhs_sig.startswith("C("):
                continue
            lhs_vars = {n.id for n in ast.walk(lhs_t) if isinstance(n, ast.Name) and n.id.startswith("__V")}
            rhs_vars = {n.id for n in ast.walk(rhs_t) if isinstance(n, ast.Name) and n.id.startswith("__V")}
            free = tuple(sorted(rhs_vars - lhs_vars))
            max_holes = 1 if self._allow_one_scope_hole else 0
            if len(free) > max_holes:
                continue
            if lhs_sig.startswith("__V") and not isinstance(rhs_t, (ast.Call, ast.IfExp, ast.BoolOp, ast.Compare)):
                continue
            key = (lhs_sig, rhs_sig)
            self._counts[key] += 1
            if key not in self._rules:
                self._free_vars[key] = free
                self._rules[key] = MinimalSubtreeRule(
                    lhs_sig=lhs_sig,
                    rhs_sig=rhs_sig,
                    lhs_template=lhs_t,
                    rhs_template=rhs_t,
                    var_names=tuple(sorted(lhs_vars)),
                    support_count=1,
                    example=f"{ast.unparse(db)[:50]} -> {ast.unparse(da)[:50]}",
                )
            added += 1
        return added

    def rules(self) -> list[MinimalSubtreeRule]:
        return [
            MinimalSubtreeRule(
                lhs_sig=r.lhs_sig,
                rhs_sig=r.rhs_sig,
                lhs_template=r.lhs_template,
                rhs_template=r.rhs_template,
                var_names=r.var_names,
                support_count=self._counts[(r.lhs_sig, r.rhs_sig)],
                example=r.example,
            )
            for r in self._rules.values()
        ]

    def apply_to_expr(
        self,
        expr_node: ast.expr,
        *,
        scope_names: Sequence[str] = (),
    ) -> list[tuple[MinimalSubtreeRule, str]]:
        """Return executable rewritten expressions using only matched bindings + target function's own scope."""
        out: list[tuple[MinimalSubtreeRule, str]] = []
        seen: set[str] = set()
        pool = list(scope_names) + list(_SAFE_SCOPE_BUILTINS)
        for rule in sorted(self.rules(), key=lambda r: -r.support_count):
            bindings: dict[str, ast.AST] = {}
            if not _match_template(rule.lhs_template, expr_node, bindings):
                continue
            free = self._free_vars.get((rule.lhs_sig, rule.rhs_sig), ())
            if not free:
                inst = _instantiate_template(rule.rhs_template, bindings)
                if inst is not None:
                    src = ast.unparse(inst)
                    if src not in seen:
                        seen.add(src)
                        out.append((rule, src))
            elif len(free) == 1:
                hv = free[0]
                for sym in pool:
                    b2 = dict(bindings)
                    b2[hv] = ast.Name(id=sym, ctx=ast.Load())
                    inst = _instantiate_template(rule.rhs_template, b2)
                    if inst is not None:
                        src = ast.unparse(inst)
                        if src not in seen:
                            seen.add(src)
                            out.append((rule, src))
        return out

    def evaluate_heldout_pairs(self, heldout_pairs: Sequence[tuple[str, str]]) -> dict[str, Any]:
        """Exact AST-match executable transfer evaluation on unseen (before_src, after_src) file pairs."""
        total_deltas = 0
        exact_hits = 0
        hit_examples: list[dict[str, str]] = []
        for b_src, a_src in heldout_pairs:
            try:
                t1, t2 = ast.parse(b_src), ast.parse(a_src)
            except SyntaxError:
                continue
            f1, f2 = _collect_functions(t1), _collect_functions(t2)
            for fn_nm in sorted(set(f1) & set(f2)):
                n1, n2 = f1[fn_nm], f2[fn_nm]
                if ast.dump(n1) == ast.dump(n2):
                    continue
                scope = collect_function_scope(n1)
                for db, da in extract_function_ast_deltas(ast.unparse(n1), ast.unparse(n2)):
                    total_deltas += 1
                    want = ast.unparse(da)
                    for rule, cand in self.apply_to_expr(db, scope_names=scope):
                        if cand == want:
                            exact_hits += 1
                            hit_examples.append({
                                "before": ast.unparse(db)[:60],
                                "after": want[:60],
                                "rule_example": rule.example,
                            })
                            break
        return {
            "learned_rules": len(self._rules),
            "heldout_deltas": total_deltas,
            "exact_executable_hits": exact_hits,
            "hit_rate": round(exact_hits / max(1, total_deltas), 4),
            "hit_examples": hit_examples[:10],
        }

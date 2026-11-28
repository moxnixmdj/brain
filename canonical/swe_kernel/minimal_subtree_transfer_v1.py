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
import pathlib
import subprocess
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
        # Keep parent expression context when only a leaf Name/Constant or operator token changed
        _leaf_types = (ast.Name, ast.Constant, ast.operator, ast.cmpop, ast.boolop, ast.unaryop)
        if isinstance(cb, _leaf_types) and isinstance(ca, _leaf_types):
            return [(b_node, a_node)]
        return minimal_changed_subtrees(cb, ca)
    return [(b_node, a_node)]


def _alpha_sig_and_template(
    node: ast.AST,
    env: dict[str, str],
    *,
    attr_env: dict[str, str] | None = None,
    const_env: dict[tuple[type, Any], str] | None = None,
) -> tuple[str, ast.AST]:
    """Build deterministic alpha-normalized signature + template AST with `__V0__` (and optional `__A0__`) placeholders."""
    cloned = copy.deepcopy(node)

    def walk(n: ast.AST) -> str:
        if isinstance(n, ast.Name):
            if n.id in _BUILTINS_KEEP:
                return f"B({n.id})"
            if n.id.startswith("__V") and n.id.endswith("__"):
                return n.id
            if n.id not in env:
                env[n.id] = f"__V{len(env)}__"
            n.id = env[n.id]
            return n.id
        if isinstance(n, ast.Constant):
            if n.value is None or isinstance(n.value, bool):
                return f"C({n.value!r})"
            if const_env is not None:
                ck = (type(n.value), n.value)
                if ck not in const_env:
                    const_env[ck] = f"__K{len(const_env)}__"
                n.value = const_env[ck]
                return f"K({type(ck[1]).__name__}:{n.value})"
            return f"C({type(n.value).__name__})"
        if isinstance(n, ast.Attribute):
            val_s = walk(n.value)
            if attr_env is not None:
                if n.attr not in attr_env:
                    attr_env[n.attr] = f"__A{len(attr_env)}__"
                n.attr = attr_env[n.attr]
            return f"Attr({val_s}.{n.attr})"
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


def _lift_shared_compound_subexprs(db: ast.expr, da: ast.expr) -> tuple[ast.expr, ast.expr] | None:
    """Plotkin LGG lifting: replace maximal non-trivial subexpressions appearing identically on BOTH
    sides of `(db, da)` with shared placeholder variables (`__V0__`, ...).

    Example: `self.envvar is not None -> self.envvar` lifts `self.envvar` to `__V0__`, yielding
    the universal rule `__V0__ is not None -> __V0__` that transfers across ANY repo!
    Similarly `'streamed' if c else 'other' -> 'streamed'` lifts `'streamed'` to `__V0__`,
    and `isinstance(x, T) or hasattr(x, 'f') -> isinstance(x, T)` lifts `isinstance(x, T)` to `__V0__`!
    """
    def sub_dumps(root: ast.AST) -> dict[str, ast.AST]:
        found: dict[str, ast.AST] = {}
        for n in ast.walk(root):
            if isinstance(n, (ast.Attribute, ast.Subscript, ast.Call, ast.BinOp, ast.BoolOp, ast.Compare, ast.Tuple)):
                found[ast.dump(n)] = n
            elif isinstance(n, ast.Constant) and n.value is not None and not isinstance(n.value, bool):
                found[ast.dump(n)] = n
        return found

    b_map = sub_dumps(db)
    a_map = sub_dumps(da)
    shared = [d for d in b_map if d in a_map]
    if not shared:
        return None
    # Prefer maximal shared subexpressions (longest AST dump first)
    shared.sort(key=len, reverse=True)
    # Keep up to 3 disjoint maximal shared subexpressions
    chosen: list[str] = []
    for d in shared:
        if any(d in prev for prev in chosen):
            continue
        chosen.append(d)
        if len(chosen) >= 3:
            break
    repl_map = {d: f"__LGG{i}__" for i, d in enumerate(chosen)}

    class _Lifter(ast.NodeTransformer):
        def visit(self, node: ast.AST) -> ast.AST:
            d = ast.dump(node)
            if d in repl_map:
                return ast.Name(id=repl_map[d], ctx=ast.Load())
            return super().visit(node)

    nb = _Lifter().visit(copy.deepcopy(db))
    na = _Lifter().visit(copy.deepcopy(da))
    if not isinstance(nb, ast.expr) or not isinstance(na, ast.expr):
        return None
    # Also lift remaining unshared constants & compound drop-branches on LHS into fresh variables so
    # `'a' if self.flag else 'b' -> 'a'` becomes `__V0__ if __V1__ else __V2__ -> __V0__`, and
    # `A or hasattr(x, 'f') -> A` becomes `__V0__ or __V1__ -> __V0__`!
    extra_idx = len(chosen)
    rhs_names = {n.id for n in ast.walk(na) if isinstance(n, ast.Name)}

    class _DropWildcard(ast.NodeTransformer):
        def __init__(self) -> None:
            self.idx = extra_idx

        def _fresh(self) -> ast.Name:
            nm = f"__LGG{self.idx}__"
            self.idx += 1
            return ast.Name(id=nm, ctx=ast.Load())

        def _contains_rhs_var(self, sub: ast.AST) -> bool:
            return any(isinstance(x, ast.Name) and x.id in rhs_names for x in ast.walk(sub))

        def visit_Constant(self, node: ast.Constant) -> ast.AST:
            if node.value is not None and not isinstance(node.value, bool):
                return self._fresh()
            return node

        def visit_Call(self, node: ast.Call) -> ast.AST:
            if node is not nb and not self._contains_rhs_var(node):
                return self._fresh()
            return self.generic_visit(node)

        def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
            if node is not nb and not self._contains_rhs_var(node):
                return self._fresh()
            return self.generic_visit(node)

    nb = _DropWildcard().visit(nb)
    if ast.dump(nb) == ast.dump(db) and ast.dump(na) == ast.dump(da):
        return None
    return nb, na


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


def _match_template(
    pat: ast.AST,
    target: ast.AST,
    bindings: dict[str, ast.AST],
    attr_bindings: dict[str, str] | None = None,
) -> bool:
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
    if isinstance(pat, ast.Attribute) and isinstance(target, ast.Attribute):
        if not _match_template(pat.value, target.value, bindings, attr_bindings):
            return False
        if pat.attr.startswith("__A") and pat.attr.endswith("__"):
            if attr_bindings is None:
                return False
            prev_a = attr_bindings.get(pat.attr)
            if prev_a is not None:
                return prev_a == target.attr
            attr_bindings[pat.attr] = target.attr
            return True
        return pat.attr == target.attr
    for f in pat._fields:
        pv, tv = getattr(pat, f), getattr(target, f)
        if isinstance(pv, ast.AST):
            if not isinstance(tv, ast.AST) or not _match_template(pv, tv, bindings, attr_bindings):
                return False
        elif isinstance(pv, list):
            if not isinstance(tv, list) or len(pv) != len(tv):
                return False
            for pe, te in zip(pv, tv):
                if isinstance(pe, ast.AST):
                    if not isinstance(te, ast.AST) or not _match_template(pe, te, bindings, attr_bindings):
                        return False
                elif pe != te:
                    return False
        elif pv != tv:
            return False
    return True


def _instantiate_template(
    rhs: ast.AST,
    bindings: Mapping[str, ast.AST],
    attr_bindings: Mapping[str, str] | None = None,
) -> ast.AST | None:
    """Substitute matched bindings into rhs template; fail closed if any unbound var/attr remains."""
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

        def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
            node = self.generic_visit(node)  # type: ignore[assignment]
            if node.attr.startswith("__A") and node.attr.endswith("__"):
                if not attr_bindings or node.attr not in attr_bindings:
                    self.unbound = True
                    return node
                node.attr = attr_bindings[node.attr]
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


def collect_file_attrs(tree: ast.AST, *, max_attrs: int = 48) -> list[str]:
    """Collect attribute and method names defined or referenced in the same Python module."""
    counts: Counter[str] = Counter()
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute) and not n.attr.startswith("__"):
            counts[n.attr] += 1
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("__"):
            counts[n.name] += 1
    return [a for a, _ in counts.most_common(max_attrs)]


def collect_class_attrs(tree: ast.AST, fn_qualname: str) -> list[str]:
    """Collect attribute and method names defined/used inside the enclosing class of `Class.method`."""
    if "." not in fn_qualname:
        return []
    cls_name = fn_qualname.split(".", 1)[0]
    counts: Counter[str] = Counter()
    for node in getattr(tree, "body", ()):
        if isinstance(node, ast.ClassDef) and node.name == cls_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith("__"):
                    counts[item.name] += 1
            for sub in ast.walk(node):
                if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) and sub.value.id == "self":
                    if not sub.attr.startswith("__"):
                        counts[sub.attr] += 1
            break
    return [a for a, _ in counts.most_common(40)]


class MinimalSubtreeTransferStore:
    """Learn executable 0-hole & 1-scope-hole minimal-subtree rewrite rules from full-function fixes."""

    def __init__(self, *, allow_one_scope_hole: bool = True) -> None:
        self._allow_one_scope_hole = allow_one_scope_hole
        self._counts: Counter[tuple[str, str]] = Counter()
        self._rules: dict[tuple[str, str], MinimalSubtreeRule] = {}
        self._free_vars: dict[tuple[str, str], tuple[str, ...]] = {}
        self._free_attrs: dict[tuple[str, str], tuple[str, ...]] = {}

    def _register_pair(
        self,
        db: ast.expr,
        da: ast.expr,
        *,
        example_str: str,
        generalize_attrs: bool = False,
    ) -> int:
        env: dict[str, str] = {}
        attr_env: dict[str, str] | None = {} if generalize_attrs else None
        lhs_sig, lhs_t = _alpha_sig_and_template(db, env, attr_env=attr_env)
        rhs_sig, rhs_t = _alpha_sig_and_template(da, env, attr_env=attr_env)
        if lhs_sig == rhs_sig or lhs_sig.startswith("C("):
            return 0
        lhs_vars = {n.id for n in ast.walk(lhs_t) if isinstance(n, ast.Name) and n.id.startswith("__V")}
        rhs_vars = {n.id for n in ast.walk(rhs_t) if isinstance(n, ast.Name) and n.id.startswith("__V")}
        lhs_attrs = {n.attr for n in ast.walk(lhs_t) if isinstance(n, ast.Attribute) and n.attr.startswith("__A")}
        rhs_attrs = {n.attr for n in ast.walk(rhs_t) if isinstance(n, ast.Attribute) and n.attr.startswith("__A")}
        free_v = tuple(sorted(rhs_vars - lhs_vars))
        free_a = tuple(sorted(rhs_attrs - lhs_attrs))
        max_holes = 1 if self._allow_one_scope_hole else 0
        if len(free_v) + len(free_a) > max_holes:
            return 0
        # Avoid degenerate bare-variable -> bare-variable or bare-attr -> bare-attr noise unless structured
        if lhs_sig.startswith("__V") and not isinstance(rhs_t, (ast.Call, ast.IfExp, ast.BoolOp, ast.Compare, ast.Subscript)):
            return 0
        if generalize_attrs and lhs_sig == "Attr(__V0__.__A0__)" and rhs_sig == "Attr(__V0__.__A1__)":
            # Only allow sibling-attribute swap explicitly via scope-grounded attr pool (still high-value when guarded!)
            pass
        key = (lhs_sig, rhs_sig)
        self._counts[key] += 1
        if key not in self._rules:
            self._free_vars[key] = free_v
            self._free_attrs[key] = free_a
            self._rules[key] = MinimalSubtreeRule(
                lhs_sig=lhs_sig,
                rhs_sig=rhs_sig,
                lhs_template=lhs_t,
                rhs_template=rhs_t,
                var_names=tuple(sorted(lhs_vars)),
                support_count=1,
                example=example_str,
            )
        return 1

    def learn_from_file_pair(self, before_src: str, after_src: str) -> int:
        added = 0
        for db, da in extract_function_ast_deltas(before_src, after_src):
            ex = f"{ast.unparse(db)[:50]} -> {ast.unparse(da)[:50]}"
            added += self._register_pair(db, da, example_str=ex, generalize_attrs=False)
            # Plotkin LGG: lift shared compound subexpressions to universal __V0__ rules!
            lifted = _lift_shared_compound_subexprs(db, da)
            if lifted is not None:
                added += self._register_pair(lifted[0], lifted[1], example_str=f"[LGG] {ex}", generalize_attrs=False)
                if any(isinstance(n, ast.Attribute) for n in ast.walk(lifted[0])):
                    added += self._register_pair(lifted[0], lifted[1], example_str=f"[LGG+ATTR] {ex}", generalize_attrs=True)
            # Also learn attribute-hole generalized rule when attributes appear on LHS
            has_attr = any(isinstance(n, ast.Attribute) for n in ast.walk(db))
            if has_attr:
                added += self._register_pair(db, da, example_str=f"[ATTR] {ex}", generalize_attrs=True)
        return added

    def learn_from_git_repo(
        self,
        repo_root: str | pathlib.Path,
        *,
        max_commits: int = 120,
        before_commit: str | None = None,
    ) -> dict[str, Any]:
        """Insanely fast pre-task repo-history instant learning via batched `git cat-file --batch`."""
        root = str(pathlib.Path(repo_root).resolve())
        rev_spec = f"{before_commit}^" if before_commit else "HEAD"
        try:
            raw_log = subprocess.check_output(
                [
                    "git", "-C", root, "log", rev_spec, f"-n{max_commits}", "--no-merges",
                    "--name-only", "--pretty=format:===COMMIT:%H===", "--", "*.py",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=8,
            )
        except Exception:
            return {"commits_scanned": 0, "pairs_learned": 0, "rules_total": len(self._rules)}

        # Parse single-source-file Python commits
        candidates: list[tuple[str, str]] = []
        cur_sha: str | None = None
        cur_files: list[str] = []

        def flush() -> None:
            if cur_sha:
                py_src = [f for f in cur_files if f.endswith(".py") and not f.startswith("tests/") and "/test" not in f and not f.split("/")[-1].startswith("test_")]
                if len(py_src) == 1:
                    candidates.append((cur_sha, py_src[0]))

        for line in raw_log.splitlines():
            line = line.strip()
            if line.startswith("===COMMIT:") and line.endswith("==="):
                flush()
                cur_sha = line[10:-3]
                cur_files = []
            elif line:
                cur_files.append(line)
        flush()

        if not candidates:
            return {"commits_scanned": 0, "pairs_learned": 0, "rules_total": len(self._rules)}

        # Batch fetch all (before, after) blobs in ONE single `git cat-file --batch` invocation!
        specs: list[str] = []
        for sha, rel in candidates:
            specs.append(f"{sha}^:{rel}")
            specs.append(f"{sha}:{rel}")
        try:
            proc = subprocess.run(
                ["git", "-C", root, "cat-file", "--batch"],
                input=("\n".join(specs) + "\n").encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=12,
                check=False,
            )
            data = proc.stdout
        except Exception:
            return {"commits_scanned": len(candidates), "pairs_learned": 0, "rules_total": len(self._rules)}

        # Parse `git cat-file --batch` framing: "<sha> <type> <size>\n<bytes>\n" OR "<spec> missing\n"
        blobs: list[str | None] = []
        pos = 0
        n_bytes = len(data)
        for _ in specs:
            nl = data.find(b"\n", pos)
            if nl < 0:
                blobs.append(None)
                continue
            header = data[pos:nl].decode("utf-8", errors="replace")
            pos = nl + 1
            if header.endswith(" missing") or header.endswith(" ambiguous"):
                blobs.append(None)
                continue
            parts = header.rsplit(" ", 2)
            if len(parts) == 3 and parts[2].isdigit():
                sz = int(parts[2])
                body = data[pos : pos + sz].decode("utf-8", errors="replace")
                pos += sz + 1  # trailing newline
                blobs.append(body)
            else:
                blobs.append(None)

        pairs_learned = 0
        for i in range(0, len(blobs) - 1, 2):
            b_src, a_src = blobs[i], blobs[i + 1]
            if b_src and a_src and b_src != a_src and len(b_src) < 400_000 and len(a_src) < 400_000:
                if self.learn_from_file_pair(b_src, a_src) > 0:
                    pairs_learned += 1

        return {
            "commits_scanned": len(candidates),
            "pairs_learned": pairs_learned,
            "rules_total": len(self._rules),
        }

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
        attr_names: Sequence[str] = (),
    ) -> list[tuple[MinimalSubtreeRule, str]]:
        """Return executable rewritten expressions using only matched bindings + target function's own scope."""
        out: list[tuple[MinimalSubtreeRule, str]] = []
        seen: set[str] = set()
        orig_src = ast.unparse(expr_node)
        seen.add(orig_src)
        pool = list(scope_names) + list(_SAFE_SCOPE_BUILTINS)
        attr_pool = list(attr_names)
        for rule in sorted(self.rules(), key=lambda r: -r.support_count):
            bindings: dict[str, ast.AST] = {}
            attr_bindings: dict[str, str] = {}
            if not _match_template(rule.lhs_template, expr_node, bindings, attr_bindings):
                continue
            key = (rule.lhs_sig, rule.rhs_sig)
            free_v = self._free_vars.get(key, ())
            free_a = self._free_attrs.get(key, ())
            if not free_v and not free_a:
                inst = _instantiate_template(rule.rhs_template, bindings, attr_bindings)
                if inst is not None:
                    src = ast.unparse(inst)
                    if src not in seen:
                        seen.add(src)
                        out.append((rule, src))
            elif len(free_v) == 1 and not free_a:
                hv = free_v[0]
                for sym in pool:
                    b2 = dict(bindings)
                    b2[hv] = ast.Name(id=sym, ctx=ast.Load())
                    inst = _instantiate_template(rule.rhs_template, b2, attr_bindings)
                    if inst is not None:
                        src = ast.unparse(inst)
                        if src not in seen:
                            seen.add(src)
                            out.append((rule, src))
            elif len(free_a) == 1 and not free_v and attr_pool:
                ha = free_a[0]
                for asym in attr_pool[:32]:
                    a2 = dict(attr_bindings)
                    a2[ha] = asym
                    inst = _instantiate_template(rule.rhs_template, bindings, a2)
                    if inst is not None:
                        src = ast.unparse(inst)
                        if src not in seen:
                            seen.add(src)
                            out.append((rule, src))
        return out

    def propose_source_rewrites(
        self,
        source: str,
        *,
        focus_lines: set[int] | None = None,
        max_candidates: int = 60,
    ) -> list[dict[str, Any]]:
        """ORIGINATING whole-source patch generator: splice learned minimal-subtree rules directly
        into matching AST expression sites inside `source` (using ONLY in-scope symbols/attrs)."""
        if not self._rules:
            return []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        file_attrs = collect_file_attrs(tree)
        # Collect (priority, fn_scope, expr_node_path) for expression sites inside functions
        candidates: list[dict[str, Any]] = []
        seen_src: set[str] = {source}

        def walk_fn(fn_node: ast.AST, scope: list[str], attrs: list[str]) -> None:
            # Find parent->(field, idx, expr) sites inside fn_node
            sites: list[tuple[int, int, ast.AST, str, int | None, ast.expr]] = []

            def collect(node: ast.AST) -> None:
                for field, val in ast.iter_fields(node):
                    if isinstance(val, ast.expr):
                        ln = int(getattr(val, "lineno", 0) or 0)
                        on_focus = 0 if (focus_lines and ln in focus_lines) else 1
                        # Prefer non-leaf expressions first (higher precision), then leaf Names
                        is_leaf = 1 if isinstance(val, (ast.Name, ast.Constant)) else 0
                        sites.append((on_focus, is_leaf, node, field, None, val))
                        collect(val)
                    elif isinstance(val, list):
                        for idx, elem in enumerate(val):
                            if isinstance(elem, ast.expr):
                                ln = int(getattr(elem, "lineno", 0) or 0)
                                on_focus = 0 if (focus_lines and ln in focus_lines) else 1
                                is_leaf = 1 if isinstance(elem, (ast.Name, ast.Constant)) else 0
                                sites.append((on_focus, is_leaf, node, field, idx, elem))
                                collect(elem)
                            elif isinstance(elem, ast.AST):
                                collect(elem)
                    elif isinstance(val, ast.AST):
                        collect(val)

            collect(fn_node)
            sites.sort(key=lambda s: (s[0], s[1]))
            for _, _, parent, field, idx, expr_node in sites:
                if len(candidates) >= max_candidates:
                    return
                if isinstance(expr_node, ast.Constant):
                    continue
                # Skip assignment LHS / Store contexts
                if isinstance(getattr(expr_node, "ctx", None), (ast.Store, ast.Del)):
                    continue
                if isinstance(parent, ast.Call) and field == "func" and isinstance(expr_node, ast.Name):
                    continue
                rewrites = self.apply_to_expr(expr_node, scope_names=scope, attr_names=attrs)
                if not rewrites:
                    continue
                for rule, new_expr_src in rewrites[:4]:
                    if len(candidates) >= max_candidates:
                        return
                    try:
                        new_expr = ast.parse(new_expr_src, mode="eval").body
                    except SyntaxError:
                        continue
                    old_val = getattr(parent, field)
                    try:
                        if idx is None:
                            setattr(parent, field, new_expr)
                        else:
                            old_val[idx] = new_expr
                        new_src = ast.unparse(tree)
                    except Exception:
                        new_src = ""
                    finally:
                        if idx is None:
                            setattr(parent, field, old_val)
                        else:
                            old_val[idx] = expr_node
                    if new_src and new_src not in seen_src:
                        seen_src.add(new_src)
                        candidates.append({
                            "source": new_src,
                            "op_kind": f"subtree_rule:{rule.lhs_sig[:24]}->{rule.rhs_sig[:24]}",
                            "rule_example": rule.example,
                            "support_count": rule.support_count,
                            "lineno": int(getattr(expr_node, "lineno", 0) or 0),
                        })

        for fn_nm, fn in _collect_functions(tree).items():
            if len(candidates) >= max_candidates:
                break
            cls_attrs = collect_class_attrs(tree, fn_nm)
            merged_attrs = list(dict.fromkeys(cls_attrs + file_attrs))
            walk_fn(fn, collect_function_scope(fn), merged_attrs)
        return candidates

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
            file_attrs = collect_file_attrs(t1)
            f1, f2 = _collect_functions(t1), _collect_functions(t2)
            for fn_nm in sorted(set(f1) & set(f2)):
                n1, n2 = f1[fn_nm], f2[fn_nm]
                if ast.dump(n1) == ast.dump(n2):
                    continue
                scope = collect_function_scope(n1)
                merged_attrs = list(dict.fromkeys(collect_class_attrs(t1, fn_nm) + file_attrs))
                for db, da in extract_function_ast_deltas(ast.unparse(n1), ast.unparse(n2)):
                    total_deltas += 1
                    want = ast.unparse(da)
                    for rule, cand in self.apply_to_expr(db, scope_names=scope, attr_names=merged_attrs):
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

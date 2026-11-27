"""External, inspectable, editable, deletable structural SWE repair-skill store.

Zero weights, zero model calls, zero memorized world facts inside parameters.
Knowledge lives strictly outside parameters in plain JSON and can be inspected,
edited, or deleted without retraining.

How one verified experience becomes a portable cross-repo skill:
  1. Given ONE verified (before_source, after_source, failure_context) repair,
     locate the smallest changed AST region: a single changed expression/
     statement (modes "expr"/"stmt") OR the minimal connected slice of
     sibling statement lists whose length changed (mode "blk", e.g. an
     `if X is None: return None` guard deleted while the adjacent `return`
     was rewritten). Statement-block slices are anti-unified via
     prefix/suffix structural alignment + largest-shared-subexpression hole
     lifting (Refazer-style), so inter-statement dataflow becomes typed
     holes rather than forcing single-statement matches.
  2. Alpha-canonicalize all local/bound names and shared subtrees into typed
     holes ($H0, $H1, ...) while preserving Python operators, structural AST
     forms, and built-in/constant tokens. Any foreign repo-specific identifier
     that does not appear in the before pattern is refused at admission time
     (preventing the foreign-name grafting defect measured in real_commit_repair_v1).
  2b. Holes are annotated with computed dataflow tags (compared_none,
      coalesced_default, returned, subscripted) inferred from pattern
      structure -- a computed mechanism, not memorized knowledge.
  3. Attach the observed runtime/failure precondition traits (e.g. exception
     type, hole value traits such as falsey/not_none/not_bool, AST position).
  4. Admit the skill ONLY if it round-trips and reproduces the verified after
     AST on its own before AST.
  5. When a recalled skill proposes a patch that FAILS tests in a new repo,
     narrow its runtime precondition from the counterexample's observed traits
     while preserving positive support (online refutation, zero weight updates).

Authority: NONE. Computed mechanism only; zero parameters, zero model calls.
"""
from __future__ import annotations

import ast
import builtins
import copy
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_INSTANT_SWE_SKILL_STORE_V1"
STATUS_PROVISIONAL = "PROVISIONAL__ADMITTED_FROM_VERIFIED_FIX"
STATUS_NARROWED = "NARROWED__COUNTEREXAMPLE_REFINED"
STATUS_QUARANTINED = "QUARANTINED__UNSEPARABLE_COUNTEREXAMPLE"

DEFAULT_STORE_PATH = (
    Path(__file__).resolve().parent.parent
    / "state"
    / "INSTANT_SWE_SKILL_STORE_V1.json"
)

_BUILTIN_NAMES = frozenset(dir(builtins)) | frozenset({"None", "True", "False"})
_HOLE_PREFIX = "__BRAIN_HOLE_"


class SkillStoreError(ValueError):
    """Raised on malformed store or skill schema."""


def new_store() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": 1,
        "skills": {},
        "updated_at": None,
        "external_model_dependency": False,
        "parameters_stored": 0,
    }


def load_store(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path is not None else DEFAULT_STORE_PATH
    if not target.exists():
        return new_store()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SkillStoreError(f"STORE_UNREADABLE:{exc}") from exc
    if not isinstance(raw, Mapping) or raw.get("schema") != SCHEMA:
        raise SkillStoreError("STORE_SCHEMA_MISMATCH")
    skills = raw.get("skills")
    if not isinstance(skills, Mapping):
        raise SkillStoreError("STORE_SKILLS_NOT_OBJECT")
    out = new_store()
    out["version"] = int(raw.get("version", 1))
    out["skills"] = {
        str(k): dict(v) for k, v in skills.items() if isinstance(v, Mapping)
    }
    out["updated_at"] = raw.get("updated_at")
    return out


def save_store(store: Mapping[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    if store.get("schema") != SCHEMA:
        raise SkillStoreError("STORE_SCHEMA_MISMATCH")
    target = Path(path) if path is not None else DEFAULT_STORE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(store)
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload["external_model_dependency"] = False
    payload["parameters_stored"] = 0
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return payload


def delete_skill(store: dict[str, Any], skill_id: str) -> bool:
    """Deleting a skill from JSON immediately removes it without retraining."""
    return store["skills"].pop(str(skill_id), None) is not None


# ---------------------------------------------------------------------------
# AST serialization & alpha-canonical hole abstraction
# ---------------------------------------------------------------------------

def _ast_dump_structural(node: ast.AST) -> str:
    return ast.dump(node, annotate_fields=True, include_attributes=False)


def _node_fingerprint(node: ast.AST) -> str:
    return hashlib.sha256(_ast_dump_structural(node).encode("utf-8")).hexdigest()[:16]


def _collect_subexprs_by_dump(node: ast.AST) -> dict[str, ast.AST]:
    """Map structural dump -> representative AST expression node."""
    found: dict[str, ast.AST] = {}
    for sub in ast.walk(node):
        if isinstance(sub, (ast.Name, ast.Attribute, ast.Subscript, ast.Call)):
            # Only abstract expression subtrees in Load context (or standalone exprs)
            if isinstance(sub, (ast.Name, ast.Attribute, ast.Subscript)):
                if isinstance(getattr(sub, "ctx", None), (ast.Store, ast.Del)):
                    continue
            if isinstance(sub, ast.Name) and sub.id in _BUILTIN_NAMES:
                continue
            key = _ast_dump_structural(sub)
            if key not in found:
                found[key] = sub
    return found


def _node_size(node: ast.AST) -> int:
    return sum(1 for _ in ast.walk(node))


def _abstract_pair(
    before_node: ast.AST,
    after_node: ast.AST,
) -> tuple[ast.AST, ast.AST, dict[str, str], dict[str, str]] | None:
    """Alpha-canonicalize shared subexpressions in (before_node, after_node).

    Largest shared non-builtin subexpressions (Attribute/Subscript/Call/Name)
    are replaced consistently by canonical placeholder Names `__BRAIN_HOLE_0__`,
    `__BRAIN_HOLE_1__`, ...
    Returns (before_pat, after_pat, hole_to_original_unparsed, hole_kind)
    or None if `after_pat` contains any foreign non-builtin identifier that is
    neither a hole nor present in Python builtins/keywords.
    """
    b_map = _collect_subexprs_by_dump(before_node)
    a_map = _collect_subexprs_by_dump(after_node)

    # Shared subexpressions sorted largest-first so `a.converter` becomes ONE
    # hole rather than abstracting `a` and keeping `.converter` literal.
    shared_keys = [k for k in b_map if k in a_map]
    shared_keys.sort(key=lambda k: (-_node_size(b_map[k]), k))

    # Also include any non-builtin leaf Names occurring in before_node (even if
    # dropped in after_node) so preconditions remain repo-independent.
    before_names = [
        k
        for k, n in b_map.items()
        if isinstance(n, ast.Name) and k not in shared_keys
    ]
    before_names.sort()

    candidate_keys = shared_keys + before_names
    key_to_hole: dict[str, str] = {}
    hole_to_orig: dict[str, str] = {}
    hole_to_kind: dict[str, str] = {}

    class _Abstractor(ast.NodeTransformer):
        def _maybe_replace(self, node: ast.AST) -> ast.AST | None:
            if isinstance(node, (ast.Name, ast.Attribute, ast.Subscript)):
                if isinstance(getattr(node, "ctx", None), (ast.Store, ast.Del)):
                    return None
            if isinstance(node, ast.Name) and node.id in _BUILTIN_NAMES:
                return None
            dump = _ast_dump_structural(node)
            if dump in key_to_hole:
                return ast.Name(id=key_to_hole[dump], ctx=ast.Load())
            if dump in candidate_keys:
                # Assign hole ID deterministically in traversal order
                idx = len(key_to_hole)
                hid = f"{_HOLE_PREFIX}{idx}__"
                key_to_hole[dump] = hid
                hole_to_orig[hid] = ast.unparse(node)
                hole_to_kind[hid] = type(node).__name__
                return ast.Name(id=hid, ctx=ast.Load())
            return None

        def generic_visit(self, node: ast.AST) -> ast.AST:
            rep = self._maybe_replace(node)
            if rep is not None:
                return rep
            return super().generic_visit(node)

    abs_before = _Abstractor().visit(copy.deepcopy(before_node))
    abs_after = _Abstractor().visit(copy.deepcopy(after_node))
    ast.fix_missing_locations(abs_before)
    ast.fix_missing_locations(abs_after)

    # Admission safety check: forbid any foreign non-builtin Name in abs_after
    # that was NOT abstracted into a hole or bound locally inside abs_after.
    bound_in_after: set[str] = set()
    for n in ast.walk(abs_after):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            bound_in_after.add(n.id)
        elif isinstance(n, ast.arg):
            bound_in_after.add(n.arg)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            bound_in_after.add(n.name)

    for n in ast.walk(abs_after):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            if (
                not n.id.startswith(_HOLE_PREFIX)
                and n.id not in _BUILTIN_NAMES
                and n.id not in bound_in_after
            ):
                return None

    # Require at least one hole so we never store zero-generality literal hacks
    if not hole_to_orig:
        return None
    return abs_before, abs_after, hole_to_orig, hole_to_kind


def _is_hole_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name) and node.id.startswith(_HOLE_PREFIX):
        return node.id
    return None


def _candidate_local_names(window: ast.AST) -> dict[str, tuple[int, int]]:
    """Name ids BOUND inside `window`, keyed by name -> first-binding position.

    Only plain-name bindings count (Assign/AugAssign/AnnAssign name targets,
    for/comprehension targets, walrus, `with ... as x`). Attribute/subscript
    targets bind their base name elsewhere and are intentionally ignored.
    """
    out: dict[str, tuple[int, int]] = {}

    def _add(nid: str, node: ast.AST) -> None:
        pos = (int(getattr(node, "lineno", 0) or 0), int(getattr(node, "col_offset", 0) or 0))
        cur = out.get(nid)
        if cur is None or pos < cur:
            out[nid] = pos

    for node in ast.walk(window):
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            for tgt in node.targets if isinstance(node, ast.Assign) else [node.target]:
                if isinstance(tgt, ast.Name):
                    _add(tgt.id, tgt)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            for sub in ast.walk(node.target):
                if isinstance(sub, ast.Name):
                    _add(sub.id, sub)
        elif isinstance(node, ast.NamedExpr):
            if isinstance(node.target, ast.Name):
                _add(node.target.id, node.target)
        elif isinstance(node, ast.comprehension):
            for sub in ast.walk(node.target):
                if isinstance(sub, ast.Name):
                    _add(sub.id, sub)
        elif isinstance(node, ast.withitem) and node.optional_vars is not None:
            for sub in ast.walk(node.optional_vars):
                if isinstance(sub, ast.Name):
                    _add(sub.id, sub)
        elif isinstance(node, ast.arg):
            # Params/comprehension-iteration args bind names not owned by the
            # window: they must never be renamed. Mark as blocked.
            _add(_PARAM_PREFIX + node.arg, node)
    return out


def _private_local_names(window: ast.AST, full_tree: ast.AST) -> list[str]:
    """Window-private names: bound inside `window`, referenced ONLY inside it.

    Such names can be alpha-renamed (locally) without changing program meaning,
    which is what lets a multi-statement skill learned with one local variable
    spelling replay on a repo that spells it differently. Privacy is measured by
    Name-occurrence counts (window count == whole-file count), so it is exact for
    copies and shared trees alike. Param/`arg` bindings, `except E as e` names and
    global/nonlocal declarations are excluded (fail closed).
    """
    cand = _candidate_local_names(window)
    blocked: set[str] = set()
    for node in ast.walk(window):
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            blocked |= set(node.names)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            blocked.add(node.name)
    win_occ: dict[str, int] = {}
    file_occ: dict[str, int] = {}
    for node in ast.walk(window):
        if isinstance(node, ast.Name):
            win_occ[node.id] = win_occ.get(node.id, 0) + 1
    for node in ast.walk(full_tree):
        if isinstance(node, ast.Name):
            file_occ[node.id] = file_occ.get(node.id, 0) + 1
    scored: list[tuple[tuple[int, int], str]] = []
    for nid, pos in cand.items():
        if nid.startswith(_PARAM_PREFIX) or nid in blocked:
            continue
        wins = win_occ.get(nid, 0)
        # Private iff the file never references the name outside the window
        if wins and wins == file_occ.get(nid, 0):
            scored.append((pos, nid))
    scored.sort()
    return [nid for _, nid in scored]


_ALPHA_SEP = "__BRAIN_ALPHA_"
_PARAM_PREFIX = "__BRAIN_PARAM__:"


def _alpha_rename(node: ast.AST, mapping: Mapping[str, str]) -> ast.AST:
    """Rename Name ids per `mapping`, capture-free via a placeholder pass."""
    if not mapping:
        return node
    placeholders = {
        value: f"{_ALPHA_SEP}{i}__" for i, value in enumerate(sorted(set(mapping.values())))
    }
    from_placeholder = {p: v for v, p in placeholders.items()}
    clone = copy.deepcopy(node)
    for n in ast.walk(clone):
        if isinstance(n, ast.Name) and n.id in mapping:
            n.id = placeholders[mapping[n.id]]
    for n in ast.walk(clone):
        if isinstance(n, ast.Name) and n.id in from_placeholder:
            n.id = from_placeholder[n.id]
    ast.fix_missing_locations(clone)
    return clone


def _holes_of(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if _is_hole_name(n)}


def _project_missing_holes(
    env: dict[str, ast.AST],
    hole_to_orig: Mapping[str, str] | None,
    *roots: ast.AST | None,
) -> None:
    """Project de novo (after-only) holes from already-bound subtrees.

    A hole that occurs ONLY in the after-pattern has no unification source;
    it denotes a subtree that was already present elsewhere in the before
    code (or inside a bound hole, e.g. the receiver inside a bound Call).
    When exactly one DISTINCT structural form satisfies the origin string we
    bind it; otherwise the hole stays unbound and the caller fails closed
    (admission refuses the skill; replay skips the proposal).
    """
    for hid, orig_str in (hole_to_orig or {}).items():
        if hid in env or not orig_str:
            continue
        seen: dict[str, ast.AST] = {}
        for root in (*roots, *env.values()):
            if root is None:
                continue
            for sub in ast.walk(root):
                if isinstance(sub, (ast.Store,)):
                    continue
                try:
                    s = ast.unparse(sub)
                except Exception:
                    continue
                if s != orig_str:
                    continue
                ctx = getattr(sub, "ctx", None)
                if ctx is not None and not isinstance(ctx, ast.Load):
                    continue
                key = _ast_dump_structural(sub)
                if key not in seen:
                    seen[key] = sub
        if len(seen) == 1:
            env[hid] = copy.deepcopy(next(iter(seen.values())))


def _unify_ast(pattern: ast.AST, target: ast.AST, env: dict[str, ast.AST]) -> bool:
    """Structural AST unification with consistent hole bindings."""
    hid = _is_hole_name(pattern)
    if hid is not None:
        if not isinstance(target, ast.expr):
            return False
        if hid in env:
            return _ast_dump_structural(env[hid]) == _ast_dump_structural(target)
        env[hid] = copy.deepcopy(target)
        return True

    if type(pattern) is not type(target):
        return False

    for field_name, pat_val in ast.iter_fields(pattern):
        if field_name == "ctx":
            continue
        tgt_val = getattr(target, field_name)
        if isinstance(pat_val, ast.AST):
            if not isinstance(tgt_val, ast.AST):
                return False
            if not _unify_ast(pat_val, tgt_val, env):
                return False
        elif isinstance(pat_val, list):
            if not isinstance(tgt_val, list) or len(pat_val) != len(tgt_val):
                return False
            for p_item, t_item in zip(pat_val, tgt_val):
                if isinstance(p_item, ast.AST):
                    if not isinstance(t_item, ast.AST):
                        return False
                    if not _unify_ast(p_item, t_item, env):
                        return False
                elif p_item != t_item:
                    return False
        else:
            if pat_val != tgt_val:
                return False
    return True


def _instantiate_ast(pattern: ast.AST, env: Mapping[str, ast.AST]) -> ast.AST:
    class _Inst(ast.NodeTransformer):
        def visit_Name(self, node: ast.Name) -> ast.AST:
            if node.id in env:
                bound = copy.deepcopy(env[node.id])
                if hasattr(bound, "ctx") and hasattr(node, "ctx"):
                    bound.ctx = copy.deepcopy(node.ctx)
                return bound
            return node

    out = _Inst().visit(copy.deepcopy(pattern))
    ast.fix_missing_locations(out)
    return out


def _parse_fragment(code: str, mode: str) -> ast.AST:
    if mode == "expr":
        return ast.parse(code, mode="eval").body
    if mode == "blk":
        return ast.parse(code, mode="exec")
    mod = ast.parse(code, mode="exec")
    if len(mod.body) != 1:
        raise SkillStoreError("FRAGMENT_MUST_BE_SINGLE_NODE")
    return mod.body[0]


def _hole_dataflow_tags(
    before_root: ast.AST,
    after_root: ast.AST,
) -> dict[str, list[str]]:
    """Compute dataflow tags for canonical holes from pattern structure.

    Purely structural inference (no memorized facts):
      * compared_none     -- hole appears as the left side of an ``is None`` test;
      * isnull_compare    -- hole appears in any Compare against a None constant;
      * coalesced_default -- hole appears in a BoolOp ``or`` with a constant default;
      * returned          -- hole reaches a Return value;
      * subscripted       -- hole is subscripted somewhere.
    """
    tags: dict[str, set[str]] = {}

    def _tag(hole_id: str, label: str) -> None:
        tags.setdefault(hole_id, set()).add(label)

    def _holes_in(node: ast.AST) -> list[str]:
        out: list[str] = []
        for n in ast.walk(node):
            hid = _is_hole_name(n)
            if hid:
                out.append(hid)
        return out

    for root in (before_root, after_root):
        for n in ast.walk(root):
            if isinstance(n, ast.Compare) and len(n.ops) == 1:
                cmp0 = n.comparators[0]
                if isinstance(cmp0, ast.Constant) and cmp0.value is None:
                    for hid in _holes_in(n.left):
                        _tag(hid, "compared_none")
                        _tag(hid, "isnull_compare")
            if isinstance(n, ast.BoolOp) and isinstance(n.op, ast.Or):
                const_side = [v for v in n.values if isinstance(v, ast.Constant)]
                if const_side:
                    for v in n.values:
                        if isinstance(v, ast.Constant):
                            continue
                        for hid in _holes_in(v):
                            _tag(hid, "coalesced_default")
            if isinstance(n, ast.Return) and n.value is not None:
                for hid in _holes_in(n.value):
                    _tag(hid, "returned")
            if isinstance(n, ast.Subscript):
                for hid in _holes_in(n.value):
                    _tag(hid, "subscripted")

    return {hid: sorted(v) for hid, v in tags.items()}


_STATEMENT_LIST_FIELDS = frozenset({"body", "orelse", "finalbody"})


def _find_stmt_list_length_mismatch(
    b_root: ast.AST,
    a_root: ast.AST,
) -> list[tuple[str, ast.AST, ast.AST, list[ast.stmt], list[ast.stmt]]]:
    """Collect statement-list fields whose LENGTH changed anywhere in the trees.

    Walks the parallel trees node-by-node. Only same-typed positions are
    traversed (a type change means the whole subtree is the diff, handled by
    the single-node path). Returns at most a few hits; the caller fails closed
    unless there is exactly one hit (unambiguous multi-statement edit).
    """
    hits: list[tuple[str, ast.AST, ast.AST, list[ast.stmt], list[ast.stmt]]] = []

    def _walk(b_node: ast.AST, a_node: ast.AST) -> None:
        if type(b_node) is not type(a_node):
            return
        for field_name, b_val in ast.iter_fields(b_node):
            if field_name == "ctx":
                continue
            a_val = getattr(a_node, field_name, None)
            if not (isinstance(b_val, list) and isinstance(a_val, list)):
                continue
            b_is_stmt_list = all(isinstance(x, ast.stmt) for x in b_val)
            a_is_stmt_list = all(isinstance(x, ast.stmt) for x in a_val)
            if (
                field_name in _STATEMENT_LIST_FIELDS
                and b_is_stmt_list
                and a_is_stmt_list
                and len(b_val) != len(a_val)
            ):
                hits.append((field_name, b_node, a_node, list(b_val), list(a_val)))
                continue
            if len(b_val) == len(a_val):
                for bi, ai in zip(b_val, a_val):
                    if isinstance(bi, ast.AST) and isinstance(ai, ast.AST):
                        _walk(bi, ai)

    _walk(b_root, a_root)
    return hits


def _trim_changed_slice(
    b_list: list[ast.stmt],
    a_list: list[ast.stmt],
) -> tuple[list[ast.stmt], list[ast.stmt]]:
    """Prefix/suffix-trim structurally identical statements."""
    dumps_b = [_ast_dump_structural(s) for s in b_list]
    dumps_a = [_ast_dump_structural(s) for s in a_list]
    i = 0
    while i < len(b_list) and i < len(a_list) and dumps_b[i] == dumps_a[i]:
        i += 1
    j = 0
    while (
        j < len(b_list) - i
        and j < len(a_list) - i
        and dumps_b[len(b_list) - 1 - j] == dumps_a[len(a_list) - 1 - j]
    ):
        j += 1
    b_end = len(b_list) - j if j else len(b_list)
    a_end = len(a_list) - j if j else len(a_list)
    return b_list[i:b_end], a_list[i:a_end]


def _as_module(stmts: list[ast.stmt]) -> ast.Module:
    mod = ast.Module(body=[copy.deepcopy(s) for s in stmts], type_ignores=[])
    ast.fix_missing_locations(mod)
    return mod


def _changed_region(
    before_source: str,
    after_source: str,
) -> tuple[ast.AST, ast.AST, str] | None:
    """Locate the minimal connected changed AST region.

    Returns (before_node, after_node, mode) with mode in {"expr", "stmt", "blk"}:
      * "expr"/"stmt" -- a single smallest changed subtree (original behavior);
      * "blk" -- ast.Module wrappers around the minimal connected slice of a
        statement list whose length changed (e.g. guard-clause deletion with an
        adjacent `return` rewrite).
    Fails closed (None) when the trees disagree in more than one
    length-mismatched statement list (ambiguous multi-hunk fix).
    """
    try:
        b_tree = ast.parse(before_source)
        a_tree = ast.parse(after_source)
    except SyntaxError:
        return None

    block_hits = _find_stmt_list_length_mismatch(b_tree, a_tree)
    if len(block_hits) > 1:
        return None
    if len(block_hits) == 1:
        _, _b_parent, _a_parent, b_list, a_list = block_hits[0]
        b_slice, a_slice = _trim_changed_slice(b_list, a_list)
        if not b_slice or not a_slice:
            # Pure deletion/insertion blocks carry no cross-side dataflow holes;
            # they fail the >=1 hole admission gate anyway, so refuse early.
            return None
        if len(b_slice) > 6 or len(a_slice) > 6:
            return None
        return _as_module(b_slice), _as_module(a_slice), "blk"

    def _descend(b_node: ast.AST, a_node: ast.AST) -> tuple[ast.AST, ast.AST] | None:
        if _ast_dump_structural(b_node) == _ast_dump_structural(a_node):
            return None
        if type(b_node) is not type(a_node):
            return (b_node, a_node)
        diff_children: list[tuple[ast.AST, ast.AST]] = []
        scalar_diff = False
        for field_name, b_val in ast.iter_fields(b_node):
            if field_name == "ctx":
                continue
            a_val = getattr(a_node, field_name)
            if isinstance(b_val, ast.AST) and isinstance(a_val, ast.AST):
                if _ast_dump_structural(b_val) != _ast_dump_structural(a_val):
                    diff_children.append((b_val, a_val))
            elif isinstance(b_val, list) and isinstance(a_val, list):
                if len(b_val) != len(a_val):
                    scalar_diff = True
                else:
                    for bi, ai in zip(b_val, a_val):
                        if isinstance(bi, ast.AST) and isinstance(ai, ast.AST):
                            if _ast_dump_structural(bi) != _ast_dump_structural(ai):
                                diff_children.append((bi, ai))
                        elif bi != ai:
                            scalar_diff = True
            elif b_val != a_val:
                scalar_diff = True
        if not scalar_diff and len(diff_children) == 1:
            deeper = _descend(diff_children[0][0], diff_children[0][1])
            if deeper is not None:
                return deeper
        return (b_node, a_node)

    pair = _descend(b_tree, a_tree)
    if pair is None:
        return None
    b_node, a_node = pair
    # Keep expressions and single statements; refuse whole-module/class/func diffs
    if isinstance(b_node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        return None
    if isinstance(b_node, ast.expr) and isinstance(a_node, ast.expr):
        return b_node, a_node, "expr"
    if isinstance(b_node, ast.stmt) and isinstance(a_node, ast.stmt):
        return b_node, a_node, "stmt"
    return None


# ---------------------------------------------------------------------------
# Single-experience skill induction, recall & online refutation
# ---------------------------------------------------------------------------

def induce_skill_from_verified_fix(
    store: dict[str, Any],
    *,
    before_source: str,
    after_source: str,
    failure_context: Mapping[str, Any],
    hole_traits: Mapping[str, Sequence[str]] | None = None,
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Compile ONE verified fix into an alpha-canonical, admission-gated skill.

    Returns the admitted skill record, or None if the fix cannot be abstracted
    safely without foreign names or fails round-trip admission.
    """
    found = _changed_region(before_source, after_source)
    if found is None:
        return None
    b_node, a_node, mode = found
    if mode == "blk":
        # Refuse rewrites that delete nothing/keep nothing
        if not getattr(b_node, "body", None) or not getattr(a_node, "body", None):
            return None
    abstracted = _abstract_pair(b_node, a_node)
    if abstracted is None:
        return None
    b_pat, a_pat, hole_to_orig, hole_to_kind = abstracted

    # Round-trip admission check: pattern MUST unify with b_node (plus
    # project de novo holes) and instantiate a_node EXACTLY.
    env: dict[str, ast.AST] = {}
    if not _unify_ast(b_pat, b_node, env):
        return None
    _project_missing_holes(env, hole_to_orig, b_node)
    if _holes_of(a_pat) - env.keys():
        return None
    reconstructed = _instantiate_ast(a_pat, env)
    if _ast_dump_structural(reconstructed) != _ast_dump_structural(a_node):
        return None

    b_code = ast.unparse(b_pat)
    a_code = ast.unparse(a_pat)
    if b_code == a_code:
        return None
    # Anti-overfit admission gate: never admit unconditional `pass` deletion of assignments
    if a_code == "pass" and isinstance(b_node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
        return None

    hole_dataflow = _hole_dataflow_tags(b_pat, a_pat)

    # Window-private local names (blk mode): replay may alpha-rename these so a
    # skill learned with one variable spelling transfers to repos that spell
    # the same dataflow differently. Computed conservatively over the FULL
    # before/after sources; empty list = exact-name matching only.
    alpha_locals: list[str] = []
    if mode == "blk":
        try:
            _b_full = ast.parse(before_source)
            _a_full = ast.parse(after_source)
            _lb = _private_local_names(b_node, _b_full)
            _la = _private_local_names(a_node, _a_full)
            if _lb and _lb == _la:
                alpha_locals = _lb
        except (SyntaxError, RecursionError):
            alpha_locals = []

    # Map hole traits from original expression strings onto canonical hole IDs
    required_traits: dict[str, list[str]] = {}
    support_traits: dict[str, list[str]] = {}
    if hole_traits:
        for hid, orig_str in hole_to_orig.items():
            if orig_str in hole_traits:
                traits = sorted(set(str(t) for t in hole_traits[orig_str]))
                support_traits[hid] = traits
                # Only promote high-signal semantic traits immediately;
                # broad traits stay in support_traits for counterexample narrowing.
                high_signal = [
                    t for t in traits
                    if t in {"falsey_non_none_non_bool", "is_none", "type_mismatch"}
                ]
                if high_signal:
                    required_traits[hid] = high_signal

    ast_position = str(failure_context.get("ast_position") or mode)
    exception_type = str(failure_context.get("exception_type") or "")
    angelic_kind = str(failure_context.get("angelic_kind") or "")

    sig_payload = json.dumps(
        {"mode": mode, "before": b_code, "after": a_code, "pos": ast_position},
        sort_keys=True,
    )
    skill_id = "skill_" + hashlib.sha256(sig_payload.encode("utf-8")).hexdigest()[:12]



    existing = store["skills"].get(skill_id)
    if existing is not None:
        existing["support_count"] = int(existing.get("support_count", 1)) + 1
        if provenance:
            provs = list(existing.get("provenance_examples") or [])
            provs.append(dict(provenance))
            existing["provenance_examples"] = provs[-10:]
        return existing

    record: dict[str, Any] = {
        "skill_id": skill_id,
        "status": STATUS_PROVISIONAL,
        "mode": mode,
        "ast_position": ast_position,
        "before_pattern": b_code,
        "after_pattern": a_code,
        "hole_kinds": hole_to_kind,
        "hole_to_orig": dict(hole_to_orig),
        "alpha_locals": alpha_locals,
        "hole_dataflow": hole_dataflow,
        "required_hole_traits": required_traits,
        "support_hole_traits": support_traits,
        "exception_type_hint": exception_type,
        "angelic_kind_hint": angelic_kind,
        "support_count": 1,
        "refutations": [],
        "provenance_examples": [dict(provenance)] if provenance else [],
        "external_model_dependency": False,
        "parameters_stored": 0,
    }
    store["skills"][skill_id] = record
    return record


def propose_from_skills(
    store: Mapping[str, Any],
    target_node: ast.AST,
    *,
    ast_position: str,
    expr_traits: Mapping[str, Sequence[str]] | None = None,
    exception_type: str = "",
) -> list[dict[str, Any]]:
    """Match stored skills against a target AST node and live runtime traits.

    Returns instantiated candidate AST nodes with skill metadata, ordered by
    support count and specificity. Quarantined skills are never proposed.
    """
    skills = store.get("skills") or {}
    if not skills:
        return []

    target_mode = "expr" if isinstance(target_node, ast.expr) else "stmt"
    proposals: list[dict[str, Any]] = []
    seen_code: set[str] = set()

    ordered_skills = sorted(
        skills.values(),
        key=lambda s: (
            s.get("status") == STATUS_NARROWED,
            int(s.get("support_count", 0)),
            len(s.get("required_hole_traits") or {}),
        ),
        reverse=True,
    )

    for skill in ordered_skills:
        if skill.get("status") == STATUS_QUARANTINED:
            continue
        if skill.get("mode") != target_mode:
            continue
        skill_pos = str(skill.get("ast_position") or target_mode)
        if skill_pos not in {target_mode, ast_position}:
            continue
        exc_hint = str(skill.get("exception_type_hint") or "")
        if exc_hint and exception_type and exc_hint != exception_type:
            # Allow AssertionError-learned skills on AssertionError; keep crash
            # skills scoped to matching exception class.
            if exc_hint != "AssertionError":
                continue

        try:
            b_pat = _parse_fragment(skill["before_pattern"], target_mode)
            a_pat = _parse_fragment(skill["after_pattern"], target_mode)
        except (SyntaxError, SkillStoreError):
            continue

        env: dict[str, ast.AST] = {}
        if not _unify_ast(b_pat, target_node, env):
            continue
        _project_missing_holes(env, skill.get("hole_to_orig") or {}, target_node)
        if _holes_of(a_pat) - env.keys():
            continue  # de novo holes unprojectable: fail closed

        # Check runtime preconditions on bound holes
        req_traits = skill.get("required_hole_traits") or {}
        precondition_ok = True
        bound_traits: dict[str, list[str]] = {}
        for hid, bound_ast in env.items():
            unparsed = ast.unparse(bound_ast)
            observed = set(str(t) for t in (expr_traits or {}).get(unparsed, ()))
            bound_traits[hid] = sorted(observed)
            needed = set(str(t) for t in req_traits.get(hid, ()))
            if needed and not needed.issubset(observed):
                precondition_ok = False
                break
        if not precondition_ok:
            continue

        inst = _instantiate_ast(a_pat, env)
        inst_code = ast.unparse(inst)
        if inst_code == ast.unparse(target_node) or inst_code in seen_code:
            continue
        seen_code.add(inst_code)
        proposals.append({
            "skill_id": skill["skill_id"],
            "node": inst,
            "code": inst_code,
            "bound_holes": {k: ast.unparse(v) for k, v in env.items()},
            "bound_traits": bound_traits,
        })
    return proposals


def refute_skill(
    store: dict[str, Any],
    skill_id: str,
    *,
    counterexample_traits: Mapping[str, Sequence[str]],
    reason: str = "TESTS_FAILED",
) -> dict[str, Any]:
    """Narrow a PROVISIONAL skill from ONE falsifying counterexample.

    Preserves every previously required trait and adds ONE separating trait
    present in the skill's positive support state and absent in the
    counterexample. If no observable separates them, quarantines the skill
    (fail-closed, never widens).
    """
    skill = store["skills"].get(skill_id)
    if skill is None:
        return {"status": "UNKNOWN_SKILL", "skill_id": skill_id}

    support = skill.get("support_hole_traits") or {}
    required = {
        k: list(v) for k, v in (skill.get("required_hole_traits") or {}).items()
    }

    added: tuple[str, str] | None = None
    for hid in sorted(support):
        pos_traits = set(str(t) for t in support.get(hid, ()))
        neg_traits = set(str(t) for t in counterexample_traits.get(hid, ()))
        already = set(required.get(hid, ()))
        separators = sorted(pos_traits - neg_traits - already)
        if separators:
            chosen = separators[0]
            required.setdefault(hid, []).append(chosen)
            required[hid] = sorted(set(required[hid]))
            added = (hid, chosen)
            break

    refutations = list(skill.get("refutations") or [])
    if added is not None:
        skill["required_hole_traits"] = required
        skill["status"] = STATUS_NARROWED
        refutations.append({
            "reason": reason,
            "counterexample_traits": {
                k: sorted(set(str(x) for x in v))
                for k, v in counterexample_traits.items()
            },
            "repair": "NARROWED__ADDED_SEPARATING_TRAIT",
            "added_hole": added[0],
            "added_trait": added[1],
        })
        skill["refutations"] = refutations[-20:]
        return {
            "status": "NARROWED",
            "skill_id": skill_id,
            "added_hole": added[0],
            "added_trait": added[1],
            "required_hole_traits": required,
        }

    # No observable separates the positive support from the counterexample -> fail closed
    skill["status"] = STATUS_QUARANTINED
    refutations.append({
        "reason": reason,
        "counterexample_traits": {
            k: sorted(set(str(x) for x in v))
            for k, v in counterexample_traits.items()
        },
        "repair": "QUARANTINED__NO_SEPARATING_OBSERVABLE",
    })
    skill["refutations"] = refutations[-20:]
    return {"status": "QUARANTINED", "skill_id": skill_id}


# ---------------------------------------------------------------------------
# Multi-statement block skills (mode "blk") — tree-rewrite morphisms
# ---------------------------------------------------------------------------

def _iter_stmt_lists(root: ast.AST) -> Iterable[list[ast.stmt]]:
    """Yield every statement list appearing as a body/orelse/finalbody field."""
    for node in ast.walk(root):
        for field_name in ("body", "orelse", "finalbody"):
            sub = getattr(node, field_name, None)
            if (
                isinstance(sub, list)
                and sub
                and all(isinstance(x, ast.stmt) for x in sub)
            ):
                yield sub


def propose_block_skills(
    store: Mapping[str, Any],
    target_tree: ast.AST,
    *,
    site_lineno: int,
    expr_traits: Mapping[str, Sequence[str]] | None = None,
    exception_type: str = "",
) -> list[dict[str, Any]]:
    """Propose multi-statement block rewrites anchored at ``site_lineno``.

    Slides a contiguous window of statements over every statement list in
    ``target_tree``. Any window whose structural skeleton unifies with an
    admitted block skill's before-pattern yields an instantiated after-block
    splice. The window must CONTAIN ``site_lineno`` (fail-closed anchoring:
    no site, no proposal).

    Returns dicts with ``node`` (list of new stmts, deepcopied and located),
    ``code`` (unparsed after-block), ``span`` = (start_lineno, end_lineno,
    window_code, window_len) for the engine-side splice, ``bound_holes`` and
    ``bound_traits``.
    """
    skills = [
        s
        for s in (store.get("skills") or {}).values()
        if s.get("mode") == "blk" and s.get("status") != STATUS_QUARANTINED
    ]
    if not skills:
        return []

    proposals: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    ordered_skills = sorted(
        skills,
        key=lambda s: (
            s.get("status") == STATUS_NARROWED,
            int(s.get("support_count", 0)),
            len(s.get("required_hole_traits") or {}),
        ),
        reverse=True,
    )

    for skill in ordered_skills:
        exc_hint = str(skill.get("exception_type_hint") or "")
        if exc_hint and exception_type and exc_hint != exception_type:
            if exc_hint != "AssertionError":
                continue
        try:
            b_pat = _parse_fragment(skill["before_pattern"], "blk")
            a_pat = _parse_fragment(skill["after_pattern"], "blk")
        except (SyntaxError, SkillStoreError):
            continue
        window_len = len(b_pat.body)
        req_traits = skill.get("required_hole_traits") or {}

        for stmt_list in _iter_stmt_lists(target_tree):
            if len(stmt_list) < window_len:
                continue
            for i in range(len(stmt_list) - window_len + 1):
                window = stmt_list[i : i + window_len]
                start_ln = int(getattr(window[0], "lineno", 0) or 0)
                end_ln = int(
                    getattr(window[-1], "end_lineno", getattr(window[-1], "lineno", 0)) or 0
                )
                if not (start_ln <= int(site_lineno) <= end_ln):
                    continue
                b_mod = ast.Module(
                    body=[copy.deepcopy(s) for s in window], type_ignores=[]
                )
                ast.fix_missing_locations(b_mod)
                pat_locals = [str(x) for x in (skill.get("alpha_locals") or [])]
                alpha_map: dict[str, str] = {}
                if pat_locals:
                    tgt_locals = _private_local_names(b_mod, target_tree)
                    if len(tgt_locals) == len(pat_locals):
                        alpha_map = dict(zip(tgt_locals, pat_locals))
                        # Refuse a rename that would capture a name the window
                        # already reads without binding it itself.
                        free_ids = {
                            n.id
                            for n in ast.walk(b_mod)
                            if isinstance(n, ast.Name)
                            and n.id not in tgt_locals
                        }
                        if free_ids & set(pat_locals):
                            alpha_map = {}
                unify_src = (
                    _alpha_rename(b_mod, alpha_map) if alpha_map else b_mod
                )
                env: dict[str, ast.AST] = {}
                if not _unify_ast(b_pat, unify_src, env):
                    continue
                # De novo (after-only) holes have no before-side occurrence to
                # bind: project them from the already-bound subtrees, and refuse
                # the proposal if any hole stays unbound (fail closed).
                _project_missing_holes(env, skill.get("hole_to_orig") or {}, b_mod)
                if _holes_of(a_pat) - env.keys():
                    continue
                # Check runtime preconditions on bound holes. Trait keys are
                # read in TARGET space, so undo the alpha-rename for lookups.
                _inv_alpha = {v: k for k, v in alpha_map.items()}
                precondition_ok = True
                bound_traits: dict[str, list[str]] = {}
                for hid, bound_ast in env.items():
                    if _inv_alpha:
                        bound_ast = _alpha_rename(bound_ast, _inv_alpha)
                    unparsed = ast.unparse(bound_ast)
                    observed = set(str(t) for t in (expr_traits or {}).get(unparsed, ()))
                    bound_traits[hid] = sorted(observed)
                    needed = set(str(t) for t in req_traits.get(hid, ()))
                    if needed and not needed.issubset(observed):
                        precondition_ok = False
                        break
                if not precondition_ok:
                    continue
                inst = _instantiate_ast(a_pat, env)
                if alpha_map:
                    inst = _alpha_rename(inst, {v: k for k, v in alpha_map.items()})
                new_stmts = list(inst.body)
                inst_code = ast.unparse(inst)
                window_code = ast.unparse(b_mod)
                if inst_code == window_code:
                    continue
                sig = hashlib.sha256(inst_code.encode("utf-8")).hexdigest()[:16]
                key = f"{skill['skill_id']}:{start_ln}:{sig}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                proposals.append({
                    "skill_id": skill["skill_id"],
                    "node": new_stmts,
                    "code": inst_code,
                    "span": (start_ln, end_ln, window_code, window_len),
                    "bound_holes": {
                        k: ast.unparse(_alpha_rename(v, _inv_alpha) if _inv_alpha else v)
                        for k, v in env.items()
                    },
                    "bound_traits": bound_traits,
                })
    return proposals

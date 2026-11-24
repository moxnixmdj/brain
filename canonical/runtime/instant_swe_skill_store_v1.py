"""External, inspectable, editable, deletable structural SWE repair-skill store.

Zero weights, zero model calls, zero memorized world facts inside parameters.
Knowledge lives strictly outside parameters in plain JSON and can be inspected,
edited, or deleted without retraining.

How one verified experience becomes a portable cross-repo skill:
  1. Given ONE verified (before_source, after_source, failure_context) repair,
     locate the smallest changed AST node pair (expression OR statement).
  2. Alpha-canonicalize all local/bound names and shared subtrees into typed
     holes ($H0, $H1, ...) while preserving Python operators, structural AST
     forms, and built-in/constant tokens. Any foreign repo-specific identifier
     that does not appear in the before pattern is refused at admission time
     (preventing the foreign-name grafting defect measured in real_commit_repair_v1).
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
    mod = ast.parse(code, mode="exec")
    if len(mod.body) != 1:
        raise SkillStoreError("FRAGMENT_MUST_BE_SINGLE_NODE")
    return mod.body[0]


def _smallest_changed_pair(
    before_source: str,
    after_source: str,
) -> tuple[ast.AST, ast.AST, str] | None:
    """Find the smallest single changed AST node pair (expr or stmt)."""
    try:
        b_tree = ast.parse(before_source)
        a_tree = ast.parse(after_source)
    except SyntaxError:
        return None

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
    found = _smallest_changed_pair(before_source, after_source)
    if found is None:
        return None
    b_node, a_node, mode = found
    abstracted = _abstract_pair(b_node, a_node)
    if abstracted is None:
        return None
    b_pat, a_pat, hole_to_orig, hole_to_kind = abstracted

    # Round-trip admission check: pattern MUST unify with b_node and instantiate a_node
    env: dict[str, ast.AST] = {}
    if not _unify_ast(b_pat, b_node, env):
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

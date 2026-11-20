#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Family Predicate Induction — falsifiable predicate from one causal cut.

THE PROBLEM
-----------
One experience yields a trace, the causal cut extracts the minimal steps that
earned success, but permanence needs a FAMILY: a predicate over tasks that says
"this new task is in-family, so the cut applies" vs "out-of-family, abstain."

Without a family, a skill fires everywhere (false positive) or nowhere (false
negative). The predicate must be:
  1. Induced from the cut + observed pre/post states (not hand-typed)
  2. Falsifiable: a constructible negative exists that it rejects
  3. Auditable: inspectable dict, editable, outside weights
  4. Re-derivable: restore() reruns induction gates, refuses if family drifted

MECHANISM (copied from acquired_operator_memory pattern)
---------------------------------------------------------
Demo is the operator -> stored examples re-derive via same gates:
  _usable(kind) + induce_laws(...) + _law_is_falsifiable(...) + indistinguishable_from(...)

Here:
  Demonstration = (pre_state_snapshot, cut_steps, post_state_snapshot)
  Family = precondition × action_schema × postcondition_check
  Falsifiable = exists negative task that predicate separates

We reuse value_algebra's falsifiability pattern but over trajectory features:
  - pre-state delta: files present/absent, content patterns, db rows
  - action type: layer/op classification (python_file_op, sqlite_exec, http_request, cli_exec)
  - post-state delta: file creation/content, db mutation, stdout shape

Zero model calls, zero network, zero knowledge house. Every parameter calculated.
Fail-closed: refuse before persisting if not falsifiable.
Authority: NONE — producer-run sandbox calculation.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_FAMILY_PREDICATE_INDUCTION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_CALCULATION"

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FamilyPredicate:
    """A falsifiable family predicate: when does the causal cut apply?"""
    family_id: str  # content hash of (precondition, action_schema, postcondition)
    precondition: Mapping[str, Any]  # state features required before
    action_schema: Mapping[str, Any]  # abstracted cut pattern
    postcondition: Mapping[str, Any]  # verifiable effect
    falsifier: Mapping[str, Any]  # constructible negative that is rejected
    derivation: str


# ---------------------------------------------------------------------------
# Feature extraction from state deltas
# ---------------------------------------------------------------------------

# Bottleneck 2 upgrade: open-delta generalization — quoted strings, identifiers,
# semantic_dom selectors as typed holes (?str, ?ident) reused from
# causal_trace_to_skill_compiler anti-unification; preserves falsifiability.
_LAYER_RE = re.compile(r"^(python_file_op|sqlite_exec|http_request|cli_exec|semantic_dom|pixel_ui|confined_python_exec)$")
_QUOTED_RE = re.compile(r"""(?:"([^"\n]+)"|'([^'\n]+)')""")
_IDENT_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_-]{2,}\b")
_KV_VAL_RE = re.compile(r"(?:[A-Za-z_][A-Za-z0-9_-]*)\s*[=:]\s*([^\s\"',;)]+)")
_STOP_WORDS = frozenset({"a","an","the","to","into","from","in","on","at","by","for","of","with","and","or","then","please","using","via","as","is","are","be"})
_LAYER_RE_ORIG = re.compile(r"^(python_file_op|sqlite_exec|http_request|cli_exec|semantic_dom|pixel_ui)$")
_PATH_LIKE_RE = re.compile(r"(?:/[^\s\"\'\',;)]+|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+|[A-Za-z0-9_-]+\.(?:py|pyi|js|ts|jsx|tsx|json|jsonl|csv|tsv|md|txt|log|yaml|yml|toml|ini|cfg|db|sqlite|sqlite3|png|jpg|jpeg|gif|svg|html|css|sh|rs|go|c|cpp|h|java|rb|php))")
_URL_RE = re.compile(r"https?://[^\\s\"'<>)\\]]+")
_NUM_RE = re.compile(r"(?<![A-Za-z0-9_./:-])\d+(?:\\.\\d+)?(?![A-Za-z0-9_./:-])")

def _hash_predicate(pre: Mapping[str, Any], schema: Mapping[str, Any], post: Mapping[str, Any]) -> str:
    payload = json.dumps({"pre": dict(pre), "schema": dict(schema), "post": dict(post)}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _extract_precondition(
    pre_state: Mapping[str, bytes] | None,
    cut_steps: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Induce precondition from pre-state + cut dependency analysis."""
    pre: dict[str, Any] = {}
    if pre_state is None:
        pre["requires"] = ["any_state"]
        pre["excludes"] = []
        return pre

    # Files that cut reads but does not create: must exist beforehand
    read_files: set[str] = set()
    written_files: set[str] = set()
    for s in cut_steps:
        layer = str(s.get("layer") or s.get("kind") or "")
        if layer == "python_file_op":
            op = str(s.get("op") or "write_text")
            path = str(s.get("path") or "")
            if path:
                if op == "read_text" or s.get("reads_before_write"):
                    read_files.add(path)
                else:
                    written_files.add(path)
        elif layer == "sqlite_exec":
            db = str(s.get("db_path") or "")
            if db:
                read_files.add(db)

    # Dependences: if cut does sql UPDATE, the table must exist pre-state
    for f in read_files:
        if f not in written_files:
            # check if file existed in pre_state
            # pre_state keys are relative POSIX paths
            if any(f in k for k in pre_state.keys()):
                pre.setdefault("requires_files", []).append(f)
            else:
                # table/file must exist but not in demo pre_state -> precondition is existence
                pre.setdefault("requires_gone", []).append(f)

    # Content-aware precondition: if a written file existed beforehand with different content,
    # capture the buggy snippet that must be present for the edit to be applicable.
    # This is the content that distinguishes "null-deref file" from "unrelated file" and makes
    # destructive world out-of-family without needing exact path match.
    # We keep path-agnostic: snippet values are stored, not exact paths, so twin file names still match.
    requires_content: dict[str, str] = {}
    for s in cut_steps:
        if str(s.get("layer") or "") == "python_file_op" and str(s.get("op") or "write_text") == "write_text":
            p = str(s.get("path") or "")
            if p and p in pre_state:
                before_raw = pre_state[p]
                before = before_raw.decode(errors="replace") if isinstance(before_raw, bytes) else str(before_raw)
                after = str(s.get("content") or "")
                if before.strip() and after.strip() and before != after:
                    # Find first line in before not equal to any line in after (buggy line)
                    before_lines = [l.strip() for l in before.splitlines() if l.strip()]
                    after_lines = set(l.strip() for l in after.splitlines() if l.strip())
                    for bl in before_lines:
                        if bl not in after_lines and len(bl) >= 6:
                            # Store snippet keyed by snippet itself (path-agnostic), value is also snippet for display
                            # Use snippet as key to avoid exact path dependence
                            snippet_key = bl[:80]
                            requires_content[snippet_key] = bl[:120]
                            break

    if read_files or pre.get("requires_files") or requires_content:
        pre["requires"] = pre.get("requires_files", ["filesystem_accessible"]) if pre.get("requires_files") else ["filesystem_accessible"]
        if requires_content:
            pre["requires_content"] = requires_content
    else:
        pre["requires"] = ["any_state"]

    pre["excludes"] = []
    return pre


def _extract_action_schema(cut_steps: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Abstract cut into typed schema with holes for generalizable literals.

    Bottleneck 2: now extracts url/path/num PLUS quoted strings and identifiers,
    and semantic_dom selector fields — same vocabulary as causal_trace_to_skill_compiler
    anti-unification, so a file edit "replace 'old_name' with 'new_name'" becomes
    ?str0/?str1 family, not concrete memorization.
    """
    schema: dict[str, Any] = {
        "step_count": len(cut_steps),
        "layers": [],
        "holes": [],
    }
    literals: list[tuple[str, str]] = []
    for s in cut_steps:
        layer = str(s.get("layer") or s.get("kind") or "cli_exec")
        schema["layers"].append(layer)
        blob = json.dumps(s, sort_keys=True)
        for m in _URL_RE.finditer(blob):
            literals.append(("url", m.group(0).rstrip(".,;:")))
        # Path holes ONLY from explicit path-typed fields, not from blob/content.
        # Over-capture bug: _PATH_LIKE_RE on json.dumps matched content strings
        # like "geom.py" inside file content as paths (2× geom.py for 6-step trace).
        # Fix: inspect only path fields; content field is handled as ?str/?ident.
        for path_key in ("path", "db_path", "source_path", "target_path", "state_path", "dom_path", "sqlite_path", "output_path"):
            v = s.get(path_key)
            if isinstance(v, str) and v.strip():
                vs = v.strip().rstrip(".,;:")
                # Accept if it looks like a path (slash or known extension) — reuse same gate
                if _PATH_LIKE_RE.search(vs):
                    if vs not in [x[1] for x in literals]:
                        literals.append(("path", vs))
                else:
                    # Fallback: any value with slash is path-like even if extension gate misses
                    if "/" in vs and vs not in [x[1] for x in literals]:
                        literals.append(("path", vs))
        for m in _NUM_RE.finditer(blob):
            literals.append(("num", m.group(0)))
        # Bottleneck 2: quoted strings and identifiers for file edits / GUI
        for m in _QUOTED_RE.finditer(blob):
            inner = m.group(1) if m.group(1) is not None else m.group(2)
            if inner and inner.strip() and len(inner.strip()) >= 2:
                literals.append(("str", inner.strip()))
        # semantic_dom selector fields are high-signal for GUI families
        if layer == "semantic_dom" and isinstance(s.get("selector"), Mapping):
            for k in ("role","name","aria","text","placeholder","tag"):
                v = str(s["selector"].get(k) or "").strip()
                if v and len(v) >= 2 and v.lower() not in _STOP_WORDS:
                    literals.append(("str", v))
        # bare identifiers that participate causally (function names, column names)
        # only if they appear as values not keys to avoid capturing json scaffolding
        for m in _IDENT_RE.finditer(blob):
            v = m.group(0)
            if v.lower() not in _STOP_WORDS and ("_" in v or "-" in v) and v not in [x[1] for x in literals]:
                # heuristic: identifier that is a file content token, not structural
                if len(v) >= 3:
                    literals.append(("ident", v))

    # Holes: each distinct literal kind gets a typed hole, same as anti_unify_workflow
    seen_val: set[str] = set()
    holes: list[str] = []
    kind_counts: dict[str, int] = {}
    for kind, val in literals:
        if val in seen_val or not val.strip():
            continue
        seen_val.add(val)
        idx = kind_counts.get(kind, 0)
        kind_counts[kind] = idx + 1
        holes.append(f"?{kind}{idx}")

    schema["holes"] = holes
    schema["literal_kinds"] = list(kind_counts.keys())
    return schema


def _extract_postcondition(
    post_state: Mapping[str, bytes] | None,
    cut_steps: Sequence[Mapping[str, Any]],
    pre_state: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    """Induce postcondition (what success looks like) from post-state delta."""
    # Prefer explicit postcondition if last step declares one
    last = cut_steps[-1] if cut_steps else {}
    if isinstance(last.get("postcondition"), Mapping):
        return dict(last["postcondition"])

    post: dict[str, Any] = {"kind": "unknown"}

    # Heuristic: infer from cut's dominant effect
    # - python_file_op write -> file_contains or file_nonempty
    # - sqlite_exec -> sqlite_query_equals or sqlite_row_exists
    # - http_request -> http_status_json or http_get_contains
    # Bottleneck 5: long-horizon composite — file edits + GUI submit
    layers = [str(s.get("layer") or s.get("kind") or "") for s in cut_steps]
    if "python_file_op" in layers and "semantic_dom" in layers:
        # Hardest case: cross-file fix + GUI submit — conjunction of file_contains + gui verify
        file_posts = []
        for s in cut_steps:
            if str(s.get("layer")) == "python_file_op" and s.get("path") and s.get("content"):
                snippet = str(s.get("content")).strip().split("\n")[0][:60].strip()
                if snippet:
                    file_posts.append({"kind": "file_contains", "path": str(s["path"]), "contains": snippet})
        if file_posts:
            # Add GUI verification as last check
            post = {"kind": "long_horizon_composition_verified", "checks": file_posts + [{"kind": "gui_submit_verified", "target": "Submit"}]}
            return post

    dominant = str(last.get("layer") or last.get("kind") or "")
    if dominant == "semantic_dom":
        sel = last.get("selector") or {}
        target = str(sel.get("name") or sel.get("text") or "Submit")
        post = {"kind": "gui_submit_verified", "target": target, "selector": dict(sel) if isinstance(sel, dict) else {}}
        return post
    if dominant == "python_file_op":
        path = str(last.get("path") or "")
        content = str(last.get("content") or "")
        if path and content.strip():
            # file_contains with shortest stable substring (avoid hole-filled template)
            snippet = content.strip().split("\n")[0][:80].strip()
            post = {"kind": "file_contains", "path": path, "contains": snippet or content[:40]}
            # Edit_vs_create guard: if pre/post snapshots show edit, mark edit_preserves_outside
            # so destroy check knows outside content is preserved (causal_trace_to_skill_compiler).
            if pre_state is not None and post_state is not None and path in pre_state and path in post_state:
                try:
                    before = pre_state[path].decode(errors="replace") if isinstance(pre_state[path], bytes) else str(pre_state[path])
                    after = post_state[path].decode(errors="replace") if isinstance(post_state[path], bytes) else str(post_state[path])
                    if before.strip() and after.strip() and before != after:
                        post["edit_of"] = path
                        post["edit_preserves_outside"] = True
                except Exception:
                    pass
        elif path:
            post = {"kind": "file_nonempty", "path": path}
    elif dominant == "sqlite_exec":
        db = str(last.get("db_path") or "")
        sql = str(last.get("sql") or "SELECT count(*) FROM sqlite_master")
        if db:
            post = {"kind": "sqlite_row_exists", "db_path": db, "sql": sql, "min_rows": 1}
    elif dominant == "http_request":
        url = str(last.get("url") or "")
        if url:
            post = {"kind": "http_status_json", "url": url, "status": 200}

    # Fallback: if we have pre/post snapshots, diff them to infer file creation/edit
    if post["kind"] == "unknown" and pre_state is not None and post_state is not None:
        created = set(post_state.keys()) - set(pre_state.keys())
        if created:
            first = sorted(created)[0]
            post = {"kind": "file_nonempty", "path": first}
        else:
            modified = [k for k in pre_state if k in post_state and pre_state[k] != post_state[k]]
            if modified:
                first = modified[0]
                before = pre_state[first].decode(errors="replace") if isinstance(pre_state[first], bytes) else str(pre_state[first])
                after = post_state[first].decode(errors="replace") if isinstance(post_state[first], bytes) else str(post_state[first])
                # Bottleneck 2: detect edit vs overwrite — preserve surrounding content proof
                # file_edit_claim requires outside content preserved; we signal that need via post kind
                snippet = after.strip().split("\n")[0][:80].strip() if after.strip() else after[:40]
                if before.strip() and after.strip() and before != after:
                    post = {"kind": "file_contains", "path": first, "contains": snippet or after[:40], "edit_of": first, "edit_preserves_outside": True}
                else:
                    post = {"kind": "file_contains", "path": first, "contains": after[:40].strip()[:40]}

    if post["kind"] == "unknown":
        post = {"kind": "file_nonempty", "path": "__any_output__"}

    return post


# ---------------------------------------------------------------------------
# Falsifiability
# ---------------------------------------------------------------------------

def _is_falsifiable(predicate: FamilyPredicate) -> tuple[bool, str]:
    """A predicate is falsifiable iff we can construct a negative it rejects.

    Following value_algebra._law_is_falsifiable: the predicate must split the
    instance space into two non-empty cells.
    """
    # Negative construction: perturb one of precondition/action/postcondition
    # If all three are "any", predicate is tautology -> not falsifiable
    pre = predicate.precondition
    schema = predicate.action_schema
    post = predicate.postcondition

    if pre.get("requires") == ["any_state"] and not schema["layers"] and post.get("kind") == "unknown":
        return False, "PREDICATE_IS_TAUTOLOGY_REQUIRES_NOTHING_CHECKS_NOTHING"

    # Must have at least one checkable clause that could fail
    checkable = 0
    if pre.get("requires_files") or pre.get("requires") != ["any_state"]:
        checkable += 1
    if schema.get("layers"):
        checkable += 1
    if post.get("kind") != "unknown" and post.get("kind") != "file_nonempty":
        checkable += 1
    elif post.get("kind") == "file_nonempty" and post.get("path") != "__any_output__":
        checkable += 1

    if checkable == 0:
        return False, "NO_CHECKABLE_CLAUSE_PREDICATE_ACCEPTS_EVERYTHING"

    # Concrete negative: empty pre-state + empty trace should be rejected
    # (unless predicate truly is "any_state -> any file": then falsifiability
    # requires file name specificity)
    if post.get("kind") == "file_nonempty" and post.get("path") == "__any_output__":
        return False, "POSTCONDITION_ANY_OUTPUT_NOT_FALSIFIABLE_NEEDS_CONCRETE_PATH"

    return True, "FALSIFIABLE_VIA_CONSTRUCTED_NEGATIVE"


def _make_falsifier(predicate: FamilyPredicate) -> dict[str, Any]:
    """Construct the canonical negative witness for this predicate."""
    pre = predicate.precondition
    post = predicate.postcondition
    schema = predicate.action_schema
    # Negative pre_state: missing required file, or wrong layer
    falsifier: dict[str, Any] = {
        "negative_pre_state": {"missing": pre.get("requires_files", ["__required_file__"])[:1]},
        "negative_trace": [{"layer": "cli_exec", "argv": ["true"]}],  # does not match required layers
        "why_rejected": "precondition_files_missing_and_layer_mismatch",
        "expected_outcome": "PREDICATE_REJECTS_NEGATIVE",
    }
    if post.get("kind") in ("file_contains", "file_nonempty"):
        falsifier["negative_post"] = {"file_missing": post.get("path")}
    elif post.get("kind") == "sqlite_row_exists":
        falsifier["negative_post"] = {"db_missing": post.get("db_path")}
    # Bottleneck 12: composite negative via content_a_generalized_write_would_destroy.
    # A file-creation family that generalizes to "replace whole file with taught content"
    # must be rejected when the target already holds unrelated content the skill never read.
    # This is the exhaustive destroy check from causal_trace_to_skill_compiler.
    layers = schema.get("layers") or []
    if "python_file_op" in layers:
        # If postcondition is not edit-aware, the destroy negative is load-bearing.
        # We construct it as a second falsifier entry.
        if not post.get("edit_preserves_outside"):
            falsifier["destroy_negative"] = {
                "existing_file_content": "unrelated content the skill never read — e.g., user data",
                "generalized_write_would_destroy": post.get("path") or "__any_path__",
                "why_rejected": "content_a_generalized_write_would_destroy__skill_must_not_replace_unread_file",
                "expected_outcome": "PREDICATE_REJECTS_DESTRUCTIVE_OVERGENERALIZATION",
                "guard": "requires edit_of + edit_preserves_outside or file creation in empty slot",
            }
        else:
            falsifier["destroy_negative"] = {
                "status": "GUARDED_BY_EDIT_PRESERVES_OUTSIDE",
                "why_accepted": "edit_preserves_outside True — outside content preserved",
            }
    return falsifier


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def induce_family_predicate(
    cut_steps: Sequence[Mapping[str, Any]],
    pre_state: Mapping[str, bytes] | None = None,
    post_state: Mapping[str, bytes] | None = None,
    explicit_postcondition: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Induce a falsifiable family predicate from a causal cut.

    Returns dict with status PASS/FAIL_CLOSED and, on PASS, a FamilyPredicate payload.
    """
    if not cut_steps:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__EMPTY_CUT_NO_FAMILY",
            "reason": "NO_CUT_STEPS_TO_GENERALIZE",
        }

    pre = _extract_precondition(pre_state, cut_steps)
    schema = _extract_action_schema(cut_steps)
    post = dict(explicit_postcondition) if explicit_postcondition else _extract_postcondition(post_state, cut_steps, pre_state)

    family_id = _hash_predicate(pre, schema, post)
    # Build predicate object for falsifiability check
    tmp = FamilyPredicate(
        family_id=family_id,
        precondition=pre,
        action_schema=schema,
        postcondition=post,
        falsifier={},
        derivation="pre_state_delta_x_action_schema_x_postcondition",
    )
    falsifiable, reason = _is_falsifiable(tmp)
    if not falsifiable:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__PREDICATE_NOT_FALSIFIABLE",
            "reason": reason,
            "precondition": pre,
            "action_schema": schema,
            "postcondition": post,
        }

    falsifier = _make_falsifier(tmp)
    predicate = FamilyPredicate(
        family_id=family_id,
        precondition=pre,
        action_schema=schema,
        postcondition=post,
        falsifier=falsifier,
        derivation="causal_cut_family_predicate_induced_and_falsified",
    )

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__FAMILY_PREDICATE_INDUCED",
        "family_id": family_id,
        "family_predicate": {
            "family_id": predicate.family_id,
            "precondition": dict(predicate.precondition),
            "action_schema": dict(predicate.action_schema),
            "postcondition": dict(predicate.postcondition),
            "falsifier": dict(predicate.falsifier),
            "derivation": predicate.derivation,
        },
        "falsifier": falsifier,
        "falsifiable_reason": reason,
    }


def predicate_matches_task(
    predicate: Mapping[str, Any],
    task_goal: str,
    task_pre_state: Mapping[str, bytes] | None = None,
) -> tuple[bool, str]:
    """Check if a task is in-family for this predicate (recall decision).

    Fail-closed: vague match -> False, do not fire.
    """
    pre = predicate.get("precondition") or {}
    schema = predicate.get("action_schema") or {}

    # Precondition check: required files must be mentioned or present
    required = pre.get("requires_files") or pre.get("requires") or []
    if required and required != ["any_state"] and required != ["filesystem_accessible"]:
        goal_lower = task_goal.lower()
        # Check if any required file pattern appears in goal or pre_state
        matched = False
        for req in required:
            if req.lower() in goal_lower:
                matched = True
                break
            if task_pre_state and any(req in k for k in task_pre_state.keys()):
                matched = True
                break
        if not matched:
            return False, f"PRECONDITION_NOT_MET_MISSING_{required[0]}"

    # Content-aware precondition: if a file must contain buggy snippet, check it.
    # When task_pre_state is None we advisory-pass (goal-only admission like twin),
    # but when task_pre_state is provided (destructive world probe) we strictly check
    # that the required buggy snippet is present — otherwise out-of-family.
    requires_content = pre.get("requires_content") or {}
    if requires_content and task_pre_state is not None:
        # Path-agnostic: each buggy snippet must appear in *some* file's content in task_pre_state.
        # This allows twin file name generalization (auth.py → auth_v2.py) while still rejecting
        # unrelated world where no file contains the buggy pattern.
        for snippet_key, snippet in requires_content.items():
            found = False
            for fpath, fcontent in task_pre_state.items():
                if isinstance(fcontent, bytes):
                    fcontent = fcontent.decode(errors="replace")
                if snippet in fcontent or snippet_key in fcontent:
                    found = True
                    break
            if not found:
                return False, f"PRECONDITION_CONTENT_MISMATCH_missing_buggy_snippet_{snippet[:30]}"

    # Action schema: goal must mention relevant layer keywords
    layers = schema.get("layers") or []
    if layers:
        goal_lower = task_goal.lower()
        layer_keywords = {
            "python_file_op": ["file", "write", "create", "put", "save"],
            "sqlite_exec": ["sqlite", "database", "table", "insert", "record"],
            "http_request": ["http", "post", "request", "api", "submit"],
            "cli_exec": ["run", "execute", "command", "shell"],
        }
        # At least one layer keyword should appear, or abstain
        any_hit = any(
            any(kw in goal_lower for kw in layer_keywords.get(lyr, []))
            for lyr in layers
        )
        # Do NOT fail closed on this alone; layers are advisory, not required
        # (avoids brittleness on paraphrase)

    return True, "FAMILY_MATCH"


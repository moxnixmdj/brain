#!/usr/bin/env python3
"""IR Bridge — makes the crystallizer understand meaning, not spelling.

Problem: verified_skill_crystallizer stores `__CST_ID0__` token skeletons. A rule
learned from `for i in range(n): x+=1` never fires on `while i<n: x+=1; i+=1`
even though both are the same Loop. Iteration 70: 5 bugs → 5 hand-written
C/C++ rules — rule accumulation, not understanding.

Solution: one minimal wire that stores a *canonical* IR hash alongside the
existing token pattern. Matching tries semantic IR first; token fallback
preserved for backward compatibility. Zero model calls, $0, deterministic.

What this does:
  - canonical_ir(source, lang): α-renames vars to V0,V1… + desugars while-counter
    patterns to Loop(init=0,end=n,step=1). Both for and while → identical hash.
  - enrich_rule_with_ir(rule, before, after): adds ir_hash_before/after + semantic kind
  - ir_matches(rule, target_source): true if canonical hashes equal → semantic fire
  - crystallize_with_ir(...): wraps anti_unify_code_rule, enriches, stores

Best part is no part: no new table, no second memory, just one JSON field per
rule. When IR matching proves superior on held-out victims, token fallback can
be deleted — not now.

Refs: UAST O(|AST|) desugaring (Wang 2026), CrossTL O(n) IR (universal type
system), semantic_unification probe equivalence, deep_understanding_engine IR.
"""
from __future__ import annotations

import hashlib
import json
import re
import ast
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_IR_BRIDGE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_CALCULATION"

# Reuse deep engine's IR where possible
try:
    from canonical.swe_kernel.deep_understanding_engine_v1 import (
        normalize_to_ir as _d_normalize,
        IRNode as _IRNode,
        ir_hash as _ir_hash_raw,
    )
    HAS_DEEP = True
except Exception:
    HAS_DEEP = False


def _collect_var_names(d: Any, out: set[str]) -> None:
    if isinstance(d, dict):
        for k, v in d.items():
            if k in ("var", "targets", "name", "func") and isinstance(v, str):
                for part in v.split(","):
                    part = part.strip()
                    if re.match(r"^[A-Za-z_]\w*$", part):
                        out.add(part)
            elif k not in ("value", "cond", "init", "end", "step", "raw", "op"):
                _collect_var_names(v, out)
            else:
                # value/cond strings may contain vars, but we collect separately
                pass
        for v in d.values():
            _collect_var_names(v, out)
    elif isinstance(d, list):
        for x in d:
            _collect_var_names(x, out)

def _alpha_rename_ir_dict(d: Any, var_map: dict[str, str], counter: list[int]) -> Any:
    """Recursively replace var names in IR dict with canonical V0,V1… — only known vars."""
    if isinstance(d, dict):
        out = {}
        for k, v in d.items():
            if k in ("var", "targets", "name", "func") and isinstance(v, str) and re.match(r"^[A-Za-z_]\w*$", v):
                if "," in v:
                    parts = [p.strip() for p in v.split(",")]
                    canon = []
                    for p in parts:
                        if p not in var_map:
                            var_map[p] = f"V{counter[0]}"
                            counter[0] += 1
                        canon.append(var_map[p])
                    out[k] = ",".join(canon)
                else:
                    if v not in var_map:
                        var_map[v] = f"V{counter[0]}"
                        counter[0] += 1
                    out[k] = var_map[v]
            elif k in ("value", "cond", "init", "end", "step") and isinstance(v, str):
                # Only replace identifiers that are known vars; leave operators/consts
                def repl(m):
                    name = m.group(0)
                    if name in var_map:
                        return var_map[name]
                    if name.isdigit() or name in ("and", "or", "not", "in", "range", "len", "True", "False", "None", "Add", "Sub", "Mult", "Div", "Mod"):
                        return name
                    # Unknown single-letter likely a var missed in collection — map it
                    if re.match(r"^[A-Za-z_]\w*$", name) and len(name) <= 3:
                        if name not in var_map:
                            var_map[name] = f"V{counter[0]}"
                            counter[0] += 1
                        return var_map[name]
                    return name
                out[k] = re.sub(r"\b[A-Za-z_]\w*\b", repl, v)
            else:
                out[k] = _alpha_rename_ir_dict(v, var_map, counter)
        return out
    if isinstance(d, list):
        return [_alpha_rename_ir_dict(x, var_map, counter) for x in d]
    return d

def _normalize_loop_op(d: Any) -> Any:
    """Ensure Loop attrs have canonical op field: for-range → op='<'"""
    if isinstance(d, dict):
        if d.get("kind") == "Loop":
            attrs = dict(d.get("attrs") or {})
            if "op" not in attrs:
                # for-range canonical is < ; preserve step/init/end
                attrs["op"] = "<"
                d = dict(d)
                d["attrs"] = attrs
            # remove desugaring marker for hash equality
            if "desugared_from_while" in attrs:
                attrs = dict(attrs)
                attrs.pop("desugared_from_while", None)
                d = dict(d)
                d["attrs"] = attrs
        # recurse
        out = {}
        for k, v in d.items():
            out[k] = _normalize_loop_op(v)
        return out
    if isinstance(d, list):
        return [_normalize_loop_op(x) for x in d]
    return d


def _desugar_while_counter(ir_dict: dict[str, Any]) -> dict[str, Any]:
    """If Module = [Assign(V0=0), Loop(cond=V0<n, body=[..., V0+=1])] → Loop(init=0,end=n,step=1)"""
    if ir_dict.get("kind") != "Module":
        return ir_dict
    children = list(ir_dict.get("children") or [])
    if len(children) < 2:
        return ir_dict
    # Pattern: first child Assign targets=V0 value=0, second child Loop while_form with cond V0<...
    first = children[0]
    second = children[1]
    if first.get("kind") != "Assign":
        return ir_dict
    if second.get("kind") != "Loop" or not second.get("attrs", {}).get("while_form"):
        return ir_dict
    init_val = first.get("attrs", {}).get("value", "")
    if init_val.strip() not in ("0", "0.0"):
        return ir_dict
    var = first.get("attrs", {}).get("targets", "")
    cond = second.get("attrs", {}).get("cond", "")
    # cond like "V0 < V1" or "i < n" (before rename, but after rename it's V0 < V1)
    # After alpha rename, var is already V0, cond contains V0
    body = list(second.get("children") or [])
    if not body:
        return ir_dict
    last = body[-1]
    # last should be Assign targets=V0 value=V0 Add 1 (or V0+1)
    if last.get("kind") != "Assign":
        return ir_dict
    last_targets = last.get("attrs", {}).get("targets", "")
    last_value = last.get("attrs", {}).get("value", "")
    if last_targets != var:
        return ir_dict
    if var not in last_value:
        return ir_dict
    # Extract end from cond: "V0 < V1" → end=V1, op=<
    m = re.match(r"\s*(\w+)\s*([<>=!]+)\s*(\w+)\s*", cond)
    if not m:
        return ir_dict
    lhs, op, rhs = m.groups()
    if lhs != var:
        return ir_dict
    # Desugar to canonical Loop
    new_loop = {
        "kind": "Loop",
        "attrs": {"var": var, "init": init_val.strip(), "end": rhs.strip(), "op": op.strip(), "step": "1", "desugared_from_while": True},
        "children": body[:-1],  # body without final increment
    }
    return {"kind": "Module", "attrs": ir_dict.get("attrs", {}), "children": [new_loop]}


def canonical_ir(source: str, language: str = "python") -> dict[str, Any]:
    """Deterministic canonical IR: desugar + α-rename + op-normalize. Hash is semantic identity."""
    if HAS_DEEP:
        ir_node = _d_normalize(source, language)
        d = ir_node.to_dict()
    else:
        try:
            tree = ast.parse(source)
            d = {"kind": "Module", "attrs": {}, "children": [{"kind": type(n).__name__, "attrs": {}} for n in tree.body]}
        except Exception:
            d = {"kind": "Module", "attrs": {}, "children": []}
    d = _desugar_while_counter(d)
    # Normalize Loop op field before rename so for and while desugared to same
    d = _normalize_loop_op(d)
    # Collect vars then alpha rename
    var_names: set[str] = set()
    _collect_var_names(d, var_names)
    var_map: dict[str, str] = {}
    counter = [0]
    # Pre-populate map with collected vars in sorted order for determinism
    for name in sorted(var_names):
        var_map[name] = f"V{counter[0]}"
        counter[0] += 1
    d = _alpha_rename_ir_dict(d, var_map, counter)
    return d


def canonical_hash(source: str, language: str = "python") -> str:
    d = canonical_ir(source, language)
    blob = json.dumps(d, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def enrich_rule_with_ir(rule: Mapping[str, Any], before_snippet: str, after_snippet: str, language: str = "python") -> dict[str, Any]:
    """Add ir_hash fields to an existing rule dict. Pure, no I/O."""
    enriched = dict(rule)
    try:
        enriched["ir_hash_before"] = canonical_hash(before_snippet, language)
        enriched["ir_hash_after"] = canonical_hash(after_snippet, language)
        enriched["ir_canonical_before"] = canonical_ir(before_snippet, language)
        enriched["ir_canonical_after"] = canonical_ir(after_snippet, language)
        enriched["ir_bridge_schema"] = SCHEMA
    except Exception:
        enriched["ir_hash_before"] = None
        enriched["ir_hash_after"] = None
    return enriched


def ir_matches(rule: Mapping[str, Any], target_source: str, language: str = "python") -> bool:
    """Does target_source mean the same thing as rule's before? Canonical hash equality."""
    want = rule.get("ir_hash_before")
    if not want:
        return False
    try:
        have = canonical_hash(target_source, language)
        return have == want
    except Exception:
        return False


def crystallize_with_ir(*, before_snippet: str, after_snippet: str, language: str = "python", error_class: str = "GENERIC") -> dict[str, Any] | None:
    """One-call: anti_unify + enrich with IR. Returns enriched rule or None."""
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import anti_unify_code_rule
    rule = anti_unify_code_rule(before_snippet, after_snippet, language=language, error_class=error_class)
    if rule is None:
        return None
    return enrich_rule_with_ir(rule, before_snippet, after_snippet, language)


# Quick self-check used by tests
def for_while_same_ir() -> dict[str, Any]:
    py_for = "for i in range(n):\n    x += 1"
    py_while = "i = 0\nwhile i < n:\n    x += 1\n    i += 1"
    h_for = canonical_hash(py_for, "python")
    h_while = canonical_hash(py_while, "python")
    return {"for_hash": h_for, "while_hash": h_while, "equal": h_for == h_while,
            "for_ir": canonical_ir(py_for, "python"), "while_ir": canonical_ir(py_while, "python")}

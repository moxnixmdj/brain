#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Causal Cut Store — external inspectable editable persistence for induced families.

DESIGN LAW
----------
- Weights hold only mechanisms (how to cut, how to induce predicate).
- Knowledge lives OUTSIDE weights in this JSON bundle, add/remove without retraining.
- Store is re-derivable: restore() reruns family induction gates; failed rows reported not trusted.
- Mirrors acquired_operator_memory_v1 teach/recall/restore but for trajectory families.

File: canonical/astra_runtime/causal_cuts/CAUSAL_CUTS_V1.json
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = "canonical/astra_runtime/causal_cuts/CAUSAL_CUTS_V1.json"

_SCHEMA = "PROJECT_BRAIN_CAUSAL_CUT_STORE_V1"
_CACHE: dict[str, dict] = {}

def _path(path: str | None = None) -> Path:
    return ROOT / (path or DEFAULT_PATH)

def _load(path: str | None = None) -> dict:
    key = str(path or DEFAULT_PATH)
    if key in _CACHE:
        return _CACHE[key]
    p = _path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    data.setdefault("cuts", {})
    data.setdefault("schema", _SCHEMA)
    _CACHE[key] = data
    return data

def _save(data: dict, path: str | None = None) -> None:
    p = _path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, p)
    _CACHE[str(path or DEFAULT_PATH)] = data

def store_cut(
    family_id: str,
    goal: str,
    minimal_trace: Sequence[Mapping[str, Any]],
    kept_indices: Sequence[int],
    original_len: int,
    family_predicate: Mapping[str, Any],
    cut_receipt: Mapping[str, Any],
    *,
    path: str | None = None,
    pre_state: Mapping[str, bytes] | None = None,
    post_state: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    """Persist a cut+family outside weights. Returns receipt."""
    data = _load(path)
    # Serialize pre/post snapshots as utf-8 strings for restore (if provided) — needed for content-aware families
    # that require buggy snippet precondition; without this restore would re-derive different family_id.
    pre_ser = None
    post_ser = None
    if pre_state is not None:
        try:
            pre_ser = {k: (v.decode(errors="replace") if isinstance(v, bytes) else str(v)) for k, v in pre_state.items()}
        except Exception:
            pre_ser = None
    if post_state is not None:
        try:
            post_ser = {k: (v.decode(errors="replace") if isinstance(v, bytes) else str(v)) for k, v in post_state.items()}
        except Exception:
            post_ser = None
    data["cuts"][str(family_id)] = {
        "family_id": str(family_id),
        "goal": str(goal),
        "minimal_trace": list(minimal_trace),
        "kept_indices": list(kept_indices),
        "original_len": int(original_len),
        "minimal_len": len(list(minimal_trace)),
        "family_predicate": dict(family_predicate),
        "cut_receipt": dict(cut_receipt),
        "pruned_count": int(original_len) - len(list(minimal_trace)),
        "pre_state": pre_ser,
        "post_state": post_ser,
    }
    data["schema"] = _SCHEMA
    _save(data, path)
    return {"stored": True, "family_id": str(family_id), "store_path": str(_path(path)), "total_cuts": len(data["cuts"])}

def recall(path: str | None = None) -> list[dict[str, Any]]:
    d = _load(path)
    return [dict(v) for v in d.get("cuts", {}).values()]

def get(family_id: str, path: str | None = None) -> dict[str, Any] | None:
    d = _load(path)
    return d.get("cuts", {}).get(str(family_id))

def remove(family_id: str, path: str | None = None) -> dict[str, Any]:
    d = _load(path)
    if str(family_id) in d.get("cuts", {}):
        del d["cuts"][str(family_id)]
        _save(d, path)
        return {"removed": True, "family_id": str(family_id)}
    return {"removed": False, "reason": "NOT_FOUND"}

def restore(path: str | None = None) -> dict[str, Any]:
    """Re-derive every stored cut's family predicate; report failures (not trusted)."""
    from canonical.swe_kernel import family_predicate_induction_v1 as F
    restored, failed = [], []
    for row in recall(path):
        try:
            pre_ser = row.get("pre_state")
            post_ser = row.get("post_state")
            pre_state = {k: v.encode() for k, v in pre_ser.items()} if isinstance(pre_ser, dict) else None
            post_state = {k: v.encode() for k, v in post_ser.items()} if isinstance(post_ser, dict) else None
            check = F.induce_family_predicate(
                row.get("minimal_trace") or [],
                pre_state=pre_state,
                post_state=post_state,
                explicit_postcondition=(row.get("family_predicate") or {}).get("postcondition"),
            )
            if check.get("pass") and check.get("family_id") == row.get("family_id"):
                restored.append(row["family_id"])
            else:
                failed.append({"family_id": row.get("family_id"), "why": check.get("reason") or check.get("status")})
        except Exception as exc:
            failed.append({"family_id": row.get("family_id"), "why": f"{type(exc).__name__}: {exc}"})
    return {"restored": restored, "failed": failed, "total": len(recall(path))}

def clear_cache():
    _CACHE.clear()

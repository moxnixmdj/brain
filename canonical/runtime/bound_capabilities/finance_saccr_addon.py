#!/usr/bin/env python3
"""Basel SA-CCR credit asset-class add-on from a portfolio trades file.

Thin live binding over the Brain-owned kernel
``canonical/runtime/saccr_credit_kernel.py`` (measured 2000/2000 fresh
instances, 5 oracles, TB4 canary hit; see
``canonical/capabilities/true/specs/SACCR_CREDIT_ADDON_V1.json``).  This
adapter owns no math: it validates the input shape, requires the one
field that discriminates the kernel's declared scope (an explicit
``credit_rating`` per trade, so a non-credit trade can never be silently
priced as credit), calls ``solve_instance``, and writes the add-on plus
the kernel's per-trade intermediate trace.

Scope is NARROWER than the kernel's (explicit rating required); every
input this adapter accepts is inside the kernel's measured input class,
so the kernel's receipt stays valid for this route.  Everything outside
fails closed with a SACCR_* reason; nothing is guessed.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib

from canonical.runtime import saccr_credit_kernel

STATUS = "CREDIT_ADDON_COMPUTED"


def _safe(root, raw, require_file=False):
    root = pathlib.Path(root).resolve()
    p = (root / str(raw or "")).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if require_file and not p.is_file():
        raise RuntimeError("SACCR_TRADES_INPUT_MISSING")
    return p


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _checked_trades(data):
    if not isinstance(data, dict) or not isinstance(data.get("trades"), list) or not data["trades"]:
        raise RuntimeError("SACCR_INPUT_SHAPE_REJECTED:need {\"trades\": [non-empty]}")
    if len(data["trades"]) > 64:
        raise RuntimeError("SACCR_INPUT_SHAPE_REJECTED:too many trades")
    trades = []
    for i, t in enumerate(data["trades"]):
        if not isinstance(t, dict):
            raise RuntimeError(f"SACCR_INPUT_SHAPE_REJECTED:trade[{i}] not an object")
        for key in ("notional", "start", "end"):
            if not _is_num(t.get(key)):
                raise RuntimeError(f"SACCR_INPUT_SHAPE_REJECTED:trade[{i}].{key} must be a finite number")
        rating = t.get("credit_rating")
        if not isinstance(rating, str) or not rating.strip():
            raise RuntimeError(
                f"SACCR_CREDIT_RATING_REQUIRED:trade[{i}] names no credit rating, "
                "so it is outside the credit-derivative scope"
            )
        clean = {
            "notional": t["notional"],
            "start": t["start"],
            "end": t["end"],
            "credit_rating": rating.strip(),
        }
        if "direction" in t:
            clean["direction"] = t["direction"]
        if "reference" in t:
            clean["reference"] = t["reference"]
        if "is_index" in t:
            clean["is_index"] = t["is_index"]
        if "margined_mpor" in t:
            clean["margined_mpor"] = t["margined_mpor"]
        trades.append(clean)
    return {"trades": trades}


def run(args, root):
    args = dict(args or {})
    src = _safe(root, args.get("json_path"), require_file=True)
    out = _safe(root, args.get("output_path"))
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise RuntimeError("SACCR_INPUT_JSON_INVALID:" + str(exc)[:200]) from exc
    instance = _checked_trades(data)
    try:
        solved = saccr_credit_kernel.solve_instance(instance)
    except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
        raise RuntimeError("SACCR_INPUT_REJECTED:" + str(exc)[:300]) from exc
    addon = solved.get("credit_addon")
    traces = solved.get("traces")
    if not _is_num(addon) or addon < 0 or not isinstance(traces, list) or len(traces) != len(instance["trades"]):
        raise RuntimeError("SACCR_KERNEL_RESULT_INVALID")
    root_path = pathlib.Path(root).resolve()
    rel_out = str(out.relative_to(root_path)).replace("\\", "/")
    payload = {
        "status": STATUS,
        "output_verified": True,
        "output_path": rel_out,
        "input_path": str(src.relative_to(root_path)).replace("\\", "/"),
        "credit_addon": addon,
        "trade_count": len(instance["trades"]),
        "traces": traces,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    raw = out.read_bytes()
    return {
        "adapter": "finance_saccr_addon",
        "status": STATUS,
        "output_verified": True,
        "output_path": rel_out,
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_bytes": len(raw),
        "credit_addon": addon,
        "trade_count": len(instance["trades"]),
    }

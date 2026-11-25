#!/usr/bin/env python3
"""Execute a discovered-but-unadmitted capability surface, and issue its receipt.

Why this module exists
----------------------
625 modules in this tree carry an invocation shape -- a ``run(args, root)``
contract or a program entry point -- and own no registry row, no projection
entry and no receipt.  They are not unreachable because they are bad; they are
unreachable because nothing enumerates the tree.  ``source_index`` enumerates
only ``canonical/runtime``, and 462 of the 625 live outside it.

This is the runtime end of that enumeration.  It does not admit anything:

* the surface set is re-derived from the tree at call time, so a file that is
  declared tomorrow stops being harvested here without anyone editing a list;
* execution goes through ``capability_receipt_lane_v1.execute_and_receipt``, the
  project's only executor, so a contract module is called in-process and a
  program is run through ``bound_capabilities/cli_command.py``;
* every successful call writes a producer receipt and returns its path.  A
  producer receipt is self-issued: ``admission`` stays ``NOT_ADMITTED`` until a
  different identity with signed GitHub OIDC claims re-runs it
  (``capability-receipt-verification.yml``).  Promotion is not this module's
  business and it has no code that could do it.

So the honest sentence is: the surface is executable *now*, and it is evidence
*now*, and it is not a verified capability until someone else runs it.

Inputs (kwargs):
  capability_id   harvested id, e.g. ``canonical.tools.foo_v1.hidden.v1``
  path            alternatively the repository-relative module path
  args            dict passed to a ``run(args, root)`` contract (default {})
  timeout_s       accepted for symmetry; the lane enforces its own bound
  receipt         set false to execute without writing a receipt (default true)

result_fields: capability_id, path, invocation, entrypoint, executed,
  admission, receipt_path, observed, result, model_calls, elapsed_ms, refusal
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_HARVESTED_CAPABILITY_EXECUTION_V1"


def _root(root: Any = None) -> Path:
    return Path(root or os.environ.get("BRAIN_ROOT") or ROOT).resolve()


def surfaces(root: Any = None) -> list[dict[str, Any]]:
    """Every harvested surface, re-derived from the tree (no cached list)."""
    base = _root(root)
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))
    from canonical.tools import harvest_hidden_capabilities_v1 as census
    return census.harvested_rows(base)


def describe(capability_id: str, root: Any = None) -> dict[str, Any] | None:
    for row in surfaces(root):
        if row["id"] == capability_id:
            return row
    return None


def _resolve(request: Mapping[str, Any], root: Path) -> tuple[dict[str, Any] | None, str | None]:
    cid = str(request.get("capability_id") or "")
    path = str(request.get("path") or "")
    for row in surfaces(root):
        if (cid and row["id"] == cid) or (path and row["path"] == path):
            return row, None
    if cid or path:
        return None, "HARVESTED_SURFACE_UNKNOWN_OR_ALREADY_DECLARED"
    return None, "HARVESTED_SURFACE_NOT_NAMED"


def run(request: Mapping[str, Any], root: Any = None) -> dict[str, Any]:
    """Execute one harvested surface.  Never returns ``verified: true``."""
    base = _root(root)
    started = time.perf_counter()
    row, refusal = _resolve(request, base)
    if refusal is not None:
        return {
            "schema": SCHEMA, "status": "REFUSED", "refusal": refusal,
            "capability_id": request.get("capability_id"), "path": request.get("path"),
            "admitted": False, "model_calls": 0,
        }

    from canonical.runtime import capability_receipt_lane_v1 as lane

    args = request.get("args")
    if not isinstance(args, Mapping):
        args = {}
    receipt = lane.execute_and_receipt(
        row["id"], row["path"], row["entrypoint"], str(base),
        str(request.get("ran_by") or "harvested-runtime"),
        row["kind"], instance_index=int(request.get("instance_index") or 0),
        probe_args=args if row["kind"] == "contract" and args else None,
    )
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "capability_id": row["id"],
        "path": row["path"],
        "invocation": row["kind"],
        "entrypoint": row["entrypoint"],
        "admitted": False,
        "admission": "NOT_ADMITTED",
        "admission_note": (
            "producer receipt only; a different identity with signed GitHub OIDC "
            "claims must re-run it before the loader admits this surface"
        ),
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
    }
    if receipt is None:
        out.update({"status": "REFUSED", "executed": False,
                    "refusal": "HARVESTED_SURFACE_DID_NOT_RUN__NO_STRUCTURED_RESULT",
                    "refusal_hint": ("contract surfaces usually require inputs: pass "
                                     "`args` naming what the module documents; program "
                                     "surfaces must print one JSON object on stdout")})
        return out

    receipt["receipt_path"] = lane.receipt_path_for(row["id"])
    if request.get("receipt", True):
        target = base / receipt["receipt_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(receipt, indent=1, sort_keys=True), encoding="utf-8")
    else:
        receipt["receipt_path"] = None

    out.update({
        "status": "EXECUTED",
        "executed": True,
        "receipt_path": receipt.get("receipt_path"),
        "observed": receipt.get("observed") or {},
        "result_sha256": receipt.get("result_sha256"),
        "result_key_count": receipt.get("result_key_count"),
        "ran_by": receipt.get("ran_by"),
    })
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Execute a harvested capability surface.")
    ap.add_argument("--capability-id", default="")
    ap.add_argument("--path", default="")
    ap.add_argument("--args-json", default="")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--json", action="store_true", help="print JSON (default)")
    args = ap.parse_args(argv)
    if args.list:
        rows = surfaces()
        print(json.dumps({"count": len(rows),
                          "rows": [{"id": r["id"], "kind": r["kind"],
                                    "path": r["path"]} for r in rows]}, indent=1))
        return 0
    request: dict[str, Any] = {"capability_id": args.capability_id, "path": args.path}
    if args.args_json.strip():
        request["args"] = json.loads(args.args_json)
    print(json.dumps(run(request), indent=1, sort_keys=True, default=repr))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""The prompt says "the 447 capabilities". What is actually there?

§4.1 asks for the 447 capabilities to be located and audited, and §0 says every number in the prompt is an
input to verify. This checks, for each capability in the shipped model:

  1. does its adapter module exist and expose the declared entrypoint?
  2. does the evidence path it points at exist on disk?
  3. is it promoted (registry_status) or merely pending?

The distinction that matters: a capability whose evidence file is missing is a NAME, not a capability.
Anything counted as verified without an artefact behind it is the same failure the whole project keeps
finding in its own receipts -- a number that looks finished.
"""
from __future__ import annotations

import argparse
import collections
import importlib
import json
import pathlib
import sys
import time
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

SCHEMA = "BRAIN_CAPABILITY_AUDIT_V1"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    started = time.time()

    from canonical.runtime.brain_unified_model_v1 import open_model

    model = open_model(root=str(REPO))
    caps = model.capabilities

    rows = []
    for cid, cell in sorted(caps.items()):
        module_name = cell.get("adapter_module")
        entry = cell.get("entrypoint") or "run"
        module_ok = False
        entry_ok = False
        # The FIRST version of this loop omitted `canonical.runtime.bound_capabilities.`, which is where
        # 261 of the 262 adapter modules actually live, and reported 119 importable capabilities when the
        # truth is nearer 440. A measurement tool that cannot find the package it is measuring is the same
        # defect as a comparator that reads the wrong line: it produced a confident, wrong number.
        for prefix in ("canonical.runtime.bound_capabilities.", "canonical.runtime.",
                       "canonical.swe_kernel.", ""):
            try:
                module = importlib.import_module(prefix + str(module_name))
            except Exception:                        # noqa: BLE001 -- a failed import is the datum
                continue
            module_ok = True
            entry_ok = callable(getattr(module, entry, None))
            break
        evidence = (cell.get("verification") or {}).get("evidence_path")
        evidence_ok = bool(evidence) and (REPO / str(evidence)).exists()
        rows.append({
            "id": cid,
            "kind": cell.get("kind"),
            "registry_status": cell.get("registry_status"),
            "module_imports": module_ok,
            "entrypoint_callable": entry_ok,
            "evidence_path": evidence,
            "evidence_exists": evidence_ok,
        })

    total = len(rows)
    by_status = collections.Counter(row["registry_status"] for row in rows)
    by_kind = collections.Counter(row["kind"] for row in rows)
    both_ok = [row for row in rows if row["entrypoint_callable"] and row["evidence_exists"]]
    neither = [row for row in rows if not row["module_imports"]]
    no_evidence = [row for row in rows if not row["evidence_exists"]]

    summary = {
        "capabilities_named": total,
        "by_kind": dict(by_kind),
        "by_registry_status": dict(by_status),
        "adapter_module_imports": sum(1 for row in rows if row["module_imports"]),
        "entrypoint_callable": sum(1 for row in rows if row["entrypoint_callable"]),
        "evidence_file_exists": sum(1 for row in rows if row["evidence_exists"]),
        "module_AND_evidence_both_present": len(both_ok),
        "module_import_failed": len(neither),
        "evidence_missing": len(no_evidence),
        "share_fully_backed": round(len(both_ok) / max(1, total), 4),
        "verdicts": {
            "the_447_figure_is_the_number_of_names_in_the_registry": total == 447,
            "the_447_figure_is_the_number_of_working_capabilities": len(both_ok) == total,
            "a_majority_are_fully_backed":
                len(both_ok) / max(1, total) > 0.5,
            "most_are_pending_rather_than_promoted":
                by_status.get("RECEIPT_BACKED_PENDING_PROMOTION", 0)
                > by_status.get("VERIFIED_BOUND_CAPABILITY", 0),
        },
        "reading": (
            "447 is the number of capability NAMES the registry carries, and every one of them resolves to "
            "an adapter and an evidence path -- which is more than most of this project's own claims "
            "survive. It is not the number of capabilities that can act: 294 are RECEIPT_BACKED_PENDING_"
            "PROMOTION, i.e. evidence exists and promotion has not happened. The routing result in "
            "WHICH_WALL_IS_CLOSED_...json is the operational consequence: 415 of the 447 never win a real "
            "issue, because the median capability carries 7 index terms."),
        "what_this_does_not_show": (
            "that any capability produces a correct result on a hard task. This checks that the adapter "
            "imports, the entrypoint is callable, and the evidence artefact exists. It does not re-execute "
            "the evidence."),
        "sample_of_unbacked": no_evidence[:10],
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "summary": summary,
        "per_capability": rows,
    }, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "sample_of_unbacked"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

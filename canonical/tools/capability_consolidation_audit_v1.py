#!/usr/bin/env python3
"""Deterministic Capability Consolidation & Truth Auditor (`capability_consolidation_audit_v1`).

Produces ONE reproducible, zero-model, fail-closed snapshot of the repository's
actual capability surface at HEAD:

  1. True Capability Ledger freshness (`canonical/capabilities/true/specs/*.json`
     checked against `TRUE_CAPABILITY_LEDGER_V1.json` and `git hash-object`).
  2. Coq formal verification certificates (`canonical/certificates/CAD_NURBS_RCF_V1`).
  3. Honest classification of all capabilities in `BRAIN_UNIFIED_MODEL_V1.json`
     (Brain-owned executable vs external CLI/library wrappers vs broken imports
     vs missing evidence vs pending-promotion entries).
  4. SWE kernel consolidation map (canonical front-door spine vs composed core
     modules vs legacy/redundant archive candidates) + front-door wiring coverage.
  5. Explicit quarantine index for known disputed/retracted receipts so future
     audits never re-cite them as verified evidence.

Every output carries `authority = "NONE_SANDBOX"` — it is a reproducible local
measurement, not referee-signed credit.
"""
from __future__ import annotations

import argparse
import importlib
import json
import pathlib
import re
import subprocess
import sys
import time
from typing import Any

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.swe_kernel import canonical_swe_spine_v1 as swe_spine

SCHEMA = "CAPABILITY_CONSOLIDATION_AUDIT_V1"
AUTHORITY = "NONE_SANDBOX"

_EXTERNAL_WRAPPER_MARKERS = (
    "tesseract",
    "zbarimg",
    "qrencode",
    "zint",
    "chromedriver",
    "pandoc",
    "weasyprint",
    "sympy",
    "jq",
    "yq",
    "gnu_tar",
    "pypdf",
    "node_library_codec",
    "python_library_codec",
    "cli_command",
)

# Receipts explicitly documented as fabricated or retracted by prior repo audits.
QUARANTINED_RECEIPTS: tuple[dict[str, str], ...] = (
    {
        "path": "canonical/verification/AST_IR_ANTI_UNIFICATION_ABLATION_20261124_V1.json",
        "status": "QUARANTINED_DISPUTED_FABRICATED",
        "evidence": "canonical/verification/FIFTH_PASS_THE_94_FILE_DELTA_20261125_V4.md",
        "note": "Flagged in Pass 5 audit as the source of retracted 45/45 and 51.11% transfer claims; exclude from verified counts.",
    },
    {
        "path": "canonical/verification/THE_TRANSFER_RECEIPT_IS_FABRICATED_20261124_V1.md",
        "status": "RETRACTION_RECORD",
        "evidence": "canonical/verification/THE_TRANSFER_RECEIPT_IS_FABRICATED_20261124_V1.md",
        "note": "Documents retraction of fabricated transfer claims.",
    },
)


def _git_blob_sha(root: pathlib.Path, rel: str) -> str | None:
    p = root / rel
    if not p.is_file():
        return None
    proc = subprocess.run(
        ["git", "hash-object", str(p)],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def audit_true_capabilities(root: pathlib.Path) -> dict[str, Any]:
    specs_dir = root / "canonical/capabilities/true/specs"
    ledger_path = root / "canonical/capabilities/true/TRUE_CAPABILITY_LEDGER_V1.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.is_file() else {}
    rows = ledger.get("rows") or {}

    items: list[dict[str, Any]] = []
    stale_count = 0
    missing_from_ledger = 0
    public_runner_count = 0

    for spec_file in sorted(specs_dir.glob("*.json")):
        spec = json.loads(spec_file.read_text(encoding="utf-8"))
        cid = str(spec.get("capability_id") or spec_file.stem)
        solver = spec.get("solver")
        solver_rel = solver.get("path") if isinstance(solver, dict) else (str(solver) if solver else None)
        head_sha = _git_blob_sha(root, solver_rel) if solver_rel else None
        row = rows.get(cid)
        in_ledger = row is not None
        led_sha = row.get("solver_git_blob_sha") if isinstance(row, dict) else None
        stale = (not in_ledger) or (head_sha is not None and led_sha != head_sha)
        if not in_ledger:
            missing_from_ledger += 1
        if stale:
            stale_count += 1
        carrier = row.get("carrier") if isinstance(row, dict) else None
        if carrier == "PUBLIC_RUNNER":
            public_runner_count += 1
        items.append(
            {
                "capability_id": cid,
                "in_ledger": in_ledger,
                "stale": stale,
                "solver_path": solver_rel,
                "head_git_blob_sha": head_sha,
                "ledger_git_blob_sha": led_sha,
                "status": row.get("status") if isinstance(row, dict) else "NOT_IN_LEDGER",
                "fresh_pass_rate": row.get("fresh_pass_rate") if isinstance(row, dict) else None,
                "instances": row.get("instances") if isinstance(row, dict) else None,
                "carrier": carrier,
            }
        )

    return {
        "specs_total": len(items),
        "in_ledger_count": len(items) - missing_from_ledger,
        "missing_from_ledger_count": missing_from_ledger,
        "stale_count": stale_count,
        "public_runner_credited_count": public_runner_count,
        "sandbox_measured_count": sum(1 for x in items if x["status"] == "MEASURED_SANDBOX"),
        "ledger_authority": ledger.get("authority", "NONE"),
        "items": items,
    }


def audit_coq_certificates(root: pathlib.Path) -> dict[str, Any]:
    coq_dir = root / "canonical/certificates/CAD_NURBS_RCF_V1"
    v_files = sorted(coq_dir.glob("*.v")) if coq_dir.is_dir() else []
    total_loc = 0
    total_qed = 0
    total_admitted = 0
    for vf in v_files:
        txt = vf.read_text(encoding="utf-8", errors="replace")
        total_loc += txt.count("\n") + 1
        total_qed += len(re.findall(r"\bQed\.", txt))
        total_admitted += len(re.findall(r"\bAdmitted\.", txt))
    return {
        "certificate_dir": "canonical/certificates/CAD_NURBS_RCF_V1",
        "coq_modules": len(v_files),
        "total_loc": total_loc,
        "qed_theorems": total_qed,
        "admitted_count": total_admitted,
        "zero_admitted": total_admitted == 0 and total_qed > 0,
    }


def audit_unified_model_registry(root: pathlib.Path) -> dict[str, Any]:
    um_path = root / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"
    um = json.loads(um_path.read_text(encoding="utf-8"))
    caps = um.get("capabilities") or []

    tier_counts: dict[str, int] = {
        "BRAIN_OWNED_EXECUTABLE_BOUND": 0,
        "EXTERNAL_TOOL_OR_LIB_WRAPPER_BOUND": 0,
        "BOUND_BROKEN_IMPORT": 0,
        "BOUND_MISSING_EVIDENCE": 0,
        "PENDING_PROMOTION_RECEIPT_BACKED": 0,
    }
    broken_imports: list[dict[str, Any]] = []
    wrapper_ids: list[str] = []
    brain_owned_ids: list[str] = []

    for c in caps:
        cid = str(c.get("id") or "")
        kind = str(c.get("kind") or "")
        if kind != "BOUND_CAPABILITY":
            tier_counts["PENDING_PROMOTION_RECEIPT_BACKED"] += 1
            continue

        mod = str(c.get("adapter_module") or "")
        ev_raw = (c.get("verification") or {}).get("evidence_path") if isinstance(c.get("verification"), dict) else None
        if not ev_raw and isinstance(c.get("provenance"), dict):
            ev_raw = c["provenance"].get("evidence_path")
        ev_exists = bool(ev_raw and (root / str(ev_raw)).exists())

        imported = False
        import_err = ""
        for prefix in ("canonical.runtime.bound_capabilities.", "canonical.runtime.", ""):
            try:
                importlib.import_module(prefix + mod)
                imported = True
                break
            except Exception as exc:
                import_err = f"{type(exc).__name__}: {exc}"

        if not imported:
            tier_counts["BOUND_BROKEN_IMPORT"] += 1
            broken_imports.append({"id": cid, "adapter_module": mod, "error": import_err, "evidence_exists": ev_exists})
            continue

        is_wrapper = any(m in cid.lower() or m in mod.lower() for m in _EXTERNAL_WRAPPER_MARKERS)
        if is_wrapper:
            tier_counts["EXTERNAL_TOOL_OR_LIB_WRAPPER_BOUND"] += 1
            wrapper_ids.append(cid)
        elif not ev_exists:
            tier_counts["BOUND_MISSING_EVIDENCE"] += 1
        else:
            tier_counts["BRAIN_OWNED_EXECUTABLE_BOUND"] += 1
            brain_owned_ids.append(cid)

    return {
        "total_named_in_unified_model": len(caps),
        "tier_counts": tier_counts,
        "brain_owned_executable_bound_count": len(brain_owned_ids),
        "external_wrapper_bound_count": len(wrapper_ids),
        "broken_import_count": len(broken_imports),
        "broken_imports": broken_imports,
        "external_wrapper_sample": sorted(wrapper_ids)[:25],
    }


def audit_swe_consolidation(root: pathlib.Path) -> dict[str, Any]:
    sk_dir = root / "canonical/swe_kernel"
    competing = sorted(
        f.relative_to(root).as_posix()
        for f in sk_dir.glob("*.py")
        if any(k in f.name for k in ("repair", "cegis", "angelic", "zipper", "cow_", "cogs", "inventor", "synthesizer", "canonical_swe_spine"))
    )
    canonical_entry = "canonical/swe_kernel/canonical_swe_spine_v1.py"
    composed = set(swe_spine.COMPOSED_CORE_MODULES)

    front_door_files = [
        "canonical/runtime/brain_unified_model_v1.py",
        "canonical/runtime/live_integrated_brain_v1.py",
        "canonical/runtime/goal_compiler.py",
        "canonical/runtime/goal_front_compiler_v1.py",
        "canonical/runtime/creature_runtime_v1.py",
    ]
    fd_text = "\n".join(
        (root / p).read_text(encoding="utf-8", errors="replace")
        for p in front_door_files
        if (root / p).is_file()
    )
    spine_wired = "canonical_swe_spine_v1" in fd_text
    archive_candidates = [
        p for p in competing
        if p != canonical_entry and p not in composed
    ]
    return {
        "canonical_front_door_spine": canonical_entry,
        "spine_wired_into_front_door": spine_wired,
        "composed_core_modules": list(swe_spine.COMPOSED_CORE_MODULES),
        "total_swe_repair_modules_detected": len(competing),
        "redundant_or_legacy_archive_candidates_count": len(archive_candidates),
        "redundant_or_legacy_archive_candidates": archive_candidates,
    }


def audit_quarantined_receipts(root: pathlib.Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in QUARANTINED_RECEIPTS:
        exists = (root / item["path"]).exists()
        rows.append({**item, "present_on_disk": exists})
    return rows


def run_audit(root: pathlib.Path | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    base = (root or REPO).resolve()
    true_caps = audit_true_capabilities(base)
    coq = audit_coq_certificates(base)
    registry = audit_unified_model_registry(base)
    swe = audit_swe_consolidation(base)
    quarantine = audit_quarantined_receipts(base)

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "incremental_spend_usd": 0.0,
        "elapsed_s": round(time.perf_counter() - t0, 4),
        "true_capabilities": true_caps,
        "coq_formal_certificates": coq,
        "unified_model_registry_truth": registry,
        "swe_kernel_consolidation": swe,
        "quarantined_receipts": quarantine,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=None, help="Optional JSON output path")
    args = parser.parse_args(argv)
    report = run_audit()
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text)
    print(
        f"CONSOLIDATION_AUDIT_OK true_caps={report['true_capabilities']['in_ledger_count']}/"
        f"{report['true_capabilities']['specs_total']} stale={report['true_capabilities']['stale_count']} "
        f"coq_qed={report['coq_formal_certificates']['qed_theorems']} "
        f"spine_wired={report['swe_kernel_consolidation']['spine_wired_into_front_door']} "
        f"archive_candidates={report['swe_kernel_consolidation']['redundant_or_legacy_archive_candidates_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

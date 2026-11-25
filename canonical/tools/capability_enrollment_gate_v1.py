#!/usr/bin/env python3
"""The enrollment gate: why 146 dispatch rows and 9 certified capabilities are not yet one system.

The tree's own diagnosis, in one sentence, is that **there is already a composition root** —
`canonical/runtime/live_integrated_brain_v1.load_verified_registry()` admits a capability only when
its row says `VERIFIED_BOUND_CAPABILITY`, its `incremental_spend_usd` is 0, and (per
`AGENTS.md` rule 4, enforced by `.github/workflows/capability-receipt-verification.yml`) a producer
receipt *and* an independently attested verification record exist for the exact content hash. What
is missing is not a framework. It is that the root and the measurement program are disjoint sets,
and that the root's own admission rule is violated by rows still in it.

Five defect classes, all mechanically checkable, none requiring judgement:

1. `DANGLING_ADAPTER` — a row names an `adapter_module` with no file under `canonical/runtime/bound_capabilities/`.
   The dispatch table points at nothing.
2. `MISSING_VERIFICATION_RECEIPT` — a row cites `verification.receipt_path` and that file is not in the tree.
   This is the root admitting (or claiming to admit) work it cannot show was independently verified.
3. `UNSATISFIABLE_REQUIRES` — a `requires` predicate that no row's `provides` can produce. A planner
   chaining on provides/requires can never satisfy these; they are either ambient facts (and must be
   declared as such, somewhere that is read) or a missing capability.
4. `UNENROLLED_CERTIFIED_CAPABILITY` — a capability with a harness measurement (fresh instances,
   independent oracles, mutation-tested) that no registry row binds. This is the class where the
   project's *strongest* evidence cannot be dispatched.
5. `REGISTRY_VS_SNAPSHOT_DIVERGENCE` — the live registry and the snapshot floor disagree about a row.
   The snapshot may not lose rows; a divergence is a drift signal, not a style choice.

`--emit-candidates` writes enrollment skeletons for class 4 carrying ONLY fields the receipt
already states. `provides`/`requires` are deliberately left as `null` with a refusal note: a
predicate invented here would be a capability claim with no measurement behind it, which is the
exact failure this project keeps re-measuring.

Model calls: 0. Network: 0. Cost: $0.00.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFECT_ORDER = (
    "DANGLING_ADAPTER",
    "MISSING_VERIFICATION_RECEIPT",
    "UNSATISFIABLE_REQUIRES",
    "UNENROLLED_CERTIFIED_CAPABILITY",
    "REGISTRY_VS_SNAPSHOT_DIVERGENCE",
)


def _read(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows_of(doc: Mapping[str, Any]) -> dict[str, Any]:
    raw = doc.get("capabilities")
    return dict(raw) if isinstance(raw, Mapping) else {}


def build(root: pathlib.Path, registry: pathlib.Path, snapshot: pathlib.Path,
          ledger: pathlib.Path, adapters: pathlib.Path) -> dict[str, Any]:
    live = _rows_of(_read(registry)) if registry.is_file() else {}
    snap = _rows_of(_read(snapshot)) if snapshot.is_file() else {}
    rows = {**live, **snap} if snap else live

    # `runtime_native_action` is a declared kind, not a missing file: the loaders special-case it
    # (canonical/runtime/capability_selection_retrieval_v1.py:692, root3_effect_channel_registry_v2.py:214).
    # Counting those rows as dangling would be my bug, not the registry's, so they are reported apart.
    NATIVE_KIND = "runtime_native_action"
    dangling = sorted(
        f"{cid} -> {r.get('adapter_module')}"
        for cid, r in rows.items()
        if r.get("adapter_module") and r["adapter_module"] != NATIVE_KIND
        and not (adapters / f"{r['adapter_module']}.py").is_file()
    )
    native_rows = sorted(cid for cid, r in rows.items() if r.get("adapter_module") == NATIVE_KIND)
    missing_receipts = sorted(
        f"{cid} -> {(r.get('verification') or {}).get('receipt_path')}"
        for cid, r in rows.items()
        if isinstance(r.get("verification"), Mapping)
        and (r["verification"].get("receipt_path"))
        and not (root / str(r["verification"]["receipt_path"])).is_file()
    )
    provides: set[str] = set()
    requires: set[str] = set()
    for r in rows.values():
        provides.update(r.get("provides") or [])
        requires.update(r.get("requires") or [])
    unsatisfiable = sorted(requires - provides)

    doc = _read(ledger) if ledger.is_file() else {}
    certified = {k: v for k, v in (doc.get("rows") or {}).items()}
    # A certified capability is "enrolled" only when a row can be traced to the artifact that was
    # measured: the adapter module, the row's source, or an entrypoint naming the kernel module.
    traceables = {
        cid: " ".join(
            str(r.get(k) or "") for k in ("adapter_module", "source", "entrypoint", "action_template")
        ).lower()
        for cid, r in rows.items()
    }
    unenrolled: list[str] = []
    for cap, row in sorted(certified.items()):
        spec_rel = row.get("spec_path")
        module = None
        if spec_rel and (root / spec_rel).is_file():
            module = (_read(root / spec_rel).get("solver") or {}).get("module")
        keys = {cap.lower()}
        if module:
            keys.add(str(module).rsplit("/", 1)[-1].removesuffix(".py").lower())
        if not any(any(k in blob for k in keys) for blob in traceables.values()):
            unenrolled.append(cap)

    # `load_verified_registry` merges as `raw = {**raw, **merged}` with merged = snapshot rows, so
    # on a collision the snapshot is what gets dispatched: a newer live row can be silently shadowed.
    divergence = sorted(
        {*set(live) - set(snap), *set(snap) - set(live)}
        | {cid for cid in set(live) & set(snap) if json.dumps(live[cid], sort_keys=True) != json.dumps(snap[cid], sort_keys=True)}
    )
    defects = {
        "DANGLING_ADAPTER": dangling,
        "MISSING_VERIFICATION_RECEIPT": missing_receipts,
        "UNSATISFIABLE_REQUIRES": unsatisfiable,
        "UNENROLLED_CERTIFIED_CAPABILITY": unenrolled,
        "REGISTRY_VS_SNAPSHOT_DIVERGENCE": divergence,
    }
    return {
        "schema": "BRAIN_CAPABILITY_ENROLLMENT_GATE_V1",
        "authority": "NONE__DERIVED_FROM_REGISTRY_ROWS_AND_COMMITTED_RECEIPTS",
        "registry_rows_live": len(live),
        "registry_rows_snapshot": len(snap),
        "registry_rows_merged": len(rows),
        "distinct_provides": len(provides),
        "native_kind_rows": len(native_rows),
        "native_kind_rows_ids": native_rows,
        "distinct_requires": len(requires),
        "certified_capabilities": len(certified),
        "defect_counts": {k: len(v) for k, v in defects.items()},
        "defects": defects,
        "clean": not any(defects.values()),
    }


def candidates(root: pathlib.Path, ledger: pathlib.Path, report: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Enrollment skeletons for class 4, carrying only what the receipt states."""
    doc = _read(ledger) if ledger.is_file() else {}
    out = []
    for cap in report["defects"]["UNENROLLED_CERTIFIED_CAPABILITY"]:
        row = (doc.get("rows") or {}).get(cap) or {}
        spec_rel = row.get("spec_path")
        module = fn = None
        limits: list[str] = []
        if spec_rel and (root / spec_rel).is_file():
            spec = _read(root / spec_rel)
            solver = spec.get("solver") or {}
            module, fn = solver.get("module"), solver.get("entry")
            limits = list(spec.get("scope_limits") or [])
        out.append({
            "capability_id": f"derived.CANDIDATE.{cap.lower()}",
            "status": "CANDIDATE_NOT_ADMITTED__DO_NOT_PROMOTE_BY_NAME",
            "adapter_module": None,
            "entrypoint": fn,
            "kernel_module": module,
            "provides": None,
            "requires": None,
            "predicate_note": (
                "null is deliberate: provides/requires are a claim about what this capability makes "
                "true in the world. The harness receipt measures correctness of an output, not this. "
                "Write them from a spec, or leave the row unadmitted."
            ),
            "limitations": limits or ["see spec scope_limits"],
            "incremental_spend_usd": 0,
            "evidence": {
                "true_capability_receipt": row.get("latest_receipt"),
                "receipt_sha256_16_present": bool(row.get("latest_receipt")) and (root / str(row.get("latest_receipt", ""))).is_file(),
                "solver_git_blob_sha": row.get("solver_git_blob_sha"),
                "instances": row.get("instances"),
                "fresh_pass_rate": row.get("fresh_pass_rate"),
                "measured_utc": row.get("measured_utc"),
            },
            "admission_blocked_until": [
                "an adapter exists under canonical/runtime/bound_capabilities/",
                "a producer receipt for that adapter at its content hash exists",
                "an independent verification record with a github_run_id exists "
                "(.github/workflows/capability-receipt-verification.yml is the only way to mint one)",
            ],
        })
    return out


def to_markdown(r: Mapping[str, Any]) -> str:
    L = ["# Enrollment gate: the root exists, the binding does not\n"]
    L.append(f"- registry rows: live {r['registry_rows_live']}, snapshot {r['registry_rows_snapshot']}, "
             f"merged {r['registry_rows_merged']} | provides vocabulary {r['distinct_provides']}, "
             f"requires vocabulary {r['distinct_requires']}")
    L.append(f"- rows dispatched as the declared native kind `{r['defects'] and 'runtime_native_action'}`: "
             f"{r['native_kind_rows']} (no adapter file expected; listed, not counted as a defect)")
    L.append(f"- harness-certified capabilities: {r['certified_capabilities']}")
    L.append(f"- **clean: {r['clean']}**\n")
    L.append("| defect class | count | what it means for 'one model' |")
    L.append("|---|---|---|")
    meaning = {
        "DANGLING_ADAPTER": "the dispatch table names code that is not in the tree",
        "MISSING_VERIFICATION_RECEIPT": "admission rule 2 is cited but the evidence file is gone",
        "UNSATISFIABLE_REQUIRES": "a planner can never satisfy these preconditions from registered work",
        "UNENROLLED_CERTIFIED_CAPABILITY": "the strongest measurements are not dispatchable",
        "REGISTRY_VS_SNAPSHOT_DIVERGENCE": "live registry and the snapshot floor disagree; at load time the snapshot wins, so a newer live row can be shadowed",
    }
    for k in DEFECT_ORDER:
        L.append(f"| `{k}` | {r['defect_counts'][k]} | {meaning[k]} |")
    for k in DEFECT_ORDER:
        items = r["defects"][k]
        if not items:
            continue
        L.append(f"\n`{k}`:\n")
        for x in items[:25]:
            L.append(f"- {x}")
        if len(items) > 25:
            L.append(f"- … {len(items) - 25} more")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--registry", default=None)
    ap.add_argument("--snapshot", default=None)
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--adapters", default=None)
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--md-out", default=None)
    ap.add_argument("--emit-candidates", default=None)
    ap.add_argument("--fail-on-defect", action="store_true")
    a = ap.parse_args(argv)
    root = pathlib.Path(a.root)
    report = build(
        root,
        pathlib.Path(a.registry or root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"),
        pathlib.Path(a.snapshot or root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json"),
        pathlib.Path(a.ledger or root / "canonical/capabilities/true/TRUE_CAPABILITY_LEDGER_V1.json"),
        pathlib.Path(a.adapters or root / "canonical/runtime/bound_capabilities"),
    )
    if a.json_out:
        p = pathlib.Path(a.json_out); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if a.md_out:
        p = pathlib.Path(a.md_out); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(to_markdown(report), encoding="utf-8")
    if a.emit_candidates:
        cands = candidates(root, pathlib.Path(a.ledger or root / "canonical/capabilities/true/TRUE_CAPABILITY_LEDGER_V1.json"), report)
        p = pathlib.Path(a.emit_candidates); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"schema": "BRAIN_CAPABILITY_ENROLLMENT_CANDIDATES_V1",
                                 "authority": "NONE__DERIVED_FROM_RECEIPTS_NOT_PROMOTABLE_AS_ADMITTED",
                                 "candidates": cands}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not any((a.json_out, a.md_out, a.emit_candidates)):
        print(to_markdown(report))
    return 1 if (a.fail_on_defect and not report["clean"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())

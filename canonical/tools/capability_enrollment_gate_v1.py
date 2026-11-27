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
The registry is read as what it is: `load_verified_registry` merges FOUR sources (curated live,
curated snapshot, the extended inventory, the receipt projection) and admits a capability from the last
two only through `_receipt_admits` — a producer receipt at the module's content hash plus an independent
verification record carrying a platform-attested `github_run_id`. Counting two of the four sources was
this tool's own first bug, and an instrument that reads half the table cannot call a row missing.

`REGISTRY_VS_SNAPSHOT_DIVERGENCE` used to be defect class 5. It is a FACT, and the reason is in the
loader's own comment: "A PROJECTION MAY ADD OR UPDATE A ROW; IT MAY NEVER DELETE ONE. The snapshot is
therefore the FLOOR." The merge is a union, so nothing is lost and the divergence is the designed
state of a repo where rows are regenerated. A gate that fires on ordinary growth is noise, and noise
gets the gate deleted: it is reported, counted, and never fails `--fail-on-defect`.

Enrollment of a certified capability is now graded, because the tree has two distinct states for it:
`registry_bound` (a curated row exists, adapter resolving) and `pending_binding_only` (the capability
sits in `canonical/astra_runtime/pending_bindings/` awaiting the receipt the CI verifier mints). Only
the third state — neither — is a defect.

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
)
FACT_ORDER = ("REGISTRY_VS_SNAPSHOT_DIVERGENCE", "OWNED_FAMILY_ROUTES")
DEFECT_ORDER = DEFECT_ORDER + ("FAMILY_ROUTE_FILE_MISSING",)
MATRIX = "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"
ROUTE_PY = __import__("re").compile(r"canonical/[A-Za-z0-9_./-]+\.py")


def _read(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows_of(doc: Mapping[str, Any]) -> dict[str, Any]:
    raw = doc.get("capabilities")
    return dict(raw) if isinstance(raw, Mapping) else {}


def build(root: pathlib.Path, registry: pathlib.Path, snapshot: pathlib.Path,
          ledger: pathlib.Path, adapters: pathlib.Path) -> dict[str, Any]:
    live = _rows_of(_read(registry)) if registry.is_file() else {}
    snap = _rows_of(_read(snapshot)) if snapshot.is_file() else {}
    ext_path = root / "canonical/runtime/AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json"
    proj_path = root / "canonical/runtime/CAPABILITY_RECEIPT_PROJECTION_V1.json"
    pending_dir = root / "canonical/astra_runtime/pending_bindings"
    extended = _rows_of(_read(ext_path)) if ext_path.is_file() else {}
    projection: dict[str, Any] = {}
    if proj_path.is_file():
        ent = _read(proj_path).get("entries")
        projection = dict(ent) if isinstance(ent, Mapping) else {}
    # Precedence is the loader's, not a preference: curated rows are collected first, and both later
    # passes skip any id already in `out` (`if cid in out: continue`). Within the curated pair the
    # snapshot is merged last and therefore wins a collision.
    rows = {**extended, **projection, **live, **snap}

    pending: dict[str, dict[str, Any]] = {}
    unreadable_pending: list[str] = []
    if pending_dir.is_dir():
        for f in sorted(pending_dir.glob("*.json")):
            try:
                d = _read(f)
            except (OSError, ValueError):
                unreadable_pending.append(f.name)
                continue
            cid = d.get("capability_id")
            if isinstance(cid, str) and cid:
                pending.setdefault(cid, d)

    # `runtime_native_action` is a declared kind, not a missing file: the loaders special-case it
    # (canonical/runtime/capability_selection_retrieval_v1.py:692, root3_effect_channel_registry_v2.py:214).
    # Counting those rows as dangling would be my bug, not the registry's, so they are reported apart.
    NATIVE_KIND = "runtime_native_action"
    def _resolves(entry: Mapping[str, Any]) -> bool:
        mod = entry.get("adapter_module")
        if not mod or mod == NATIVE_KIND:
            return True
        if (adapters / f"{mod}.py").is_file():
            return True
        src = entry.get("source") if isinstance(entry.get("source"), Mapping) else {}
        rel = src.get("path") or src.get("adapter_path")
        return bool(rel) and (root / str(rel)).is_file()

    dangling = sorted(
        f"{cid} -> {r.get('adapter_module')}"
        for cid, r in rows.items()
        if r.get("adapter_module") and r["adapter_module"] != NATIVE_KIND and not _resolves(r)
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
    # Binding is decided by identity of the artifact, never by a substring of the row's JSON. When
    # this check read only the curated pair, a name match was tight; over all 2,463 merged rows it was
    # not -- the extended inventory has a row for almost every module in the tree, so "mentions the
    # kernel's name" made 9 of 9 capabilities look registry-bound, which is exactly the kind of green
    # that means nothing. The rule now: a row binds a certified capability if the file it dispatches to
    # IS the measured kernel or forwards to it, and if the row cites the capability's own spec.
    def _file_binds(rel: Any, module: Any) -> bool:
        if not isinstance(rel, str) or not rel or not module:
            return False
        f = root / rel
        if not f.is_file():
            return False
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
        stem = str(module).rsplit("/", 1)[-1].removesuffix(".py")
        return str(module) in text or f'"canonical.{stem}"' in text or f"{stem} import" in text

    def _candidate_files(r: Mapping[str, Any]) -> list[str]:
        out = []
        am = r.get("adapter_module")
        if isinstance(am, str) and am and am != NATIVE_KIND:
            out.append(f"canonical/runtime/bound_capabilities/{am}.py")
        src = r.get("source") if isinstance(r.get("source"), Mapping) else {}
        for key in ("path", "adapter_path", "module"):
            v = src.get(key)
            if isinstance(v, str):
                out.append(v)
        return out

    registry_bound: list[str] = []
    pending_only: list[str] = []
    unenrolled: list[str] = []
    for cap, row in sorted(certified.items()):
        spec_rel = row.get("spec_path")
        module = None
        if spec_rel and (root / spec_rel).is_file():
            module = (_read(root / spec_rel).get("solver") or {}).get("module")
        bound = queued = False
        for r in rows.values():
            src = r.get("source") if isinstance(r.get("source"), Mapping) else {}
            if spec_rel and src.get("spec") == spec_rel:
                bound = True
                break
            stem = str(module).rsplit("/", 1)[-1].removesuffix(".py").lower() if module else None
            if stem and stem not in json.dumps(r, sort_keys=True).lower():
                continue  # a cheap prefilter, never the verdict: the verdict is the file identity below
            if any(_file_binds(f, module) for f in _candidate_files(r)):
                bound = True
                break
        if not bound:
            for d in pending.values():
                entry = d.get("registry_entry") or {}
                contract = d.get("contract") or {}
                if spec_rel and (entry.get("source") or {}).get("spec") == spec_rel:
                    queued = True
                    break
                if module and (contract.get("kernel") or {}).get("module") == module:
                    queued = True
                    break
                if any(_file_binds(f, module) for f in _candidate_files(entry)):
                    queued = True
                    break
        if bound:
            registry_bound.append(cap)
        elif queued:
            pending_only.append(cap)
        else:
            unenrolled.append(cap)

    # `load_verified_registry` merges as `raw = {**raw, **merged}` with merged = snapshot rows, so
    # on a collision the snapshot is what gets dispatched: a newer live row can be silently shadowed.
    divergence = sorted(
        {*set(live) - set(snap), *set(snap) - set(live)}
        | {cid for cid in set(live) & set(snap) if json.dumps(live[cid], sort_keys=True) != json.dumps(snap[cid], sort_keys=True)}
    )
    # The root's own answer, not a re-implementation of it: how many rows it will actually dispatch.
    # Only probe the real root: `live_integrated_brain_v1` reads its own module-level ROOT, so pointing
    # the probe at a fixture root would answer with the repository's counts and call that a measurement.
    admitted: Any = None
    admitted_ids: set[str] = set()
    admission_error: str | None = None
    if (root / "canonical/runtime/live_integrated_brain_v1.py").is_file():
        try:
            import sys
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            from canonical.runtime import live_integrated_brain_v1 as brain  # type: ignore[import-not-found]
            admitted_ids = set(brain.load_verified_registry())
            admitted = len(admitted_ids)
        except Exception as exc:  # a probe that cannot run is a fact about the probe, not a defect
            admission_error = f"{type(exc).__name__}: {str(exc)[:160]}"
    else:
        admission_error = "skipped: not the repository root"
    # The other capability class in this repo: the ownership matrix's VERIFIED_OWNED families, whose
    # "capability" is a route module plus a public-runner verification record rather than a harness
    # spec. Enrollment cannot be *granted* here -- a wrapper around code with no generator and no
    # oracle would be a claim with nothing behind it -- but the gap must be visible where it can be
    # counted, or it is forgotten. Measured today: 4 named route modules, all present, all reachable
    # only as `UNVERIFIED_INVENTORY` rows, and none speaking `run(args, root)`, so the receipt lane
    # cannot execute them at all. That is the honest denominator for "every advanced capability is in
    # one model": 9 measured kernels enrolled and receiptable, 4 owned-family routes that need a spec
    # and an envelope before any registry can hold them truthfully.
    families: dict[str, Any] = {}
    missing_routes: list[str] = []
    matrix_path = root / MATRIX
    if matrix_path.is_file():
        try:
            rows_m = _read(matrix_path).get("rows") or []
        except (OSError, ValueError):
            rows_m = []
        for fr in rows_m:
            if not isinstance(fr, Mapping):
                continue
            for rel in sorted(set(ROUTE_PY.findall(json.dumps(fr)))):
                if not (root / rel).is_file():
                    missing_routes.append(f"{fr.get('family')} -> {rel}")
                    continue
                cid_auto = f"{rel}.auto.v1"
                safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in cid_auto)
                receipt = (root / "canonical/astra_runtime/evidence"
                           / f"CAPABILITY__{safe}__EXECUTION_RECEIPT.json").is_file()
                indep = (root / "canonical/astra_runtime/evidence"
                         / f"CAPABILITY__{safe}__INDEPENDENT_VERIFICATION.json").is_file()
                curated = sorted(
                    cid for cid, r in rows.items()
                    if cid != cid_auto and rel in {str(((r.get("source") or {}).get(k) or ""))
                                                    for k in ("path", "adapter_path")}
                )
                try:
                    import sys
                    if str(root) not in sys.path:
                        sys.path.insert(0, str(root))
                    from canonical.runtime import capability_receipt_lane_v1 as lane  # type: ignore
                    shape = lane.contract_shape(str(root / rel))
                except Exception:
                    shape = None
                if cid_auto in admitted_ids or any(c in admitted_ids for c in curated):
                    verdict = "ADMITTED"
                elif receipt:
                    verdict = "RECEIPTED__NO_INDEPENDENT_VERIFICATION" if not indep else "IN_PROJECTION"
                elif curated:
                    verdict = "ENROLLED_NOT_RECEIPTED"
                elif shape is not None:
                    verdict = "INVENTORY_ONLY__ADAPTABLE"
                else:
                    verdict = "INVENTORY_ONLY__NOT_DISPATCH_SHAPE"
                families[str(fr.get("family"))] = {
                    "route": rel,
                    "inventory_status": (extended.get(cid_auto) or {}).get("status"),
                    "producer_receipt": receipt,
                    "independent_verification": indep,
                    "bound_by_other_rows": curated,
                    "dispatch_shape": bool(shape),
                    "verdict": verdict,
                }
    defects = {
        "FAMILY_ROUTE_FILE_MISSING": missing_routes,
        "DANGLING_ADAPTER": dangling,
        "MISSING_VERIFICATION_RECEIPT": missing_receipts,
        "UNSATISFIABLE_REQUIRES": unsatisfiable,
        "UNENROLLED_CERTIFIED_CAPABILITY": unenrolled,
    }
    return {
        "schema": "BRAIN_CAPABILITY_ENROLLMENT_GATE_V2",
        "authority": "NONE__DERIVED_FROM_REGISTRY_ROWS_AND_COMMITTED_RECEIPTS",
        "registry_rows_live": len(live),
        "registry_rows_snapshot": len(snap),
        "registry_rows_extended": len(extended),
        "registry_rows_projection": len(projection),
        "pending_bindings": len(pending),
        "pending_bindings_unreadable": unreadable_pending[:10],
        "registry_rows_merged": len(rows),
        "registry_rows_admitted_by_root": admitted,
        "admission_probe_error": admission_error,
        "distinct_provides": len(provides),
        "native_kind_rows": len(native_rows),
        "native_kind_rows_ids": native_rows,
        "distinct_requires": len(requires),
        "certified_capabilities": len(certified),
        "certified_registry_bound": registry_bound,
        "certified_pending_binding_only": pending_only,
        "family_routes": families,
        "family_route_verdicts": {v["verdict"]: sum(1 for x in families.values() if x["verdict"] == v["verdict"])
                                  for v in families.values()},
        "facts": {"REGISTRY_VS_SNAPSHOT_DIVERGENCE": divergence,
                  "REGISTRY_VS_SNAPSHOT_DIVERGENCE_note": (
                      "by design: the snapshot is a floor and the merge is a union, so divergence "
                      "cannot delete a row -- it is drift to read, not a defect to block")},
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
    L = ["# Enrollment gate: what the root can actually dispatch\n"]
    L.append(f"- registry rows: live {r['registry_rows_live']}, snapshot {r['registry_rows_snapshot']}, "
             f"extended {r['registry_rows_extended']}, projection {r['registry_rows_projection']}, "
             f"pending bindings {r['pending_bindings']} → merged {r['registry_rows_merged']} "
             f"| admitted by `load_verified_registry`: **{r['registry_rows_admitted_by_root']}**"
             + (f" (probe error: {r['admission_probe_error']})" if r.get("admission_probe_error") else ""))
    L.append(f"- provides vocabulary {r['distinct_provides']}, requires vocabulary {r['distinct_requires']}")
    L.append(f"- rows dispatched as the declared native kind `{r['defects'] and 'runtime_native_action'}`: "
             f"{r['native_kind_rows']} (no adapter file expected; listed, not counted as a defect)")
    verdicts = r.get("family_route_verdicts") or {}
    if r.get("family_routes") is not None:
        L.append(f"- `OWNED_FAMILY_ROUTES` (fact): ownership-matrix route modules, {len(r['family_routes'])} named, "
                 + ", ".join(f"{k} {v}" for k, v in sorted(verdicts.items()))
                 + " -- an inventory row is not enrollment; only ADMITTED means the root can dispatch it")
    L.append(f"- harness-certified capabilities: {r['certified_capabilities']} — registry-bound "
             f"{len(r['certified_registry_bound'])}, pending binding only "
             f"{len(r['certified_pending_binding_only'])} ({', '.join(r['certified_pending_binding_only'])}), "
             f"unenrolled {len(r['defects']['UNENROLLED_CERTIFIED_CAPABILITY'])}")
    L.append(f"- **clean: {r['clean']}**\n")
    L.append("| defect class | count | what it means for 'one model' |")
    L.append("|---|---|---|")
    meaning = {
        "FAMILY_ROUTE_FILE_MISSING": "an owned capability family cites a route module that is not in the tree",
        "DANGLING_ADAPTER": "the dispatch table names code that is not in the tree",
        "MISSING_VERIFICATION_RECEIPT": "admission rule 2 is cited but the evidence file is gone",
        "UNSATISFIABLE_REQUIRES": "a planner can never satisfy these preconditions from registered work",
        "UNENROLLED_CERTIFIED_CAPABILITY": "the strongest measurements are not dispatchable and not even queued",
    }
    for k in DEFECT_ORDER:
        L.append(f"| `{k}` | {r['defect_counts'][k]} | {meaning[k]} |")
    L.append(f"| `REGISTRY_VS_SNAPSHOT_DIVERGENCE` (fact, not a defect) | "
             f"{len(r['facts']['REGISTRY_VS_SNAPSHOT_DIVERGENCE'])} | {r['facts']['REGISTRY_VS_SNAPSHOT_DIVERGENCE_note']} |")
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

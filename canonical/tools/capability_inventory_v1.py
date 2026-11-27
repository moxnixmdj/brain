#!/usr/bin/env python3
"""What this repository can actually claim about its own capabilities — read from the tree, not from memory.

WHY A TOOL AND NOT A TABLE
--------------------------
The session's standing correction is that claims keep failing against checked data. So this
script refuses to be a place where numbers are typed by hand. Every row is *derived*, and three
integrity properties are enforced rather than assumed:

1. **Measured means the measured bytes are still here.** A `TRUE_CAPABILITY_LEDGER` row records the
   git blob sha of the solver it measured. Here that sha is looked up in `HEAD`'s tree; if the
   artifact has changed since, the row is reported as `STALE_MEASUREMENT`, not as a pass.
2. **A pointer that does not resolve is a finding, not a footnote.** Every `evidence` /
   `postwave_*_evidence` path in the frontier ownership matrix is checked for existence; missing
   ones are counted in `broken_pointers` and named in the markdown.
3. **Self-reported counts must agree with the fields they summarize.** The ownership file's
   `status` string carries counts; those are compared against its own `acceptance_truth` /
   `ownership_truth` dicts and any disagreement is emitted as a `count_mismatch`.

The capability law (`canonical/swe_kernel/capability_law_v1.py`) is imported, not reimplemented,
so its pinned-receipt discipline (it raises when a receipt is missing or changed) guards those
terms too. Benchmark numbers are read from the committed CI reports, including a run that produced
nothing (`run_produced_number: false`), because a void run is a fact about the branch.

Model calls: 0.  Network: 0.  Cost: $0.00.  It writes nothing outside the two --out paths.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "BRAIN_CAPABILITY_INVENTORY_V1"
AUTHORITY = "NONE__DERIVED_FROM_COMMITTED_RECEIPTS_AND_CI_REPORTS"

TRUE_LEDGER = ROOT / "canonical/capabilities/true/TRUE_CAPABILITY_LEDGER_V1.json"
OWNERSHIP_MATRIX = ROOT / "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"
OPUS55_FRONTIER_FILE = ROOT / "canonical/capabilities/frontier/OPUS_5_5_USEFUL_CAPABILITY_OWNERSHIP_V1.json"
EVAL_RESULTS = ROOT / "canonical/eval/results/swe-bench-pro-v2"
CREDITS = {"n_files_read", "n_rows"}


def _git_blob_shas_at_head() -> dict[str, str]:
    """path -> blob sha for every tracked file at HEAD (the tree we would be shipping)."""
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-tree", "-r", "HEAD", "--format=%(objectname) %(path)"],
        capture_output=True, text=True, check=True,
    ).stdout
    mapping: dict[str, str] = {}
    for line in out.splitlines():
        sha, _, path = line.partition(" ")
        mapping[path] = sha
    return mapping


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16] if path.is_file() else "MISSING"


def _paths_in(value: Any) -> list[str]:
    """Every plausible repo-relative path inside a JSON blob, as written."""
    found: list[str] = []
    if isinstance(value, str):
        if value.startswith("canonical/") or value.startswith("execution_guard/"):
            found.append(value.split("#", 1)[0].strip())
    elif isinstance(value, Mapping):
        for v in value.values():
            found += _paths_in(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            found += _paths_in(v)
    return found


def _true_capabilities(tree: dict[str, str]) -> dict[str, Any]:
    """Harness-written measurements, each re-bound to the bytes in HEAD."""
    doc = json.loads(TRUE_LEDGER.read_text(encoding="utf-8"))
    rows: dict[str, Any] = {}
    for cap, row in sorted(doc.get("rows", {}).items()):
        entry: dict[str, Any] = {
            "verdict": row.get("verdict"),
            "status": row.get("status"),
            "instances": row.get("instances"),
            "fresh_pass_rate": row.get("fresh_pass_rate"),
            "n_oracles": len(row.get("independent_oracle_ids") or []),
            "oracle_classes": sorted(set((row.get("oracle_classes") or {}).values())),
            "canary_pass": row.get("canary_pass"),
            "measured_utc": row.get("measured_utc"),
            "carrier": row.get("carrier"),
            "claim_chars": len(str(row.get("claim", ""))),
            "scope_limits": len(row.get("scope_limits") or []),
            "receipt": row.get("latest_receipt"),
            "receipt_sha256_16": _digest(ROOT / str(row.get("latest_receipt", ""))),
        }
        solver_sha = str(row.get("solver_git_blob_sha") or "")
        kernels = row.get("kernel_git_blob_shas") or {}
        bound = [p for p, sha in kernels.items() if tree.get(p) == sha]
        entry["solver_blob_present_in_head"] = solver_sha in set(tree.values())
        entry["kernels_pinned"] = f"{len(bound)}/{len(kernels)}"
        entry["binding"] = (
            "MEASURED_BYTES_STILL_IN_HEAD"
            if entry["solver_blob_present_in_head"] and (not kernels or len(bound) == len(kernels))
            else "STALE_MEASUREMENT"
        )
        rows[cap] = entry
    return {
        "ledger_authority": doc.get("authority"),
        "law": "canonical/laws/TRUE_CAPABILITY_TEST_LAW_V1.md",
        "law_exists": (ROOT / "canonical/laws/TRUE_CAPABILITY_TEST_LAW_V1.md").is_file(),
        "n_capabilities": len(rows),
        "n_pass": sum(1 for r in rows.values() if r["verdict"] == "PASS"),
        "n_stale": sum(1 for r in rows.values() if r["binding"] == "STALE_MEASUREMENT"),
        "rows": rows,
    }


def _frontier_matrix() -> dict[str, Any]:
    """The repo's own per-family verdicts against the frontier, plus pointer and count audits."""
    doc = json.loads(OWNERSHIP_MATRIX.read_text(encoding="utf-8"))
    fams: dict[str, Any] = {}
    broken: dict[str, list[str]] = {}
    for row in doc.get("rows", []):
        fam = str(row.get("family"))
        pointers = _paths_in(row)
        missing = sorted({p for p in pointers if not (ROOT / p).exists()})
        if missing:
            broken[fam] = missing
        fams[fam] = {
            "status": row.get("status"),
            "ownership_credit": row.get("postwave_ownership_credit"),
            "behavioral_status": row.get("postwave_terminal_behavioral_status"),
            "scope_state": row.get("current_behavioral_scope_state"),
            "evidence_chars": len(str(row.get("evidence", ""))),
            "residual_chars": len(str(row.get("residual", ""))),
            "n_pointers": len(set(pointers)),
            "n_broken_pointers": len(missing),
            "has_next_action": bool(row.get("next_required_action") or row.get("campaign_next_action")),
        }
    summary = doc.get("summary") or {}
    counts: dict[str, list[str]] = {}
    for key, val in summary.items():
        if isinstance(val, list):
            counts[key] = val
    return {
        "evaluated_utc": doc.get("evaluated_utc"),
        "matrix_status": doc.get("status"),
        "n_families": len(fams),
        "n_verified_owned": sum(1 for f in fams.values() if f["ownership_credit"] == "VERIFIED_OWNED_EQUAL_OR_BETTER"),
        "n_behavioral_pass": sum(1 for f in fams.values() if f["behavioral_status"] == "PASS"),
        "n_quarantined_scope": sum(1 for f in fams.values() if str(f["scope_state"] or "").startswith("P1_WHOLE_SCOPE_QUARANTINED")),
        "families": fams,
        "summary_lists": {k: v for k, v in counts.items()},
        "broken_pointers": broken,
        "n_broken_pointers": sum(len(v) for v in broken.values()),
    }


def _count_mismatch() -> dict[str, Any]:
    """The frontier ownership file states counts in prose; check them against its own fields."""
    doc = json.loads(OPUS55_FRONTIER_FILE.read_text(encoding="utf-8"))
    status = str(doc.get("status", ""))
    accepted = re.findall(r"(\d+)_OF_(\d+)_ACCEPTED", status)
    owned = re.findall(r"(\d+)_OF_(\d+)_VERIFIED_OWNED", status)
    truth = doc.get("acceptance_truth") or {}
    owner = doc.get("ownership_truth") or {}
    problems: list[str] = []
    if accepted and int(accepted[0][0]) != int(truth.get("accepted_families", -1)):
        problems.append(
            f"status says {accepted[0][0]} of {accepted[0][1]} accepted; acceptance_truth says "
            f"{truth.get('accepted_families')} of {truth.get('total_families')}"
        )
    if owned and int(owned[0][0]) != int(owner.get("verified_owned_families", -1)):
        problems.append(
            f"status says {owned[0][0]} of {owned[0][1]} verified owned; ownership_truth says "
            f"{owner.get('verified_owned_families')} of {owner.get('total_families')}"
        )
    if int(truth.get("verified_owned_families", -1)) != int(owner.get("verified_owned_families", -2)):
        problems.append(
            f"acceptance_truth.verified_owned_families={truth.get('verified_owned_families')} but "
            f"ownership_truth.verified_owned_families={owner.get('verified_owned_families')}"
        )
    resid = re.findall(r"(\d+)_OF_(\d+)_FAMILIES_OPEN", str(doc.get("residual_gap", "")))
    if resid and accepted:
        open_families = int(truth.get("total_families", 0)) - int(truth.get("accepted_families", 0))
        if int(resid[0][0]) != open_families:
            problems.append(
                f"residual_gap says {resid[0][0]} of {resid[0][1]} families open; the fields imply "
                f"{open_families} open ({truth.get('accepted_families')} accepted of {truth.get('total_families')})"
            )
    return {
        "file": "canonical/capabilities/frontier/OPUS_5_5_USEFUL_CAPABILITY_OWNERSHIP_V1.json",
        "status_string": status,
        "agrees_with_fields": not problems,
        "problems": problems,
    }


def _law_terms() -> dict[str, Any]:
    try:
        from canonical.swe_kernel import capability_law_v1 as law  # type: ignore
    except Exception as exc:  # pragma: no cover - import failure is itself a finding
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    try:
        report = law.compose(pins=None)
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    terms = report.get("terms") or report.get("values") or {}
    out = {"available": True, "authority": report.get("authority")}
    if isinstance(terms, Mapping):
        vals = {}
        for k, v in terms.items():
            vals[k] = v.get("value") if isinstance(v, Mapping) else v
        out["terms"] = vals
    for key in ("operating_point", "p_correct", "p_correct_value", "headline"):
        if key in report:
            val = report[key]
            out[key] = {k: v for k, v in val.items() if not isinstance(v, (dict, list))} if isinstance(val, Mapping) else val
    out["report_keys"] = sorted(report)
    return out


def _benchmark_runs() -> dict[str, Any]:
    """Every committed CI report: the number, the gates, and whether it may be quoted."""
    arms_out: dict[str, Any] = {}
    # Only the *-latest.json roll-ups: they are what CI keeps current, and the timestamped
    # copies would otherwise double-count the same run.
    for path in sorted(EVAL_RESULTS.glob("*-latest.json")) if EVAL_RESULTS.is_dir() else []:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            arms_out[path.name] = {"error": f"UNPARSEABLE: {type(exc).__name__}"}
            continue
        arms = doc.get("arms") or {}
        summary = {}
        for arm, rep in sorted(arms.items()):
            if not isinstance(rep, Mapping):
                continue
            summary[arm] = {
                "resolved": rep.get("resolved"),
                "n_expected": rep.get("n_expected"),
                "model_calls": rep.get("model_calls"),
                "cost_usd": rep.get("cost_usd"),
                "n_missing_trial": rep.get("n_missing_trial"),
                "conditions": rep.get("conditions"),
                "engine_statuses": rep.get("engine_statuses"),
                "agent_wall_seconds_total": rep.get("agent_wall_seconds_total"),
            }
        # Pair a report with the receipt of ITS OWN mode, never with whatever receipt is lying
        # around: hard51-latest.json belongs to swe-pro-v2-hard51-receipt.json.
        parts = path.name[:-5].split("-")
        mode = next(
            (p for p in parts
             if p not in {"swe", "pro", "v2", "latest"} and not re.match(r"^\d{8}T\d{6}Z$", p)),
            None,
        )
        cand = sorted(EVAL_RESULTS.glob(f"*-{mode}-receipt.json")) if mode else []
        if not cand and mode:
            # A receipt committed by hand under canonical/verification is still the receipt for
            # that mode's run; bind it by name rather than pretending the report is uncertified.
            cand = sorted((ROOT / "canonical/verification").glob(f"*{mode.upper()}*RECEIPT*.json")) + \
                   sorted((ROOT / "canonical/verification").glob(f"*{mode.upper()}*_V1.json"))
        receipt = None
        if cand:
            try:
                receipt = json.loads(cand[0].read_text(encoding="utf-8"))
            except Exception as exc:
                receipt = {"error": f"{type(exc).__name__}"}
        arms_out[path.name] = {
            "schema": doc.get("schema"),
            "run_produced_number": doc.get("run_produced_number"),
            "run_failed": doc.get("run_failed"),
            "mode_inputs": doc.get("mode_inputs"),
            "gates": doc.get("gates"),
            "incomplete_shards": doc.get("incomplete_shards"),
            "n_arms": len(summary),
            "arms": summary,
            "receipt_file": cand[0].name if cand and receipt else None,
            "receipt_claimable": (receipt or {}).get("claimable_as_a_benchmark_number") if isinstance(receipt, Mapping) else None,
            "receipt_authority": (receipt or {}).get("authority") if isinstance(receipt, Mapping) else None,
            "receipt_why_not": (receipt or {}).get("why_not_claimable") if isinstance(receipt, Mapping) else None,
        }
    return {"n_reports": len(arms_out), "reports": arms_out}


def _root_ledgers() -> dict[str, Any]:
    """Ledgers are the project's claim surface; count them and name the newest."""
    files = sorted(ROOT.glob("*_20[0-9][0-9][0-9][0-9][0-9][0-9]_V[0-9].md"))
    dated: list[tuple[str, str]] = []
    for f in files:
        m = re.search(r"_(20\d{6})_V\d+\.md$", f.name)
        if m:
            dated.append((m.group(1), f.name))
    dated.sort(reverse=True)
    today = datetime.date.today().strftime("%Y%m%d")
    return {
        "run_date": today,
        "n_ledgers_dated_after_run_date": sum(1 for d, _ in dated if d > today),
        "ledgers_dated_after_run_date": [n for d, n in dated if d > today][:8],
        "n_root_ledgers": len(dated),
        "date_range": [dated[-1][0], dated[0][0]] if dated else None,
        "newest_15": [n for _, n in dated[:15]],
        "verification_receipts": len(list((ROOT / "canonical/verification").glob("*.json"))),
    }


def build() -> dict[str, Any]:
    tree = _git_blob_shas_at_head()
    inv = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "head": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                               capture_output=True, text=True).stdout.strip(),
        "n_tracked_files": len(tree),
        "model_calls": 0,
        "cost_usd": 0.0,
        "measured_capabilities": _true_capabilities(tree),
        "frontier_ownership_matrix": _frontier_matrix(),
        "frontier_self_report_consistency": _count_mismatch(),
        "capability_law": _law_terms(),
        "benchmark_runs": _benchmark_runs(),
        "claim_surface": _root_ledgers(),
    }
    inv["inventory_sha256_16"] = hashlib.sha256(
        json.dumps(inv, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]
    return inv


def to_markdown(inv: Mapping[str, Any]) -> str:
    mc = inv["measured_capabilities"]
    fm = inv["frontier_ownership_matrix"]
    cons = inv["frontier_self_report_consistency"]
    law = inv["capability_law"]
    runs = inv["benchmark_runs"]
    L: list[str] = []
    L.append("# Capability inventory, derived from the tree (no hand-typed numbers)\n")
    L.append(f"- head `{inv['head']}`, {inv['n_tracked_files']} tracked files, "
             f"inventory digest `{inv['inventory_sha256_16']}`")
    L.append(f"- authority: `{inv['authority']}`; model calls {inv['model_calls']}, cost ${inv['cost_usd']:.2f}\n")
    L.append("## What is measured against the bytes we ship")
    L.append(f"law on file: {mc['law_exists']} | ledger authority: `{mc['ledger_authority']}` | "
             f"{mc['n_pass']}/{mc['n_capabilities']} PASS | stale measurements: {mc['n_stale']}\n")
    L.append("| capability | verdict | fresh instances | pass rate | oracle classes | canary | binding |")
    L.append("|---|---|---|---|---|---|---|")
    for cap, r in mc["rows"].items():
        oc = "+".join(r["oracle_classes"]) or "-"
        L.append(f"| `{cap}` | {r['verdict']} | {r['instances']} | {r['fresh_pass_rate']} | {oc} | "
                 f"{r['canary_pass']} | {r['binding']} ({r['kernels_pinned']} kernels) |")
    L.append("")
    L.append("## Frontier ownership, per family (the repo's own comparison, dated "
             f"{fm['evaluated_utc']})")
    L.append(f"{fm['n_families']} families | verified-owned-or-better: {fm['n_verified_owned']} | "
             f"behavioral PASS: {fm['n_behavioral_pass']} | quarantined scope: {fm['n_quarantined_scope']} | "
             f"broken evidence pointers: {fm['n_broken_pointers']}\n")
    L.append("| family | status | ownership credit | behavioral | pointers | broken |")
    L.append("|---|---|---|---|---|---|")
    for fam, r in fm["families"].items():
        L.append(f"| {fam} | {r['status']} | {r['ownership_credit']} | {r['behavioral_status']} | "
                 f"{r['n_pointers']} | {r['n_broken_pointers']} |")
    if fm["broken_pointers"]:
        L.append("\nBroken pointers (the claim names a receipt that is not in the tree):\n")
        for fam, missing in fm["broken_pointers"].items():
            L.append(f"- `{fam}`: " + ", ".join(f"`{m}`" for m in missing))
    L.append("")
    L.append("## Self-reported counts vs the fields they summarize")
    if cons["agrees_with_fields"]:
        L.append("Agree. No drift found.\n")
    else:
        L.append(f"**Disagree** — the prose status and the numeric fields cannot both be true:\n")
        for p in cons["problems"]:
            L.append(f"- {p}")
        L.append(f"\nstatus string: `{cons['status_string']}`\n")
    L.append("## The capability law (imported, pinned receipts)")
    if law.get("available"):
        op = law.get("operating_point") or law.get("terms") or {}
        L.append(f"authority `{law.get('authority')}`; terms: "
                 + ", ".join(f"{k}={v}" for k, v in sorted(dict(op).items()) if isinstance(v, (int, float))))
        L.append("")
    else:
        L.append(f"UNAVAILABLE: {law.get('error')}\n")
    L.append("## Benchmark runs published by CI")
    L.append(f"{runs['n_reports']} committed report(s).\n")
    for name, r in runs["reports"].items():
        if not name.endswith("-latest.json"):
            continue
        L.append(f"### `{name}`")
        L.append(f"- produced a number: {r.get('run_produced_number')} | run_failed: {r.get('run_failed')} | "
                 f"inputs: `{json.dumps(r.get('mode_inputs'), sort_keys=True)}`")
        L.append(f"- gates: `{json.dumps(r.get('gates'), sort_keys=True)}` | incomplete shards: "
                 f"{json.dumps(r.get('incomplete_shards'))}")
        L.append(f"- receipt: `{r.get('receipt_file')}` claimable={r.get('receipt_claimable')} "
                 f"authority=`{r.get('receipt_authority')}`")
        for arm, a in sorted(dict(r.get("arms") or {}).items()):
            L.append(f"  - `{arm}`: {a.get('resolved')}/{a.get('n_expected')} "
                     f"(missing {a.get('n_missing_trial')}, calls {a.get('model_calls')}, "
                     f"${a.get('cost_usd')}) conditions=`{json.dumps(a.get('conditions'), sort_keys=True)}`")
        if r.get("receipt_why_not"):
            L.append("  - why not quotable: " + "; ".join(str(x)[:160] for x in r["receipt_why_not"]))
        L.append("")
    cs = inv["claim_surface"]
    L.append(f"## Claim surface: {cs['n_root_ledgers']} dated ledgers at the repo root "
             f"({cs['date_range'][0]}..{cs['date_range'][1]}) and {cs['verification_receipts']} verification receipts")
    L.append("Newest 15:")
    for n in cs["newest_15"]:
        L.append(f"- `{n}`")
    if cs["n_ledgers_dated_after_run_date"]:
        L.append(f"\n**Date hygiene:** {cs['n_ledgers_dated_after_run_date']} ledgers carry an as-of date after "
                 f"the date this inventory was built ({cs['run_date']}), e.g. "
                 + ", ".join(f"`{n}`" for n in cs["ledgers_dated_after_run_date"]) +
                 ". A ledger date is a label, not a measurement; nothing here treats it as one.")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--md-out", default=None)
    args = ap.parse_args(argv)
    inv = build()
    md = to_markdown(inv)
    if args.json_out:
        p = pathlib.Path(args.json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(inv, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    if args.md_out:
        p = pathlib.Path(args.md_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(md, encoding="utf-8")
    if not args.json_out and not args.md_out:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

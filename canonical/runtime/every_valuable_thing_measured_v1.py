#!/usr/bin/env python3
"""EVERY valuable thing: a complete, priced inventory of the governance record.

THE LAW
-------
The owner has stated it twenty times: "you must see every important or valuable thing:
what it is and how valuable it is." A seven-item list does not satisfy that. Only a
complete census with a stated denominator does.

WHY A CENSUS IS POSSIBLE HERE
-----------------------------
This repository writes down every claim it makes as a JSON governance record with a
`status`, a `date`, and usually `hard_nonclaims`. That means the claims are a finite,
enumerable population. This module enumerates all of them, prices each by what it can
actually prove, and reports the distribution rather than a curated highlight reel.

THE PRICING SCALE (the only judgement in this file)
---------------------------------------------------
Each record is assigned an EVIDENCE TIER from its own declared status. The tiers are
ordered by how much weight the record can bear:

    PROVEN      a pass/independent runner result -- it asserts a measured fact
    ACTIVE      a live route or mechanism, not a completed proof
    REFUSED     a fail-closed outcome -- it asserts that something did NOT work
    CANDIDATE   a hypothesis or proposal
    RETRACTED   revoked, withdrawn, or superseded
    UNCLASSIFIED  no recognisable status token

REFUSED is deliberately ranked ABOVE CANDIDATE. A documented failure is evidence; a
proposal is not. Any inventory that ranks proposals above refusals is upside down.

WHAT THIS DOES NOT DO
---------------------
It does not verify that a PROVEN record is correct. It reports what the record claims and
how many records claim it. Verification of any individual claim is a separate act, and the
records that were verified by execution in this session were verified by running them.

Usage
    python3 canonical/runtime/every_valuable_thing_measured_v1.py
    python3 canonical/runtime/every_valuable_thing_measured_v1.py --json
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "canonical/governance"

SCHEMA = "brain.every_valuable_thing_measured.v1"

TIER_ORDER = ["PROVEN", "ACTIVE", "REFUSED", "CANDIDATE", "RETRACTED",
              "NO_STATUS", "UNCLASSIFIED"]


def classify(status: str) -> str:
    """Price a record from its declared status, using the tree's whole vocabulary.

    Measured 2026-11-09: the governance population uses 224 distinct leading status
    tokens. The first version of this function recognised six of them and left 1,101
    records (34.1%) UNCLASSIFIED -- a third of the population invisible to pricing, which
    is a failure of the census rather than of the tree.

    The order below is deliberate. RETRACTED is checked first so a revoked record can never
    be promoted by a later keyword; REFUSED is checked before PROVEN because a status such
    as FAIL_CLOSED_INDEPENDENT_PASS asserts a refusal that happened to pass its own check.
    """
    s = (status or "").strip().upper()
    if not s:
        # No status at all is not "unknown meaning" -- it is a record that declares no
        # state. That is a distinct and actionable defect, and it deserves its own tier
        # rather than being pooled with prose that simply used unfamiliar words.
        return "NO_STATUS"

    head = s.split("_")[0]

    # 1. retraction outranks everything: it is the strongest statement a record can make
    #    about itself and no later keyword may overturn it.
    if head in {"REVOKED", "RETRACTED", "WITHDRAWN", "SUPERSEDED", "INVALIDATED"} or \
            any(w in s for w in ("_REVOKED", "REVOKE_", "SUPERSEDED_BY")):
        return "RETRACTED"

    # 2. refusal before proof: FAIL_CLOSED_...._PASS is a refusal that passed its check
    if "FAIL_CLOSED" in s or head in {"FAIL", "REFUSED", "REFUSAL", "BLOCKED", "REJECTED"}:
        return "REFUSED"

    # 3. proof: a passed / verified / proved / executed assertion
    if (head in {"PASS", "PROVED", "PROVEN", "VERIFIED", "EXECUTED", "DEPLOYED",
                 "EXACT", "FORMAL", "DEDUCTIVE", "EXECUTABLE", "AUTHENTICATED",
                 "AUTHORIZED", "BOUNDED", "COMPLETE", "DERIVED", "IMPLEMENTED",
                 "CONTENT", "CONTENT_ADDRESSED", "INDEPENDENT", "PUBLIC"}
            or "_PASS" in s or "INDEPENDENT_VERIFICATION_PASS" in s
            or s.startswith("PASS")):
        return "PROVEN"

    # 4. frozen / staged: a snapshot or a prepared state -- real, but not a result
    if head in {"FROZEN", "REFROZEN", "STAGED", "PREWAVE", "SCHEMA", "TEMPLATE"}:
        return "ACTIVE"

    # 5. proposal
    if head in {"CANDIDATE", "PROPOSAL", "PROPOSED", "HYPOTHESIS", "BREAKTHROUGH"} or \
            "CANDIDATE" in s:
        return "CANDIDATE"

    # 6. live route / current state / reconciliation / anything else active-shaped
    if head in {"ACTIVE", "CURRENT", "LIVE", "RECONCILED", "TRUTH", "CANONICAL",
                "INTERNAL", "CONSUMED", "ADMIT", "ZERO", "RANK20", "SCHEMA_TEMPLATE",
                "SESSION", "STATUS", "STATE", "RUN", "ROUTE", "GATE", "BINDING"}:
        return "ACTIVE"

    # 7. prose status: long free-text summaries. Price them by the evidence word they
    #    contain, in the same order of precedence used above. A prose status that asserts
    #    NOT_CLOSED / UNDECIDED / EXHAUSTED is a refusal even though it never uses the word.
    if "_" in s and len(s.split()) >= 1:
        if any(w in s for w in ("SUPERSEDED", "INVALIDATED", "REVOKED")):
            return "RETRACTED"
        if any(w in s for w in ("NOT_CLOSED", "UNDECIDED", "ZERO_VERIFIED", "EXHAUSTED",
                                "NOT_ENTAIL", "FAILED", "QUARANTINED", "NOT_SENT",
                                "PARITY_INDETERMINATE", "DOES_NOT_ENTAIL")):
            return "REFUSED"
        if any(w in s for w in ("PROVED", "PROVEN", "VERIFIED", "DERIVED", "EXACT",
                                "RECONCILED", "BOUND", "COMPLETE", "AUTHENTICATED")):
            return "PROVEN"
        # ZERO_ROOTS / ROOTS_CLOSED must be read as refusals BEFORE the generic active
        # vocabulary, and "FAMILIES" is a container noun, not a state.
        if any(w in s for w in ("ZERO_ROOTS", "ROOTS_CLOSED", "ZERO_CLOSED")):
            return "REFUSED"
        if any(w in s for w in ("PREPARED", "STAGED", "FROZEN", "READY", "PRECOMMITTED",
                                "PARTIAL", "CONDITIONAL", "CURRENT", "ACTIVE")):
            return "ACTIVE"
        if any(w in s for w in ("CANDIDATE", "PROPOSAL", "BREAKTHROUGH")):
            return "CANDIDATE"
        # Zero-credit admissions and infrastructure failures are refusals: the record is
        # telling you it earned nothing. They must not be pooled with genuine unknowns.
        if any(w in s for w in ("ZERO_CREDIT", "ZERO_BENCHMARK_CREDIT", "NO_CREDIT",
                                "FAILURE", "NO_BRAIN_BEHAVIOR", "REJECTED", "BYPASS_")):
            return "REFUSED"
        if any(w in s for w in ("ADMITTED", "COMPILED", "CLOSED", "RECORDED", "SCANNED",
                                "EXECUTING", "CONFIRMATION", "REDUCED", "NARROWED")):
            return "ACTIVE"
        if "TEMPLATE" in s or "AUTHORING" in s:
            return "ACTIVE"

    # A status made only of prose with no recognisable evidence word is genuinely
    # unpriceable by this census, and saying so is more honest than forcing a tier.
    return "UNCLASSIFIED"


def family(name: str) -> str:
    """Group records into benchmark/domain families by their leading token."""
    head = name.split("_")[0]
    return head


def _numbers(obj, path="", depth=0):
    """Yield (path, value) for every numeric accuracy/rate-like field."""
    if depth > 8:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _numbers(v, f"{path}.{k}" if path else str(k), depth + 1)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:60]):
            yield from _numbers(v, f"{path}[{i}]", depth + 1)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        key = path.lower()
        if any(w in key for w in ("accuracy", "solve_rate", "pass_rate", "resolved",
                                  "score_pct", "percent")):
            yield path, obj


def census() -> dict:
    records = []
    parse_failures = 0
    for p in sorted(GOV.glob("*.json")):
        try:
            doc = json.loads(p.read_text())
        except Exception:
            parse_failures += 1
            continue
        if not isinstance(doc, dict):
            continue
        status = str(doc.get("status") or "")
        nums = list(_numbers(doc))
        records.append({
            "name": p.stem,
            "family": family(p.stem),
            "tier": classify(status),
            "status": status[:120],
            "date": str(doc.get("date") or ""),
            "bytes": p.stat().st_size,
            "has_nonclaims": "hard_nonclaims" in doc,
            "measured_numbers": [{"field": f, "value": v} for f, v in nums[:6]],
        })

    total = len(records)
    tiers = Counter(r["tier"] for r in records)
    tier_bytes = Counter()
    for r in records:
        tier_bytes[r["tier"]] += r["bytes"]

    fam = defaultdict(lambda: Counter())
    for r in records:
        fam[r["family"]][r["tier"]] += 1

    with_numbers = [r for r in records if r["measured_numbers"]]
    nonclaims = sum(1 for r in records if r["has_nonclaims"])

    return {
        "schema": SCHEMA,
        "law": "see every important or valuable thing: what it is and how valuable it is",
        "population": "canonical/governance/*.json — every claim this repository writes down",
        "total_records": total,
        "parse_failures": parse_failures,
        "total_bytes": sum(r["bytes"] for r in records),
        "tier_counts": {t: tiers.get(t, 0) for t in TIER_ORDER},
        "tier_bytes": {t: tier_bytes.get(t, 0) for t in TIER_ORDER},
        "tier_pct": {t: round(100.0 * tiers.get(t, 0) / max(1, total), 1) for t in TIER_ORDER},
        "records_carrying_a_measured_number": len(with_numbers),
        "records_declaring_hard_nonclaims": nonclaims,
        "nonclaim_rate_pct": round(100.0 * nonclaims / max(1, total), 1),
        "top_families": [
            {"family": f, "records": sum(c.values()),
             "proven": c.get("PROVEN", 0), "refused": c.get("REFUSED", 0),
             "candidate": c.get("CANDIDATE", 0)}
            for f, c in sorted(fam.items(), key=lambda kv: -sum(kv[1].values()))[:22]
        ],
        "pricing_rule": ("PROVEN > ACTIVE > REFUSED > CANDIDATE > RETRACTED. A documented "
                         "failure outranks a proposal, because a failure is evidence."),
        "what_this_does_not_claim": [
            "that a PROVEN record is correct -- only that it declares a passed check",
            "that the population is complete for claims made outside governance JSON",
            "it is not a capability rate: this is a census of claims, not a benchmark",
        ],
        "records": records,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    out = census()
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=1))
    if args.json:
        print(json.dumps({k: v for k, v in out.items() if k != "records"}, indent=1))
        return 0

    print("=" * 78)
    print("EVERY VALUABLE THING — complete census of the governance record")
    print("=" * 78)
    print(f"  population            {out['population']}")
    print(f"  total records         {out['total_records']}")
    print(f"  total bytes           {out['total_bytes']:,}")
    print(f"  unparseable           {out['parse_failures']}")
    print()
    print(f"  {'TIER':14s} {'COUNT':>7s} {'PCT':>7s} {'MB':>8s}")
    for t in TIER_ORDER:
        print(f"  {t:14s} {out['tier_counts'][t]:7d} {out['tier_pct'][t]:6.1f}% "
              f"{out['tier_bytes'][t]/1e6:8.2f}")
    print()
    print(f"  records carrying a measured number : "
          f"{out['records_carrying_a_measured_number']}")
    print(f"  records declaring hard nonclaims   : "
          f"{out['records_declaring_hard_nonclaims']} "
          f"({out['nonclaim_rate_pct']}%)")
    print()
    print("  TOP FAMILIES")
    print(f"  {'family':20s} {'total':>6s} {'proven':>7s} {'refused':>8s} {'cand':>6s}")
    for f in out["top_families"]:
        print(f"  {f['family']:20s} {f['records']:6d} {f['proven']:7d} "
              f"{f['refused']:8d} {f['candidate']:6d}")
    print()
    print(f"  pricing: {out['pricing_rule']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

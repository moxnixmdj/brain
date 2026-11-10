#!/usr/bin/env python3
"""CENSUS V1 — every valuable thing in this repository, named and priced.

THE LAW
-------
"You must see every important or valuable thing: what it is and how valuable it is."

A list of 16,312 files is not a census; it is a phone book. A census must be
(a) GENERATED from the repository, so completeness is provable rather than asserted,
(b) RANKED by value, so the important things are at the top, and
(c) EXPLICIT about what could not be priced.

WHAT THIS DOES
--------------
1. Walks every git-tracked file.
2. Prices each one on EVIDENCE IN THE FILE ITSELF, never on its name alone:
     - does it carry a verification/refusal vocabulary (proof machinery)?
     - does it carry a benchmark measurement?
     - is it reachable from the one model (`BRAIN_UNIFIED_MODEL_V1.json`)?
     - what does it actually define (entry points, tests, schemas)?
3. Assigns a tier, and reports totals per tier with the bytes each tier represents.
4. Emits the gap lists: things on disk that the one model cannot see.

VALUE IS NOT SIZE
-----------------
A 40-line verifier that can refute a claim outranks a 3,000-line module that only
formats output. The pricing below encodes that ordering explicitly, and every weight
is printed so it can be argued with.

Usage
    python3 canonical/runtime/census_every_valuable_thing_v1.py            # summary
    python3 canonical/runtime/census_every_valuable_thing_v1.py --json     # machine
    python3 canonical/runtime/census_every_valuable_thing_v1.py --top 50   # ranked
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNIFIED = ROOT / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"

# ---- PRICING -------------------------------------------------------------------
# Each signal is evidence a reader can check in the file. The weights say what this
# project values: the ability to REFUTE and PROVE outranks the ability to produce.
SIGNALS = [
    # (name, tier, weight, regex over the file head)
    ("REFUSAL__CAN_SAY_NO",      1, 10, r"fail_closed|FAIL_CLOSED|refus\w*|ABSTAIN|abstain"),
    ("VERIFICATION__CAN_CHECK",  1,  9, r"\bverif\w*|\bverdict\b|recompute|assert_\w+"),
    ("THEOREM__CAN_PROVE_LIMIT", 1,  9, r"no[_ ]go|impossib\w*|lower_bound|nonidentifiab\w*|noninversion"),
    ("BENCHMARK__HAS_A_NUMBER",  1,  8, r"\b\d+/\d+\b.*\b(pass|verified|correct)\b|accura\w*|score\b"),
    ("TASK_GENERATOR__MAKES_TRUTH", 2, 7, r"task_generator|generate_task|make_task|challenge"),
    ("COMPOSITION__COMBINES",    2,  6, r"\bcompos\w*|\bpipeline\b|\bchain\b|\bbridge\b"),
    ("ROUTING__CHOOSES",         2,  6, r"\broute\b|\bdispatch\b|\bcandidate\w*|\brank\b"),
    ("LEARNING__CHANGES_ITSELF", 2,  6, r"\blearn\w*|\bmemor\w*|_CACHE|memo\w*"),
    ("SEMANTICS__MEANS_NOT_SPELLS", 2, 6, r"semantic\w*|hyperdimensional|embedding|neighbou?r"),
    ("INSTANT__NO_TRAINING",     2,  5, r"zero[_ ](?:trained|learned)|no[_ ]weights|gradient_steps"),
    ("EXECUTION__ACTS",          3,  4, r"subprocess|os\.exec|Popen|execute\w*"),
    ("PERSISTENCE__REMEMBERS",   3,  3, r"\bjson\.dump|write_text|sqlite|ledger\b"),
    ("TEST__PINS_BEHAVIOUR",     3,  3, r"def test_|unittest|pytest"),
    ("GOVERNANCE__SETS_A_RULE",  3,  3, r"\blaw\b|\bpolicy\b|\bprecommit\b|agreement"),
    ("SPEED__MEASURED_LATENCY",  3,  3, r"perf_counter|time\.time|micros|\bms\b|\bs\b.*tok"),
    ("CENSUS__COUNTS_THINGS",    3,  2, r"\bcensus\b|\binventory\b|\bcoverage\b"),
]

TIER_NAME = {
    1: "TIER 1 — CAN REFUTE, PROVE, OR MEASURE",
    2: "TIER 2 — CAN REASON, COMPOSE, ROUTE, LEARN",
    3: "TIER 3 — CAN ACT, REMEMBER, PIN, GOVERN",
    4: "TIER 4 — SUPPORT, FORMAT, GLUE",
}

TEXT_EXT = {".py", ".md", ".json", ".jsonl", ".txt", ".yml", ".yaml", ".toml", ".cfg",
            ".stub", ".sh", ".sql"}
MAX_READ = 220_000


def _git_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    return [p for p in out.stdout.splitlines() if p]


def _read(p: Path) -> str:
    try:
        if p.stat().st_size > MAX_READ:
            with p.open("rb") as fh:
                return fh.read(MAX_READ).decode("utf-8", "ignore")
        return p.read_text("utf-8", "ignore")
    except OSError:
        return ""


def _count_defs(text: str) -> dict:
    return {
        "defs": len(re.findall(r"^(?:def|class)\s+\w+", text, re.M)),
        "tests": len(re.findall(r"^def test_\w+", text, re.M)),
        "schemas": len(re.findall(r'^SCHEMA\s*=|"schema"\s*:', text, re.M)),
        "refusals": len(re.findall(r"FAIL_CLOSED|fail_closed|ABSTAIN", text)),
        "verdicts": len(re.findall(r"\bverdict\b|\bverified\b", text, re.I)),
    }


def _model_reach() -> dict:
    """What the one model can already see."""
    if not UNIFIED.exists():
        return {"paths": set(), "capabilities": set(), "counts": {}}
    d = json.loads(UNIFIED.read_text())
    paths = {e.get("path") for e in d.get("source_index") or [] if e.get("path")}
    caps = set()
    for c in d.get("capabilities") or []:
        for k in ("id", "capability_id"):
            if c.get(k):
                caps.add(c[k])
    return {"paths": paths, "capabilities": caps, "counts": d.get("counts") or {},
            "non_claims": d.get("non_claims") or [],
            "objective": d.get("objective") or {}, "theory": d.get("theory") or {}}


def price(files: list[str], model: dict) -> list[dict]:
    rows = []
    for rel in files:
        p = ROOT / rel
        if not p.is_file():
            continue
        size = p.stat().st_size
        ext = p.suffix.lower()
        text = _read(p) if ext in TEXT_EXT else ""
        head = text[:60_000]

        hits, score, tiers = [], 0, []
        for name, tier, weight, pat in SIGNALS:
            n = len(re.findall(pat, head, re.I))
            if n:
                bonus = weight * (1 + min(n, 20) / 20.0)   # present twice is worth more
                score += bonus
                hits.append({"signal": name, "tier": tier, "n": n,
                             "worth": round(bonus, 1)})
                tiers.append(tier)

        defs = _count_defs(head) if text else {}
        # reachability from the one model is itself valuable: unseen is unspent
        reachable = rel in model["paths"]
        if reachable:
            score += 3.0
        rows.append({
            "path": rel,
            "bytes": size,
            "score": round(score, 1),
            "tier": min(tiers) if tiers else 4,
            "reachable": reachable,
            "signals": hits,
            "defs": defs,
        })
    rows.sort(key=lambda r: (-r["score"], -r["bytes"]))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("--all", action="store_true", help="list every priced file")
    args = ap.parse_args(argv)

    files = _git_files()
    model = _model_reach()
    rows = price(files, model)

    by_tier = defaultdict(list)
    for r in rows:
        by_tier[r["tier"]].append(r)

    total_bytes = sum(r["bytes"] for r in rows)
    reach = [r for r in rows if r["reachable"]]
    summary = {
        "files_walked": len(files),
        "files_priced": len(rows),
        "bytes_total": total_bytes,
        "reachable_by_one_model": len(reach),
        "unreachable": len(rows) - len(reach),
        "unreachable_but_priced": len([r for r in rows if not r["reachable"] and r["score"] > 0]),
        "tiers": {t: {"files": len(v),
                      "bytes": sum(x["bytes"] for x in v),
                      "top_score": max((x["score"] for x in v), default=0.0)}
                  for t, v in sorted(by_tier.items())},
        "tier_names": TIER_NAME,
        "pricing_weights": [{"signal": s[0], "tier": s[1], "weight": s[2]} for s in SIGNALS],
        "model_counts": model.get("counts") or {},
        "model_theory": model.get("theory") or {},
        "model_non_claims": model.get("non_claims") or [],
    }

    if args.json:
        print(json.dumps({"summary": summary,
                          "rows": rows if (args.all or args.top == 0) else rows[:args.top]},
                         indent=1))
        return 0

    print("=" * 78)
    print("CENSUS — every tracked file, priced by evidence inside the file")
    print("=" * 78)
    print(f"files walked {summary['files_walked']:,}   priced {summary['files_priced']:,}   "
          f"bytes {total_bytes:,}")
    print(f"visible to the one model: {summary['reachable_by_one_model']:,}   "
          f"NOT visible: {summary['unreachable']:,}   "
          f"(of those, {summary['unreachable_but_priced']:,} carry real signals)")
    print()
    for t, v in sorted(summary["tiers"].items()):
        print(f"  {TIER_NAME[t]}")
        print(f"      {v['files']:>6,} files   {v['bytes']:>12,} bytes   "
              f"top score {v['top_score']}")
    print()
    print("THE ONE MODEL ALREADY SEE (counts from its own artifact):")
    for k, v in sorted(summary["model_counts"].items()):
        print(f"  {v:>6,}  {k}")
    print()
    print("ITS OWN NON-CLAIMS (what it refuses to assert):")
    for c in summary["model_non_claims"]:
        print("  -", c)

    n = args.top or 25
    print()
    print(f"TOP {n} BY VALUE")
    for i, r in enumerate(rows[:n], 1):
        seen = "seen" if r["reachable"] else "----"
        print(f"{i:>3}. [{seen}] {r['score']:>6.1f}  T{r['tier']}  {r['path']}")
        if r["signals"]:
            top = ", ".join(f"{h['signal'].split('__')[0]}x{h['n']}"
                            for h in sorted(r["signals"], key=lambda h: -h["worth"])[:3])
            print(f"          {top}")
    if args.all:
        print()
        print("EVERY PRICED FILE")
        for r in rows:
            print(f"{r['score']:>6.1f}  T{r['tier']}  {r['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

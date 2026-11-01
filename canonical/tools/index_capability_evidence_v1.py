#!/usr/bin/env python3
"""Make this repository findable, so "it's in here somewhere" is a query and not an argument.

Why this exists
---------------
On 2026-11-01 an agent spent five turns telling the owner that instant learning and
cross-environment transfer were unsolved. Both were solved. The mechanisms were present the
whole time under names nobody would guess::

    THE_SECOND_TIME_IS_INSTANT_V1_20261101_V1
    A_VARIANT_IS_NOT_A_NEW_PROBLEM_V1_20261101_V1
    LEARNED_ONCE_IS_FAST_ON_THE_NEXT_MACHINE_V1_20261101_V1
    elevate_trace_to_fastest_layer        (pixel/UI trace -> sqlite in <2 ms)
    ignorance_ledger_v1                   (ranks what it does not know by expected value)

Searching for `instant_learning`, `cross_language` or `observation_abstraction` returns
nothing. **Absence of a name is not absence of a mechanism**, and a 15,900-file tree with 722
action intents cannot be searched by guessing filenames.

What this builds
----------------
One index over the two corpora that actually carry the evidence:

  1. every action intent — its id, its `measured_effect`, the modules it names, its claimed
     progress class;
  2. every module under `canonical/` — its docstring headline and the capability ids it
     declares.

Then a keyword query that returns *where to look*, ranked by where the word appears
(measured_effect > intent summary > module docstring > filename). It is deterministic,
stdlib-only, and reads nothing it does not print.

Usage
-----
    python3 canonical/tools/index_capability_evidence_v1.py build
    python3 canonical/tools/index_capability_evidence_v1.py search transfer environment
    python3 canonical/tools/index_capability_evidence_v1.py search learning --limit 20
    python3 canonical/tools/index_capability_evidence_v1.py stats

The index is written to `canonical/evidence/CAPABILITY_EVIDENCE_INDEX_V1.json` and is
regenerated, never hand-edited.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
INTENTS = ROOT / "canonical" / "action_intents"
CANONICAL = ROOT / "canonical"
INDEX_PATH = CANONICAL / "evidence" / "CAPABILITY_EVIDENCE_INDEX_V1.json"

SCHEMA = "PROJECT_BRAIN_CAPABILITY_EVIDENCE_INDEX_V1"

_MODULE_REF = re.compile(r"canonical/[A-Za-z0-9_/]+\.py")
_TEST_REF = re.compile(r"canonical/tests/[A-Za-z0-9_/]+\.py")


# --------------------------------------------------------------------------- intents
def _intent_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not INTENTS.is_dir():
        return rows
    for path in sorted(INTENTS.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        blob = json.dumps(data)
        orient = data.get("agent_orientation") if isinstance(data.get("agent_orientation"), dict) else {}
        rows.append({
            "kind": "ACTION_INTENT",
            "id": str(data.get("action_id") or path.stem),
            "path": path.relative_to(ROOT).as_posix(),
            "date": str(data.get("date") or ""),
            "progress_class": str(orient.get("progress_class") or ""),
            "route_class": str(orient.get("route_class") or ""),
            "spend_usd": orient.get("incremental_spend_usd"),
            "model_dependency_count": orient.get("producer_cognition_model_dependency_count"),
            "measured_effect": str(data.get("measured_effect") or "")[:2000],
            "summary": str(data.get("action_summary") or "")[:2000],
            "modules": sorted(set(_MODULE_REF.findall(blob))),
            "tests": sorted(set(_TEST_REF.findall(blob))),
            "capability_credit_delta": data.get("capability_credit_delta"),
        })
    return rows


# --------------------------------------------------------------------------- modules
def _first_docstring(path: Path) -> str:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return ""
    doc = ast.get_docstring(tree) or ""
    if doc:
        return " ".join(doc.strip().split())[:600]
    try:
        src = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return ""
    for line in src[:40]:
        s = line.strip()
        if s.startswith('"""') or s.startswith("'''"):
            return " ".join(s.strip("\"'").split())[:300]
    return ""


def _module_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(CANONICAL.rglob("*.py")):
        if any(part in {"__pycache__", "tests", "fixtures", "vendored"} for part in path.parts):
            continue
        rel = path.relative_to(ROOT).as_posix()
        text = ""
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[:20000]
        except Exception:
            pass
        cap = ""
        m = re.search(r'^CAPABILITY_ID\s*=\s*["\']([^"\']+)', text, re.M)
        if m:
            cap = m.group(1)
        schema = ""
        m = re.search(r'^SCHEMA\s*=\s*["\']([^"\']+)', text, re.M)
        if m:
            schema = m.group(1)
        rows.append({
            "kind": "MODULE",
            "id": path.stem,
            "path": rel,
            "capability_id": cap,
            "schema": schema,
            "doc": _first_docstring(path),
            "lines": text.count("\n") + (1 if text else 0),
        })
    return rows


# --------------------------------------------------------------------------- build/search
def build() -> dict[str, Any]:
    index = {
        "schema": SCHEMA,
        "root": str(ROOT),
        "counts": {},
        "intents": _intent_rows(),
        "modules": _module_rows(),
    }
    index["counts"] = {"intents": len(index["intents"]), "modules": len(index["modules"])}
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return index


def _load() -> dict[str, Any]:
    if not INDEX_PATH.is_file():
        return build()
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def _score(row: dict[str, Any], terms: Iterable[str]) -> int:
    """Where the word appears decides how much it is worth."""
    weighted = [
        (str(row.get("measured_effect") or ""), 6),
        (str(row.get("summary") or ""), 3),
        (str(row.get("doc") or ""), 2),
        (str(row.get("id") or ""), 2),
        (str(row.get("path") or ""), 1),
        (str(row.get("capability_id") or ""), 2),
    ]
    total = 0
    for term in terms:
        low = term.lower()
        for text, weight in weighted:
            if low in text.lower():
                total += weight
    return total


def search(terms: list[str], *, limit: int = 15, want: str = "all") -> list[dict[str, Any]]:
    index = _load()
    pool: list[dict[str, Any]] = []
    if want in ("all", "intents"):
        pool += index.get("intents") or []
    if want in ("all", "modules"):
        pool += index.get("modules") or []
    scored = [(s, r) for r in pool if (s := _score(r, terms)) > 0]
    scored.sort(key=lambda t: (-t[0], t[1].get("path", "")))
    return [dict(r, _score=s) for s, r in scored[:limit]]


def _print(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("  (nothing matched — try a narrower term, or a synonym; the mechanism may be\n"
              "   named for its effect rather than its subject, e.g. THE_SECOND_TIME_IS_INSTANT)")
        return
    for r in rows:
        tag = "INTENT" if r["kind"] == "ACTION_INTENT" else "MODULE"
        print(f"[{r['_score']:>2}] {tag} {r['id']}")
        print(f"      {r['path']}")
        if r.get("measured_effect"):
            print(f"      measured: {r['measured_effect'][:300]}")
        elif r.get("doc"):
            print(f"      doc: {r['doc'][:220]}")
        if r.get("modules"):
            print(f"      modules: {', '.join(r['modules'][:4])}")
        print()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("build", help="regenerate the index")
    p_search = sub.add_parser("search", help="find where a capability lives")
    p_search.add_argument("terms", nargs="+")
    p_search.add_argument("--limit", type=int, default=15)
    p_search.add_argument("--only", choices=["all", "intents", "modules"], default="all")
    sub.add_parser("stats", help="counts and the newest measured intents")

    args = ap.parse_args(argv)

    if args.cmd == "build":
        index = build()
        print(f"indexed {index['counts']['intents']} action intents, "
              f"{index['counts']['modules']} modules -> {INDEX_PATH.relative_to(ROOT)}")
        return 0

    if args.cmd == "stats":
        index = _load()
        print(f"action intents : {index['counts']['intents']}")
        print(f"modules        : {index['counts']['modules']}")
        intents = index.get("intents") or []
        with_effect = [i for i in intents if i.get("measured_effect")]
        print(f"intents carrying a measured_effect: {len(with_effect)}")
        zero_credit = [i for i in with_effect
                       if i.get("model_dependency_count") == 0 and i.get("spend_usd") == 0]
        print(f"  ...of those, zero model dependency and zero spend: {len(zero_credit)}")
        print("\nmost recent ten with a measured effect:")
        for i in sorted(with_effect, key=lambda x: x.get("date") or "", reverse=True)[:10]:
            print(f"  {i.get('date') or '?':10} {i['id'][:66]}")
        return 0

    rows = search(args.terms, limit=args.limit, want=args.only)
    print(f"query: {' '.join(args.terms)}  ({len(rows)} hit(s))\n")
    _print(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

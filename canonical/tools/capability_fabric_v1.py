#!/usr/bin/env python3
"""The composition fabric of this repository: what is actually connected to what, derived on every run.

WHY THIS EXISTS
---------------
The diagnosis "we have tons of advanced capabilities and they are thrown everywhere" is only usable
if it is a number, because the fix has to be judged by a number moving. This script computes the
import graph over every Python module under `canonical/`, the certified-capability manifest derived
from the harness ledger and the frontier matrix (never typed by hand), and a per-module reachability
class. It also has a --check mode for CI: the committed fabric must equal what the tree implies, so
the picture cannot go stale the way the ownership matrix's prose counts did.

What it deliberately measures, and why each one matters for unification:

* **components** — islands of modules that share no import edge. If the count is high, "one model"
  is not a missing refactor of a big module, it is a missing *fabric*.
* **private_schemas** — distinct `SCHEMA = "..."` string constants. Every one is a bespoke envelope
  that a composed edge must translate; this is the real cost of composition, and it is the number a
  shared envelope drives down. Unification is measured here, not in renamed directories.
* **entry_points** — modules with their own `main()`. Each is a separate way in; a system has one.
* **max_fan_out** — the widest importer in the tree. This is the honest ceiling for "just write an
  orchestrator that imports everything": the tree does not currently compose at scale anywhere.
* **certified** — capabilities with a receipt. Everything else is a candidate, so the fabric lists
  what may be wired into the root, and the manifest carries the binding (module, entry, spec,
  receipt, blob) that makes a wiring auditable. `--check` gates *this* part and no other, because a
  check that fires on unrelated tree growth gets deleted rather than obeyed.

Model calls: 0. Network: 0. Cost: $0.00. Deterministic: no timestamps in the checked payload.
"""
from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[2]
TRUE_LEDGER = ROOT / "canonical/capabilities/true/TRUE_CAPABILITY_LEDGER_V1.json"
OWNERSHIP_MATRIX = ROOT / "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"
SCHEMA_RE = re.compile(r"^\s*SCHEMA\s*=\s*[\"']([^\"']+)[\"']", re.M)
AUTHORITY_RE = re.compile(r"^\s*AUTHORITY\s*=\s*[\"']([^\"']+)[\"']", re.M)
MAIN_RE = re.compile(r"^\s*def main\(", re.M)
# A trailing comment is not a different kind of entry point: do not anchor the pattern to end of line.
# The first version did (`...\s*:` with re.M only), and an independent AST scan caught it: 1,694
# regex hits vs 2,687 top-level guards. Reported here so the fix is on the record, not in a footnote.
GUARD_RE = re.compile(r"""^\s*if\s+__name__\s*==\s*["']__main__["']\s*:""", re.M)
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+(canonical(?:\.[A-Za-z0-9_]+)*)", re.M)


def _modules() -> dict[str, pathlib.Path]:
    out: dict[str, pathlib.Path] = {}
    for p in sorted(ROOT.glob("canonical/**/*.py")):
        if "__pycache__" in p.parts:
            continue
        rel = p.relative_to(ROOT).as_posix()
        out[rel[:-3].replace("/", ".")] = p
    return out


def _import_edges(mods: Mapping[str, pathlib.Path]) -> tuple[dict[str, set[str]], collections.Counter]:
    graph: dict[str, set[str]] = {}
    indeg: collections.Counter = collections.Counter()
    for mod, path in mods.items():
        text = path.read_text(encoding="utf-8", errors="replace")
        targets = {t for t in IMPORT_RE.findall(text) if t in mods and t != mod}
        graph[mod] = targets
        for t in targets:
            indeg[t] += 1
    return graph, indeg


def _components(mods: Mapping[str, Any], graph: dict[str, set[str]]) -> list[str]:
    parent = {m: m for m in mods}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, nbrs in graph.items():
        for b in nbrs:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
    sizes = collections.Counter(find(m) for m in mods)
    return sorted((f"{n}" for n in sizes.values()), key=lambda s: (-int(s), s))


def _classify(mods: Mapping[str, pathlib.Path], graph: dict[str, set[str]],
              indeg: collections.Counter, is_test: dict[str, bool]) -> dict[str, int]:
    """Reachability class per module. Import order matters: CERTIFIED beats everything, an
    orphan beats a plain island, an island is everything not otherwise named."""
    cls: dict[str, str] = {}
    for mod in mods:
        imported_by_non_test = indeg[mod] > 0 and any(not is_test[s] for s in graph if mod in graph[s])
        imported_by_test = any(is_test[s] and mod in graph[s] for s in graph)
        text = mods[mod].read_text(encoding="utf-8", errors="replace")
        if is_test[mod]:
            cls[mod] = "TEST"
        elif MAIN_RE.search(text):
            cls[mod] = "ENTRY_POINT"
        elif imported_by_non_test:
            cls[mod] = "IN_USE"
        elif imported_by_test:
            cls[mod] = "TEST_ONLY"
        else:
            cls[mod] = "ISLAND"
    return {k: sum(1 for v in cls.values() if v == k) for k in sorted(set(cls.values()))}


def _certified() -> dict[str, Any]:
    """The manifest of what may be wired: derived from the harness ledger + the ownership matrix."""
    out: dict[str, Any] = {}
    ledger = json.loads(TRUE_LEDGER.read_text(encoding="utf-8"))
    for cap, row in sorted((ledger.get("rows") or {}).items()):
        spec_path = row.get("spec_path")
        entry = {"module": None, "function": None}
        if spec_path and (ROOT / spec_path).is_file():
            spec = json.loads((ROOT / spec_path).read_text(encoding="utf-8"))
            solver = spec.get("solver") or {}
            entry = {"module": solver.get("module"), "function": solver.get("entry")}
        out[cap] = {
            "class": "TRUE_CAPABILITY",
            "verdict": row.get("verdict"),
            "instances": row.get("instances"),
            "fresh_pass_rate": row.get("fresh_pass_rate"),
            "entry_module": entry["module"],
            "entry_function": entry["function"],
            "spec": spec_path,
            "receipt": row.get("latest_receipt"),
            "solver_blob": row.get("solver_git_blob_sha"),
            "receipt_present": bool(row.get("latest_receipt")) and (ROOT / str(row["latest_receipt"])).is_file(),
        }
    matrix = json.loads(OWNERSHIP_MATRIX.read_text(encoding="utf-8"))
    for row in matrix.get("rows") or []:
        if row.get("postwave_ownership_credit") != "VERIFIED_OWNED_EQUAL_OR_BETTER":
            continue
        route = row.get("verified_route") or {}
        fam = str(row.get("family"))
        out[f"FAMILY:{fam}"] = {
            "class": "FRONTIER_FAMILY",
            "verdict": row.get("status"),
            "entry_module": route.get("path") if isinstance(route, Mapping) else None,
            "entry_blob": route.get("git_blob_sha") if isinstance(route, Mapping) else None,
            "receipt": row.get("postwave_acceptance_evidence"),
            "receipt_present": bool(row.get("postwave_acceptance_evidence"))
            and (ROOT / str(row["postwave_acceptance_evidence"])).exists(),
        }
    return out


def build() -> dict[str, Any]:
    mods = _modules()
    graph, indeg = _import_edges(mods)
    is_test = {m: "/tests/" in str(p) for m, p in mods.items()}
    schemas: dict[str, str] = {}
    authorities = 0
    entries = 0
    for mod, path in mods.items():
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in SCHEMA_RE.finditer(text):
            schemas.setdefault(m.group(1), mod)
        authorities += 1 if AUTHORITY_RE.search(text) else 0
        entries += 1 if GUARD_RE.search(text) else 0
    comp_sizes = _components(mods, graph)
    out_fan = {m: len(v) for m, v in graph.items()}
    biggest = max(out_fan.values()) if out_fan else 0
    certified = _certified()
    payload = {
        "schema": "BRAIN_CAPABILITY_FABRIC_V1",
        "authority": "NONE__DERIVED_FROM_IMPORT_GRAPH_AND_COMMITTED_RECEIPTS",
        "model_calls": 0,
        "cost_usd": 0.0,
        "head": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                               capture_output=True, text=True).stdout.strip(),
        "counts": {
            "modules": len(mods),
            "import_edges": sum(len(v) for v in graph.values()),
            "components": len(comp_sizes),
            "component_sizes_desc": comp_sizes[:12],
            "singletons": sum(1 for s in comp_sizes if s == "1"),
            "max_fan_out": biggest,
            "widest_importers": sorted(out_fan.items(), key=lambda kv: -kv[1])[:8],
            "most_imported": indeg.most_common(8),
            "distinct_schema_constants": len(schemas),
            "modules_declaring_authority": authorities,
            # Two different notions of "a way in", because the first is not the second:
            # 1,668 modules can be *run*; 579 of them expose a `main()`. Both are counted so nobody
            # has to guess which one a "one entry point" claim is about. (My first version reported
            # only `def main(` and understated the surface by ~3x.)
            "runnable_entry_points": entries,
            "modules_exposing_def_main": sum(
                1 for p in mods.values() if MAIN_RE.search(p.read_text(encoding="utf-8", errors="replace"))
            ),
            "modules_with_no_internal_importer": sum(1 for m in mods if indeg[m] == 0),
        },
        "reachability": _classify(mods, graph, indeg, is_test),
        "certified_capabilities": certified,
        "certified_count": len(certified),
        "admission_coverage_ratio": round(len(certified) / max(1, len([m for m in mods if not is_test[m]])), 6),
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    payload["fabric_sha256_16"] = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
    return payload


def to_markdown(f: Mapping[str, Any]) -> str:
    c = f["counts"]
    L = ["# Capability fabric: what is connected to what, derived\n"]
    L.append(f"digest `{f['fabric_sha256_16']}` · authority `{f['authority']}` · 0 model calls, $0.00\n")
    L.append("| measure | value | what it decides |")
    L.append("|---|---|---|")
    rows = [
        ("modules under `canonical/`", c["modules"], "the surface any unification has to cover"),
        ("internal import edges", c["import_edges"], "what is actually composed today"),
        ("connected components", f"{c['components']} (largest {c['component_sizes_desc'][0] if c['component_sizes_desc'] else 0}, singletons {c['singletons']})",
         "**the fragmentation, measured** — 'not one model' is this number"),
        ("distinct `SCHEMA = \"…\"` constants", c["distinct_schema_constants"],
         "bespoke envelopes; the cost a shared envelope removes; the number to drive to 1"),
        ("modules declaring an `AUTHORITY`", c["modules_declaring_authority"],
         "self-limiting claims — the good part of the culture"),
        ("runnable modules (`if __name__ == \"__main__\"`)", c["runnable_entry_points"],
         "**ways in**; a system has one root and N adapters. Of these, "
         f"{c['modules_exposing_def_main']} expose a `main()` at all"),
        ("modules nothing in `canonical/` imports", c["modules_with_no_internal_importer"],
         "nothing in the tree imports them; they are reached only by hand or not at all"),
        ("widest importer fan-out", c["max_fan_out"],
         "the ceiling on 'just write an orchestrator that imports everything'"),
        ("certified capabilities", f"{f['certified_count']} ({f['admission_coverage_ratio'] * 100:.3f} % of non-test modules)",
         "what may be wired into the root with a receipt behind it"),
    ]
    for name, val, why in rows:
        L.append(f"| {name} | {val} | {why} |")
    L.append("\n## Reachability classes (every module, one label each)\n")
    for k, v in f["reachability"].items():
        L.append(f"- `{k}`: {v}")
    L.append("\n## What is composed most, and what is certified most\n")
    L.append("- most imported: " + ", ".join(f"`{m}` ({n})" for m, n in f["counts"]["most_imported"]))
    L.append("- widest importers: " + ", ".join(f"`{m}` ({n})" for m, n in f["counts"]["widest_importers"]))
    L.append("\n## The manifest a composition root is allowed to dispatch to\n")
    L.append("| capability | class | entry | receipt present |")
    L.append("|---|---|---|---|")
    for cap, r in sorted(f["certified_capabilities"].items()):
        ent = r.get("entry_module") or "-"
        fn = r.get("entry_function")
        L.append(f"| `{cap}` | {r['class']} | `{ent}`" + (f"`::{fn}`" if fn else "") + f" | {r['receipt_present']} |")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--md-out", default=None)
    ap.add_argument("--check", default=None, metavar="FABRIC_JSON",
                    help="compare the committed fabric's DISPATCH SURFACE against the tree; exit 1 on drift. "
                         "Graph counts are printed but never gate: the tree grows on every unrelated PR, "
                         "and a check that fires on growth is noise that trains people to delete it.")
    args = ap.parse_args(argv)
    fabric = build()
    if args.check:
        path = pathlib.Path(args.check)
        if not path.is_absolute():
            path = ROOT / path
        if not path.is_file():
            print(f"CHECK FAIL: committed fabric {path} does not exist")
            return 1
        committed = json.loads(path.read_text(encoding="utf-8"))
        drift = {
            k: (committed.get(k), fabric.get(k))
            for k in ("certified_capabilities", "certified_count", "authority", "schema")
            if committed.get(k) != fabric.get(k)
        }
        for k in ("modules", "components", "singletons", "distinct_schema_constants", "runnable_entry_points"):
            a, b = (committed.get("counts") or {}).get(k), fabric["counts"][k]
            if a != b:
                print(f"note (not a failure): {k} {a} -> {b}")
        if drift:
            print("CHECK FAIL: the committed dispatch surface does not match the receipts. Drifted keys:")
            for k, (a, b) in sorted(drift.items()):
                print(f"  {k}\n    committed: {json.dumps(a, default=str)[:220]}\n    derived:   {json.dumps(b, default=str)[:220]}")
            return 1
        print(f"CHECK PASS: the certified manifest matches the tree ({fabric['fabric_sha256_16']})")
        return 0
    if args.json_out:
        p = pathlib.Path(args.json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(fabric, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    if args.md_out:
        p = pathlib.Path(args.md_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(to_markdown(fabric), encoding="utf-8")
    if not (args.json_out or args.md_out):
        print(to_markdown(fabric))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

"""What can this brain actually do? Measured, not counted.

The premise this answers: *"we have tremendous hidden capabilities under non-obvious names, and they
need to be at the unified model."* That is a claim about coverage, and coverage has three layers
that had never been measured together:

1. **Reachable** -- will the unified model's import closure even load the module?
2. **Sayable** -- does the routing index contain the words a person would use to ask for it?
3. **Routable** -- given a sentence, does the model send it to that module?

Measured 2026-11-24 on this repository: 2,247 runtime modules, 580 reachable (26%), and the largest
ones are reachable but not sayable. `computer_env_v1.py` (138 KB, "the computer itself, as an
environment the learner can act in") is reachable, and the router has **zero** postings for the word
`computer` -- so "act on the computer as an environment" routes to `shell.command.run`.

The three layers are separate gates. A module that fails layer 2 is not a missing capability; it is
an unread one.

Run: ``python3 -m canonical.tools.capability_concept_coverage_v1``
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
from typing import Any

CLAUSE = (
    "A capability is present only if it is reachable, sayable, and routable -- in that order. "
    "Counting reachable modules measures the import graph; counting sayable ones measures what a "
    "person can ask for; only the third is a capability."
)

# Concepts the mechanisms in this repository actually implement, in the words their own authors
# used. If the router cannot act on one of these, a request phrased with it cannot reach the code.
MECHANISM_CONCEPTS = (
    "route", "routing", "compile", "compiler", "bind", "binding", "derive", "derivation",
    "environment", "computer", "organ", "self-improvement", "acceptance", "admission",
    "verify", "trace", "ledger", "repair", "localize", "policy", "metamorphic", "oracle",
    "bisimulation", "continual", "forget", "transfer", "curriculum", "attention",
)


def _first_sentence(path: pathlib.Path) -> str:
    try:
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8", errors="replace")))
    except SyntaxError:
        return ""
    if not doc:
        return ""
    flat = " ".join(doc.split())
    return " ".join(flat.split(". ")[0].split())


def coverage(root: str | pathlib.Path = ".", *, large_only_bytes: int = 50_000) -> dict[str, Any]:
    base = pathlib.Path(root).resolve()
    sys.path.insert(0, str(base))
    from canonical.runtime.brain_owned_python_closure_census_v1 import census
    from canonical.runtime.brain_unified_model_v1 import open_model, tokenize

    closure = census(str(base), ["canonical/runtime/brain_unified_model_v1.py"])
    reachable = {row["path"] for row in closure["brain_owned_transitive_files"] if isinstance(row, dict)}

    model = open_model(root=str(base))
    index_tokens = set(model.index)
    askable_modules: set[str] = set()
    for capability_id, record in model.capabilities.items():
        if record.get("kind") != "BOUND_CAPABILITY":
            continue
        provenance = record.get("provenance") or {}
        path = provenance.get("source_path")
        if not path and str(capability_id).startswith("canonical/"):
            path = str(capability_id).split(".auto.v1")[0]
        if path:
            askable_modules.add(str(path))

    modules: list[dict[str, Any]] = []
    for path in sorted((base / "canonical" / "runtime").glob("*.py")):
        rel = path.relative_to(base).as_posix()
        claims = _first_sentence(path)
        tokens = tokenize(claims) if claims else []
        usable = [t for t in tokens if t in index_tokens]
        modules.append({
            "module": rel,
            "bytes": path.stat().st_size,
            "reachable": rel in reachable,
            "askable": rel in askable_modules,
            "claims": claims,
            "claim_tokens": len(tokens),
            "sayable_tokens": len(usable),
            "sayable_share": round(len(usable) / len(tokens), 4) if tokens else None,
        })

    mechanisms = [row for row in modules if row["reachable"] and row["bytes"] >= large_only_bytes]
    concept_rows = []
    for concept in MECHANISM_CONCEPTS:
        concept_rows.append({
            "concept": concept,
            "in_index": concept in index_tokens,
            "postings": len(model.index.get(concept) or {}),
        })

    total_bytes = sum(row["bytes"] for row in modules)
    return {
        "schema": "PROJECT_BRAIN_CAPABILITY_CONCEPT_COVERAGE_V1",
        "clause": CLAUSE,
        "modules": len(modules),
        "total_bytes": total_bytes,
        "reachable": sum(1 for row in modules if row["reachable"]),
        "askable": sum(1 for row in modules if row["askable"]),
        "routable_note": "askable is the layer the router can send a sentence to",
        "large_mechanisms": {
            "threshold_bytes": large_only_bytes,
            "count": len(mechanisms),
            "bytes": sum(row["bytes"] for row in mechanisms),
            "sayable_share_mean": (
                round(sum(row["sayable_share"] or 0 for row in mechanisms) / len(mechanisms), 4)
                if mechanisms else None
            ),
            "rows": [
                {k: row[k] for k in ("module", "bytes", "claims", "sayable_share")}
                for row in sorted(mechanisms, key=lambda r: -r["bytes"])
            ],
        },
        "concepts": concept_rows,
        "concepts_unusable": [row["concept"] for row in concept_rows if not row["in_index"]],
        "modules_detail": modules,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = coverage(args.root)
    if args.json:
        report.pop("modules_detail", None)
        print(json.dumps(report, indent=1))
        return 0
    print(f"  {report['clause']}\n")
    print(f"  runtime modules                   : {report['modules']}")
    print(f"  reachable from the unified model  : {report['reachable']}"
          f"  ({report['reachable'] / report['modules'] * 100:.0f}%)")
    print(f"  registered as an askable capability: {report['askable']}"
          f"  ({report['askable'] / report['modules'] * 100:.0f}%)")
    mech = report["large_mechanisms"]
    print(f"\n  reachable mechanisms >= {mech['threshold_bytes'] // 1000} KB: {mech['count']}"
          f"  ({mech['bytes'] / 1e6:.2f} MB)")
    print(f"  their claims, share of tokens the router can act on: {mech['sayable_share_mean']}")
    print(f"\n  {'module':40s} {'KB':>6s}  sayable")
    for row in mech["rows"][:10]:
        name = row["module"].split("/")[-1]
        print(f"  {name[:40]:40s} {row['bytes'] // 1024:6d}  {row['sayable_share']}")
    print(f"\n  concepts a request cannot use (no posting in the router index):")
    print(f"    {', '.join(report['concepts_unusable']) or '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Inventory every capability the project owns, grouped by what it can do.

Three layers, because they have three different epistemic statuses and a single
number would blur them:

``admitted``    rows the live registry serves (receipt-backed or bound).
``discovered``  executable surfaces the tree carries that no registry declares
                (see ``harvest_hidden_capabilities_v1``).
``branch_only`` files that exist on a session branch and not on ``main`` --
                read from a TSV of ``branch<TAB>path`` produced by comparing each
                ``arena/*`` branch against ``main``.

Classification is keyword scoring over the vocabulary each row already carries
(id, provides, keywords, triggers, summary). It is a reading aid, not a claim:
every count is reproducible from the artifacts, and a row that scores nothing
lands in ``unclassified`` rather than being forced into a bucket.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "PROJECT_BRAIN_CAPABILITY_DOMAIN_INVENTORY_V1"
MODEL = "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"

# Domain -> (strong terms, weak terms).  Strong terms are distinctive enough to
# decide alone; weak terms only count when nothing strong matched.
DOMAINS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "blind_repair": (
        ("repair", "fix", "patch", "bug", "cegis", "synthes", "edit", "refactor", "mutant"),
        ("change", "diff", "commit", "issue"),
    ),
    "verification_proof": (
        ("verify", "verifier", "oracle", "proof", "law", "contract", "falsif", "invariant",
         "attest", "receipt", "refut", "differential", "metamorphic"),
        ("check", "gate", "audit", "certificate"),
    ),
    "code_comprehension": (
        ("ast", "ir", "parse", "symbol", "scope", "resolve", "lift", "tree_sitter", "callgraph",
         "type", "syntax", "semantic", "structural"),
        ("module", "function", "class"),
    ),
    "perception_documents": (
        ("ocr", "chart", "image", "pdf", "docx", "xlsx", "vision", "geometry", "svg", "drawing",
         "pixel", "glyph", "cad", "tesseract", "ooxml", "layout"),
        ("document", "page", "figure", "table"),
    ),
    "computer_use_gui": (
        ("gui", "browser", "click", "screen", "desktop", "adb", "x11", "window", "mouse",
         "webarena", "browsergym", "osworld", "selenium", "chromedriver", "playwright"),
        ("ui", "app", "dom", "website"),
    ),
    "terminal_shell": (
        ("terminal", "shell", "cli", "command", "bash", "subprocess", "argv", "stdin", "tty"),
        ("process", "exec", "run"),
    ),
    "planning_agency": (
        ("plan", "goal", "agent", "loop", "schedul", "orchestr", "decide", "decision", "policy",
         "petri", "frontier", "route", "select"),
        ("step", "action", "control"),
    ),
    "memory_learning": (
        ("memory", "learn", "lesson", "skill", "experience", "recall", "replay", "store",
         "crystal", "ablat", "transfer", "continu", "epoch", "knowledge"),
        ("remember", "prior", "teach"),
    ),
    "search_retrieval": (
        ("search", "index", "retriev", "lookup", "census", "enumerate", "discover", "inventory"),
        ("find", "locate", "rank"),
    ),
    "data_query": (
        ("json", "jq", "sql", "yaml", "csv", "query", "sqlite", "toml", "xml"),
        ("data", "record", "schema"),
    ),
    "security_policy": (
        ("guard", "policy", "integrity", "security", "auth", "sandbox", "confine", "refus",
         "admission", "authority", "boundary", "secret"),
        ("permission", "scope", "deny"),
    ),
    "math_symbolic": (
        ("sympy", "numeric", "algebra", "expression", "arithmetic", "theorem", "matrix",
         "linear", "interval", "solver", "z3", "smt"),
        ("compute", "formula", "number"),
    ),
    "benchmark_harness": (
        ("bench", "eval", "harness", "score", "leaderboard", "corpus", "measur", "suite",
         "swebench", "terminal_bench", "human_eval", "quixbugs", "bugsInpy"),
        ("task", "trial", "sample"),
    ),
    "orchestration_runtime": (
        ("runtime", "fabric", "engine", "dispatch", "capability", "registry", "compose",
         "orchestrat", "adapter", "projection", "unified"),
        ("system", "core"),
    ),
}

WORD_RE = re.compile(r"[a-z0-9_]+")


def tokens(text: str) -> list[str]:
    return WORD_RE.findall(str(text or "").lower().replace("/", " ").replace("-", " "))


def classify(texts: Iterable[str]) -> str:
    blob = " ".join(t for t in texts if t)
    words = set(tokens(blob))
    best, best_score = "unclassified", 0
    for domain, (strong, weak) in DOMAINS.items():
        score = 2 * sum(1 for s in strong if s in words) + sum(1 for w in weak if w in words)
        if score > best_score:
            best, best_score = domain, score
    return best


def _model(root: Path) -> dict[str, Any]:
    return json.loads((root / MODEL).read_text(encoding="utf-8"))


def inventory(root: Path, branch_tsv: Path | None = None) -> dict[str, Any]:
    model = _model(root)
    layers: dict[str, dict[str, list[dict[str, Any]]]] = {
        "admitted": {}, "discovered": {}, "branch_only": {},
    }

    for row in model.get("capabilities") or []:
        prov = row.get("provenance") or {}
        domain = classify([
            row.get("id", ""), " ".join(row.get("provides") or []),
            " ".join(row.get("keywords") or []), " ".join(row.get("triggers") or []),
            str(prov.get("adapter_module") or ""), str(prov.get("source_path") or ""),
        ])
        layers["admitted"].setdefault(domain, []).append({
            "id": row.get("id"), "kind": row.get("kind"),
            "adapter": prov.get("adapter_module") or prov.get("source_path"),
        })

    for row in model.get("harvested_capabilities") or []:
        domain = classify([
            row.get("path", ""), row.get("summary", ""),
            row.get("declared_capability_id") or "", " ".join(row.get("triggers") or []),
            " ".join(row.get("declared_result_fields") or []),
        ])
        layers["discovered"].setdefault(domain, []).append({
            "id": row.get("id"), "path": row.get("path"), "invocation": row.get("invocation"),
        })

    if branch_tsv and branch_tsv.is_file():
        for line in branch_tsv.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) != 2:
                continue
            branch, path = parts
            if "/evidence/" in path or path.endswith(".json") or path.startswith("canonical/astra_runtime/"):
                continue
            named = path.rsplit("/", 1)[-1]
            if named.startswith(("test_", "conftest")) or "/tests/" in path:
                continue
            domain = classify([path.replace("/", " "), named.replace("_", " ")])
            layers["branch_only"].setdefault(domain, []).append({"branch": branch, "path": path})

    summary = {}
    for layer, buckets in layers.items():
        summary[layer] = {d: len(v) for d, v in sorted(buckets.items(), key=lambda kv: -len(kv[1]))}
        summary[layer]["__total__"] = sum(len(v) for v in buckets.values())

    return {
        "schema": SCHEMA,
        "model_digest": (model.get("digest") or {}).get("value"),
        "domains": sorted(DOMAINS),
        "summary": summary,
        "layers": layers,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--branch-tsv", default="")
    ap.add_argument("--out", default="canonical/capabilities/hidden/CAPABILITY_DOMAIN_INVENTORY_V1.json")
    ap.add_argument("--top", type=int, default=3)
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    result = inventory(root, Path(args.branch_tsv) if args.branch_tsv else None)
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    domains = [d for d in result["summary"]["admitted"] if d != "__total__"]
    print(f"{'domain':<24}{'admitted':>10}{'discovered':>12}{'branch-only':>13}")
    for d in domains:
        print(f"{d:<24}{result['summary']['admitted'].get(d, 0):>10}"
              f"{result['summary']['discovered'].get(d, 0):>12}"
              f"{result['summary']['branch_only'].get(d, 0):>13}")
    for d, v in result["summary"].items():
        print(f"{d:<24}{v.get('__total__', 0):>10}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

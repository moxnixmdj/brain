#!/usr/bin/env python3
"""Where the machine's five frontier functions actually live, and whether the model can see them.

Why this exists
---------------
The unified model indexes 2,242 source modules and names 628 executable surfaces. The
tree outside tests and scratch holds 3,311 modules. The difference is not junk: this
repository solved a great deal of the frontier's open problems years before the frontier
named them, under names nobody would search for -- ``cli_capability_acquisition_v1``
("infer a program, then prove it works"), ``manufacture_what_the_refusal_asks_for_v1``,
``causal_computer_use_agent_v1``, ``release_chunk_archive_v1``,
``terminal_falsification_control_loop_v3``.

Searching for "continual learning" finds none of them. So this atlas classifies the tree
by *what a module does*, not what it is called: every domain owns a weighted vocabulary
that mixes the frontier's words with this repository's own vocabulary, and a module scores
by where those words appear -- stem, docstring, function and class names.

What it produces, and what it refuses to claim
----------------------------------------------
For each domain it ranks modules and records, on every row, whether the unified model can
already see the module (``source_index``), execute it (``harvested``), or route to a
capability whose adapter it is. A module that scores high and is invisible is exactly the
"hidden capability" the promotion work is about -- and the row says which of the three
states it is in, because "we have it" and "the runtime can reach it" are different claims.

Nothing here is admission. A high score means the module's own text says it does this
work; it does not mean the work is correct. That requires execution, a receipt, and an
independent re-run, none of which this tool does.

Determinism: sorted traversal, no timestamps, no environment values.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import pathlib
import re
import sys
from typing import Any, Iterable, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = "BRAIN_DOMAIN_ATLAS_V1"
DATE = "2026-11-26"

SKIP_PARTS = frozenset({"__pycache__", ".git", "node_modules", "tmp", "tests",
                        "instances", "generated_tests"})
SKIP_PREFIXES = (
    "canonical/astra_runtime/tmp/",
    "canonical/capabilities/internalized/software_engineering/mini_swe_agent_02",
)

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_+.-]*")

# --------------------------------------------------------------------------- domains
#
# Each term carries a weight. 2.0 = the word is the function itself; 1.0 = the word is
# evidence of it; 0.5 = the word is weak and would otherwise flood the ranking (e.g.
# `state`, `test`, `plan`). The frontier's words and this repository's own words sit in
# one table on purpose: the whole point is that they name the same work.

DOMAINS: dict[str, dict[str, Any]] = {
    "instant_learning": {
        "frontier": "adapt from one episode without touching weights",
        "terms": {
            "induce": 1.5, "induc": 1.5, "infer": 1.0, "inference": 0.5, "generaliz": 1.5,
            "general": 0.5, "acquire": 1.5, "acquisition": 1.5, "one_shot": 2.0,
            "few_shot": 2.0, "demonstration": 1.5, "demo": 0.5, "exemplar": 1.0,
            "teach": 1.0, "lesson": 1.0, "learn": 1.0, "adapt": 1.0, "transfer": 1.5,
            "anti_unif": 2.0, "synthes": 1.0, "speculate": 0.5, "hypothes": 1.0,
            "abduct": 1.5, "analog": 1.0, "abstract": 1.0, "skill": 1.0, "program": 0.5,
        },
        "queries": [
            "learn a new capability from a single demonstration without training",
            "infer a program from one example and prove it works",
            "generalize one episode into a reusable rule",
        ],
        "native_queries": [
            "acquire a capability by inducing the program then proving it works",
            "anti-unify two examples into one rule",
            "teach a lesson from one trace",
        ],
    },
    "continual_learning": {
        "frontier": "keep improving without forgetting or drifting",
        "terms": {
            "consolidat": 1.5, "forget": 1.5, "drift": 1.5, "expire": 1.0, "expiry": 1.5,
            "supersed": 1.0, "retain": 1.0, "retention": 1.0, "replay": 1.0,
            "curriculum": 1.0, "obsolesc": 1.5, "deprecat": 1.0, "revis": 0.5,
            "regress": 1.0, "monoton": 1.0, "refine": 1.0, "refinement": 1.0,
            "epoch": 0.5, "update": 0.5, "stable": 0.5, "stability": 1.0,
            "catastroph": 2.0, "refresh": 1.0, "currentness": 1.0, "stale": 1.0,
        },
        "native_queries": [
            "expire a rule whose scope no longer holds",
            "consolidate without drift and keep the store current",
            "refine a decision across epochs without regressing",
        ],
        "queries": [
            "keep improving on new tasks without forgetting earlier ones",
            "expire rules that no longer hold and keep the store current",
            "detect drift between what was taught and what is now true",
        ],
    },
    "memory": {
        "frontier": "context that stays correct as it fills",
        "terms": {
            "memory": 1.0, "remember": 1.5, "recall": 1.5, "retriev": 1.5, "store": 0.5,
            "ledger": 1.0, "archive": 1.0, "chunk": 1.0, "index": 0.5, "cache": 0.5,
            "context": 1.0, "compact": 1.0, "compress": 1.0, "summar": 0.5,
            "episod": 1.5, "trace": 1.0, "journal": 1.0, "receipt": 1.0,
            "provenance": 1.0, "projec": 0.5, "record": 0.5, "history": 1.0,
        },
        "native_queries": [
            "recall from the chunk archive by content address",
            "retrieve a receipt by provenance when the context is full",
            "compact an episode journal without losing facts",
        ],
        "queries": [
            "recall the right prior episode as context when the window is nearly full",
            "keep a durable memory of prior runs that stays correct as it grows",
            "compress a long trajectory without losing the facts it carried",
        ],
    },
    "computer_use": {
        "frontier": "drive a GUI it has never seen",
        "terms": {
            "gui": 2.0, "browser": 2.0, "osworld": 2.0, "screen": 1.5, "screenshot": 1.5,
            "click": 1.5, "pointer": 1.0, "cursor": 1.0, "dom": 1.5, "cdp": 1.5,
            "web": 1.0, "page": 0.5, "element": 0.5, "widget": 1.0, "visual": 1.0,
            "ocr": 1.5, "geometry": 1.0, "bbox": 1.0, "coordinate": 1.0, "guest": 1.5,
            "desktop": 1.5, "app": 0.5, "chrome": 1.5, "sensor": 1.0, "actuat": 1.0,
            "navigat": 1.0, "keyboard": 1.5, "scroll": 1.5, "focus": 0.5, "tab": 0.5,
        },
        "native_queries": [
            "drive the OSWorld guest through CDP browser ops",
            "resolve a compound visual feature to a click coordinate",
            "bind a sensor request into guest state ops",
        ],
        "queries": [
            "operate a browser page by clicking elements on screen",
            "drive an unfamiliar desktop application through its GUI",
            "read the screen, decide the next action, and verify the effect",
        ],
    },
    "coding_agents": {
        "frontier": "resolve a repository issue from a text description",
        "terms": {
            "patch": 1.5, "diff": 1.0, "repair": 1.5, "localiz": 1.5, "bisect": 1.5,
            "mutant": 1.0, "mutation": 1.0, "oracle": 1.0, "metamorphic": 2.0,
            "fault": 1.0, "bug": 1.0, "issue": 0.5, "refactor": 1.0, "swe": 1.5,
            "test": 0.5, "assert": 0.5, "synthes": 1.0, "candidate": 0.5,
            "compile": 0.5, "typecheck": 1.0, "static": 1.0, "ast": 1.0,
            "call_site": 1.5, "dataflow": 1.0, "symbol": 0.5, "merge": 0.5,
            "review": 0.5, "regress": 1.0, "flaky": 1.0,
        },
        "native_queries": [
            "repair a repository from a failing test using a metamorphic oracle",
            "localize the fault by bisecting revisions",
            "synthesize a candidate patch and measure acceptance",
        ],
        "queries": [
            "fix a failing test in a repository from an issue description",
            "localize the faulty function and produce a patch",
            "verify a patch with the tests that guard the changed code",
        ],
    },
    "verification_abstention": {
        "frontier": "know when you do not know, and prove what you did",
        "terms": {
            "verify": 0.5, "proof": 1.5, "prove": 1.5, "witness": 1.5, "certif": 1.0,
            "falsif": 1.5, "refus": 1.5, "abstain": 2.0, "gate": 0.5, "admit": 1.0,
            "admission": 1.0, "receipt": 0.5, "attest": 1.0, "invariant": 1.0,
            "counterexample": 1.5, "soundness": 1.5, "complete": 0.5, "fail_closed": 1.5,
            "independent": 1.0, "audit": 1.0, "tamper": 1.0, "epoch": 0.5,
        },
        "native_queries": [
            "refuse fail-closed when the binding pin is not current",
            "verify two witnesses that are not constant",
            "manufacture what the refusal asks for instead of faking it",
        ],
        "queries": [
            "refuse when the evidence does not establish the claim",
            "prove the result with an independent witness",
            "verify that a receipt was not edited after the fact",
        ],
    },
    "world_model": {
        "frontier": "predict what an action does before doing it",
        "terms": {
            "predict": 1.5, "transition": 1.5, "simulat": 1.5, "world_model": 2.0,
            "forecast": 1.5, "counterfactual": 2.0, "rollout": 1.5, "plan": 0.5,
            "search": 0.5, "state_delta": 2.0, "delta": 1.0, "causal": 1.5,
            "residual": 1.0, "dynamics": 1.5, "expect": 0.5, "outcome": 1.0,
            "consequence": 1.5, "effect": 1.0, "hypothesis": 0.5, "model": 0.5,
        },
        "native_queries": [
            "project the state delta of an action before doing it",
            "rank residual causes for an observed effect",
            "falsify the control loop hypothesis",
        ],
        "queries": [
            "predict the next screen state before taking the action",
            "simulate the consequence of a patch before applying it",
            "forecast whether an outcome will follow from this plan",
        ],
    },
}

STEM_BOOST = 2.0
SYMBOL_BOOST = 1.5
DOC_BOOST = 1.0
MIN_SCORE = 3.0
#: A module must be anchored: the function's word in its own name or its definitions.
MIN_ANCHORED = 2.0
VENDORED_PREFIX = "canonical/capabilities/internalized/"


# --------------------------------------------------------------------------- helpers


def _tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(str(text or "").casefold())


def _stem_tokens(path: pathlib.Path) -> set[str]:
    return set(_tokens(path.stem))


def _symbol_names(tree: ast.AST) -> list[str]:
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.append(node.name.casefold())
    return out


def _walk(root: pathlib.Path) -> Iterable[pathlib.Path]:
    for path in sorted((root / "canonical").rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        # Match skip names on the path *inside* the tree: an absolute path may contain
        # `tmp` because the checkout lives in one, and that must not empty the census.
        if any(part in SKIP_PARTS for part in path.relative_to(root).parts):
            continue
        if any(rel.startswith(prefix) for prefix in SKIP_PREFIXES):
            continue
        if path.name.startswith("test_") or path.name == "conftest.py":
            continue
        yield path


def _score_module(stem: set[str], doc: str, symbols: list[str],
                  terms: Mapping[str, float]) -> tuple[float, float, list[str]]:
    """Weighted, auditable score. Every point is attributable to a term and a place."""
    score = 0.0
    anchored = 0.0
    hits: dict[str, float] = {}
    doc_text = doc.casefold()
    symbol_text = " ".join(symbols)
    for term, weight in terms.items():
        if term in stem:
            score += weight * STEM_BOOST
            anchored += weight * STEM_BOOST
            hits[term + "@stem"] = weight * STEM_BOOST
        occurrences = min(3, doc_text.count(term))
        if occurrences:
            score += weight * DOC_BOOST * occurrences
            hits[term + "@doc"] = weight * DOC_BOOST * occurrences
        if term in symbol_text:
            score += weight * SYMBOL_BOOST
            anchored += weight * SYMBOL_BOOST
            hits[term + "@symbol"] = weight * SYMBOL_BOOST
    top = [name for name, _ in sorted(hits.items(), key=lambda kv: (-kv[1], kv[0]))[:8]]
    return round(score, 3), round(anchored, 3), top


def _model_status(model: Mapping[str, Any] | None) -> dict[str, Any]:
    if not model:
        return {"source_index": set(), "harvested": set(), "adapters": set()}
    indexed_paths = {row.get("path") for row in model.get("source_index") or []}
    indexed_paths |= {row.get("path") for row in model.get("extended_source_index") or []}
    adapter_stems = {str(row.get("adapter_module") or "") for row in model.get("capabilities") or []}
    for crow in model.get("capabilities") or []:
        cid = str(crow.get("id") or "")
        if cid.endswith(".py.auto.v1"):
            adapter_stems.add(pathlib.PurePosixPath(cid[: -len(".auto.v1")]).stem)
    for erow in model.get("engines") or []:
        spath = (erow.get("route") or {}).get("source_path") if isinstance(erow, Mapping) else None
        if spath:
            adapter_stems.add(pathlib.PurePosixPath(str(spath)).stem)
    return {
        "source_index": indexed_paths,
        "harvested": {row.get("path") for row in model.get("harvested_capabilities") or []},
        "adapters": adapter_stems,
    }


# --------------------------------------------------------------------------- atlas


def build_atlas(root: pathlib.Path, model: Mapping[str, Any] | None = None,
                per_domain: int = 25) -> dict[str, Any]:
    status = _model_status(model)
    scanned = 0
    vendored_counts: dict[str, int] = {}
    domains: dict[str, list[dict[str, Any]]] = {name: [] for name in DOMAINS}
    for path in _walk(root):
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8", errors="replace")
            tree = ast.parse(text)
        except (OSError, SyntaxError, ValueError):
            continue
        scanned += 1
        doc = ast.get_docstring(tree) or ""
        stem = _stem_tokens(path)
        symbols = _symbol_names(tree)
        rel = path.relative_to(root).as_posix()
        if path.name == "__init__.py":
            continue
        vendored = rel.startswith(VENDORED_PREFIX)
        for name, spec in DOMAINS.items():
            score, anchored, hits = _score_module(stem, doc, symbols, spec["terms"])
            # A docstring that happens to mention `memory` is not the memory subsystem.
            # The module must be *anchored*: the function word appears in its own name or
            # in the names of the things it defines.
            if score < MIN_SCORE or anchored < MIN_ANCHORED:
                continue
            if vendored:
                vendored_counts[name] = vendored_counts.get(name, 0) + 1
                continue
            domains[name].append({
                "path": rel,
                "score": score,
                "matched": hits,
                "summary": " ".join(doc.strip().splitlines()[0].split())[:180] if doc.strip() else "",
                "sha256": hashlib.sha256(raw).hexdigest()[:16],
                "anchored": anchored,
                "source_index": rel in status["source_index"],
                "harvested": rel in status["harvested"],
                "adapter_module_match": path.stem in status["adapters"],
            })

    digest: dict[str, Any] = {}
    for name, rows in domains.items():
        rows.sort(key=lambda row: (-row["score"], row["path"]))
        kept = rows[:per_domain]
        # "Hidden" means the model cannot see it *by any of the three routes it has*:
        # not indexed as source, not a harvested executable surface, and not the adapter
        # of an admitted capability. Leaving the third out mislabelled eleven bound
        # capabilities -- `python_repair_apply_verified_v1` among them, which is admitted
        # and executed -- as invisible.
        hidden = [row for row in rows
                  if not row["source_index"] and not row["harvested"]
                  and not row["adapter_module_match"]]
        total = len(rows)
        digest[name] = {
            "frontier_function": DOMAINS[name]["frontier"],
            "candidates": len(rows),
            "vendored_donors_excluded": vendored_counts.get(name, 0),
            "in_source_index_top": sum(1 for row in kept if row["source_index"]),
            "harvested_executable_top": sum(1 for row in kept if row["harvested"]),
            "indexed_all": sum(1 for row in rows if row["source_index"]),
            "harvested_all": sum(1 for row in rows if row["harvested"]),
            "hidden_share_all": round(len(hidden) / total, 3) if total else None,
            "invisible_to_model": len(hidden),
            "invisible_share": round(len(hidden) / len(rows), 3) if rows else None,
            "top": kept,
            "candidate_stems": sorted({pathlib.PurePosixPath(row["path"]).stem for row in rows}),
            "hidden_top": [row["path"] for row in hidden[:8]],
        }
    return {
        "schema": SCHEMA,
        "date_utc": DATE,
        "model_calls": 0,
        "network_calls": 0,
        "method": ("weighted lexical evidence over module stem, docstring and symbol names; "
                   "frontier vocabulary and this repository's own vocabulary in one table"),
        "modules_scanned": scanned,
        "vendored_donors_excluded_total": sum(vendored_counts.values()),
        "min_score": MIN_SCORE,
        "per_domain": per_domain,
        "domains": digest,
        "claim_limit": ("a score is evidence that the module's own text says it does this "
                        "work; it is not evidence that the work is correct"),
    }


# --------------------------------------------------------------------------- reachability


def reachability(atlas: Mapping[str, Any], root: pathlib.Path,
                 top_k: int = 5) -> dict[str, Any]:
    """Can the shipped model *reach* the modules the atlas says implement each function?

    Two surfaces are measured, because they are the two a solver can use:

    * ``route()`` over the 449 capabilities -- what the runtime would actually do with
      the ask;
    * ``find_source()`` over the 2,242 indexed modules -- what the model can point at.

    A hit means the returned capability's adapter or the returned source path is one of
    the atlas's own candidates for that domain. Both query sets are run: the frontier's
    phrasing, and this repository's own vocabulary. If the own-vocabulary numbers are
    much higher, the index is readable only to someone who already knows the names --
    which is the problem, not the fix.
    """
    sys.path.insert(0, str(root))
    from canonical.runtime import brain_unified_model_v1 as U

    model = U.UnifiedModel(U.load_model(root=root))
    report: dict[str, Any] = {}
    for name, spec in DOMAINS.items():
        stems = set(atlas["domains"][name]["candidate_stems"])
        # A capability id either names a module path (`canonical/runtime/x_v1.py.auto.v1`) or
        # is a bound id whose adapter the registry maps to a module stem. Both are resolved
        # to stems so the comparison is module-to-module, not string-to-string.
        adapter_of: dict[str, str] = {}
        try:
            registry = json.loads((root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
                                  .read_text(encoding="utf-8"))
            for cid, row in (registry.get("capabilities") or {}).items():
                if isinstance(row, dict) and row.get("adapter_module"):
                    adapter_of[cid] = str(row["adapter_module"])
        except (OSError, ValueError):
            pass
        # ENGINES WERE INVISIBLE TO THIS MEASUREMENT. `adapter_of` was built from the bound
        # registry alone, so a route that returned an engine -- the majority of the model's
        # routing targets -- resolved to a string that can never be a module stem, and scored
        # MISS even when the engine's source or carrier module is a catalogued candidate for
        # the domain. Prefer `source_path` when a federated engine names its backing module,
        # falling back to `carrier_path` for fabric engines.
        try:
            for engine_id, engine in (model.engines.items()
                                      if isinstance(model.engines, dict) else ()):
                eroute = engine.get("route") or {}
                mod_path = (eroute.get("source_path") or eroute.get("carrier_path") or "")
                if mod_path.endswith(".py"):
                    adapter_of[str(engine_id)] = pathlib.PurePosixPath(mod_path).stem
        except (AttributeError, TypeError):
            pass
        # Chance baselines make the recalls readable: a domain with 287 candidate stems
        # would score 100% against a five-document draw even with no navigation at all.
        indexed_total = max(1, len(model.source_index))
        routable_ids = list(model.capabilities) + [eid for eid in model.engines if eid in adapter_of]
        capability_total = max(1, len(routable_ids))
        route_chance = sum(1 for cid in routable_ids
                           if any(stem in str(adapter_of.get(cid, cid)) for stem in stems))
        rows: list[dict[str, Any]] = []
        for kind, queries in (("frontier", spec["queries"]), ("native", spec["native_queries"])):
            for query in queries:
                routed = model.route(query, top_k=top_k)
                candidates = routed.get("candidates") or []
                adapter_hit = [c["id"] for c in candidates
                               if any(stem in str(adapter_of.get(c["id"], c["id"])) for stem in stems)]
                try:
                    located = model.find_source(query, top_k=top_k)
                except Exception as exc:
                    rows.append({"kind": kind, "query": query, "error": str(exc)[:120]})
                    continue
                found = [row.get("path") for row in located.get("candidates") or []]
                source_hit = [p for p in found if pathlib.PurePosixPath(p).stem in stems]
                rows.append({
                    "kind": kind,
                    "query": query,
                    "routed_top": [c["id"] for c in candidates[:3]],
                    "coverage": routed.get("coverage"),
                    "routed_hit": adapter_hit[:3],
                    "source_top": found[:3],
                    "source_hit": source_hit[:3],
                    "route_hit": bool(adapter_hit),
                    "source_hit": bool(source_hit),
                    "hit": bool(adapter_hit or source_hit),
                })
        report[name] = {
            "rows": rows,
            "chance_source_recall": round(min(1.0, len(stems) / indexed_total), 4),
            "chance_route_recall": round(min(1.0, route_chance / capability_total), 4),
            **{f"{kind}_{channel}_recall": round(
                sum(1 for r in rows if r.get("kind") == kind and r.get(channel))
                / max(1, sum(1 for r in rows if r.get("kind") == kind)), 3)
               for kind in ("frontier", "native") for channel in ("route_hit", "source_hit")},
        }
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--per-domain", type=int, default=25)
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--out", default="canonical/unified_model/DOMAIN_ATLAS_V1.json")
    ap.add_argument("--no-reachability", action="store_true")
    args = ap.parse_args(argv)

    root = pathlib.Path(args.root).resolve()
    model_path = root / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"
    model = json.loads(model_path.read_text(encoding="utf-8")) if model_path.is_file() else None
    atlas = build_atlas(root, model, args.per_domain)
    if not args.no_reachability:
        atlas["reachability"] = reachability(atlas, root, args.top_k)

    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(atlas, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    print(f"scanned {atlas['modules_scanned']} modules\n")
    print(f"{'domain':26s} {'cands':>6s} {'indexed':>8s} {'harv':>5s} {'hidden':>7s} "
          f"{'src·frn':>8s} {'src·nat':>8s} {'rte·nat':>8s}")
    for name, row in atlas["domains"].items():
        reach = atlas.get("reachability", {}).get(name) or {}
        fr = reach.get("frontier_source_hit_recall")
        nr = reach.get("native_source_hit_recall")
        rr = reach.get("native_route_hit_recall")
        print(f"{name:26s} {row['candidates']:6d} {row['indexed_all']:8d} "
              f"{row['harvested_all']:5d} {row['invisible_to_model']:7d} "
              f"{(f'{fr:.3f}' if fr is not None else '-'):>8s} "
              f"{(f'{nr:.3f}' if nr is not None else '-'):>8s} "
              f"{(f'{rr:.3f}' if rr is not None else '-'):>8s}")
    print("\nleaders invisible to the model:")
    for name, row in atlas["domains"].items():
        if row["hidden_top"]:
            print(f"  {name}: " + ", ".join(p.split('/')[-1] for p in row["hidden_top"][:4]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

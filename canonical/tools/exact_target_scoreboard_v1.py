"""The scoreboard two rounds asked for: one module per query, chance 1/849.

Every routing number this repository has published so far was measured against a *domain*
label, and the last round showed why that could not work: the label is built from the same
vocabulary as the pool, so a random five drawn from the topic-sharing pool already scores
0.846. This tool removes the label from the loop.

The targets come from the tree itself, not from a model and not from a person:

* the module is one of the ledger's ``SOURCE_ONLY`` rows -- real, indexed, uncallable code;
* the query is the *test author's* statement of intent for that module: the names of its
  tests, stripped of ``test_`` and version suffixes, plus the test module's docstring;
* the target is exactly one module path, so chance at rank 1 is 1/849 and at rank 5 is 5/849.

A query that repeats the module's own name is a leak, not a query: those rows are counted
separately and excluded from the headline. Three channels are scored on the same rows --
``find_source`` (the index), the contract router (verbs and objects from module ASTs), and a
topic-only ablation with the contract gate removed -- so a number can be told from a
vocabulary. Nothing is executed and no model is called.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.tools import contract_first_routing_v1 as C  # noqa: E402

SCHEMA = "PROJECT_BRAIN_EXACT_TARGET_SCOREBOARD_V1"
LEDGER = "canonical/verification/PROMOTION_LEDGER_20261127_V1.json"
TEST_DIR = "canonical/tests"
_VERSION = re.compile(r"_?v\d+$|_\d{8}$")


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[A-Za-z][A-Za-z_]+", text) if len(w) > 2]


def _norm_set(text: str) -> set[str]:
    return {C._norm(w) for w in _words(text)}


def query_for(test_path: pathlib.Path) -> dict[str, Any]:
    import ast

    text = test_path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(text)
    doc = (ast.get_docstring(tree) or "").strip()
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            cleaned = _VERSION.sub("", node.name[len("test_"):].replace("_", " "))
            names.append(cleaned)
    query = " ".join([doc, " ".join(names)]).strip()
    return {"query": query, "test_count": len(names), "doc": doc[:160]}


def targets(root: pathlib.Path) -> list[dict[str, Any]]:
    ledger = json.loads((root / LEDGER).read_text())
    rows = sorted((row for row in ledger["rows"] if row["category"] == "SOURCE_ONLY"),
                  key=lambda row: row["path"])
    out: list[dict[str, Any]] = []
    for row in rows:
        stem = row["stem"]
        test_path = root / TEST_DIR / f"test_{stem}.py"
        if not test_path.is_file():
            continue
        payload = query_for(test_path)
        if not payload["query"]:
            continue
        module_words = _norm_set(stem.replace("_", " "))
        leak = sorted(_norm_set(payload["query"]) & module_words)
        out.append({
            "module": row["path"],
            "stem": stem,
            "query": payload["query"],
            "test_count": payload["test_count"],
            "leak": leak,
            "leaked": bool(leak),
            "domains": row.get("domains") or [],
        })
    return out


def score(root: pathlib.Path, *, top_k: int = 5, use_contract_router: bool = True) -> dict[str, Any]:
    from canonical.runtime import brain_unified_model_v1 as U

    model = U.UnifiedModel(U.load_model(root=root))
    rows = targets(root)
    pool = len(json.loads((root / LEDGER).read_text())["rows"])
    index = C.build_index(root) if use_contract_router else None

    scored: list[dict[str, Any]] = []
    for row in rows:
        located = model.find_source(row["query"], top_k=top_k)
        found = [str(c.get("path") or "") for c in located.get("candidates") or []]
        found_stems = [pathlib.PurePosixPath(p).stem for p in found]
        entry: dict[str, Any] = {
            **row,
            "find_top": found_stems,
            "find_hit_at_1": bool(found_stems) and found_stems[0] == row["stem"],
            "find_hit_at_5": row["stem"] in found_stems,
        }
        if index is not None:
            routed = C.route_by_contract(index, row["query"], top_k=top_k)
            routed_stems = [c["stem"] for c in routed["candidates"]]
            ablation = C.route_by_contract(index, row["query"], top_k=top_k,
                                           require_contract=False, use_verbs=False)
            ablation_stems = [c["stem"] for c in ablation["candidates"]]
            entry.update({
                "contract_top": routed_stems,
                "contract_hit_at_1": bool(routed_stems) and routed_stems[0] == row["stem"],
                "contract_hit_at_5": row["stem"] in routed_stems,
                "ablation_top": ablation_stems,
                "ablation_hit_at_1": bool(ablation_stems) and ablation_stems[0] == row["stem"],
                "ablation_hit_at_5": row["stem"] in ablation_stems,
            })
        scored.append(entry)

    def recall(key: str, subset: list[dict[str, Any]]) -> float:
        return round(sum(1 for r in subset if r.get(key)) / max(1, len(subset)), 4)

    clean = [r for r in scored if not r["leaked"]]
    leaked = [r for r in scored if r["leaked"]]
    channels = [("find", "find_source")]
    if index is not None:
        channels += [("contract", "contract_router"), ("ablation", "topic_only_ablation")]
    summary = {
        name: {
            "clean_at_1": recall(f"{key}_hit_at_1", clean),
            "clean_at_5": recall(f"{key}_hit_at_5", clean),
            "leaked_at_1": recall(f"{key}_hit_at_1", leaked),
            "leaked_at_5": recall(f"{key}_hit_at_5", leaked),
        }
        for key, name in channels
    }
    return {
        "schema": SCHEMA,
        "method": {
            "targets": "one module per query, from the test author's own wording",
            "pool": "the ledger's classified modules",
            "leak_rule": "a query that repeats the module's name is excluded from the clean figures and reported separately",
            "channels": [name for _, name in channels],
        },
        "pool": pool,
        "targets": len(scored),
        "clean_targets": len(clean),
        "leaked_targets": len(leaked),
        "leak_share": round(len(leaked) / max(1, len(scored)), 3),
        "chance_at_1": round(1 / max(1, pool), 5),
        "chance_at_5": round(min(1.0, top_k / max(1, pool)), 5),
        "summary": summary,
        "claim_limit": (
            "The target is the module the test author wrote tests for; the query is their words. A hit means the "
            "channel returned that module, not that it was the only reasonable answer. Nothing was executed and no "
            "test was run, so this measures navigation against one author's intent, producer-run in one sandbox."
        ),
        "model_calls": 0,
        "network_calls": 0,
        "rows": scored,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--out", default="canonical/verification/EXACT_TARGET_SCOREBOARD_20261127_V1.json")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--no-contract", action="store_true")
    args = ap.parse_args(argv)
    report = score(pathlib.Path(args.root), top_k=args.top_k, use_contract_router=not args.no_contract)
    out = pathlib.Path(args.root) / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("pool", "targets", "clean_targets", "leaked_targets",
                                             "leak_share", "chance_at_1", "chance_at_5", "summary")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

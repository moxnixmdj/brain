"""The scoreboard two rounds asked for: one module per query, chance 1/849.

Every routing number this repository published before this instrument was measured against a
*domain* label, and the round that built it showed why that could not work: the label is drawn
from the same vocabulary as the pool, so a random five from the topic-sharing pool already
scored 0.846. This tool removes the label from the loop.

The targets come from the tree itself, not from a model and not from a person:

* the module is one of the ledger's ``SOURCE_ONLY`` rows -- real, indexed, uncallable code;
* the query is the *test author's* statement of intent for that module: the names of its
  tests, stripped of ``test_`` and version suffixes, plus the test module's docstring;
* the target is exactly one module path, so chance at rank 1 is 1/849 and at rank 5 is 5/849.

A query that repeats the module's own name is a leak, not a query: those rows are counted
separately and excluded from the headline.

**What survived the gate's deletion (2026-11-27).** Two rounds measured a contract-first router
against a gate-free ablation of itself and the ablation won both times (0.181 vs 0.128 at rank
5 on the clean quarter; 0.252 vs 0.268 leaked). ``runtime_answer_fingerprint_v1.py`` then
showed the router had never been called by the runtime at all: 404 of 404 answers were identical
with it in the tree and with it deleted. A component that no runtime path reaches and that loses
to its own removal is not a part; it was deleted, with its test, and this file keeps only the
ablation -- the objects-and-topic ranker that beat it -- as the one channel besides
``find_source``. The archived numbers stay readable in
``EXACT_TARGET_SCOREBOARD_20261127_V1.json``.
"""
from __future__ import annotations

import argparse
import ast
import json
import math
import pathlib
import re
import sys
from collections import defaultdict
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.tools import domain_atlas_v1 as A  # noqa: E402

SCHEMA = "PROJECT_BRAIN_EXACT_TARGET_SCOREBOARD_V2"
LEDGER = "canonical/verification/PROMOTION_LEDGER_20261127_V1.json"
ARCHIVE = "canonical/verification/EXACT_TARGET_SCOREBOARD_20261127_V1.json"
TEST_DIR = "canonical/tests"
_VERSION = re.compile(r"_?v\d+$|_\d{8}$")
_SUFFIXES = ("ations", "ation", "ings", "ing", "ers", "er", "ies", "ied", "es", "ed", "s")
WEIGHT_OBJECT = 1.0
WEIGHT_TOPIC = 0.25


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[A-Za-z][A-Za-z_]+", text) if len(w) > 2]


def _norm(token: str) -> str:
    """A deliberately dumb root: two words agree only if they share it after suffix stripping."""
    word = re.sub(r"[^a-z0-9_]+", "", token.casefold())
    for suffix in _SUFFIXES:
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _norm_set(text: str) -> set[str]:
    return {_norm(w) for w in _words(text)}


def query_for(test_path: pathlib.Path) -> dict[str, Any]:
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


# --------------------------------------------------------------- the one surviving channel
# This is the ablation that beat the deleted contract gate, kept verbatim in behaviour: objects
# from public callables (idf-weighted) plus docstring topic words at a quarter weight, with a
# half-weighted topic score when neither agrees. No gate, no verbs -- that is the elimination.


def _public_functions(tree: ast.AST) -> list[ast.AST]:
    return [n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_")]


def _entry_for(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError, ValueError):
        return None
    verbs: dict[str, int] = defaultdict(int)
    objects: dict[str, int] = defaultdict(int)
    for func in _public_functions(tree):
        parts = [_norm(p) for p in func.name.split("_") if p]
        if parts:
            verbs[parts[0]] += 1
        for token in parts[1:]:
            objects[token] += 1
    doc = ast.get_docstring(tree) or ""
    topic = {_norm(tok) for tok in re.findall(r"[A-Za-z][A-Za-z_]+", doc) if len(tok) > 2}
    return {"verbs": dict(verbs), "objects": dict(objects), "topic": sorted(topic),
            "stem": path.stem, "path": str(path)}


def build_index(root: pathlib.Path, *, per_domain: int = 400) -> dict[str, Any]:
    atlas = A.build_atlas(root, per_domain=per_domain)
    entries: dict[str, dict[str, Any]] = {}
    domain_of: dict[str, set[str]] = defaultdict(set)
    for domain, payload in atlas["domains"].items():
        for row in payload["top"]:
            rel = row["path"]
            domain_of[rel].add(domain)
            if rel not in entries:
                entry = _entry_for(root / rel)
                if entry is None:
                    continue
                entry["path"] = rel
                entry["executable"] = bool(row.get("adapter_module_match"))
                entries[rel] = entry
    df_object: dict[str, int] = defaultdict(int)
    for entry in entries.values():
        for obj in entry["objects"]:
            df_object[obj] += 1
    total = max(1, len(entries))
    idf_object = {k: math.log(1.0 + total / v) for k, v in df_object.items()}
    # The vocabulary is the set of *verbs*, kept so the ablation excludes verb-like words from
    # object agreement exactly as the deleted module did; changing it silently improved the
    # ablation from 0.181 to 0.309 at rank 5, which is how the difference was found.
    verb_vocabulary: set[str] = set()
    for entry in entries.values():
        verb_vocabulary.update(entry["verbs"])
    return {"entries": entries, "domain_of": {k: sorted(v) for k, v in domain_of.items()},
            "idf_object": idf_object, "vocabulary": verb_vocabulary}


def route_topic_only(index: dict[str, Any], query: str, *, top_k: int = 5) -> dict[str, Any]:
    terms = [t for t in (_norm(tok) for tok in re.findall(r"[A-Za-z][A-Za-z_]+", query)) if len(t) > 2]
    query_objects = [t for t in terms if t not in index["vocabulary"]]
    query_topic = set(terms)
    scored: list[tuple[float, str]] = []
    for rel, entry in index["entries"].items():
        shared_objects = [o for o in query_objects if o in entry["objects"]]
        topic_hits = sorted(query_topic & set(entry["topic"]))
        score = WEIGHT_OBJECT * sum(index["idf_object"].get(o, 0.0) for o in shared_objects)
        score += WEIGHT_TOPIC * len(topic_hits)
        if not shared_objects:
            score = WEIGHT_TOPIC * len(topic_hits) * 0.5
        if score <= 0.0:
            continue
        scored.append((score, rel))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return {
        "operation": "TOPIC_ONLY_ROUTE",
        "query": query,
        "candidates": [{"path": rel, "stem": index["entries"][rel]["stem"], "score": round(score, 3)}
                       for score, rel in scored[:top_k]],
        "pool": len(index["entries"]),
    }


def score(root: pathlib.Path, *, top_k: int = 5) -> dict[str, Any]:
    from canonical.runtime import brain_unified_model_v1 as U

    model = U.UnifiedModel(U.load_model(root=root))
    rows = targets(root)
    pool = len(json.loads((root / LEDGER).read_text())["rows"])
    index = build_index(root)

    scored: list[dict[str, Any]] = []
    for row in rows:
        located = model.find_source(row["query"], top_k=top_k)
        found = [str(c.get("path") or "") for c in located.get("candidates") or []]
        found_stems = [pathlib.PurePosixPath(p).stem for p in found]
        ablation = route_topic_only(index, row["query"], top_k=top_k)
        ablation_stems = [c["stem"] for c in ablation["candidates"]]
        scored.append({
            **row,
            "find_top": found_stems,
            "find_hit_at_1": bool(found_stems) and found_stems[0] == row["stem"],
            "find_hit_at_5": row["stem"] in found_stems,
            "topic_top": ablation_stems,
            "topic_hit_at_1": bool(ablation_stems) and ablation_stems[0] == row["stem"],
            "topic_hit_at_5": row["stem"] in ablation_stems,
        })

    def recall(key: str, subset: list[dict[str, Any]]) -> float:
        return round(sum(1 for r in subset if r.get(key)) / max(1, len(subset)), 4)

    clean = [r for r in scored if not r["leaked"]]
    leaked = [r for r in scored if r["leaked"]]
    channels = [("find", "find_source"), ("topic", "topic_only_ranker")]
    summary = {
        name: {
            "clean_at_1": recall(f"{key}_hit_at_1", clean),
            "clean_at_5": recall(f"{key}_hit_at_5", clean),
            "leaked_at_1": recall(f"{key}_hit_at_1", leaked),
            "leaked_at_5": recall(f"{key}_hit_at_5", leaked),
        }
        for key, name in channels
    }
    archive = {}
    archive_path = root / ARCHIVE
    if archive_path.is_file():
        prior = json.loads(archive_path.read_text())
        archive = {"path": ARCHIVE, "schema": prior.get("schema"),
                   "summary": prior.get("summary"), "note": "the deleted contract channel's numbers, kept as history"}

    return {
        "schema": SCHEMA,
        "method": {
            "targets": "one module per query, from the test author's own wording",
            "pool": "the ledger's classified modules",
            "leak_rule": "a query that repeats the module's name is excluded from the clean figures and reported separately",
            "channels": [name for _, name in channels],
            "deleted": "the contract router (and its gate) was deleted 2026-11-27; runtime answers unchanged, 404/404",
        },
        "pool": pool,
        "targets": len(scored),
        "clean_targets": len(clean),
        "leaked_targets": len(leaked),
        "leak_share": round(len(leaked) / max(1, len(scored)), 3),
        "chance_at_1": round(1 / max(1, pool), 5),
        "chance_at_5": round(min(1.0, top_k / max(1, pool)), 5),
        "summary": summary,
        "archive": archive,
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
    ap.add_argument("--out", default="canonical/verification/EXACT_TARGET_SCOREBOARD_20261127_V2.json")
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args(argv)
    report = score(pathlib.Path(args.root), top_k=args.top_k)
    out = pathlib.Path(args.root) / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("pool", "targets", "clean_targets", "leaked_targets",
                                             "leak_share", "chance_at_1", "chance_at_5", "summary")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Play 1: route by contract, not by name.

The atlas measured where the wall is. Over the same 1,260 domain candidates the source
index reaches a module of the right domain at 0.76 mean recall@5, while ``route()`` --
the channel ``solve()`` actually uses -- reaches it at 0.33, and at 0.00 for instant
learning and world model. Both channels score a bag of words: ``find_source`` over module
text, ``route()`` over capability descriptions. Neither asks what a module *promises*.

A contract is what a module says it will do, read from its own AST:

* ``verbs``  -- the leading verb of every public callable (``expire_rule`` -> ``expire``);
* ``objects`` -- what those callables act on (``rule``);
* ``guards``  -- the exception messages its public callables raise: its stated refusals;
* ``topic``   -- the words of its docstring, weighted least, because a docstring is a
  claim *about* the code and the atlas already measured it as unreliable for 28 modules.

Routing, then, is agreement on an action, not overlap of a topic. A candidate is
admissible only if it shares at least one verb with the request, or at least two objects.
Everything else is a topic match and is not offered at all -- which is the one thing a
bag-of-words ranker structurally cannot do.

Kill criterion, fixed before the measurement: mean recall@5 must be at least 0.53 (the
incumbent's 0.33 plus twenty points) over the same 42 queries, with a pool no larger
than the atlas's 1,260 candidates and no model calls. Below that the play dies here.
"""
from __future__ import annotations

import argparse
import ast
import datetime
import json
import math
import pathlib
import re
import sys
from collections import defaultdict
from typing import Any, Iterable, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.tools import domain_atlas_v1 as A  # noqa: E402

SCHEMA = "PROJECT_BRAIN_CONTRACT_ROUTING_V1"
KILL_FLOOR = 0.53
TOP_K = 5
MIN_VERB_AGREEMENT = 1
MIN_OBJECT_AGREEMENT = 2
WEIGHT_VERB = 2.0
WEIGHT_OBJECT = 1.0
WEIGHT_TOPIC = 0.25

_SUFFIXES = ("ations", "ation", "ings", "ing", "ers", "er", "ies", "ied", "es", "ed", "s")


def _norm(token: str) -> str:
    """A deliberately dumb root. Applied to the corpus and the query by the same code.

    No thesaurus, no synonyms, no hand table: two words agree only if they share this root
    after suffix stripping, and the same rule is used in both directions.
    """
    word = re.sub(r"[^a-z0-9_]+", "", token.casefold())
    for suffix in _SUFFIXES:
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _split_name(name: str) -> tuple[str, list[str]]:
    parts = [_norm(p) for p in name.split("_") if p]
    if not parts:
        return "", []
    return parts[0], parts[1:]


def _public_functions(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    out: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            out.append(node)
    return out


def _guard_messages(functions: Iterable[ast.AST]) -> list[str]:
    messages: list[str] = []
    for func in functions:
        for node in ast.walk(func):
            if not isinstance(node, ast.Raise) or node.exc is None:
                continue
            exc = node.exc
            args = getattr(exc, "args", [])
            for arg in args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    messages.append(arg.value[:120])
                elif isinstance(arg, ast.JoinedStr):
                    messages.append(ast.unparse(arg)[:120])
    return messages[:12]


def contract_of(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(text)
    except (OSError, SyntaxError, ValueError):
        return None
    functions = _public_functions(tree)
    verbs: dict[str, int] = defaultdict(int)
    objects: dict[str, int] = defaultdict(int)
    for func in functions:
        verb, rest = _split_name(func.name)
        if verb:
            verbs[verb] += 1
        for token in rest:
            objects[token] += 1
    doc = ast.get_docstring(tree) or ""
    topic = {_norm(tok) for tok in re.findall(r"[A-Za-z][A-Za-z_]+", doc) if len(tok) > 2}
    return {
        "verbs": dict(verbs),
        "objects": dict(objects),
        "topic": sorted(topic),
        "guards": _guard_messages(functions),
        "public_callables": [f.name for f in functions][:40],
    }


def build_index(root: pathlib.Path, per_domain: int = 400) -> dict[str, Any]:
    atlas = A.build_atlas(root, per_domain=per_domain)
    contracts: dict[str, dict[str, Any]] = {}
    domain_of: dict[str, set[str]] = defaultdict(set)
    stems: dict[str, str] = {}
    for domain, payload in atlas["domains"].items():
        for row in payload["top"]:
            rel = row["path"]
            stem = pathlib.PurePosixPath(rel).stem
            domain_of[rel].add(domain)
            stems[rel] = stem
            if rel not in contracts:
                contract = contract_of(root / rel)
                if contract is None:
                    continue
                contract["path"] = rel
                contract["stem"] = stem
                contract["executable"] = bool(row.get("adapter_module_match"))
                contract["atlas_score"] = row["score"]
                contracts[rel] = contract
    df_verb: dict[str, int] = defaultdict(int)
    df_object: dict[str, int] = defaultdict(int)
    for contract in contracts.values():
        for verb in contract["verbs"]:
            df_verb[verb] += 1
        for obj in contract["objects"]:
            df_object[obj] += 1
    total = max(1, len(contracts))
    idf_verb = {k: math.log(1.0 + total / v) for k, v in df_verb.items()}
    idf_object = {k: math.log(1.0 + total / v) for k, v in df_object.items()}
    return {
        "atlas": atlas,
        "contracts": contracts,
        "domain_of": {k: sorted(v) for k, v in domain_of.items()},
        "stems": stems,
        "idf_verb": idf_verb,
        "idf_object": idf_object,
        "verb_vocabulary": set(df_verb),
    }


def route_by_contract(index: Mapping[str, Any], query: str, *, top_k: int = TOP_K,
                      require_contract: bool = True, use_verbs: bool = True) -> dict[str, Any]:
    """Rank modules by what they promise.

    ``require_contract`` and ``use_verbs`` exist so the claim can be falsified in the same
    run that makes it: with the gate removed and verbs ignored, the ranker is a plain
    bag-of-words and must score no better, or the contract was never doing the work.
    """
    contracts = index["contracts"]
    idf_verb = index["idf_verb"]
    idf_object = index["idf_object"]
    vocabulary = index["verb_vocabulary"]

    terms = [_norm(tok) for tok in re.findall(r"[A-Za-z][A-Za-z_]+", query)]
    terms = [t for t in terms if len(t) > 2]
    query_verbs = [t for t in terms if t in vocabulary]
    query_objects = [t for t in terms if t not in vocabulary]
    query_topic = set(terms)

    scored: list[tuple[float, str]] = []
    reasons: dict[str, dict[str, Any]] = {}
    for rel, contract in contracts.items():
        verbs = contract["verbs"]
        objects = contract["objects"]
        shared_verbs = [v for v in query_verbs if v in verbs] if use_verbs else []
        shared_objects = [o for o in query_objects if o in objects]
        if require_contract and len(shared_verbs) < MIN_VERB_AGREEMENT and len(shared_objects) < MIN_OBJECT_AGREEMENT:
            continue  # topic overlap is not a contract
        score = (WEIGHT_VERB if use_verbs else 0.0) * sum(idf_verb.get(v, 0.0) for v in shared_verbs)
        score += WEIGHT_OBJECT * sum(idf_object.get(o, 0.0) for o in shared_objects)
        topic_hits = sorted(query_topic & set(contract["topic"]))
        score += WEIGHT_TOPIC * len(topic_hits)
        if not require_contract and not shared_verbs and not shared_objects:
            score = WEIGHT_TOPIC * len(topic_hits) * 0.5
        if score <= 0.0:
            continue
        scored.append((score, rel))
        reasons[rel] = {
            "verbs": shared_verbs,
            "objects": shared_objects,
            "topic": topic_hits[:6],
            "guards": contract["guards"][:2],
        }
    scored.sort(key=lambda item: (-item[0], item[1]))
    rows = [
        {
            "path": rel,
            "stem": contracts[rel]["stem"],
            "score": round(score, 3),
            "domains": index["domain_of"].get(rel, []),
            "executable": contracts[rel]["executable"],
            "agreement": reasons[rel],
        }
        for score, rel in scored[:top_k]
    ]
    return {
        "operation": "ROUTE_BY_CONTRACT",
        "query": query,
        "query_verbs": query_verbs,
        "query_objects": query_objects,
        "candidates": rows,
        "admissible": len(scored),
        "pool": len(contracts),
        "reason": "CONTRACT_AGREEMENT" if rows else "NO_CONTRACT_AGREEMENT__NOT_A_TOPIC_MATCH",
    }


def measure(root: pathlib.Path = ROOT, *, per_domain: int = 400) -> dict[str, Any]:
    index = build_index(root, per_domain=per_domain)
    atlas = index["atlas"]
    pool = len(index["contracts"])

    sys.path.insert(0, str(root))
    from canonical.runtime import brain_unified_model_v1 as U

    model = U.UnifiedModel(U.load_model(root=root))

    rows: list[dict[str, Any]] = []
    for domain, spec in A.DOMAINS.items():
        stems = set(atlas["domains"][domain]["candidate_stems"])
        executable_stems = {
            pathlib.PurePosixPath(row["path"]).stem
            for row in atlas["domains"][domain]["top"]
            if row.get("adapter_module_match")
        }
        topic_pool = 0
        routed_stems = {
            pathlib.PurePosixPath(rel).stem for rel in index["contracts"] if rel in index["domain_of"]
        }
        del routed_stems
        for kind, queries in (("frontier", spec["queries"]), ("native", spec["native_queries"])):
            for query in queries:
                result = route_by_contract(index, query)
                ablation = route_by_contract(index, query, require_contract=False, use_verbs=False)
                ablation_stems = [row["stem"] for row in ablation["candidates"]]
                returned = [row["stem"] for row in result["candidates"]]
                incumbent = model.find_source(query, top_k=TOP_K)
                incumbent_stems = [
                    pathlib.PurePosixPath(row.get("path", "")).stem
                    for row in incumbent.get("candidates") or []
                ]
                words = {_norm(t) for t in re.findall(r"[A-Za-z][A-Za-z_]+", query)}
                topic_pool = sum(
                    1 for contract in index["contracts"].values()
                    if words & (set(contract["topic"]) | set(contract["verbs"]) | set(contract["objects"]))
                )
                domain_in_pool = sum(
                    1 for rel in index["contracts"] if domain in index["domain_of"].get(rel, [])
                )
                domain_sharing = sum(
                    1 for rel, contract in index["contracts"].items()
                    if domain in index["domain_of"].get(rel, [])
                    and words & (set(contract["topic"]) | set(contract["verbs"]) | set(contract["objects"]))
                )
                rows.append({
                    "domain": domain,
                    "kind": kind,
                    "query": query,
                    "contract_top": returned,
                    "contract_hit": any(stem in stems for stem in returned),
                    "contract_hit_executable": any(stem in executable_stems for stem in returned),
                    "incumbent_top": incumbent_stems,
                    "incumbent_hit": any(stem in stems for stem in incumbent_stems),
                    "contract_hit_at_1": bool(returned[:1]) and returned[0] in stems,
                    "ablation_top": ablation_stems,
                    "ablation_hit": any(stem in stems for stem in ablation_stems),
                    "ablation_hit_at_1": bool(ablation_stems[:1]) and ablation_stems[0] in stems,
                    "admissible": result["admissible"],
                    "topic_pool": topic_pool,
                    "chance_uniform": round(min(1.0, TOP_K / max(1, pool)), 4),
                    "chance_topic": round(min(1.0, TOP_K * domain_sharing / max(1, topic_pool)), 4),
                    "reason": result["reason"],
                })

    def recall(key: str) -> float:
        return round(sum(1 for row in rows if row[key]) / max(1, len(rows)), 3)

    per_domain: dict[str, Any] = {}
    for domain in A.DOMAINS:
        subset = [row for row in rows if row["domain"] == domain]
        per_domain[domain] = {
            "queries": len(subset),
            "contract_recall_at_5": round(sum(1 for r in subset if r["contract_hit"]) / max(1, len(subset)), 3),
            "contract_recall_executable_at_5": round(
                sum(1 for r in subset if r["contract_hit_executable"]) / max(1, len(subset)), 3
            ),
            "incumbent_recall_at_5": round(sum(1 for r in subset if r["incumbent_hit"]) / max(1, len(subset)), 3),
            "contract_recall_at_1": round(sum(1 for r in subset if r["contract_hit_at_1"]) / max(1, len(subset)), 3),
            "ablation_topic_only_recall_at_5": round(sum(1 for r in subset if r["ablation_hit"]) / max(1, len(subset)), 3),
            "ablation_topic_only_recall_at_1": round(sum(1 for r in subset if r["ablation_hit_at_1"]) / max(1, len(subset)), 3),
            "mean_admissible": round(sum(r["admissible"] for r in subset) / max(1, len(subset)), 1),
            "chance_uniform_at_5": round(sum(r["chance_uniform"] for r in subset) / max(1, len(subset)), 4),
            "chance_topic_at_5": round(sum(r["chance_topic"] for r in subset) / max(1, len(subset)), 4),
        }
    by_kind = {
        kind: {
            "contract_recall_at_5": round(
                sum(1 for r in rows if r["kind"] == kind and r["contract_hit"])
                / max(1, sum(1 for r in rows if r["kind"] == kind)), 3),
            "incumbent_recall_at_5": round(
                sum(1 for r in rows if r["kind"] == kind and r["incumbent_hit"])
                / max(1, sum(1 for r in rows if r["kind"] == kind)), 3),
        }
        for kind in ("frontier", "native")
    }
    contract_mean = recall("contract_hit")
    incumbent_mean = recall("incumbent_hit")
    return {
        "schema": SCHEMA,
        "date_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": {
            "pool": "every module the atlas ranked into one of the seven domains",
            "admission": "at least one verb in common, or at least two objects; topic overlap alone is refused",
            "weights": {"verb": WEIGHT_VERB, "object": WEIGHT_OBJECT, "topic": WEIGHT_TOPIC},
            "incumbent": "UnifiedModel.find_source, the channel that already beats route() 0.76 to 0.33",
            "ground_truth": "returned module stem is among the domain's atlas candidate stems",
        },
        "pool": pool,
        "queries": len(rows),
        "contract_recall_at_5": contract_mean,
        "contract_recall_executable_at_5": recall("contract_hit_executable"),
        "incumbent_recall_at_5": incumbent_mean,
        "ablation_topic_only_recall_at_5": recall("ablation_hit"),
        "ablation_topic_only_recall_at_1": recall("ablation_hit_at_1"),
        "contract_recall_at_1": recall("contract_hit_at_1"),
        "chance_uniform_at_5": round(sum(r["chance_uniform"] for r in rows) / max(1, len(rows)), 4),
        "chance_topic_at_5": round(sum(r["chance_topic"] for r in rows) / max(1, len(rows)), 4),
        "by_kind": by_kind,
        "per_domain": per_domain,
        "gain_over_incumbent": round(contract_mean - incumbent_mean, 3),
        "kill_floor": KILL_FLOOR,
        "verdict": (
            "KILLED"
            if (contract_mean < KILL_FLOOR
                or contract_mean <= recall("ablation_hit")
                or contract_mean - round(sum(r["chance_topic"] for r in rows) / max(1, len(rows)), 4) < 0.20)
            else "SURVIVES"
        ),
        "verdict_rule": (
            "KILLED if mean recall@5 is below 0.53, or if a topic-only bag of words over the same pool does at "
            "least as well, or if the gain over the topic-sharing chance baseline is under twenty points. The "
            "third clause was added after the first run showed the metric saturating: a random five drawn from "
            "the modules that share any query word already lands in the right domain 84.6% of the time."
        ),
        "claim_limit": (
            "Ground truth is the atlas classification, not a human label: a hit means the router returned a module "
            "the atlas places in that domain. It measures navigation, not capability, and it says nothing about "
            "whether the module works. Producer-run in one sandbox; independent reproduction is open."
        ),
        "model_calls": 0,
        "network_calls": 0,
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--out", default="canonical/verification/PLAY_1_ROUTE_BY_CONTRACT_20261126_V1.json")
    ap.add_argument("--per-domain", type=int, default=400)
    args = ap.parse_args(argv)
    report = measure(pathlib.Path(args.root), per_domain=args.per_domain)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "pool": report["pool"],
        "queries": report["queries"],
        "contract_recall_at_5": report["contract_recall_at_5"],
        "contract_recall_executable_at_5": report["contract_recall_executable_at_5"],
        "incumbent_recall_at_5": report["incumbent_recall_at_5"],
        "ablation_topic_only_recall_at_5": report["ablation_topic_only_recall_at_5"],
        "ablation_topic_only_recall_at_1": report["ablation_topic_only_recall_at_1"],
        "contract_recall_at_1": report["contract_recall_at_1"],
        "chance_uniform_at_5": report["chance_uniform_at_5"],
        "chance_topic_at_5": report["chance_topic_at_5"],
        "by_kind": report["by_kind"],
        "per_domain": {k: v["contract_recall_at_5"] for k, v in report["per_domain"].items()},
        "verdict": report["verdict"],
        "out": str(out),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

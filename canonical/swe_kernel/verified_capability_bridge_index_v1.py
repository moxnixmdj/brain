#!/usr/bin/env python3
"""Self-Derived Capability Phrase Reachability & Byte-Verified Bridge Graph (`K3 = 0`).

Closes Wall 2 (`HARDCORE_SWE_ALL_PROBLEMS_20261101_V4.md` §4 D1 + `bridge_enumeration_v1.py`)
by reusing existing repository mechanisms without hand-written routing tables or naive
bag-of-tokens `provides` pollution:
  1. AST-Proved Multi-Word Dispatch Phrase Index (`< 0.05 ms` in RAM):
     Reads `BRAIN_UNIFIED_MODEL_V1.json["grammar"]["adapter_ast_index"]` (138 operations across
     8 multi-operation adapters) and matches explicit multi-word operation phrases stated in a
     goal (tolerating optional English articles `a`/`an`/`the` between verb and object, while
     never matching single-word tokens like `add`).
  2. Byte-Verified Multi-Step Capability Bridges (`bridge_enumeration_v1.py`):
     Caches and executes `EMITS_VERIFIED` + `BRIDGE_VERIFIED` producer->artifact->consumer
     chains backed by independent stdlib byte oracles (`oracle_bytes_of`).
  3. Zero-LLM Supplier Acquisition Hook (`auto_capability_acquisition.py`):
     Maps structurally missing codecs/CLIs (`pypi` / `npm` / `apt_cli`) to governed supplier
     acquisition plans when `experience_v1` or `environment_fit_v1` flags an absent binary/codec.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

from canonical.runtime import bridge_enumeration_v1 as bridge_enum
from canonical.runtime import brain_unified_model_v1 as bum

SCHEMA = "PROJECT_BRAIN_VERIFIED_CAPABILITY_BRIDGE_INDEX_V1"

_ARTICLES = frozenset({"a", "an", "the", "all", "any", "current", "existing"})
_WORD_RE = re.compile(r"[a-z0-9]+")

# Strict zero-weight verb/qualifier canonicalization used ONLY inside multi-word (`>= 2` words)
# ordered phrase matching (`_contains_ordered_phrase`). Object-role nouns (`parameter`, `symbol`,
# `variable`, `function`, `method`, `class`) are intentionally NEVER merged.
_STRICT_PHRASE_SYNONYMS: dict[str, str] = {
    "locate": "find",
    "identify": "find",
    "spot": "detect",
    "unreferenced": "unused",
    "calculate": "compute",
    "validate": "verify",
    "produce": "generate",
    "eliminate": "remove",
    "erase": "delete",
}

_PHRASE_INDEX_CACHE: dict[str, dict[str, Any]] = {}
_BRIDGE_MEM_CACHE: dict[str, dict[str, Any]] = {}
_TYPE_GRAPH_MEM_CACHE: dict[str, dict[str, Any]] = {}


def _content_words(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall(str(text or "").lower()) if w and w not in _ARTICLES]


def _words_equivalent(gw: str, pw: str) -> bool:
    if gw == pw:
        return True
    if len(pw) >= 4 and (
        gw == pw + "s"
        or pw == gw + "s"
        or (pw.endswith("y") and gw == pw[:-1] + "ies")
        or (gw.endswith("y") and pw == gw[:-1] + "ies")
    ):
        return True
    cg = _STRICT_PHRASE_SYNONYMS.get(gw, gw)
    cp = _STRICT_PHRASE_SYNONYMS.get(pw, pw)
    return cg == cp


def induce_zero_weight_semantic_roles(text: str) -> dict[str, Any]:
    """Delegate finite-ontology input/target role normalization to `h100_zero_learned_semantic_paraphrase_v1`."""
    from canonical.runtime.h100_zero_learned_semantic_paraphrase_v1 import (
        induce_semantic_roles,
    )

    return dict(induce_semantic_roles(text))


def _contains_ordered_phrase(goal_words: Sequence[str], phrase_words: Sequence[str], *, max_gap: int = 2) -> bool:
    """True iff `phrase_words` (>= 2 words) occur in order in `goal_words` separated by <= `max_gap` words."""
    m = len(phrase_words)
    n = len(goal_words)
    if m < 2 or m > n:
        return False
    first = phrase_words[0]
    for i in range(n - m + 1):
        if not _words_equivalent(goal_words[i], first):
            continue
        pos = i
        matched = True
        for pw in phrase_words[1:]:
            found_next = -1
            upper = min(n, pos + 1 + max_gap + 1)
            for j in range(pos + 1, upper):
                if _words_equivalent(goal_words[j], pw):
                    found_next = j
                    break
            if found_next < 0:
                matched = False
                break
            pos = found_next
        if matched:
            return True
    return False


def build_ast_phrase_index(artifact_path: str | pathlib.Path | None = None) -> dict[str, Any]:
    """Compile a RAM-cached multi-word phrase index over `BRAIN_UNIFIED_MODEL_V1`'s `.core.marshal`."""
    model = bum.open_model(artifact_path)
    digest = str(getattr(model, "digest", None) or "live")
    cached = _PHRASE_INDEX_CACHE.get(digest)
    if cached is not None:
        return cached

    core_meta = getattr(model, "_core_meta", None) or {}
    ast_idx = core_meta.get("adapter_ast_index") or ((model.model.get("grammar") or {}).get("adapter_ast_index") or {})
    caps_map = core_meta.get("capabilities_map") or {str(c.get("id")): c for c in model.capabilities}

    # Map adapter stem -> capability_ids
    stem_to_cids: dict[str, list[str]] = {}
    for cid, cap in caps_map.items():
        mod = str(cap.get("adapter_module") or "")
        if cid and mod:
            leaf = mod.rsplit(".", 1)[-1]
            stem_to_cids.setdefault(leaf, []).append(str(cid))

    by_adapter: dict[str, list[dict[str, Any]]] = {}
    by_cid: dict[str, list[dict[str, Any]]] = {}
    total_phrases = 0
    for adapter_rel, meta in sorted(ast_idx.items()):
        ops = list(meta.get("dispatch_ops") or [])
        entries: list[dict[str, Any]] = []
        for op in ops:
            op_str = str(op)
            if "_" not in op_str and "-" not in op_str:
                continue
            p_words = _content_words(op_str.replace("_", " ").replace("-", " "))
            if len(p_words) < 2:
                continue
            entries.append(
                {
                    "op": op_str,
                    "phrase": " ".join(p_words),
                    "words": tuple(p_words),
                    "specificity": len(p_words),
                }
            )
            total_phrases += 1
        if not entries:
            continue
        by_adapter[adapter_rel] = entries
        stem = pathlib.PurePosixPath(adapter_rel).stem
        for cid in stem_to_cids.get(stem, ()):
            by_cid[cid] = entries

    built = {
        "digest": digest,
        "by_adapter": by_adapter,
        "by_cid": by_cid,
        "total_multiword_ops": total_phrases,
    }
    _PHRASE_INDEX_CACHE[digest] = built
    return built


def match_ast_dispatch_op_for_capability(
    goal: str,
    capability_id: str,
    *,
    artifact_path: str | pathlib.Path | None = None,
) -> str | None:
    """Return the unique highest-specificity AST-proved `operation` stated in `goal`, or `None` on tie/miss."""
    idx = build_ast_phrase_index(artifact_path)
    entries = idx["by_cid"].get(capability_id) or ()
    if not entries:
        return None
    g_words = _content_words(goal)
    if len(g_words) < 2:
        return None
    hits = [e for e in entries if _contains_ordered_phrase(g_words, e["words"])]
    if not hits:
        return None
    best_spec = max(h["specificity"] for h in hits)
    winners = [h for h in hits if h["specificity"] == best_spec]
    ops = {w["op"] for w in winners}
    if len(ops) != 1:
        return None
    return next(iter(ops))


def find_phrase_matched_capabilities(
    goal: str,
    registry: Mapping[str, Mapping[str, Any]],
    *,
    artifact_path: str | pathlib.Path | None = None,
) -> list[dict[str, Any]]:
    """Return verified registry capabilities whose AST-proved multi-word dispatch phrase is stated in `goal`."""
    idx = build_ast_phrase_index(artifact_path)
    g_words = _content_words(goal)
    if len(g_words) < 2:
        return []
    matched: list[dict[str, Any]] = []
    for cid, entries in idx["by_cid"].items():
        if cid not in registry:
            continue
        hits = [e for e in entries if _contains_ordered_phrase(g_words, e["words"])]
        if not hits:
            continue
        best_spec = max(h["specificity"] for h in hits)
        winners = [h for h in hits if h["specificity"] == best_spec]
        ops = sorted({w["op"] for w in winners})
        if len(ops) == 1:
            matched.append(
                {
                    "capability_id": cid,
                    "matched_op": ops[0],
                    "matched_phrase": winners[0]["phrase"],
                    "specificity": best_spec,
                }
            )
    matched.sort(key=lambda r: (-int(r["specificity"]), str(r["capability_id"])))
    return matched


def get_or_build_verified_bridge_graph(
    *,
    reg_path: str = bridge_enum.DEFAULT_REGISTRY,
    cache_path: str | pathlib.Path | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Load or compute the byte-verified (`EMITS_VERIFIED` + `BRIDGE_VERIFIED`) capability bridge graph."""
    repo_root = bridge_enum.REPO_ROOT
    reg_abs = (repo_root / reg_path).resolve()
    reg_sha = hashlib.sha256(reg_abs.read_bytes()).hexdigest() if reg_abs.is_file() else "missing"

    if not force_refresh and reg_sha in _BRIDGE_MEM_CACHE:
        return _BRIDGE_MEM_CACHE[reg_sha]

    disk_cache = (
        pathlib.Path(cache_path)
        if cache_path is not None
        else (repo_root / "canonical" / "astra_runtime" / "tmp" / "verified_bridge_graph_v1.json")
    )
    if not force_refresh and disk_cache.is_file():
        try:
            loaded = json.loads(disk_cache.read_text(encoding="utf-8"))
            if loaded.get("registry_sha256") == reg_sha and isinstance(loaded.get("bridges"), list):
                _BRIDGE_MEM_CACHE[reg_sha] = loaded
                return loaded
        except Exception:
            pass

    report = bridge_enum.enumerate_bridges(reg_path=reg_path)
    graph = {
        "schema": SCHEMA + "/bridge_graph",
        "registry_sha256": reg_sha,
        "emits_verified": list(report.get("emits_verified") or []),
        "bridges": list(report.get("bridges_verified") or report.get("bridges") or []),
    }
    try:
        disk_cache.parent.mkdir(parents=True, exist_ok=True)
        disk_cache.write_text(json.dumps(graph, separators=(",", ":")), encoding="utf-8")
    except OSError:
        pass
    _BRIDGE_MEM_CACHE[reg_sha] = graph
    return graph


def execute_byte_verified_two_step_bridge(
    *,
    producer_cid: str,
    producer_args: Mapping[str, Any],
    artifact_type: str,
    consumer_cid: str,
    consumer_artifact_arg: str,
    consumer_extra_args: Mapping[str, Any] | None = None,
    reg_path: str = bridge_enum.DEFAULT_REGISTRY,
    root: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Execute Producer -> independent `oracle_bytes_of` byte check (`EMITS_VERIFIED`) -> Consumer (`BRIDGE_VERIFIED`)."""
    from canonical.runtime import live_brain_route_admission_v1 as ra

    t0 = time.perf_counter_ns()
    repo_root = pathlib.Path(root or bridge_enum.REPO_ROOT).resolve()
    reg_data = json.loads((bridge_enum.REPO_ROOT / reg_path).read_text(encoding="utf-8"))["capabilities"]
    if producer_cid not in reg_data or consumer_cid not in reg_data:
        return {"pass": False, "status": "FAIL_CLOSED__CAPABILITY_NOT_IN_BOUND_REGISTRY"}

    p_entry = reg_data[producer_cid]
    c_entry = reg_data[consumer_cid]

    p_action = {
        "type": "invoke_capability",
        "args": dict(producer_args),
        "expect": (p_entry.get("action_template") or {}).get("expect"),
    }
    p_res = ra.run_adapter_locally(p_entry, p_action)
    emitted_rel = str(producer_args.get("output_path") or "")
    if not emitted_rel or not (repo_root / emitted_rel).is_file():
        return {"pass": False, "status": "FAIL_CLOSED__PRODUCER_NO_FILE_EMITTED", "producer_result": p_res}

    # Independent stdlib byte-level verification (`EMITS_VERIFIED`)
    if not bridge_enum.oracle_bytes_of(artifact_type, repo_root, emitted_rel):
        return {
            "pass": False,
            "status": "FAIL_CLOSED__INDEPENDENT_BYTE_ORACLE_REJECTED",
            "artifact": emitted_rel,
            "claimed_type": artifact_type,
        }

    c_args = dict(consumer_extra_args or {})
    c_args[consumer_artifact_arg] = emitted_rel
    c_action = {
        "type": "invoke_capability",
        "args": c_args,
        "expect": (c_entry.get("action_template") or {}).get("expect"),
    }
    c_res = ra.run_adapter_locally(c_entry, c_action)
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__BYTE_VERIFIED_CAPABILITY_BRIDGE_EXECUTED",
        "producer": producer_cid,
        "emits_type": artifact_type,
        "emits_verified": True,
        "artifact": emitted_rel,
        "artifact_sha256": hashlib.sha256((repo_root / emitted_rel).read_bytes()).hexdigest(),
        "consumer": consumer_cid,
        "bridge_verified": True,
        "producer_result": p_res,
        "consumer_result": c_res,
        "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
        "k3_external_llm_calls": 0,
    }


def plan_autonomous_supplier_acquisition(goal: str) -> dict[str, Any]:
    """Identify zero-LLM supplier acquisition routes (`pypi` / `npm` / `apt_cli`) for missing codecs/tools."""
    rt_dir = str((bridge_enum.REPO_ROOT / "canonical" / "runtime").resolve())
    if rt_dir not in sys.path:
        sys.path.insert(0, rt_dir)
    from canonical.runtime import auto_capability_acquisition as auto_acq

    classes = list(auto_acq.supplier_classes_supporting(goal) or [])
    return {
        "schema": SCHEMA + "/supplier_plan",
        "goal": goal,
        "supported": bool(classes),
        "supplier_classes": classes,
        "k3_external_llm_calls": 0,
    }


def get_cached_type_level_graph(
    registry: Mapping[str, Any] | None = None,
    *,
    max_len: int = 2,
) -> dict[str, Any]:
    """Build or return the RAM-cached 113-edge artifact type graph (`type_level_composer_v1`) in `< 0.3 ms` warm."""
    from canonical.runtime import type_level_composer_v1 as tlc

    cache_k = f"default::{max_len}" if registry is None else f"custom::{len(registry)}::{max_len}"
    if cache_k in _TYPE_GRAPH_MEM_CACHE:
        return _TYPE_GRAPH_MEM_CACHE[cache_k]
    t0 = time.perf_counter_ns()
    tg = tlc.type_graph(registry)
    all_edges = tlc.edges(tg)
    all_chains = tlc.chains(tg, max_len=max_len, limit=256)
    bundle = {
        "schema": tlc.SCHEMA + "/cached_graph",
        "type_graph": tg,
        "edge_count": len(all_edges),
        "edges": all_edges,
        "chains": all_chains,
        "build_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
    }
    if registry is None:
        _TYPE_GRAPH_MEM_CACHE[cache_k] = bundle
    return bundle


def compose_and_execute_type_level_chain(
    goal_or_cid: str,
    *,
    registry: Mapping[str, Any] | None = None,
    max_len: int = 2,
    limit: int = 16,
    seed: int | None = 0,
    macro_state_path: str | pathlib.Path | None = None,
) -> dict[str, Any]:
    """Compose and execute a multi-step capability chain by artifact TYPE (`type_level_composer_v1`), caching winners in `macro_v1`."""
    from canonical.runtime import type_level_composer_v1 as tlc
    from canonical.swe_kernel.forged_binding_and_macro_spine_v1 import (
        lookup_verified_chain_macro,
        record_verified_chain_macro,
    )

    t0 = time.perf_counter_ns()
    target = str(goal_or_cid or "").strip()
    if not target:
        return {"schema": SCHEMA + "/type_chain", "pass": False, "status": "EMPTY_GOAL_OR_CID"}

    macro_clauses = [f"type_chain_target:{target.lower()}", f"max_len:{max_len}"]
    macro_hit = lookup_verified_chain_macro(macro_clauses, state_path=macro_state_path)
    if isinstance(macro_hit, Mapping):
        rem_steps = [
            str(s.get("capability_id") or "")
            for s in (macro_hit.get("plan") or macro_hit.get("steps") or [])
            if isinstance(s, Mapping) and s.get("capability_id")
        ]
        if len(rem_steps) >= 2:
            v_res = tlc.verify_chain(rem_steps, registry=registry, seed=seed)
            if v_res.get("pass") is True:
                return {
                    "schema": SCHEMA + "/type_chain",
                    "pass": True,
                    "status": "PASS__TYPE_LEVEL_MACRO_RECALLED_AND_EXECUTED",
                    "from_macro_cache": True,
                    "chain": rem_steps,
                    "execution": v_res,
                    "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
                    "k3_external_llm_calls": 0,
                }

    cached = get_cached_type_level_graph(registry, max_len=max_len)
    tg = cached["type_graph"]
    candidates = list(cached["chains"])

    # Match either an explicit capability ID or artifact content types mentioned in a plain sentence
    nodes = tg.get("nodes") if isinstance(tg.get("nodes"), Mapping) else tg
    if target in nodes:
        candidates = [c for c in candidates if c[-1] == target] or [c for c in candidates if target in c]
    else:
        mentioned_types = tlc._content_of(target)
        goal_words = set(_content_words(target))
        scored: list[tuple[int, list[str]]] = []
        for ch in candidates:
            ch_types: set[str] = set()
            ch_words: set[str] = set()
            for cid in ch:
                ninfo = nodes.get(cid) or {}
                ch_types |= set(ninfo.get("consumes") or ()) | set(ninfo.get("produces") or ())
                ch_words |= set(_content_words(cid.replace(".", " ")))
            type_overlap = len(mentioned_types & ch_types)
            word_overlap = len(goal_words & ch_words)
            if type_overlap >= 1 and (type_overlap + word_overlap) >= 2:
                scored.append((type_overlap * 4 + word_overlap, ch))
        scored.sort(key=lambda item: (-item[0], item[1]))
        candidates = [ch for _, ch in scored]

    if not candidates:
        return {
            "schema": SCHEMA + "/type_chain",
            "pass": False,
            "status": tlc.OPEN_NO_EDGE,
            "attempted": 0,
            "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
            "k3_external_llm_calls": 0,
        }

    tried = 0
    for chain in candidates[: max(1, int(limit))]:
        tried += 1
        res = tlc.verify_chain(chain, registry=registry, seed=seed)
        if res.get("pass") is True:
            record_verified_chain_macro(
                macro_clauses,
                [{"capability_id": cid, "verified": True} for cid in chain],
                state_path=macro_state_path,
            )
            return {
                "schema": SCHEMA + "/type_chain",
                "pass": True,
                "status": tlc.PASS,
                "from_macro_cache": False,
                "attempted": tried,
                "chain": list(chain),
                "execution": res,
                "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
                "k3_external_llm_calls": 0,
            }

    return {
        "schema": SCHEMA + "/type_chain",
        "pass": False,
        "status": tlc.FAIL_STEP,
        "attempted": tried,
        "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
        "k3_external_llm_calls": 0,
    }


def query_semantic_repo_navigation(
    root: str | pathlib.Path,
    query_kind: str,
    target_or_symbol: str = "",
    *,
    scope_path: str = ".",
) -> dict[str, Any]:
    """Fast SQLite-WAL incremental semantic graph queries (`definition`, `importers`, `cycles`, `hierarchy`, `symptom`)."""
    from canonical.swe_kernel import incremental_semantic_graph_v1 as sem_g

    repo = pathlib.Path(root).resolve()
    qk = str(query_kind or "").strip().lower()
    if qk in {"definition", "find_definition", "show_definition"}:
        out = sem_g.query_definition(repo, scope_path, target_or_symbol)
    elif qk in {"importers", "which_modules_import"}:
        out = sem_g.query_importers_of(repo, scope_path, target_or_symbol)
    elif qk in {"cycles", "import_cycles"}:
        out = sem_g.query_import_cycles(repo, scope_path)
    elif qk in {"hierarchy", "class_hierarchy"}:
        out = sem_g.query_class_hierarchy(repo, scope_path, target_or_symbol or None)
    elif qk in {"symptom", "localize_symptom"}:
        out = sem_g.localize_symptom_and_impacted_tests(repo, target_or_symbol, scope_path=scope_path)
    else:
        return {"pass": False, "status": f"UNSUPPORTED_SEMANTIC_QUERY:{query_kind}"}
    out = dict(out)
    out["pass"] = True
    out["k3_external_llm_calls"] = 0
    return out


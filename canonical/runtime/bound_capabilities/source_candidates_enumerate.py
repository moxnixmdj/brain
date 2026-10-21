#!/usr/bin/env python3
"""Enumerate source candidates from the repository as a rankable JSON corpus.

Producer for ``source.candidates.available``. Measured gap: 30 effects appear
in capability ``requires`` lists that nothing in the registry produces, and
this is the one required by ``source.objective_relevance.rank.bm25``, whose
``input_path`` therefore had no upstream step to fill it. World binding handed
it the first sorted file whose name matched -- a ``.py`` file -- and the ranker
died with RELEVANCE_INPUT_NOT_JSON, an incident recorded in the ranker's own
comment.

No learned parameters, no external spend. Emits the object shape ``rank()``
already consumes. Nothing here scores or selects.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

SCHEMA = "PROJECT_BRAIN_SOURCE_CANDIDATE_ENUMERATION_V1"
DEFAULT_SNIPPET_BYTES = 4000
DEFAULT_MAX_CANDIDATES = 400


def _safe_path(root, raw):
    root = pathlib.Path(root).resolve()
    p = (root / str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _snippet(path, limit):
    try:
        raw = path.read_bytes()[:limit]
    except OSError:
        return ""
    try:
        return " ".join(raw.decode("utf-8").split())
    except UnicodeDecodeError:
        return ""


def run(args, root):
    args = dict(args or {})
    base = _safe_path(root, args.get("search_root") or ".")
    out = _safe_path(root, args.get("output_path"))
    if not base.is_dir():
        raise RuntimeError("SEARCH_ROOT_NOT_A_DIRECTORY")
    if out.suffix.lower() != ".json":
        raise RuntimeError("JSON_OUTPUT_REQUIRED")
    pattern = str(args.get("glob") or "**/*.py")
    try:
        limit = max(1, min(int(args.get("max_candidates", DEFAULT_MAX_CANDIDATES)), 5000))
        snippet_bytes = max(0, min(int(args.get("snippet_bytes", DEFAULT_SNIPPET_BYTES)), 1 << 20))
    except (TypeError, ValueError):
        raise RuntimeError("ENUMERATION_LIMIT_INVALID")

    root_path = pathlib.Path(root).resolve()
    seen, candidates = set(), []
    for path in sorted(base.glob(pattern)):
        if not path.is_file():
            continue
        rel = path.resolve().relative_to(root_path).as_posix()
        if rel in seen:
            continue
        seen.add(rel)
        candidates.append({
            "title": rel, "record_title": path.name,
            "snippet": _snippet(path, snippet_bytes),
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
        if len(candidates) >= limit:
            break
    if not candidates:
        raise RuntimeError("SOURCE_CANDIDATES_NONE_FOUND:" + pattern)

    payload = {
        "schema": SCHEMA, "objective": args.get("objective") or None,
        "search_root": base.resolve().relative_to(root_path).as_posix(),
        "glob": pattern, "candidate_count": len(candidates),
        "model_dependency_count": 0, "incremental_spend_usd": 0,
        "candidates": candidates,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = {
        "adapter": "source_candidates_enumerate", "schema": SCHEMA,
        "status": "SOURCE_CANDIDATES_ENUMERATED",
        "candidate_count": len(candidates),
        "search_root": payload["search_root"], "glob": pattern,
        "model_dependency_count": 0, "incremental_spend_usd": 0,
        "output_path": str(out.resolve().relative_to(root_path)).replace("\\", "/"),
    }
    result["output_verified"] = out.is_file() and len(candidates) > 0
    return result

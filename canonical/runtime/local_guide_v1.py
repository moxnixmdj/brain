#!/usr/bin/env python3
"""Local instant-knowledge source: the computer's own guides.

The Perfect Algorithm's instant-knowledge tier reads the web as a fallback,
but every component on this computer already has a guide: README, AGENTS.md,
the man pages that ship with installed tools, and the repo's own documentation.
Local guides are offline, version-matched with the install, and cheap to read
-- they are the first tier of instant knowledge, not the last.

This module is honest about what it IS:

  - It is external knowledge, read from local files. It is never counted as
    Brain capability.
  - It is "last known state", not ground truth. A local guide tells the agent
    HOW to orient; the environment's own verification still decides.
  - It is completeness-gated. One isolated keyword hit is not a conclusion:
    a document answers only if a single paragraph shares two or more of the
    query's content tokens. One content token anywhere in a document is a
    thin hit, not a guide -- it is an OPEN result, never a confident guess.

The default root is the repository root. It is bounded: at most 500 ``.md``
files, never ``.git``/``node_modules``/build output.

Model calls: 0. Network calls: 0. Spend: $0.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

SCHEMA = "PROJECT_BRAIN_LOCAL_GUIDE_V1"
PASS = "PASS__LOCAL_GUIDE_FOUND"
OPEN_NOT_FOUND = "OPEN__LOCAL_GUIDE_NOT_FOUND"
FAIL_EMPTY = "FAIL_CLOSED__LOCAL_GUIDE_EMPTY_QUERY"

_SKIP = {".git", "node_modules", "build", "dist", "out", ".next", ".venv",
         "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
_MAX_FILES = 500
_MAX_SNIPPET_LINES = 3

# Function words carry no content. A document that merely contains "how" or
# "use" has not answered anything. They are dropped from the query before
# scoring -- otherwise every engineering doc matches every query.
_STOPWORDS = frozenset({
    "a", "an", "the", "of", "to", "in", "on", "at", "by", "for", "with",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "can", "could", "will", "would", "shall", "should",
    "may", "might", "must", "need", "needs", "we", "you", "i", "he", "she",
    "it", "they", "our", "my", "its", "their", "this", "that", "these",
    "those", "what", "which", "who", "whom", "when", "where", "why", "how",
    "use", "using", "used", "and", "or", "but", "if", "then", "so", "because",
    "as", "than", "about", "around", "into", "from", "out", "up", "down",
    "over", "under", "again", "here", "there", "not", "no", "yes", "all",
    "any", "some", "each", "every", "both", "few", "more", "most", "other",
    "such", "only", "also", "just", "very", "too", "like", "well", "get",
    "got", "make", "made", "take", "took", "go", "goes", "went", "whether",
    "given", "give", "back", "tell", "tell me", "show", "see", "ask", "know",
    "want", "wants", "needed", "need", "needs", "want", "asked",
})


def _default_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _query_tokens(query: str) -> list[str]:
    text = str(query or "").lower()
    tokens = re.findall(r"[a-z0-9][a-z0-9_\-]{2,}", text)
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t in seen or t in _STOPWORDS:
            continue
        seen.add(t)
        out.append(t)
    return out


def _local_guide_files(root: Path) -> list[Path]:
    root = Path(root)
    if not root.is_dir():
        return []
    out: list[Path] = []
    for p in root.rglob("*.md"):
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue
        if any(part in _SKIP for part in rel.parts):
            continue
        out.append(p)
        if len(out) >= _MAX_FILES:
            break
    return sorted(out)


def _content_hits(text: str, tokens: Sequence[str]) -> list[str]:
    lower = text.lower()
    return [t for t in tokens
            if re.search(r"\b" + re.escape(t) + r"\b", lower)]


def _best_paragraph(text: str, tokens: Sequence[str]) -> tuple[int, str] | None:
    """The single paragraph sharing the most content tokens with the query.
    One isolated keyword in a doc is a thin hit; the same passage answering
    the question is what a guide means."""
    best: tuple[int, str] | None = None
    for para in re.split(r"\n\s*\n", text):
        hits = _content_hits(para, tokens)
        if len(hits) < 2:
            continue
        if best is None or len(hits) > best[0]:
            best = (len(hits), para.strip()[:600])
    return best


def lookup(query: str, *, root: Path | str | None = None,
           max_snippets: int = 5, min_tokens: int = 2,
           deadline_s: float = 30.0) -> dict[str, Any]:
    """Search the local guides on this computer for what a query asks.

    Returns evidence (path, score, matched tokens, paragraph snippet) or an
    honest OPEN. Completeness means at least one local document has a single
    paragraph sharing two or more of the query's content tokens -- one
    content token anywhere in a document is NOT a conclusion.
    """
    started = time.time()
    q = str(query or "").strip()
    if not q:
        return {"schema": SCHEMA, "status": FAIL_EMPTY, "pass": False,
                "query": q, "score": 0.0, "documents": [],
                "authority": "NONE"}

    tokens = _query_tokens(q)
    # A guide answers the question, not a word of it. The bar is content-token
    # proportional: with few content tokens it wants all of them, with many it
    # refuses to conclude on thin overlap (60%, minimum 2).
    import math
    needed = max(2, math.ceil(len(tokens) * 0.6)) if tokens else 2
    root_path = Path(root) if root is not None else _default_root()
    docs: list[dict[str, Any]] = []
    try:
        for p in _local_guide_files(root_path):
            if time.time() - started > deadline_s:
                break
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            best = _best_paragraph(text, tokens)
            if best is None:
                continue
            score, snippet = best
            try:
                rel = str(p.relative_to(root_path))
            except ValueError:
                rel = str(p)
            docs.append({
                "path": rel,
                "score": float(score),
                "matched_terms": score,
                "snippet": snippet,
            })
    except Exception as e:  # noqa: BLE001
        return {"schema": SCHEMA, "status": OPEN_NOT_FOUND, "pass": False,
                "query": q, "score": 0.0, "documents": [],
                "error": str(e)[:200], "authority": "NONE__LOCAL_GUIDE_UNAVAILABLE"}

    docs.sort(key=lambda d: d["score"], reverse=True)
    docs = docs[:max_snippets]
    best = docs[0]["score"] if docs else 0.0
    enough = bool(docs) and best >= max(min_tokens, needed)
    return {
        "schema": SCHEMA,
        "status": PASS if enough else OPEN_NOT_FOUND,
        "pass": enough,
        "query": q,
        "score": best,
        "min_tokens_required": min_tokens,
        "documents": docs,
        "tokens": tokens,
        "documents_scanned": len(_local_guide_files(root_path)),
        "duration_s": round(time.time() - started, 4),
        "authority": "EXTERNAL_LOCAL_DOCS_RETRIEVED" if enough else "NONE__LOCAL_GUIDE_UNANSWERED",
    }

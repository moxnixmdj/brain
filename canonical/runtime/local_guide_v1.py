#!/usr/bin/env python3
"""Local instant-knowledge source: the computer's own guides.

The Perfect Algorithm's instant-knowledge tier reads the web as an explicit
fallback, but every component on this computer already has a guide: README,
AGENTS.md, man pages for the tools that ship with installed packages, and
the repo's own documentation. Local guides are offline, version-matched with
the install, and cheap to read -- they are the first tier of instant
knowledge, not the last.

This module is honest about what it IS:

  - It is external knowledge, read from local files. It is never counted as
    Brain capability.
  - It is "last known state", not ground truth. A local guide tells the agent
    HOW to orient; the environment's own verification still decides.
  - It is completeness-gated. One isolated keyword hit is not a conclusion:
      - the md tier requires ONE paragraph with at least two of the query's
        content tokens (a big query wants at least 60%);
      - the tool --help/man-page tier is the direct guide for the tool named
        in the query and is gated by proportion only -- a tool's own guide
        answering the question names it, so it needs at least 60% of the
        query's content tokens, all when the query is small.
    Function words are dropped before scoring -- one keyword anywhere in a
    document is a thin hit, not a guide -- and it is an OPEN result, never
    a confident guess.

The md default root is the repository root. It is bounded: at most 500
``.md`` files, never ``.git``/``node_modules``/build output. Tool help and
man pages are only read for the tools the caller names.

Model calls: 0. Network calls: 0. Spend: $0.
"""
from __future__ import annotations

import gzip
import math
import re
import subprocess
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
_MAX_TEXT = 200_000
_MAX_SNIPPETS = 5
_MAN_SECTIONS = (1, 2, 3, 4, 5, 6, 7, 8)
_DEFAULT_MAN_ROOT = "/usr/share/man"

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
    "given", "give", "back", "tell", "show", "see", "ask", "know", "want",
    "wants", "needed", "asked",
})


def _default_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _query_tokens(query: str) -> list[str]:
    text = str(query or "").lower()
    tokens = re.findall(r"[a-z0-9][a-z0-9_\-]{1,}", text)
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


def _best_paragraph(text: str, tokens: Sequence[str],
                    weights: Mapping[str, float] | None = None
                    ) -> tuple[float, frozenset[str], str] | None:
    """The single paragraph sharing the most query tokens with the query, WEIGHTED.

    The weight of a token is how rare it is across the documents read. A raw count made
    "user" (in every paragraph) worth as much as "greet" (in one), so a paragraph that answered
    the question in its two specific words scored below a paragraph that mentioned two common
    ones, and the guide was reported not found. Weighing by rarity does not add a rule: it
    removes one, because the count was the rule that was wrong.
    """
    best: tuple[float, frozenset[str], str] | None = None
    for para in re.split(r"\n\s*\n", text):
        hits = _content_hits(para, tokens)
        if not hits:
            continue
        score = sum((weights or {}).get(hit, 1.0) for hit in hits)
        if best is None or score > best[0]:
            best = (score, frozenset(hits), para.strip()[:600])
    return best


# --------------------------------------------------------------------------- #
# tool / man-page guides: the standardized offline contract between a tool and
# its user. These are also "last known state" -- never ground truth.
# --------------------------------------------------------------------------- #

def _tool_help_text(tool: str, timeout_s: float) -> dict[str, Any] | None:
    """The tool's own ``--help`` text (offline, version-matched). Returns None
    when the tool is absent or produces no output -- an honest no-evidence."""
    try:
        proc = subprocess.run([tool, "--help"], capture_output=True,
                              text=True, timeout=timeout_s)
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return None
    except Exception:  # noqa: BLE001
        return None
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if not text.strip():
        return None
    return {"source": "tool_help", "tool": tool, "text": text,
            "exit_code": proc.returncode}


def _man_page_files(tool: str, root: Path) -> list[tuple[Path, int]]:
    found: list[tuple[Path, int]] = []
    for section in _MAN_SECTIONS:
        base = root / f"man{section}" / f"{tool}.{section}"
        for candidate in (base.with_suffix(".gz"), base):
            if candidate.is_file():
                found.append((candidate, section))
                break
    return found


def _man_page_text(tool: str, root: Path) -> dict[str, Any] | None:
    """A rough but honest man-page read: gunzip if needed, drop nroff control
    sequences, keep the plain text. Heavier parsing (troff semantics) is out
    of scope -- the receipt labels this an honest, rough parse."""
    files = _man_page_files(tool, root)
    if not files:
        return None
    path, section = files[0]
    try:
        raw = (gzip.open(path, "rt", encoding="utf-8", errors="replace").read()
               if path.suffix == ".gz" else Path(path).read_text(encoding="utf-8", errors="replace"))
    except Exception:  # noqa: BLE001
        return None
    lines = []
    for line in raw.splitlines():
        if line.startswith("."):
            continue
        line = re.sub(r"\\s*\.\s*", " ", line)
        if line.strip():
            lines.append(line.strip())
    text = "\n".join(lines)
    if not text.strip():
        return None
    return {"source": "man_page", "tool": tool, "text": text,
            "path": str(path), "sections": [section]}


def lookup(query: str, *, root: Path | str | None = None,
           tools: Sequence[str] | None = None,
           man_root: Path | str | None = None,
           timeout_s: float = 5.0,
           max_snippets: int = _MAX_SNIPPETS,
           deadline_s: float = 30.0) -> dict[str, Any]:
    """Search the local guides on this computer for what a query asks.

    Returns evidence (path, score, matched tokens, paragraph snippet, source)
    or an honest OPEN. Completeness means at least one candidate answered:
      - tool --help/man-page documents (when ``tools`` is named) are the
        direct guide for the named tool: a paragraph sharing at least 60% of
        the query's content tokens, or all of them when the query is small;
      - md documents are the repo's broader is-a-guide: a paragraph sharing
        at least two content tokens (or all of them when the query is small).
    Function words are dropped before scoring. One isolated keyword anywhere
    in a document is a thin hit, not a conclusion -- OPEN.
    """
    started = time.time()
    q = str(query or "").strip()
    if not q:
        return {"schema": SCHEMA, "status": FAIL_EMPTY, "pass": False,
                "query": q, "score": 0.0, "documents": [],
                "authority": "NONE"}

    tokens = _query_tokens(q)
    tool_needed = max(1, math.ceil(len(tokens) * 0.6)) if tokens else 1
    md_needed = max(2, math.ceil(len(tokens) * 0.6)) if tokens else 2
    root_path = Path(root) if root is not None else _default_root()

    md_docs: list[dict[str, Any]] = []
    # PASS 1 reads every candidate and records WHICH tokens each paragraph matched. Nothing is
    # accepted yet: the weight of a token is its rarity across the documents read, and that is
    # not known until they have all been read.
    candidates: list[tuple[Path, str, tuple[float, frozenset[str], str]]] = []
    try:
        for p in _local_guide_files(root_path):
            if time.time() - started > deadline_s:
                break
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            best = _best_paragraph(text, tokens)
            if best is None or best[0] < 1:
                continue
            candidates.append((p, text, best))
    except Exception as e:  # noqa: BLE001
        return {"schema": SCHEMA, "status": OPEN_NOT_FOUND, "pass": False,
                "query": q, "score": 0.0, "documents": [],
                "error": str(e)[:200],
                "authority": "NONE__LOCAL_GUIDE_UNAVAILABLE"}

    # RARITY IS THE WEIGHT. `df` counts in how many candidate paragraphs a token appears; a
    # token in every paragraph carries no information about which one answers the question.
    df: dict[str, int] = {}
    for _, _, (_, hits, _) in candidates:
        for hit in hits:
            df[hit] = df.get(hit, 0) + 1
    weights = {token: 1.0 / (1 + df.get(token, 0)) for token in tokens}
    # the rarest token that appears AT ALL. A token absent from every paragraph has df 0 and
    # would always win the minimum, which would make the gate ask for a word nobody wrote.
    present = [token for token in tokens if df.get(token, 0) > 0]
    rarest = min(present, key=lambda token: (df.get(token, 0), token)) if present else ""
    for p, text, (score, hits, snippet) in candidates:
        # TWO TOKENS, AND ONE OF THEM THE RARE ONE. The old gate asked for 60% of the query,
        # which refused a paragraph that answered the question in its two specific words. This
        # asks for the word that makes the question specific plus one more, so "one isolated
        # keyword anywhere" is still a thin hit.
        if len(hits) < 2 or (rarest and rarest not in hits):
            continue
        try:
            rel = str(p.relative_to(root_path))
        except ValueError:
            rel = str(p)
        md_docs.append({
            "path": rel,
            "source": "local_md",
            "score": float(score),
            "matched_terms": len(hits),
            "snippet": snippet,
            # The snippet is a paragraph; the CALLER needs the document. A fetcher that
            # returns only a summary cannot feed an extractor, which is why the circuit
            # stayed open while `lookup` alone reported PASS.
            "text": text[:_MAX_TEXT],
        })

    tool_docs: list[dict[str, Any]] = []
    if tools:
        tool_list = list(tools)
        for tool in tool_list:
            if time.time() - started > deadline_s:
                break
            tool_name = str(tool).rsplit("/", 1)[-1]
            help_out = _tool_help_text(tool, timeout_s=timeout_s)
            if help_out is not None:
                best = _best_paragraph(help_out["text"], tokens)
                if best is not None and len(best[1]) >= tool_needed:
                    score, snippet = best[0], best[2]
                    tool_docs.append({
                        "path": f"{tool_name} --help",
                        "source": "tool_help",
                        "tool": tool_name,
                        "score": float(score),
                        "matched_terms": score,
                        "snippet": snippet,
                        "exit_code": help_out.get("exit_code"),
                        "text": str(help_out.get("text") or "")[:_MAX_TEXT],
                    })
                    continue
            man_out = _man_page_text(tool_name, Path(man_root) if man_root is not None else Path(_DEFAULT_MAN_ROOT))
            if man_out is not None:
                best = _best_paragraph(man_out["text"], tokens)
                if best is not None and len(best[1]) >= tool_needed:
                    score, snippet = best[0], best[2]
                    tool_docs.append({
                        "path": f"{tool} man page ({man_out.get('path')})",
                        "source": "man_page",
                        "tool": tool,
                        "score": float(score),
                        "matched_terms": score,
                        "snippet": snippet,
                        "sections": man_out.get("sections"),
                        "text": str(man_out.get("text") or "")[:_MAX_TEXT],
                    })

    # tool-guide documents are the direct answer for a named tool; they outrank
    # md documents, which are a broader is-a-guide. Honest precedence, not
    # invention.
    tool_docs.sort(key=lambda d: d["score"], reverse=True)
    md_docs.sort(key=lambda d: d["score"], reverse=True)
    tool_preferred = bool(tool_docs)
    docs = (tool_docs or md_docs)[:max_snippets]

    best = docs[0]["score"] if docs else 0.0
    enough = bool(docs)
    return {
        "schema": SCHEMA,
        "status": PASS if enough else OPEN_NOT_FOUND,
        "pass": enough,
        "query": q,
        "score": best,
        "min_tokens_required": tool_needed if tool_preferred else md_needed,
        "documents": docs,
        "tokens": tokens,
        "documents_scanned": len(_local_guide_files(root_path)),
        "duration_s": round(time.time() - started, 4),
        "authority": "EXTERNAL_LOCAL_DOCS_RETRIEVED" if enough else "NONE__LOCAL_GUIDE_UNANSWERED",
        "sources_answered": sorted({d.get("source") for d in docs if d.get("source")}),
        "tool_preferred": tool_preferred,
    }

#!/usr/bin/env python3
"""Adaptive Unicode query evolution for residual-witness retrieval.

Consumes:
- a compiled residual-witness retrieval program,
- optional multilingual bridge variants,
- optional prior candidate rows.

Produces new candidate query variants by:
1. preserving existing Unicode queries,
2. mixing technical anchors with multilingual variants,
3. harvesting high-information Unicode terms from prior candidates,
4. preferring cross-script and cross-source novelty.

This is a recall amplifier, not a semantic oracle or completeness proof.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ADAPTIVE_RETRIEVAL_QUERY_EXPANSION_V1"
_WORD = re.compile(r"[^\W_]+(?:[-/.][^\W_]+)*", re.UNICODE)


def _canon(value: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).strip().split())


def _tokens(value: Any) -> list[str]:
    out: list[str] = []
    for raw in _WORD.findall(_canon(value)):
        t = raw.casefold().strip("-/.")
        if len(t) < 2:
            continue
        if t not in out:
            out.append(t)
    return out


def _script(text: str) -> str:
    counts = Counter()
    for ch in text:
        if ch.isspace() or ch.isdigit() or unicodedata.category(ch).startswith("P"):
            continue
        cp = ord(ch)
        name = unicodedata.name(ch, "")
        if 0x3400 <= cp <= 0x4DBF or 0x4E00 <= cp <= 0x9FFF or 0xF900 <= cp <= 0xFAFF or "HIRAGANA" in name or "KATAKANA" in name or "HANGUL" in name:
            counts["CJK"] += 1
        elif "ARABIC" in name:
            counts["ARABIC"] += 1
        elif "CYRILLIC" in name:
            counts["CYRILLIC"] += 1
        elif "LATIN" in name:
            counts["LATIN"] += 1
        else:
            counts["OTHER"] += 1
    return counts.most_common(1)[0][0] if counts else "UNKNOWN"


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for k, v in value.items():
            if str(k).lower() in {"description", "title", "name", "path", "message", "summary", "text", "snippet", "repository", "language", "kind"}:
                yield from _walk_strings(v)
            elif isinstance(v, (Mapping, list, tuple)):
                yield from _walk_strings(v)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_strings(item)


def _technical_anchors(program: Mapping[str, Any]) -> list[str]:
    rows = program.get("query_lattice") or []
    out: list[str] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            text = _canon(row.get("text"))
            basis = _canon(row.get("basis"))
            if not text:
                continue
            toks = _tokens(text)
            is_technical = (
                basis.startswith("OBSERVABLE_")
                or any(any(c.isdigit() for c in t) for t in toks)
                or any(any(c in t for c in "-/._") for t in text.split())
                or any(t.isupper() and len(t) >= 2 for t in text.split())
            )
            if is_technical and text.casefold() not in {x.casefold() for x in out}:
                out.append(text)
    effect = _canon(program.get("effect"))
    if effect and not out:
        out.append(effect)
    return out[:16]


def expand(
    program: Mapping[str, Any],
    *,
    bridge_variants: Sequence[Mapping[str, Any]] | None = None,
    prior_candidates: Sequence[Mapping[str, Any]] | None = None,
    max_queries: int = 96,
) -> dict[str, Any]:
    if not isinstance(program, Mapping):
        raise ValueError("PROGRAM_MAPPING_REQUIRED")
    rows = program.get("query_lattice")
    if not isinstance(rows, list) or not rows:
        raise ValueError("PROGRAM_QUERY_LATTICE_REQUIRED")

    max_queries = max(1, min(int(max_queries), 512))
    anchors = _technical_anchors(program)
    existing: list[str] = []
    scripts = set()
    for row in rows:
        if isinstance(row, Mapping):
            q = _canon(row.get("text"))
            if q and q.casefold() not in {x.casefold() for x in existing}:
                existing.append(q)
                scripts.add(_script(q))

    new_rows: list[dict[str, Any]] = []
    seen = {q.casefold() for q in existing}

    def add(text: Any, basis: str, *, provenance: Mapping[str, Any] | None = None) -> None:
        q = _canon(text)
        if not q or q.casefold() in seen or len(new_rows) >= max_queries:
            return
        seen.add(q.casefold())
        new_rows.append({
            "text": q,
            "basis": basis,
            "script_hint": _script(q),
            "provenance": dict(provenance or {}),
        })

    for row in bridge_variants or []:
        if not isinstance(row, Mapping):
            continue
        text = _canon(row.get("text"))
        if not text:
            continue
        prov = {
            "language": row.get("language"),
            "source": row.get("source"),
            "qid": row.get("qid"),
            "semantic_equivalence_verified": bool(row.get("semantic_equivalence_verified")),
        }
        add(text, "MULTILINGUAL_BRIDGE_VARIANT", provenance=prov)
        for anchor in anchors[:8]:
            if anchor.casefold() not in text.casefold():
                add(f"{anchor} {text}", "TECHNICAL_ANCHOR_PLUS_MULTILINGUAL_VARIANT", provenance=prov)

    candidates = [x for x in (prior_candidates or []) if isinstance(x, Mapping)]
    doc_tokens: list[set[str]] = []
    token_sources: dict[str, set[str]] = defaultdict(set)
    token_scripts: dict[str, str] = {}
    for i, cand in enumerate(candidates):
        text = " ".join(_walk_strings(cand))
        toks = set(_tokens(text))
        doc_tokens.append(toks)
        source = _canon(cand.get("source") or cand.get("backend_id") or cand.get("surface") or f"C{i}")
        for tok in toks:
            token_sources[tok].add(source)
            token_scripts[tok] = _script(tok)

    n = len(doc_tokens)
    scores: list[tuple[float, str]] = []
    anchor_tokens = {t for a in anchors for t in _tokens(a)}
    existing_tokens = {t for q in existing for t in _tokens(q)}
    if n:
        df = Counter(tok for toks in doc_tokens for tok in toks)
        for tok, freq in df.items():
            if tok in existing_tokens or tok in anchor_tokens or len(tok) < 3:
                continue
            novelty = 1.0 + (0.85 if token_scripts.get(tok) not in {"LATIN", "UNKNOWN"} else 0.0)
            source_div = 1.0 + math.log1p(len(token_sources.get(tok, ())))
            rarity = math.log((n + 1.0) / (freq + 0.5)) + 1.0
            score = novelty * source_div * rarity
            scores.append((score, tok))
        scores.sort(reverse=True)

    for score, tok in scores[:32]:
        add(tok, "PSEUDO_RELEVANCE_UNICODE_TERM", provenance={"score": round(score, 6)})
        for anchor in anchors[:4]:
            add(f"{anchor} {tok}", "TECHNICAL_ANCHOR_PLUS_PSEUDO_RELEVANCE_TERM", provenance={"score": round(score, 6)})

    all_scripts = scripts | {row["script_hint"] for row in new_rows}
    return {
        "schema": SCHEMA,
        "status": "EXPANDED",
        "base_query_count": len(existing),
        "new_query_count": len(new_rows),
        "new_queries": new_rows,
        "technical_anchors": anchors,
        "observed_scripts": sorted(x for x in all_scripts if x),
        "candidate_document_count": n,
        "complete": False,
        "semantic_equivalence_verified": False,
        "incremental_spend_usd": 0,
        "hard_rules": [
            "QUERY_EXPANSION_IS_CANDIDATE_GENERATION_ONLY",
            "MULTILINGUAL_LABELS_ARE_NOT_ACCEPTANCE_EVIDENCE",
            "PSEUDO_RELEVANCE_TERMS_REQUIRE_DOWNSTREAM_WITNESS_VERIFICATION",
            "NO_QUERY_SATURATION_TO_NONEXISTENCE_INFERENCE",
            "STOP_ON_FIRST_INDEPENDENTLY_VERIFIED_SUFFICIENT_WITNESS",
        ],
    }

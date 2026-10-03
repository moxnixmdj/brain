"""Retrieval V6 omniretrieval planner.

The planner turns one residual/proof obligation into independent discovery
channels. It deliberately separates *diminishing novelty* from *completeness*:
repeated zero-yield rounds are scheduling evidence only and can never prove
that an open-world witness does not exist.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence
import re

SCHEMA = "PROJECT_BRAIN_EVIDENCE_OMNIRETRIEVAL_PLAN_V2"
CHANNELS = (
    "LEXICAL",
    "MULTILINGUAL",
    "INVARIANT",
    "STRUCTURAL_CODE",
    "BEHAVIORAL",
    "HISTORY",
    "GRAPH",
    "ECOSYSTEM",
    "QUERYLESS_ENUMERATION",
    "ARCHIVE",
)


@dataclass(frozen=True)
class ProofObligation:
    obligation_id: str
    concepts: tuple[str, ...]
    aliases: tuple[str, ...] = ()
    language_variants: tuple[str, ...] = ()
    numeric_anchors: tuple[str, ...] = ()
    identifiers: tuple[str, ...] = ()
    code_symbols: tuple[str, ...] = ()
    hashes: tuple[str, ...] = ()
    io_signatures: tuple[str, ...] = ()
    protocols: tuple[str, ...] = ()
    seed_repositories: tuple[str, ...] = ()
    authors: tuple[str, ...] = ()
    citations: tuple[str, ...] = ()
    enumerable_scopes: tuple[str, ...] = ()
    archive_seeds: tuple[str, ...] = ()


def _clean(xs: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in xs:
        value = " ".join(str(raw or "").split())
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            out.append(value)
    return out


def _numeric_variants(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    for raw in _clean(values):
        vals = [raw]
        try:
            stripped = raw.rstrip("%")
            x = float(stripped)
            if raw.endswith("%"):
                vals.append(str(x / 100.0))
            elif 0 <= x <= 1:
                vals.append(f"{x * 100:g}%")
            else:
                vals.append(f"{x:g}")
        except Exception:
            pass
        for value in vals:
            if value not in out:
                out.append(value)
    return out


def compile_channels(o: ProofObligation) -> dict:
    concepts = _clean(o.concepts)
    if not o.obligation_id or not concepts:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "OBLIGATION_ID_AND_CONCEPT_REQUIRED"}

    aliases = _clean(o.aliases)
    lang = _clean(o.language_variants)
    identifiers = _clean(o.identifiers)
    symbols = _clean(o.code_symbols)
    hashes = _clean(o.hashes)
    numbers = _numeric_variants(o.numeric_anchors)
    io = _clean(o.io_signatures)
    protocols = _clean(o.protocols)
    seeds = _clean(o.seed_repositories)
    authors = _clean(o.authors)
    citations = _clean(o.citations)
    scopes = _clean(o.enumerable_scopes)
    archives = _clean(o.archive_seeds)

    lexical = [f'"{x}"' for x in concepts + aliases]
    multilingual = [x for x in aliases + lang if any(ord(ch) > 127 for ch in x)]
    invariant = identifiers + hashes + numbers + protocols

    structural: list[str] = []
    for sym in symbols:
        structural += [sym, f"symbol:{sym}"]
    for ident in identifiers:
        if re.search(r"[A-Za-z_][A-Za-z0-9_.:/@-]{2,}", ident):
            structural.append(ident)

    behavioral = io + [f"protocol:{x}" for x in protocols]
    history = [item for seed in seeds for item in (
        f"repo:{seed} branches tags releases",
        f"repo:{seed} commits diffs deleted-files",
        f"repo:{seed} forks mirrors",
    )]
    graph = [item for seed in seeds for item in (
        f"repo:{seed} dependencies dependents",
        f"repo:{seed} contributors related-repositories",
        f"repo:{seed} references backlinks",
    )]
    graph += [f"author:{a}" for a in authors]
    graph += [f"citation:{c}" for c in citations]

    ecosystem = [item for ident in identifiers + concepts + protocols for item in (
        f"code-host:{ident}",
        f"package-registry:{ident}",
        f"model-dataset-registry:{ident}",
        f"scholarly:{ident}",
        f"technical-discussion:{ident}",
    )]
    enumeration = [f"enumerate:{scope}" for scope in scopes]
    archive = [f"archive:{x}" for x in archives + seeds]

    payload = {
        "LEXICAL": _clean(lexical),
        "MULTILINGUAL": _clean(multilingual),
        "INVARIANT": _clean(invariant),
        "STRUCTURAL_CODE": _clean(structural),
        "BEHAVIORAL": _clean(behavioral),
        "HISTORY": _clean(history),
        "GRAPH": _clean(graph),
        "ECOSYSTEM": _clean(ecosystem),
        "QUERYLESS_ENUMERATION": _clean(enumeration),
        "ARCHIVE": _clean(archive),
    }
    active = [name for name, rows in payload.items() if rows]
    nonlex = [x for x in active if x not in {"LEXICAL", "MULTILINGUAL"}]
    return {
        "schema": SCHEMA,
        "status": "COMPILED" if nonlex else "FAIL_CLOSED",
        "obligation_id": o.obligation_id,
        "channels": payload,
        "active_channels": active,
        "nonlexical_channel_count": len(nonlex),
        "lexical_only_saturation_forbidden": True,
        "queryless_enumeration_available": bool(enumeration),
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "incremental_spend_usd": 0,
        "hard_rules": [
            "LEXICAL_ONLY_SEARCH_CANNOT_PROVE_COMPLETENESS",
            "MULTILINGUAL_SEARCH_IS_CANDIDATE_GENERATION_NOT_SEMANTIC_PROOF",
            "QUERYLESS_ENUMERATION_PRECEDES_NEGATIVE_CLAIMS_WHEN_A_FINITE_ENUMERABLE_SCOPE_EXISTS",
            "ZERO_YIELD_ROUNDS_ARE_DIMINISHING_RETURN_EVIDENCE_ONLY",
            "OPEN_WORLD_NO_RESULT_REMAINS_UNKNOWN",
        ],
    }


def novelty_signal(plan: dict, rounds: Sequence[dict], *, zero_round_window: int = 2) -> dict:
    """Return a scheduling signal only; never a completeness verdict."""
    if plan.get("status") != "COMPILED":
        return {"status": "FAIL_CLOSED", "reason": "PLAN_NOT_COMPILED"}
    if zero_round_window < 1:
        return {"status": "FAIL_CLOSED", "reason": "INVALID_ZERO_ROUND_WINDOW"}
    active = set(plan.get("active_channels") or [])
    consecutive = {c: 0 for c in active}
    observed = {c: False for c in active}
    for row in rounds:
        channel = row.get("channel")
        if channel not in active:
            continue
        observed[channel] = True
        count = row.get("new_unique_candidates")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            return {"status": "FAIL_CLOSED", "reason": "INVALID_ROUND_COUNT"}
        consecutive[channel] = consecutive[channel] + 1 if count == 0 else 0
    missing = sorted(c for c in active if not observed[c])
    low_novelty = sorted(c for c in active if observed[c] and consecutive[c] >= zero_round_window)
    return {
        "schema": "PROJECT_BRAIN_RETRIEVAL_NOVELTY_SIGNAL_V1",
        "status": "LOW_NOVELTY_SIGNAL" if not missing and len(low_novelty) == len(active) else "CONTINUE_OR_RERANK",
        "missing_channels": missing,
        "low_novelty_channels": low_novelty,
        "completeness_proof": False,
        "nonexistence_claim_authorized": False,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
    }

#!/usr/bin/env python3
"""Residual-to-witness retrieval compiler.

This module is intentionally source-agnostic. It compiles one exact unresolved
acceptance residual into a finite, auditable retrieval program that:
- preserves Unicode/native-language terms;
- expands across behavioral, identifier, alias, and language-variant queries;
- searches orthogonal evidence surfaces rather than trusting repository metadata;
- never treats "no result" as "no solution";
- stops immediately when a verified sufficient witness is present;
- permits "exhaustively closed" only for a declared scope whose required
  retrieval cells are independently marked complete.

It does not claim that the public internet is enumerable or that any current
backend is complete.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_RESIDUAL_WITNESS_RETRIEVAL_COMPILER_V1"

SURFACES = (
    "PACKAGE_REGISTRY",
    "REPOSITORY_METADATA",
    "CODE_CONTENT",
    "SYMBOLS",
    "MANIFESTS",
    "TESTS_EXAMPLES",
    "ISSUES_PRS",
    "COMMITS_RELEASES_BRANCHES_TAGS",
    "DOCUMENTATION",
    "OPEN_WEB",
    "SCHOLARLY",
    "SOCIAL_TECHNICAL_DISCUSSION",
)

CANDIDATE_ONLY_SURFACES = {"REPOSITORY_METADATA", "SOCIAL_TECHNICAL_DISCUSSION"}

SURFACE_PRIOR = {
    "PACKAGE_REGISTRY": (0.78, 1.0, 0.65),
    "REPOSITORY_METADATA": (0.55, 0.8, 0.35),
    "CODE_CONTENT": (0.92, 1.8, 0.95),
    "SYMBOLS": (0.88, 1.3, 0.90),
    "MANIFESTS": (0.82, 1.0, 0.80),
    "TESTS_EXAMPLES": (0.86, 1.5, 0.90),
    "ISSUES_PRS": (0.52, 1.3, 0.50),
    "COMMITS_RELEASES_BRANCHES_TAGS": (0.64, 1.7, 0.70),
    "DOCUMENTATION": (0.72, 1.0, 0.65),
    "OPEN_WEB": (0.60, 1.0, 0.55),
    "SCHOLARLY": (0.38, 1.2, 0.42),
    "SOCIAL_TECHNICAL_DISCUSSION": (0.24, 0.7, 0.32),
}

CELL_STATES = {
    "UNQUERIED",
    "QUERIED_NO_CANDIDATE",
    "QUERIED_CANDIDATE",
    "FAILED_TRANSIENT",
    "FAILED_PERMANENT",
    "EXHAUSTIVELY_CLOSED",
}

_WORD = re.compile(r"[^\W_]+(?:[-/.][^\W_]+)*", re.UNICODE)


def _canon(value: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).strip().split())


def unicode_tokens(value: Any) -> list[str]:
    """Return stable Unicode tokens without collapsing non-Latin scripts."""
    out: list[str] = []
    for raw in _WORD.findall(_canon(value)):
        t = raw.casefold().strip("-/.")
        if not t:
            continue
        if t not in out:
            out.append(t)
    return out


def _script_hint(text: str) -> str:
    counts = {"CJK": 0, "ARABIC": 0, "CYRILLIC": 0, "LATIN": 0, "OTHER": 0}
    for ch in text:
        if ch.isspace() or ch.isdigit() or unicodedata.category(ch).startswith("P"):
            continue
        cp = ord(ch)
        name = unicodedata.name(ch, "")
        if (
            0x3400 <= cp <= 0x4DBF
            or 0x4E00 <= cp <= 0x9FFF
            or 0xF900 <= cp <= 0xFAFF
            or "HIRAGANA" in name
            or "KATAKANA" in name
            or "HANGUL" in name
        ):
            counts["CJK"] += 1
        elif "ARABIC" in name:
            counts["ARABIC"] += 1
        elif "CYRILLIC" in name:
            counts["CYRILLIC"] += 1
        elif "LATIN" in name:
            counts["LATIN"] += 1
        else:
            counts["OTHER"] += 1
    best = max(counts, key=counts.get)
    return best if counts[best] else "UNKNOWN"


def _clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        raise ValueError("EXPECTED_STRING_LIST")
    out = []
    for item in value:
        text = _canon(item)
        if text and text not in out:
            out.append(text)
    return out


def compile_residual(residual: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(residual, Mapping):
        raise ValueError("RESIDUAL_MAPPING_REQUIRED")
    residual_id = _canon(residual.get("residual_id"))
    effect = _canon(residual.get("effect") or residual.get("objective"))
    required = _clean_list(residual.get("required_capabilities"))
    if not residual_id:
        raise ValueError("RESIDUAL_ID_REQUIRED")
    if not effect and not required:
        raise ValueError("RESIDUAL_EFFECT_OR_CAPABILITY_REQUIRED")

    observables = residual.get("observables") or {}
    if not isinstance(observables, Mapping):
        raise ValueError("OBSERVABLES_MAPPING_REQUIRED")

    aliases = _clean_list(residual.get("aliases"))
    language_variants = residual.get("language_variants") or {}
    if not isinstance(language_variants, Mapping):
        raise ValueError("LANGUAGE_VARIANTS_MAPPING_REQUIRED")

    query_rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(text: Any, basis: str, language_hint: str | None = None) -> None:
        q = _canon(text)
        if not q:
            return
        key = q.casefold()
        if key in seen:
            return
        seen.add(key)
        query_rows.append({
            "query_id": f"Q{len(query_rows):03d}",
            "text": q,
            "basis": basis,
            "language_hint": language_hint or _script_hint(q),
        })

    if effect:
        add(effect, "RESIDUAL_EFFECT")
        toks = unicode_tokens(effect)
        if toks:
            add(" ".join(toks[:48]), "UNICODE_SUBJECT_TOKENS")

    for cap in required:
        add(cap, "REQUIRED_CAPABILITY")

    for alias in aliases:
        add(alias, "ALIAS")

    for language, variants in sorted(language_variants.items(), key=lambda kv: str(kv[0])):
        for variant in _clean_list(variants):
            add(variant, "LANGUAGE_VARIANT", str(language))

    observable_keys = (
        "api_symbols",
        "commands",
        "protocols",
        "file_formats",
        "error_strings",
        "imports",
        "input_signatures",
        "output_signatures",
    )
    observable_terms: list[str] = []
    for key in observable_keys:
        for term in _clean_list(observables.get(key)):
            observable_terms.append(term)
            add(term, "OBSERVABLE_" + key.upper())

    anchor = effect or " ".join(required)
    for term in observable_terms[:24]:
        if anchor and term.casefold() not in anchor.casefold():
            add(f"{anchor} {term}", "BEHAVIOR_PLUS_OBSERVABLE")

    if not query_rows:
        raise ValueError("NO_QUERY_VARIANTS_COMPILED")

    scope = residual.get("declared_scope")
    if scope is not None and not isinstance(scope, Mapping):
        raise ValueError("DECLARED_SCOPE_MAPPING_REQUIRED")

    digest_payload = {
        "residual_id": residual_id,
        "effect": effect,
        "required_capabilities": required,
        "queries": query_rows,
        "declared_scope": scope,
    }
    digest = hashlib.sha256(
        json.dumps(
            digest_payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    return {
        "schema": SCHEMA,
        "status": "COMPILED",
        "residual_id": residual_id,
        "effect": effect or None,
        "required_capabilities": required,
        "constraints": dict(residual.get("constraints") or {}),
        "query_lattice": query_rows,
        "surfaces": list(SURFACES),
        "candidate_only_surfaces": sorted(CANDIDATE_ONLY_SURFACES),
        "declared_scope": dict(scope) if isinstance(scope, Mapping) else None,
        "retrieval_program_sha256": digest,
        "hard_rules": [
            "NO_RESULT_IS_NOT_NONEXISTENCE",
            "REPOSITORY_METADATA_IS_NEVER_SUFFICIENT_ACCEPTANCE_EVIDENCE",
            "CANDIDATE_ONLY_SURFACES_CANNOT_CLOSE_ACCEPTANCE",
            "STOP_ON_FIRST_INDEPENDENTLY_VERIFIED_SUFFICIENT_WITNESS",
            "EXHAUSTIVE_CLOSURE_REQUIRES_DECLARED_SCOPE_AND_ALL_REQUIRED_CELLS_CLOSED",
        ],
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


def initial_state(program: Mapping[str, Any]) -> dict[str, Any]:
    if program.get("schema") != SCHEMA or program.get("status") != "COMPILED":
        raise ValueError("COMPILED_PROGRAM_REQUIRED")
    cells = []
    for q in program["query_lattice"]:
        for surface in program["surfaces"]:
            cells.append({
                "query_id": q["query_id"],
                "surface": surface,
                "state": "UNQUERIED",
                "candidate_count": 0,
                "independently_complete": False,
            })
    return {
        "schema": "PROJECT_BRAIN_RESIDUAL_WITNESS_RETRIEVAL_STATE_V1",
        "residual_id": program["residual_id"],
        "retrieval_program_sha256": program["retrieval_program_sha256"],
        "cells": cells,
        "verified_witnesses": [],
        "observed_candidates": [],
        "declared_scope": program.get("declared_scope"),
    }


def _valid_cell(cell: Mapping[str, Any]) -> None:
    if cell.get("state") not in CELL_STATES:
        raise ValueError("CELL_STATE_INVALID")
    if cell.get("surface") not in SURFACES:
        raise ValueError("CELL_SURFACE_INVALID")


def update_cell(
    state: Mapping[str, Any],
    *,
    query_id: str,
    surface: str,
    cell_state: str,
    candidate_count: int = 0,
    independently_complete: bool = False,
) -> dict[str, Any]:
    if cell_state not in CELL_STATES:
        raise ValueError("CELL_STATE_INVALID")
    out = json.loads(json.dumps(state))
    matched = 0
    for cell in out.get("cells") or []:
        if cell.get("query_id") == query_id and cell.get("surface") == surface:
            cell["state"] = cell_state
            cell["candidate_count"] = max(0, int(candidate_count))
            cell["independently_complete"] = bool(independently_complete)
            matched += 1
    if matched != 1:
        raise ValueError("CELL_NOT_UNIQUE")
    return out


def add_verified_witness(
    state: Mapping[str, Any],
    *,
    witness_id: str,
    residual_id: str,
    source_surface: str,
    independent_receipt: str,
) -> dict[str, Any]:
    if source_surface in CANDIDATE_ONLY_SURFACES:
        raise ValueError("CANDIDATE_ONLY_SURFACE_CANNOT_VERIFY")
    if source_surface not in SURFACES:
        raise ValueError("WITNESS_SURFACE_INVALID")
    if _canon(residual_id) != _canon(state.get("residual_id")):
        raise ValueError("WITNESS_RESIDUAL_MISMATCH")
    wid = _canon(witness_id)
    receipt = _canon(independent_receipt)
    if not wid or not receipt:
        raise ValueError("WITNESS_ID_AND_RECEIPT_REQUIRED")
    out = json.loads(json.dumps(state))
    rec = {
        "witness_id": wid,
        "residual_id": _canon(residual_id),
        "source_surface": source_surface,
        "independent_receipt": receipt,
        "verified_sufficient": True,
    }
    if rec not in out.setdefault("verified_witnesses", []):
        out["verified_witnesses"].append(rec)
    return out


def capture_recapture_unseen(
    single_source_only: int,
    multi_source_overlap: int,
) -> dict[str, Any]:
    """Heuristic unseen-mass alarm; never a completeness proof."""
    n1 = max(0, int(single_source_only))
    n2 = max(0, int(multi_source_overlap))
    if n2 == 0:
        return {
            "status": "UNBOUNDED_OR_INSUFFICIENT_OVERLAP",
            "estimated_unseen": None,
            "completeness_proof": False,
        }
    estimate = (n1 * n1) / (2.0 * n2)
    return {
        "status": "HEURISTIC_ESTIMATE_ONLY",
        "estimated_unseen": estimate,
        "completeness_proof": False,
    }


def _all_declared_cells_closed(state: Mapping[str, Any]) -> bool:
    scope = state.get("declared_scope")
    if (
        not isinstance(scope, Mapping)
        or scope.get("independently_verified_complete") is not True
    ):
        return False
    cells = state.get("cells") or []
    if not cells:
        return False

    all_surfaces = {str(cell.get("surface")) for cell in cells}
    all_queries = {str(cell.get("query_id")) for cell in cells}
    required_surfaces = set(scope.get("required_surfaces") or all_surfaces)
    required_queries = set(scope.get("required_query_ids") or all_queries)
    if not required_surfaces or not required_queries:
        return False
    if not required_surfaces.issubset(all_surfaces):
        raise ValueError("DECLARED_SCOPE_SURFACE_OUTSIDE_PROGRAM")
    if not required_queries.issubset(all_queries):
        raise ValueError("DECLARED_SCOPE_QUERY_OUTSIDE_PROGRAM")

    relevant = [
        cell for cell in cells
        if str(cell.get("surface")) in required_surfaces
        and str(cell.get("query_id")) in required_queries
    ]
    if len(relevant) != len(required_surfaces) * len(required_queries):
        raise ValueError("DECLARED_SCOPE_CELL_MATRIX_INCOMPLETE")
    for cell in relevant:
        _valid_cell(cell)
        if not (
            cell.get("state") == "EXHAUSTIVELY_CLOSED"
            and cell.get("independently_complete") is True
        ):
            return False
    return True


def terminal_status(state: Mapping[str, Any]) -> dict[str, Any]:
    witnesses = [
        w for w in (state.get("verified_witnesses") or [])
        if w.get("verified_sufficient") is True
        and _canon(w.get("residual_id")) == _canon(state.get("residual_id"))
        and w.get("source_surface") not in CANDIDATE_ONLY_SURFACES
        and _canon(w.get("independent_receipt"))
    ]
    if witnesses:
        return {
            "status": "VERIFIED_WITNESS_FOUND",
            "stop": True,
            "witness": witnesses[0],
            "nonexistence_claim_authorized": False,
        }
    if _all_declared_cells_closed(state):
        return {
            "status": "DECLARED_SCOPE_EXHAUSTIVELY_CLOSED",
            "stop": True,
            "witness": None,
            "nonexistence_claim_authorized": True,
            "scope_limited": True,
        }
    return {
        "status": "UNKNOWN_CONTINUE_RETRIEVAL",
        "stop": False,
        "witness": None,
        "nonexistence_claim_authorized": False,
    }


def _cell_priority(
    cell: Mapping[str, Any],
    query_count: int,
    query_basis: str,
    surface_attempts: int,
) -> float:
    surface = str(cell["surface"])
    p_close, cost, coverage_gain = SURFACE_PRIOR[surface]
    query_penalty = 1.0 + 0.015 * max(0, query_count - 1)
    repeat_penalty = 1.0 + 2.0 * max(0, surface_attempts)
    compatibility = 1.0
    if query_basis.startswith("OBSERVABLE_API_SYMBOLS") and surface in {"SYMBOLS", "CODE_CONTENT"}:
        compatibility = 1.45
    elif query_basis.startswith("OBSERVABLE_IMPORTS") and surface in {"MANIFESTS", "CODE_CONTENT"}:
        compatibility = 1.35
    elif query_basis.startswith("OBSERVABLE_COMMANDS") and surface in {"PACKAGE_REGISTRY", "DOCUMENTATION", "CODE_CONTENT"}:
        compatibility = 1.25
    elif query_basis == "LANGUAGE_VARIANT" and surface in {"CODE_CONTENT", "OPEN_WEB", "REPOSITORY_METADATA", "DOCUMENTATION"}:
        compatibility = 1.20
    elif query_basis == "BEHAVIOR_PLUS_OBSERVABLE" and surface in {"CODE_CONTENT", "TESTS_EXAMPLES", "SYMBOLS"}:
        compatibility = 1.30
    return (
        (p_close + 0.35 * coverage_gain)
        * compatibility
        / (cost * query_penalty * repeat_penalty)
    )


def next_action(
    program: Mapping[str, Any],
    state: Mapping[str, Any],
) -> dict[str, Any]:
    terminal = terminal_status(state)
    if terminal["stop"]:
        return {"action": "STOP", **terminal}

    query_map = {
        q["query_id"]: q
        for q in program.get("query_lattice") or []
    }
    attempts_by_surface = {surface: 0 for surface in SURFACES}
    for prior in state.get("cells") or []:
        _valid_cell(prior)
        if prior.get("state") != "UNQUERIED":
            attempts_by_surface[str(prior["surface"])] += 1

    candidates = []
    for cell in state.get("cells") or []:
        _valid_cell(cell)
        if cell.get("state") not in {"UNQUERIED", "FAILED_TRANSIENT"}:
            continue
        qid = cell.get("query_id")
        if qid not in query_map:
            raise ValueError("STATE_QUERY_NOT_IN_PROGRAM")
        query = query_map[qid]
        priority = _cell_priority(
            cell,
            len(query_map),
            str(query.get("basis") or ""),
            attempts_by_surface[str(cell["surface"])],
        )
        if cell.get("state") == "FAILED_TRANSIENT":
            priority *= 0.85
        candidates.append((priority, str(qid), str(cell["surface"])))

    if not candidates:
        return {
            "action": "ESCALATE",
            "reason": "NO_QUERYABLE_CELL_BUT_SCOPE_NOT_PROVEN_COMPLETE",
            "status": terminal["status"],
        }

    candidates.sort(key=lambda row: (-row[0], row[1], row[2]))
    score, qid, surface = candidates[0]
    q = query_map[qid]
    return {
        "action": "QUERY",
        "query_id": qid,
        "query": q["text"],
        "basis": q["basis"],
        "language_hint": q["language_hint"],
        "surface": surface,
        "priority_score": round(score, 9),
        "acceptance_credit": 0,
    }


def evaluate(residual: Mapping[str, Any]) -> dict[str, Any]:
    program = compile_residual(residual)
    state = initial_state(program)
    return {
        "program": program,
        "state": state,
        "terminal": terminal_status(state),
        "next_action": next_action(program, state),
    }

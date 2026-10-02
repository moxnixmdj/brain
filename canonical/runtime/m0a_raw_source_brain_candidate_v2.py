"""Brain-owned composed candidate for the M0A raw-source diagnostic.

No oracle/evaluator import is allowed. The route composes only Brain-owned bounded
semantic mechanisms and the normalized-requirement acceptance compiler.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from canonical.runtime import bounded_predicate_argument_semantics as pas
from canonical.runtime import explicit_compound_requirement_decomposer as compound
from canonical.runtime import source_grounded_coreference as coref
from canonical.runtime import requirement_acceptance_compiler as acceptance

SCHEMA = "PROJECT_BRAIN_M0A_RAW_SOURCE_CANDIDATE_V2"

_KIND_BY_PREDICATE = {
    "aggregate": "aggregate",
    "select": "selection",
    "reconcile": "entity_reconciliation",
    "close": "hierarchy_closure",
    "reconstruct": "geometry_reconstruction",
    "compute": "numeric_formula",
    "preserve": "artifact",
    "transition": "state_transition",
    "calibrate": "measurement_calibration",
    "correct": "signal_correction",
    "choose": "method_model_selection",
}
_LEMMA = {
    "aggregated": "aggregate",
    "selected": "select",
    "reconciled": "reconcile",
    "closed": "close",
    "reconstructed": "reconstruct",
    "computed": "compute",
    "preserved": "preserve",
    "transitioned": "transition",
    "calibrated": "calibrate",
    "corrected": "correct",
    "chosen": "choose",
}
_MODAL = re.compile(r"\b(must|shall|should)\b", re.I)

def _surface_mentions(text: str):
    out = coref.extract_surface_mentions(text)
    if out.get("status") != "COMPILED":
        return [], {}
    mentions = [coref.Mention(**m) for m in out.get("mentions", [])]
    graph = coref.compile_coreference_candidates(mentions)
    by_id = {m.mention_id: m for m in mentions}
    return mentions, {"graph": graph, "by_id": by_id}

def _unique_pronoun_bindings(text: str):
    _, state = _surface_mentions(text)
    graph = state.get("graph") or {}
    by_id = state.get("by_id") or {}
    edges = graph.get("candidate_edges") or []
    grouped = {}
    for e in edges:
        grouped.setdefault(e["reference_id"], []).append(e["antecedent_id"])
    ambiguous = [rid for rid, ants in grouped.items() if len(set(ants)) != 1]
    if ambiguous:
        return None, "AMBIGUOUS"
    replacements = []
    for rid, ants in grouped.items():
        ref = by_id.get(rid)
        ant = by_id.get(ants[0])
        if ref is not None and ant is not None:
            replacements.append((ref.start, ref.end, ant.text))
    rewritten = text
    for s, e, value in sorted(replacements, reverse=True):
        rewritten = rewritten[:s] + value + rewritten[e:]
    return rewritten, "OK"

def _clauses(text: str):
    rows = []
    for raw in re.split(r"(?<=[.!?])\s+", text.strip()):
        raw = raw.strip()
        if not raw or not _MODAL.search(raw):
            continue
        dec = compound.decompose_explicit_compound(raw)
        if dec.get("status") == "DECOMPOSED":
            rows.extend(dec.get("obligations", []))
        else:
            rows.append(raw)
    return rows

def solve(public: Mapping[str, Any]) -> dict[str, Any]:
    text = public.get("raw_source")
    if not isinstance(text, str) or not text.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "RAW_SOURCE_REQUIRED"}

    rewritten, ref_status = _unique_pronoun_bindings(text)
    if ref_status == "AMBIGUOUS":
        return {"schema": SCHEMA, "status": "AMBIGUOUS", "requirements": [], "terminal_authority": False}
    if rewritten is None:
        return {"schema": SCHEMA, "status": "UNRESOLVED", "reason": "REFERENCE_GRAPH_UNAVAILABLE"}

    requirements = []
    normalized_for_acceptance = []
    for idx, clause in enumerate(_clauses(rewritten)):
        condition_override = None
        conditioned = re.match(r"^\\s*(after|unless)\\s+(.+?),\\s*(.+)$", clause, re.I)
        if conditioned:
            marker = conditioned.group(1).lower()
            condition_override = marker + " " + conditioned.group(2).strip()
            clause = conditioned.group(3).strip()
        parsed = pas.parse_clause(clause)
        if parsed.get("status") != "RESOLVED":
            return {
                "schema": SCHEMA,
                "status": "UNRESOLVED",
                "reason": parsed.get("reason") or "SEMANTIC_PARSE_UNRESOLVED",
                "requirements": requirements,
                "terminal_authority": False,
            }
        g = parsed["semantic_graph"]
        pred = _LEMMA.get(g["predicate"], g["predicate"])
        kind = _KIND_BY_PREDICATE.get(pred)
        if kind is None:
            return {
                "schema": SCHEMA,
                "status": "UNRESOLVED",
                "reason": "TRANSFORM_KIND_UNIDENTIFIED:" + pred,
                "requirements": requirements,
                "terminal_authority": False,
            }
        condition = condition_override
        if condition is None and "condition" in parsed:
            condition = parsed["condition"]["text"]
        semantic = {
            "subject": g["subject"],
            "predicate": pred,
            "object": g["object"],
            "polarity": g["polarity"].lower(),
            "transform_kind": kind,
            "transform_kinds": [kind],
        }
        if condition is not None:
            semantic["condition"] = condition
        requirements.append(semantic)
        normalized_for_acceptance.append({
            "id": f"R{idx}",
            "critical": True,
            "transform_kinds": [kind],
            "builder_dependencies": [f"raw:source:R{idx}"],
            "must_detect_failure_modes": [],
        })

    if not requirements:
        return {"schema": SCHEMA, "status": "UNRESOLVED", "reason": "NO_OPERATIVE_REQUIREMENTS"}

    acc = acceptance.compile_requirements(normalized_for_acceptance)
    if acc.get("status") != "COMPILED":
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "ACCEPTANCE_COMPILATION_FAILED", "acceptance": acc}
    return {
        "schema": SCHEMA,
        "status": "RESOLVED",
        "requirements": requirements,
        "acceptance": acc,
        "terminal_authority": False,
        "route": "BOUNDED_BRAIN_SEMANTIC_COMPOSITION_PLUS_INDEPENDENT_ACCEPTANCE",
    }

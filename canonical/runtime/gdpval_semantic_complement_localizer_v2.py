"""GDPval public-220 composed semantic complement localizer v2.

Diagnostic only. It composes already-owned, fail-closed Brain semantic components over
the complete public GDPval population. It never upgrades a proposal into terminal,
family, ABC, or policy-adequacy credit.

The point is narrower and useful: exhaust structural localization that is already
available before any fresh target-model or provider query is considered irreducible.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import re
from typing import Any, Iterable
from urllib.request import Request, urlopen

from canonical.runtime.explicit_obligation_index_v1 import build_index
from canonical.runtime.explicit_compound_requirement_decomposer import decompose_explicit_compound
from canonical.runtime.bounded_predicate_argument_semantics import parse_clause
from canonical.runtime.explicit_definition_reference_graph import compile_reference_graph
from canonical.runtime.bounded_contextual_semantics import explicit_discourse_relations
from canonical.runtime.contextual_reference_operators import propose_contextual_references
from canonical.runtime.bounded_semantic_decomposer import decompose as bounded_decompose
from canonical.runtime.source_obligation_inventory import inventory_source_obligations

SCHEMA = "PROJECT_BRAIN_GDPVAL_PUBLIC_220_COMPOSED_SEMANTIC_LOCALIZER_V2"
ROWS_API = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=openai%2Fgdpval&config=default&split=train"
)
EXPECTED_TASKS = 220

_SEGMENT_RE = re.compile(r"[^.!?\n]+(?:[.!?]+|\n|$)")
_MODAL_RE = re.compile(r"\b(?:must|shall|should|required to|is required to)\b", re.I)


def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _segments(text: str) -> Iterable[str]:
    for m in _SEGMENT_RE.finditer(text):
        s = m.group(0).strip()
        if s:
            yield s


def _fetch_json(url: str) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": "project-brain-gdpval-localizer-v2/1.0"})
    with urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))


def load_public_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for offset, length in ((0, 100), (100, 100), (200, 20)):
        payload = _fetch_json(f"{ROWS_API}&offset={offset}&length={length}")
        page = payload.get("rows")
        if not isinstance(page, list):
            raise RuntimeError(f"rows API page missing rows at offset {offset}")
        rows.extend(page)
    if len(rows) != EXPECTED_TASKS:
        raise RuntimeError(f"expected {EXPECTED_TASKS} rows, got {len(rows)}")
    indices = [int(x.get("row_idx")) for x in rows]
    if indices != list(range(EXPECTED_TASKS)):
        raise RuntimeError("GDPval row_idx population is not exactly contiguous 0..219")
    task_ids = [str((x.get("row") or {}).get("task_id") or "") for x in rows]
    if any(not x for x in task_ids) or len(set(task_ids)) != EXPECTED_TASKS:
        raise RuntimeError("GDPval task_id population missing or non-unique")
    return rows


def _compound_candidate(segment: str) -> dict[str, Any]:
    """Try the already-verified bounded compound decomposer, then reparse every part.

    This is candidate structural localization only because a decomposed reconstructed
    clause is not automatically a contiguous source-span obligation.
    """
    d = decompose_explicit_compound(segment)
    if d.get("status") != "DECOMPOSED":
        return {"status": "NO_SAFE_COMPOUND_DECOMPOSITION", "reason": d.get("error")}
    parts = list(d.get("obligations") or [])
    parsed = [parse_clause(x) for x in parts]
    if not parts or any(x.get("status") != "RESOLVED" for x in parsed):
        return {
            "status": "DECOMPOSED_BUT_REPARSE_UNRESOLVED",
            "route": d.get("route"),
            "part_count": len(parts),
        }
    return {
        "status": "BOUNDED_COMPOUND_CANDIDATE",
        "route": d.get("route"),
        "part_count": len(parts),
    }


def localize_task(row_idx: int, row: dict[str, Any]) -> dict[str, Any]:
    task_id = str(row.get("task_id") or "")
    prompt = str(row.get("prompt") or "")
    if not task_id or not prompt.strip():
        return {
            "row_idx": row_idx,
            "task_id": task_id,
            "status": "FAIL_CLOSED",
            "errors": ["TASK_ID_OR_PROMPT_MISSING"],
        }

    baseline = build_index(prompt, source_id=task_id)
    baseline_obligations = int(baseline.get("obligation_count") or 0)
    unresolved = list(baseline.get("unresolved_segments") or [])
    ignored = list(baseline.get("ignored_nonobligation_segments") or [])

    compound = Counter()
    modal_segments = 0
    for segment in _segments(prompt):
        if _MODAL_RE.search(segment):
            modal_segments += 1
            c = _compound_candidate(segment)
            compound[c["status"]] += 1

    defs = compile_reference_graph(prompt)
    definitions = len(defs.get("definitions") or []) if defs.get("status") == "COMPILED" else 0
    named_reference_sentences = len(defs.get("references") or []) if defs.get("status") == "COMPILED" else 0

    discourse = explicit_discourse_relations(prompt)

    contextual = propose_contextual_references(prompt)
    proposal = contextual.get("proposal") or {}
    contextual_claims = (
        len(proposal.get("bindings") or [])
        + len(proposal.get("relations") or [])
        + len(proposal.get("obligations") or [])
    )
    contextual_unresolved = len(contextual.get("unresolved") or [])

    bounded_consensus_segments = 0
    bounded_fail_closed_segments = 0
    for segment in _segments(prompt):
        b = bounded_decompose(segment)
        if b.get("status") == "CONSENSUS":
            bounded_consensus_segments += int(b.get("unit_count") or 0)
        else:
            bounded_fail_closed_segments += 1

    scope_obligations = inventory_source_obligations(prompt, task_id)

    rubric_raw = row.get("rubric_json")
    rubric_items = []
    if isinstance(rubric_raw, str) and rubric_raw.strip():
        try:
            parsed = json.loads(rubric_raw)
            if isinstance(parsed, list):
                rubric_items = parsed
        except Exception:
            pass

    return {
        "row_idx": row_idx,
        "task_id": task_id,
        "sector": row.get("sector"),
        "occupation": row.get("occupation"),
        "prompt_sha256": sha256(prompt.encode("utf-8")).hexdigest(),
        "status": "STRUCTURALLY_LOCALIZED_WITH_UNKNOWN_COMPLEMENT",
        "baseline_explicit_obligation_count": baseline_obligations,
        "baseline_unresolved_segment_count": len(unresolved),
        "baseline_ignored_segment_count": len(ignored),
        "modal_segment_count": modal_segments,
        "compound_candidate_counts": dict(sorted(compound.items())),
        "explicit_definition_count": definitions,
        "named_reference_sentence_count": named_reference_sentences,
        "explicit_discourse_relation_count": len(discourse),
        "contextual_reference_candidate_claim_count": contextual_claims,
        "contextual_reference_unresolved_count": contextual_unresolved,
        "bounded_lexical_consensus_unit_count": bounded_consensus_segments,
        "bounded_lexical_fail_closed_segment_count": bounded_fail_closed_segments,
        "high_scope_source_obligation_count": len(scope_obligations),
        "rubric_item_count_observed": len(rubric_items),
        "reference_file_count": len(row.get("reference_files") or []),
        "deliverable_file_count": len(row.get("deliverable_files") or []),
        "terminal_authority": False,
    }


def localize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tasks = [localize_task(int(x["row_idx"]), dict(x["row"])) for x in rows]
    if len(tasks) != EXPECTED_TASKS or any(t.get("status") == "FAIL_CLOSED" for t in tasks):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "task_count": len(tasks),
            "errors": [t for t in tasks if t.get("status") == "FAIL_CLOSED"],
            "terminal_authority": False,
        }

    agg = Counter()
    compound = Counter()
    for t in tasks:
        for k in (
            "baseline_explicit_obligation_count",
            "baseline_unresolved_segment_count",
            "baseline_ignored_segment_count",
            "modal_segment_count",
            "explicit_definition_count",
            "named_reference_sentence_count",
            "explicit_discourse_relation_count",
            "contextual_reference_candidate_claim_count",
            "contextual_reference_unresolved_count",
            "bounded_lexical_consensus_unit_count",
            "bounded_lexical_fail_closed_segment_count",
            "high_scope_source_obligation_count",
            "rubric_item_count_observed",
        ):
            agg[k] += int(t[k])
        compound.update(t["compound_candidate_counts"])

    population_manifest = sha256(
        "\n".join(f'{t["row_idx"]}:{t["task_id"]}:{t["prompt_sha256"]}' for t in tasks).encode("utf-8")
    ).hexdigest()

    return {
        "schema": SCHEMA,
        "status": "PASS__COMPLETE_PUBLIC_220_STRUCTURAL_RELOCALIZATION__ZERO_PROMOTION_CREDIT",
        "population": {
            "task_count": EXPECTED_TASKS,
            "row_indices_contiguous": True,
            "unique_task_ids": True,
            "population_manifest_sha256": population_manifest,
        },
        "aggregate": dict(sorted(agg.items())),
        "compound_candidate_counts": dict(sorted(compound.items())),
        "tasks": tasks,
        "inference": {
            "fresh_target_model_queries": 0,
            "provider_evaluation_queries": 0,
            "new_internal_model_inference": 0,
            "incremental_spend_usd": 0,
        },
        "soundness": {
            "purpose": "STRUCTURAL_COMPLEMENT_LOCALIZATION_ONLY",
            "candidate_is_credit": False,
            "unparsed_or_unresolved_means_irrelevant": False,
            "whole_task_semantic_membership_proved": False,
            "policy_adequacy_proved": False,
            "gdpval_scope_closed": False,
            "u_deletion_authority": False,
            "terminal_authority": False,
            "next_rule": (
                "USE_ONLY_CONTENT_ADDRESSED_SOURCE_ALIGNED RESULTS TO DELETE U; "
                "KEEP THE SURVIVING SEMANTIC_OR_QUALITY_COMPLEMENT OPEN; "
                "DO_NOT_WAKE A TARGET MODEL WHILE NEW INTERNAL STRUCTURAL LOCALIZATION REMAINS AVAILABLE"
            ),
        },
    }


def main() -> None:
    print(json.dumps(localize_rows(load_public_rows()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

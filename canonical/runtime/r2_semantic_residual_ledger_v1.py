"""Current-authority-derived R2 shared-cause semantic residual ledger.

The ledger does not create semantic truth, capability credit, or execution
authority. It classifies the current R2 residual surface into explicit
machine-readable causes and shared parent causes so scheduling can prefer
high-fanout repairs after the primary capability/resource score ties.

The source of truth remains CURRENT_R2_DECISION_INTELLIGENCE.json.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_R2_SHARED_CAUSE_RESIDUAL_LEDGER_V1"
CURRENT_R2_AUTHORITY = (
    Path(__file__).resolve().parents[1]
    / "governance"
    / "CURRENT_R2_DECISION_INTELLIGENCE.json"
)

# Ordered, non-authoritative taxonomy. A clause may map to multiple fine causes.
CAUSE_PATTERNS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "MENTION_UNIVERSE_COMPLETENESS",
        ("MENTION_UNIVERSE", "COREFERENCE_CASES"),
        "SEMANTIC_SCOPE_AUTHORITY",
    ),
    (
        "TERMINAL_SIGNATURE_COVERAGE",
        ("TERMINAL_SIGNATURE", "TYPED_DECISION_PROBLEM_COVER"),
        "SEMANTIC_SCOPE_AUTHORITY",
    ),
    (
        "POLICY_ADEQUACY_COVERAGE",
        ("DECISION_PROBLEM_COVER", "POLICY_ADEQUACY"),
        "SEMANTIC_SCOPE_AUTHORITY",
    ),
    (
        "DECISIVE_OBSERVABILITY",
        ("DECISIVE_OBSERVATION", "OBSERVATION_TOP", "OBSERVATION_RECEIPT"),
        "POLICY_CHANGING_OBSERVABILITY",
    ),
    (
        "WORD_SENSE_BINDING",
        ("OEWN_SENSE", "SENSE_INFERENCE", "SURVIVING_SENSE"),
        "SEMANTIC_SCOPE_AUTHORITY",
    ),
    (
        "SCOPED_DOMAIN_MAPPING_AUTHORITY",
        ("DOMAIN_CONCEPT", "SCOPED_DOMAIN_MAPPING", "DOMAIN_MAPPING"),
        "SEMANTIC_SCOPE_AUTHORITY",
    ),
    (
        "SEMANTIC_RELATION_PROOF",
        ("NONEXPLICIT_SEMANTIC_RELATION", "ENTAILMENT_DAG", "SET_RELATION_EVIDENCE"),
        "SEMANTIC_SCOPE_AUTHORITY",
    ),
    (
        "OPEN_WORLD_ONTOLOGY_AUTHORITY",
        ("OPEN_WORLD_ONTOLOGY",),
        "SEMANTIC_SCOPE_AUTHORITY",
    ),
    (
        "CROSS_DOCUMENT_EFFECT_PROOF",
        ("CROSS_DOCUMENT_CASE", "EFFECT_ID_INVENTORY", "EFFECT_FIELD"),
        "DOCUMENT_EFFECT_AUTHORITY",
    ),
    (
        "EXTERNAL_FACT_AUTHENTICATION",
        ("EXTERNAL_FACT_AUTHENTICATION", "OBSERVATION_CHANNEL"),
        "POLICY_CHANGING_OBSERVABILITY",
    ),
    (
        "CROSS_FILING_SEMANTIC_STABILITY",
        ("CROSS_FILING_ISSUER_EXTENSION", "CROSS_FILING"),
        "DOCUMENT_EFFECT_AUTHORITY",
    ),
    (
        "IDENTITY_DISCRIMINATION",
        (
            "IDENTITY_CASE",
            "IDENTITY_DISCRIMINATOR",
            "AUTHENTICATED_DISCRIMINATOR",
            "GOVERNING_REQUIREMENT_MARKER",
            "PAIR_MARKER",
        ),
        "POLICY_CHANGING_OBSERVABILITY",
    ),
)

PARENT_ORDER = (
    "SEMANTIC_SCOPE_AUTHORITY",
    "POLICY_CHANGING_OBSERVABILITY",
    "DOCUMENT_EFFECT_AUTHORITY",
)


class R2SemanticResidualLedgerError(ValueError):
    pass


def _s(value: Any) -> str:
    return " ".join(str(value or "").split())


def _boundary_clauses(boundary: str) -> list[str]:
    raw = [part.strip() for part in boundary.split("__") if part.strip()]
    if not raw:
        raise R2SemanticResidualLedgerError("REMAINING_BOUNDARY_EMPTY")
    return raw


def _matched_causes(clause: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for cause_id, patterns, parent_id in CAUSE_PATTERNS:
        if any(pattern in clause for pattern in patterns):
            out.append({"cause_id": cause_id, "parent_cause_id": parent_id})
    return out


def build_ledger(authority: Mapping[str, Any]) -> dict[str, Any]:
    status = _s(authority.get("status"))
    if "GENERAL_MECHANISM_CLOSED" not in status:
        raise R2SemanticResidualLedgerError("GENERAL_R2_MECHANISM_NOT_CLOSED")
    if authority.get("general_mechanism_missing") is not False:
        raise R2SemanticResidualLedgerError("GENERAL_MECHANISM_MISSING_NOT_FALSE")

    cell = (
        authority.get("current_cell_classifications", {})
        .get("FINANCE_SEMANTIC_ADEQUACY_TAIL", {})
    )
    if not isinstance(cell, Mapping):
        raise R2SemanticResidualLedgerError("FINANCE_RESIDUAL_CELL_INVALID")
    boundary = _s(cell.get("remaining_boundary") or authority.get("remaining_hard_frontier"))
    clauses = _boundary_clauses(boundary)

    fine_index: dict[str, dict[str, Any]] = {}
    clause_rows: list[dict[str, Any]] = []
    unclassified: list[str] = []

    for index, clause in enumerate(clauses, start=1):
        matches = _matched_causes(clause)
        if not matches:
            unclassified.append(clause)
        clause_id = f"R2_RESIDUAL_CLAUSE_{index:02d}"
        cause_ids = sorted({row["cause_id"] for row in matches})
        parent_ids = sorted({row["parent_cause_id"] for row in matches})
        clause_rows.append(
            {
                "clause_id": clause_id,
                "source_clause": clause,
                "cause_ids": cause_ids,
                "parent_cause_ids": parent_ids,
                "semantic_truth_authority": False,
                "execution_authority": False,
            }
        )
        for row in matches:
            bucket = fine_index.setdefault(
                row["cause_id"],
                {
                    "cause_id": row["cause_id"],
                    "parent_cause_id": row["parent_cause_id"],
                    "clause_ids": set(),
                },
            )
            bucket["clause_ids"].add(clause_id)

    fine_causes = []
    for cause_id in sorted(fine_index):
        row = fine_index[cause_id]
        clause_ids = sorted(row["clause_ids"])
        fine_causes.append(
            {
                "cause_id": cause_id,
                "parent_cause_id": row["parent_cause_id"],
                "clause_ids": clause_ids,
                "fanout_clause_count": len(clause_ids),
                "wake_gated": True,
            }
        )

    parent_index: dict[str, set[str]] = {parent: set() for parent in PARENT_ORDER}
    child_index: dict[str, list[str]] = {parent: [] for parent in PARENT_ORDER}
    for row in fine_causes:
        parent = row["parent_cause_id"]
        parent_index.setdefault(parent, set()).update(row["clause_ids"])
        child_index.setdefault(parent, []).append(row["cause_id"])

    shared_causes = []
    for parent in PARENT_ORDER:
        clause_ids = sorted(parent_index.get(parent, set()))
        shared_causes.append(
            {
                "cause_id": parent,
                "child_cause_ids": sorted(child_index.get(parent, [])),
                "clause_ids": clause_ids,
                "fanout_clause_count": len(clause_ids),
                "wake_gated": True,
            }
        )

    ranked_shared = sorted(
        shared_causes,
        key=lambda row: (-row["fanout_clause_count"], row["cause_id"]),
    )

    wake_on = cell.get("wake_on", [])
    if not isinstance(wake_on, list) or not all(isinstance(x, str) for x in wake_on):
        raise R2SemanticResidualLedgerError("WAKE_ON_INVALID")

    classification_complete = not unclassified
    return {
        "schema": SCHEMA,
        "status": (
            "CURRENT_AUTHORITY_DERIVED__CLASSIFIED"
            if classification_complete
            else "CURRENT_AUTHORITY_DERIVED__UNCLASSIFIED_RESIDUAL_PRESENT"
        ),
        "source_authority_schema": _s(authority.get("schema")),
        "source_authority_status": status,
        "general_mechanism_closed": True,
        "residual_cell_id": "FINANCE_SEMANTIC_ADEQUACY_TAIL",
        "residual_cell_state": _s(cell.get("state")),
        "classification_complete": classification_complete,
        "unclassified_clauses": unclassified,
        "clauses": clause_rows,
        "fine_causes": fine_causes,
        "shared_causes": shared_causes,
        "highest_fanout_shared_cause": (
            ranked_shared[0]["cause_id"] if ranked_shared else None
        ),
        "highest_fanout_clause_count": (
            ranked_shared[0]["fanout_clause_count"] if ranked_shared else 0
        ),
        "wake_conditions": sorted(set(_s(x) for x in wake_on if _s(x))),
        "scheduler_semantics": {
            "global_open_world_residual_is_primary_by_existence": False,
            "wake_requires_task_local_counterexample_or_verified_capability_defect": True,
            "fanout_is_tie_break_after_primary_capability_resource_score": True,
            "unknown_or_unclassified_residual_fails_closed": True,
        },
        "required_action": _s(cell.get("required_action")),
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "credit_delta": 0,
    }


def load_current_ledger() -> dict[str, Any]:
    try:
        authority = json.loads(CURRENT_R2_AUTHORITY.read_text(encoding="utf-8"))
    except Exception as exc:
        raise R2SemanticResidualLedgerError("CURRENT_R2_AUTHORITY_UNAVAILABLE") from exc
    if not isinstance(authority, Mapping):
        raise R2SemanticResidualLedgerError("CURRENT_R2_AUTHORITY_INVALID")
    return build_ledger(authority)


def cause_fanout_index(ledger: Mapping[str, Any]) -> dict[str, int]:
    if ledger.get("classification_complete") is not True:
        raise R2SemanticResidualLedgerError("RESIDUAL_LEDGER_CLASSIFICATION_INCOMPLETE")
    out: dict[str, int] = {}
    for key in ("fine_causes", "shared_causes"):
        rows = ledger.get(key, [])
        if not isinstance(rows, list):
            raise R2SemanticResidualLedgerError(key.upper() + "_INVALID")
        for row in rows:
            if not isinstance(row, Mapping):
                raise R2SemanticResidualLedgerError(key.upper() + "_ROW_INVALID")
            cause_id = _s(row.get("cause_id"))
            count = row.get("fanout_clause_count")
            if (
                not cause_id
                or isinstance(count, bool)
                or not isinstance(count, int)
                or count < 0
            ):
                raise R2SemanticResidualLedgerError("CAUSE_FANOUT_INVALID")
            if cause_id in out and out[cause_id] != count:
                raise R2SemanticResidualLedgerError("CAUSE_FANOUT_CONFLICT:" + cause_id)
            out[cause_id] = count
    return out

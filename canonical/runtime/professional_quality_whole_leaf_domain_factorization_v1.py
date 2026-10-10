"""Factor Professional whole-leaf claim-scope work without granting scope credit.

The 24 semantic/execution leaves are organized into 12 root pairs. A pair may
reuse one domain definition only after independent proof that the semantic and
execution admissible domains are exactly equivalent. Common subject/behavior
identity is coordination structure, not domain-equivalence authority.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_FACTORIZATION_V1"


class ProfessionalDomainFactorizationError(ValueError):
    pass


def _s(value: Any) -> str:
    return " ".join(str(value or "").split())


def compile_factorization(
    manifest: Mapping[str, Any],
    complement_worklist: Mapping[str, Any],
) -> dict[str, Any]:
    roots = manifest.get("roots")
    rows = complement_worklist.get("rows")
    if not isinstance(roots, list) or len(roots) != 12:
        raise ProfessionalDomainFactorizationError("ROOT_UNIVERSE_NOT_12")
    if not isinstance(rows, list) or len(rows) != 24:
        raise ProfessionalDomainFactorizationError("COMPLEMENT_UNIVERSE_NOT_24")

    by_leaf: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ProfessionalDomainFactorizationError("COMPLEMENT_ROW_INVALID")
        leaf_id = _s(row.get("leaf_id"))
        if not leaf_id or leaf_id in by_leaf:
            raise ProfessionalDomainFactorizationError("COMPLEMENT_LEAF_ID_INVALID")
        by_leaf[leaf_id] = row

    out_roots: list[dict[str, Any]] = []
    expected_leaf_ids: set[str] = set()

    for root in roots:
        if not isinstance(root, Mapping):
            raise ProfessionalDomainFactorizationError("ROOT_ROW_INVALID")
        root_id = _s(root.get("root_id"))
        if not root_id:
            raise ProfessionalDomainFactorizationError("ROOT_ID_REQUIRED")
        semantic = root.get("semantic_leaf")
        execution = root.get("execution_leaf")
        if not isinstance(semantic, Mapping) or not isinstance(execution, Mapping):
            raise ProfessionalDomainFactorizationError("ROOT_LEAF_PAIR_REQUIRED:" + root_id)

        semantic_id = _s(semantic.get("id"))
        execution_id = _s(execution.get("id"))
        if not semantic_id or not execution_id or semantic_id == execution_id:
            raise ProfessionalDomainFactorizationError("ROOT_LEAF_PAIR_INVALID:" + root_id)
        expected_leaf_ids.update((semantic_id, execution_id))

        if semantic_id not in by_leaf or execution_id not in by_leaf:
            raise ProfessionalDomainFactorizationError("COMPLEMENT_PAIR_MISSING:" + root_id)

        semantic_row = by_leaf[semantic_id]
        execution_row = by_leaf[execution_id]
        if _s(semantic_row.get("root_id")) != root_id or _s(execution_row.get("root_id")) != root_id:
            raise ProfessionalDomainFactorizationError("COMPLEMENT_ROOT_MISMATCH:" + root_id)

        out_roots.append(
            {
                "root_id": root_id,
                "root_contract": root.get("contract"),
                "semantic_leaf": {
                    "leaf_id": semantic_id,
                    "obligation": semantic.get("obligation"),
                    "acceptance": semantic.get("acceptance"),
                    "uncovered_partition_id": semantic_row.get("uncovered_partition_id"),
                    "bounded_witness_scope_ids": semantic_row.get("bounded_witness_scope_ids") or [],
                },
                "execution_leaf": {
                    "leaf_id": execution_id,
                    "obligation": execution.get("obligation"),
                    "acceptance": execution.get("acceptance"),
                    "uncovered_partition_id": execution_row.get("uncovered_partition_id"),
                    "bounded_witness_scope_ids": execution_row.get("bounded_witness_scope_ids") or [],
                },
                "domain_reuse_candidate": True,
                "semantic_execution_domain_equivalence_proved": False,
                "domain_reuse_authority": False,
                "next_proof": (
                    "FREEZE_EXACT_SEMANTIC_AND_EXECUTION_DOMAIN_DEFINITIONS__"
                    "INDEPENDENTLY_PROVE_EQUAL_OR_KEEP_SEPARATE"
                ),
            }
        )

    if set(by_leaf) != expected_leaf_ids:
        raise ProfessionalDomainFactorizationError("MANIFEST_COMPLEMENT_LEAF_UNIVERSE_MISMATCH")

    return {
        "schema": SCHEMA,
        "status": (
            "MECHANICALLY_FACTORIZED__12_ROOT_PAIRS__24_LEAVES__"
            "ZERO_DOMAIN_EQUIVALENCE_OR_SCOPE_CREDIT"
        ),
        "root_count": len(out_roots),
        "leaf_count": len(expected_leaf_ids),
        "pair_domain_equivalence_proved_count": 0,
        "pair_domain_equivalence_required_count": len(out_roots),
        "shared_claim_invariants": {
            "behavior_id": "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
            "subject_kind": "DECLARED_SYSTEM",
            "coordination_only": True,
            "domain_equivalence_authority": False,
        },
        "roots": out_roots,
        "rules": [
            "COMMON_SUBJECT_OR_BEHAVIOR_IDENTITY_DOES_NOT_PROVE_COMMON_ADMISSIBLE_DOMAIN",
            "REUSE_ONE_ROOT_DOMAIN_ONLY_AFTER_INDEPENDENT_SEMANTIC_EXECUTION_DOMAIN_EQUIVALENCE",
            "IF_EQUIVALENCE_FAILS_KEEP_TWO_CLAIM_SCOPES_FOR_THE_ROOT",
            "SCOPE_COMPLETENESS_AND_PROPERTY_TRUTH_REMAIN_SEPARATE",
        ],
        "scope_credit_delta": 0,
        "property_truth_credit_delta": 0,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }

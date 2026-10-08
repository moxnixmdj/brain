"""Exact finite observational obstruction reducer.

Given a finite reached decision-region set H, a declared complete-on-H discriminator
library Q, and authenticated-positive policy adequacy regions P, compute the final
observational equivalence classes induced by all Q signatures and prove either:

1. every final class is covered by at least one declared policy region; or
2. return one exact unsplittable class with empty declared common-policy cover.

This module proves only the finite structural proposition over its declared H/P/Q.
It does not self-certify that Q is globally complete, that policy adequacy receipts
are semantically true, or that H covers all real target-supported escape states.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from canonical.runtime.finite_identifiability import Experiment, equivalence_classes

SCHEMA = "PROJECT_BRAIN_FINITE_OBSERVATIONAL_OBSTRUCTION_REDUCER_V1"


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "declared_q_complete_on_h": False,
        "all_final_observational_classes_covered": False,
        "global_q_scope_complete": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _ids(values: Sequence[str], *, label: str) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or not values:
        raise ValueError(label + "_INVALID_OR_EMPTY")
    out = tuple(str(v) for v in values)
    if any(not v for v in out) or len(set(out)) != len(out):
        raise ValueError(label + "_INVALID_OR_DUPLICATE")
    return out


def reduce_obstruction(payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(payload, Mapping):
            return _fail("PAYLOAD_MAPPING_REQUIRED")

        regions = _ids(payload.get("region_ids"), label="REGION_IDS")
        region_set = set(regions)

        q_rows = payload.get("discriminators")
        if not isinstance(q_rows, Sequence) or isinstance(q_rows, (str, bytes)):
            return _fail("DISCRIMINATORS_INVALID")
        experiments: list[Experiment] = []
        q_ids: set[str] = set()
        for i, row in enumerate(q_rows):
            if not isinstance(row, Mapping):
                return _fail("DISCRIMINATOR_NOT_OBJECT", index=i)
            qid = row.get("discriminator_id")
            outcomes = row.get("outcomes")
            if not isinstance(qid, str) or not qid or qid in q_ids:
                return _fail("DISCRIMINATOR_ID_INVALID_OR_DUPLICATE", index=i)
            if not isinstance(outcomes, Mapping) or set(outcomes) != region_set:
                return _fail(
                    "DISCRIMINATOR_OUTCOME_DOMAIN_INCOMPLETE",
                    discriminator_id=qid,
                    missing=sorted(region_set - set(outcomes) if isinstance(outcomes, Mapping) else region_set),
                    extra=sorted(set(outcomes) - region_set if isinstance(outcomes, Mapping) else set()),
                )
            if any(not isinstance(v, str) or not v for v in outcomes.values()):
                return _fail("DISCRIMINATOR_OUTCOME_INVALID", discriminator_id=qid)
            q_ids.add(qid)
            experiments.append(Experiment(qid, dict(outcomes), 1.0))

        p_rows = payload.get("policies")
        if not isinstance(p_rows, Sequence) or isinstance(p_rows, (str, bytes)) or not p_rows:
            return _fail("POLICIES_INVALID_OR_EMPTY")
        policies: dict[str, dict[str, Any]] = {}
        for i, row in enumerate(p_rows):
            if not isinstance(row, Mapping):
                return _fail("POLICY_NOT_OBJECT", index=i)
            pid = row.get("policy_id")
            covered = row.get("adequate_region_ids")
            receipt = row.get("adequacy_receipt")
            if not isinstance(pid, str) or not pid or pid in policies:
                return _fail("POLICY_ID_INVALID_OR_DUPLICATE", index=i)
            if not isinstance(covered, Sequence) or isinstance(covered, (str, bytes)):
                return _fail("POLICY_REGION_SET_INVALID", policy_id=pid)
            covered_set = set(covered)
            if any(not isinstance(x, str) or not x for x in covered) or not covered_set <= region_set:
                return _fail("POLICY_REGION_SET_OUT_OF_DOMAIN", policy_id=pid)
            if not isinstance(receipt, Mapping):
                return _fail("POLICY_ADEQUACY_RECEIPT_REQUIRED", policy_id=pid)
            if (
                not isinstance(receipt.get("path"), str)
                or not receipt.get("path")
                or not isinstance(receipt.get("git_blob_sha"), str)
                or len(receipt.get("git_blob_sha")) != 40
                or receipt.get("independent_verified") is not True
                or receipt.get("exact_byte_bound") is not True
                or receipt.get("conclusion") != "success"
                or receipt.get("policy_adequacy_region_sound") is not True
            ):
                return _fail("POLICY_ADEQUACY_RECEIPT_INVALID", policy_id=pid)
            policies[pid] = {
                "regions": covered_set,
                "receipt_path": receipt["path"],
                "receipt_blob": receipt["git_blob_sha"],
            }

        classes = equivalence_classes(regions, experiments)
        detailed = []
        bad = []
        for members in classes:
            member_set = set(members)
            common = sorted(
                pid for pid, row in policies.items()
                if member_set <= row["regions"]
            )
            signature = []
            representative = members[0]
            for e in sorted(experiments, key=lambda x: x.experiment_id):
                signature.append({
                    "discriminator_id": e.experiment_id,
                    "outcome": e.outcomes[representative],
                })
            item = {
                "region_ids": members,
                "full_q_signature": signature,
                "common_adequate_policy_ids": common,
                "covered": bool(common),
            }
            detailed.append(item)
            if not common:
                bad.append(item)

        if bad:
            witness = sorted(bad, key=lambda x: (len(x["region_ids"]), x["region_ids"]))[0]
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "UNSPLITTABLE_POLICY_CONFLICT_CLASS_FOUND",
                "reason": "FINAL_OBSERVATIONAL_CLASS_HAS_NO_COMMON_DECLARED_ADEQUATE_POLICY",
                "region_count": len(regions),
                "discriminator_count": len(experiments),
                "policy_count": len(policies),
                "final_class_count": len(classes),
                "uncovered_final_class_count": len(bad),
                "counterexample_class": witness,
                "declared_q_complete_on_h": True,
                "all_final_observational_classes_covered": False,
                "global_q_scope_complete": False,
                "u_empty_authorized": False,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
                "boundary": (
                    "EXACT_STRUCTURAL_COUNTEREXAMPLE_OVER_DECLARED_FINITE_H_P_Q_ONLY;"
                    "NO_CLAIM_Q_IS_GLOBALLY_SCOPE_COMPLETE_OR_POLICY_RECEIPT_SEMANTICS_ARE_TRUE"
                ),
            }

        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__ALL_DECLARED_FINAL_OBSERVATIONAL_CLASSES_HAVE_COMMON_POLICY",
            "region_count": len(regions),
            "discriminator_count": len(experiments),
            "policy_count": len(policies),
            "final_class_count": len(classes),
            "classes": detailed,
            "declared_q_complete_on_h": True,
            "all_final_observational_classes_covered": True,
            "global_q_scope_complete": False,
            "u_empty_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "EXACT_ONLY_OVER_DECLARED_FINITE_H_P_Q;"
                "GLOBAL_SCOPE_COMPLETENESS_AND_SEMANTIC_RECEIPT_TRUTH_REMAIN_EXTERNAL_PREMISES"
            ),
        }
    except Exception as exc:
        return _fail("INVALID_INPUT", exception_type=type(exc).__name__, detail_text=str(exc)[:200])

"""Exact finite observational obstruction reducer.

Given a finite reached decision-region set H, a declared complete-on-H discriminator
library Q, and DECLARED policy adequacy regions P with byte-bound certificate
references, compute the final observational equivalence classes induced by all Q
signatures and prove either:

1. every final class is structurally covered by at least one declared policy region; or
2. return one exact unsplittable class with empty declared common-policy cover.

This kernel never treats a certificate-shaped flag as proof. It authenticates the
referenced certificate bytes only. The semantic truth of each adequacy certificate,
global Q completeness, and coverage of real target-supported escape states remain
separate premises.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes
from canonical.runtime.finite_identifiability import Experiment, equivalence_classes

SCHEMA = "PROJECT_BRAIN_FINITE_OBSERVATIONAL_OBSTRUCTION_REDUCER_V2"


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "declared_q_complete_on_h": False,
        "all_final_observational_classes_structurally_covered": False,
        "policy_certificate_bytes_bound": False,
        "policy_adequacy_semantics_verified": False,
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


def reduce_obstruction(
    payload: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    try:
        if not isinstance(payload, Mapping):
            return _fail("PAYLOAD_MAPPING_REQUIRED")
        root = Path(repo_root).resolve(strict=True)

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
            if set(row) != {"policy_id", "adequate_region_ids", "adequacy_certificate_ref"}:
                return _fail("POLICY_FIELDS_INVALID", index=i)
            pid = row.get("policy_id")
            covered = row.get("adequate_region_ids")
            ref = row.get("adequacy_certificate_ref")
            if not isinstance(pid, str) or not pid or pid in policies:
                return _fail("POLICY_ID_INVALID_OR_DUPLICATE", index=i)
            if not isinstance(covered, Sequence) or isinstance(covered, (str, bytes)):
                return _fail("POLICY_REGION_SET_INVALID", policy_id=pid)
            covered_set = set(covered)
            if any(not isinstance(x, str) or not x for x in covered) or not covered_set <= region_set:
                return _fail("POLICY_REGION_SET_OUT_OF_DOMAIN", policy_id=pid)
            if not isinstance(ref, Mapping):
                return _fail("POLICY_ADEQUACY_CERTIFICATE_REF_REQUIRED", policy_id=pid)
            try:
                bound = resolve_receipt_bytes(ref, repo_root=root)
            except Exception as exc:
                return _fail(
                    "POLICY_ADEQUACY_CERTIFICATE_BINDING_INVALID",
                    policy_id=pid,
                    exception_type=type(exc).__name__,
                    detail_text=str(exc)[:160],
                )
            policies[pid] = {
                "regions": covered_set,
                "certificate_path": bound["path"],
                "certificate_git_blob_sha": bound["git_blob_sha"],
                "certificate_byte_sha256": bound["byte_sha256"],
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
                "common_declared_policy_ids": common,
                "structurally_covered": bool(common),
            }
            detailed.append(item)
            if not common:
                bad.append(item)

        base = {
            "schema": SCHEMA,
            "region_count": len(regions),
            "discriminator_count": len(experiments),
            "policy_count": len(policies),
            "final_class_count": len(classes),
            "declared_q_complete_on_h": True,
            "policy_certificate_bytes_bound": True,
            "policy_adequacy_semantics_verified": False,
            "global_q_scope_complete": False,
            "u_empty_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

        if bad:
            witness = sorted(bad, key=lambda x: (len(x["region_ids"]), x["region_ids"]))[0]
            return {
                **base,
                "pass": False,
                "status": "UNSPLITTABLE_DECLARED_POLICY_CONFLICT_CLASS_FOUND",
                "reason": "FINAL_OBSERVATIONAL_CLASS_HAS_NO_COMMON_DECLARED_POLICY_REGION",
                "uncovered_final_class_count": len(bad),
                "counterexample_class": witness,
                "all_final_observational_classes_structurally_covered": False,
                "boundary": (
                    "EXACT_STRUCTURAL_COUNTEREXAMPLE_OVER_DECLARED_FINITE_H_P_Q_ONLY;"
                    "ADEQUACY_CERTIFICATE_BYTES_ARE_BOUND_BUT_SEMANTIC_TRUTH_IS_NOT_SELF_CERTIFIED"
                ),
            }

        return {
            **base,
            "pass": True,
            "status": "PASS__ALL_DECLARED_FINAL_OBSERVATIONAL_CLASSES_STRUCTURALLY_COVERED",
            "classes": detailed,
            "all_final_observational_classes_structurally_covered": True,
            "boundary": (
                "EXACT_ONLY_OVER_DECLARED_FINITE_H_P_Q;"
                "BYTE_BOUND_CERTIFICATE_REFERENCES_DO_NOT_SELF_PROVE_ADEQUACY_SEMANTICS;"
                "GLOBAL_SCOPE_COMPLETENESS_REMAINS_EXTERNAL"
            ),
        }
    except Exception as exc:
        return _fail("INVALID_INPUT", exception_type=type(exc).__name__, detail_text=str(exc)[:200])

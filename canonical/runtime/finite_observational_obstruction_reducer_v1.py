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

from collections import deque
from itertools import combinations
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



MAX_CORE_SEARCH_STATES = 8192
MAX_EXACT_Q_DISCRIMINATORS = 12


def _smallest_conflict_core(
    members: Sequence[str], policies: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    """Find minimum-cardinality H subset with no shared declared policy.

    BFS explores intersections of policy-support sets, retaining the shortest
    route to each distinct intersection. On a state-budget hit, deletion
    reduction still gives a verified 1-minimal core, never a fake exact minimum.
    No content/adequacy receipt is authenticated by this structural algorithm.
    """
    policy_ids = sorted(policies)
    full = (1 << len(policy_ids)) - 1
    region_masks = {
        r: sum(1 << i for i, pid in enumerate(policy_ids)
               if r in policies[pid]["regions"])
        for r in sorted(members)
    }
    frontier = deque([(full, ())])
    seen = {full}
    exhausted = False
    while frontier and not exhausted:
        mask, chosen = frontier.popleft()
        for region in sorted(members):
            if region in chosen:
                continue
            next_mask = mask & region_masks[region]
            if next_mask == mask:
                continue
            path = chosen + (region,)
            if next_mask == 0:
                return {
                    "region_ids": list(path),
                    "minimum_cardinality_proved": True,
                    "irreducible_proved": True,
                    "checked_intersection_states": len(seen),
                }
            if next_mask not in seen:
                if len(seen) >= MAX_CORE_SEARCH_STATES:
                    exhausted = True
                    break
                seen.add(next_mask)
                frontier.append((next_mask, path))

    # Monotonic intersection means each remaining region is necessary after
    # one deletion pass. This is 1-minimal, not necessarily globally minimum.
    core = sorted(members)
    for region in list(core):
        other = [r for r in core if r != region]
        intersection = full
        for r in other:
            intersection &= region_masks[r]
        if intersection == 0:
            core.remove(region)
    remaining = full
    for region in core:
        remaining &= region_masks[region]
    if remaining != 0:
        raise ValueError("CONFLICT_CORE_INVARIANT_FAILED")
    for region in core:
        without = full
        for other in core:
            if other != region:
                without &= region_masks[other]
        if without == 0:
            raise ValueError("CONFLICT_CORE_NOT_IRREDUCIBLE")
    return {
        "region_ids": core,
        "minimum_cardinality_proved": False,
        "irreducible_proved": True,
        "checked_intersection_states": len(seen),
        "search_budget_exceeded": exhausted,
    }



def _minimal_observation_plan(
    regions: Sequence[str],
    experiments: Sequence[Experiment],
    policies: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Exact minimum-count subset of declared Q sufficient for common policies.

    Enumerates subsets in cardinality order, including the no-observation
    common-policy case. Does not claim receipt semantics or global Q completeness.
    """
    qs = sorted(experiments, key=lambda x: x.experiment_id)
    if len(qs) > MAX_EXACT_Q_DISCRIMINATORS:
        return {
            "status": "UNPROVED_TOO_MANY_DECLARED_DISCRIMINATORS",
            "minimum_proved": False,
            "searched_subsets": 0,
            "max_exact_q_count": MAX_EXACT_Q_DISCRIMINATORS,
        }
    tested = 0
    for count in range(len(qs) + 1):
        for subset in combinations(qs, count):
            tested += 1
            classes = equivalence_classes(regions, subset)
            chosen_policies = []
            for members in classes:
                common = sorted(
                    pid for pid, p in policies.items()
                    if set(members) <= p["regions"]
                )
                if not common:
                    break
                chosen_policies.append({
                    "region_ids": members,
                    "common_declared_policy_id": common[0],
                })
            else:
                return {
                    "status": "PASS__EXACT_MINIMUM_Q_SUBSET_OVER_DECLARED_H_P_Q",
                    "minimum_proved": True,
                    "selected_discriminator_ids": [e.experiment_id for e in subset],
                    "observation_count": count,
                    "full_declared_q_count": len(qs),
                    "avoided_declared_observations": len(qs) - count,
                    "policy_by_observation_class": chosen_policies,
                    "searched_subsets": tested,
                    "bound": "DECLARED_FINITE_H_P_Q_ONLY__ADEQUACY_SEMANTICS_AND_Q_COMPLETENESS_UNPROVED",
                }
    raise ValueError("OBSERVATION_PLANNER_INVARIANT_FAILED")


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
            if not common:
                core = _smallest_conflict_core(members, policies)
                without_policy = sorted(
                    r for r in members
                    if not any(r in row["regions"] for row in policies.values())
                )
                item["smallest_verified_conflict_core"] = core
                item["regions_with_no_declared_adequate_policy"] = without_policy
                item["minimum_missing_decision_relevant_primitive"] = (
                    "PROVE_OR_BUILD_ADEQUATE_POLICY"
                    if without_policy
                    else "ADD_TRUTHFUL_DISCRIMINATOR_OR_PROVE_COMMON_ADEQUATE_POLICY"
                )
                bad.append(item)
            detailed.append(item)

        base = {
            "schema": SCHEMA,
            "region_count": len(regions),
            "discriminator_count": len(experiments),
            "policy_count": len(policies),
            "final_class_count": len(classes),
            "declared_q_complete_on_h": False,
                "declared_q_outcome_domain_total_on_h": True,
                "q_information_library_complete_proved": False,
            "policy_certificate_bytes_bound": True,
            "policy_adequacy_semantics_verified": False,
            "global_q_scope_complete": False,
            "u_empty_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

        if bad:
            witness = min(
                bad,
                key=lambda x: (
                    len(x["smallest_verified_conflict_core"]["region_ids"]),
                    len(x["region_ids"]),
                    x["region_ids"],
                ),
            )
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
            "minimum_declared_observation_plan": _minimal_observation_plan(regions, experiments, policies),
            "all_final_observational_classes_structurally_covered": True,
            "boundary": (
                "EXACT_ONLY_OVER_DECLARED_FINITE_H_P_Q;"
                "BYTE_BOUND_CERTIFICATE_REFERENCES_DO_NOT_SELF_PROVE_ADEQUACY_SEMANTICS;"
                "GLOBAL_SCOPE_COMPLETENESS_REMAINS_EXTERNAL"
            ),
        }
    except Exception as exc:
        return _fail("INVALID_INPUT", exception_type=type(exc).__name__, detail_text=str(exc)[:200])

"""Dynamic minimum-action compiler for the terminal Opus-5.5 objective.

Unlike snapshot policies, this compiler derives the live residual from the
content of the canonical registry, acceptance ledger, root partition, and
terminal authority every time it runs. A closure or revocation therefore
changes the action frontier mechanically instead of leaving stale 12/26 or
13/25 policy state behind.

This is scheduling only. It grants no acceptance, family, capability,
ownership, execution, promotion, or fresh-reality authority.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V6"

REGISTRY = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
LEDGER = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
ROOT_STATE = "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"
AUTHORITY = "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"

# Root2 targets for which current critical-path work is authenticated/self-service
# access, exact environment binding, zero-cost carrier/quota facts, or public
# route completion. This list is intentionally small and explicit.
ACCESS_COMPUTE = frozenset({
    "CODING_TB4_GE_66_4",
    "HLE_TOOLS_GE_67_7",
    "TB_SCIENCE_GE_58_7",
    "CHARTOGRAPHY_TOOLS_GE_89",
    "OSWORLD_2_1_PARTIAL_GE_81_8",
    "FINANCE_AGENT_V2_GE_58_59",
})

# LiveBench remains in the proof-collapse lane even when Root2-only because its
# active scorer/proof surface is public and can change by authoritative route
# reconciliation (e.g. legacy surface -> IFBench58). The compiler deliberately
# does not encode a specific scorer surface.
PUBLIC_FORMAL_ROOT2 = frozenset({
    "LIVEBENCH_IF_GE_65_7",
})


def _load(root: Path, rel: str) -> dict[str, Any]:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def _sha256_obj(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _ids(registry: Mapping[str, Any]) -> set[str]:
    out: set[str] = set()
    for row in registry.get("predicates", []):
        pid = row.get("predicate_id") or row.get("id")
        if not isinstance(pid, str) or not pid:
            raise ValueError("INVALID_REGISTRY_PREDICATE_ID")
        if pid in out:
            raise ValueError("DUPLICATE_REGISTRY_PREDICATE:" + pid)
        out.add(pid)
    return out


def _proved(ledger: Mapping[str, Any]) -> set[str]:
    out: set[str] = set()
    for row in ledger.get("claims", []):
        pid = row.get("predicate_id")
        if row.get("state") == "PROVED":
            if not isinstance(pid, str) or not pid:
                raise ValueError("INVALID_PROVED_PREDICATE_ID")
            out.add(pid)
    return out


def _set_from(partition: Mapping[str, Any], key: str) -> set[str]:
    rows = partition.get(key, [])
    if not isinstance(rows, list) or any(not isinstance(x, str) for x in rows):
        raise ValueError("INVALID_ROOT_PARTITION_LIST:" + key)
    return set(rows)


def compile_from_objects(
    registry: Mapping[str, Any],
    ledger: Mapping[str, Any],
    root_state: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    registry = copy.deepcopy(dict(registry))
    ledger = copy.deepcopy(dict(ledger))
    root_state = copy.deepcopy(dict(root_state))
    authority = copy.deepcopy(dict(authority))

    all_ids = _ids(registry)
    proved = _proved(ledger)
    if not proved <= all_ids:
        raise ValueError("PROVED_PREDICATE_OUTSIDE_REGISTRY")
    unresolved = all_ids - proved

    partition = root_state.get("current_residual_root_partition")
    if not isinstance(partition, Mapping):
        raise ValueError("MISSING_CURRENT_ROOT_PARTITION")

    r1 = _set_from(partition, "root1_only")
    r2 = _set_from(partition, "root2_only")
    r3 = _set_from(partition, "root3_only")
    mixed = _set_from(partition, "root2_and_root3")

    buckets = [r1, r2, r3, mixed]
    for i, left in enumerate(buckets):
        for right in buckets[i + 1:]:
            if left & right:
                raise ValueError("ROOT_PARTITION_OVERLAP:" + ",".join(sorted(left & right)))

    partition_union = set().union(*buckets)
    if partition_union != unresolved:
        missing = sorted(unresolved - partition_union)
        extra = sorted(partition_union - unresolved)
        raise ValueError(
            "ROOT_PARTITION_NOT_EXACT_RESIDUAL:"
            + "MISSING=" + ",".join(missing)
            + ":EXTRA=" + ",".join(extra)
        )

    declared_unresolved = partition.get("unresolved_total")
    if declared_unresolved != len(unresolved):
        raise ValueError("ROOT_UNRESOLVED_COUNT_DRIFT")

    overlay = authority.get("current_root_partition_override")
    if not isinstance(overlay, Mapping):
        raise ValueError("MISSING_TERMINAL_AUTHORITY_ROOT_OVERRIDE")
    if overlay.get("proved_atomic") != len(proved):
        raise ValueError("AUTHORITY_PROVED_COUNT_DRIFT")
    if overlay.get("unresolved_atomic") != len(unresolved):
        raise ValueError("AUTHORITY_UNRESOLVED_COUNT_DRIFT")
    if overlay.get("root1_positive_gap_count") != len(r1):
        raise ValueError("AUTHORITY_ROOT1_COUNT_DRIFT")
    if overlay.get("root2_only") != len(r2):
        raise ValueError("AUTHORITY_ROOT2_COUNT_DRIFT")
    if overlay.get("root3_only") != len(r3):
        raise ValueError("AUTHORITY_ROOT3_COUNT_DRIFT")
    if overlay.get("root2_and_root3") != len(mixed):
        raise ValueError("AUTHORITY_MIXED_COUNT_DRIFT")

    # Any constructive Root1 gap is its own acquisition/repair front. Current
    # truth is zero, but the compiler remains correct if one reopens later.
    acquisition = set(r1)

    # Root3 and mixed claims prefer formal/exhaustive scope closure first.
    proof = set(r3) | set(mixed)

    # Selected public Root2 surfaces are theorem/score-construction races.
    proof |= r2 & PUBLIC_FORMAL_ROOT2

    access = r2 & ACCESS_COMPUTE

    # Remaining Root2-only claims are comparator/private-bar/proprietary-route
    # escape work: exact owner receipt, exact/superset public protocol, relative
    # bridge, or scope-complete stronger proof. This default is fail-safe because
    # it never authorizes reality by itself.
    proprietary = r2 - access - PUBLIC_FORMAL_ROOT2

    fronts = {
        "ROOT1_ACQUISITION_REPAIR": acquisition,
        "ZERO_REALITY_PROOF_COLLAPSE": proof,
        "AUTHENTICATED_ACCESS_AND_COMPUTE": access,
        "PROPRIETARY_BAR_ESCAPE": proprietary,
    }

    names = list(fronts)
    for i, name in enumerate(names):
        for other in names[i + 1:]:
            if fronts[name] & fronts[other]:
                raise ValueError(
                    "ACTION_FRONT_OVERLAP:"
                    + name + ":"
                    + other + ":"
                    + ",".join(sorted(fronts[name] & fronts[other]))
                )
    if set().union(*fronts.values()) != unresolved:
        raise ValueError("ACTION_FRONTS_NOT_EXACT_RESIDUAL_COVER")

    livebench_open = "LIVEBENCH_IF_GE_65_7" in unresolved
    unknown_open = "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT" in unresolved

    policy = {
        "schema": SCHEMA,
        "status": "ACTIVE_DYNAMIC_COMPILATION__SCHEDULING_ONLY__ZERO_CREDIT",
        "objective": (
            "MINIMIZE_TERMINAL_WALL_CLOCK_SUBJECT_TO_CORRECTNESS_FIRST_"
            "ZERO_INCREMENTAL_SPEND_DONOR_INDEPENDENCE_AND_FAIL_CLOSED_PROMOTION"
        ),
        "live_state": {
            "total_atomic": len(all_ids),
            "proved_atomic": len(proved),
            "unresolved_atomic": len(unresolved),
            "root1_only": len(r1),
            "root2_only": len(r2),
            "root3_only": len(r3),
            "root2_and_root3": len(mixed),
            "terminal": len(unresolved) == 0,
        },
        "state_digest_sha256": _sha256_obj({
            "registry_ids": sorted(all_ids),
            "proved_ids": sorted(proved),
            "root1": sorted(r1),
            "root2": sorted(r2),
            "root3": sorted(r3),
            "mixed": sorted(mixed),
            "authority_override": dict(overlay),
        }),
        "optimization": {
            "lexicographic": [
                "MINIMIZE_TERMINAL_WALL_CLOCK",
                "MINIMIZE_IRREVERSIBLE_REALITY_UNITS",
                "MINIMIZE_EXTERNAL_WAIT_DEPENDENCIES",
                "MINIMIZE_ACTIVE_ACTION_COUNT",
            ],
            "bellman": "V(S)=min_a[t(a)+sum_o P(o|a,S)*V(T(S,a,o))]",
            "priority": (
                "L(a)=E[predicates_closed|evidence]*fanout(a)*"
                "downstream_action_deletion(a)*information_gain(a)/"
                "(critical_path_seconds(a)+epsilon)"
            ),
            "probability_rule": (
                "NO_INVENTED_POINT_PROBABILITIES__USE_JEFFREYS_BETA_ONLY_FOR_"
                "ACTUAL_REPEATED_BERNOULLI_OBSERVATIONS__UNIVERSAL_CLAIMS_"
                "REQUIRE_DOMAIN_COMPLETE_LOGIC"
            ),
        },
        "fronts": {
            key: sorted(value)
            for key, value in fronts.items()
        },
        "front_rules": {
            "ROOT1_ACQUISITION_REPAIR": (
                "RUN_ONLY_FOR_POSITIVELY_ESTABLISHED_OPERATIVE_CAPABILITY_GAPS"
            ),
            "ZERO_REALITY_PROOF_COLLAPSE": (
                "USE_CURRENT_CONTENT_ADDRESSED_SCORER_SCOPE_AND_PROOF_AUTHORITIES_"
                "AT_SCHEDULING_TIME__FORMAL_OR_EXHAUSTIVE_CLOSURE_FIRST__"
                "PREPROMOTION_FALSIFICATION_GATE_REQUIRED"
            ),
            "AUTHENTICATED_ACCESS_AND_COMPUTE": (
                "ONE_SELF_SERVICE_ACCOUNT_RESOURCE_QUOTA_DATASET_ENVIRONMENT_SWEEP_"
                "WHEN_A_ZERO_COST_AUTHENTICATED_CHANNEL_EXISTS__NO_PUBLIC_PAGE_"
                "MAY_SUBSTITUTE_FOR_ACCOUNT_RECEIPT"
            ),
            "PROPRIETARY_BAR_ESCAPE": (
                "BIND_OWNER_RESULT_ON_ARRIVAL_OR_PROVE_EXACT_SUPERSET_PUBLIC_ROUTE_"
                "OR_VALID_RELATIVE_SCORE_BRIDGE_OR_SCOPE_COMPLETE_STRONGER_PROOF__"
                "NO_DUPLICATE_OUTREACH"
            ),
        },
        "dynamic_special_cases": {
            "livebench_open": livebench_open,
            "livebench_rule": (
                "READ_CURRENT_LIVEBENCH_SCORER_ROUTE_AUTHORITY_AT_EXECUTION_TIME__"
                "DO_NOT_HARDCODE_LEGACY25_UNION25_OR_IFBENCH58_IN_THIS_POLICY"
                if livebench_open else "NO_LIVEBENCH_WORK"
            ),
            "unknown_domain_open": unknown_open,
            "unknown_domain_rule": (
                "COUNTEREXAMPLE_GUIDED_DOMAIN_TOTALITY_REPAIR_THEN_INDEPENDENT_"
                "CONTENT_BOUND_VERIFICATION__NO_CREDIT_FROM_FINITE_PASS_MASS"
                if unknown_open else "NO_UNKNOWN_DOMAIN_DIRECT_AUDIT_WORK"
            ),
        },
        "final_empirical_superwave": {
            "start_condition": (
                "ZERO_REALITY_FIXED_POINT_AND_EXPLICIT_FRESH_REALITY_AUTHORITY"
            ),
            "targets": "SURVIVING_RESIDUAL_ONLY",
            "binary_pass_stop": "S_t>=K",
            "binary_fail_stop": "S_t+R_t<K",
            "weighted_pass_stop": "VERIFIED_WEIGHTED_LOWER_BOUND>=THRESHOLD",
            "weighted_fail_stop": "VERIFIED_WEIGHTED_UPPER_BOUND<THRESHOLD",
        },
        "global_controls": [
            "PREPROMOTION_FALSIFICATION_GATE_BEFORE_ANY_FORMAL_OR_STRONGER_PROOF_LEDGER_MUTATION",
            "RECOMPUTE_THIS_POLICY_AFTER_EVERY_VERIFIED_DELTA",
            "DELETE_CLOSED_FALSIFIED_OR_DOMINATED_ACTIONS_BEFORE_NEXT_WORK",
            "NO_FRESH_REALITY_BEFORE_FIXED_POINT_AND_EXPLICIT_AUTHORITY",
            "NO_PUBLIC_PRIVATE_SUBSTITUTION_WITHOUT_EXACT_OR_SUPERSET_PROOF",
            "NO_RELATIVE_ELO_INFERENCE_FROM_PURE_ABSOLUTE_CERTIFICATES",
            "NO_DUPLICATE_OWNER_OUTREACH_WITHOUT_MATERIAL_WAKE",
            "UNKNOWN_IS_NOT_MISSING",
            "ZERO_INCREMENTAL_SPEND",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "new_reality_units_consumed": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
    return policy


def compile_from_root(root: Path) -> dict[str, Any]:
    return compile_from_objects(
        _load(root, REGISTRY),
        _load(root, LEDGER),
        _load(root, ROOT_STATE),
        _load(root, AUTHORITY),
    )


def run(args=None, root=None):
    root_path = Path(root) if root is not None else Path.cwd()
    return compile_from_root(root_path)


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))

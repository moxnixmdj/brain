"""Fail-closed verifier for the minimum B2 creative/diagram semantic repair."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

EXPECTED = {
    "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json": "661a57f839101fbf54c7e4edc76166c65ce9327d",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json": "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    "canonical/governance/CREATIVE_DIAGRAM_TERMINAL_PROOF_BASIS_GAP_20261005_V1.json": "07de409df048ba2e8e9598f917fa937656b2f354",
    "canonical/governance/OPUS55_OBSERVABLE_BEHAVIOR_FUNCTIONAL_BASIS_CHARACTERIZATION_20261005_V1.json": "62c0e207ce935a02611700a69e0917f938792b11",
    "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json": "7c1ed0adf243b92abab2cbdb6ebced921dcbb860",
    "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V12.json": "2628f99626ca64f4d57920f732b19021f8cc34c2",
    "canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_ACTIVATION_V1.json": "300fb663e6b598b389961ddf663d88abcd206545",
}

CANDIDATE = "canonical/governance/OPUS55_B2_CREATIVE_DIAGRAM_MINIMUM_SEMANTIC_REPAIR_20261005_V1.json"
SYNTHESIS_PREDICATE = "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
DIAGRAM_PREDICATE = "DIAGRAM_OUTPUT_SCOPE_QUALITY_NONINFERIOR"


class VerificationError(RuntimeError):
    pass


def _raw(path: str, root: Path = ROOT) -> bytes:
    p = root / path
    if not p.is_file():
        raise VerificationError(f"MISSING_FILE:{path}")
    return p.read_bytes()


def _load(path: str, root: Path = ROOT) -> dict[str, Any]:
    try:
        v = json.loads(_raw(path, root))
    except json.JSONDecodeError as exc:
        raise VerificationError(f"INVALID_JSON:{path}:{exc}") from exc
    if not isinstance(v, dict):
        raise VerificationError(f"NOT_OBJECT:{path}")
    return v


def git_blob_sha(path: str, root: Path = ROOT) -> str:
    raw = _raw(path, root)
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _must(cond: bool, code: str) -> None:
    if not cond:
        raise VerificationError(code)


def verify(root: Path = ROOT) -> dict[str, Any]:
    for path, expected in EXPECTED.items():
        actual = git_blob_sha(path, root)
        _must(actual == expected, f"BOUND_BLOB_DRIFT:{path}:{expected}:{actual}")

    env = _load("canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json", root)
    registry = _load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json", root)
    gap = _load("canonical/governance/CREATIVE_DIAGRAM_TERMINAL_PROOF_BASIS_GAP_20261005_V1.json", root)
    basis = _load("canonical/governance/OPUS55_OBSERVABLE_BEHAVIOR_FUNCTIONAL_BASIS_CHARACTERIZATION_20261005_V1.json", root)
    root_state = _load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json", root)
    cut = _load("canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V12.json", root)
    scorer = _load("canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_ACTIVATION_V1.json", root)
    candidate = _load(CANDIDATE, root)

    families = env.get("families")
    _must(isinstance(families, list), "ENVELOPE_FAMILIES_MISSING")
    _must(env.get("target_family_count") == 19 and len(families) == 19, "FAMILY_COUNT_NOT_19")
    comm = [x for x in families if isinstance(x, dict) and x.get("id") == "COMMUNICATION_AND_SYNTHESIS"]
    _must(len(comm) == 1, "COMMUNICATION_SYNTHESIS_FAMILY_IDENTITY")
    old = "Communicate clearly, prioritize what matters, follow writing rules and synthesize complex work over long sessions."
    _must(comm[0].get("useful_behavior") == old, "COMMUNICATION_SYNTHESIS_BASE_SEMANTICS_DRIFT")

    predicates = registry.get("predicates")
    _must(isinstance(predicates, list), "REGISTRY_PREDICATES_MISSING")
    ids = [str(x.get("id")) for x in predicates if isinstance(x, dict)]
    _must(len(predicates) == 38 and len(ids) == 38 and len(set(ids)) == 38, "REGISTRY_NOT_EXACT_38_UNIQUE")
    _must(SYNTHESIS_PREDICATE in ids, "SYNTHESIS_PREDICATE_MISSING")
    _must(DIAGRAM_PREDICATE not in ids, "DIAGRAM_PREDICATE_ALREADY_EXISTS")

    recompute = gap.get("exact_recomputation")
    _must(isinstance(recompute, dict), "CREATIVE_GAP_RECOMPUTATION_MISSING")
    _must(recompute.get("current_registry_has_creative_generation_predicate") is False, "CREATIVE_ATOM_ALREADY_PRESENT")
    _must(recompute.get("current_registry_has_diagram_output_quality_predicate") is False, "DIAGRAM_ATOM_ALREADY_PRESENT")
    _must(gap.get("classification", {}).get("terminal_proof_basis_gap_proved_candidate") is True, "CREATIVE_DIAGRAM_GAP_NOT_BOUND")

    b2 = [x for x in basis.get("functional_basis", []) if isinstance(x, dict) and x.get("id") == "B2_INFORMATION_TRANSFORMATION_REASONING_AND_PROBLEM_SOLVING"]
    _must(len(b2) == 1, "B2_BASIS_IDENTITY")
    _must("COMMUNICATION_AND_SYNTHESIS" not in (b2[0].get("families") or []), "B2_ALREADY_ASSIGNED_TO_COMMUNICATION_SYNTHESIS")

    acceptance = root_state.get("current_acceptance")
    _must(isinstance(acceptance, dict), "ROOT_ACCEPTANCE_MISSING")
    _must(acceptance.get("proved_atomic") == 14 and acceptance.get("unresolved_atomic") == 24, "ROOT_NOT_14_24")
    partition = root_state.get("current_residual_root_partition")
    _must(isinstance(partition, dict), "ROOT_PARTITION_MISSING")
    _must(SYNTHESIS_PREDICATE in (partition.get("root2_only") or []), "SYNTHESIS_NOT_CURRENTLY_UNRESOLVED_ROOT2_ONLY")

    groups = cut.get("minimum_zero_reality_action_groups")
    _must(isinstance(groups, list), "ZERO_REALITY_GROUPS_MISSING")
    f = [x for x in groups if isinstance(x, dict) and x.get("id") == "F_SYNTHESIS_COMPARATOR_CERTIFICATE"]
    _must(len(f) == 1 and f[0].get("predicates") == [SYNTHESIS_PREDICATE], "SYNTHESIS_ZERO_REALITY_GROUP_DRIFT")
    action = str(f[0].get("action") or "").upper()
    _must("NO_MATCHED CASE EXECUTION" in action, "SYNTHESIS_PREEXPOSURE_EXECUTION_GUARD_MISSING")

    status = str(scorer.get("status") or "").upper()
    _must("PREEXPOSURE" in status and "ACTIVE" in status, "SCORER_NOT_ACTIVE_PREEXPOSURE")
    authority = scorer.get("authority")
    _must(isinstance(authority, dict), "SCORER_AUTHORITY_MISSING")
    _must(authority.get("execution") is False and authority.get("promotion") is False and authority.get("fresh_reality") is False, "SCORER_AUTHORITY_TOO_STRONG")
    preserved = scorer.get("effects", {}).get("preserve") or []
    for required in [
        "FROZEN_MATCHED_CASE_POPULATION_AND_EXPLICIT_FRESH_REALITY_AUTHORITY",
        "BRAIN_AND_OPUS_IDENTICAL_CASE_EXECUTION",
        "MATCHED_QUALITY_RESULT",
    ]:
        _must(required in preserved, f"SCORER_PREEXPOSURE_RESIDUAL_MISSING:{required}")

    _must(candidate.get("independent_verification_required") is True, "CANDIDATE_INDEPENDENCE_NOT_REQUIRED")
    for k in ["scheduling_authority", "execution_authority", "promotion_authority", "fresh_reality_authority"]:
        _must(candidate.get(k) is False, f"CANDIDATE_AUTHORITY_NONZERO:{k}")
    accounting = candidate.get("accounting") or {}
    for k in [
        "incremental_spend_usd",
        "new_reality_units_consumed",
        "terminal_cases_consumed",
        "acceptance_credit_delta",
        "family_credit_delta",
        "capability_credit_delta",
        "ownership_credit_delta",
    ]:
        _must(accounting.get(k) == 0, f"CANDIDATE_ACCOUNTING_NONZERO:{k}")

    proposed = candidate.get("single_new_atomic_obligation") or {}
    _must(proposed.get("id") == DIAGRAM_PREDICATE, "CANDIDATE_DIAGRAM_ATOM_ID_DRIFT")
    _must(proposed.get("atomic_count_after_if_integrated") == 39, "CANDIDATE_ATOMIC_PROJECTION_NOT_39")
    _must(proposed.get("unresolved_atomic_after_if_integrated") == 25, "CANDIDATE_UNRESOLVED_PROJECTION_NOT_25")

    return {
        "status": "PASS",
        "base_state": "14_PROVED_24_UNRESOLVED_19_FAMILIES_38_ATOMS",
        "verified_candidate": CANDIDATE,
        "preexposure_synthesis_widening_admissible_as_candidate": True,
        "diagram_requires_separate_atomic_obligation_as_candidate": True,
        "projected_if_integrated": "19_FAMILIES_39_ATOMS_14_PROVED_25_UNRESOLVED",
        "credit_delta": 0,
        "fresh_reality": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))

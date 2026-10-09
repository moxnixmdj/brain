"""OEWN-complete sense to authenticated concept-policy bridge V1.

This is deliberately a composition layer, not a new semantic inference engine.

It accepts:
1. a complete release-relative OEWN sense enumeration for one lemma/POS;
2. an authenticated bounded concept registry whose concepts already carry complete
   terminal signatures and complete declared observation outcome maps; and
3. an independently verified mapping from EVERY OEWN candidate sense to one or
   more concepts in that registry.

The bridge never ranks away OEWN senses. It projects the authenticated mapping
onto the already-owned semantic ambiguity controller. Consequently it can:
- prove that surviving sense ambiguity is terminally irrelevant;
- return the exact existing minimax discriminator when policy changes across
  surviving concepts; or
- fail closed and request stronger authenticated information.

No open-world English completeness, intended-sense identity, execution,
acceptance, promotion, or terminal authority is created here.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import bounded_authenticated_concept_universe_v1 as concepts
from canonical.runtime.semantic_ambiguity_control_v1 import decide as decide_ambiguity

SCHEMA = "PROJECT_BRAIN_OEWN_CONCEPT_POLICY_BRIDGE_V1"
MAPPING_AUTHORITY_SCHEMA = (
    "PROJECT_BRAIN_OEWN_CONCEPT_MAPPING_AUTHORITY_RECEIPT_V1"
)
_HEX = set("0123456789abcdef")


class OEWNConceptPolicyBridgeError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _sha_ok(value: Any) -> bool:
    text = str(value or "").lower()
    return len(text) == 64 and all(ch in _HEX for ch in text)


def _base(status: str, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "oewn_candidate_set_complete": False,
        "mapping_complete_for_oewn_candidate_senses": False,
        "registry_scope_authenticated": False,
        "concept_link_semantics_authenticated": False,
        "hypothesis_set_complete_for_bound_bridge": False,
        "intended_sense_identified": False,
        "intended_sense_identity_required": None,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def _normalize_oewn(oewn_result: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(oewn_result, Mapping):
        raise OEWNConceptPolicyBridgeError("OEWN_RESULT_REQUIRED")
    if oewn_result.get("pass") is not True:
        raise OEWNConceptPolicyBridgeError("OEWN_ENUMERATION_NOT_PASSED")
    if oewn_result.get("candidate_set_complete_relative_to_release") is not True:
        raise OEWNConceptPolicyBridgeError(
            "OEWN_RELEASE_RELATIVE_COMPLETENESS_UNPROVED"
        )
    archive_sha = str(oewn_result.get("archive_sha256") or "").lower()
    if not _sha_ok(archive_sha):
        raise OEWNConceptPolicyBridgeError("OEWN_ARCHIVE_SHA256_INVALID")
    lemma = str(oewn_result.get("lemma") or "").strip()
    if not lemma:
        raise OEWNConceptPolicyBridgeError("OEWN_LEMMA_REQUIRED")
    senses = oewn_result.get("senses")
    if not isinstance(senses, Sequence) or isinstance(senses, (str, bytes)):
        raise OEWNConceptPolicyBridgeError("OEWN_SENSES_INVALID")
    normalized = []
    seen = set()
    for i, raw in enumerate(senses):
        if not isinstance(raw, Mapping):
            raise OEWNConceptPolicyBridgeError(f"OEWN_SENSE_NOT_OBJECT:{i}")
        sid = str(raw.get("sense_id") or "").strip()
        synset = str(raw.get("synset_id") or "").strip()
        pos = str(raw.get("part_of_speech") or "").strip()
        if not sid or not synset or not pos:
            raise OEWNConceptPolicyBridgeError(
                f"OEWN_SENSE_ID_SYNSET_OR_POS_MISSING:{i}"
            )
        if sid in seen:
            raise OEWNConceptPolicyBridgeError("OEWN_SENSE_ID_DUPLICATE:" + sid)
        seen.add(sid)
        normalized.append(
            {
                "sense_id": sid,
                "synset_id": synset,
                "part_of_speech": pos,
            }
        )
    normalized.sort(
        key=lambda row: (
            row["part_of_speech"],
            row["sense_id"],
            row["synset_id"],
        )
    )
    return {
        "archive_sha256": archive_sha,
        "lemma": lemma,
        "requested_part_of_speech": oewn_result.get("requested_part_of_speech"),
        "release_relative_absence": bool(oewn_result.get("release_relative_absence")),
        "senses": normalized,
    }


def _normalize_mapping(
    mapping: Mapping[str, Any],
    *,
    sense_ids: Sequence[str],
    registry_concept_ids: Sequence[str],
) -> dict[str, list[str]]:
    if not isinstance(mapping, Mapping):
        raise OEWNConceptPolicyBridgeError("SENSE_TO_CONCEPT_MAPPING_REQUIRED")
    required = set(sense_ids)
    supplied = {str(k) for k in mapping}
    if supplied != required:
        missing = sorted(required - supplied)
        extra = sorted(supplied - required)
        raise OEWNConceptPolicyBridgeError(
            "SENSE_MAPPING_DOMAIN_MISMATCH:"
            + json.dumps({"missing": missing, "extra": extra}, sort_keys=True)
        )
    allowed = set(registry_concept_ids)
    normalized: dict[str, list[str]] = {}
    for sid in sorted(required):
        raw = mapping.get(sid)
        if (
            not isinstance(raw, Sequence)
            or isinstance(raw, (str, bytes))
            or not raw
        ):
            raise OEWNConceptPolicyBridgeError(
                "SENSE_MAPPING_CONCEPT_IDS_REQUIRED:" + sid
            )
        ids = sorted({str(x).strip() for x in raw if str(x).strip()})
        if not ids:
            raise OEWNConceptPolicyBridgeError(
                "SENSE_MAPPING_CONCEPT_IDS_EMPTY:" + sid
            )
        unknown = sorted(set(ids) - allowed)
        if unknown:
            raise OEWNConceptPolicyBridgeError(
                "SENSE_MAPPING_UNKNOWN_CONCEPT:"
                + sid
                + ":"
                + ",".join(unknown)
            )
        normalized[sid] = ids
    return normalized


def _authenticate_mapping(
    *,
    mapping_basis: Mapping[str, Any],
    mapping_authority_receipt: Mapping[str, Any] | None,
    mapping_authority_verifier: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None,
) -> dict[str, Any]:
    if mapping_authority_receipt is None or mapping_authority_verifier is None:
        return {
            "pass": False,
            "status": "AUTHORITY_NOT_BOUND",
            "reason": "MAPPING_AUTHORITY_RECEIPT_AND_VERIFIER_REQUIRED",
        }
    if not isinstance(mapping_authority_receipt, Mapping):
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "MAPPING_AUTHORITY_RECEIPT_INVALID",
        }
    result = mapping_authority_verifier(
        deepcopy(dict(mapping_authority_receipt))
    )
    if not isinstance(result, Mapping):
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "MAPPING_AUTHORITY_VERIFIER_RETURNED_NO_RECEIPT",
        }
    out = deepcopy(dict(result))
    required = {
        "pass": True,
        "schema": MAPPING_AUTHORITY_SCHEMA,
        "mapping_sha256": _sha(mapping_basis),
        "oewn_archive_sha256": mapping_basis["oewn_archive_sha256"],
        "registry_sha256": mapping_basis["registry_sha256"],
        "mapping_complete_for_oewn_candidate_senses": True,
        "concept_link_semantics_authenticated": True,
        "verification_authority_mutated": False,
        "independent_verifier": True,
    }
    mismatch = [key for key, value in required.items() if out.get(key) != value]
    if not _sha_ok(out.get("receipt_sha256")):
        mismatch.append("receipt_sha256")
    if mismatch:
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "MAPPING_AUTHORITY_BINDING_INVALID",
            "mismatch_fields": sorted(set(mismatch)),
            "authority_result": out,
        }
    return out


def resolve(
    *,
    oewn_result: Mapping[str, Any],
    registry: Mapping[str, Any],
    sense_to_concept_ids: Mapping[str, Any],
    registry_authority_receipt: Mapping[str, Any] | None = None,
    registry_authority_verifier: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None = None,
    mapping_authority_receipt: Mapping[str, Any] | None = None,
    mapping_authority_verifier: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None = None,
    ambiguity_owner: str = "SYSTEM_MODEL",
) -> dict[str, Any]:
    """Resolve only the terminally relevant ambiguity on a bound OEWN universe."""
    try:
        oewn = _normalize_oewn(oewn_result)
        if oewn["release_relative_absence"] or not oewn["senses"]:
            return _base(
                "OPEN__OEWN_RELEASE_RELATIVE_ABSENCE__AUTHENTICATED_DOMAIN_UNIVERSE_REQUIRED",
                False,
                oewn_candidate_set_complete=True,
                oewn_archive_sha256=oewn["archive_sha256"],
                lemma=oewn["lemma"],
                reason=(
                    "OEWN_RELEASE_RELATIVE_ABSENCE_IS_NOT_OPEN_WORLD_SEMANTIC_ABSENCE"
                ),
                required_action=(
                    "ACQUIRE_MINIMUM_AUTHENTICATED_DOMAIN_CONCEPT_UNIVERSE_OR_DIRECT_E2E_CERTIFICATE"
                ),
            )

        universe = concepts.resolve(
            registry,
            {},
            ambiguity_owner=ambiguity_owner,
            authority_receipt=registry_authority_receipt,
            authority_verifier=registry_authority_verifier,
        )
        registry_sha = str(universe.get("registry_sha256") or "").lower()
        candidate_registry_ids = list(universe.get("candidate_concept_ids") or [])
        registry_authenticated = (
            universe.get("authenticated_scope_completeness") is True
            and universe.get("hypothesis_set_complete") is True
            and _sha_ok(registry_sha)
            and bool(candidate_registry_ids)
        )
        if not registry_authenticated:
            return _base(
                "OPEN__AUTHENTICATED_BOUNDED_CONCEPT_REGISTRY_REQUIRED",
                False,
                oewn_candidate_set_complete=True,
                oewn_archive_sha256=oewn["archive_sha256"],
                lemma=oewn["lemma"],
                registry_result=deepcopy(dict(universe)),
                required_action=(
                    "ACQUIRE_OR_VERIFY_ONLY_REGISTRY_SCOPE_COMPLETENESS_CONCEPT_SEMANTICS_AND_TERMINAL_SIGNATURES"
                ),
            )

        sense_ids = [row["sense_id"] for row in oewn["senses"]]
        mapping = _normalize_mapping(
            sense_to_concept_ids,
            sense_ids=sense_ids,
            registry_concept_ids=candidate_registry_ids,
        )
        mapping_basis = {
            "oewn_archive_sha256": oewn["archive_sha256"],
            "lemma": oewn["lemma"],
            "requested_part_of_speech": oewn["requested_part_of_speech"],
            "oewn_senses": deepcopy(oewn["senses"]),
            "registry_sha256": registry_sha,
            "mapping": mapping,
        }
        mapping_auth = _authenticate_mapping(
            mapping_basis=mapping_basis,
            mapping_authority_receipt=mapping_authority_receipt,
            mapping_authority_verifier=mapping_authority_verifier,
        )
        if mapping_auth.get("pass") is not True:
            return _base(
                "OPEN__AUTHENTICATED_OEWN_SENSE_TO_CONCEPT_MAPPING_REQUIRED",
                False,
                oewn_candidate_set_complete=True,
                registry_scope_authenticated=True,
                oewn_archive_sha256=oewn["archive_sha256"],
                registry_sha256=registry_sha,
                lemma=oewn["lemma"],
                mapping_sha256=_sha(mapping_basis),
                mapping_authority_result=mapping_auth,
                required_action=(
                    "ACQUIRE_OR_VERIFY_ONLY_COMPLETE_OEWN_SENSE_TO_BOUNDED_CONCEPT_MAPPING"
                ),
            )

        full_problem = universe.get("ambiguity_problem")
        if not isinstance(full_problem, Mapping):
            raise OEWNConceptPolicyBridgeError(
                "AUTHENTICATED_REGISTRY_AMBIGUITY_PROBLEM_MISSING"
            )
        full_worlds = full_problem.get("worlds")
        full_observations = full_problem.get("observations")
        if (
            not isinstance(full_worlds, Sequence)
            or isinstance(full_worlds, (str, bytes))
            or not isinstance(full_observations, Sequence)
            or isinstance(full_observations, (str, bytes))
        ):
            raise OEWNConceptPolicyBridgeError(
                "AUTHENTICATED_REGISTRY_AMBIGUITY_PROBLEM_INVALID"
            )

        mapped_concepts = sorted(
            {cid for ids in mapping.values() for cid in ids}
        )
        mapped_set = set(mapped_concepts)
        worlds = [
            deepcopy(dict(row))
            for row in full_worlds
            if isinstance(row, Mapping) and row.get("world_id") in mapped_set
        ]
        if {str(row.get("world_id")) for row in worlds} != mapped_set:
            raise OEWNConceptPolicyBridgeError(
                "MAPPED_CONCEPT_WORLD_COVERAGE_INCOMPLETE"
            )

        observations = []
        for raw in full_observations:
            if not isinstance(raw, Mapping):
                raise OEWNConceptPolicyBridgeError(
                    "REGISTRY_OBSERVATION_NOT_OBJECT"
                )
            outcomes = raw.get("outcomes")
            if not isinstance(outcomes, Mapping):
                raise OEWNConceptPolicyBridgeError(
                    "REGISTRY_OBSERVATION_OUTCOMES_INVALID"
                )
            subset = {cid: deepcopy(outcomes[cid]) for cid in mapped_concepts}
            observations.append(
                {
                    "observation_id": raw.get("observation_id"),
                    "outcome_map_complete": set(subset) == mapped_set,
                    "outcomes": subset,
                    "cost_units": raw.get("cost_units"),
                }
            )

        problem = {
            "ambiguity_owner": ambiguity_owner,
            "hypothesis_set_complete": True,
            "worlds": worlds,
            "observations": observations,
        }
        decision = decide_ambiguity(problem)

        common = {
            "oewn_candidate_set_complete": True,
            "mapping_complete_for_oewn_candidate_senses": True,
            "registry_scope_authenticated": True,
            "concept_link_semantics_authenticated": True,
            "hypothesis_set_complete_for_bound_bridge": True,
            "oewn_archive_sha256": oewn["archive_sha256"],
            "lemma": oewn["lemma"],
            "oewn_sense_ids": sorted(sense_ids),
            "registry_sha256": registry_sha,
            "mapping_sha256": _sha(mapping_basis),
            "mapped_concept_ids": mapped_concepts,
            "mapping_authority_result": mapping_auth,
            "ambiguity_problem": problem,
            "ambiguity_decision": deepcopy(dict(decision)),
        }

        if (
            decision.get("pass") is True
            and decision.get("terminally_equivalent") is True
        ):
            return _base(
                "PASS__OEWN_COMPLETE_SENSES_BOUND_TO_TERMINALLY_EQUIVALENT_AUTHENTICATED_CONCEPTS",
                True,
                intended_sense_identity_required=False,
                action="CONTINUE_WITHOUT_INTENDED_SENSE_SELECTION",
                **common,
            )

        if decision.get("status") == "OPEN__MINIMUM_TERMINAL_DISCRIMINATOR_REQUIRED":
            return _base(
                "OPEN__OEWN_SENSES_REQUIRE_MINIMUM_AUTHENTICATED_POLICY_DISCRIMINATOR",
                False,
                intended_sense_identity_required=True,
                additional_information_required=True,
                next_observation_id=decision.get("next_observation_id"),
                minimum_worst_case_cost_units=decision.get(
                    "minimum_worst_case_cost_units"
                ),
                required_action=(
                    "ACQUIRE_ONLY_THE_SELECTED_AUTHENTICATED_POLICY_CHANGING_DISCRIMINATOR"
                ),
                **common,
            )

        if decision.get("status") in {
            "OPEN__DECISIVE_INFORMATION_UNOBSERVABLE_WITHIN_DECLARED_MODEL",
            "OPEN__MINIMUM_USER_CLARIFICATION_REQUIRED__SEMANTIC_UNDERDETERMINATION",
        }:
            return _base(
                "OPEN__OEWN_SENSES_REQUIRE_STRONGER_AUTHENTIC_INFORMATION",
                False,
                intended_sense_identity_required=True,
                additional_information_required=True,
                ask_user_required=decision.get("ask_user_required") is True,
                required_action=decision.get("action"),
                **common,
            )

        return _base(
            "FAIL_CLOSED__OEWN_CONCEPT_POLICY_AMBIGUITY_MODEL_INSUFFICIENT",
            False,
            intended_sense_identity_required=None,
            reason=str(decision.get("reason") or decision.get("status") or ""),
            **common,
        )
    except Exception as exc:
        return _base(
            "FAIL_CLOSED",
            False,
            reason=type(exc).__name__ + ":" + str(exc),
        )

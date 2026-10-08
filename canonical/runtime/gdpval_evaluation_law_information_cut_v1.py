from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_GDPVAL_EVALUATION_LAW_INFORMATION_CUT_V1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
OWNER_OUTCOMES = {"BRAIN_WIN", "TIE", "OPUS_WIN"}
DECISIVE_CLASSES = {
    "EXACT_CURRENT_OWNER_SEMANTICS",
    "EXTENSIONALLY_EQUIVALENT_CURRENT_PREFERENCE_RELATION",
    "AUTHENTIC_CURRENT_OWNER_PAIRWISE_OUTCOME",
    "INDEPENDENTLY_VERIFIED_RESTRICTED_OWNER_CLASS",
    "EVALUATOR_INDEPENDENT_SCOPE_COMPLETE_DOMINANCE",
    "TARGET_TRAJECTORY_LAW_EQUALITY",
}


def _sha(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "UNRESOLVED__FAIL_CLOSED",
        "reason": reason,
        "gdpval_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
    out.update(extra)
    return out


def verify_countermodel(manifest: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        return _fail("MANIFEST_INVALID")

    public = manifest.get("public_observation_class")
    worlds = manifest.get("worlds")
    if not isinstance(public, Mapping):
        return _fail("PUBLIC_OBSERVATION_CLASS_MISSING")
    if not isinstance(worlds, Mapping):
        return _fail("WORLDS_MISSING")

    if public.get("current_owner_contract_bound") is not True:
        return _fail("CURRENT_OWNER_PUBLIC_CONTRACT_NOT_BOUND")
    if public.get("exact_current_preference_relation_bound") is not False:
        return _fail("COUNTERMODEL_REQUIRES_CURRENT_RELATION_TO_REMAIN_UNBOUND")
    if not _sha(public.get("observation_digest_sha256")):
        return _fail("PUBLIC_OBSERVATION_DIGEST_MISSING")

    left = worlds.get("left")
    right = worlds.get("right")
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        return _fail("TWO_WORLDS_REQUIRED")

    digest = public["observation_digest_sha256"]
    for name, world in (("left", left), ("right", right)):
        if world.get("public_observation_digest_sha256") != digest:
            return _fail(
                "WORLD_PUBLIC_OBSERVATIONS_NOT_IDENTICAL",
                world=name,
            )
        if world.get("consistent_with_all_bound_public_facts") is not True:
            return _fail(
                "WORLD_NOT_PROVED_COMPATIBLE_WITH_BOUND_PUBLIC_FACTS",
                world=name,
            )
        if world.get("owner_outcome") not in OWNER_OUTCOMES:
            return _fail("WORLD_OWNER_OUTCOME_INVALID", world=name)

    if left.get("owner_outcome") == right.get("owner_outcome"):
        return _fail("TARGET_RELATION_DOES_NOT_DIFFER_BETWEEN_WORLDS")

    outcomes = {left.get("owner_outcome"), right.get("owner_outcome")}
    if outcomes.isdisjoint({"OPUS_WIN"}) or outcomes.isdisjoint({"BRAIN_WIN", "TIE"}):
        return _fail("COUNTERMODEL_DOES_NOT_FLIP_BRAIN_NONINFERIORITY_TRUTH")

    separator = manifest.get("separator")
    if not isinstance(separator, Mapping):
        return _fail("SEPARATOR_STATE_MISSING")

    if separator.get("already_bound") is True:
        proof_class = separator.get("proof_class")
        if proof_class not in DECISIVE_CLASSES:
            return _fail(
                "BOUND_SEPARATOR_CLASS_NOT_DECISIVE",
                proof_class=proof_class,
            )
        if not _sha(separator.get("evidence_sha256")):
            return _fail("BOUND_SEPARATOR_EVIDENCE_MISSING")
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "COUNTERMODEL_ALREADY_SEPARATED__RERUN_TARGET_PROOF",
            "reason": "A_DECISIVE_SEPARATOR_IS_ALREADY_BOUND",
            "separator_proof_class": proof_class,
            "gdpval_credit_delta": 0,
            "terminal_credit_delta": 0,
        }

    if separator.get("public_metadata_only") is not False:
        return _fail("SEPARATOR_STATE_MUST_EXPLICITLY_REJECT_METADATA_ONLY")

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__PUBLIC_INFORMATION_NONIDENTIFIABILITY_COUNTERMODEL",
        "public_observations_identical": True,
        "target_relation_differs": True,
        "public_information_alone_entails_brain_noninferiority": False,
        "public_information_alone_entails_opus_superiority": False,
        "minimum_information_statement": (
            "AT_LEAST_ONE_AUTHENTIC_SEPARATOR_MUST_EXCLUDE_ONE_OF_THE_"
            "PUBLICLY_INDISTINGUISHABLE_OWNER_RELATION_WORLDS__UNLESS_A_"
            "STRONGER_EVALUATOR_INDEPENDENT_CERTIFICATE_BYPASSES_THE_RELATION"
        ),
        "admissible_separator_classes": sorted(DECISIVE_CLASSES),
        "not_sufficient_by_itself": [
            "MORE_GENERAL_GDPVAL_METADATA",
            "CROWD_BT_FORMULA",
            "AGGREGATE_ELO",
            "HISTORICAL_V1_GRADING_PROMPT",
            "PUBLIC_RUBRIC_CRITERIA",
            "UNVERIFIED_THIRD_PARTY_GRADER",
        ],
        "next_action": (
            "ACQUIRE_OR_PROVE_ONLY_ONE_DECISIVE_SEPARATOR_CLASS__OR_PROVE_"
            "EVALUATOR_INDEPENDENT_SCOPE_COMPLETE_DOMINANCE__DO_NOT_REPEAT_"
            "METADATA_SEARCH"
        ),
        "gdpval_credit_delta": 0,
        "terminal_credit_delta": 0,
    }

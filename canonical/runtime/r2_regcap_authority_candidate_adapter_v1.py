"""Bind a V89 authority-domain candidate to an existing REGCAP truth payload.

This is a proposal adapter only. It does not fetch the candidate and does not
declare semantic truth. It validates the propagated next-information request,
then attaches discovered URL metadata to the existing loss-cushion truth payload.
The downstream checker owns refetch, observation compilation, predicate identity,
and truth.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from canonical.runtime import regcap_four_way_governing_requirement_discriminator_v1 as four
from canonical.runtime import r2_authority_domain_discovery_provider_v1 as discovery

SCHEMA = "PROJECT_BRAIN_R2_REGCAP_AUTHORITY_CANDIDATE_ADAPTER_V1"
REQUEST_KIND = "ACQUIRE_ONE_AUTHENTICATED_GOVERNING_REQUIREMENT_OBSERVATION"
TRUTH_KIND = "REGCAP_LOSS_CUSHION_GROUNDING"


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "provider_authority": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _domains(raw: Any) -> list[str]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("AUTHORITY_DOMAINS_INVALID")
    out = []
    for item in raw:
        value = str(item or "").casefold().strip().lstrip(".")
        if not value:
            raise ValueError("AUTHORITY_DOMAIN_EMPTY")
        if value not in out:
            out.append(value)
    return out


def _existing_payloads(
    decision_payload: Mapping[str, Any],
    predicate_id: str,
) -> list[Mapping[str, Any]]:
    loop = decision_payload.get("bound_relevance_cegar_loop")
    if not isinstance(loop, Mapping):
        raise ValueError("BOUND_RELEVANCE_CEGAR_LOOP_REQUIRED")
    by_predicate = loop.get("truth_payloads_by_predicate_id")
    if not isinstance(by_predicate, Mapping):
        raise ValueError("TRUTH_PAYLOADS_BY_PREDICATE_ID_REQUIRED")
    value = by_predicate.get(predicate_id)
    if value is None:
        return []
    if isinstance(value, Mapping):
        return [value]
    if isinstance(value, list) and all(isinstance(x, Mapping) for x in value):
        return value
    raise ValueError("EXISTING_TRUTH_PAYLOAD_INVALID")


def adapt(
    decision_payload: Mapping[str, Any],
    predicate_id: str,
    request_packet: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        if not isinstance(predicate_id, str) or not predicate_id:
            return _base("FAIL_CLOSED", reason="PREDICATE_ID_REQUIRED")
        typed = request_packet.get("truth_next_information_request")
        if not isinstance(typed, Mapping):
            return _base("NOT_APPLICABLE__NO_TYPED_TRUTH_INFORMATION_REQUEST")
        if typed.get("request_kind") != REQUEST_KIND:
            return _base("NOT_APPLICABLE__TRUTH_REQUEST_KIND_UNMODELED")
        if typed.get("scope_id") != four.SCOPE_ID:
            return _base("FAIL_CLOSED", reason="FOUR_WAY_REQUEST_SCOPE_DRIFT")
        if typed.get("observation_id") != four.OBSERVATION_ID:
            return _base("FAIL_CLOSED", reason="FOUR_WAY_REQUEST_OBSERVATION_DRIFT")
        if sorted(str(x) for x in typed.get("candidate_concept_ids") or []) != sorted(four.DOMAIN):
            return _base("FAIL_CLOSED", reason="FOUR_WAY_REQUEST_DOMAIN_DRIFT")
        if dict(typed.get("allowed_outcomes") or {}) != dict(four.OUTCOMES):
            return _base("FAIL_CLOSED", reason="FOUR_WAY_REQUEST_OUTCOME_DRIFT")
        if typed.get("minimum_observation_count") != 1:
            return _base("FAIL_CLOSED", reason="FOUR_WAY_REQUEST_COUNT_DRIFT")
        if typed.get("independent_verification_required") is not True:
            return _base("FAIL_CLOSED", reason="FOUR_WAY_REQUEST_VERIFICATION_DRIFT")

        if (
            candidate.get("schema") != discovery.SCHEMA
            or candidate.get("pass") is not True
            or candidate.get("candidate_only") is not True
            or candidate.get("semantic_truth_authority") is True
        ):
            return _base("FAIL_CLOSED", reason="DISCOVERY_CANDIDATE_INVALID")
        scope = request_packet.get("source_scope")
        if not isinstance(scope, Mapping) or scope.get("kind") != discovery.SCOPE_KIND:
            return _base("FAIL_CLOSED", reason="UNBOUND_SOURCE_SCOPE_REQUIRED")
        scope_domains = _domains(scope.get("authority_domains"))
        if scope_domains != _domains(candidate.get("authority_domains")):
            return _base("FAIL_CLOSED", reason="DISCOVERY_AUTHORITY_DOMAIN_DRIFT")

        attachment = {
            "chosen_url": str(candidate.get("chosen_url") or "").strip(),
            "chosen_host": str(candidate.get("chosen_host") or "").casefold().strip(),
            "query": str(candidate.get("query") or scope.get("query") or "").strip(),
            "authority_domains": scope_domains,
            "timeout_s": int(scope.get("timeout_s", 20)),
            "max_bytes": int(scope.get("max_bytes", 1_500_000)),
            "discovery_evidence_path": str(candidate.get("discovery_evidence_path") or ""),
        }
        if not attachment["chosen_url"] or not attachment["chosen_host"]:
            return _base("FAIL_CLOSED", reason="DISCOVERY_CANDIDATE_IDENTITY_MISSING")

        payloads = _existing_payloads(decision_payload, predicate_id)
        eligible = [p for p in payloads if p.get("truth_kind") == TRUTH_KIND]
        if not eligible:
            return _base("NOT_APPLICABLE__NO_REGCAP_LOSS_CUSHION_TRUTH_PAYLOAD")

        enriched = []
        for payload in eligible:
            prior = payload.get("governing_requirement_candidate")
            if isinstance(prior, Mapping):
                if dict(prior) == attachment:
                    return _base(
                        "UNRESOLVED__IDENTICAL_AUTHORITY_CANDIDATE_ALREADY_ATTEMPTED",
                        chosen_url=attachment["chosen_url"],
                    )
                return _base(
                    "FAIL_CLOSED",
                    reason="EXISTING_GOVERNING_REQUIREMENT_CANDIDATE_MUTATION_FORBIDDEN",
                )
            row = deepcopy(dict(payload))
            row["governing_requirement_candidate"] = deepcopy(attachment)
            enriched.append(row)

        return _base(
            "PASS__AUTHORITY_CANDIDATE_BOUND_TO_EXISTING_REGCAP_TRUTH_CHECKER",
            passed=True,
            truth_payload_candidates=enriched,
            candidate_count=len(enriched),
            chosen_url=attachment["chosen_url"],
            downstream_checker_refetch_required=True,
            original_predicate_identity_preserved=True,
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))

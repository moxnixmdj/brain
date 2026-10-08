"""Strict source-aligned finite policy constructor with positive adequacy.

This is a positive-only policy-adequacy route.

Root contract:
- exact JSON object with no extra fields;
- every source segment must compile into the controlled acceptance grammar;
- candidate field schema and finite proposal domains are part of the root task;
- no caller verifier, capability graph, policy ID, target-effect label, or semantic
  success flag is accepted.

Positive theorem:
If exhaustive search over the declared domain finds a candidate and the
proof-to-effect-bound V2 solver independently re-verifies that exact candidate
against the Brain-compiled acceptance program, then the candidate satisfies every
source requirement admitted by this strict controlled root contract.

The declared proposal domain need NOT be complete for positive adequacy. Domain
completeness is required only for negative impossibility claims, which this module
never emits.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.source_aligned_acceptance_program_v1 import compile_program
from canonical.runtime.typed_acceptance_finite_search_v1 import search
from canonical.runtime.universal_verified_adaptive_solver_v2 import run as run_v2

SCHEMA = "PROJECT_BRAIN_SOURCE_ALIGNED_FINITE_POLICY_CONSTRUCTOR_V1"
CONTRACT_SCHEMA = "PROJECT_BRAIN_SOURCE_ALIGNED_FINITE_POLICY_CONTRACT_V1"
INTERNAL_EFFECT = "SOURCE_ALIGNED_ACCEPTANCE_SATISFIED"
CAPABILITY_ID = "source-aligned-finite-policy-constructor"

_TOP_KEYS = {
    "schema",
    "source_text",
    "source_id",
    "field_schema",
    "candidate_domains",
    "max_candidates",
}


class ContractError(ValueError):
    pass


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ContractError("DUPLICATE_JSON_KEY:" + str(key))
        out[key] = value
    return out


def _fail(reason: str, *, status: str = "FAIL_CLOSED", **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": status,
        "reason": reason,
        "policy_adequacy_proved": False,
        "negative_impossibility_authorized": False,
        "proposal_domain_global_completeness_required_for_positive_adequacy": False,
        "root_task_authority_self_proved": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def solve(raw_contract: str | bytes) -> dict[str, Any]:
    try:
        raw = raw_contract.encode("utf-8") if isinstance(raw_contract, str) else raw_contract
        if not isinstance(raw, bytes) or not raw:
            raise ContractError("RAW_CONTRACT_BYTES_REQUIRED")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ContractError("RAW_CONTRACT_NOT_UTF8") from exc
        try:
            contract = json.loads(text, object_pairs_hook=_pairs)
        except ContractError:
            raise
        except Exception as exc:
            raise ContractError("RAW_CONTRACT_JSON_INVALID") from exc

        if not isinstance(contract, Mapping) or set(contract) != _TOP_KEYS:
            raise ContractError("CONTRACT_KEYS_INVALID")
        if contract.get("schema") != CONTRACT_SCHEMA:
            raise ContractError("CONTRACT_SCHEMA_INVALID")

        source_text = contract.get("source_text")
        source_id = contract.get("source_id")
        field_schema = contract.get("field_schema")
        candidate_domains = contract.get("candidate_domains")
        max_candidates = contract.get("max_candidates")
        if not isinstance(source_text, str) or not source_text.strip():
            raise ContractError("SOURCE_TEXT_REQUIRED")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ContractError("SOURCE_ID_REQUIRED")
        if not isinstance(field_schema, Mapping) or not field_schema:
            raise ContractError("FIELD_SCHEMA_REQUIRED")
        if not isinstance(candidate_domains, Mapping) or not candidate_domains:
            raise ContractError("CANDIDATE_DOMAINS_REQUIRED")
        if (
            not isinstance(max_candidates, int)
            or isinstance(max_candidates, bool)
            or not (1 <= max_candidates <= 100000)
        ):
            raise ContractError("MAX_CANDIDATES_INVALID")

        compiled = compile_program(
            source_text,
            source_id=source_id,
            field_schema=field_schema,
        )
        if compiled.get("status") != "COMPILED":
            return _fail(
                "SOURCE_ACCEPTANCE_PROGRAM_NOT_COMPILED",
                status="UNRESOLVED__ROOT_TASK_NOT_IN_STRICT_CONTROLLED_ACCEPTANCE_CLASS",
                compilation=compiled,
            )
        ignored = compiled.get("ignored_non_normative_segments")
        unresolved = compiled.get("unresolved_normative_requirements")
        requirements = compiled.get("compiled_requirements")
        if not isinstance(ignored, list) or ignored:
            return _fail(
                "UNCOMPILED_SOURCE_SEGMENT_PRESENT",
                status="UNRESOLVED__ROOT_TASK_NOT_IN_STRICT_CONTROLLED_ACCEPTANCE_CLASS",
                compilation=compiled,
            )
        if not isinstance(unresolved, list) or unresolved:
            return _fail(
                "UNRESOLVED_NORMATIVE_REQUIREMENT_PRESENT",
                status="UNRESOLVED__ROOT_TASK_NOT_IN_STRICT_CONTROLLED_ACCEPTANCE_CLASS",
                compilation=compiled,
            )
        if not isinstance(requirements, list) or not requirements:
            return _fail(
                "NO_COMPILED_REQUIREMENTS",
                status="UNRESOLVED__ROOT_TASK_NOT_IN_STRICT_CONTROLLED_ACCEPTANCE_CLASS",
                compilation=compiled,
            )

        proposal_search = search(
            compiled["acceptance_program"],
            trusted_values={},
            candidate_domains=candidate_domains,
            max_candidates=max_candidates,
        )
        if proposal_search.get("pass") is not True:
            return _fail(
                "NO_POSITIVE_ADEQUACY_WITNESS_FROM_DECLARED_DOMAIN",
                status="UNRESOLVED__NO_POSITIVE_ADEQUACY_WITNESS",
                compilation=compiled,
                proposal_search=proposal_search,
            )
        candidate = proposal_search.get("selected_candidate")
        if not isinstance(candidate, Mapping):
            return _fail("FINITE_SEARCH_SELECTED_CANDIDATE_INVALID")

        problem = {
            "initial_facts": [],
            "target_effects": [INTERNAL_EFFECT],
            "max_solver_cycles": 4,
            "capabilities": [{
                "id": CAPABILITY_ID,
                "requires": [],
                "provides": [INTERNAL_EFFECT],
                "cost": 1,
                "result_fields": [],
                "action": {
                    "type": "verified_policy",
                    "verifier_id": "TYPED_ACCEPTANCE_PROGRAM_V1",
                    "verifier_payload": {
                        "program": compiled["acceptance_program"],
                        "trusted_values": {},
                    },
                    "effect_contract": {
                        "effects": [INTERNAL_EFFECT],
                        "verifier_success_condition": "TYPED_ACCEPTANCE_PROGRAM_PASS",
                    },
                },
            }],
        }
        verified = run_v2(
            problem,
            proposal_packets={
                CAPABILITY_ID: [{"candidate_values": dict(candidate)}],
            },
        )
        if (
            verified.get("pass") is not True
            or verified.get("status") != "SOLVED__ALL_TARGET_EFFECTS_VERIFIER_BOUND"
            or verified.get("run_verified_target_effects") != [INTERNAL_EFFECT]
        ):
            return _fail(
                "V2_REVERIFICATION_DID_NOT_MINT_BOUND_ACCEPTANCE_EFFECT",
                verifier_result=verified,
            )
        trace = verified.get("trace")
        if not isinstance(trace, list) or len(trace) != 1:
            return _fail("V2_TRACE_CARDINALITY_INVALID", verifier_result=verified)
        row = trace[0]
        if row.get("verified_output") != dict(candidate):
            return _fail("V2_VERIFIED_OUTPUT_MISMATCH", verifier_result=verified)
        if row.get("new_verified_effects") != [INTERNAL_EFFECT]:
            return _fail("V2_BOUND_EFFECT_MISMATCH", verifier_result=verified)

        root_sha = sha256(raw).hexdigest()
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__POSITIVE_POLICY_ADEQUACY_WITNESS_CONSTRUCTED_AND_REVERIFIED",
            "root_contract_sha256": root_sha,
            "source_id": source_id,
            "source_sha256": compiled.get("source_sha256"),
            "compiled_requirement_count": len(requirements),
            "selected_candidate": dict(candidate),
            "declared_candidate_count": proposal_search.get("declared_candidate_count"),
            "proposal_search_complete_over_declared_domains":
                proposal_search.get("complete_over_declared_domains") is True,
            "proposal_domain_global_completeness_required_for_positive_adequacy": False,
            "policy_constructor_id": "SOURCE_ALIGNED_FINITE_VERIFIED_SEARCH_POLICY_V1",
            "policy_adequacy_proved": True,
            "adequacy_scope":
                "EXACT_ROOT_CONTRACT_WHOSE_EVERY_SOURCE_SEGMENT_IS_COMPILED_BY_THE_CONTROLLED_ACCEPTANCE_GRAMMAR",
            "acceptance_compilation": compiled,
            "proposal_search": proposal_search,
            "v2_reverification": verified,
            "root_task_authority": {
                "state": "UPSTREAM_ROOT_OF_TRUST",
                "self_proved_by_constructor": False,
            },
            "root_task_authority_self_proved": False,
            "negative_impossibility_authorized": False,
            "u_subtraction_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "POSITIVE_WITNESS_ONLY__A_PASS_PROVES_THE_SELECTED_CANDIDATE_SATISFIES_"
                "EVERY_REQUIREMENT_IN_THIS_STRICT_CONTROLLED_ROOT_CONTRACT__"
                "SEARCH_FAILURE_DOES_NOT_PROVE_NO_ADEQUATE_POLICY_EXISTS_OUTSIDE_THE_DECLARED_DOMAIN"
            ),
        }
    except ContractError as exc:
        return _fail(str(exc))

"""Fail-closed automatic semantic discriminator and policy-dispatch adapter.

Reuses the Brain-owned v1 semantic truth checker. Discovers a selected
boolean result by checking both candidate truth values. The checker-minted,
source-bound predicate identity is authoritative; caller predicate labels
remain trace metadata only. It then binds an optional policy selection to
that *recomputed* result. No adequacy,
source-authorization, U-subtraction, or terminal credit is emitted.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from canonical.runtime.selected_semantic_truth_certificate_v1 import evaluate as verify_candidate

SCHEMA = "PROJECT_BRAIN_SELECTED_SEMANTIC_DISCRIMINATOR_DISPATCH_V1"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "UNKNOWN__FAIL_CLOSED",
        "reason": reason,
        "predicate_truth": "UNKNOWN",
        "selected_policy_id": None,
        "source_authorization_verified": False,
        "policy_adequacy_authority": False,
        "u_subtraction_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **detail,
    }


def evaluate(payload: Mapping[str, Any], policy_map: Mapping[str, str]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_REQUIRED")
    if not isinstance(policy_map, Mapping) or set(policy_map) != {"TRUE", "FALSE"}:
        return _fail("EXACT_TRUE_FALSE_POLICY_MAP_REQUIRED")
    if any(not isinstance(v, str) or not v.strip() for v in policy_map.values()):
        return _fail("POLICY_IDS_REQUIRED")
    if policy_map["TRUE"] == policy_map["FALSE"]:
        return _fail("POLICY_SELECTION_MUST_BE_DISTINCT")
    if not isinstance(payload.get("source_text"), str) or not payload["source_text"]:
        return _fail("SOURCE_TEXT_REQUIRED")
    if not isinstance(payload.get("fact_source"), str) or not payload["fact_source"]:
        return _fail("RAW_FACT_SOURCE_REQUIRED")
    if not isinstance(payload.get("fact_source_id"), str) or not payload["fact_source_id"].strip():
        return _fail("RAW_FACT_SOURCE_ID_REQUIRED")
    if not isinstance(payload.get("source_id"), str) or not payload["source_id"].strip():
        return _fail("POLICY_SOURCE_ID_REQUIRED")
    target = payload.get("target_claim_id")
    if not isinstance(target, str) or not target:
        return _fail("SELECTED_CLAIM_REQUIRED")
    claims = payload.get("claims")
    if not isinstance(claims, list) or len(claims) != 1 or not isinstance(claims[0], Mapping):
        return _fail("EXACT_ONE_SELECTED_CLAIM_REQUIRED")
    claim = claims[0]
    if claim.get("claim_id") != target:
        return _fail("SELECTED_CLAIM_ID_MISMATCH")
    if claim.get("kind") != "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION":
        return _fail("UNSUPPORTED_SEMANTIC_PROOF_FRAGMENT")
    if "condition_holds" in claim:
        return _fail("CALLER_MUST_NOT_SUPPLY_PREDICATE_TRUTH")

    results = {}
    for guessed_truth in (True, False):
        trial = dict(payload)
        trial["claims"] = [{**claim, "condition_holds": guessed_truth}]
        try:
            result = verify_candidate(trial)
        except (TypeError, ValueError, KeyError):
            return _fail("SEMANTIC_CHECKER_REJECTED_INPUT")
        if result.get("pass") is True:
            truth = "TRUE" if guessed_truth else "FALSE"
            if result.get("predicate_truth") != truth:
                return _fail("CHECKER_TRUTH_CONTRADICTION")
            results[truth] = result

    if len(results) != 1:
        return _fail(
            "SELECTED_TRUTH_NOT_UNIQUELY_PROVABLE",
            sound_candidate_count=len(results),
        )

    truth, certificate = next(iter(results.items()))
    requested_predicate_id = payload.get("predicate_id")
    if certificate.get("requested_predicate_id") != requested_predicate_id:
        return _fail("CERTIFICATE_REQUEST_ALIAS_TRACE_MISMATCH")
    verified_predicate_id = certificate.get("predicate_id")
    prefix = "source-condition-sha256:"
    if (
        not isinstance(verified_predicate_id, str)
        or not verified_predicate_id.startswith(prefix)
        or len(verified_predicate_id) != len(prefix) + 64
        or any(ch not in "0123456789abcdef" for ch in verified_predicate_id[len(prefix):])
    ):
        return _fail("CERTIFICATE_SOURCE_PREDICATE_ID_INVALID")
    selected = policy_map[truth]
    input_binding = {
        "predicate_id": verified_predicate_id,
        "requested_predicate_id": requested_predicate_id,
        "requested_predicate_id_authority": False,
        "target_claim_id": target,
        "source_id": payload["source_id"],
        "source_sha256": hashlib.sha256(payload["source_text"].encode()).hexdigest(),
        "fact_source_id": payload["fact_source_id"],
        "fact_source_sha256": hashlib.sha256(payload["fact_source"].encode()).hexdigest(),
        "policy_map": dict(policy_map),
    }
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "SELECTED_SEMANTIC_TRUTH_PROVED__POLICY_ROUTE_SELECTED__ADEQUACY_UNVERIFIED",
        "predicate_truth": truth,
        "predicate_id": verified_predicate_id,
        "requested_predicate_id": requested_predicate_id,
        "requested_predicate_id_authority": False,
        "selected_policy_id": selected,
        "input_binding_sha256": _digest(input_binding),
        "input_binding": input_binding,
        "selected_truth_certificate": certificate,
        "truthful_precommitment_observation": True,
        "source_authorization_verified": False,
        "policy_adequacy_authority": False,
        "u_subtraction_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "BRANCH_SELECTION_ONLY__CHECKER_MINTED_SOURCE_PREDICATE_ID_AUTHORITATIVE__"
            "CALLER_LABEL_NONAUTHORITATIVE__NO_CLAIM_POLICY_IS_ADEQUATE__"
            "NO_GLOBAL_SCOPE_OR_TERMINAL_CREDIT"
        ),
    }


def run(args: Mapping[str, Any], root: Any) -> dict[str, Any]:
    """Execute from repository-contained JSON inputs and write a zero-credit receipt."""
    from pathlib import Path

    if not isinstance(args, Mapping):
        raise ValueError("ARGS_MAPPING_REQUIRED")
    base = Path(root).resolve()

    def bounded_path(key: str) -> Path:
        name = args.get(key)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("PATH_REQUIRED:" + key)
        p = (base / name).resolve()
        if p == base or base not in p.parents:
            raise ValueError("PATH_OUTSIDE_REPOSITORY:" + key)
        return p

    payload_file = bounded_path("payload_path")
    policy_file = bounded_path("policy_map_path")
    output_file = bounded_path("output_path")
    if output_file in (payload_file, policy_file):
        raise ValueError("OUTPUT_MUST_NOT_OVERWRITE_INPUT")
    payload = json.loads(payload_file.read_text(encoding="utf-8"))
    policy_map = json.loads(policy_file.read_text(encoding="utf-8"))
    result = evaluate(payload, policy_map)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return {
        "status": result["status"],
        "output_path": str(output_file.relative_to(base)),
        "output_verified": True,
        "selected_policy_id": result.get("selected_policy_id"),
        "predicate_truth": result["predicate_truth"],
        "u_subtraction_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }

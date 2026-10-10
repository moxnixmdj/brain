"""Content-bound value state for the Universal Verified Adaptive Solver.

The existing universal solver state capsule proves Boolean effect lineage but does
not retain the exact verified values needed by later capabilities. This module
adds a value-carrying composition layer on top of composition_state_capsule_v2.

Trusted inputs:
- a capability contract with declared requires/provides/result_fields;
- a trace row already accepted by the universal solver's verifier/effect gates.

Stored result envelope:
- every key from a mapping verified_output, or verified_output as one scalar key;
- effect_outcome when present;
- proof_digest;
- proposal_sha256;
- action_contract_sha256.

Later capability templates may use:
  {"$effect_result": {"effect": "EFFECT_ID", "field": "field.path"}}

Resolution reads ONLY the verified capsule state. The referenced effect must be a
declared prerequisite, and the requested top-level result field must have been
declared by the producer capability. Nested lookup below that declared top-level
field is allowed.

This module proves value/provenance continuity, not semantic adequacy of field
meaning. Dynamic use of a resolved value inside a later verifier/effect still
requires independently authenticated value/effect semantics.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from canonical.runtime.composition_state_capsule_v2 import (
    empty_capsule,
    append_macrostep,
    project_context,
    verify_capsule,
)

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_SOLVER_VALUE_STATE_V1"


class ValueStateError(ValueError):
    pass


def _tokens(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueStateError(label + "_INVALID")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueStateError(label + "_ITEM_INVALID")
        token = item.strip()
        if token in out:
            raise ValueStateError(label + "_DUPLICATE:" + token)
        out.append(token)
    return out


def initialize(
    problem: Mapping[str, Any],
    *,
    initial_values: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        raise ValueStateError("PROBLEM_NOT_OBJECT")
    initial = _tokens(problem.get("initial_facts", []), "INITIAL_FACTS")
    supplied = dict(initial_values or {})
    if set(supplied) - set(initial):
        raise ValueStateError("INITIAL_VALUE_FOR_UNDECLARED_FACT")
    cap = empty_capsule()
    if not initial:
        return cap

    values = {}
    for fact in initial:
        values[fact] = {
            "effect": fact,
            "producer_cycle": None,
            "capability_id": "TASK_CONTRACT",
            "result": deepcopy(supplied.get(fact)),
            "result_fields": [],
            "has_explicit_initial_value": fact in supplied,
        }
    evidence_id = "task_contract_initial_values"
    return append_macrostep(
        cap,
        producer_ref="TASK_CONTRACT",
        producer_descriptor={
            "kind": "UPSTREAM_TASK_CONTRACT",
            "initial_facts": initial,
            "initial_value_keys": sorted(supplied),
        },
        action_ref="TASK_CONTRACT_INITIALIZATION",
        action_descriptor={
            "kind": "INITIAL_VALUE_STATE_ADMISSION",
            "initial_facts": initial,
        },
        requires=[],
        provides=initial,
        values=values,
        evidence_values={
            evidence_id: {
                "kind": "UPSTREAM_TASK_CONTRACT_INITIAL_STATE",
                "initial_facts": initial,
                "initial_value_keys": sorted(supplied),
            }
        },
        lineage={
            fact: [
                "evidence:" + evidence_id,
                "action:TASK_CONTRACT_INITIALIZATION",
                "producer:TASK_CONTRACT",
            ]
            for fact in initial
        },
    )


def result_envelope(trace_row: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(trace_row, Mapping):
        raise ValueStateError("TRACE_ROW_INVALID")
    verified = trace_row.get("verified_output")
    if isinstance(verified, Mapping):
        out = deepcopy(dict(verified))
    else:
        out = {"verified_output": deepcopy(verified)}

    reserved = {
        "effect_outcome",
        "proof_digest",
        "proposal_sha256",
        "action_contract_sha256",
    }
    collision = reserved & set(out)
    if collision:
        raise ValueStateError(
            "VERIFIED_OUTPUT_RESERVED_FIELD_COLLISION:" + ",".join(sorted(collision))
        )
    out["effect_outcome"] = deepcopy(trace_row.get("effect_outcome"))
    out["proof_digest"] = trace_row.get("proof_digest")
    out["proposal_sha256"] = trace_row.get("proposal_sha256")
    out["action_contract_sha256"] = trace_row.get("action_contract_sha256")
    return out


def append_verified_transition(
    capsule: Mapping[str, Any],
    *,
    capability: Mapping[str, Any],
    trace_row: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(capability, Mapping):
        raise ValueStateError("CAPABILITY_INVALID")
    cid = capability.get("id")
    if not isinstance(cid, str) or not cid:
        raise ValueStateError("CAPABILITY_ID_INVALID")
    if trace_row.get("capability_id") != cid:
        raise ValueStateError("TRACE_CAPABILITY_MISMATCH")
    cycle = trace_row.get("cycle")
    if not isinstance(cycle, int) or isinstance(cycle, bool) or cycle < 0:
        raise ValueStateError("TRACE_CYCLE_INVALID")

    requires = _tokens(capability.get("requires", []), "REQUIRES")
    provides = _tokens(capability.get("provides", []), "PROVIDES")
    result_fields = _tokens(capability.get("result_fields", []), "RESULT_FIELDS")
    if not provides:
        raise ValueStateError("PROVIDES_EMPTY")

    context = project_context(capsule, requires) if requires else {
        "capsule_head_hash": capsule.get("head_hash"),
        "values": {},
        "bindings": {},
    }
    envelope = result_envelope(trace_row)
    missing_fields = [field for field in result_fields if field.split(".", 1)[0] not in envelope]
    if missing_fields:
        raise ValueStateError(
            "DECLARED_RESULT_FIELD_MISSING:" + ",".join(sorted(missing_fields))
        )

    provider_bindings = {}
    for effect in requires:
        state = context["values"][effect]
        if not isinstance(state, Mapping):
            raise ValueStateError("REQUIRED_VALUE_STATE_INVALID:" + effect)
        provider_bindings[effect] = {
            "producer_cycle": state.get("producer_cycle"),
            "capability_id": state.get("capability_id"),
        }

    values = {
        effect: {
            "effect": effect,
            "producer_cycle": cycle,
            "capability_id": cid,
            "result": deepcopy(envelope),
            "result_fields": sorted(result_fields),
        }
        for effect in provides
    }
    evidence_id = "verified_execution_result:" + str(cycle)
    lineage_refs = (
        ["state:" + x for x in requires]
        + ["evidence:" + evidence_id, "action:solver-step-" + str(cycle), "producer:" + cid]
    )
    out = append_macrostep(
        capsule,
        producer_ref=cid,
        producer_descriptor={
            "kind": "UNIVERSAL_SOLVER_CAPABILITY",
            "capability_id": cid,
            "requires": requires,
            "provides": provides,
            "result_fields": sorted(result_fields),
            "provider_bindings": provider_bindings,
        },
        action_ref="solver-step-" + str(cycle),
        action_descriptor={
            "action_contract_sha256": trace_row.get("action_contract_sha256"),
            "proposal_sha256": trace_row.get("proposal_sha256"),
            "proof_digest": trace_row.get("proof_digest"),
            "verifier_id": trace_row.get("verifier_id"),
            "effect_outcome_sha256": trace_row.get("effect_outcome_sha256"),
        },
        requires=requires,
        provides=provides,
        values=values,
        evidence_values={
            evidence_id: {
                "verified_output": deepcopy(trace_row.get("verified_output")),
                "effect_outcome": deepcopy(trace_row.get("effect_outcome")),
                "proof_digest": trace_row.get("proof_digest"),
                "proposal_sha256": trace_row.get("proposal_sha256"),
                "action_contract_sha256": trace_row.get("action_contract_sha256"),
            }
        },
        lineage={effect: list(lineage_refs) for effect in provides},
    )
    verdict = verify_capsule(out)
    if verdict.get("status") != "PASS":
        raise ValueStateError("VALUE_CAPSULE_INVALID_AFTER_APPEND:" + str(verdict.get("reason")))
    return out


def _field(value: Any, path: str) -> Any:
    current = value
    for token in path.split("."):
        if isinstance(current, Mapping):
            if token not in current:
                raise ValueStateError("RESULT_REFERENCE_FIELD_MISSING:" + path)
            current = current[token]
        elif isinstance(current, list) and token.isdigit():
            index = int(token)
            if index < 0 or index >= len(current):
                raise ValueStateError("RESULT_REFERENCE_INDEX_INVALID:" + path)
            current = current[index]
        else:
            raise ValueStateError("RESULT_REFERENCE_FIELD_INVALID:" + path)
    return deepcopy(current)


def resolve_effect_results(
    capsule: Mapping[str, Any],
    *,
    capability: Mapping[str, Any],
    template: Any,
) -> Any:
    if not isinstance(capability, Mapping):
        raise ValueStateError("CAPABILITY_INVALID")
    requires = _tokens(capability.get("requires", []), "REQUIRES")
    context = project_context(capsule, requires) if requires else {
        "capsule_head_hash": capsule.get("head_hash"),
        "values": {},
        "bindings": {},
    }

    def resolve(value: Any) -> Any:
        if isinstance(value, Mapping):
            if set(value) == {"$effect_result"}:
                spec = value["$effect_result"]
                if not isinstance(spec, Mapping) or set(spec) != {"effect", "field"}:
                    raise ValueStateError("EFFECT_RESULT_REFERENCE_INVALID")
                effect = spec.get("effect")
                field = spec.get("field")
                if not isinstance(effect, str) or effect not in requires:
                    raise ValueStateError("EFFECT_RESULT_REFERENCE_NOT_DECLARED_REQUIREMENT:" + str(effect))
                if not isinstance(field, str) or not field.strip():
                    raise ValueStateError("EFFECT_RESULT_REFERENCE_FIELD_INVALID")
                state = context["values"].get(effect)
                if not isinstance(state, Mapping):
                    raise ValueStateError("CAPSULE_EFFECT_STATE_INVALID:" + effect)
                result = state.get("result")
                declared = state.get("result_fields")
                if not isinstance(result, Mapping) or not isinstance(declared, list):
                    raise ValueStateError("CAPSULE_EFFECT_RESULT_INVALID:" + effect)
                top = field.split(".", 1)[0]
                allowed_tops = {str(x).split(".", 1)[0] for x in declared}
                if top not in allowed_tops:
                    raise ValueStateError(
                        "RESULT_REFERENCE_FIELD_UNDECLARED:" + effect + ":" + field
                    )
                return _field(result, field)
            return {k: resolve(v) for k, v in value.items()}
        if isinstance(value, list):
            return [resolve(x) for x in value]
        return deepcopy(value)

    out = resolve(template)

    def unresolved(value: Any) -> bool:
        if isinstance(value, Mapping):
            if "$effect_result" in value:
                return True
            return any(unresolved(x) for x in value.values())
        if isinstance(value, list):
            return any(unresolved(x) for x in value)
        return False

    if unresolved(out):
        raise ValueStateError("UNRESOLVED_EFFECT_RESULT_REFERENCE")
    return out


def project_verified_values(
    capsule: Mapping[str, Any],
    effects: Sequence[str],
) -> dict[str, Any]:
    context = project_context(capsule, effects)
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "capsule_head_hash": context["capsule_head_hash"],
        "values": deepcopy(context["values"]),
        "bindings": deepcopy(context["bindings"]),
        "terminal_authority": False,
    }

"""Conservative parameterized skill candidate induction.

This module anti-unifies multiple independently verified exact solver episodes.
It generalizes ONLY proposal scalar leaves while requiring invariant:
- scope ID;
- step count and order;
- operation/capability ID;
- verifier ID;
- action-contract SHA256;
- output effects;
- proposal JSON container structure and keys/list lengths.

Equal proposal values remain constants. Varying scalar leaves become typed slots.
The result is a CANDIDATE ONLY. It may not be reused or executed until a separate
independent proof establishes behavior preservation over a declared parameter
domain.

This deliberately refuses structural generalization, control-flow changes,
verifier changes, action-contract changes, or inferred parameter domains.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_PARAMETERIZED_SKILL_CANDIDATE_V1"


class ParameterizedSkillError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if type(value) is bool:
        return "boolean"
    if type(value) is int:
        return "integer"
    if type(value) is float:
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise ParameterizedSkillError("UNSUPPORTED_JSON_TYPE:" + type(value).__name__)


def _verified_episode(row: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        raise ParameterizedSkillError("EPISODE_NOT_OBJECT")
    eid = row.get("episode_id")
    scope = row.get("scope_id")
    steps = row.get("steps")
    receipt = row.get("verification_receipt")
    if not isinstance(eid, str) or not eid:
        raise ParameterizedSkillError("EPISODE_ID_INVALID")
    if not isinstance(scope, str) or not scope:
        raise ParameterizedSkillError("SCOPE_ID_INVALID")
    if not isinstance(steps, list) or not steps:
        raise ParameterizedSkillError("EPISODE_STEPS_INVALID")
    if not isinstance(receipt, Mapping):
        raise ParameterizedSkillError("EPISODE_VERIFICATION_RECEIPT_REQUIRED:" + eid)
    if receipt.get("independent_verified") is not True:
        raise ParameterizedSkillError("EPISODE_NOT_INDEPENDENTLY_VERIFIED:" + eid)
    if receipt.get("exact_byte_bound") is not True or receipt.get("conclusion") != "success":
        raise ParameterizedSkillError("EPISODE_VERIFICATION_NOT_EXACT_SUCCESS:" + eid)
    if not isinstance(receipt.get("public_runner_provenance"), Mapping):
        raise ParameterizedSkillError("EPISODE_PUBLIC_RUNNER_PROVENANCE_REQUIRED:" + eid)
    return {
        "episode_id": eid,
        "scope_id": scope,
        "steps": steps,
        "verification_receipt": dict(receipt),
    }


def _step_parts(step: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(step, Mapping):
        raise ParameterizedSkillError("STEP_NOT_OBJECT")
    op = step.get("op")
    inputs = step.get("inputs")
    outputs = step.get("outputs")
    if not isinstance(op, str) or not op:
        raise ParameterizedSkillError("STEP_OP_INVALID")
    if not isinstance(inputs, list) or any(not isinstance(x, str) for x in inputs):
        raise ParameterizedSkillError("STEP_INPUTS_INVALID")
    if not isinstance(outputs, list) or not outputs or any(not isinstance(x, str) for x in outputs):
        raise ParameterizedSkillError("STEP_OUTPUTS_INVALID")

    by_prefix: dict[str, str] = {}
    for raw in inputs:
        for prefix in (
            "VERIFIER::",
            "ACTION_CONTRACT_SHA256::",
            "ACCEPTED_PROPOSAL_BASE64::",
        ):
            if raw.startswith(prefix):
                if prefix in by_prefix:
                    raise ParameterizedSkillError("STEP_INPUT_PREFIX_DUPLICATE:" + prefix)
                by_prefix[prefix] = raw[len(prefix):]
                break

    required = {
        "VERIFIER::",
        "ACTION_CONTRACT_SHA256::",
        "ACCEPTED_PROPOSAL_BASE64::",
    }
    if set(by_prefix) != required:
        raise ParameterizedSkillError("STEP_REQUIRED_EXACT_SEMANTICS_INPUTS_MISSING")
    action_sha = by_prefix["ACTION_CONTRACT_SHA256::"]
    if len(action_sha) != 64:
        raise ParameterizedSkillError("ACTION_CONTRACT_SHA256_INVALID")
    try:
        proposal_raw = base64.b64decode(
            by_prefix["ACCEPTED_PROPOSAL_BASE64::"].encode("ascii"),
            validate=True,
        )
        proposal = json.loads(proposal_raw.decode("utf-8"))
    except Exception as exc:
        raise ParameterizedSkillError("ACCEPTED_PROPOSAL_DECODE_FAILED") from exc
    if not isinstance(proposal, Mapping):
        raise ParameterizedSkillError("ACCEPTED_PROPOSAL_NOT_OBJECT")

    extra_inputs = sorted(
        x for x in inputs
        if not any(
            x.startswith(prefix)
            for prefix in (
                "VERIFIER::",
                "ACTION_CONTRACT_SHA256::",
                "ACCEPTED_PROPOSAL_BASE64::",
            )
        )
    )
    return {
        "op": op,
        "verifier_id": by_prefix["VERIFIER::"],
        "action_contract_sha256": action_sha,
        "proposal": dict(proposal),
        "outputs": list(outputs),
        "extra_inputs": extra_inputs,
    }


def _slot_name(path: tuple[Any, ...], index: int) -> str:
    path_text = "/".join(str(x) for x in path) or "root"
    short = sha256(path_text.encode("utf-8")).hexdigest()[:8]
    return f"slot_{index}_{short}"


def _anti_unify(
    values: Sequence[Any],
    *,
    path: tuple[Any, ...],
    slots: list[dict[str, Any]],
) -> Any:
    if not values:
        raise ParameterizedSkillError("ANTI_UNIFY_VALUES_EMPTY")
    canonical = [_canon(x) for x in values]
    if len(set(canonical)) == 1:
        return values[0]

    kinds = [_json_type(x) for x in values]
    if len(set(kinds)) != 1:
        raise ParameterizedSkillError(
            "PARAMETER_TYPE_DRIFT_AT:" + "/".join(map(str, path))
        )
    kind = kinds[0]

    if kind == "object":
        key_sets = [set(x) for x in values]
        if any(keys != key_sets[0] for keys in key_sets[1:]):
            raise ParameterizedSkillError(
                "PARAMETER_OBJECT_STRUCTURE_DRIFT_AT:" + "/".join(map(str, path))
            )
        return {
            key: _anti_unify(
                [x[key] for x in values],
                path=path + (key,),
                slots=slots,
            )
            for key in sorted(key_sets[0])
        }

    if kind == "array":
        lengths = {len(x) for x in values}
        if len(lengths) != 1:
            raise ParameterizedSkillError(
                "PARAMETER_ARRAY_LENGTH_DRIFT_AT:" + "/".join(map(str, path))
            )
        n = next(iter(lengths))
        return [
            _anti_unify(
                [x[i] for x in values],
                path=path + (i,),
                slots=slots,
            )
            for i in range(n)
        ]

    slot = _slot_name(path, len(slots))
    observed = sorted(set(canonical))
    slots.append({
        "slot_id": slot,
        "json_path": list(path),
        "json_type": kind,
        "observed_value_count": len(observed),
        "observed_values_sha256": sha256(
            ("\n".join(observed)).encode("utf-8")
        ).hexdigest(),
        "domain_proved": False,
    })
    return {"$slot": slot}


def induce_parameterized_candidate(
    verified_episodes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if (
        not isinstance(verified_episodes, Sequence)
        or isinstance(verified_episodes, (str, bytes))
        or len(verified_episodes) < 2
    ):
        raise ParameterizedSkillError("AT_LEAST_TWO_VERIFIED_EPISODES_REQUIRED")

    eps = [_verified_episode(x) for x in verified_episodes]
    ids = [x["episode_id"] for x in eps]
    if len(ids) != len(set(ids)):
        raise ParameterizedSkillError("EPISODE_ID_DUPLICATE")
    scopes = {x["scope_id"] for x in eps}
    if len(scopes) != 1:
        raise ParameterizedSkillError("EPISODE_SCOPE_MISMATCH")
    step_counts = {len(x["steps"]) for x in eps}
    if len(step_counts) != 1:
        raise ParameterizedSkillError("EPISODE_STEP_COUNT_MISMATCH")

    templates = []
    slots: list[dict[str, Any]] = []
    for i in range(next(iter(step_counts))):
        rows = [_step_parts(ep["steps"][i]) for ep in eps]
        invariant_keys = (
            "op",
            "verifier_id",
            "action_contract_sha256",
            "outputs",
            "extra_inputs",
        )
        for key in invariant_keys:
            vals = [_canon(row[key]) for row in rows]
            if len(set(vals)) != 1:
                raise ParameterizedSkillError(
                    "STEP_INVARIANT_DRIFT:" + str(i) + ":" + key
                )

        template_proposal = _anti_unify(
            [row["proposal"] for row in rows],
            path=("steps", i, "proposal"),
            slots=slots,
        )
        templates.append({
            "index": i,
            "op": rows[0]["op"],
            "verifier_id": rows[0]["verifier_id"],
            "action_contract_sha256": rows[0]["action_contract_sha256"],
            "proposal_template": template_proposal,
            "outputs": rows[0]["outputs"],
            "extra_inputs": rows[0]["extra_inputs"],
        })

    if not slots:
        raise ParameterizedSkillError(
            "NO_PARAMETER_VARIATION__USE_EXACT_EXECUTABLE_SKILL_INDUCTION"
        )

    core = {
        "scope_id": next(iter(scopes)),
        "source_episode_ids": sorted(ids),
        "steps": templates,
        "parameter_slots": slots,
        "parameterization_rule": "ONLY_VARYING_SCALAR_JSON_LEAVES__STRUCTURE_AND_ACTION_CONTRACT_FIXED",
    }
    return {
        "schema": SCHEMA,
        "status": "PARAMETERIZED_SKILL_CANDIDATE_ONLY",
        **core,
        "candidate_sha256": _sha(core),
        "verified_skill": False,
        "reuse_authorized": False,
        "parameter_domain_proved": False,
        "behavior_preservation_proved": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "required_before_reuse": [
            "INDEPENDENT_CONTENT_ADDRESSED_PARAMETER_DOMAIN_CERTIFICATE",
            "INDEPENDENT_BEHAVIOR_PRESERVATION_PROOF_FOR_ALL_ADMISSIBLE_PARAMETERS",
            "EXACT_TEMPLATE_AND_INSTANTIATION_RUNTIME_BYTE_BINDING",
        ],
    }


def instantiate_candidate(
    candidate: Mapping[str, Any],
    parameters: Mapping[str, Any],
) -> dict[str, Any]:
    """Materialize a candidate instance for testing only.

    This function intentionally never grants execution or reuse authority.
    """
    if candidate.get("schema") != SCHEMA:
        raise ParameterizedSkillError("CANDIDATE_SCHEMA_INVALID")
    if candidate.get("status") != "PARAMETERIZED_SKILL_CANDIDATE_ONLY":
        raise ParameterizedSkillError("CANDIDATE_STATUS_INVALID")
    slots = candidate.get("parameter_slots")
    if not isinstance(slots, list) or not slots:
        raise ParameterizedSkillError("PARAMETER_SLOTS_INVALID")
    expected = {row["slot_id"] for row in slots if isinstance(row, Mapping)}
    if set(parameters) != expected:
        raise ParameterizedSkillError("PARAMETER_SET_MISMATCH")
    slot_types = {
        row["slot_id"]: row["json_type"]
        for row in slots
        if isinstance(row, Mapping)
    }
    for sid, value in parameters.items():
        if _json_type(value) != slot_types[sid]:
            raise ParameterizedSkillError("PARAMETER_TYPE_MISMATCH:" + sid)

    def sub(value: Any) -> Any:
        if isinstance(value, Mapping):
            if set(value) == {"$slot"}:
                sid = value["$slot"]
                if sid not in parameters:
                    raise ParameterizedSkillError("PARAMETER_MISSING:" + str(sid))
                return parameters[sid]
            return {k: sub(v) for k, v in value.items()}
        if isinstance(value, list):
            return [sub(x) for x in value]
        return value

    instantiated_steps = []
    for step in candidate["steps"]:
        instantiated_steps.append({
            "index": step["index"],
            "op": step["op"],
            "verifier_id": step["verifier_id"],
            "action_contract_sha256": step["action_contract_sha256"],
            "proposal": sub(step["proposal_template"]),
            "outputs": step["outputs"],
            "extra_inputs": step["extra_inputs"],
        })
    return {
        "schema": SCHEMA,
        "status": "PARAMETERIZED_SKILL_INSTANCE_CANDIDATE_ONLY",
        "candidate_sha256": candidate.get("candidate_sha256"),
        "parameters": dict(parameters),
        "steps": instantiated_steps,
        "reuse_authorized": False,
        "execution_authority": False,
        "terminal_authority": False,
    }

"""Independent read-only verifier for compiled-bound success episodes.

The verifier does not replay effects. It reauthenticates the exact controller
checkpoint, current promoted registry binding, embedded one-capability trace proof,
composition capsule head, and durable artifact hashes. Only then may R3 treat the
historical success as a verified episode.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import astra_runtime
from canonical.runtime import verified_bound_capability_execution_adapter_v1 as bound_adapter
from canonical.runtime.bound_capability_execution_verifier_v1 import verify as verify_bound_execution
from canonical.runtime.executable_skill_program_v7 import program_digest
from canonical.runtime.r3_bound_success_adapter_v1 import VERIFICATION_KIND

SCHEMA = "PROJECT_BRAIN_R3_BOUND_SUCCESS_CHECKPOINT_VERIFIER_V1"


class BoundSuccessVerificationError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str)


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _items(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise BoundSuccessVerificationError("STRING_SEQUENCE_REQUIRED")
    out: list[str] = []
    for raw in value:
        item = str(raw or "").strip()
        if not item:
            raise BoundSuccessVerificationError("STRING_SEQUENCE_ITEM_INVALID")
        if item not in out:
            out.append(item)
    return out


def _safe_file(root: Path, relative: str) -> Path:
    rel = Path(str(relative or "").strip())
    if not rel.as_posix() or rel.is_absolute():
        raise BoundSuccessVerificationError("REPOSITORY_PATH_INVALID")
    target = (root / rel).resolve(strict=True)
    target.relative_to(root)
    if not target.is_file():
        raise BoundSuccessVerificationError("REPOSITORY_FILE_REQUIRED")
    return target


def _reverify_hashed_artifact(inner: Mapping[str, Any], root: Path) -> bool:
    pairs = (
        ("output_path", "output_sha256"),
        ("screenshot_path", "screenshot_sha256"),
        ("xlsx_path", "xlsx_sha256"),
    )
    observed = 0
    for path_key, hash_key in pairs:
        raw_path = inner.get(path_key)
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        expected = inner.get(hash_key)
        if not isinstance(expected, str) or len(expected) != 64:
            raise BoundSuccessVerificationError("DURABLE_ARTIFACT_HASH_REQUIRED:" + path_key)
        artifact = _safe_file(root, raw_path)
        actual = sha256(artifact.read_bytes()).hexdigest()
        if actual != expected:
            raise BoundSuccessVerificationError("DURABLE_ARTIFACT_HASH_MISMATCH:" + path_key)
        observed += 1
    if observed < 1:
        raise BoundSuccessVerificationError("NO_HASHED_DURABLE_ARTIFACT_TO_REVERIFY")
    return True


def _lineage_heads(
    *,
    initial_facts: Sequence[str],
    target_effects: Sequence[str],
    steps: Sequence[Mapping[str, Any]],
    trace: Sequence[Mapping[str, Any]],
) -> tuple[str, str]:
    return (
        _sha({
            "schema": "PROJECT_BRAIN_BOUND_SUCCESS_FACT_LINEAGE_V1",
            "initial_facts": list(initial_facts),
            "target_effects": list(target_effects),
            "steps": [dict(x) for x in steps],
        }),
        _sha({
            "schema": "PROJECT_BRAIN_BOUND_SUCCESS_VALUE_LINEAGE_V1",
            "results": [
                {
                    "capability_id": row.get("capability_id"),
                    "result_sha256": row.get("result_sha256"),
                    "composition_capsule_head_hash": row.get("composition_capsule_head_hash"),
                }
                for row in trace
            ],
        }),
    )


def verify_material(
    *,
    problem: Mapping[str, Any],
    episode: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
    fact_capsule_head_hash: str,
    value_capsule_head_hash: str,
    repo_root: str | Path,
) -> dict[str, Any]:
    try:
        if problem.get("verification_kind") != VERIFICATION_KIND:
            raise BoundSuccessVerificationError("VERIFICATION_KIND_INVALID")
        root = Path(repo_root).resolve(strict=True)
        checkpoint = _safe_file(root, str(problem.get("checkpoint_path") or ""))
        raw_checkpoint = checkpoint.read_bytes()
        if sha256(raw_checkpoint).hexdigest() != problem.get("checkpoint_sha256"):
            raise BoundSuccessVerificationError("CHECKPOINT_SHA256_MISMATCH")
        doc = json.loads(raw_checkpoint.decode("utf-8"))
        if (
            not isinstance(doc, Mapping)
            or doc.get("schema") != "PROJECT_BRAIN_CONTROLLER_CHECKPOINT_V1"
            or doc.get("status") != "COMPLETE"
        ):
            raise BoundSuccessVerificationError("CHECKPOINT_NOT_COMPLETE")
        if doc.get("plan_sha256") != problem.get("controller_plan_sha256"):
            raise BoundSuccessVerificationError("CHECKPOINT_PLAN_SHA_MISMATCH")
        completed = doc.get("completed_actions")
        selected = _items(problem.get("selected_plan"))
        if not isinstance(completed, list) or len(completed) != len(selected) + 1:
            raise BoundSuccessVerificationError("CHECKPOINT_ACTION_COUNT_MISMATCH")
        plans = []
        for raw in completed:
            if not isinstance(raw, Mapping) or not isinstance(raw.get("plan"), Mapping):
                raise BoundSuccessVerificationError("CHECKPOINT_RECORD_INVALID")
            plans.append(deepcopy(dict(raw["plan"])))
        if astra_runtime._controller_plan_sha256(plans) != problem.get("controller_plan_sha256"):
            raise BoundSuccessVerificationError("CHECKPOINT_PLAN_RECOMPUTATION_MISMATCH")
        if plans[-1].get("type") != "finish":
            raise BoundSuccessVerificationError("CHECKPOINT_FINISH_MISSING")

        compiled = problem.get("compiled_request")
        if not isinstance(compiled, Mapping):
            raise BoundSuccessVerificationError("COMPILED_REQUEST_MISSING")
        initial_facts = _items(compiled.get("initial_facts", []))
        target_effects = _items(compiled.get("target_effects"))
        if initial_facts != _items(problem.get("initial_facts", [])):
            raise BoundSuccessVerificationError("INITIAL_FACT_BINDING_MISMATCH")
        if target_effects != _items(problem.get("target_effects")):
            raise BoundSuccessVerificationError("TARGET_EFFECT_BINDING_MISMATCH")

        expected_steps: list[dict[str, Any]] = []
        expected_trace: list[dict[str, Any]] = []
        for index, cid in enumerate(selected):
            record = completed[index]
            if astra_runtime._controller_checkpoint_record_valid(record) is not True:
                raise BoundSuccessVerificationError("CHECKPOINT_RECORD_READBACK_INVALID:" + cid)
            plan = record["plan"]
            result = record.get("result")
            if plan.get("type") != "invoke_verified_bound_capability_adapter":
                raise BoundSuccessVerificationError("CHECKPOINT_ACTION_TYPE_INVALID:" + cid)
            args = plan.get("args")
            if not isinstance(args, Mapping) or str(args.get("capability_id") or "") != cid:
                raise BoundSuccessVerificationError("CHECKPOINT_CAPABILITY_ID_MISMATCH:" + cid)
            if not isinstance(result, Mapping) or result.get("pass") is not True:
                raise BoundSuccessVerificationError("BOUND_RESULT_NOT_PASSING:" + cid)

            prepared = bound_adapter.prepare(
                cid,
                inputs=dict(args.get("inputs") or {}),
                instance_id=str(args.get("instance_id") or cid),
                requires=list(args.get("requires") or []),
                provides=list(args.get("provides") or []),
                result_fields=list(args.get("result_fields") or []),
            )
            for key in (
                "inputs_sha256",
                "registry_file_sha256",
                "registry_entry_sha256",
                "rendered_action_sha256",
            ):
                if result.get(key) != prepared.get(key):
                    raise BoundSuccessVerificationError("BOUND_PREPARATION_DIGEST_MISMATCH:" + cid + ":" + key)
            if result.get("rendered_action") != prepared.get("rendered_action"):
                raise BoundSuccessVerificationError("BOUND_RENDERED_ACTION_MISMATCH:" + cid)
            inner = result.get("result")
            if not isinstance(inner, Mapping):
                raise BoundSuccessVerificationError("BOUND_INNER_RESULT_INVALID:" + cid)
            if _sha(inner) != result.get("result_sha256"):
                raise BoundSuccessVerificationError("BOUND_RESULT_DIGEST_MISMATCH:" + cid)
            _reverify_hashed_artifact(inner, root)

            inspected = bound_adapter.inspect(cid)
            entry = inspected.get("entry")
            if not isinstance(entry, Mapping):
                raise BoundSuccessVerificationError("BOUND_REGISTRY_ENTRY_INVALID:" + cid)
            one_problem = {
                "initial_facts": list(prepared["requires"]),
                "target_effects": list(prepared["provides"]),
                "capabilities": [{
                    "id": prepared["instance_id"],
                    "requires": list(prepared["requires"]),
                    "provides": list(prepared["provides"]),
                    "cost": float(entry.get("cost", 1)),
                    "action": deepcopy(dict(prepared["rendered_action"])),
                    "result_fields": list(prepared["result_fields"]),
                }],
                "finish_summary": "verified promoted bound capability execution",
            }
            execution_trace = result.get("execution_trace")
            if not isinstance(execution_trace, Mapping):
                raise BoundSuccessVerificationError("BOUND_EXECUTION_TRACE_MISSING:" + cid)
            verdict = verify_bound_execution(
                {"problem": one_problem},
                {"execution": deepcopy(dict(execution_trace))},
            )
            if verdict.get("pass") is not True:
                raise BoundSuccessVerificationError("BOUND_TRACE_REVERIFICATION_FAILED:" + cid)
            head = (verdict.get("verified_output") or {}).get("capsule_head_hash")
            if head != result.get("composition_capsule_head_hash"):
                raise BoundSuccessVerificationError("BOUND_COMPOSITION_HEAD_MISMATCH:" + cid)

            requires = list(prepared["requires"])
            provides = list(prepared["provides"])
            expected_steps.append({
                "index": index,
                "op": cid,
                "inputs": requires,
                "outputs": provides,
            })
            expected_trace.append({
                "cycle": index,
                "capability_id": cid,
                "requires": requires,
                "provides": provides,
                "result_sha256": result["result_sha256"],
                "composition_capsule_head_hash": result["composition_capsule_head_hash"],
                "effect_outcome_sha256": result["result_sha256"],
            })

        if [dict(x) for x in trace] != expected_trace:
            raise BoundSuccessVerificationError("EPISODE_TRACE_MISMATCH")
        if list(episode.get("steps") or []) != expected_steps:
            raise BoundSuccessVerificationError("EPISODE_STEPS_MISMATCH")
        if list(episode.get("preconditions") or []) != initial_facts:
            raise BoundSuccessVerificationError("EPISODE_PRECONDITIONS_MISMATCH")
        if list(episode.get("postconditions") or []) != target_effects:
            raise BoundSuccessVerificationError("EPISODE_POSTCONDITIONS_MISMATCH")
        if list(episode.get("invalidators") or []):
            raise BoundSuccessVerificationError("BOUND_SUCCESS_INVALIDATORS_UNSUPPORTED")
        expected_program = program_digest(
            steps=expected_steps,
            preconditions=initial_facts,
            postconditions=target_effects,
            invalidators=[],
        )
        if episode.get("program_sha256") != expected_program:
            raise BoundSuccessVerificationError("EPISODE_PROGRAM_DIGEST_MISMATCH")
        fact_head, value_head = _lineage_heads(
            initial_facts=initial_facts,
            target_effects=target_effects,
            steps=expected_steps,
            trace=expected_trace,
        )
        if fact_capsule_head_hash != fact_head:
            raise BoundSuccessVerificationError("FACT_LINEAGE_HEAD_MISMATCH")
        if value_capsule_head_hash != value_head:
            raise BoundSuccessVerificationError("VALUE_LINEAGE_HEAD_MISMATCH")

        return {
            "schema": SCHEMA,
            "status": "PASS__BOUND_SUCCESS_CHECKPOINT_REVERIFIED_READ_ONLY",
            "pass": True,
            "checkpoint_sha256": problem.get("checkpoint_sha256"),
            "step_count": len(expected_steps),
            "effect_outcomes_reverified": True,
            "state_lineage_reverified": True,
            "trace_reverified": True,
            "execution_replayed": False,
            "verification_basis": "BOUND_CONTROLLER_CHECKPOINT_AND_DURABLE_ARTIFACT_READBACK_V1",
            "terminal_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "execution_replayed": False,
            "terminal_authority": False,
        }

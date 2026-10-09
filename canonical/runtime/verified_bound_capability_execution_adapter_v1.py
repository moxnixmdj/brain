"""Execute one promoted verified Brain capability and reverify its trace.

This adapter closes the execution gap between:
- BOUND_CAPABILITY_REGISTRY_V1 promoted capabilities; and
- the universal solver's verified capability semantics.

Authority rules:
- registry entry must exist and status == VERIFIED_BOUND_CAPABILITY;
- incremental spend must be exactly zero;
- caller inputs may only instantiate the frozen registry action template;
- execution delegates to Astra's existing content-addressed dependency loader and
  bound adapter invocation;
- the rendered action's declared expectation must pass;
- the exact execution is then independently rechecked by
  BOUND_CAPABILITY_EXECUTION_V1 over a one-capability deterministic plan.

The adapter returns the concrete result plus content digests for the registry,
entry, rendered action, and verified composition capsule. It does not decide what
higher-level semantic effect this capability should mean in an arbitrary task;
the universal solver must still authenticate that mapping separately.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import json
import importlib.util
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping

from canonical.runtime import astra_runtime
from canonical.runtime.bound_capability_execution_verifier_v1 import verify as verify_execution
from canonical.runtime.capability_planner import plan_actions

SCHEMA = "PROJECT_BRAIN_VERIFIED_BOUND_CAPABILITY_EXECUTION_ADAPTER_V1"
ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"


class BoundExecutionError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _load_registry() -> tuple[bytes, Mapping[str, Any], Mapping[str, Any]]:
    raw = REGISTRY_PATH.read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    if not isinstance(doc, Mapping) or doc.get("schema") != "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1":
        raise BoundExecutionError("BOUND_CAPABILITY_REGISTRY_INVALID")
    caps = doc.get("capabilities")
    if not isinstance(caps, Mapping):
        raise BoundExecutionError("BOUND_CAPABILITY_REGISTRY_CAPABILITIES_INVALID")
    return raw, doc, caps


def inspect(capability_id: str) -> dict[str, Any]:
    cid = str(capability_id or "").strip()
    if not cid:
        raise BoundExecutionError("CAPABILITY_ID_REQUIRED")
    raw, _, caps = _load_registry()
    entry = caps.get(cid)
    if not isinstance(entry, Mapping):
        raise BoundExecutionError("BOUND_CAPABILITY_UNKNOWN:" + cid)
    if entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise BoundExecutionError("BOUND_CAPABILITY_NOT_VERIFIED:" + cid)
    if float(entry.get("incremental_spend_usd", 0)) != 0:
        raise BoundExecutionError("BOUND_CAPABILITY_NONZERO_COST:" + cid)
    verification = entry.get("verification")
    if not isinstance(verification, Mapping) or not verification:
        raise BoundExecutionError("BOUND_CAPABILITY_VERIFICATION_MISSING:" + cid)
    independently_verified = (
        verification.get("independent_verified") is True
        or isinstance(verification.get("independently_verified_by"), str)
        or verification.get("producer_independent") is True
    )
    if not independently_verified:
        raise BoundExecutionError("BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT:" + cid)
    action_template = entry.get("action_template")
    if not isinstance(action_template, Mapping) or action_template.get("type") != "invoke_capability":
        raise BoundExecutionError("BOUND_CAPABILITY_ACTION_TEMPLATE_INVALID:" + cid)
    return {
        "capability_id": cid,
        "entry": deepcopy(dict(entry)),
        "registry_file_sha256": sha256(raw).hexdigest(),
        "registry_entry_sha256": _sha(entry),
    }


def prepare(
    capability_id: str,
    *,
    inputs: Mapping[str, Any],
    instance_id: str | None = None,
    requires: list[str] | None = None,
    provides: list[str] | None = None,
    result_fields: list[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(inputs, Mapping):
        raise BoundExecutionError("INPUTS_NOT_OBJECT")
    inspected = inspect(capability_id)
    cid = inspected["capability_id"]
    entry = inspected["entry"]
    template = entry["action_template"]
    try:
        rendered = astra_runtime._render_bound_template(template, dict(inputs))
    except Exception as exc:
        raise BoundExecutionError(
            "BOUND_TEMPLATE_RENDER_FAILED:" + type(exc).__name__ + ":" + str(exc)
        ) from exc
    if not isinstance(rendered, Mapping) or rendered.get("type") != "invoke_capability":
        raise BoundExecutionError("RENDERED_BOUND_ACTION_INVALID")
    args = rendered.get("args")
    if not isinstance(args, Mapping) or args.get("capability_id") != cid:
        raise BoundExecutionError("RENDERED_BOUND_ACTION_CAPABILITY_ID_MISMATCH")

    iid = str(instance_id or cid).strip()
    if not iid:
        raise BoundExecutionError("INSTANCE_ID_INVALID")
    req = list(entry.get("requires") or []) if requires is None else list(requires)
    prov = list(entry.get("provides") or []) if provides is None else list(provides)
    fields = list(entry.get("result_fields") or []) if result_fields is None else list(result_fields)
    if not prov:
        raise BoundExecutionError("INSTANCE_PROVIDES_EMPTY")
    return {
        "schema": SCHEMA,
        "status": "PREPARED__PROMOTED_BOUND_CAPABILITY",
        "capability_id": cid,
        "instance_id": iid,
        "requires": req,
        "provides": prov,
        "result_fields": fields,
        "inputs": deepcopy(dict(inputs)),
        "inputs_sha256": _sha(inputs),
        "registry_file_sha256": inspected["registry_file_sha256"],
        "registry_entry_sha256": inspected["registry_entry_sha256"],
        "_frozen_entry": deepcopy(dict(entry)),
        "rendered_action": deepcopy(dict(rendered)),
        "rendered_action_sha256": _sha(rendered),
        "incremental_spend_usd": 0,
        "execution_authority": False,
        "terminal_authority": False,
    }



def _git_blob_sha(raw: bytes) -> str:
    return sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _invoke_frozen_bound_capability(
    entry: Mapping[str, Any],
    args: Mapping[str, Any],
    *,
    expected_adapter_git_blob_sha: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Invoke from one frozen registry entry and one frozen adapter byte buffer."""
    if not isinstance(entry, Mapping):
        raise BoundExecutionError("FROZEN_ENTRY_NOT_OBJECT")
    source = entry.get("source") or {}
    if not isinstance(source, Mapping):
        raise BoundExecutionError("FROZEN_ENTRY_SOURCE_INVALID")

    call_args = dict(args)
    call_args.pop("capability_id", None)
    dependency = None
    source_type = str(source.get("type") or "").strip()
    if source_type == "pypi":
        dependency = astra_runtime._ensure_pypi_dependency(source)
    elif source_type == "npm":
        dependency = astra_runtime._ensure_npm_dependency(source)
        call_args["_package_root"] = dependency.get("package_root")
    elif source_type == "apt":
        dependency = astra_runtime._ensure_apt_dependencies(source)
    elif source_type == "git_source_tree":
        dependency = astra_runtime._ensure_git_source_tree_dependency(source)
        call_args["_source_root"] = dependency.get("source_root")
    elif source_type in {"python_stdlib", "system_tool"}:
        dependency = astra_runtime._ensure_local_dependency(source)
    elif source_type:
        raise BoundExecutionError("BOUND_CAPABILITY_SOURCE_UNSUPPORTED:" + source_type)

    module_name = str(entry.get("adapter_module") or "")
    if (
        not module_name
        or any(
            ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
            for ch in module_name
        )
    ):
        raise BoundExecutionError("BOUND_CAPABILITY_ADAPTER_INVALID")
    source_path = (
        ROOT / "canonical" / "runtime" / "bound_capabilities" / (module_name + ".py")
    )
    if not source_path.is_file():
        raise BoundExecutionError("BOUND_CAPABILITY_ADAPTER_MISSING")

    raw = source_path.read_bytes()
    adapter_git_blob_sha = _git_blob_sha(raw)
    if (
        expected_adapter_git_blob_sha is not None
        and adapter_git_blob_sha != str(expected_adapter_git_blob_sha).lower()
    ):
        raise BoundExecutionError("BOUND_CAPABILITY_ADAPTER_BLOB_MISMATCH")

    with tempfile.TemporaryDirectory(prefix="brain-bound-adapter-") as td:
        frozen_path = Path(td) / (module_name + ".py")
        frozen_path.write_bytes(raw)
        if _git_blob_sha(frozen_path.read_bytes()) != adapter_git_blob_sha:
            raise BoundExecutionError("BOUND_CAPABILITY_ADAPTER_FROZEN_COPY_MISMATCH")
        full_name = "project_brain_frozen_bound_" + module_name
        spec = importlib.util.spec_from_file_location(full_name, frozen_path)
        if spec is None or spec.loader is None:
            raise BoundExecutionError("BOUND_CAPABILITY_ADAPTER_LOAD_FAILED")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        fn = getattr(module, str(entry.get("entrypoint") or "run"), None)
        if not callable(fn):
            raise BoundExecutionError("BOUND_CAPABILITY_ENTRYPOINT_MISSING")
        result = fn(call_args, ROOT)

    if not isinstance(result, dict):
        raise BoundExecutionError("BOUND_CAPABILITY_RESULT_INVALID")
    result.setdefault("capability_id", str(args.get("capability_id") or ""))
    result["dependency"] = dependency
    return result, adapter_git_blob_sha


def execute(
    capability_id: str,
    *,
    inputs: Mapping[str, Any],
    instance_id: str | None = None,
    requires: list[str] | None = None,
    provides: list[str] | None = None,
    result_fields: list[str] | None = None,
    expected_registry_file_sha256: str | None = None,
    expected_registry_entry_sha256: str | None = None,
    expected_rendered_action_sha256: str | None = None,
) -> dict[str, Any]:
    try:
        prepared = prepare(
            capability_id,
            inputs=inputs,
            instance_id=instance_id,
            requires=requires,
            provides=provides,
            result_fields=result_fields,
        )
        cid = prepared["capability_id"]
        inspected = inspect(cid)
        entry = inspected["entry"]
        rendered = prepared["rendered_action"]
        args = rendered["args"]

        if (
            expected_registry_file_sha256 is not None
            and prepared["registry_file_sha256"] != expected_registry_file_sha256
        ):
            raise BoundExecutionError("REGISTRY_FILE_CHANGED_AFTER_PREPARATION")
        if (
            expected_registry_entry_sha256 is not None
            and prepared["registry_entry_sha256"] != expected_registry_entry_sha256
        ):
            raise BoundExecutionError("REGISTRY_ENTRY_CHANGED_AFTER_PREPARATION")
        if (
            expected_rendered_action_sha256 is not None
            and prepared["rendered_action_sha256"] != expected_rendered_action_sha256
        ):
            raise BoundExecutionError("RENDERED_ACTION_CHANGED_AFTER_PREPARATION")

        result = astra_runtime._invoke_bound_capability(dict(args))
        if not isinstance(result, Mapping):
            raise BoundExecutionError("BOUND_CAPABILITY_RESULT_INVALID")
        astra_runtime._verify_action_expectation(rendered, result)

        iid = prepared["instance_id"]
        req = list(prepared["requires"])
        prov = list(prepared["provides"])
        declared_result_fields = list(prepared["result_fields"])

        problem = {
            "initial_facts": list(req),
            "target_effects": list(prov),
            "capabilities": [{
                "id": iid,
                "requires": list(req),
                "provides": list(prov),
                "cost": float(entry.get("cost", 1)),
                "action": deepcopy(dict(rendered)),
                "result_fields": declared_result_fields,
            }],
            "finish_summary": "verified promoted bound capability execution",
        }
        planned = plan_actions(problem)
        actions = planned["actions"]
        if len(actions) != 2:
            raise BoundExecutionError("SINGLE_CAPABILITY_PLAN_ACTION_COUNT_INVALID")
        execution = {
            "trace": [
                {"cycle": 0, "plan": deepcopy(actions[0]), "result": deepcopy(dict(result))},
                {
                    "cycle": 1,
                    "plan": deepcopy(actions[1]),
                    "result": {"summary": "verified promoted bound capability execution"},
                },
            ]
        }
        verdict = verify_execution(
            {"problem": problem},
            {"execution": execution},
        )
        if verdict.get("pass") is not True:
            raise BoundExecutionError(
                "BOUND_CAPABILITY_EXECUTION_TRACE_NOT_VERIFIED:"
                + str(verdict.get("reason"))
            )

        return {
            "schema": SCHEMA,
            "status": "PASS__PROMOTED_BOUND_CAPABILITY_EXECUTED_AND_TRACE_VERIFIED",
            "pass": True,
            "capability_id": cid,
            "instance_id": iid,
            "requires": list(req),
            "provides": list(prov),
            "result_fields": declared_result_fields,
            "inputs_sha256": prepared["inputs_sha256"],
            "registry_file_sha256": prepared["registry_file_sha256"],
            "registry_entry_sha256": prepared["registry_entry_sha256"],
            "rendered_action_sha256": prepared["rendered_action_sha256"],
            "rendered_action": deepcopy(dict(rendered)),
            "result_sha256": _sha(result),
            "result": deepcopy(dict(result)),
            "execution_trace": execution,
            "execution_verification": verdict,
            "composition_capsule_head_hash": (
                verdict.get("verified_output") or {}
            ).get("capsule_head_hash"),
            "incremental_spend_usd": 0,
            "search_or_pending_binding_execution_allowed": False,
            "terminal_authority": False,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "semantic_boundary": (
                "PROVES_EXECUTION_OF_THE_PROMOTED_REGISTRY_CONTRACT_AND_DECLARED_EXPECTATION;"
                "HIGHER_LEVEL_TASK_EFFECT_MEANING_REQUIRES_SEPARATE_AUTHENTICATION"
            ),
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_authority": False,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }

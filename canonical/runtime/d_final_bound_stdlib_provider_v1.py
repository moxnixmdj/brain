"""Minimal D-final provider for sealed Python-stdlib bound capabilities V1.

This is deliberately narrower than the general Astra bound-capability loader.
It exists to make D-final ownership proofs small and explicit.

Scope:
- only registry rows with source.type == "python_stdlib";
- exact registry bytes may be pinned by caller;
- exact registry-entry hash may be pinned by caller;
- exact adapter Git blob must be supplied and checked before import;
- frozen action template is rendered locally;
- adapter result must satisfy the frozen expectation;
- deterministic plan/trace is reverified by the independent bound execution verifier.

It does not install packages, use network discovery, invoke shell tools, or grant
semantic meaning beyond the promoted registry contract.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256, sha1
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping

from canonical.runtime.bound_capability_execution_verifier_v1 import verify as verify_execution
from canonical.runtime.capability_planner import plan_actions

SCHEMA="PROJECT_BRAIN_D_FINAL_BOUND_STDLIB_PROVIDER_V1"


class DFinalBoundProviderError(ValueError):
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


def _git_blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _render(value: Any, inputs: Mapping[str, Any]) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _render(v, inputs) for k, v in value.items()}
    if isinstance(value, list):
        return [_render(v, inputs) for v in value]
    if isinstance(value, str):
        if value.startswith("${input.") and value.endswith("}") and value.count("${")==1:
            key=value[len("${input."):-1]
            if key not in inputs:
                raise DFinalBoundProviderError("BOUND_CAPABILITY_INPUT_MISSING:" + key)
            return deepcopy(inputs[key])
        out=value
        for key, val in inputs.items():
            out=out.replace("${input."+str(key)+"}",str(val))
        if "${input." in out:
            raise DFinalBoundProviderError("BOUND_CAPABILITY_INPUT_MISSING")
        return out
    return deepcopy(value)


def _verify_expectation(action: Mapping[str, Any], result: Mapping[str, Any]) -> None:
    expect=action.get("expect")
    if expect is None:
        return
    if not isinstance(expect, Mapping):
        raise DFinalBoundProviderError("ACTION_EXPECTATION_INVALID")
    field=str(expect.get("field") or "").strip()
    if not field:
        raise DFinalBoundProviderError("ACTION_EXPECTATION_FIELD_REQUIRED")
    value=result.get(field)
    typ=str(expect.get("type") or "field_nonempty")
    if typ=="field_nonempty":
        ok=value not in (None,"",[],{})
    elif typ=="field_contains":
        ok=str(expect.get("value","")) in str(value or "")
    elif typ=="field_equals":
        ok=value==expect.get("value")
    else:
        raise DFinalBoundProviderError("ACTION_EXPECTATION_TYPE_UNKNOWN:"+typ)
    if not ok:
        raise DFinalBoundProviderError("ACTION_EXPECTATION_FAILED:"+field)


def _load_registry(path: Path) -> tuple[bytes, Mapping[str, Any], Mapping[str, Any]]:
    raw=path.read_bytes()
    doc=json.loads(raw.decode("utf-8"))
    if not isinstance(doc, Mapping) or doc.get("schema")!="PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1":
        raise DFinalBoundProviderError("BOUND_CAPABILITY_REGISTRY_INVALID")
    caps=doc.get("capabilities")
    if not isinstance(caps, Mapping):
        raise DFinalBoundProviderError("BOUND_CAPABILITY_REGISTRY_CAPABILITIES_INVALID")
    return raw, doc, caps


def inspect(
    capability_id: str,
    *,
    registry_path: str | Path,
    expected_registry_file_sha256: str | None = None,
    expected_registry_entry_sha256: str | None = None,
) -> dict[str, Any]:
    cid=str(capability_id or "").strip()
    if not cid:
        raise DFinalBoundProviderError("CAPABILITY_ID_REQUIRED")
    raw, _, caps=_load_registry(Path(registry_path))
    registry_sha=sha256(raw).hexdigest()
    if expected_registry_file_sha256 is not None and registry_sha!=expected_registry_file_sha256:
        raise DFinalBoundProviderError("REGISTRY_FILE_SHA256_MISMATCH")
    entry=caps.get(cid)
    if not isinstance(entry, Mapping):
        raise DFinalBoundProviderError("BOUND_CAPABILITY_UNKNOWN:"+cid)
    if entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
        raise DFinalBoundProviderError("BOUND_CAPABILITY_NOT_VERIFIED:"+cid)
    if float(entry.get("incremental_spend_usd",0))!=0:
        raise DFinalBoundProviderError("BOUND_CAPABILITY_NONZERO_COST:"+cid)
    source=entry.get("source")
    if not isinstance(source, Mapping) or source.get("type")!="python_stdlib":
        raise DFinalBoundProviderError("SOURCE_NOT_D_FINAL_STDLIB:"+cid)
    verification=entry.get("verification")
    if not isinstance(verification, Mapping) or not verification:
        raise DFinalBoundProviderError("BOUND_CAPABILITY_VERIFICATION_MISSING:"+cid)
    independent=(
        verification.get("independent_verified") is True
        or verification.get("producer_independent") is True
        or isinstance(verification.get("independently_verified_by"), str)
    )
    if not independent:
        raise DFinalBoundProviderError("INDEPENDENT_VERIFICATION_NOT_EVIDENT:"+cid)
    template=entry.get("action_template")
    if not isinstance(template, Mapping) or template.get("type")!="invoke_capability":
        raise DFinalBoundProviderError("ACTION_TEMPLATE_INVALID:"+cid)
    entry_sha=_sha(entry)
    if expected_registry_entry_sha256 is not None and entry_sha!=expected_registry_entry_sha256:
        raise DFinalBoundProviderError("REGISTRY_ENTRY_SHA256_MISMATCH")
    return {
        "capability_id":cid,
        "entry":deepcopy(dict(entry)),
        "registry_file_sha256":registry_sha,
        "registry_entry_sha256":entry_sha,
    }


def execute(
    capability_id: str,
    *,
    inputs: Mapping[str, Any],
    repo_root: str | Path,
    registry_path: str | Path,
    adapter_path: str | Path,
    expected_adapter_git_blob_sha: str,
    expected_registry_file_sha256: str | None = None,
    expected_registry_entry_sha256: str | None = None,
) -> dict[str, Any]:
    try:
        if not isinstance(inputs, Mapping):
            raise DFinalBoundProviderError("INPUTS_NOT_OBJECT")
        root=Path(repo_root).resolve()
        inspected=inspect(
            capability_id,
            registry_path=registry_path,
            expected_registry_file_sha256=expected_registry_file_sha256,
            expected_registry_entry_sha256=expected_registry_entry_sha256,
        )
        entry=inspected["entry"]
        rendered=_render(entry["action_template"], inputs)
        args=rendered.get("args")
        if not isinstance(args, Mapping) or args.get("capability_id")!=capability_id:
            raise DFinalBoundProviderError("RENDERED_ACTION_CAPABILITY_ID_MISMATCH")

        path=Path(adapter_path).resolve()
        raw=path.read_bytes()
        observed_blob=_git_blob(raw)
        if observed_blob!=str(expected_adapter_git_blob_sha).lower():
            raise DFinalBoundProviderError("ADAPTER_GIT_BLOB_MISMATCH")

        module_name=str(entry.get("adapter_module") or "")
        if path.name!=module_name+".py":
            raise DFinalBoundProviderError("ADAPTER_PATH_MODULE_MISMATCH")
        spec=importlib.util.spec_from_file_location("project_brain_d_final_"+module_name,path)
        if spec is None or spec.loader is None:
            raise DFinalBoundProviderError("ADAPTER_LOAD_FAILED")
        module=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=module
        spec.loader.exec_module(module)
        fn=getattr(module,str(entry.get("entrypoint") or "run"),None)
        if not callable(fn):
            raise DFinalBoundProviderError("ADAPTER_ENTRYPOINT_MISSING")
        call_args=dict(args)
        call_args.pop("capability_id",None)
        result=fn(call_args,root)
        if not isinstance(result, Mapping):
            raise DFinalBoundProviderError("BOUND_CAPABILITY_RESULT_INVALID")
        result=dict(result)
        result.setdefault("capability_id",capability_id)
        result["dependency"]={
            "status":"SEALED_STDLIB_MEMBER",
            "type":"python_stdlib",
        }
        _verify_expectation(rendered,result)

        req=list(entry.get("requires") or [])
        prov=list(entry.get("provides") or [])
        fields=list(entry.get("result_fields") or [])
        if not prov:
            raise DFinalBoundProviderError("INSTANCE_PROVIDES_EMPTY")
        problem={
            "initial_facts":list(req),
            "target_effects":list(prov),
            "capabilities":[{
                "id":capability_id,
                "requires":list(req),
                "provides":list(prov),
                "cost":float(entry.get("cost",1)),
                "action":deepcopy(dict(rendered)),
                "result_fields":fields,
            }],
            "finish_summary":"verified D-final stdlib bound capability execution",
        }
        planned=plan_actions(problem)
        actions=planned["actions"]
        if len(actions)!=2:
            raise DFinalBoundProviderError("SINGLE_CAPABILITY_PLAN_ACTION_COUNT_INVALID")
        execution={"trace":[
            {"cycle":0,"plan":deepcopy(actions[0]),"result":deepcopy(result)},
            {"cycle":1,"plan":deepcopy(actions[1]),"result":{"summary":"verified D-final stdlib bound capability execution"}},
        ]}
        verdict=verify_execution({"problem":problem},{"execution":execution})
        if verdict.get("pass") is not True:
            raise DFinalBoundProviderError("EXECUTION_TRACE_NOT_VERIFIED:"+str(verdict.get("reason")))
        return {
            "schema":SCHEMA,
            "status":"PASS__D_FINAL_STDLIB_PROVIDER_EXECUTED_AND_TRACE_VERIFIED",
            "pass":True,
            "capability_id":capability_id,
            "registry_file_sha256":inspected["registry_file_sha256"],
            "registry_entry_sha256":inspected["registry_entry_sha256"],
            "rendered_action_sha256":_sha(rendered),
            "adapter_git_blob_sha":observed_blob,
            "result_sha256":_sha(result),
            "result":deepcopy(result),
            "execution_verification":verdict,
            "composition_capsule_head_hash":(verdict.get("verified_output") or {}).get("capsule_head_hash"),
            "incremental_spend_usd":0,
            "network_or_package_acquisition_permitted":False,
            "execution_authority":False,
            "ownership_credit_delta":0,
            "terminal_credit_delta":0,
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "pass":False,
            "errors":[type(exc).__name__+":"+str(exc)],
            "execution_authority":False,
            "ownership_credit_delta":0,
            "terminal_credit_delta":0,
        }

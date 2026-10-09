"""Confined execution runner for pure D-final stdlib bound capabilities V1.

The host process only:
- validates/copies certified executable materials into a temporary input capsule;
- copies explicitly declared task input files;
- invokes the zero-ambient namespace launcher;
- parses one JSON result from the inherited broker.

The child receives no general host filesystem or network authority. It executes
the minimal D-final stdlib provider against a private writable /work/repo copy.
No material effect is committed to the host.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping, Sequence

from canonical.runtime import zero_ambient_namespace_launcher_v1 as ns

SCHEMA="PROJECT_BRAIN_D_FINAL_PURE_STDLIB_CONFINED_RUNNER_V1"

EXECUTABLE_RELATIVE_PATHS=(
    "canonical/runtime/d_final_bound_stdlib_provider_v1.py",
    "canonical/runtime/bound_capability_execution_verifier_v1.py",
    "canonical/runtime/capability_planner.py",
    "canonical/runtime/capability_execution_trace_capsule_v1.py",
    "canonical/runtime/composition_state_capsule_v1.py",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
)

_CHILD=r'''from __future__ import annotations
import json, os, pathlib, shutil, sys

def emit(obj):
    raw=(json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n").encode()
    fd=int(os.environ["PROJECT_BRAIN_BROKER_FD"]); off=0
    while off<len(raw): off+=os.write(fd,raw[off:])

src=pathlib.Path("/input/repo")
root=pathlib.Path("/work/repo")
shutil.copytree(src,root,dirs_exist_ok=True)
request=json.loads(pathlib.Path("/input/request.json").read_text())
sys.path.insert(0,str(root))
from canonical.runtime import d_final_bound_stdlib_provider_v1 as provider
out=provider.execute(
    request["local_capability_id"],
    inputs=request["payload"],
    repo_root=root,
    registry_path=root/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
    adapter_path=root/request["adapter_rel"],
    expected_adapter_git_blob_sha=request["expected_adapter_git_blob_sha"],
    expected_registry_entry_sha256=request["expected_registry_entry_sha256"],
)
emit(out)
raise SystemExit(0 if out.get("pass") is True else 5)
'''


class DFinalPureConfinedRunnerError(ValueError):
    pass


def _safe_repo_file(root: Path, raw: str) -> Path:
    rel=str(raw or "").strip()
    p=Path(rel)
    if not rel or p.is_absolute() or ".." in p.parts:
        raise DFinalPureConfinedRunnerError("INPUT_PATH_INVALID:"+rel)
    full=(root/p).resolve()
    try:
        full.relative_to(root)
    except ValueError as exc:
        raise DFinalPureConfinedRunnerError("INPUT_PATH_ESCAPES_ROOT:"+rel) from exc
    if not full.is_file():
        raise DFinalPureConfinedRunnerError("INPUT_FILE_MISSING:"+rel)
    return full


def run(
    *,
    local_capability_id: str,
    payload: Mapping[str, Any],
    repo_root: str | Path,
    adapter_rel: str,
    expected_adapter_git_blob_sha: str,
    expected_registry_entry_sha256: str,
    task_input_paths: Sequence[str],
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise DFinalPureConfinedRunnerError("PAYLOAD_NOT_OBJECT")
    root=Path(repo_root).resolve()
    adapter_rel=str(adapter_rel or "").strip()
    if not adapter_rel:
        raise DFinalPureConfinedRunnerError("ADAPTER_REL_REQUIRED")

    with tempfile.TemporaryDirectory(prefix="brain-d-final-pure-") as td:
        capsule=Path(td)
        repo_capsule=capsule/"repo"
        for rel in (*EXECUTABLE_RELATIVE_PATHS,adapter_rel):
            source=_safe_repo_file(root,rel)
            dest=repo_capsule/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,dest)

        copied_inputs=[]
        for rel in task_input_paths:
            source=_safe_repo_file(root,str(rel))
            dest=repo_capsule/str(rel)
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,dest)
            copied_inputs.append(str(rel))

        request={
            "local_capability_id":str(local_capability_id),
            "payload":dict(payload),
            "adapter_rel":adapter_rel,
            "expected_adapter_git_blob_sha":str(expected_adapter_git_blob_sha),
            "expected_registry_entry_sha256":str(expected_registry_entry_sha256),
        }
        (capsule/"request.json").write_text(
            json.dumps(request,sort_keys=True,separators=(",",":")),
            encoding="utf-8",
        )
        (capsule/"child.py").write_text(_CHILD,encoding="utf-8")

        policy={
            "argv":["/usr/bin/python3","/input/child.py"],
            "input_dir":str(capsule),
            "env":{
                "PYTHONDONTWRITEBYTECODE":"1",
                "PYTHONHASHSEED":"0",
                "TZ":"UTC",
                "LANG":"C.UTF-8",
            },
            "limits":{
                "pids":16,
                "memory_mb":512,
                "cpu_seconds":15,
                "wallclock_s":30,
                "scratch_mb":128,
                "max_file_mb":32,
                "nofile":32,
                "broker_max_bytes":1_000_000,
            },
        }
        confined=ns.run_confined(policy)
        raw=confined.get("broker_payload") or b""
        if not isinstance(raw,(bytes,bytearray)):
            raise DFinalPureConfinedRunnerError("BROKER_PAYLOAD_INVALID")
        try:
            result=json.loads(bytes(raw).decode("utf-8"))
        except Exception as exc:
            raise DFinalPureConfinedRunnerError("BROKER_RESULT_NOT_JSON") from exc
        if confined.get("returncode")!=0 or result.get("pass") is not True:
            raise DFinalPureConfinedRunnerError(
                "CONFINED_CHILD_FAILED:"+str(result.get("errors") or result.get("status"))
            )
        return {
            "schema":SCHEMA,
            "status":"PASS__PURE_STDLIB_EXECUTED_ZERO_AMBIENT",
            "pass":True,
            "local_capability_id":str(local_capability_id),
            "task_input_paths":copied_inputs,
            "namespace_policy_sha256":confined.get("policy_sha256"),
            "broker_sha256":confined.get("broker_sha256"),
            "material_effects_committed":confined.get("material_effects_committed"),
            "result":result,
            "execution_authority":False,
            "ownership_credit_delta":0,
            "terminal_credit_delta":0,
        }

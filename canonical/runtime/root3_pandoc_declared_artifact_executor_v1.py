"""Confined one-site executor for current DECLARED_ARTIFACT_PRODUCTION.

The Pandoc child may write only to an ephemeral output directory. After the
child exits, the parent validates exact PDF output bytes and routes the only
durable write through the existing content-addressed declared-artifact finalizer.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from typing import Any

from canonical.runtime.effect_broker_contract_v1 import make_grant
from canonical.runtime import root3_astra_composition_context_v1 as composition_context
from canonical.runtime import root3_declared_artifact_finalizer_v1 as finalizer
from canonical.runtime import root3_pdf_raster_temp_executor_v1 as temp_carrier

ROOT=pathlib.Path(__file__).resolve().parents[2]
EFFECT_CLASS="DECLARED_ARTIFACT_PRODUCTION"
SUPPORTED_SITE=(
    "canonical/runtime/bound_capabilities/pandoc_weasyprint.py",
    24,
    "subprocess.run",
)
ARTIFACT_ROOT=(ROOT/"canonical/astra_runtime/artifacts").resolve()
PDF_MAGIC=b"%PDF-"
AUTHORITY_RECEIPT={
    "path":"canonical/verification/DECLARED_ARTIFACT_AUTHORITY_RECEIPT_20261005_V1.json",
    "git_blob_sha":"12ba23e0f071c46fd931dcc9734ff63025ef165c",
    "scope_complete":True,
    "allow_implies_zero_critical_authority_violation":True,
    "independent_or_objective":True,
}
COMPOSITION_RECEIPT={
    "path":"canonical/verification/DECLARED_ARTIFACT_COMPOSITION_RECEIPT_20261005_V1.json",
    "git_blob_sha":"10974b543f9d550ac3afdbe6d0dfade6b4adce62",
    "scope_complete":True,
    "state_and_provenance_invariants_hold":True,
    "independent_or_objective":True,
}
SHA256_RE=re.compile(r"^[0-9a-f]{64}$")

_WRAPPER=r"""
import base64,json,os,subprocess,sys
spec=json.loads(base64.urlsafe_b64decode(sys.argv[1].encode("ascii")).decode("utf-8"))
try:
    p=subprocess.run(
        spec["argv"],
        cwd="/input",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=spec["timeout"],
        check=False,
    )
    out={
        "timed_out":False,
        "returncode":int(p.returncode),
        "stdout_b64":base64.b64encode(p.stdout or b"").decode("ascii"),
        "stderr_b64":base64.b64encode(p.stderr or b"").decode("ascii"),
    }
except subprocess.TimeoutExpired as exc:
    out={
        "timed_out":True,
        "returncode":None,
        "stdout_b64":base64.b64encode(exc.output or b"").decode("ascii"),
        "stderr_b64":base64.b64encode(exc.stderr or b"").decode("ascii"),
    }
fd=int(os.environ["PROJECT_BRAIN_BROKER_FD"])
os.write(fd,(json.dumps(out,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8"))
"""

class DeclaredArtifactExecutorDenied(PermissionError):
    pass

def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def _site(context:Mapping[str,Any])->tuple[str,int,str]:
    callsite=context.get("callsite")
    if not isinstance(callsite,Mapping):
        raise DeclaredArtifactExecutorDenied("CALLSITE_MISSING")
    try:
        key=(
            str(callsite.get("module_path") or ""),
            int(callsite.get("lineno") or 0),
            str(callsite.get("process_api") or ""),
        )
    except Exception as exc:
        raise DeclaredArtifactExecutorDenied("CALLSITE_INVALID") from exc
    if key!=SUPPORTED_SITE:
        raise DeclaredArtifactExecutorDenied("DECLARED_ARTIFACT_CALLSITE_NOT_SUPPORTED:"+repr(key))
    return key

def _resolved_system_tool(name:str)->pathlib.Path:
    raw=shutil.which(name)
    if not raw:
        raise DeclaredArtifactExecutorDenied("SYSTEM_TOOL_MISSING:"+name)
    path=pathlib.Path(raw).resolve()
    if not (str(path).startswith("/usr/") or str(path).startswith("/bin/")):
        raise DeclaredArtifactExecutorDenied("SYSTEM_TOOL_OUTSIDE_READ_ONLY_SYSTEM_MOUNTS:"+name)
    if not path.is_file():
        raise DeclaredArtifactExecutorDenied("SYSTEM_TOOL_NOT_FILE:"+name)
    return path

def _repo_path(value:Any,label:str)->pathlib.Path:
    try:
        p=pathlib.Path(os.fspath(value)).resolve()
        p.relative_to(ROOT.resolve())
    except Exception as exc:
        raise DeclaredArtifactExecutorDenied(label+"_OUTSIDE_REPOSITORY") from exc
    return p

def _expected_prestate(dst:pathlib.Path)->str:
    if dst.is_symlink():
        raise DeclaredArtifactExecutorDenied("ARTIFACT_DESTINATION_SYMLINK_DENIED")
    if not dst.exists():
        return "ABSENT"
    if not dst.is_file():
        raise DeclaredArtifactExecutorDenied("ARTIFACT_DESTINATION_NOT_REGULAR_FILE")
    raw=dst.read_bytes()
    if len(raw)>finalizer.MAX_ARTIFACT_BYTES:
        raise DeclaredArtifactExecutorDenied("ARTIFACT_PRESTATE_TOO_LARGE")
    return _sha(raw)

def _toolchain_sha(pandoc:pathlib.Path,weasyprint:pathlib.Path)->str:
    adapter=ROOT/"canonical/runtime/bound_capabilities/pandoc_weasyprint.py"
    fields={
        "executor_sha256":_sha(pathlib.Path(__file__).read_bytes()),
        "adapter_sha256":_sha(adapter.read_bytes()),
        "pandoc_path":str(pandoc),
        "pandoc_sha256":_sha(pandoc.read_bytes()),
        "weasyprint_path":str(weasyprint),
        "weasyprint_sha256":_sha(weasyprint.read_bytes()),
    }
    return _sha(json.dumps(fields,sort_keys=True,separators=(",",":")).encode())

def _prepare(context:Mapping[str,Any])->dict[str,Any]:
    if context.get("effect_class")!=EFFECT_CLASS:
        raise DeclaredArtifactExecutorDenied("EFFECT_CLASS_MISMATCH")
    _site(context)
    if context.get("api")!="subprocess.run":
        raise DeclaredArtifactExecutorDenied("PROCESS_API_NOT_SUPPORTED")
    args=context.get("args")
    if not isinstance(args,(tuple,list)) or len(args)!=1:
        raise DeclaredArtifactExecutorDenied("COMMAND_POSITIONAL_SHAPE_INVALID")
    command=args[0]
    if not isinstance(command,(tuple,list)) or len(command)!=5:
        raise DeclaredArtifactExecutorDenied("PANDOC_ARGV_SHAPE_INVALID")
    argv=[os.fspath(x) if isinstance(x,os.PathLike) else str(x) for x in command]
    if pathlib.Path(argv[0]).name!="pandoc":
        raise DeclaredArtifactExecutorDenied("EXECUTABLE_NOT_PANDOC")
    if argv[2]!="-o" or argv[4]!="--pdf-engine=weasyprint":
        raise DeclaredArtifactExecutorDenied("PANDOC_OPTIONS_INVALID")
    src=_repo_path(argv[1],"MARKDOWN_INPUT")
    dst=_repo_path(argv[3],"PDF_OUTPUT")
    if not src.is_file() or src.suffix.lower() not in {".md",".markdown"}:
        raise DeclaredArtifactExecutorDenied("MARKDOWN_INPUT_REQUIRED")
    if dst.suffix.lower()!=".pdf":
        raise DeclaredArtifactExecutorDenied("PDF_OUTPUT_REQUIRED")
    if dst.parent.resolve()!=ARTIFACT_ROOT:
        raise DeclaredArtifactExecutorDenied("PDF_OUTPUT_NOT_RESERVED_ARTIFACT_ROOT")
    if not ARTIFACT_ROOT.is_dir() or ARTIFACT_ROOT.is_symlink():
        raise DeclaredArtifactExecutorDenied("ARTIFACT_ROOT_INVALID")

    kwargs=dict(context.get("kwargs") or {})
    cwd=kwargs.get("cwd")
    if cwd is None or pathlib.Path(cwd).resolve()!=ROOT.resolve():
        raise DeclaredArtifactExecutorDenied("CWD_MUST_BE_REPOSITORY_ROOT")
    if kwargs.get("shell",False):
        raise DeclaredArtifactExecutorDenied("SHELL_FORBIDDEN")
    if kwargs.get("env") is not None:
        raise DeclaredArtifactExecutorDenied("CUSTOM_ENV_FORBIDDEN")
    if kwargs.get("input") is not None or kwargs.get("stdin") not in (None,subprocess.DEVNULL):
        raise DeclaredArtifactExecutorDenied("STDIN_OR_INPUT_FORBIDDEN")
    if kwargs.get("capture_output") is not True:
        raise DeclaredArtifactExecutorDenied("CAPTURE_OUTPUT_REQUIRED")
    if not (kwargs.get("text") is True or kwargs.get("universal_newlines") is True or kwargs.get("encoding")):
        raise DeclaredArtifactExecutorDenied("TEXT_MODE_REQUIRED")
    timeout=float(kwargs.get("timeout") or 120)
    if not (0<timeout<=300):
        raise DeclaredArtifactExecutorDenied("TIMEOUT_OUT_OF_RANGE")

    pandoc=_resolved_system_tool("pandoc")
    weasyprint=_resolved_system_tool("weasyprint")
    python3=_resolved_system_tool("python3")
    src_rel=src.relative_to(ROOT.resolve()).as_posix()
    inner=[
        str(pandoc),
        "/input/"+src_rel,
        "-o",
        "/output/result.pdf",
        "--pdf-engine="+str(weasyprint),
    ]
    spec={"argv":inner,"timeout":timeout}
    encoded=base64.urlsafe_b64encode(
        json.dumps(spec,sort_keys=True,separators=(",",":")).encode("utf-8")
    ).decode("ascii")
    return {
        "original_argv":argv,
        "kwargs":kwargs,
        "src":src,
        "dst":dst,
        "src_rel":src_rel,
        "input_dir":ROOT.resolve(),
        "timeout":timeout,
        "wrapper_argv":[str(python3),"-c",_WRAPPER,encoded],
        "pandoc":pandoc,
        "weasyprint":weasyprint,
        "expected_pre_sha256":_expected_prestate(dst),
        "producer_sha256":_sha(src.read_bytes()),
        "toolchain_sha256":_toolchain_sha(pandoc,weasyprint),
    }

def _validate_ephemeral_pdf(output_dir:pathlib.Path)->bytes:
    entries=sorted(output_dir.iterdir())
    if len(entries)!=1 or entries[0].name!="result.pdf":
        raise DeclaredArtifactExecutorDenied(
            "EPHEMERAL_OUTPUT_SET_INVALID:"+",".join(x.name for x in entries)
        )
    p=entries[0]
    if p.is_symlink() or not p.is_file():
        raise DeclaredArtifactExecutorDenied("EPHEMERAL_PDF_NOT_REGULAR_FILE")
    raw=p.read_bytes()
    if not raw.startswith(PDF_MAGIC):
        raise DeclaredArtifactExecutorDenied("PDF_MAGIC_MISMATCH")
    if not raw or len(raw)>finalizer.MAX_ARTIFACT_BYTES:
        raise DeclaredArtifactExecutorDenied("PDF_SIZE_INVALID")
    return raw

def _artifact_grant(request:Mapping[str,Any])->dict[str,Any]:
    return make_grant(
        request=request,
        authority_receipt=AUTHORITY_RECEIPT,
        composition_receipt=COMPOSITION_RECEIPT,
        max_payload_bytes=8_000_000,
    )

def make_executor(
    *,
    popen_impl:Callable[...,Any],
    context_provider:Callable[[],Mapping[str,Any]]=composition_context.capture,
    repo_root:pathlib.Path=ROOT,
    confined_runner:Callable[[Mapping[str,Any],Callable[...,Any]],dict[str,Any]]=temp_carrier._run_confined,
)->Callable[[Mapping[str,Any]],subprocess.CompletedProcess]:
    if not callable(popen_impl) or not callable(context_provider) or not callable(confined_runner):
        raise TypeError("EXECUTOR_DEPENDENCY_NOT_CALLABLE")
    root=pathlib.Path(repo_root).resolve()
    if root!=ROOT.resolve():
        raise DeclaredArtifactExecutorDenied("REPO_ROOT_IDENTITY_MISMATCH")

    def execute(context:Mapping[str,Any])->subprocess.CompletedProcess:
        prepared=_prepare(context)
        identity=dict(context_provider())
        if identity.get("astra_runtime_git_blob_sha")!=composition_context.EXPECTED_ASTRA_BLOB:
            raise DeclaredArtifactExecutorDenied("ASTRA_CONTEXT_BLOB_MISMATCH")
        mission_id=str(identity.get("mission_id") or "")
        capsule_head=str(identity.get("capsule_head_sha256") or "")
        action_ref=str(identity.get("action_ref") or "")
        if not mission_id or SHA256_RE.fullmatch(capsule_head) is None or not action_ref:
            raise DeclaredArtifactExecutorDenied("COMPOSITION_IDENTITY_INVALID")

        with tempfile.TemporaryDirectory(prefix="project-brain-declared-artifact-") as td:
            output_dir=pathlib.Path(td).resolve()
            run_spec=dict(prepared)
            run_spec["output_dir"]=output_dir
            try:
                result=confined_runner(run_spec,popen_impl)
            except Exception as exc:
                if isinstance(exc,subprocess.TimeoutExpired):
                    raise
                raise DeclaredArtifactExecutorDenied(
                    "ARTIFACT_CONFINEMENT_FAILED:"+type(exc).__name__+":"+str(exc)
                ) from exc
            if result.get("timed_out"):
                raise subprocess.TimeoutExpired(
                    prepared["original_argv"],prepared["timeout"]
                )
            stdout_b=base64.b64decode(result.get("stdout_b64") or "")
            stderr_b=base64.b64decode(result.get("stderr_b64") or "")
            returncode=int(result.get("returncode"))
            kwargs=prepared["kwargs"]
            encoding=kwargs.get("encoding") or "utf-8"
            errors=kwargs.get("errors") or "strict"
            cp=subprocess.CompletedProcess(
                args=prepared["original_argv"],
                returncode=returncode,
                stdout=stdout_b.decode(encoding,errors=errors),
                stderr=stderr_b.decode(encoding,errors=errors),
            )
            if returncode!=0:
                return cp

            payload=_validate_ephemeral_pdf(output_dir)
            destination=prepared["dst"].relative_to(root).as_posix()
            plan=finalizer.build_plan(
                mission_id=mission_id,
                capsule_head_sha256=capsule_head,
                action_ref=action_ref,
                destination_path=destination,
                payload=payload,
                expected_pre_sha256=prepared["expected_pre_sha256"],
                content_type="application/pdf",
                producer_sha256=prepared["producer_sha256"],
                toolchain_sha256=prepared["toolchain_sha256"],
            )
            request=finalizer.effect_request(plan,payload)
            grant=_artifact_grant(request)
            receipt=finalizer.commit(root,plan,payload,grant)
            if (
                receipt.get("status")!="COMMITTED"
                or receipt.get("destination_path")!=destination
                or receipt.get("post_sha256")!=_sha(payload)
                or receipt.get("exact_readback") is not True
            ):
                raise DeclaredArtifactExecutorDenied("FINALIZER_RECEIPT_INVALID")
            return cp

    return execute

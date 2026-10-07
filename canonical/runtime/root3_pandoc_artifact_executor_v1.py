"""Exact Root3 executor for the one DECLARED_ARTIFACT_PRODUCTION process site.

The Pandoc/WeasyPrint child is confined by the already verified namespace
carrier used by the TEMP class. The repository is exposed read-only to the
child. Child output goes to a caller-created staging directory only. After a
successful child exit, the parent validates exact PDF output bytes and performs
a compare-and-swap style atomic replace of the exact declared repository-local
.pdf destination.

This is not generic repository write authority.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from typing import Any

from canonical.runtime import root3_pdf_raster_temp_executor_v1 as confinement

SCHEMA = "PROJECT_BRAIN_ROOT3_PANDOC_ARTIFACT_EXECUTOR_V1"
EFFECT_CLASS = "DECLARED_ARTIFACT_PRODUCTION"
SUPPORTED_SITE = (
    "canonical/runtime/bound_capabilities/pandoc_weasyprint.py",
    24,
    "subprocess.run",
)
PDF_MAGIC = b"%PDF-"
MAX_PDF_BYTES = 536_870_912

_WRAPPER = r"""
import base64,json,os,pathlib,subprocess,sys
spec=json.loads(base64.urlsafe_b64decode(sys.argv[1].encode("ascii")).decode("utf-8"))
try:
    p=subprocess.run(
        spec["argv"],
        cwd="/input",
        stdin=None,
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


class PandocArtifactDenied(PermissionError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _site(context: Mapping[str, Any]) -> None:
    callsite = context.get("callsite")
    if not isinstance(callsite, Mapping):
        raise PandocArtifactDenied("CALLSITE_MISSING")
    try:
        key = (
            str(callsite.get("module_path") or ""),
            int(callsite.get("lineno") or 0),
            str(callsite.get("process_api") or ""),
        )
    except Exception as exc:
        raise PandocArtifactDenied("CALLSITE_INVALID") from exc
    if key != SUPPORTED_SITE:
        raise PandocArtifactDenied("ARTIFACT_CALLSITE_NOT_SUPPORTED:" + repr(key))


def _inside(root: pathlib.Path, raw: Any, label: str) -> pathlib.Path:
    try:
        root = root.resolve(strict=True)
        raw_path = pathlib.Path(os.fspath(raw))
        candidate = raw_path.resolve() if raw_path.is_absolute() else (root / raw_path).resolve()
    except Exception as exc:
        raise PandocArtifactDenied(label + "_PATH_INVALID") from exc
    if candidate != root and root not in candidate.parents:
        raise PandocArtifactDenied(label + "_PATH_OUTSIDE_REPOSITORY")
    return candidate


def _target_parent_safe(root: pathlib.Path, target: pathlib.Path) -> None:
    root = root.resolve(strict=True)
    try:
        rel = target.relative_to(root)
    except ValueError as exc:
        raise PandocArtifactDenied("OUTPUT_PATH_OUTSIDE_REPOSITORY") from exc
    cursor = root
    for part in rel.parts[:-1]:
        cursor = cursor / part
        if cursor.is_symlink():
            raise PandocArtifactDenied("OUTPUT_PARENT_SYMLINK_DENIED")
    if not target.parent.is_dir():
        raise PandocArtifactDenied("OUTPUT_PARENT_MISSING")
    if target.is_symlink():
        raise PandocArtifactDenied("OUTPUT_TARGET_SYMLINK_DENIED")
    if target.exists() and not target.is_file():
        raise PandocArtifactDenied("OUTPUT_TARGET_NOT_REGULAR_FILE")


def _prestate(target: pathlib.Path) -> tuple[str, bytes]:
    if not target.exists():
        return "ABSENT", b""
    data = target.read_bytes()
    if len(data) > MAX_PDF_BYTES:
        raise PandocArtifactDenied("OUTPUT_PRESTATE_TOO_LARGE")
    return _sha(data), data


def _resolve_tool(name: str) -> str:
    resolved = shutil.which(name)
    if not resolved:
        raise PandocArtifactDenied(name.upper() + "_UNAVAILABLE")
    path = pathlib.Path(resolved).resolve()
    if not (str(path).startswith("/usr/") or str(path).startswith("/bin/")):
        raise PandocArtifactDenied(name.upper() + "_OUTSIDE_SYSTEM_MOUNTS")
    return str(path)


def _prepare(context: Mapping[str, Any]) -> dict[str, Any]:
    if context.get("effect_class") != EFFECT_CLASS:
        raise PandocArtifactDenied("EFFECT_CLASS_MISMATCH")
    _site(context)
    if context.get("api") != "subprocess.run":
        raise PandocArtifactDenied("PROCESS_API_NOT_SUPPORTED")

    args = context.get("args")
    if not isinstance(args, (tuple, list)) or len(args) != 1:
        raise PandocArtifactDenied("COMMAND_POSITIONAL_SHAPE_INVALID")
    command = args[0]
    if not isinstance(command, (tuple, list)) or len(command) != 5:
        raise PandocArtifactDenied("PANDOC_ARGV_SHAPE_INVALID")
    argv = [os.fspath(x) if isinstance(x, os.PathLike) else str(x) for x in command]
    if pathlib.Path(argv[0]).name != "pandoc":
        raise PandocArtifactDenied("EXECUTABLE_NOT_PANDOC")
    if argv[2] != "-o" or argv[4] != "--pdf-engine=weasyprint":
        raise PandocArtifactDenied("PANDOC_OPTIONS_INVALID")

    kwargs = dict(context.get("kwargs") or {})
    if set(kwargs) != {"cwd", "text", "capture_output", "timeout"}:
        raise PandocArtifactDenied("PROCESS_KWARGS_NOT_EXACT_FROZEN_SURFACE")
    if kwargs.get("shell", False):
        raise PandocArtifactDenied("SHELL_FORBIDDEN")
    if kwargs.get("env") is not None:
        raise PandocArtifactDenied("CUSTOM_ENV_FORBIDDEN")
    if kwargs.get("input") is not None or kwargs.get("stdin") not in (None, subprocess.DEVNULL):
        raise PandocArtifactDenied("STDIN_OR_INPUT_FORBIDDEN")
    if kwargs.get("capture_output") is not True:
        raise PandocArtifactDenied("CAPTURE_OUTPUT_REQUIRED")
    if not (kwargs.get("text") is True or kwargs.get("universal_newlines") is True or kwargs.get("encoding")):
        raise PandocArtifactDenied("TEXT_MODE_REQUIRED")
    timeout = float(kwargs.get("timeout") or 120)
    if not (0 < timeout <= 300):
        raise PandocArtifactDenied("TIMEOUT_OUT_OF_RANGE")

    cwd_raw = kwargs.get("cwd")
    if cwd_raw is None:
        raise PandocArtifactDenied("REPOSITORY_ROOT_CWD_REQUIRED")
    repo_root = pathlib.Path(os.fspath(cwd_raw)).resolve(strict=True)
    if not repo_root.is_dir():
        raise PandocArtifactDenied("REPOSITORY_ROOT_CWD_INVALID")
    if confinement._inside_mounts(repo_root):
        raise PandocArtifactDenied("REPOSITORY_INPUT_HAS_NESTED_MOUNTS")

    src = _inside(repo_root, argv[1], "INPUT")
    dst = _inside(repo_root, argv[3], "OUTPUT")
    if not src.is_file() or src.suffix.lower() not in {".md", ".markdown"}:
        raise PandocArtifactDenied("MARKDOWN_INPUT_REQUIRED")
    if dst.suffix.lower() != ".pdf":
        raise PandocArtifactDenied("PDF_OUTPUT_REQUIRED")
    _target_parent_safe(repo_root, dst)
    pre_sha, _ = _prestate(dst)

    pandoc = _resolve_tool("pandoc")
    weasyprint = _resolve_tool("weasyprint")
    src_rel = src.relative_to(repo_root).as_posix()
    inner = [
        pandoc,
        "/input/" + src_rel,
        "-o",
        "/output/artifact.pdf",
        "--pdf-engine=" + weasyprint,
    ]
    spec = {"argv": inner, "timeout": timeout}
    encoded = base64.urlsafe_b64encode(
        json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")

    return {
        "original_argv": argv,
        "kwargs": kwargs,
        "timeout": timeout,
        "repo_root": repo_root,
        "input_dir": repo_root,
        "destination": dst,
        "expected_pre_sha256": pre_sha,
        "inner_argv": inner,
        "wrapper_argv": ["/usr/bin/python3", "-I", "-c", _WRAPPER, encoded],
    }


def _validated_staged_pdf(stage: pathlib.Path) -> bytes:
    entries = list(stage.iterdir())
    if len(entries) != 1:
        raise PandocArtifactDenied("STAGED_OUTPUT_CARDINALITY_INVALID")
    artifact = entries[0]
    if artifact.name != "artifact.pdf" or artifact.is_symlink() or not artifact.is_file():
        raise PandocArtifactDenied("STAGED_OUTPUT_INVALID")
    raw = artifact.read_bytes()
    if not raw.startswith(PDF_MAGIC):
        raise PandocArtifactDenied("STAGED_OUTPUT_NOT_PDF")
    if not (1 <= len(raw) <= MAX_PDF_BYTES):
        raise PandocArtifactDenied("STAGED_OUTPUT_SIZE_INVALID")
    return raw


def _atomic_replace(target: pathlib.Path, payload: bytes) -> None:
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix="." + target.name + ".root3-artifact.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            temp_name = fh.name
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_name, target)
        temp_name = None
        try:
            fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            pass
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def make_executor(*, popen_impl: Callable[..., Any]) -> Callable[[Mapping[str, Any]], subprocess.CompletedProcess]:
    if not callable(popen_impl):
        raise TypeError("POPEN_IMPL_NOT_CALLABLE")

    def execute(context: Mapping[str, Any]) -> subprocess.CompletedProcess:
        prepared = _prepare(context)
        stage = pathlib.Path(tempfile.mkdtemp(prefix="project-brain-pandoc-artifact-"))
        if os.geteuid() == 0:
            os.chown(stage, 65534, 65534)
        try:
            confined = {
                **prepared,
                "output_dir": stage,
            }
            result = confinement._run_confined(confined, popen_impl)
            if result.get("timed_out"):
                raise subprocess.TimeoutExpired(
                    prepared["original_argv"],
                    prepared["timeout"],
                    output=base64.b64decode(result.get("stdout_b64") or ""),
                    stderr=base64.b64decode(result.get("stderr_b64") or ""),
                )
            stdout_b = base64.b64decode(result.get("stdout_b64") or "")
            stderr_b = base64.b64decode(result.get("stderr_b64") or "")
            encoding = prepared["kwargs"].get("encoding") or "utf-8"
            errors = prepared["kwargs"].get("errors") or "strict"
            cp = subprocess.CompletedProcess(
                args=prepared["original_argv"],
                returncode=int(result["returncode"]),
                stdout=stdout_b.decode(encoding, errors=errors),
                stderr=stderr_b.decode(encoding, errors=errors),
            )
            if cp.returncode != 0:
                return cp

            raw = _validated_staged_pdf(stage)
            current_sha, _ = _prestate(prepared["destination"])
            if current_sha != prepared["expected_pre_sha256"]:
                raise PandocArtifactDenied("OUTPUT_PRESTATE_CHANGED_DURING_CHILD_EXECUTION")
            _target_parent_safe(prepared["repo_root"], prepared["destination"])
            _atomic_replace(prepared["destination"], raw)
            observed = prepared["destination"].read_bytes()
            if observed != raw:
                raise PandocArtifactDenied("OUTPUT_POSTSTATE_BYTE_MISMATCH")
            return cp
        finally:
            shutil.rmtree(stage, ignore_errors=True)

    return execute

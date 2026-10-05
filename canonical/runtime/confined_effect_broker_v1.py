"""Project Brain confined effect broker substrate V1.

This module implements only the K1-K3 substrate:
- launch untrusted/dynamic computation in a Docker-confined child;
- deny direct child network and canonical-repository writes;
- expose one typed, validated broker spool for material host commits.

It deliberately does NOT claim predicate-specific guard soundness (K4), final-output
mediation (K5), or terminal acceptance. The broker spool is untrusted ephemeral
staging; only validated broker requests may reach the caller-owned output root.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REQUEST_SCHEMA = "PROJECT_BRAIN_EFFECT_REQUEST_V1"
RESPONSE_SCHEMA = "PROJECT_BRAIN_EFFECT_RESPONSE_V1"
SUPPORTED_EFFECTS = {"write_text_artifact"}
MAX_REQUEST_BYTES = 1_000_000
MAX_TEXT_BYTES = 750_000


class ConfinedEffectError(RuntimeError):
    pass


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def request_body(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": request.get("schema"),
        "effect_type": request.get("effect_type"),
        "target": request.get("target"),
        "payload": request.get("payload"),
        "guard_context": request.get("guard_context"),
    }


def request_id_for(request: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(request_body(request))).hexdigest()


def validate_request(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ConfinedEffectError("REQUEST_NOT_OBJECT")
    if request.get("schema") != REQUEST_SCHEMA:
        raise ConfinedEffectError("REQUEST_SCHEMA_INVALID")
    effect_type = request.get("effect_type")
    if effect_type not in SUPPORTED_EFFECTS:
        raise ConfinedEffectError("EFFECT_TYPE_UNSUPPORTED")
    rid = str(request.get("request_id") or "")
    if len(rid) != 64 or rid != request_id_for(request):
        raise ConfinedEffectError("REQUEST_ID_MISMATCH")
    target = str(request.get("target") or "")
    rel = Path(target)
    if (
        not target
        or rel.is_absolute()
        or ".." in rel.parts
        or "." in rel.parts
        or "\x00" in target
    ):
        raise ConfinedEffectError("TARGET_PATH_INVALID")
    payload = request.get("payload")
    if not isinstance(payload, dict):
        raise ConfinedEffectError("PAYLOAD_NOT_OBJECT")
    if effect_type == "write_text_artifact":
        text = payload.get("text")
        if not isinstance(text, str):
            raise ConfinedEffectError("TEXT_PAYLOAD_INVALID")
        if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
            raise ConfinedEffectError("TEXT_PAYLOAD_TOO_LARGE")
    return request


def _safe_destination(output_root: Path, target: str) -> Path:
    root = output_root.resolve()
    rel = Path(target)
    if rel.is_absolute() or ".." in rel.parts or "." in rel.parts:
        raise ConfinedEffectError("TARGET_PATH_INVALID")
    destination = (root / rel).resolve()
    try:
        destination.relative_to(root)
    except ValueError as exc:
        raise ConfinedEffectError("TARGET_ESCAPES_OUTPUT_ROOT") from exc
    # The child never receives output_root as a mount. Existing symlinks in a
    # caller-supplied output tree are nevertheless rejected rather than followed.
    cursor = root
    for part in rel.parts[:-1]:
        cursor = cursor / part
        if cursor.exists() and cursor.is_symlink():
            raise ConfinedEffectError("OUTPUT_PARENT_SYMLINK_FORBIDDEN")
    if destination.exists() and destination.is_symlink():
        raise ConfinedEffectError("OUTPUT_TARGET_SYMLINK_FORBIDDEN")
    return destination


def apply_request(
    request: dict[str, Any],
    output_root: Path,
    *,
    allowed_effect_types: set[str] | None = None,
) -> dict[str, Any]:
    request = validate_request(request)
    allowed = SUPPORTED_EFFECTS if allowed_effect_types is None else set(allowed_effect_types)
    effect_type = str(request["effect_type"])
    if effect_type not in allowed:
        raise ConfinedEffectError("EFFECT_NOT_ALLOWED_BY_CALLER")

    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    destination = _safe_destination(output_root, str(request["target"]))

    if effect_type == "write_text_artifact":
        raw = str(request["payload"]["text"]).encode("utf-8")
        destination.parent.mkdir(parents=True, exist_ok=True)
        tmp = destination.with_name(destination.name + ".broker-tmp-" + request["request_id"][:12])
        if tmp.exists():
            tmp.unlink()
        with tmp.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, destination)
        try:
            dir_fd = os.open(str(destination.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
        return {
            "schema": RESPONSE_SCHEMA,
            "request_id": request["request_id"],
            "status": "applied",
            "effect_type": effect_type,
            "target": str(request["target"]),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    raise ConfinedEffectError("EFFECT_TYPE_UNSUPPORTED")


def _read_untrusted_json_nofollow(path: Path) -> dict[str, Any]:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(str(path), flags)
    except OSError as exc:
        raise ConfinedEffectError("REQUEST_OPEN_FAILED") from exc
    try:
        stat = os.fstat(fd)
        if stat.st_size > MAX_REQUEST_BYTES:
            raise ConfinedEffectError("REQUEST_TOO_LARGE")
        raw = os.read(fd, MAX_REQUEST_BYTES + 1)
    finally:
        os.close(fd)
    if len(raw) > MAX_REQUEST_BYTES:
        raise ConfinedEffectError("REQUEST_TOO_LARGE")
    try:
        value = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ConfinedEffectError("REQUEST_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise ConfinedEffectError("REQUEST_NOT_OBJECT")
    return value


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    raw = json.dumps(value, sort_keys=True, indent=2) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(raw, encoding="utf-8")
    os.replace(tmp, path)


def serve_pending_once(
    spool_root: Path,
    output_root: Path,
    *,
    processed: set[str] | None = None,
    allowed_effect_types: set[str] | None = None,
) -> list[dict[str, Any]]:
    spool_root = Path(spool_root)
    request_dir = spool_root / "requests"
    response_dir = spool_root / "responses"
    request_dir.mkdir(parents=True, exist_ok=True)
    response_dir.mkdir(parents=True, exist_ok=True)
    seen = processed if processed is not None else set()
    results: list[dict[str, Any]] = []

    for path in sorted(request_dir.glob("*.json")):
        if path.name in seen:
            continue
        seen.add(path.name)
        rid_from_name = path.stem
        try:
            request = _read_untrusted_json_nofollow(path)
            if request.get("request_id") != rid_from_name:
                raise ConfinedEffectError("REQUEST_FILENAME_ID_MISMATCH")
            response = apply_request(
                request,
                output_root,
                allowed_effect_types=allowed_effect_types,
            )
        except Exception as exc:
            response = {
                "schema": RESPONSE_SCHEMA,
                "request_id": rid_from_name,
                "status": "denied",
                "error": type(exc).__name__ + ":" + str(exc),
            }
        _atomic_json(response_dir / (rid_from_name + ".json"), response)
        results.append(response)
    return results


def resolve_local_image_id(image: str) -> str:
    if not shutil.which("docker"):
        raise ConfinedEffectError("DOCKER_NOT_AVAILABLE")
    proc = subprocess.run(
        ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise ConfinedEffectError("IMAGE_NOT_PRESENT__PULL_EXPLICITLY")
    image_id = proc.stdout.strip()
    if not image_id.startswith("sha256:") or len(image_id) != 71:
        raise ConfinedEffectError("IMAGE_ID_INVALID")
    return image_id


def docker_command(
    *,
    image_id: str,
    repo_root: Path,
    spool_root: Path,
    child_command: list[str],
) -> list[str]:
    if not image_id.startswith("sha256:") or len(image_id) != 71:
        raise ConfinedEffectError("IMAGE_ID_MUST_BE_CONTENT_ADDRESSED")
    if not child_command or not all(isinstance(x, str) and x for x in child_command):
        raise ConfinedEffectError("CHILD_COMMAND_INVALID")
    repo_root = Path(repo_root).resolve()
    spool_root = Path(spool_root).resolve()
    return [
        "docker", "run", "--rm",
        "--network", "none",
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges:true",
        "--pids-limit", "64",
        "--memory", "256m",
        "--cpus", "1",
        "--user", "65534:65534",
        "--env", "PYTHONDONTWRITEBYTECODE=1",
        "--mount", f"type=bind,src={repo_root},dst=/repo,readonly",
        "--mount", f"type=bind,src={spool_root},dst=/broker",
        "--tmpfs", "/scratch:rw,nosuid,nodev,noexec,size=67108864,mode=1777",
        "--tmpfs", "/tmp:rw,nosuid,nodev,noexec,size=33554432,mode=1777",
        "--workdir", "/scratch",
        image_id,
        *child_command,
    ]


def run_confined(
    child_command: list[str],
    output_root: Path,
    *,
    image: str,
    timeout_s: float = 30.0,
    allowed_effect_types: set[str] | None = None,
) -> dict[str, Any]:
    """Run a child in confinement and service typed broker requests.

    The image must already exist locally. It is resolved to an immutable local
    sha256 image ID before execution; this function never pulls an image.
    """
    if timeout_s <= 0 or timeout_s > 300:
        raise ConfinedEffectError("TIMEOUT_INVALID")
    image_id = resolve_local_image_id(image)
    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="brain-effect-spool-") as td:
        spool = Path(td).resolve()
        (spool / "requests").mkdir()
        (spool / "responses").mkdir()
        # The confined child runs as nobody and can write only to this ephemeral
        # spool and tmpfs. The output root is intentionally never mounted.
        os.chmod(spool, 0o777)
        os.chmod(spool / "requests", 0o777)
        os.chmod(spool / "responses", 0o777)

        cmd = docker_command(
            image_id=image_id,
            repo_root=ROOT,
            spool_root=spool,
            child_command=child_command,
        )
        proc = subprocess.Popen(
            cmd,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        start = time.monotonic()
        processed: set[str] = set()
        responses: list[dict[str, Any]] = []
        try:
            while proc.poll() is None:
                responses.extend(
                    serve_pending_once(
                        spool,
                        output_root,
                        processed=processed,
                        allowed_effect_types=allowed_effect_types,
                    )
                )
                if time.monotonic() - start > timeout_s:
                    proc.kill()
                    raise ConfinedEffectError("CONFINED_CHILD_TIMEOUT")
                time.sleep(0.02)
            responses.extend(
                serve_pending_once(
                    spool,
                    output_root,
                    processed=processed,
                    allowed_effect_types=allowed_effect_types,
                )
            )
            stdout, stderr = proc.communicate(timeout=2)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()
        return {
            "schema": "PROJECT_BRAIN_CONFINED_EFFECT_RUN_V1",
            "image_id": image_id,
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "broker_responses": responses,
            "broker_applied": sum(1 for x in responses if x.get("status") == "applied"),
            "broker_denied": sum(1 for x in responses if x.get("status") == "denied"),
            "network_mode": "none",
            "repo_mount": "read_only",
            "rootfs": "read_only",
            "capabilities": "drop_all",
            "no_new_privileges": True,
            "output_root_mounted_into_child": False,
        }

"""Declarative guest-state operation compiler for OSWorld 2.1.

The output is Python source executed inside the OSWorld guest through the
benchmark's own PythonController. The operation language is deliberately small:
it exposes ordinary file/state transforms and allowlisted application CLIs while
keeping raw benchmark-specific source/evaluator access out of the policy surface.
"""
from __future__ import annotations

import json
import shlex
from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_OSWORLD_V21_STATE_OPS_V1"
MAX_OPS = 32
MAX_TEXT_BYTES = 1_000_000
MAX_ARGS = 64
ALLOWED_CLI = frozenset({
    "libreoffice", "soffice", "ffmpeg", "ffprobe",
    "convert", "magick", "identify", "pdftotext", "pandoc",
})

FORBIDDEN_CLI_ARGUMENTS = {
    "pandoc": frozenset({"--filter", "--lua-filter", "-F", "-L"}),
    "libreoffice": frozenset({"--accept"}),
    "soffice": frozenset({"--accept"}),
}


class StateOpsError(ValueError):
    pass


def _path(value: Any) -> str:
    if not isinstance(value, str) or not value.startswith("/"):
        raise StateOpsError("ABSOLUTE_GUEST_PATH_REQUIRED")
    p = PurePosixPath(value)
    if ".." in p.parts:
        raise StateOpsError("PARENT_TRAVERSAL_FORBIDDEN")
    text = str(p)
    forbidden = (
        "/root", "/proc", "/sys", "/dev", "/run/secrets",
        "/evaluation_examples", "/benchmark_releases",
    )
    if any(text == x or text.startswith(x + "/") for x in forbidden):
        raise StateOpsError("PROTECTED_PATH_FORBIDDEN")
    return text


def _ops(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not value:
        raise StateOpsError("OPS_REQUIRED")
    if len(value) > MAX_OPS:
        raise StateOpsError("TOO_MANY_OPS")
    if any(not isinstance(x, Mapping) for x in value):
        raise StateOpsError("OP_NOT_OBJECT")
    return value


def _compile_op(op: Mapping[str, Any]) -> str:
    kind = str(op.get("type") or "").strip().upper()

    if kind == "MKDIR":
        p = _path(op.get("path"))
        return f"pathlib.Path({p!r}).mkdir(parents=True, exist_ok=True)"

    if kind == "WRITE_TEXT":
        p = _path(op.get("path"))
        text = op.get("text")
        if not isinstance(text, str):
            raise StateOpsError("WRITE_TEXT_TEXT_REQUIRED")
        if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
            raise StateOpsError("WRITE_TEXT_TOO_LARGE")
        return (
            f"_p=pathlib.Path({p!r}); _p.parent.mkdir(parents=True, exist_ok=True); "
            f"_p.write_text({text!r}, encoding='utf-8')"
        )

    if kind == "COPY":
        src = _path(op.get("src"))
        dst = _path(op.get("dst"))
        return (
            f"_s=pathlib.Path({src!r}); _d=pathlib.Path({dst!r}); "
            "_d.parent.mkdir(parents=True, exist_ok=True); "
            "shutil.copy2(_s, _d)"
        )

    if kind == "MOVE":
        src = _path(op.get("src"))
        dst = _path(op.get("dst"))
        return (
            f"_s=pathlib.Path({src!r}); _d=pathlib.Path({dst!r}); "
            "_d.parent.mkdir(parents=True, exist_ok=True); "
            "shutil.move(str(_s), str(_d))"
        )

    if kind == "DELETE":
        p = _path(op.get("path"))
        return (
            f"_p=pathlib.Path({p!r}); "
            "shutil.rmtree(_p) if _p.is_dir() else (_p.unlink() if _p.exists() else None)"
        )

    if kind == "READ_TEXT":
        p = _path(op.get("path"))
        max_chars = op.get("max_chars", 8000)
        if isinstance(max_chars, bool) or not isinstance(max_chars, int) or not 1 <= max_chars <= 20000:
            raise StateOpsError("READ_TEXT_MAX_CHARS_INVALID")
        return f"_p=pathlib.Path({p!r}); print(_p.read_text(encoding='utf-8')[:{max_chars}])"

    if kind == "ASSERT_PATH_EXISTS":
        p = _path(op.get("path"))
        return (
            f"_p=pathlib.Path({p!r}); "
            f"assert _p.exists(), 'PATH_MISSING:{p}'; print('ASSERT_PATH_EXISTS:PASS:{p}')"
        )

    if kind == "ASSERT_TEXT_EQUALS":
        p = _path(op.get("path"))
        text = op.get("text")
        if not isinstance(text, str):
            raise StateOpsError("ASSERT_TEXT_EQUALS_TEXT_REQUIRED")
        if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
            raise StateOpsError("ASSERT_TEXT_EQUALS_TEXT_TOO_LARGE")
        return (
            f"_p=pathlib.Path({p!r}); _got=_p.read_text(encoding='utf-8'); "
            f"assert _got=={text!r}, 'TEXT_MISMATCH'; print('ASSERT_TEXT_EQUALS:PASS:{p}')"
        )

    if kind == "SHA256_FILE":
        p = _path(op.get("path"))
        return (
            f"_p=pathlib.Path({p!r}); "
            "print(hashlib.sha256(_p.read_bytes()).hexdigest())"
        )

    if kind == "JSON_SET":
        p = _path(op.get("path"))
        key = op.get("key")
        if not isinstance(key, str) or not key:
            raise StateOpsError("JSON_SET_KEY_REQUIRED")
        value = op.get("value")
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return (
            f"_p=pathlib.Path({p!r}); _o=json.loads(_p.read_text(encoding='utf-8')); "
            f"_o[{key!r}]=json.loads({encoded!r}); "
            "_p.write_text(json.dumps(_o,ensure_ascii=False,indent=2)+'\\n',encoding='utf-8')"
        )

    if kind == "RUN_CLI":
        argv = op.get("argv")
        if not isinstance(argv, Sequence) or isinstance(argv, (str, bytes)) or not argv:
            raise StateOpsError("RUN_CLI_ARGV_REQUIRED")
        if len(argv) > MAX_ARGS or any(not isinstance(x, str) for x in argv):
            raise StateOpsError("RUN_CLI_ARGV_INVALID")
        exe = PurePosixPath(argv[0]).name
        if exe not in ALLOWED_CLI:
            raise StateOpsError("RUN_CLI_EXECUTABLE_NOT_ALLOWED:" + exe)
        forbidden_args = FORBIDDEN_CLI_ARGUMENTS.get(exe, frozenset())
        for index, arg in enumerate(argv[1:], start=1):
            if arg in forbidden_args or any(
                arg.startswith(prefix + "=")
                for prefix in forbidden_args
                if prefix.startswith("--")
            ):
                raise StateOpsError("RUN_CLI_ARGUMENT_NOT_ALLOWED:" + exe + ":" + arg)
            if arg.startswith("/"):
                _path(arg)
            if exe == "pandoc" and index > 0 and argv[index - 1] in {"--filter", "--lua-filter", "-F", "-L"}:
                raise StateOpsError("RUN_CLI_ARGUMENT_NOT_ALLOWED:pandoc:" + argv[index - 1])
        timeout = op.get("timeout_s", 60)
        if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 300:
            raise StateOpsError("RUN_CLI_TIMEOUT_INVALID")
        return (
            f"_r=subprocess.run({list(argv)!r},check=True,capture_output=True,text=True,"
            f"timeout={timeout}); print(_r.stdout[-4000:])"
        )

    raise StateOpsError("UNSUPPORTED_STATE_OP:" + kind)


def compile_state_ops(payload: Mapping[str, Any]) -> str:
    if not isinstance(payload, Mapping):
        raise StateOpsError("PAYLOAD_NOT_OBJECT")
    ops = _ops(payload.get("ops"))
    statements = [_compile_op(op) for op in ops]
    prelude = "import hashlib,json,pathlib,shutil,subprocess"
    return prelude + "; " + "; ".join(statements)

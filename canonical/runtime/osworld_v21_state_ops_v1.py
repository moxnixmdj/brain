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


def normalize_state_op(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise StateOpsError("OP_NOT_OBJECT")
    out = dict(value)
    primary = str(out.get("type") or "").strip().upper()
    alias = str(out.get("op") or "").strip().upper()
    if primary and alias and primary != alias:
        raise StateOpsError("OP_TYPE_ALIAS_CONFLICT")
    kind = primary or alias
    if not kind:
        raise StateOpsError("OP_TYPE_REQUIRED")
    out["type"] = kind
    out.pop("op", None)

    if kind == "RUN_CLI":
        argv = out.get("argv")
        args = out.get("args")
        if argv is not None and args is not None and argv != args:
            raise StateOpsError("RUN_CLI_ARGV_ALIAS_CONFLICT")
        if argv is None and args is not None:
            out["argv"] = args
        out.pop("args", None)
    return out


def normalize_state_ops(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise StateOpsError("OPS_REQUIRED")
    if len(value) > MAX_OPS:
        raise StateOpsError("TOO_MANY_OPS")
    return [normalize_state_op(x) for x in value]


def _ops(value: Any) -> list[Mapping[str, Any]]:
    return normalize_state_ops(value)


def _compile_op(op: Mapping[str, Any]) -> str:
    kind = str(op.get("type") or "").strip().upper()

    if kind == "MKDIR":
        p = _path(op.get("path"))
        return (
            f"_p=pathlib.Path({p!r}); _p.mkdir(parents=True, exist_ok=True); "
            f"print('MKDIR:PASS:{p}:exists='+str(_p.is_dir()))"
        )

    if kind == "WRITE_TEXT":
        p = _path(op.get("path"))
        text = op.get("text")
        if not isinstance(text, str):
            raise StateOpsError("WRITE_TEXT_TEXT_REQUIRED")
        if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
            raise StateOpsError("WRITE_TEXT_TOO_LARGE")
        return (
            f"_p=pathlib.Path({p!r}); _p.parent.mkdir(parents=True, exist_ok=True); "
            f"_n=_p.write_text({text!r}, encoding='utf-8'); "
            f"_b=_p.read_bytes(); print('WRITE_TEXT:PASS:{p}:chars='+str(_n)+':bytes='+str(len(_b))+':sha256='+hashlib.sha256(_b).hexdigest())"
        )

    if kind == "COPY":
        src = _path(op.get("src"))
        dst = _path(op.get("dst"))
        return (
            f"_s=pathlib.Path({src!r}); _d=pathlib.Path({dst!r}); "
            "_d.parent.mkdir(parents=True, exist_ok=True); "
            "shutil.copy2(_s, _d); _b=_d.read_bytes(); "
            f"print('COPY:PASS:{src}->{dst}:bytes='+str(len(_b))+':sha256='+hashlib.sha256(_b).hexdigest())"
        )

    if kind == "MOVE":
        src = _path(op.get("src"))
        dst = _path(op.get("dst"))
        return (
            f"_s=pathlib.Path({src!r}); _d=pathlib.Path({dst!r}); "
            "_d.parent.mkdir(parents=True, exist_ok=True); "
            "shutil.move(str(_s), str(_d)); "
            f"print('MOVE:PASS:{src}->{dst}:exists='+str(_d.exists()))"
        )

    if kind == "DELETE":
        p = _path(op.get("path"))
        return (
            f"_p=pathlib.Path({p!r}); "
            "shutil.rmtree(_p) if _p.is_dir() else (_p.unlink() if _p.exists() else None); "
            f"print('DELETE:PASS:{p}:exists='+str(_p.exists()))"
        )

    if kind == "LIST_DIR":
        p = _path(op.get("path"))
        max_entries = op.get("max_entries", 200)
        if isinstance(max_entries, bool) or not isinstance(max_entries, int) or not 1 <= max_entries <= 500:
            raise StateOpsError("LIST_DIR_MAX_ENTRIES_INVALID")
        return (
            f"_p=pathlib.Path({p!r}); assert _p.is_dir(), 'NOT_DIRECTORY:{p}'; "
            f"_rows=[]; "
            f"[_rows.append({{'name':x.name,'path':str(x),'is_file':x.is_file(),'is_dir':x.is_dir(),'size':(x.stat().st_size if x.is_file() else None)}}) "
            f"for x in sorted(_p.iterdir(), key=lambda z:z.name.casefold())[:{max_entries}]]; "
            f"print('LIST_DIR:PASS:{p}:'+json.dumps(_rows,ensure_ascii=False,separators=(',',':')))"
        )

    if kind == "TEXT_REPLACE":
        p = _path(op.get("path"))
        old = op.get("old")
        new = op.get("new")
        replace_all = op.get("replace_all", True)
        if not isinstance(old, str) or not old:
            raise StateOpsError("TEXT_REPLACE_OLD_REQUIRED")
        if not isinstance(new, str):
            raise StateOpsError("TEXT_REPLACE_NEW_REQUIRED")
        if not isinstance(replace_all, bool):
            raise StateOpsError("TEXT_REPLACE_ALL_INVALID")
        if len(old.encode("utf-8")) > MAX_TEXT_BYTES or len(new.encode("utf-8")) > MAX_TEXT_BYTES:
            raise StateOpsError("TEXT_REPLACE_VALUE_TOO_LARGE")
        count_expr = "-1" if replace_all else "1"
        return (
            f"_p=pathlib.Path({p!r}); _src=_p.read_text(encoding='utf-8'); "
            f"assert {old!r} in _src, 'TEXT_REPLACE_OLD_NOT_FOUND'; "
            f"_dst=_src.replace({old!r},{new!r},{count_expr}); "
            f"_n=_p.write_text(_dst,encoding='utf-8'); _b=_p.read_bytes(); "
            f"print('TEXT_REPLACE:PASS:{p}:chars='+str(_n)+':sha256='+hashlib.sha256(_b).hexdigest())"
        )

    if kind == "READ_TEXT":
        p = _path(op.get("path"))
        max_chars = op.get("max_chars", 8000)
        if isinstance(max_chars, bool) or not isinstance(max_chars, int) or not 1 <= max_chars <= 20000:
            raise StateOpsError("READ_TEXT_MAX_CHARS_INVALID")
        return (
            f"_p=pathlib.Path({p!r}); _v=_p.read_text(encoding='utf-8')[:{max_chars}]; "
            f"print('READ_TEXT:PASS:{p}:chars='+str(len(_v))); print(_v)"
        )

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
            f"print('SHA256_FILE:PASS:{p}:sha256='+hashlib.sha256(_p.read_bytes()).hexdigest())"
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
            "_p.write_text(json.dumps(_o,ensure_ascii=False,indent=2)+'\\n',encoding='utf-8'); "
            f"_b=_p.read_bytes(); print('JSON_SET:PASS:{p}:key={key}:sha256='+hashlib.sha256(_b).hexdigest())"
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
            f"timeout={timeout}); print('RUN_CLI:PASS:{exe}:returncode='+str(_r.returncode)); "
            "print(_r.stdout[-4000:]) if _r.stdout else None"
        )

    raise StateOpsError("UNSUPPORTED_STATE_OP:" + kind)


def compile_state_ops(payload: Mapping[str, Any]) -> str:
    if not isinstance(payload, Mapping):
        raise StateOpsError("PAYLOAD_NOT_OBJECT")
    ops = _ops(payload.get("ops"))
    statements = [_compile_op(op) for op in ops]
    prelude = "import hashlib,json,pathlib,shutil,subprocess"
    return prelude + "; " + "; ".join(statements)

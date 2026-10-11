"""Typed code-workspace operations for the model-independent OSWorld subject.

The policy never receives a shell. Each operation is a fixed host program with
validated data arguments, bounded paths, postcondition receipts, and explicit
benchmark-source quarantine.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import PurePosixPath
from typing import Any, Mapping

MAX_TEXT_BYTES = 1_000_000
MAX_OUTPUT = 12000
SAFE_ROOTS = ("/home/oai",)
PROTECTED_TOKENS = (
    "/evaluation_examples",
    "/benchmark_releases",
    "osworld_v2_tasks",
    "desktop_env/evaluators",
)


class CodeOpsError(RuntimeError):
    pass


def _safe_path(value: Any, *, allow_dir: bool = True) -> str:
    if not isinstance(value, str) or not value.startswith("/"):
        raise CodeOpsError("ABSOLUTE_CODE_PATH_REQUIRED")
    p = PurePosixPath(value)
    if ".." in p.parts:
        raise CodeOpsError("CODE_PATH_TRAVERSAL_FORBIDDEN")
    text = str(p)
    if not any(text == root or text.startswith(root + "/") for root in SAFE_ROOTS):
        raise CodeOpsError("CODE_PATH_OUTSIDE_SAFE_ROOT")
    if any(token in text for token in PROTECTED_TOKENS):
        raise CodeOpsError("CODE_PATH_PROTECTED")
    return text


def _text(value: Any, name: str, limit: int = MAX_TEXT_BYTES) -> str:
    if not isinstance(value, str):
        raise CodeOpsError(name + "_REQUIRED")
    if len(value.encode("utf-8")) > limit:
        raise CodeOpsError(name + "_TOO_LARGE")
    return value


def _relative_target(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise CodeOpsError("PYTEST_TARGET_INVALID")
    p = PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts or len(value) > 300:
        raise CodeOpsError("PYTEST_TARGET_INVALID")
    if any(token in value for token in PROTECTED_TOKENS):
        raise CodeOpsError("PYTEST_TARGET_PROTECTED")
    return str(p)


def _program_header() -> str:
    return (
        "import hashlib,json,pathlib,subprocess,sys\n"
        "PROTECTED_TOKENS=" + repr(PROTECTED_TOKENS) + "\n"
        "def _scan(root):\n"
        "  total=0\n"
        "  for p in sorted(pathlib.Path(root).rglob('*')):\n"
        "    if not p.is_file() or p.suffix.lower() not in {'.py','.toml','.ini','.cfg','.json','.yaml','.yml','.sh'}: continue\n"
        "    total+=1\n"
        "    if total>500: raise RuntimeError('WORKSPACE_SCAN_FILE_LIMIT')\n"
        "    try: data=p.read_text(encoding='utf-8',errors='ignore')[:200000]\n"
        "    except Exception: continue\n"
        "    if any(tok in data for tok in PROTECTED_TOKENS): raise RuntimeError('WORKSPACE_SOURCE_QUARANTINE:'+str(p))\n"
    )


@dataclass
class OSWorldHostCodeOps:
    environment: Any | None = None

    def bind_environment(self, environment: Any) -> None:
        controller = getattr(environment, "controller", None)
        if controller is None or not callable(getattr(controller, "execute_python_command", None)):
            raise CodeOpsError("DESKTOP_ENV_PYTHON_CONTROLLER_MISSING")
        self.environment = environment

    def _execute(self, program: str) -> Mapping[str, Any]:
        if self.environment is None:
            raise CodeOpsError("CODE_ENVIRONMENT_NOT_BOUND")
        try:
            result = self.environment.controller.execute_python_command(program)
        except Exception as exc:
            raise CodeOpsError("CODE_OP_EXECUTION_EXCEPTION:" + type(exc).__name__) from exc
        if not isinstance(result, Mapping):
            raise CodeOpsError("CODE_OP_NO_RECEIPT")
        status = str(result.get("status") or "").strip().lower()
        error = result.get("error")
        if error or status in {"error", "failed", "failure"}:
            raise CodeOpsError("CODE_OP_CONTROLLER_FAILURE:" + str(error or status)[:2000])
        return result

    def run(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise CodeOpsError("CODE_OP_NOT_OBJECT")
        op = str(payload.get("operation") or "").strip().upper()
        args = payload.get("args", {})
        if not isinstance(args, Mapping):
            raise CodeOpsError("CODE_OP_ARGS_NOT_OBJECT")

        if op == "READ_TEXT":
            path = _safe_path(args.get("path"))
            max_chars = args.get("max_chars", 12000)
            if isinstance(max_chars, bool) or not isinstance(max_chars, int) or not 1 <= max_chars <= 20000:
                raise CodeOpsError("READ_TEXT_MAX_CHARS_INVALID")
            program = _program_header() + (
                f"p=pathlib.Path({path!r})\n"
                f"v=p.read_text(encoding='utf-8')[:{max_chars}]\n"
                "print(json.dumps({'ok':True,'operation':'READ_TEXT','path':str(p),'text':v,'chars':len(v)},ensure_ascii=False))\n"
            )

        elif op == "WRITE_TEXT_VERIFIED":
            path = _safe_path(args.get("path"))
            text = _text(args.get("text"), "WRITE_TEXT")
            program = _program_header() + (
                f"p=pathlib.Path({path!r}); p.parent.mkdir(parents=True,exist_ok=True)\n"
                f"expected={text!r}\n"
                "p.write_text(expected,encoding='utf-8')\n"
                "actual=p.read_text(encoding='utf-8')\n"
                "assert actual==expected,'CODE_WRITE_READBACK_MISMATCH'\n"
                "print(json.dumps({'ok':True,'operation':'WRITE_TEXT_VERIFIED','path':str(p),'sha256':hashlib.sha256(actual.encode()).hexdigest()},ensure_ascii=False))\n"
            )

        elif op == "REPLACE_TEXT_VERIFIED":
            path = _safe_path(args.get("path"))
            old = _text(args.get("old"), "REPLACE_OLD")
            new = _text(args.get("new"), "REPLACE_NEW")
            if not old:
                raise CodeOpsError("REPLACE_OLD_EMPTY")
            replace_all = args.get("replace_all", True)
            if not isinstance(replace_all, bool):
                raise CodeOpsError("REPLACE_ALL_INVALID")
            count = -1 if replace_all else 1
            program = _program_header() + (
                f"p=pathlib.Path({path!r}); old={old!r}; new={new!r}\n"
                "src=p.read_text(encoding='utf-8')\n"
                "assert old in src,'CODE_REPLACE_OLD_NOT_FOUND'\n"
                f"dst=src.replace(old,new,{count})\n"
                "p.write_text(dst,encoding='utf-8')\n"
                "actual=p.read_text(encoding='utf-8')\n"
                "assert actual==dst and new in actual,'CODE_REPLACE_READBACK_MISMATCH'\n"
                "print(json.dumps({'ok':True,'operation':'REPLACE_TEXT_VERIFIED','path':str(p),'sha256':hashlib.sha256(actual.encode()).hexdigest()},ensure_ascii=False))\n"
            )

        elif op == "PYTHON_COMPILE":
            path = _safe_path(args.get("path"))
            program = _program_header() + (
                f"p=pathlib.Path({path!r}); src=p.read_text(encoding='utf-8')\n"
                "assert not any(tok in src for tok in PROTECTED_TOKENS),'CODE_SOURCE_QUARANTINE'\n"
                "compile(src,str(p),'exec')\n"
                "print(json.dumps({'ok':True,'operation':'PYTHON_COMPILE','path':str(p)},ensure_ascii=False))\n"
            )

        elif op == "PYTEST":
            cwd = _safe_path(args.get("cwd"))
            target = _relative_target(args.get("target"))
            timeout = args.get("timeout_s", 120)
            if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 180:
                raise CodeOpsError("PYTEST_TIMEOUT_INVALID")
            target_line = "None" if target is None else repr(target)
            program = _program_header() + (
                f"cwd={cwd!r}; _scan(cwd); target={target_line}\n"
                "cmd=[sys.executable,'-m','pytest','-q'] + ([target] if target else [])\n"
                f"r=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout={timeout})\n"
                "print(json.dumps({'ok':r.returncode==0,'operation':'PYTEST','cwd':cwd,'target':target,'returncode':r.returncode,'stdout':r.stdout[-8000:],'stderr':r.stderr[-4000:]},ensure_ascii=False))\n"
            )

        elif op == "GIT_STATUS":
            cwd = _safe_path(args.get("cwd"))
            program = _program_header() + (
                f"cwd={cwd!r}; _scan(cwd)\n"
                "r=subprocess.run(['git','status','--short'],cwd=cwd,capture_output=True,text=True,timeout=30)\n"
                "print(json.dumps({'ok':r.returncode==0,'operation':'GIT_STATUS','cwd':cwd,'returncode':r.returncode,'stdout':r.stdout[-8000:],'stderr':r.stderr[-2000:]},ensure_ascii=False))\n"
            )

        else:
            raise CodeOpsError("CODE_OPERATION_NOT_ALLOWED:" + op)

        result = self._execute(program)
        output = str(result.get("output") or "")
        structured = None
        for line in reversed(output.splitlines()):
            try:
                parsed = json.loads(line)
            except Exception:
                continue
            if isinstance(parsed, Mapping) and parsed.get("operation"):
                structured = dict(parsed)
                break
        if structured is None:
            raise CodeOpsError("CODE_OP_STRUCTURED_RECEIPT_MISSING")
        return {
            "type": "CODE_OP",
            "ok": structured.get("ok") is True,
            "operation": op,
            "result": structured,
            "status": str(result.get("status") or "ok"),
            "output": output[-MAX_OUTPUT:],
        }

"""Harbor task-environment transport for Project Brain.

This is deliberately cognition-free.  It gives Brain-owned controllers a narrow
execution boundary for a Harbor BaseEnvironment without importing any model,
benchmark task, or verifier logic.  Unknown actions fail closed.
"""
from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Any, Mapping


class HarborTransportError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExecReceipt:
    command: str
    returncode: int
    stdout: str
    stderr: str


class HarborEnvironmentTransport:
    """Minimal deterministic wrapper over Harbor's BaseEnvironment.exec."""

    def __init__(self, environment: Any):
        if environment is None or not callable(getattr(environment, "exec", None)):
            raise HarborTransportError("HARBOR_ENVIRONMENT_EXEC_UNAVAILABLE")
        self._environment = environment

    async def exec(self, command: str, *, timeout_sec: int | None = None) -> ExecReceipt:
        if not isinstance(command, str) or not command.strip():
            raise HarborTransportError("COMMAND_INVALID")
        if timeout_sec is not None and (
            not isinstance(timeout_sec, int)
            or isinstance(timeout_sec, bool)
            or timeout_sec < 1
            or timeout_sec > 3600
        ):
            raise HarborTransportError("TIMEOUT_INVALID")

        kwargs: dict[str, Any] = {}
        if timeout_sec is not None:
            kwargs["timeout_sec"] = timeout_sec
        result = await self._environment.exec(command, **kwargs)

        rc = getattr(result, "return_code", getattr(result, "returncode", getattr(result, "exit_code", None)))
        stdout = getattr(result, "stdout", "")
        stderr = getattr(result, "stderr", "")
        if rc is None and isinstance(result, Mapping):
            rc = result.get("return_code", result.get("returncode", result.get("exit_code")))
            stdout = result.get("stdout", stdout)
            stderr = result.get("stderr", stderr)
        if not isinstance(rc, int) or isinstance(rc, bool):
            raise HarborTransportError("EXEC_RECEIPT_RETURNCODE_INVALID")
        return ExecReceipt(
            command=command,
            returncode=rc,
            stdout=str(stdout or ""),
            stderr=str(stderr or ""),
        )

    async def read_text(self, path: str, *, max_bytes: int = 1_000_000) -> str:
        if not isinstance(path, str) or not path.startswith("/") or "\x00" in path:
            raise HarborTransportError("ABSOLUTE_PATH_REQUIRED")
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or not (1 <= max_bytes <= 10_000_000):
            raise HarborTransportError("MAX_BYTES_INVALID")
        cmd=(
            "python3 - <<'PY'\n"
            "from pathlib import Path\n"
            f"p=Path({path!r})\n"
            f"raw=p.read_bytes()[:{max_bytes}]\n"
            "print(raw.decode('utf-8','replace'), end='')\n"
            "PY"
        )
        receipt=await self.exec(cmd)
        if receipt.returncode != 0:
            raise HarborTransportError("READ_FAILED:"+receipt.stderr[-500:])
        return receipt.stdout

    async def write_text(self, path: str, text: str) -> ExecReceipt:
        if not isinstance(path, str) or not path.startswith("/") or "\x00" in path:
            raise HarborTransportError("ABSOLUTE_PATH_REQUIRED")
        if not isinstance(text, str):
            raise HarborTransportError("TEXT_INVALID")
        # Base64 avoids shell interpolation of untrusted task text.
        import base64
        payload=base64.b64encode(text.encode("utf-8")).decode("ascii")
        cmd=(
            "python3 - <<'PY'\n"
            "from pathlib import Path\n"
            "import base64\n"
            f"p=Path({path!r}); p.parent.mkdir(parents=True,exist_ok=True)\n"
            f"p.write_bytes(base64.b64decode({payload!r}))\n"
            "PY"
        )
        receipt=await self.exec(cmd)
        if receipt.returncode != 0:
            raise HarborTransportError("WRITE_FAILED:"+receipt.stderr[-500:])
        return receipt


async def execute_predeclared_action(transport: HarborEnvironmentTransport, action: Mapping[str, Any]) -> dict:
    """Execute only the small transport action vocabulary used by the adapter."""
    if not isinstance(action, Mapping):
        raise HarborTransportError("ACTION_NOT_OBJECT")
    typ=action.get("type")
    args=action.get("args") or {}
    if not isinstance(args, Mapping):
        raise HarborTransportError("ACTION_ARGS_NOT_OBJECT")

    if typ == "terminal_exec":
        receipt=await transport.exec(str(args.get("command") or ""), timeout_sec=args.get("timeout_sec"))
        return {
            "type":typ,
            "returncode":receipt.returncode,
            "stdout":receipt.stdout,
            "stderr":receipt.stderr,
        }
    if typ == "terminal_read_text":
        body=await transport.read_text(str(args.get("path") or ""), max_bytes=int(args.get("max_bytes",1_000_000)))
        return {"type":typ,"text":body}
    if typ == "terminal_write_text":
        receipt=await transport.write_text(str(args.get("path") or ""), str(args.get("text") or ""))
        return {"type":typ,"returncode":receipt.returncode}
    raise HarborTransportError("ACTION_TYPE_REJECTED:"+str(typ))

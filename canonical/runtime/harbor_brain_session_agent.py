"""Harbor external-agent adapter for a Project Brain command session.

The adapter is transport/integration glue only:
- Harbor owns task setup and verifier lifecycle.
- The task instruction is received only through Harbor's BaseAgent.run contract.
- Brain commands are typed JSON records fetched from a predeclared Git branch.
- Commands execute only through HarborEnvironmentTransport/BaseEnvironment.exec.
- The adapter cannot return success without a Brain terminal authorization record.
- It never reads benchmark verifier logic or task files from the host repository.

This module supplies no semantic/cognitive capability and earns no capability credit.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Mapping

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

from canonical.runtime.harbor_environment_transport import (
    HarborEnvironmentTransport,
    execute_predeclared_action,
)


COMMAND_SCHEMA = "PROJECT_BRAIN_HARBOR_COMMAND_V1"
AUTH_SCHEMA = "BRAIN_SESSION_TERMINAL_AUTHORIZATION_V1"


class BrainHarborSessionError(RuntimeError):
    pass


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if check and proc.returncode != 0:
        raise BrainHarborSessionError(
            "GIT_FAILED:" + " ".join(args) + ":" + (proc.stderr or "")[-800:]
        )
    return proc


def _validate_authorization(auth: Any, session_id: str) -> dict[str, Any]:
    if not isinstance(auth, Mapping):
        raise BrainHarborSessionError("TERMINAL_AUTHORIZATION_NOT_OBJECT")
    if auth.get("schema") != AUTH_SCHEMA:
        raise BrainHarborSessionError("TERMINAL_AUTHORIZATION_SCHEMA_INVALID")
    if auth.get("session_id") != session_id:
        raise BrainHarborSessionError("TERMINAL_AUTHORIZATION_SESSION_MISMATCH")
    if auth.get("submission_authorized") is not True:
        raise BrainHarborSessionError("TERMINAL_AUTHORIZATION_FALSE")
    if auth.get("known_relevant_failures") not in ([], None):
        raise BrainHarborSessionError("KNOWN_RELEVANT_FAILURES_REMAIN")

    criteria = auth.get("acceptance_criteria")
    if not isinstance(criteria, list) or not criteria:
        raise BrainHarborSessionError("ACCEPTANCE_CRITERIA_EVIDENCE_MISSING")
    for row in criteria:
        if (
            not isinstance(row, Mapping)
            or row.get("status") != "PASS"
            or not str(row.get("evidence") or "").strip()
        ):
            raise BrainHarborSessionError("ACCEPTANCE_CRITERIA_NOT_ALL_PASS")

    checks = auth.get("verification_commands")
    if not isinstance(checks, list) or not checks:
        raise BrainHarborSessionError("VERIFICATION_COMMANDS_MISSING")
    for row in checks:
        if (
            not isinstance(row, Mapping)
            or row.get("exit_code") != 0
            or not str(row.get("command") or "").strip()
        ):
            raise BrainHarborSessionError("VERIFICATION_COMMANDS_NOT_ALL_PASS")

    canonical = json.dumps(auth, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {
        "authorized": True,
        "authorization_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "acceptance_criterion_count": len(criteria),
        "verification_command_count": len(checks),
    }


class BrainHarborSessionAgent(BaseAgent):
    """External Harbor agent that relays typed Project Brain commands."""

    def __init__(
        self,
        logs_dir: Path,
        *,
        control_repo: str | Path | None = None,
        control_branch: str | None = None,
        command_prefix: str = "harbor_brain_session/commands",
        poll_interval_sec: float = 2.0,
        command_wait_timeout_sec: int = 7200,
        max_steps: int = 80,
        **kwargs: Any,
    ) -> None:
        super().__init__(logs_dir, **kwargs)
        raw_repo = control_repo or os.environ.get("GITHUB_WORKSPACE") or os.getcwd()
        self.control_repo = Path(raw_repo).expanduser().resolve()
        self.control_branch = str(
            control_branch
            or os.environ.get("PROJECT_BRAIN_HARBOR_CONTROL_BRANCH")
            or os.environ.get("GITHUB_HEAD_REF")
            or ""
        ).strip()
        self.command_prefix = str(command_prefix).strip().strip("/")
        self.poll_interval_sec = float(poll_interval_sec)
        self.command_wait_timeout_sec = int(command_wait_timeout_sec)
        self.max_steps = int(max_steps)

        if not (self.control_repo / ".git").exists():
            raise BrainHarborSessionError("CONTROL_REPOSITORY_NOT_GIT")
        if not self.control_branch:
            raise BrainHarborSessionError("CONTROL_BRANCH_REQUIRED")
        if not self.command_prefix:
            raise BrainHarborSessionError("COMMAND_PREFIX_REQUIRED")
        if not (0.05 <= self.poll_interval_sec <= 60):
            raise BrainHarborSessionError("POLL_INTERVAL_INVALID")
        if not (1 <= self.command_wait_timeout_sec <= 21600):
            raise BrainHarborSessionError("COMMAND_WAIT_TIMEOUT_INVALID")
        if not (1 <= self.max_steps <= 256):
            raise BrainHarborSessionError("MAX_STEPS_INVALID")

    @staticmethod
    def name() -> str:
        return "project-brain-harbor-session"

    def version(self) -> str | None:
        return "1.0.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        if environment is None or not callable(getattr(environment, "exec", None)):
            raise BrainHarborSessionError("HARBOR_ENVIRONMENT_EXEC_UNAVAILABLE")
        # Deliberately no environment mutation during setup.
        return None

    def _command_path(self, step: int) -> str:
        return f"{self.command_prefix}/{step:03d}.json"

    def _read_remote_command_once(self, step: int) -> dict[str, Any] | None:
        fetch = _git(
            self.control_repo,
            "fetch",
            "--quiet",
            "origin",
            self.control_branch,
            check=False,
        )
        if fetch.returncode != 0:
            return None
        path = self._command_path(step)
        show = _git(
            self.control_repo,
            "show",
            f"FETCH_HEAD:{path}",
            check=False,
        )
        if show.returncode != 0:
            return None
        try:
            payload = json.loads(show.stdout)
        except json.JSONDecodeError as exc:
            raise BrainHarborSessionError("COMMAND_JSON_INVALID:" + path) from exc
        if not isinstance(payload, dict):
            raise BrainHarborSessionError("COMMAND_NOT_OBJECT:" + path)
        return payload

    async def _wait_command(self, step: int) -> dict[str, Any]:
        deadline = time.monotonic() + self.command_wait_timeout_sec
        while time.monotonic() < deadline:
            payload = await asyncio.to_thread(self._read_remote_command_once, step)
            if payload is not None:
                return payload
            await asyncio.sleep(self.poll_interval_sec)
        raise BrainHarborSessionError("COMMAND_WAIT_TIMEOUT:" + str(step))

    def _validate_command(
        self,
        payload: Mapping[str, Any],
        *,
        session_id: str,
        step: int,
    ) -> Mapping[str, Any]:
        if payload.get("schema") != COMMAND_SCHEMA:
            raise BrainHarborSessionError("COMMAND_SCHEMA_INVALID")
        if payload.get("session_id") != session_id:
            raise BrainHarborSessionError("COMMAND_SESSION_MISMATCH")
        if payload.get("step") != step:
            raise BrainHarborSessionError("COMMAND_STEP_MISMATCH")
        action = payload.get("action")
        if not isinstance(action, Mapping):
            raise BrainHarborSessionError("COMMAND_ACTION_INVALID")
        return action

    def _write_receipt(self, session_id: str, step: int, value: Mapping[str, Any]) -> None:
        root = self.logs_dir / "project_brain_harbor_session"
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"{step:03d}.json"
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        # Explicit stdout sentinel lets an authorized external controller observe
        # progress from the carrier log without reading verifier files.
        print(
            "PROJECT_BRAIN_HARBOR_OBSERVATION "
            + json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
            flush=True,
        )

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        session_id = str(self.session_id or "").strip()
        if not session_id:
            raise BrainHarborSessionError("HARBOR_SESSION_ID_REQUIRED")
        if not isinstance(instruction, str) or not instruction.strip():
            raise BrainHarborSessionError("TASK_INSTRUCTION_REQUIRED")

        transport = HarborEnvironmentTransport(environment)
        instruction_sha = _sha_text(instruction)
        start = {
            "schema": "PROJECT_BRAIN_HARBOR_SESSION_START_V1",
            "session_id": session_id,
            "instruction_sha256": instruction_sha,
            "instruction_char_count": len(instruction),
            "verifier_content_read": False,
        }
        self._write_receipt(session_id, -1, start)
        print(
            "PROJECT_BRAIN_HARBOR_INSTRUCTION "
            + json.dumps(
                {
                    "session_id": session_id,
                    "instruction": instruction,
                    "instruction_sha256": instruction_sha,
                },
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ),
            flush=True,
        )

        completed = 0
        for step in range(self.max_steps):
            payload = await self._wait_command(step)
            action = self._validate_command(payload, session_id=session_id, step=step)
            typ = str(action.get("type") or "")

            if typ == "finish":
                args = action.get("args") or {}
                if not isinstance(args, Mapping):
                    raise BrainHarborSessionError("FINISH_ARGS_INVALID")
                verified = _validate_authorization(args.get("authorization"), session_id)
                receipt = {
                    "schema": "PROJECT_BRAIN_HARBOR_OBSERVATION_V1",
                    "session_id": session_id,
                    "step": step,
                    "action_type": "finish",
                    "result": verified,
                    "terminal_authorized": True,
                }
                self._write_receipt(session_id, step, receipt)
                completed = step + 1
                context.metadata = {
                    **(context.metadata or {}),
                    "project_brain_harbor_session": {
                        "status": "AUTHORIZED_COMPLETE",
                        "session_id": session_id,
                        "instruction_sha256": instruction_sha,
                        "completed_steps": completed,
                        **verified,
                    },
                }
                return

            if typ not in {"terminal_exec", "terminal_read_text", "terminal_write_text"}:
                raise BrainHarborSessionError("COMMAND_ACTION_TYPE_REJECTED:" + typ)

            result = await execute_predeclared_action(transport, action)
            receipt = {
                "schema": "PROJECT_BRAIN_HARBOR_OBSERVATION_V1",
                "session_id": session_id,
                "step": step,
                "action_sha256": hashlib.sha256(
                    json.dumps(
                        action, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                    ).encode("utf-8")
                ).hexdigest(),
                "action_type": typ,
                "result": result,
                "terminal_authorized": False,
            }
            self._write_receipt(session_id, step, receipt)
            completed = step + 1

        raise BrainHarborSessionError("SESSION_STEP_LIMIT:" + str(completed))

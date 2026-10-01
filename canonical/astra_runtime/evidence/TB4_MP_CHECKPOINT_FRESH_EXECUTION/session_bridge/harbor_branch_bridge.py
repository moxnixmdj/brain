"""Harbor branch-command bridge agent (brain-side).

Polls the control branch for shell commands and executes them inside the
official Harbor task environment. Observations are pushed back to an
observation branch so the operator can drive the task step by step.

Guard: refuses to execute any command that names the task's hidden verifier
(`tests/`) or the reference solution (`solution/`). The independent verifier
must stay unread by the substrate; it is executed by Harbor itself after the
terminal authorization is accepted.
"""
from __future__ import annotations
import hashlib, json, os, re, subprocess, time
from pathlib import Path

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

ROOT = Path(os.environ["BRAIN_REPO_ROOT"])
OBS = Path(os.environ["BRAIN_OBSERVATION_DIR"])
CONTROL = os.environ["BRAIN_CONTROL_BRANCH"]
SESSION = os.environ["BRAIN_SESSION_ID"]
# Path prefix (inside the control branch) that holds commands/ and
# terminal_authorization.json.
PREFIX = os.environ.get("BRAIN_COMMAND_PREFIX", "session_bridge")
POLL = int(os.environ.get("BRAIN_POLL_INTERVAL_SEC", "3"))
LIMIT = int(os.environ.get("BRAIN_COMMAND_TIMEOUT_SEC", "900"))
MAX_STEPS = int(os.environ.get("BRAIN_MAX_STEPS", "80"))
DEADLINE_SEC = int(os.environ.get("BRAIN_SESSION_TIMEOUT_SEC", "14000"))
CAP = int(os.environ.get("BRAIN_OBSERVATION_CHAR_LIMIT", "120000"))

# The substrate must never read the hidden verifier or the reference solution.
_FORBIDDEN = re.compile(r"(^|[\s'\"`=/])tests/|(^|[\s'\"`=/])solution/|/tests\b|/solution\b")


def run_host(*args, check=True):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=check)


def fetch_file(rel: str):
    cp = run_host("git", "fetch", "--quiet", "origin", CONTROL, check=False)
    if cp.returncode:
        return None
    cp = run_host("git", "show", f"FETCH_HEAD:{rel}", check=False)
    return cp.stdout if cp.returncode == 0 else None


def commit_obs(rel: str, value, message: str):
    p = OBS / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", rel], cwd=OBS, check=True)
    cp = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=OBS)
    if cp.returncode:
        subprocess.run(["git", "commit", "-m", message], cwd=OBS, check=True,
                       capture_output=True, text=True)
        subprocess.run(["git", "push", "origin",
                        f"HEAD:refs/heads/{os.environ['BRAIN_OBSERVATION_BRANCH']}"],
                       cwd=OBS, check=True, capture_output=True, text=True)


def validate_auth(raw: str | None):
    if raw is None:
        return None, "TERMINAL_AUTHORIZATION_MISSING"
    try:
        auth = json.loads(raw)
    except Exception:
        return None, "TERMINAL_AUTHORIZATION_INVALID_JSON"
    if auth.get("schema") != "BRAIN_SESSION_TERMINAL_AUTHORIZATION_V1":
        return auth, "TERMINAL_AUTHORIZATION_SCHEMA_INVALID"
    if auth.get("session_id") != SESSION:
        return auth, "TERMINAL_AUTHORIZATION_SESSION_MISMATCH"
    if auth.get("submission_authorized") is not True:
        return auth, "TERMINAL_AUTHORIZATION_FALSE"
    if auth.get("known_relevant_failures") not in ([], None):
        return auth, "KNOWN_RELEVANT_FAILURES_REMAIN"
    criteria = auth.get("acceptance_criteria")
    checks = auth.get("verification_commands")
    if not isinstance(criteria, list) or not criteria:
        return auth, "ACCEPTANCE_CRITERIA_EVIDENCE_MISSING"
    if any(not isinstance(x, dict) or x.get("status") != "PASS" or not x.get("evidence")
           for x in criteria):
        return auth, "ACCEPTANCE_CRITERIA_NOT_ALL_PASS"
    if not isinstance(checks, list) or not checks:
        return auth, "VERIFICATION_COMMANDS_MISSING"
    if any(not isinstance(x, dict) or x.get("exit_code") != 0 or not x.get("command")
           for x in checks):
        return auth, "VERIFICATION_COMMANDS_NOT_ALL_PASS"
    return auth, None


class HarborBranchBridgeAgent(BaseAgent):
    @staticmethod
    def name() -> str:
        return "brain-harbor-branch-bridge"

    def version(self) -> str:
        return "1.0.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        return

    async def run(self, instruction: str, environment: BaseEnvironment,
                  context: AgentContext) -> None:
        commit_obs(f"{PREFIX}/instruction_receipt.json", {
            "schema": "BRAIN_HARBOR_INSTRUCTION_RECEIPT_V1",
            "session_id": SESSION,
            "instruction_sha256": hashlib.sha256(instruction.encode()).hexdigest(),
            "instruction_length": len(instruction),
        }, "harbor bridge: instruction received")
        deadline = time.time() + DEADLINE_SEC
        for step in range(MAX_STEPS):
            command = None
            while time.time() < deadline:
                command = fetch_file(f"{PREFIX}/commands/{step:03d}.sh")
                if command is not None:
                    break
                time.sleep(POLL)
            if command is None:
                commit_obs(f"{PREFIX}/status.json", {
                    "status": "SESSION_TIMEOUT", "session_id": SESSION, "next_step": step
                }, "harbor bridge: session timeout")
                return

            if command.strip() == "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT":
                raw = fetch_file(f"{PREFIX}/terminal_authorization.json")
                auth, blocked = validate_auth(raw)
                if blocked:
                    commit_obs(f"{PREFIX}/observations/{step:03d}.json", {
                        "schema": "BRAIN_HARBOR_OBSERVATION_V1", "session_id": SESSION,
                        "step": step,
                        "command_sha256": hashlib.sha256(command.encode()).hexdigest(),
                        "exit_code": 1, "stdout": "",
                        "stderr": "SUBMISSION_BLOCKED__" + blocked + "\n"
                    }, f"harbor bridge: block premature submission step {step}")
                    commit_obs(f"{PREFIX}/status.json", {
                        "status": "READY_FOR_COMMAND", "session_id": SESSION,
                        "next_step": step + 1, "last_submission_blocker": blocked
                    }, f"harbor bridge: continue step {step+1}")
                    continue
                commit_obs(f"{PREFIX}/observations/{step:03d}.json", {
                    "schema": "BRAIN_HARBOR_OBSERVATION_V1", "session_id": SESSION,
                    "step": step,
                    "command_sha256": hashlib.sha256(command.encode()).hexdigest(),
                    "exit_code": 0,
                    "stdout": "SUBMISSION_ACCEPTED_FOR_HARBOR_VERIFICATION\n",
                    "stderr": "", "completion_authorization": auth
                }, f"harbor bridge: accept submission step {step}")
                commit_obs(f"{PREFIX}/status.json", {
                    "status": "AGENT_COMPLETE_AWAITING_HARBOR_VERIFIER",
                    "session_id": SESSION, "final_step": step
                }, "harbor bridge: agent complete")
                return

            if _FORBIDDEN.search(command):
                commit_obs(f"{PREFIX}/observations/{step:03d}.json", {
                    "schema": "BRAIN_HARBOR_OBSERVATION_V1", "session_id": SESSION,
                    "step": step,
                    "command_sha256": hashlib.sha256(command.encode()).hexdigest(),
                    "exit_code": 126, "stdout": "",
                    "stderr": "REFUSED__COMMAND_REFERENCES_HIDDEN_VERIFIER_OR_SOLUTION\n"
                }, f"harbor bridge: refused step {step}")
                commit_obs(f"{PREFIX}/status.json", {
                    "status": "READY_FOR_COMMAND", "session_id": SESSION, "next_step": step + 1,
                    "last_refusal": "HIDDEN_VERIFIER_OR_SOLUTION_PATH"
                }, f"harbor bridge: ready step {step+1}")
                continue

            started = time.time()
            try:
                res = await environment.exec(command=command, cwd="/app", timeout_sec=LIMIT)
                code = res.return_code
                stdout = (res.stdout or "")[-CAP:]
                stderr = (res.stderr or "")[-CAP:]
            except Exception as exc:
                code = 124
                stdout = ""
                stderr = f"{type(exc).__name__}: {exc}"
            obs = {
                "schema": "BRAIN_HARBOR_OBSERVATION_V1", "session_id": SESSION, "step": step,
                "command_sha256": hashlib.sha256(command.encode()).hexdigest(),
                "exit_code": code, "duration_sec": round(time.time() - started, 3),
                "stdout": stdout, "stderr": stderr
            }
            commit_obs(f"{PREFIX}/observations/{step:03d}.json", obs,
                       f"harbor bridge: observation step {step}")
            commit_obs(f"{PREFIX}/status.json", {
                "status": "READY_FOR_COMMAND", "session_id": SESSION, "next_step": step + 1
            }, f"harbor bridge: ready step {step+1}")

        commit_obs(f"{PREFIX}/status.json", {
            "status": "STEP_LIMIT", "session_id": SESSION, "max_steps": MAX_STEPS
        }, "harbor bridge: step limit")

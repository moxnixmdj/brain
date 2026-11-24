"""Owner-opted experimental Harbor Docker orchestration, not verification.

Container inspection is sampled, not atomic with exec. The process cleanup is
best effort and can kill newly appearing container processes. A disposable VM
and an independently run verifier are required. This module does not invoke
an external model, score a task, or establish a security boundary.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
import re
import shlex
from typing import Any

from canonical.runtime.harbor_live_compose_diagnostic_v1 import inspect_compose_environment
from canonical.runtime.harbor_environment_transport_v2 import HarborEnvironmentTransport
from canonical.runtime.harbor_pro_capture_transport_v1 import capture_unqualified_candidate

_PROCESS_MARKER = 'BRAIN_PROCESS_CLEANUP_V1:'
_PROCESS_SCRIPT = '/opt/brain-ro/canonical/runtime/harbor_process_cleanup_worker_v1.py'
_COMMIT = re.compile(r'(?:[0-9a-f]{40}|[0-9a-f]{64})\Z')


class ExperimentalVMError(RuntimeError):
    pass


class CheckedEnvironment:
    """Re-sample Compose around each exec; does not eliminate the race."""
    def __init__(self, environment: Any, brain_source: str):
        self.environment = environment
        self.brain_source = brain_source
        self.container_id: str | None = None

    async def check(self) -> dict[str, Any]:
        data = await inspect_compose_environment(self.environment, brain_source=self.brain_source)
        if not isinstance(data, dict) or data.get('static_filter_passed') is not True:
            raise ExperimentalVMError('COMPOSE_STATIC_CHECK_FAILED')
        cid = data.get('compose_main_container_id')
        if not isinstance(cid, str) or not re.fullmatch(r'[0-9a-f]{64}', cid):
            raise ExperimentalVMError('COMPOSE_CONTAINER_ID_INVALID')
        if self.container_id is not None and self.container_id != cid:
            raise ExperimentalVMError('COMPOSE_CONTAINER_CHANGED')
        # The patch and trace writer must not use an agent-writable host log dir.
        if '/logs/agent' in data.get('host_log_mount_destinations', []):
            raise ExperimentalVMError('AGENT_LOG_HOST_MOUNT_UNSAFE')
        self.container_id = cid
        return data

    async def exec(self, command: str, **kwargs: Any) -> Any:
        await self.check()
        result = await self.environment.exec(command, **kwargs)
        await self.check()
        return result


async def _process_command(environment: CheckedEnvironment, mode: str, baseline: dict | None = None) -> dict:
    command = ('env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp python3 -I -B '
               + _PROCESS_SCRIPT + ' ' + mode)
    if baseline is not None:
        raw = json.dumps(baseline, sort_keys=True, separators=(',', ':')).encode('ascii')
        if len(raw) > 100_000:
            raise ExperimentalVMError('BASELINE_TOO_LARGE')
        command += ' ' + shlex.quote(base64.b64encode(raw).decode('ascii'))
    receipt = await HarborEnvironmentTransport(environment).exec(command, timeout_sec=30)
    if receipt.returncode != 0:
        raise ExperimentalVMError('PROCESS_' + mode.upper() + '_FAILED')
    lines = [s[len(_PROCESS_MARKER):] for s in receipt.stdout.splitlines() if s.startswith(_PROCESS_MARKER)]
    if len(lines) != 1 or len(lines[0]) > 100_000:
        raise ExperimentalVMError('PROCESS_RESPONSE_INVALID')
    try:
        result = json.loads(lines[0])
    except ValueError as exc:
        raise ExperimentalVMError('PROCESS_RESPONSE_INVALID') from exc
    if not isinstance(result, dict) or result.get('quiescence_verified') is not False:
        raise ExperimentalVMError('PROCESS_RESPONSE_INVALID')
    return result


async def _base_commit(environment: CheckedEnvironment, repo: str) -> str:
    if not isinstance(repo, str) or repo not in ('/app', '/testbed'):
        raise ExperimentalVMError('UNSUPPORTED_PRO_REPOSITORY')
    command = ('env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp GIT_CONFIG_NOSYSTEM=1 '
               'GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0 '
               'git -C ' + shlex.quote(repo) + " rev-parse --verify 'HEAD^{commit}'")
    receipt = await HarborEnvironmentTransport(environment).exec(command, timeout_sec=30)
    value = receipt.stdout.strip()
    if receipt.returncode != 0 or not _COMMIT.fullmatch(value):
        raise ExperimentalVMError('PRO_BASE_COMMIT_UNAVAILABLE')
    return value


async def run_experimental(instruction: str, environment: Any, *, brain_source: str,
                           suite: str, repo: str, agent_log_dir: Path) -> dict[str, Any]:
    """Dispatch Brain inside sampled Docker, optionally capture a Pro candidate.

    Terminal-Bench artifacts remain in the task container for Harbor's own
    verifier. Pro is only a candidate: the official pristine replay is separate.
    """
    if suite not in ('pro-v2', 'terminal-bench-4'):
        raise ExperimentalVMError('SUITE_NOT_SUPPORTED')
    from canonical.runtime.harbor_epistemic_agent_v1 import run_epistemic_goal

    checked = CheckedEnvironment(environment, brain_source)
    await checked.check()
    base = await _base_commit(checked, repo) if suite == 'pro-v2' else None
    before = await _process_command(checked, 'snapshot')
    baseline = before.get('baseline')
    if not isinstance(baseline, dict) or not baseline:
        raise ExperimentalVMError('PROCESS_BASELINE_INVALID')
    result = await run_epistemic_goal(instruction, checked, suite=suite, repo=repo,
                                      experimental_candidate_path=True)
    # Cleanup is best effort, not a proof. Even a clean snapshot can miss a
    # detached process. An uncertain command never leads to patch publication.
    cleanup = await _process_command(checked, 'cleanup', baseline)
    if cleanup.get('status') != 'NO_NEW_VISIBLE_PROCESSES':
        raise ExperimentalVMError('PROCESS_CLEANUP_INCOMPLETE')
    if result.get('status') in ('BLOCKED_CONTAINER_SOLVER_UNAVAILABLE', 'BLOCKED_EXEC_OUTCOME_UNCERTAIN'):
        raise ExperimentalVMError('SOLVER_OR_ACTION_EXEC_UNCERTAIN')
    result.update({'experiment': 'OWNER_OPTED_DISPOSABLE_VM__UNVERIFIED', 'suite': suite,
                   'compose_container_id': checked.container_id,
                   'identity_atomically_bound': False, 'egress_verified': False,
                   'worker_quiescence_verified': False, 'process_cleanup': cleanup,
                   'external_verifier_invoked': False, 'task_completion_claimed': False})
    if suite == 'pro-v2':
        if base is None:
            raise ExperimentalVMError('PRO_BASE_COMMIT_UNAVAILABLE')
        result['pro_candidate_handoff'] = await capture_unqualified_candidate(
            checked, repo=repo, expected_base=base, agent_log_dir=agent_log_dir)
        result['patch_emitted'] = True
    return result


def atif_trajectory(instruction: str, result: dict[str, Any], session_id: str | None) -> dict[str, Any]:
    """Construct an ATIF-shaped audit trail; no verifier or completion claim."""
    steps: list[dict[str, Any]] = [{'step_id': 1, 'source': 'user', 'message': instruction}]
    for entry in result.get('trace', []):
        step: dict[str, Any] = {'step_id': len(steps) + 1, 'source': 'agent',
                                'message': json.dumps(entry, sort_keys=True, default=str)}
        action = entry.get('action') if isinstance(entry, dict) else None
        if isinstance(action, dict) and action.get('type') == 'exec':
            call_id = 'call-' + str(len(steps))
            step['tool_calls'] = [{'tool_call_id': call_id, 'function_name': 'terminal_exec',
                                   'arguments': {'command': action.get('command'),
                                                 'timeout_sec': action.get('timeout_sec')}}]
            if isinstance(entry.get('result'), dict):
                step['observation'] = {'results': [{'source_call_id': call_id,
                    'content': json.dumps(entry['result'], sort_keys=True)}]}
        steps.append(step)
    return {'schema_version': 'ATIF-v1.8', 'session_id': session_id,
            'agent': {'name': 'brain-epistemic', 'version': '1.0.0'}, 'steps': steps,
            'notes': 'Experimental audit trace; output may be truncated; no verifier result.'}

"""Prewave verifier for Harbor transport/adapter boundary without terminal task exposure.

This proves only the deterministic execution seam:
- command policy blocks network/package acquisition,
- HarborEnvironmentTransport normalizes receipts,
- adapter imports without Harbor installed,
- no terminal task/verifier content is consumed.

It does NOT certify the planner/controller as zero-cost or donor-independent.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from canonical.runtime.harbor_environment_transport import HarborEnvironmentTransport
from canonical.runtime.harbor_command_policy import validate_environment_command


@dataclass
class FakeResult:
    return_code: int
    stdout: str
    stderr: str


class FakeEnv:
    def __init__(self):
        self.calls=[]

    async def exec(self, command: str, **kwargs: Any):
        self.calls.append((command,dict(kwargs)))
        return FakeResult(0,"ok","")


async def _exercise():
    env=FakeEnv()
    t=HarborEnvironmentTransport(env)
    r=await t.exec("printf ok",timeout_sec=5)
    assert r.returncode==0 and r.stdout=="ok"
    assert env.calls==[("printf ok",{"timeout_sec":5})]
    return True


def run_preflight()->dict:
    errors=[]
    try:
        validate_environment_command("python3 -c 'print(1)'")
    except Exception as exc:
        errors.append("SAFE_COMMAND_REJECTED:"+type(exc).__name__)

    for bad in (
        "curl https://example.com",
        "wget https://example.com/x",
        "git clone https://example.com/repo",
        "pip install x",
        "apt-get install x",
        "ssh host",
    ):
        try:
            validate_environment_command(bad)
            errors.append("FORBIDDEN_COMMAND_ACCEPTED:"+bad.split()[0])
        except ValueError:
            pass

    try:
        asyncio.run(_exercise())
    except Exception as exc:
        errors.append("TRANSPORT_EXERCISE_FAILED:"+type(exc).__name__+":"+str(exc))

    return {
        "schema":"PROJECT_BRAIN_HARBOR_ADAPTER_TRANSPORT_PREFLIGHT_V1",
        "pass":not errors,
        "errors":errors,
        "terminal_task_content_consumed":False,
        "terminal_result_observed":False,
        "controller_zero_cost_certified":False,
        "controller_donor_independence_certified":False,
        "scope":"TRANSPORT_AND_COMMAND_POLICY_ONLY",
    }


if __name__=="__main__":
    import json
    out=run_preflight()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)

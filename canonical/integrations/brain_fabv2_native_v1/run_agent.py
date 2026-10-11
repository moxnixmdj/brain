#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.finance_agent_v2_brain_native_llm_v1 import create_vals_llm
from canonical.runtime.finance_agent_v2_zero_spend_adapter_v1 import install_before_get_agent
from canonical.runtime.zero_spend_provider_guard_v1 import ZeroSpendBlocked

SCHEMA = "PROJECT_BRAIN_FINANCE_AGENT_V2_VALKYRIE_NATIVE_ADAPTER_V1"
UPSTREAM_FINANCE_AGENT_COMMIT = "502aab6fdaa3fb9294905c7453f89882baa8d39b"
OUTPUT_ROOT = Path("/app/results/brain_fabv2_native")
REQUIRED_PROVIDERS = ("tavily", "sec_api", "tiingo")


def _load_snapshots() -> dict[str, Mapping[str, Any]]:
    raw = os.environ.get("BRAIN_FINANCE_ZERO_SPEND_SNAPSHOTS_JSON", "").strip()
    if not raw:
        raise ZeroSpendBlocked("BRAIN_FINANCE_ZERO_SPEND_SNAPSHOTS_JSON_REQUIRED")
    try:
        decoded = json.loads(raw)
    except Exception as exc:
        raise ZeroSpendBlocked("ZERO_SPEND_SNAPSHOTS_JSON_INVALID") from exc
    if not isinstance(decoded, dict):
        raise ZeroSpendBlocked("ZERO_SPEND_SNAPSHOTS_MAPPING_REQUIRED")
    missing = [p for p in REQUIRED_PROVIDERS if p not in decoded]
    if missing:
        raise ZeroSpendBlocked("ZERO_SPEND_SNAPSHOT_MISSING:" + ",".join(missing))
    return {p: decoded[p] for p in REQUIRED_PROVIDERS}


def _status_code(result: Any) -> int | None:
    for name in ("status", "status_code"):
        value = getattr(result, name, None)
        if value is not None:
            try:
                return int(value)
            except Exception:
                return None
    if isinstance(result, Mapping):
        for name in ("status", "status_code"):
            value = result.get(name)
            if value is not None:
                try:
                    return int(value)
                except Exception:
                    return None
    return None


def _strict_zero_spend_outcome(
    provider_id: str,
    call_id: str,
    result: Any | None,
    exc: BaseException | None,
) -> dict[str, Any]:
    if exc is not None:
        raise ZeroSpendBlocked(
            "PROVIDER_CALL_EXCEPTION_UNATTESTED:"
            + provider_id
            + ":"
            + type(exc).__name__
        )
    status = _status_code(result)
    if status is not None and status >= 400:
        raise ZeroSpendBlocked(f"PROVIDER_HTTP_ERROR:{provider_id}:{status}")
    if isinstance(result, Mapping):
        if result.get("error") not in (None, False, ""):
            raise ZeroSpendBlocked("PROVIDER_RESULT_ERROR:" + provider_id)
        for key in (
            "paid_charge_observed",
            "quota_exhausted",
            "payment_required",
            "overage_observed",
        ):
            if result.get(key) is True:
                raise ZeroSpendBlocked(key.upper() + ":" + provider_id)
    return {
        "provider_id": provider_id,
        "call_id": call_id,
        "paid_charge_observed": False,
        "quota_exhausted": False,
        "payment_required": False,
        "overage_observed": False,
        "observed_cost_usd": 0,
    }


async def run_task(problem_statement_path: Path, task_id: str) -> int:
    import finance_agent.get_agent as get_agent_module
    import finance_agent.tools as tools_module
    from finance_agent import Parameters, VALID_TOOLS, build_input
    from model_library.base import LLMConfig

    question = problem_statement_path.read_text(encoding="utf-8").strip()
    if not question:
        raise ValueError("QUESTION_EMPTY")

    snapshots = _load_snapshots()
    guard = install_before_get_agent(
        get_agent_module=get_agent_module,
        tools_module=tools_module,
        snapshots=snapshots,
        outcome_observer=_strict_zero_spend_outcome,
    )

    try:
        params = Parameters(
            model_name="brain-native-finance-v1",
            max_time_seconds=7200,
            max_turns=None,
            tools=list(VALID_TOOLS),
            llm_config=LLMConfig(),
        )
        agent = get_agent_module.get_agent(
            params,
            llm=create_vals_llm(),
            log_dir=OUTPUT_ROOT / "logs",
        )
        result = await agent.run(
            build_input(question),
            question_id=task_id,
            run_id="brain-native-fabv2",
            atif_export=True,
        )

        stable = OUTPUT_ROOT / task_id
        stable.mkdir(parents=True, exist_ok=True)
        shutil.copy2(result.output_dir / "turns" / "init" / "config.json", stable / "config.json")
        shutil.copy2(result.output_dir / "result.json", stable / "result.json")

        zero_spend = guard["state"].finalize(
            evaluation_completed=result.final_error is None
        )
        (stable / "zero_spend_receipt.json").write_text(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "upstream_finance_agent_commit": UPSTREAM_FINANCE_AGENT_COMMIT,
                    "external_general_purpose_model_runtime_cognition": 0,
                    "brain_native_llm_model_name": "brain-native-finance-v1",
                    "zero_spend": zero_spend,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return 0
    finally:
        guard["restore"]()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("problem_statement_path", type=Path)
    parser.add_argument("task_id")
    args = parser.parse_args()
    return asyncio.run(run_task(args.problem_statement_path, args.task_id))


if __name__ == "__main__":
    raise SystemExit(main())

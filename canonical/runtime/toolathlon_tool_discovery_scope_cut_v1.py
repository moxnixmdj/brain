from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_TOOLATHLON_TOOL_DISCOVERY_SCOPE_CUT_VERDICT_V1"
EXPECTED_TASKS = 108

CONNECT_MARKER = "await self.mcp_manager.connect_servers(self.task_config.needed_mcp_servers)"
GET_TOOLS_MARKER = "available_tools = await self.agent.get_all_tools()"
BIND_SERVERS_MARKER = "mcp_servers=[*self.mcp_manager.get_all_connected_servers()]"


def evaluate_checkout(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    finalpool = root / "tasks" / "finalpool"
    task_agent = root / "utils" / "roles" / "task_agent.py"
    errors: list[str] = []

    configs = sorted(finalpool.glob("*/task_config.json"))
    parsed: list[tuple[Path, Any]] = []
    for path in configs:
        try:
            parsed.append((path, json.loads(path.read_text(encoding="utf-8"))))
        except Exception as exc:
            errors.append(f"TASK_CONFIG_PARSE_ERROR::{path.name}::{type(exc).__name__}")

    count_ok = len(configs) == EXPECTED_TASKS
    if not count_ok:
        errors.append(f"TASK_CONFIG_COUNT_NOT_108::{len(configs)}")

    field_count = sum(
        1
        for _, obj in parsed
        if isinstance(obj, dict) and isinstance(obj.get("needed_mcp_servers"), list)
    )
    all_configs_predeclare_server_set = (
        len(parsed) == EXPECTED_TASKS and field_count == EXPECTED_TASKS
    )
    if not all_configs_predeclare_server_set:
        errors.append(f"NEEDED_MCP_SERVERS_NOT_LIST_IN_ALL_TASKS::{field_count}")

    source = ""
    if task_agent.exists():
        source = task_agent.read_text(encoding="utf-8")
    else:
        errors.append("TASK_AGENT_SOURCE_MISSING")

    connect_pos = source.find(CONNECT_MARKER)
    get_tools_pos = source.find(GET_TOOLS_MARKER)
    bind_pos = source.find(BIND_SERVERS_MARKER)

    exact_server_set_connected = connect_pos >= 0
    tool_surface_enumerated_before_agent_execution = (
        get_tools_pos >= 0
        and connect_pos >= 0
        and connect_pos < get_tools_pos
    )
    connected_servers_bound_into_agent = bind_pos >= 0

    if not exact_server_set_connected:
        errors.append("TASK_AGENT_DOES_NOT_CONNECT_EXACT_NEEDED_MCP_SERVER_SET")
    if not tool_surface_enumerated_before_agent_execution:
        errors.append("TOOL_SURFACE_PREEXECUTION_ENUMERATION_NOT_PROVED")
    if not connected_servers_bound_into_agent:
        errors.append("CONNECTED_SERVERS_NOT_BOUND_INTO_AGENT")

    observation_pass = not errors
    return {
        "schema": SCHEMA,
        "benchmark_task_count": len(configs),
        "configs_with_needed_mcp_servers_list": field_count,
        "all_configs_predeclare_server_set": all_configs_predeclare_server_set,
        "exact_server_set_connected": exact_server_set_connected,
        "tool_surface_enumerated_before_agent_execution": tool_surface_enumerated_before_agent_execution,
        "connected_servers_bound_into_agent": connected_servers_bound_into_agent,
        "public_harness_observation_pass": observation_pass,
        "scope_relation": (
            "PARTIAL_STRICT_SUBSET__SUPPLEMENT_REQUIRED"
            if observation_pass
            else "UNPROVED"
        ),
        "toolathlon_standalone_whole_family_closure_admissible": False,
        "represented_directly": [
            "REAL_WORLD_LONG_HORIZON_TOOL_EXECUTION",
            "SELECTION_AND_USE_FROM_A_FRESH_TASK_SPECIFIC_MCP_TOOL_SURFACE",
            "END_STATE_EXECUTION_BASED_TERMINAL_SUCCESS",
        ] if observation_pass else [],
        "remaining_scope_leaf": (
            "BRAIN_OWNED_UNKNOWN_TOOL_IDENTITY_OR_DISCOVERY_SOURCE_EXPANSION_PROOF"
            if observation_pass
            else None
        ),
        "new_reality_units_consumed": 0,
        "terminal_results_observed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("toolathlon_checkout")
    args = parser.parse_args(argv)
    verdict = evaluate_checkout(args.toolathlon_checkout)
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if verdict["public_harness_observation_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

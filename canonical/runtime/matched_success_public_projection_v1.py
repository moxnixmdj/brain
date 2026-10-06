from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import browser_state_information_safe_proof as browser
from canonical.runtime import delegation_structural_variety_proof_v3 as delegation_v3
from canonical.runtime import delegation_whole_scope_proof_v2 as delegation_v2
from canonical.runtime import tool_discovery_information_safe_proof_v2 as tool
from canonical.runtime import m0a_raw_source_terminal_suite_v2 as m0
from canonical.runtime import contract_native_proof_suites as contract
from canonical.runtime import native_artifact_cross_format_proof_v1 as native


def public_component(component: Mapping[str, Any]) -> Mapping[str, Any]:
    kind = str(component["kind"])
    case = component["case"]

    if kind == "browser":
        return browser.public_state(case, case["_initial_state"], [])
    if kind == "delegation_v2":
        return delegation_v2.public_initial(case)
    if kind == "delegation_v3":
        return delegation_v3.public_case(case)
    if kind == "tool":
        return tool.public_stage(case, 1, ())
    if kind in {"m0", "m0_change"}:
        return m0.public_task(case)
    if kind in {"structured", "p1", "p2", "p3"}:
        return contract.public_task(case)
    if kind == "native":
        return native.public_task(case)
    raise ValueError("UNKNOWN_COMPONENT_KIND:" + kind)

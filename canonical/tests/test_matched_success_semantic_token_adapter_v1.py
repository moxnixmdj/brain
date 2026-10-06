from __future__ import annotations

from canonical.runtime import browser_state_information_safe_proof as browser
from canonical.runtime import contract_native_proof_suites as contract
from canonical.runtime import delegation_structural_variety_proof_v3 as delegation_v3
from canonical.runtime import delegation_whole_scope_proof_v2 as delegation_v2
from canonical.runtime import m0a_raw_source_terminal_suite_v2 as m0
from canonical.runtime import native_artifact_cross_format_proof_v1 as native
from canonical.runtime import tool_discovery_information_safe_proof_v2 as tool
from canonical.runtime.matched_success_semantic_token_adapter_v1 import (
    inject_token,
    run_component,
)

TRUE = "SEMANTIC_TOKEN_AAAAAA"
DECOY = "SEMANTIC_TOKEN_BBBBBB"

STRUCTURED = "STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001"
P1 = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
P2 = "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
P3 = "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"


def base(kind: str):
    if kind == "browser":
        return browser.generate_case(101, 0)
    if kind == "tool":
        return tool.generate_case(102, 0)
    if kind == "delegation_v2":
        return delegation_v2.generate_case(103, 0)
    if kind == "delegation_v3":
        return delegation_v3.generate_case(104, 0)
    if kind in {"m0", "m0_change"}:
        return m0.generate_case(105, 3)
    if kind == "structured":
        return contract.generate_case(STRUCTURED, 106, 3)
    if kind == "p1":
        return contract.generate_case(P1, 107, 3)
    if kind == "p2":
        return contract.generate_case(P2, 108, 3)
    if kind == "p3":
        return contract.generate_case(P3, 109, 3)
    if kind == "native":
        return native.generate_case("docx", 110)
    raise AssertionError(kind)


def test_every_component_kind_transports_load_bearing_token():
    kinds = [
        "browser",
        "tool",
        "delegation_v2",
        "delegation_v3",
        "m0",
        "m0_change",
        "structured",
        "p1",
        "p2",
        "p3",
        "native",
    ]
    failures = {}
    for kind in kinds:
        case = inject_token(kind, base(kind), TRUE)
        out = run_component(kind, case, TRUE)
        if out["pass"] is not True:
            failures[kind] = out
    assert failures == {}


def test_same_shape_ablation_changes_actual_component_semantics():
    kinds = [
        "browser",
        "tool",
        "delegation_v2",
        "delegation_v3",
        "m0",
        "m0_change",
        "structured",
        "p1",
        "p2",
        "p3",
        "native",
    ]
    failures = {}
    for kind in kinds:
        true_out = run_component(
            kind, inject_token(kind, base(kind), TRUE), TRUE
        )
        ablated_out = run_component(
            kind, inject_token(kind, base(kind), DECOY), DECOY
        )
        if not (
            true_out["pass"] is True
            and ablated_out["pass"] is True
            and true_out["observed_token"] == TRUE
            and ablated_out["observed_token"] == DECOY
            and TRUE != DECOY
        ):
            failures[kind] = {
                "true": true_out,
                "ablated": ablated_out,
            }
    assert failures == {}


def test_all_native_formats_transport_token():
    failures = {}
    for i, fmt in enumerate(native.FORMATS):
        case = native.generate_case(fmt, 200 + i)
        out = run_component(
            "native", inject_token("native", case, TRUE), TRUE
        )
        if out["pass"] is not True:
            failures[fmt] = out
    assert failures == {}


def test_token_substitution_is_not_silently_accepted():
    case = inject_token("p3", base("p3"), TRUE)
    wrong = run_component("p3", case, DECOY)
    assert wrong["base_scorer_pass"] is True
    assert wrong["pass"] is False
    assert wrong["observed_token"] is None


def test_adapter_grants_no_authority():
    out = run_component(
        "structured",
        inject_token("structured", base("structured"), TRUE),
        TRUE,
    )
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["fresh_reality_authority"] is False

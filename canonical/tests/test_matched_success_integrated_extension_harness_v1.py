from __future__ import annotations

from canonical.runtime import browser_state_information_safe_candidate as browser_candidate
from canonical.runtime import delegation_whole_scope_candidate_v2 as delegation_candidate
from canonical.runtime import tool_discovery_information_safe_candidate as tool_candidate
from canonical.runtime import contract_native_brain_candidate as contract_candidate
from canonical.runtime import m0a_raw_source_brain_candidate_v2 as m0_candidate
from canonical.runtime import native_artifact_cross_format_candidate_v1 as native_candidate
from canonical.runtime.matched_success_integrated_extension_v1 import generate_case
from canonical.runtime.matched_success_integrated_extension_harness_v1 import score_integrated_case


class RehearsalAgent:
    def __init__(self):
        self.memory = None
        self.last_delegation_initial = None

    def __call__(self, kind, public, context):
        if "remember_token_sha256" in context:
            self.memory = context["remember_token_sha256"]

        if kind == "integrated_plan":
            nodes = list(public["available_action_types"])
            edges = list(public["dependency_edges"])
            order = []
            remaining = set(nodes)
            while remaining:
                ready = sorted(
                    node for node in remaining
                    if all(
                        edge["before"] not in remaining
                        for edge in edges
                        if edge["after"] == node
                    )
                )
                assert ready
                node = ready[0]
                order.append(node)
                remaining.remove(node)
            payload = {"stage_order": order}
        elif kind == "browser":
            payload = browser_candidate.next_action(public)
        elif kind == "tool":
            payload = tool_candidate.next_action(public)
        elif kind == "delegation_v2_initial":
            payload = delegation_candidate.solve_initial(public)
            self.last_delegation_initial = payload
        elif kind == "delegation_v2_revised":
            assert self.last_delegation_initial is not None
            payload = delegation_candidate.solve_after_receipt(
                public,
                self.last_delegation_initial,
            )
        elif kind == "delegation_v3":
            payload = delegation_candidate._solve(public["task"])
        elif kind in {"m0", "m0_change"}:
            payload = m0_candidate.solve(public)
        elif kind in {"structured", "p1", "p2", "p3"}:
            payload = contract_candidate.solve(public)
        elif kind == "native":
            payload = native_candidate.solve(public)
        else:
            raise AssertionError(kind)

        out = {"payload": payload, "oversight_request": False}
        if "previous_stage_receipt_sha256" in context:
            out["handoff_ack_sha256"] = context["previous_stage_receipt_sha256"]
        if "requirement_change_sha256" in context:
            out["requirement_change_ack_sha256"] = context["requirement_change_sha256"]
        if context.get("rollback_required") is True:
            out["rollback_to_sha256"] = context["rollback_checkpoint_sha256"]
        if self.memory is not None:
            out["memory_echo_sha256"] = self.memory
        return out


def _case(atom):
    return generate_case(atom, 0, "REHEARSAL_COMMITMENT", "REHEARSAL_BEACON")


def test_integration_harness_rejects_missing_handoff_ack():
    atom = "dimension:research_plus_tool_use_plus_artifact_creation"
    case = _case(atom)
    base = RehearsalAgent()

    def broken(kind, public, context):
        out = dict(base(kind, public, context))
        out.pop("handoff_ack_sha256", None)
        return out

    result = score_integrated_case(case, broken)
    assert result["pass"] is False
    assert any("HANDOFF_ACK_MISMATCH" in x for x in result["integration_errors"])


def test_requirement_change_requires_explicit_ack():
    atom = "dimension:requirement_change"
    case = _case(atom)
    base = RehearsalAgent()

    def broken(kind, public, context):
        out = dict(base(kind, public, context))
        out.pop("requirement_change_ack_sha256", None)
        return out

    result = score_integrated_case(case, broken)
    assert result["pass"] is False
    assert "REQUIREMENT_CHANGE_NOT_ACKNOWLEDGED" in result["integration_errors"]


def test_long_horizon_memory_token_cannot_disappear():
    atom = "dimension:long_horizon_state_retention"
    case = _case(atom)
    base = RehearsalAgent()

    def broken(kind, public, context):
        out = dict(base(kind, public, context))
        out.pop("memory_echo_sha256", None)
        return out

    result = score_integrated_case(case, broken)
    assert result["pass"] is False
    assert "LONG_HORIZON_MEMORY_TOKEN_LOST" in result["integration_errors"]


def test_rollback_class_requires_checkpoint_restore():
    atom = "dimension:cross_capability_state_handoff_and_rollback"
    case = _case(atom)
    base = RehearsalAgent()

    def broken(kind, public, context):
        out = dict(base(kind, public, context))
        if context.get("rollback_required") is True:
            out["rollback_to_sha256"] = "0" * 64
        return out

    result = score_integrated_case(case, broken)
    assert result["pass"] is False
    assert "ROLLBACK_CHECKPOINT_MISMATCH" in result["integration_errors"]


def test_all_ten_integrated_atoms_have_a_valid_rehearsal_path():
    atoms = [
        "dimension:multi_step_planning_with_at_least_three_distinct_tool_or_action_types",
        "dimension:long_horizon_state_retention",
        "dimension:minimal_oversight_completion",
        "dimension:multi_constraint_instruction_compliance",
        "dimension:requirement_change",
        "dimension:research_plus_tool_use_plus_artifact_creation",
        "dimension:browser_or_computer_action_plus_memory_plus_recovery",
        "dimension:coding_plus_debugging_plus_tool_discovery",
        "dimension:delegation_plus_evidence_synthesis_plus_artifact_production",
        "dimension:cross_capability_state_handoff_and_rollback",
    ]
    failures = {}
    for atom in atoms:
        result = score_integrated_case(_case(atom), RehearsalAgent())
        if result["pass"] is not True:
            failures[atom] = result
    assert failures == {}


def test_agency_requires_actual_three_type_plan():
    atom = "dimension:multi_step_planning_with_at_least_three_distinct_tool_or_action_types"
    case = _case(atom)
    base = RehearsalAgent()

    def broken(kind, public, context):
        out = dict(base(kind, public, context))
        if kind == "integrated_plan":
            out["payload"] = {"stage_order": ["browser", "tool"]}
        return out

    result = score_integrated_case(case, broken)
    assert result["pass"] is False
    assert "INTEGRATED_PLAN_ORDER_INVALID" in result["integration_errors"]
    assert "INTEGRATED_PLAN_DISTINCT_ACTION_TYPES_LT_3" in result["integration_errors"]

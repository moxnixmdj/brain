from canonical.runtime.matched_success_integrated_extension_harness_v1 import score_integrated_case
from canonical.runtime.matched_success_integrated_extension_v1 import generate_case
from canonical.tests.test_matched_success_integrated_extension_harness_v1 import RehearsalAgent


INTEGRATED_ATOMS = [
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


def disconnected_case(atom):
    return generate_case(
        atom,
        0,
        "SEMANTIC_COUPLING_COUNTERMODEL_COMMITMENT",
        "SEMANTIC_COUPLING_COUNTERMODEL_BEACON",
    )


def test_v1_receipt_ack_harness_exhibits_semantic_false_positive():
    """
    This is a countermodel test, not a desired-behavior test.

    RehearsalAgent solves standalone components independently and merely echoes
    receipt/memory/change/rollback acknowledgements. If V1 passes those cases,
    the result proves V1 acknowledgement mechanics are insufficient evidence
    for integrated semantic coupling. V2 is the candidate repair route.
    """
    false_positive_atoms = []
    for atom in INTEGRATED_ATOMS:
        result = score_integrated_case(
            disconnected_case(atom),
            RehearsalAgent(),
        )
        if result["pass"] is True:
            false_positive_atoms.append(atom)

    assert false_positive_atoms, "EXPECTED_V1_SEMANTIC_FALSE_POSITIVE_NOT_REPRODUCED"

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


def test_disconnected_component_solver_must_not_certify_integrated_dimensions():
    """
    RehearsalAgent solves each component using the standalone component candidate.
    It does not use upstream semantic outputs to construct downstream answers; it
    only acknowledges handoff/memory/change/rollback hashes supplied by context.

    Therefore a sound integrated harness must reject at least one such integrated
    case rather than certify all ten dimensions.
    """
    false_positive_atoms = []
    for atom in INTEGRATED_ATOMS:
        result = score_integrated_case(disconnected_case(atom), RehearsalAgent())
        if result["pass"] is True:
            false_positive_atoms.append(atom)

    assert false_positive_atoms == [], (
        "SEMANTIC_INTEGRATION_FALSE_POSITIVE:"
        + ",".join(false_positive_atoms)
    )

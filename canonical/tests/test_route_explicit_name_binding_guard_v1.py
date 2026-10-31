"""An explicitly named capability still requires bindable inputs at admission."""
from pathlib import Path

import pytest

from canonical.runtime import capability_selection_retrieval_v1 as selection
from canonical.runtime import goal_compiler
from canonical.runtime import live_brain_route_admission_v1 as admission
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("goal,should_admit", [
    ("Run python.source.symbols.index.ast and save to report.json.", False),
    ("Run python.source.symbols.index.ast on source root canonical/runtime and save to canonical/tmp_symbols_report.json.", True),
])
def test_explicit_name_does_not_override_refused_input(goal, should_admit):
    registry = goal_compiler._platform_admissible_registry(dict(load_verified_registry()))
    cid = "python.source.symbols.index.ast"
    typed = selection.admit(goal, cid, registry[cid], ROOT)
    assert typed["admitted"] is should_admit
    compiled = {"selected_capability": cid,
                "front_compiler": {"rules_applied": ["F15_EXPLICIT_CAPABILITY_ID_NAMED"]}}
    result = admission.route_admission(goal, compiled, registry)
    assert result["admitted"] is should_admit
    if not should_admit:
        assert result["typed_binding_reason"] == typed["reason"]
        assert result["rule"] == "R15_TYPED_INPUT_BINDING_REFUSED"
    else:
        assert result["admission_basis"] == "EXPLICIT_CAPABILITY_ID_IN_GOAL"

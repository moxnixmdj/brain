from copy import deepcopy

from canonical.runtime.terminal_reality_gate_v1 import evaluate
from canonical.runtime.terminal_closure_reducer import REQUIRED_COUNTERS, REQUIRED_PREDICATES

IDS = [f"F{i:02d}" for i in range(19)]

def pointer(*, terminal=False, family_open=0, atoms_proved=38, atoms_open=0):
    return {
        "live_truth": {
            "terminal": terminal,
            "terminal_root_semantics": "FROZEN_19_FAMILY_ACCEPTANCE_AND_OWNERSHIP_FINALITY",
            "frozen_terminal_family_open_count": family_open,
            "frozen_atomic_predicates_proved": atoms_proved,
            "frozen_atomic_predicates_unresolved": atoms_open,
        },
        "terminal_semantics_override": {
            "mandatory_terminal_predicate": "TERMINAL_CLOSURE_REDUCER_ACHIEVED_TRUE",
            "optional_stronger_route": "PROVE_NOT_X_OVER_SOUND_OBSERVABLE_TRACE_ESCAPE_MODEL",
        },
    }

def manifest():
    return {
        "expected_family_count": 19,
        "actual_family_count": 19,
        "families": [{"id": x, "closure_state": "PASS"} for x in IDS],
        "counters": {x: 0 for x in REQUIRED_COUNTERS},
        "terminal_predicates": {x: True for x in REQUIRED_PREDICATES},
    }

def test_gate_passes_exact_frozen_terminal_reducer():
    out=evaluate(pointer(),manifest())
    assert out["terminal_real"] is True
    assert out["phase"] == "TERMINAL"
    assert out["blockers"] == []

def test_old_universal_u_abc_fields_are_not_mandatory_terminal_conjuncts():
    p=pointer()
    p["live_truth"].update({
        "current_U_empty_proved": False,
        "router_registry_real_selected_cover_complete": False,
        "complete_selected_context_ABC_closed": False,
        "D_finality_closed": False,
    })
    out=evaluate(p,manifest())
    assert out["terminal_real"] is True
    assert out["universal_trace_not_x_required_for_terminal"] is False

def test_open_frozen_family_fails_closed():
    m=manifest()
    m["families"][3]["closure_state"]="OPUS55_ACCEPTANCE_OPEN"
    out=evaluate(pointer(family_open=1,atoms_proved=37,atoms_open=1),m)
    assert out["terminal_real"] is False
    assert out["phase"] == "FROZEN_ACCEPTANCE_CLOSURE"
    assert "FAMILY_OPEN:F03" in out["blockers"]

def test_acceptance_predicate_false_fails_closed():
    m=manifest()
    m["terminal_predicates"]["all_frozen_opus_acceptance_predicates_pass"]=False
    out=evaluate(pointer(family_open=1,atoms_proved=37,atoms_open=1),m)
    assert out["terminal_real"] is False
    assert "PREDICATE_NOT_TRUE:all_frozen_opus_acceptance_predicates_pass" in out["blockers"]

def test_missing_semantics_override_fails_closed():
    p=pointer()
    p.pop("terminal_semantics_override")
    out=evaluate(p,manifest())
    assert out["terminal_real"] is False
    assert "TERMINAL_SEMANTICS_OVERRIDE_MISSING" in out["blockers"]

def test_false_positive_terminal_declaration_cannot_override_reducer():
    m=manifest()
    m["terminal_predicates"]["proof_bundle_frozen"]=False
    out=evaluate(pointer(terminal=True),m)
    assert out["terminal_real"] is False
    assert "DECLARED_TERMINAL_INCONSISTENT_WITH_FROZEN_REDUCER" in out["blockers"]

def test_derived_terminal_warns_if_metadata_lags():
    out=evaluate(pointer(terminal=False),manifest())
    assert out["terminal_real"] is True
    assert out["declaration_warnings"] == [
        "DECLARED_TERMINAL_FALSE_BUT_FROZEN_REDUCER_ACHIEVED_TRUE__METADATA_OUT_OF_SYNC"
    ]

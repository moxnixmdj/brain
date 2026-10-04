import json
from pathlib import Path
from canonical.runtime.livebench_if_execution_precommit_v1 import verify_precommit

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"canonical/governance/LIVEBENCH_IF_EXECUTION_PRECOMMIT_V1.json"

def load():
    return json.loads(MANIFEST.read_text())

def test_exact_manifest_passes_zero_credit():
    o=verify_precommit(load())
    assert o["precommit_pass"] is True
    assert o["terminal_cases_consumed"] == 0
    assert o["resource_fit_proved"] is False
    assert o["generic_isolation_instantiation_proved"] is False
    assert o["shadow_collection_authority"] is False
    assert o["fresh_reality_authority"] is False
    assert o["acceptance_credit_authorized"] is False

def test_candidate_commit_mutation_fails():
    x=load(); x["candidate"]["commit"]="0"*40
    assert verify_precommit(x)["precommit_pass"] is False

def test_feedback_visibility_fails():
    for field in ("result_visible_to_candidate_before_fixed_point","result_visible_to_planner_before_fixed_point","result_visible_to_zero_reality_work_before_fixed_point"):
        x=load(); x["policy"][field]=True
        assert verify_precommit(x)["precommit_pass"] is False

def test_model_or_external_tool_escape_fails():
    x=load(); x["policy"]["allow_optional_model_planner"]=True
    assert verify_precommit(x)["precommit_pass"] is False
    x=load(); x["policy"]["external_tools_allowed"]=True
    assert verify_precommit(x)["precommit_pass"] is False

def test_resource_fit_cannot_be_claimed_by_precommit():
    x=load(); x["environment"]["resource_fit_status"]="PASS"
    assert verify_precommit(x)["precommit_pass"] is False

def test_any_component_change_breaks_digest():
    for component in ("candidate","harness","scorer","environment","policy"):
        x=load(); x[component]["_mutation"]="x"
        assert verify_precommit(x)["precommit_pass"] is False

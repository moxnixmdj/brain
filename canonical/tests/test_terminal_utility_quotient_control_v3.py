import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"canonical/governance/TERMINAL_UTILITY_QUOTIENT_CONTROL_REPAIR_V3.json"

def load():
    return json.loads(P.read_text(encoding="utf-8"))

def test_terminal_objective_frozen():
    d=load()
    assert d["terminal_objective"]=="PERMANENTLY_INTERNALIZE_CONFIGURE_VERIFY_AND_OWN_ALL_USEFUL_OPUS_5_5_CAPABILITIES_AT_EQUAL_OR_BETTER_LEVEL__KNOWLEDGE_EXTERNAL_JIT_ONLY"

def test_exact_target_route_not_unique_gate():
    d=load()
    ids=[r["id"] for r in d["candidate_terminal_routes"]]
    assert ids==["E_EXACT_TARGET_QUOTIENT","S_UTILITY_RELEVANT_SUPERSET","G_GENERATOR_CLOSURE"]
    assert "DO_NOT_SERIALIZE_ALL_PROGRESS_BEHIND_E" in d["tournament_scheduler"]["rule"]

def test_external_reality_last():
    d=load()
    assert d["tournament_scheduler"]["ranking"][-1]=="FULL_BENCHMARK_OR_EXTERNAL_TARGET_RESULT_LAST"
    assert "IRREDUCIBLE_INFORMATION_RESIDUAL_ONLY" in d["current_evidence_role"]["direct_opus_or_target_reality"]

def test_no_credit_from_scheduler_change():
    d=load()
    for k in ["terminal_credit_delta","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"]:
        assert d["accounting"][k]==0

def test_routes_preserve_ownership_and_safety():
    d=load()
    for r in d["candidate_terminal_routes"]:
        req=set(r["requirements"])
        assert any("OWNERSHIP" in x for x in req)
        assert any("RESOURCE_SAFETY_AND_AUTHORITY_NONREGRESSION" in x for x in req)

def test_survival_not_proof():
    d=load()
    assert "ROUTE_SURVIVAL_IS_NOT_PROOF" in d["tournament_scheduler"]["promotion_rule"]

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"canonical/governance/TERMINAL_GENERATOR_BASIS_CANDIDATE_20261006_V1.json"

EXPECTED={
"ADVANCED_AGENTIC_CODING","COMPLEX_MULTI_TOOL_AGENCY","PROFESSIONAL_KNOWLEDGE_WORK",
"BUSINESS_WORKFLOW_AUTOMATION","MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING",
"AGENTIC_SCIENTIFIC_RESEARCH","VISION_AND_DENSE_DOCUMENT_UNDERSTANDING",
"COMPUTER_AND_BROWSER_USE","FINANCIAL_ANALYSIS","INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT",
"LONG_HORIZON_MEMORY_AND_CONTINUITY","SUBAGENT_DELEGATION_AND_COORDINATION",
"SELF_VERIFICATION_DEBUGGING_AND_RECOVERY","ARTIFACT_CREATION","COMMUNICATION_AND_SYNTHESIS",
"TOOL_DISCOVERY_SELECTION_AND_LEARNING","UNKNOWN_DOMAIN_ADAPTATION","MULTI_CAPABILITY_COMPOSITION",
"EXACT_SYMBOLIC_COMPUTATION"}

def load(): return json.loads(P.read_text(encoding="utf-8"))

def test_exact_19_family_totality():
    d=load()
    assert set(d["family_factorization"])==EXPECTED
    assert d["candidate_compression"]["target_family_count"]==19

def test_seven_generators_five_owned_two_open():
    d=load()
    gs=d["generators"]
    assert len(gs)==7
    assert sum(g["status"]=="VERIFIED_OWNED" for g in gs)==5
    assert sum(g["status"]=="UNBOUND_RESIDUAL_GENERATOR" for g in gs)==2
    assert d["candidate_compression"]["verified_owned_generator_count"]==5
    assert d["candidate_compression"]["unbound_residual_generator_count"]==2

def test_every_family_has_nonempty_generator_mapping():
    d=load()
    known={g["id"] for g in d["generators"]}
    for fam, gen in d["family_factorization"].items():
        assert gen, fam
        assert set(gen)<=known

def test_owned_singletons_bind_to_exact_owned_generators():
    d=load()
    m=d["family_factorization"]
    assert m["LONG_HORIZON_MEMORY_AND_CONTINUITY"]==["G1_PERSISTENT_STATE_AND_CONTINUITY"]
    assert m["SUBAGENT_DELEGATION_AND_COORDINATION"]==["G2_DELEGATION_AND_COORDINATION"]
    assert m["SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"]==["G3_VERIFICATION_DEBUGGING_AND_RECOVERY"]
    assert m["TOOL_DISCOVERY_SELECTION_AND_LEARNING"]==["G4_TOOL_DISCOVERY_SELECTION_AND_LEARNING"]
    assert m["EXACT_SYMBOLIC_COMPUTATION"]==["G5_EXACT_DETERMINISTIC_COMPUTATION"]

def test_candidate_is_fail_closed_zero_credit():
    d=load()
    assert "NO_CLAIM_THE_19_TO_7_FACTORIZATION_IS_PROVED" in d["hard_nonclaims"]
    for k in ["terminal_credit_delta","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"]:
        assert d["accounting"][k]==0

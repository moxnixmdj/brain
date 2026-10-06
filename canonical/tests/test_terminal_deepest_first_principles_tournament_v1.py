import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "canonical/governance/TERMINAL_DEEPEST_FIRST_PRINCIPLES_TOURNAMENT_V1.json"

def load():
    return json.loads(PATH.read_text(encoding="utf-8"))

def test_terminal_objective_is_frozen():
    d = load()
    assert d["terminal_objective"] == "PERMANENTLY_INTERNALIZE_CONFIGURE_VERIFY_AND_OWN_ALL_USEFUL_OPUS_5_5_CAPABILITIES_AT_EQUAL_OR_BETTER_LEVEL__KNOWLEDGE_EXTERNAL_JIT_ONLY"
    assert "DO_NOT_WEAKEN_OR_SUBSTITUTE_THE_TERMINAL_OBJECTIVE" in d["mission_lock"]

def test_existing_obligations_are_not_axioms():
    d = load()
    obs = d["critical_observation"]
    assert obs["current_open_obligations_are_not_axioms"] is True
    assert obs["current_routes_are_not_axioms"] is True
    assert obs["current_architecture_is_not_axiomatic"] is True

def test_tournament_starts_below_leaf_benchmarks():
    d = load()
    ids = [r["id"] for r in d["rounds"]]
    assert ids[:3] == [
        "SEMANTIC_MINIMALITY",
        "MINIMUM_CAUSAL_GENERATING_BASIS",
        "OBLIGATION_NECESSITY_TOURNAMENT",
    ]
    assert ids.index("BENCHMARK_AND_EXTERNAL_WITNESS_ELIMINATION") > ids.index("OBLIGATION_NECESSITY_TOURNAMENT")

def test_external_reality_is_last_resort():
    d = load()
    r4 = next(r for r in d["rounds"] if r["id"] == "BENCHMARK_AND_EXTERNAL_WITNESS_ELIMINATION")
    order = r4["proof_order"]
    assert order[-1] == "FULL_EXTERNAL_BENCHMARK"
    assert order.index("MINIMUM_MATCHED_DISCRIMINATING_RESULT") < order.index("FULL_EXTERNAL_BENCHMARK")
    assert "NEVER_AS_ROUTINE_RESEARCH" in r4["astra_rule"]

def test_unproved_necessity_never_silently_deletes_truth():
    d = load()
    r2 = next(r for r in d["rounds"] if r["id"] == "OBLIGATION_NECESSITY_TOURNAMENT")
    assert "UNPROVED_NECESSITY_DOES_NOT_DELETE_A_TRUTH_OBLIGATION" in r2["hard_rule"]
    assert d["promotion_law"]["truth_deletion_requires_verified_redundancy_or_countermodel"] is True

def test_donor_independence_and_clean_room_are_terminal_requirements():
    d = load()
    r6 = next(r for r in d["rounds"] if r["id"] == "DONOR_DELETION_AND_CLEAN_ROOM_FINALITY")
    steps = r6["steps"]
    assert "REMOVE_OPAQUE_DONOR_CAPABILITY_EXECUTION" in steps
    assert "RECONSTRUCT_FROM_CANONICAL_BRAIN_OWNED_ARTIFACTS" in steps
    assert "REPLAY_MINIMUM_TERMINAL_CERTIFICATE_BASIS_ON_INDEPENDENT_CARRIER" in steps

def test_control_repair_grants_zero_credit():
    d = load()
    a = d["accounting"]
    assert a["incremental_spend_usd"] == 0
    assert a["terminal_credit_delta"] == 0
    assert a["acceptance_credit_delta"] == 0
    assert a["family_credit_delta"] == 0
    assert a["capability_credit_delta"] == 0
    assert a["ownership_credit_delta"] == 0

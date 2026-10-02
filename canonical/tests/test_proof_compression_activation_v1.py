import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def git_blob_sha(rel):
    data=(ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

receipt=load("canonical/verification/PROOF_COMPRESSION_KERNELS_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
activation=load("canonical/governance/PROOF_COMPRESSION_KERNELS_ACTIVATION_V1.json")
optimizer=load("canonical/governance/EXECUTION_FIRST_SELF_PROVING_OPTIMIZER_V1.json")
hypergraph=load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json")
evidence=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")

assert receipt["status"]=="INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_7_OF_7_KERNEL_BLOBS__ALL_DETERMINISTIC_TESTS_PASS__ZERO_CREDIT"
assert receipt["public_runner"]["conclusion"]=="success"
for rel,want in receipt["exact_brain_blobs"].items():
    got=git_blob_sha(rel)
    assert got==want,(rel,got,want)

assert activation["status"]=="ACTIVE_INDEPENDENT_PASS__ZERO_REALITY_REDUCTION_ONLY__ZERO_CREDIT"
assert activation["new_reality_units_consumed"]==0
assert activation["capability_credit_delta"]==0
assert activation["family_credit_delta"]==0
assert activation["promotion_authority"] is False
assert activation["execution_authority"] is False

expected_steps=[
    "NORMALIZED_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA",
    "EPISTEMIC_CLOSURE_AND_MINIMUM_DISCRIMINATOR",
    "LOAD_BEARING_COMPONENT_PROOF_SLICING",
]
ladder=optimizer["execution_ladder"]
reality_idx=ladder.index("EXACT_MINIMUM_REALITY_CUT")
for step in expected_steps:
    assert step in ladder
    assert ladder.index(step) < reality_idx
assert optimizer["proof_compression_kernels"]["status"]=="ACTIVE_INDEPENDENT_PASS__ZERO_REALITY_ONLY"
assert optimizer["proof_compression_kernels"]["terminal_credit_from_kernels_alone"] is False
assert optimizer["reality_query_admission"]["proof_compression_kernels_required"] is True

proved={
    row["predicate_id"]
    for row in evidence["claims"]
    if row.get("state")=="PROVED"
}
actions={a["id"]:a for a in hypergraph["actions"]}
required_action_ids=[
    "RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA",
    "RUN_EPISTEMIC_CLOSURE_DIRECT_JUDGMENT_SUBTRACTION",
    "RUN_COMPOSITION_COMPONENT_PROOF_SLICER",
]
for aid in required_action_ids:
    assert aid in actions,aid
    a=actions[aid]
    assert a["new_reality_units"]==0
    assert not (set(a["target_predicates"]) & proved),(aid,set(a["target_predicates"]) & proved)

assert "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR" not in actions["RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA"]["target_predicates"]
assert "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" not in actions["RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA"]["target_predicates"]

print("test_proof_compression_activation_v1: PASS")

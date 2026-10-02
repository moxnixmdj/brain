import json
from pathlib import Path

from canonical.runtime.multiplex_exhaustive_family_witness_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

FAMILY = "COMMUNICATION_AND_SYNTHESIS"
BEHAVIOR = "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
BINDING = "canonical/governance/P3_SYNTHESIS_T1_T3_MULTIPLEX_TERMINAL_BINDING_V1.json"
BLOB = "ad790afa864bd8f770c3d8a6e3ac901ed2843d26"

base = dict(
    family=FAMILY,
    behavior_id=BEHAVIOR,
    binding_path=BINDING,
    binding_blob_sha=BLOB,
    protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
    registry=load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
    direct_contracts=load("canonical/governance/FOUR_UNCOVERED_BEHAVIORAL_PROOF_CONTRACTS_V1.json"),
    binding=load(BINDING),
    binding_verification=load("canonical/verification/P3_SYNTHESIS_T1_T3_MULTIPLEX_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
    executor_manifest=load("canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json"),
    terminal_result=load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"),
    postwave_reduction=load("canonical/verification/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json"),
)

out = evaluate(**base)
assert out["pass"] is True, out
w = out["candidate_witness"]
assert w["family"] == FAMILY
assert w["mode"] == "EXHAUSTIVE_FINITE"
assert w["result"] == {"exhaustive": True, "all_cases_pass": True}
assert w["source_parent_portfolios"] == ["T1", "T3"]
assert w["source_parent_observation_count"] == 2
assert w["verified"] is False
assert w["independent"] is False

bad = dict(base)
bad["registry"] = json.loads(json.dumps(base["registry"]))
bad["registry"]["family_to_residual_contracts"][FAMILY] = [BEHAVIOR, "OTHER"]
assert evaluate(**bad)["pass"] is False

bad = dict(base)
bad["direct_contracts"] = json.loads(json.dumps(base["direct_contracts"]))
for row in bad["direct_contracts"]["obligations"]:
    if row["behavior_id"] == BEHAVIOR:
        row["proof_mode"] = "PREDECLARED_MATCHED_STATISTICAL_COMPARISON"
assert evaluate(**bad)["pass"] is False

bad = dict(base)
bad["terminal_result"] = json.loads(json.dumps(base["terminal_result"]))
for row in bad["terminal_result"]["reduction_input"]["wave"]["parent_portfolio_receipts"]["T3"]:
    if row.get("behavior_id") == BEHAVIOR:
        row["direct_instrumentation_pass"] = False
assert evaluate(**bad)["pass"] is False

bad = dict(base)
bad["binding_verification"] = json.loads(json.dumps(base["binding_verification"]))
bad["binding_verification"]["exact_brain_blobs"][BINDING] = "stale"
assert evaluate(**bad)["pass"] is False

bad = dict(base)
bad["postwave_reduction"] = json.loads(json.dumps(base["postwave_reduction"]))
bad["postwave_reduction"]["public_verifier"]["conclusion"] = "failure"
assert evaluate(**bad)["pass"] is False

bad = dict(base)
bad["binding"] = json.loads(json.dumps(base["binding"]))
bad["binding"]["terminal_acceptance"]["standalone_synthetic_whole_domain_score_forbidden"] = False
assert evaluate(**bad)["pass"] is False

print("test_multiplex_exhaustive_family_witness_v1: PASS")

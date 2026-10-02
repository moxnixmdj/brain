from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

receipt = load("canonical/verification/OPUS55_BRAIN_WITNESS_NORMALIZATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
candidate = load("canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json")
activation = load("canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_ACTIVATION_V1.json")
matched = load("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_ACTIVATION_V1.json")
hyper = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json")
authority = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
basis = load("canonical/governance/MINIMUM_TERMINAL_BASIS_ACTIVATION_V1.json")

assert receipt["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__9_OF_9"), receipt
assert receipt["target_atom_mapping_verified"] is False
assert receipt["semantic_implication_verified"] is False
assert receipt["capability_credit_delta"] == 0
assert receipt["family_credit_delta"] == 0

assert activation["exact_candidate_blob_sha"] == "68af5a081b87ce83db6f69e864843d090206db4c"
assert activation["exact_state"]["witness_count"] == 9
assert activation["exact_state"]["catalog_normalization_verified"] is True
assert activation["exact_state"]["target_atom_mapping_verified"] is False
assert activation["exact_state"]["semantic_implication_verified"] is False
assert activation["execution_authority"] is False
assert activation["promotion_authority"] is False

assert candidate["witness_count"] == 9
assert all(x["normalized_target_atoms"] == [] for x in candidate["witnesses"])
assert all(x["semantic_implications"] == [] for x in candidate["witnesses"])

assert matched["exact_state"]["target_source_provenance_verified"] is True
assert matched["exact_state"]["brain_witness_normalization_verified"] is True
assert matched["exact_state"]["brain_witness_target_atom_mapping_verified"] is False
assert matched["exact_state"]["semantic_implication_verified"] is False

action = next(x for x in hyper["actions"] if x["id"] == "RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA")
pre = {x["id"]: x for x in action["preconditions"]}
assert pre["PROOF_COMPRESSION_KERNELS_INDEPENDENT_PASS"]["satisfied"] is True
assert pre["MATCHED_TARGET_NORMALIZATION_INDEPENDENT_PASS"]["satisfied"] is True
assert pre["MATCHED_BRAIN_WITNESS_NORMALIZATION_INDEPENDENT_PASS"]["satisfied"] is True

assert basis["status"].startswith("ACTIVE_INDEPENDENT_PASS")
assert basis["capability_credit_delta"] == 0
assert basis["family_credit_delta"] == 0

assert authority["truth"]["opus55_acceptance"] == "4/19_PASS__15/19_OPEN"
assert authority["truth"]["achieved"] is False
assert authority["atomic_acceptance_frontier"]["proved"] == 9
assert authority["atomic_acceptance_frontier"]["blocked"] == 29
assert authority["atomic_acceptance_frontier"]["total"] == 38
assert any("TARGET_ATOM_MAPPING_AND_SEMANTIC_IMPLICATION_REMAIN_OPEN" in x for x in authority["residual"])

print("test_witness_normalization_authority_reconciliation_v1: PASS")

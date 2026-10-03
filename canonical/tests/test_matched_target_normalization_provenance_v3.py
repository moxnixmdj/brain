import hashlib
import json
from pathlib import Path

from canonical.runtime.matched_target_normalization_provenance_verifier_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def git_blob_sha(rel):
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

protocol_path = "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
registry_path = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
evidence_path = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
matched_path = "canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json"
candidate_path = "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_CANDIDATE_V3.json"
provenance_path = "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json"

protocols = load(protocol_path)
registry = load(registry_path)
evidence = load(evidence_path)
matched = load(matched_path)
candidate = load(candidate_path)
provenance = load(provenance_path)

assert candidate["authority"]["protocols"]["git_blob_sha"] == git_blob_sha(protocol_path)
assert candidate["authority"]["predicate_registry"]["git_blob_sha"] == git_blob_sha(registry_path)
assert candidate["authority"]["evidence_bindings"]["git_blob_sha"] == git_blob_sha(evidence_path)
assert candidate["authority"]["matched_scope_residual"]["git_blob_sha"] == git_blob_sha(matched_path)
assert provenance["authority"]["candidate"]["git_blob_sha"] == git_blob_sha(candidate_path)
assert provenance["authority"]["protocols"]["git_blob_sha"] == git_blob_sha(protocol_path)
assert provenance["authority"]["predicate_registry"]["git_blob_sha"] == git_blob_sha(registry_path)
assert provenance["authority"]["evidence_bindings"]["git_blob_sha"] == git_blob_sha(evidence_path)
assert provenance["authority"]["matched_scope_residual"]["git_blob_sha"] == git_blob_sha(matched_path)

live = sorted({t for edge in matched["implications"] for t in edge["then"]})
candidate_ids = sorted(x["predicate_id"] for x in candidate["targets"])
provenance_ids = sorted(x["predicate_id"] for x in provenance["targets"])
assert len(live) == 8
assert candidate_ids == live
assert provenance_ids == live

proved = {x["predicate_id"] for x in evidence["claims"] if x.get("state") == "PROVED"}
assert proved.isdisjoint(live)

out = evaluate(protocols, registry, candidate, provenance)
assert out["status"] == "PASS__ALL_TARGET_ATOMS_AND_METRICS_BOUND_TO_EXACT_FROZEN_SOURCE_LITERALS", out
assert out["verified_target_count"] == 8, out
assert out["verified_atom_count"] == 37, out
assert out["verified_metric_requirement_count"] == 7, out
assert out["semantic_implication_verified"] is False, out
assert all(x["source_literal_binding_pass"] for x in out["target_results"]), out
assert out["capability_credit_delta"] == 0
assert out["family_credit_delta"] == 0
assert out["new_reality_units_consumed"] == 0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False

bad = json.loads(json.dumps(provenance))
bad["targets"][0]["atom_sources"][0]["sources"][0]["literal"] = "not a current frozen literal"
failed = evaluate(protocols, registry, candidate, bad)
assert failed["status"] == "FAIL_CLOSED", failed
assert any("LITERAL_NOT_FOUND" in e for e in failed["errors"]), failed

print("test_matched_target_normalization_provenance_v3: PASS")

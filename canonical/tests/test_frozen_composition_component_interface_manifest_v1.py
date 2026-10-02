import hashlib
import json
from pathlib import Path

from canonical.runtime.composition_interface_manifest_compiler_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def git_blob_sha(rel):
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


protocol_path = "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
manifest_path = "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json"

protocols = load(protocol_path)
manifest = load(manifest_path)
derived = evaluate(protocols)

assert derived["status"] == "LITERAL_INTERFACE_MANIFEST_READY__FAMILY_AND_RECEIPT_BINDINGS_OPEN", derived
assert manifest["status"] == "CANDIDATE_LITERAL_EXTRACTION__INDEPENDENT_VERIFICATION_REQUIRED__ZERO_CREDIT", manifest
assert manifest["authority"]["protocols"]["git_blob_sha"] == git_blob_sha(protocol_path), manifest

for key in (
    "claim_id",
    "family",
    "source_acceptance_literal",
    "source_task_dimensions",
    "interfaces",
    "composition_only_dimensions",
    "isolated_component_interface_count",
    "unique_component_literals",
    "family_bindings_complete",
    "receipt_bindings_complete",
):
    assert manifest[key] == derived[key], (key, manifest[key], derived[key])

assert manifest["new_reality_units_consumed"] == 0
assert manifest["incremental_spend_usd"] == 0
assert manifest["capability_credit_delta"] == 0
assert manifest["family_credit_delta"] == 0
assert manifest["execution_authority"] is False
assert manifest["promotion_authority"] is False

print("test_frozen_composition_component_interface_manifest_v1: PASS")

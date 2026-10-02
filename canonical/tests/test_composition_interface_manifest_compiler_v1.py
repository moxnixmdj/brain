import json
from pathlib import Path

from canonical.runtime.composition_interface_manifest_compiler_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]
protocols = json.loads(
    (ROOT / "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json").read_text(encoding="utf-8")
)

out = evaluate(protocols)
assert out["status"] == "LITERAL_INTERFACE_MANIFEST_READY__FAMILY_AND_RECEIPT_BINDINGS_OPEN", out
assert out["claim_id"] == "MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1", out
assert out["isolated_component_interface_count"] == 12, out
assert out["unique_component_literals"] == [
    "artifact creation",
    "artifact production",
    "browser/computer action",
    "coding",
    "debugging",
    "delegation",
    "evidence synthesis",
    "memory",
    "recovery",
    "research",
    "tool discovery",
    "tool use",
], out
assert out["composition_only_dimensions"] == [{
    "source_dimension_index": 4,
    "source_dimension_literal": "cross-capability state handoff and rollback",
    "reason": "NO_LITERAL_PLUS_JOINED_ISOLATED_COMPONENT_CHAIN",
}], out
assert all(x["family_binding"] is None for x in out["interfaces"])
assert all(x["receipt_binding"] is None for x in out["interfaces"])
assert out["capability_credit_delta"] == 0
assert out["family_credit_delta"] == 0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False

bad = json.loads(json.dumps(protocols))
row = next(r for r in bad["protocols"] if r["family"] == "MULTI_CAPABILITY_COMPOSITION")
row["acceptance"] = "changed"
failed = evaluate(bad)
assert failed["status"] == "FAIL_CLOSED", failed
assert "ISOLATED_COMPONENT_SCOPED_PROOF_CLAUSE_MISSING" in failed["errors"], failed

print("test_composition_interface_manifest_compiler_v1: PASS")

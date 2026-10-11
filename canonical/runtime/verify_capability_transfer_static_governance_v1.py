from pathlib import Path
import json

R=Path(__file__).resolve().parents[2]
def J(p): return json.loads((R/p).read_text())

p=J("canonical/CANONICAL_POINTER.json")
b=p["boot_requirements"]
assert "canonical/laws/CAPABILITY_TRANSFER_VS_COGNITION_OUTSOURCING_LAW_V1.md" in p["mandatory_laws"]
assert b["capability_transfer_vs_cognition_outsourcing_law_required"] is True
assert b["capability_transfer_ownership_gate_required"] is True
assert b["teacher_or_donor_runtime_cognition_forbidden"] is True
assert b["copied_or_rehosted_teacher_is_not_transfer"] is True
assert b["post_donor_removal_heldout_qualification_required"] is True
s=J("canonical/governance/WHITE_BOX_CAPABILITY_CAPSULE_SCHEMA_V3.json")
assert s["promotion_requires_transfer_gate_pass"] is True
d=J("canonical/governance/DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_V2.json")
assert d["fail_closed"] is True
print("CAPABILITY_TRANSFER_STATIC_GOVERNANCE_PASS")

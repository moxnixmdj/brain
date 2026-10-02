from canonical.runtime.composition_component_proof_slicer_v1 import evaluate

doc = {
    "claim_id": "FROZEN_COMPOSITION_1",
    "interfaces": [
        {"component_id": "browser", "interface_id": "observe_act", "required_properties": ["observe", "validated_action"]},
        {"component_id": "memory", "interface_id": "state", "required_properties": ["persist", "restore"]},
    ],
    "receipts": [
        {
            "receipt_id": "r1", "component_id": "browser", "interface_id": "observe_act",
            "proved_properties": ["observe"], "verified": True, "independent": True,
            "contamination_clean": True, "acceptance_scoped": True,
            "binds_frozen_claim": "FROZEN_COMPOSITION_1",
        },
        {
            "receipt_id": "r2", "component_id": "browser", "interface_id": "observe_act",
            "proved_properties": ["validated_action"], "verified": True, "independent": True,
            "contamination_clean": True, "acceptance_scoped": True,
            "binds_frozen_claim": "FROZEN_COMPOSITION_1",
        },
        {
            "receipt_id": "r3", "component_id": "memory", "interface_id": "state",
            "proved_properties": ["persist", "restore"], "verified": True, "independent": True,
            "contamination_clean": True, "acceptance_scoped": True,
            "binds_frozen_claim": "FROZEN_COMPOSITION_1",
        },
    ],
}
r = evaluate(doc)
assert r["status"] == "ALL_USED_COMPONENT_INTERFACES_SCOPED_PROVED", r
assert r["all_used_component_interfaces_scoped_proved"] is True

bad = dict(doc)
bad["receipts"] = doc["receipts"][:-1]
r = evaluate(bad)
assert r["status"] == "RESIDUAL_COMPONENT_INTERFACE_PROOFS_OPEN", r
memory = [x for x in r["interfaces"] if x["component_id"] == "memory"][0]
assert memory["missing_properties"] == ["persist", "restore"], r

wrong_claim = dict(doc)
wrong_claim["receipts"] = [
    {**x, "binds_frozen_claim": "OTHER"} for x in doc["receipts"]
]
r = evaluate(wrong_claim)
assert r["all_used_component_interfaces_scoped_proved"] is False, r

print("test_composition_component_proof_slicer_v1: PASS")

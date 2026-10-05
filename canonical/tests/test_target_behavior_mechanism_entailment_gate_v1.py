from canonical.runtime.target_behavior_mechanism_entailment_gate_v1 import evaluate, TARGET_RULE

def base(relation="EXPLICIT_TARGET_BEHAVIOR", mandatory=True, receipt="receipt://x"):
    return {
        "target_rule": TARGET_RULE,
        "obligations": [{
            "family": "F",
            "behavior_id": "B",
            "contract_kind": "TARGET_BEHAVIOR",
            "mandatory_acceptance_obligation": mandatory,
            "target_entailment_relation": relation,
            "target_entailment_receipt": receipt,
            "registry_incidence_only": False,
        }],
    }

def test_explicit_target_behavior_with_receipt_passes():
    out = evaluate(base())
    assert out["status"] == "PASS"
    assert out["mandatory_admissible_count"] == 1

def test_logically_necessary_observable_consequence_passes():
    out = evaluate(base("LOGICALLY_NECESSARY_OBSERVABLE_CONSEQUENCE"))
    assert out["status"] == "PASS"

def test_registry_incidence_alone_cannot_make_mandatory():
    doc = base()
    doc["obligations"][0]["registry_incidence_only"] = True
    assert evaluate(doc)["status"] == "FAIL_CLOSED"

def test_implementation_mechanism_without_entailment_fails():
    doc = base("SUFFICIENT_MECHANISM_ONLY")
    doc["obligations"][0]["contract_kind"] = "IMPLEMENTATION_MECHANISM"
    assert evaluate(doc)["status"] == "FAIL_CLOSED"

def test_out_of_scope_cannot_be_mandatory():
    assert evaluate(base("OUT_OF_SCOPE"))["status"] == "FAIL_CLOSED"

def test_nonmandatory_supporting_mechanism_is_allowed():
    doc = base("SUFFICIENT_MECHANISM_ONLY", mandatory=False, receipt="")
    doc["obligations"][0]["contract_kind"] = "IMPLEMENTATION_MECHANISM"
    out = evaluate(doc)
    assert out["status"] == "PASS"
    assert out["mandatory_admissible_count"] == 0

def test_mandatory_entailment_requires_receipt():
    assert evaluate(base(receipt=""))["status"] == "FAIL_CLOSED"

def test_target_rule_must_match_canonical_semantics():
    doc = base()
    doc["target_rule"] = "INTERNAL_IMPLEMENTATION_PARITY"
    assert evaluate(doc)["status"] == "FAIL_CLOSED"

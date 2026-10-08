"""Independent discriminative tests for automatic v1 selected semantic policy dispatch."""
import json
from canonical.runtime.selected_semantic_discriminator_dispatch_v1 import evaluate

POLICY = ("Total exposure means exposure_amount. "
          "Apply Rule A unless Total exposure is at least 125.50.")
MAP = {"TRUE": "APPLY_EXCEPTION", "FALSE": "DO_NOT_APPLY_EXCEPTION"}
ALIAS = "EXPOSURE_EXCEPTION_APPLIES"

def payload(value="130.00", text=POLICY, alias=ALIAS):
    return {
        "predicate_id": alias,
        "target_claim_id": "selected",
        "source_text": text,
        "source_id": "policy",
        "claims": [{"claim_id": "selected",
                    "kind": "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION"}],
        "fact_source": json.dumps({
            "schema_id": "FINANCE_TYPED_CONTEXT_V1",
            "fields": {"exposure_amount": {"type": "DECIMAL_STRING", "value": value}}},
            separators=(",", ":")),
        "fact_source_id": "case-facts",
    }

def test_true_selected_without_caller_guess():
    out = evaluate(payload(), MAP)
    assert out["pass"] is True
    assert out["predicate_truth"] == "TRUE"
    assert out["selected_policy_id"] == "APPLY_EXCEPTION"
    assert out["predicate_id"].startswith("source-condition-sha256:")
    assert out["requested_predicate_id"] == ALIAS
    assert out["requested_predicate_id_authority"] is False
    assert out["source_authorization_verified"] is False
    assert out["policy_adequacy_authority"] is False
    assert out["u_subtraction_authorized"] is False
    assert out["terminal_credit_delta"] == 0

def test_false_selected_without_caller_guess():
    out = evaluate(payload("100.00"), MAP)
    assert out["pass"] is True
    assert out["predicate_truth"] == "FALSE"
    assert out["selected_policy_id"] == "DO_NOT_APPLY_EXCEPTION"
    assert out["selected_truth_certificate"]["predicate_truth"] == "FALSE"
    assert out["predicate_id"] == out["selected_truth_certificate"]["predicate_id"]

def test_alias_relabel_never_changes_verified_predicate_or_policy():
    a = evaluate(payload("130.00", alias="EXPOSURE_EXCEPTION_APPLIES"), MAP)
    b = evaluate(payload("130.00", alias="SOMETHING_ELSE"), MAP)
    assert a["pass"] is True and b["pass"] is True
    assert a["predicate_id"] == b["predicate_id"]
    assert a["selected_policy_id"] == b["selected_policy_id"] == "APPLY_EXCEPTION"
    assert a["requested_predicate_id"] != b["requested_predicate_id"]
    assert b["requested_predicate_id_authority"] is False

def test_changed_source_changes_verified_predicate_identity():
    changed = POLICY.replace("125.50", "120.00")
    a = evaluate(payload("130.00"), MAP)
    b = evaluate(payload("130.00", text=changed), MAP)
    assert a["pass"] is True and b["pass"] is True
    assert a["predicate_id"] != b["predicate_id"]
    assert a["requested_predicate_id"] == b["requested_predicate_id"] == ALIAS

def test_unsupported_paraphrase_stays_unknown():
    out = evaluate(payload(text=POLICY.replace(
        "unless Total exposure", "unless Aggregate exposure")), MAP)
    assert out["pass"] is False
    assert out["predicate_truth"] == "UNKNOWN"
    assert out["selected_policy_id"] is None

def test_reject_untrusted_claimed_truth():
    p = payload()
    p["claims"][0]["condition_holds"] = False
    out = evaluate(p, MAP)
    assert out["pass"] is False
    assert out["reason"] == "CALLER_MUST_NOT_SUPPLY_PREDICATE_TRUTH"

def test_reject_missing_or_forged_fact_source():
    p = payload()
    p["fact_source"] = '{"fields":{"exposure_amount":{}}}'
    out = evaluate(p, MAP)
    assert out["pass"] is False
    assert out["predicate_truth"] == "UNKNOWN"

def test_refuse_incomplete_policy_map():
    out = evaluate(payload(), {"TRUE":"APPLY_EXCEPTION"})
    assert out["pass"] is False
    assert out["reason"] == "EXACT_TRUE_FALSE_POLICY_MAP_REQUIRED"

def test_source_and_fact_bytes_bind_receipt():
    a = evaluate(payload("130.00"), MAP)
    b = evaluate(payload("131.00"), MAP)
    assert a["pass"] is True and b["pass"] is True
    assert a["input_binding_sha256"] != b["input_binding_sha256"]
    assert a["predicate_id"] == b["predicate_id"]
    assert a["source_authorization_verified"] is False
    assert b["terminal_authority"] is False

def test_reject_non_raw_or_multiple_claims():
    p = payload()
    p["claims"].append({"claim_id":"injected","kind":"CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION"})
    assert evaluate(p, MAP)["pass"] is False
    p = payload()
    p["claims"][0]["kind"] = "OPAQUE_LLM_JUDGMENT"
    assert evaluate(p, MAP)["pass"] is False

def test_repository_runner_writes_actual_selection(tmp_path):
    from canonical.runtime.selected_semantic_discriminator_dispatch_v1 import run
    (tmp_path / "payload.json").write_text(json.dumps(payload("130.00")))
    (tmp_path / "map.json").write_text(json.dumps(MAP))
    receipt = run({
        "payload_path": "payload.json",
        "policy_map_path": "map.json",
        "output_path": "receipts/selection.json",
    }, tmp_path)
    assert receipt["output_verified"] is True
    assert receipt["predicate_truth"] == "TRUE"
    persisted = json.loads((tmp_path / "receipts/selection.json").read_text())
    assert persisted["selected_policy_id"] == "APPLY_EXCEPTION"
    assert persisted["predicate_id"].startswith("source-condition-sha256:")
    assert persisted["requested_predicate_id"] == ALIAS
    assert persisted["terminal_credit_delta"] == 0

def test_repository_runner_blocks_escape_and_overwrite(tmp_path):
    import pytest
    from canonical.runtime.selected_semantic_discriminator_dispatch_v1 import run
    (tmp_path / "payload.json").write_text(json.dumps(payload()))
    (tmp_path / "map.json").write_text(json.dumps(MAP))
    with pytest.raises(ValueError, match="PATH_OUTSIDE_REPOSITORY"):
        run({"payload_path":"payload.json", "policy_map_path":"map.json",
             "output_path":"../outside.json"},tmp_path)
    with pytest.raises(ValueError, match="OUTPUT_MUST_NOT_OVERWRITE_INPUT"):
        run({"payload_path":"payload.json","policy_map_path":"map.json",
             "output_path":"payload.json"},tmp_path)

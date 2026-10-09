from canonical.runtime.cc_r3_counterexample_v1 import evaluate

CLAIM_ID="fda1409a94d983f61888f08f3df99cad50dc36edc3f5feb01b6df20e31156eaa"


def claim_doc():
    return {
        "claim":{
            "claim_kind":"CHECKPOINT_ACCEPTANCE",
            "mission_blob_sha":"7ad5f82d8434966781bf97c725d482e10133fc7c",
            "scope_sha256":"e7461e484491196b40ebf88b7840fe17fb464be83f7a74d13363cd0427c665c9",
            "target_predicate_sha256":"24820adb64697831d6ef7b13ea471c6f23a6fc1b995a7f15deb3f65963b8c0ba",
            "semantics_sha256":"19fe42d190497e96546799cbdaa269c09f2505f0b76fa735d3f8c10e9e5eac3c",
            "epoch":"2026-10-09-CCRT-R3-CLAIM-V1",
            "authority_id":"PROJECT_BRAIN_CURRENT_TERMINAL_AUTHORITY_CHECKPOINT_OBJECTIVE",
            "claim_id":CLAIM_ID,
            "terminal_credit_delta":0,
        },
        "semantics_descriptor":{
            "b_plus_rule":"OPEN_OR_UNKNOWN_FROZEN_ACCEPTANCE_PREDICATE_RETAINS_BOTH_PASS_AND_FAIL_COMPLETIONS_UNTIL_PROVED",
            "g_minus_rule":"ONLY_COMPLETIONS_SATISFYING_ALL_MANDATORY_TERMINAL_PREDICATES_ARE_DEFINITELY_GOOD",
        },
    }


def manifest(open_count=1):
    rows=[]
    for i in range(19):
        is_open=i<open_count
        rows.append({
            "id":f"F{i}",
            "opus55_acceptance_state":"OPEN" if is_open else "PASS",
            "unresolved":["OPEN"] if is_open else [],
        })
    return {"expected_family_count":19,"actual_family_count":19,"families":rows}


def test_open_family_constructs_r3_counterexample():
    out=evaluate(claim_doc(),manifest(1))
    assert out["status"]=="CC_R3_COUNTEREXAMPLE_CURRENT_EPISTEMIC_ENVELOPE"
    assert out["u_empty"] is False
    assert out["cc_r3_proved"] is False


def test_all_pass_does_not_fabricate_u_empty_proof():
    out=evaluate(claim_doc(),manifest(0))
    assert out["status"]=="NO_R3_COUNTEREXAMPLE_FROM_FROZEN_ACCEPTANCE_STATES__U_EMPTY_NOT_PROVED"
    assert out["terminal_credit_delta"]==0


def test_claim_drift_fails_closed():
    doc=claim_doc()
    doc["claim"]["scope_sha256"]="4"*64
    out=evaluate(doc,manifest(1))
    assert out["status"]=="FAIL_CLOSED"


def test_family_universe_drift_fails_closed():
    m=manifest(1)
    m["actual_family_count"]=18
    out=evaluate(claim_doc(),m)
    assert out["status"]=="FAIL_CLOSED"

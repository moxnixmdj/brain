from canonical.runtime.predicate_selected_cover_complement_gate_v1 import evaluate, predicate_set_digest

SCOPE="scope://opus55/observable-trace"

def route(cell,route,pid,ch):
    pred=(ch*40)[:40]
    adeq=((str((int(ch,16)+1)%16))*40)[:40]
    snd=((str((int(ch,16)+2)%16))*40)[:40]
    return {
        "cell_id":cell,
        "route_id":route,
        "admission_predicate_id":pid,
        "admission_predicate_blob_sha":pred,
        "adequacy_certificate_blob_sha":adeq,
        "admission_soundness_receipt_blob_sha":snd,
        "admission_soundness_receipt":{
            "independent_verified":True,
            "exact_byte_bound":True,
            "conclusion":"success",
            "admission_implies_route_adequacy":True,
            "scope_id":SCOPE,
            "cell_id":cell,
            "route_id":route,
            "admission_predicate_id":pid,
            "admission_predicate_blob_sha":pred,
            "adequacy_certificate_blob_sha":adeq,
        },
    }

def payload():
    routes=[route("c1","r1","A1","1"),route("c2","r2","A2","4")]
    return {
        "scope_id":SCOPE,
        "routes":routes,
        "complement_coverage_receipt":{
            "receipt_id":"cover",
            "independent_verified":True,
            "exact_byte_bound":True,
            "conclusion":"success",
            "proof_kind":"FORMAL_UNSAT",
            "residual_complement_unsat":True,
            "scope_id":SCOPE,
            "predicate_set_sha256":predicate_set_digest(SCOPE,routes),
            "residual_definition":"S_TRACE_AND_NOT_ANY_SOUND_ADMISSION_PREDICATE",
        },
    }

def test_claimed_predicates_and_unsat_receipts_do_not_grant_authority():
    # The fixture uses fabricated Git SHAs and unsupported self-asserted proof flags.
    out=evaluate(payload())
    assert out["pass"] is False
    assert out["receipt_claim_shape_consistent"] is True
    assert out["independent_proof_replay_performed"] is False
    assert out["selected_cover_complete_authorized"] is False
    assert out["u_empty_authorized"] is False
    assert out["abc_closed_authorized"] is False
    assert out["terminal_credit_delta"] == 0
    assert out["d_finality_required"] is True
    assert out["terminal_authority"] is False

def test_missing_complement_proof_blocks_cover():
    p=payload()
    p["complement_coverage_receipt"]["residual_complement_unsat"]=False
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="RESIDUAL_COMPLEMENT_UNSAT_UNPROVED"

def test_stale_predicate_set_digest_blocks_cover():
    p=payload()
    p["complement_coverage_receipt"]["predicate_set_sha256"]="sha256:"+"0"*64
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="COMPLEMENT_PREDICATE_SET_DIGEST_MISMATCH"

def test_unsound_admission_row_blocks_global_closure():
    p=payload()
    p["routes"][0]["admission_soundness_receipt"]["admission_implies_route_adequacy"]=False
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="ADMISSION_SOUNDNESS_UNPROVED"

def test_scope_mismatch_blocks_cover():
    p=payload()
    p["routes"][1]["admission_soundness_receipt"]["scope_id"]="other"
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="ADMISSION_SOUNDNESS_SCOPE_MISMATCH"

def test_duplicate_predicate_id_fails_closed():
    p=payload()
    p["routes"][1]["admission_predicate_id"]="A1"
    p["routes"][1]["admission_soundness_receipt"]["admission_predicate_id"]="A1"
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="ADMISSION_PREDICATE_ID_DUPLICATE"


def test_self_asserted_receipt_flags_and_plausible_hashes_never_close_abc():
    p=payload()
    # Invented strings have the correct length; no Git object or theorem checked.
    p["routes"][0]["admission_predicate_blob_sha"]="a"*40
    p["routes"][0]["admission_soundness_receipt"]["admission_predicate_blob_sha"]="a"*40
    p["complement_coverage_receipt"]["predicate_set_sha256"]=predicate_set_digest(SCOPE,p["routes"])
    out=evaluate(p)
    assert out["receipt_claim_shape_consistent"] is True
    assert out["pass"] is False
    assert out["u_empty_authorized"] is False
    assert out["abc_closed_authorized"] is False
    assert out["reason"] == "INDEPENDENT_PROOF_REPLAY_NOT_PERFORMED"

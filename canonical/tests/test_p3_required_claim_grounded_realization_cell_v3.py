from canonical.runtime.p3_required_claim_grounded_realization_cell_v2 import evaluate as evaluate_v2
from canonical.runtime.p3_required_claim_grounded_realization_cell_v3 import evaluate as evaluate_v3


def _constraints():
    return {
        "output_format":"BULLETS",
        "citation_mode":"INLINE_SOURCE_IDS",
        "style":"VERBATIM_GROUNDED",
        "required_sections":[],
        "allowed_sections":None,
        "max_items":4,
        "max_chars":5000,
        "heading_level":2,
        "require_title":False,
    }


def _payload():
    return {"v3_input":{"schema":"PROJECT_BRAIN_SYNTHESIS_C2_INPUT_V1","task":{
        "claims":[{"claim_id":"C1","text":"Alice must verify report","required":True}],
        "evidence":[{
            "evidence_id":"E1",
            "text":"report must be verified by Alice",
            "verified":True,
            "provenance":[{"source_id":"REPORT","locator":"p1"}],
        }],
        "audience_profile":{"profile_id":"EXPLICIT","constraints":_constraints()},
        "required_uncertainty_units":[],
    }}}


def test_v3_closes_active_passive_case_that_v2_leaves_unknown():
    old=evaluate_v2(_payload())
    new=evaluate_v3(_payload())

    assert old["pass"] is False
    assert old["reason"]=="REQUIRED_CLAIM_SUPPORT_UNKNOWN"

    assert new["pass"] is True
    assert new["rendered_text"]=="- Alice must verify report [src:REPORT@p1]"
    receipt=new["support_receipts"][0]["receipt"]
    assert receipt["relation_audit"][0]["grammar"]=="PREDICATE_ARGUMENT_SUPPORT_V1"

    assert new["source_authorization_verified"] is False
    assert new["policy_adequacy_authority"] is False
    assert new["db_admission_authority"] is False
    assert new["u_subtraction_authority"] is False
    assert new["terminal_authority"] is False
    assert new["terminal_credit_delta"]==0

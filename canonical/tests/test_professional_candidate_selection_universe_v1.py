from copy import deepcopy
from canonical.runtime import professional_candidate_selection_universe_v1 as u

SUBJECT="FINAL-V6"
SUBJECT_SHA="a"*64
CTX="sha256:"+"b"*64

def payload():
    return {
        "behavior_id":u.BEHAVIOR_ID,
        "subject_id":SUBJECT,
        "subject_sha256":SUBJECT_SHA,
        "run_context_sha256":CTX,
        "incumbent_candidate_id":"inc",
        "candidates":[
            {
                "candidate_id":"inc",
                "content_sha256":"1"*64,
                "source_kind":"INCUMBENT",
                "artifact_type":"docx",
                "generator_trace_sha256":None,
            },
            {
                "candidate_id":"alt",
                "content_sha256":"2"*64,
                "source_kind":"GENERATED",
                "artifact_type":"docx",
                "generator_trace_sha256":"sha256:"+"3"*64,
            },
        ],
    }

def test_freeze_exact_finite_universe_without_generation_completeness():
    out=u.freeze(payload())
    assert out["pass"] is True,out
    assert out["candidate_count"]==2
    assert out["finite_selection_universe_complete_by_construction"] is True
    assert out["incumbent_preserved"] is True
    assert out["open_world_generation_complete"] is False
    assert out["policy_generation_complete"] is False
    assert out["selection_universe_authority"] is False
    assert out["quality_authority"] is False
    assert out["terminal_authority"] is False

def test_order_independent_manifest_digest():
    a=payload()
    b=payload()
    b["candidates"]=list(reversed(b["candidates"]))
    oa=u.freeze(a); ob=u.freeze(b)
    assert oa["pass"] and ob["pass"]
    assert oa["candidate_universe_sha256"]==ob["candidate_universe_sha256"]

def test_incumbent_must_be_real_manifest_member_and_marked_incumbent():
    p=payload()
    p["incumbent_candidate_id"]="missing"
    out=u.freeze(p)
    assert out["pass"] is False
    assert out["reason"]=="INCUMBENT_NOT_EXACTLY_ONE_MANIFEST_MEMBER"

    p=payload()
    p["candidates"][0]["source_kind"]="REUSED_VERIFIED"
    out=u.freeze(p)
    assert out["pass"] is False
    assert out["reason"]=="INCUMBENT_SOURCE_KIND_INVALID"

def test_generated_candidate_requires_bound_trace_digest():
    p=payload()
    p["candidates"][1]["generator_trace_sha256"]=None
    out=u.freeze(p)
    assert out["pass"] is False
    assert out["reason"]=="GENERATED_CANDIDATE_TRACE_SHA256_REQUIRED"

def test_duplicate_identity_or_content_fails_closed():
    p=payload()
    p["candidates"][1]["candidate_id"]="inc"
    assert u.freeze(p)["reason"]=="CANDIDATE_ID_INVALID_OR_DUPLICATE"

    p=payload()
    p["candidates"][1]["content_sha256"]="1"*64
    assert u.freeze(p)["reason"]=="CANDIDATE_CONTENT_SHA256_INVALID_OR_DUPLICATE"

def test_selection_cannot_escape_manifest():
    frozen=u.freeze(payload())
    good=u.select(frozen,"alt")
    assert good["pass"] is True
    assert good["selection_membership_verified"] is True
    assert good["policy_adequacy_authority"] is False

    bad=u.select(frozen,"outside")
    assert bad["pass"] is False
    assert bad["reason"]=="SELECTION_OUTSIDE_FROZEN_CANDIDATE_UNIVERSE"

def test_tampered_frozen_manifest_fails_closed():
    frozen=u.freeze(payload())
    broken=deepcopy(frozen)
    broken["manifest"]["candidates"][0]["content_sha256"]="f"*64
    out=u.select(broken,"inc")
    assert out["pass"] is False
    assert out["reason"]=="FROZEN_MANIFEST_DIGEST_MISMATCH"

def test_unknown_fields_fail_closed():
    p=payload()
    p["pretend_complete"]=True
    out=u.freeze(p)
    assert out["pass"] is False
    assert out["reason"]=="UNMODELED_FIELDS"

    p=payload()
    p["candidates"][0]["quality_score"]=999
    out=u.freeze(p)
    assert out["pass"] is False
    assert out["reason"]=="CANDIDATE_UNMODELED_FIELDS"

def test_forged_pass_object_is_revalidated_not_trusted():
    frozen=u.freeze(payload())
    forged=deepcopy(frozen)
    forged["manifest"]["candidates"][1]["generator_trace_sha256"]=None
    forged["candidate_universe_sha256"]=u._digest(forged["manifest"])
    out=u.validate_frozen(forged)
    assert out["pass"] is False
    assert out["reason"]=="FROZEN_MANIFEST_REVALIDATION_FAILED"
    assert out["revalidation_reason"]=="GENERATED_CANDIDATE_TRACE_SHA256_REQUIRED"

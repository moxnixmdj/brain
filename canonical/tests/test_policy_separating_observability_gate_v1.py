from canonical.runtime.policy_separating_observability_gate_v1 import evaluate

R={
    "path":"canonical/verification/PROOF.json",
    "git_blob_sha":"0"*40,
    "independent_verified":True,
    "exact_byte_bound":True,
    "conclusion":"success",
}
def rec(**claims):
    x=dict(R);x.update(claims);return x

def base():
    return {
        "states":[
            {
                "state_id":"s0",
                "policy_region_ids":["r0","r1"],
                "terminal":False,
                "discriminators":[
                    {
                        "discriminator_id":"d0",
                        "resource_cost_units":1,
                        "truth_soundness_receipt":rec(truthful_selected_discriminator=True),
                        "safety_receipt":rec(safe_on_entire_source_region_set=True),
                        "outcome_completeness_receipt":rec(finite_outcome_alphabet_complete=True),
                        "outcomes":[
                            {"outcome_id":"o0","successor_policy_region_ids":["r0"],"true_region_preserved":True},
                            {"outcome_id":"o1","successor_policy_region_ids":["r1"],"true_region_preserved":True},
                        ],
                    }
                ],
            },
            {
                "state_id":"s1",
                "policy_region_ids":["r0"],
                "terminal":True,
                "terminal_policy_id":"p0",
                "terminal_adequacy_receipt":rec(policy_adequate_on_entire_region_set=True),
                "terminal_safety_receipt":rec(policy_safe_on_entire_region_set=True),
            }
        ]
    }

def test_totality_passes_with_strict_separator_and_terminal():
    out=evaluate(base())
    assert out["pass"] is True
    assert out["declared_state_progress_totality"] is True
    assert out["uncovered_state_ids"]==[]

def test_no_separator_reports_exact_uncovered_state():
    p=base()
    p["states"][0]["discriminators"]=[]
    out=evaluate(p)
    assert out["pass"] is False
    assert out["uncovered_state_ids"]==["s0"]

def test_non_strict_outcome_does_not_count():
    p=base()
    p["states"][0]["discriminators"][0]["outcomes"][0]["successor_policy_region_ids"]=["r0","r1"]
    out=evaluate(p)
    assert out["pass"] is False
    assert out["uncovered_state_ids"]==["s0"]

def test_unverified_truth_receipt_does_not_count():
    p=base()
    p["states"][0]["discriminators"][0]["truth_soundness_receipt"]["independent_verified"]=False
    out=evaluate(p)
    assert out["pass"] is False
    assert out["uncovered_state_ids"]==["s0"]

def test_incomplete_outcome_receipt_does_not_count():
    p=base()
    p["states"][0]["discriminators"][0]["outcome_completeness_receipt"]["finite_outcome_alphabet_complete"]=False
    out=evaluate(p)
    assert out["pass"] is False
    assert out["uncovered_state_ids"]==["s0"]

def test_terminal_without_adequacy_fails_closed():
    p=base()
    p["states"][1]["terminal_adequacy_receipt"]["policy_adequate_on_entire_region_set"]=False
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="TERMINAL_ADEQUACY_UNPROVED"

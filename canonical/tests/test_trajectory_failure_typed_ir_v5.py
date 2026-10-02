import copy
from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as c
from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as p


def test_full_192_case_cross_product_and_intervention_rescue():
    cases=p.suite_cases()
    assert len(cases)==6*8*4
    seen_kinds=set()
    rescued=0
    ambiguous=0
    for case in cases:
        public=p.public_task(case)
        assert "_oracle" not in public
        out=c.solve(public)
        verdict=p.score_case(case,out)
        assert verdict["pass"], (case["seed"],case["_oracle"],out,verdict)
        for ks in case["_oracle"]["mechanisms"].values():
            seen_kinds.update(ks)
        if case["_oracle"]["status"]=="AMBIGUOUS":
            ambiguous+=1
            assert verdict["intervention_rescue_verified"] is False
        else:
            rescued+=1
            assert verdict["intervention_rescue_verified"] is True
            assert verdict["intervention"]["terminal_rescued"] is True
    assert seen_kinds==set(p.KINDS)
    assert rescued==6*8*3
    assert ambiguous==6*8


def test_scope_is_first_class_and_not_authority_alias():
    case=p.generate_case(3101,pattern="DELAYED",domain="TOOL_API",kind="SCOPE")
    out=c.solve(p.public_task(case))
    assert out["status"]=="IDENTIFIED"
    assert out["mechanism_classes"]==["SCOPE"]
    assert out["repair_targets"]==["restore:A1:SCOPE"]
    verdict=p.score_case(case,out)
    assert verdict["pass"], verdict
    assert verdict["intervention"]["terminal_rescued"] is True


def test_interaction_requires_both_repairs_for_rescue():
    case=p.generate_case(3102,pattern="INTERACTION",domain="RESEARCH",kind="SCOPE")
    out=c.solve(p.public_task(case))
    assert p.score_case(case,out)["pass"]
    attacked=copy.deepcopy(out)
    attacked["repair_targets"]=attacked["repair_targets"][:1]
    intervention=p.execute_intervention(p.public_task(case),attacked)
    assert intervention["terminal_rescued"] is False
    verdict=p.score_case(case,attacked)
    assert verdict["pass"] is False


def test_repair_label_alone_cannot_fake_rescue():
    case=p.generate_case(3103,pattern="DELAYED",domain="FILESYSTEM",kind="PROVENANCE")
    out=c.solve(p.public_task(case))
    attacked=copy.deepcopy(out)
    attacked["repair_targets"]=["restore:A999:PROVENANCE"]
    intervention=p.execute_intervention(p.public_task(case),attacked)
    assert intervention["terminal_rescued"] is False
    assert p.score_case(case,attacked)["pass"] is False


def test_derived_symptom_is_recomputed_after_root_repair():
    case=p.generate_case(3104,pattern="DELAYED",domain="CODE",kind="SCOPE")
    public=p.public_task(case)
    out=c.solve(public)
    intervention=p.execute_intervention(public,out)
    assert intervention["terminal_rescued"] is True
    assert intervention["active_direct_failures"]==[]
    assert intervention["active_derived_failures"]==[]


def test_ambiguous_case_refuses_forced_repair_and_rescue_claim():
    case=p.generate_case(3105,pattern="AMBIGUOUS",domain="BROWSER",kind="SCOPE")
    out=c.solve(p.public_task(case))
    assert out["status"]=="AMBIGUOUS"
    assert not out.get("repair_targets")
    verdict=p.score_case(case,out)
    assert verdict["pass"]
    assert verdict["intervention_rescue_verified"] is False


def test_hidden_oracle_mutation_does_not_change_candidate_input():
    case=p.generate_case(3106,pattern="SINGLE",domain="ARTIFACT",kind="SCOPE")
    before=p.public_task(case)
    case["_oracle"]["critical"]="A999"
    after=p.public_task(case)
    assert before==after

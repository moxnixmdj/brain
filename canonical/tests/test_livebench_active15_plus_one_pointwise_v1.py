from canonical.runtime.livebench_active15_plus_one_pointwise_v1 import (
    solve,
    minimum_hitting_set,
)

def c(iid, **slots):
    return {"instruction_id": iid, "slots": slots, "parameter_complete": True}

def test_minimum_hitting_set_handles_shared_edges_exactly():
    ids=["a","b","c"]
    edges=[frozenset({"a","b"}),frozenset({"a","c"})]
    assert minimum_hitting_set(ids, edges)==("a",)

def test_constrained_is_exact_singleton_candidate():
    out=solve([c("detectable_format:constrained_response")])
    assert out["status"]=="CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE"
    assert out["response"]=="My answer is yes."
    assert out["sacrificed_instruction_ids"]==[]

def test_repeat_comma_drops_one_checker_not_two():
    out=solve([
        c("combination:repeat_prompt", prompt_to_repeat="alpha, beta"),
        c("punctuation:no_comma"),
    ])
    assert out["status"]=="CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE"
    assert len(out["sacrificed_instruction_ids"])==1
    assert out["theoretical_max_pass_count_from_sound_loss_edges"]==1

def test_no_comma_transparent_on_two_response_route():
    out=solve([
        c("combination:two_responses"),
        c("punctuation:no_comma"),
    ])
    assert out["status"]=="CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE"
    assert "," not in out["response"]
    assert out["sacrificed_instruction_ids"]==[]

def test_uppercase_mixed_section_has_exact_one_loss():
    out=solve([
        c("detectable_format:multiple_sections", section_spliter="Section", num_sections=2),
        c("change_case:english_capital"),
    ])
    assert out["status"]=="CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE"
    assert len(out["sacrificed_instruction_ids"])==1
    assert out["theoretical_max_pass_count_from_sound_loss_edges"]==1

def test_lowercase_section_has_exact_one_loss():
    out=solve([
        c("detectable_format:multiple_sections", section_spliter="SECTION", num_sections=2),
        c("change_case:english_lowercase"),
    ])
    assert out["status"]=="CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE"
    assert len(out["sacrificed_instruction_ids"])==1

def test_uppercase_extension_only_constructs_cased_carrier():
    out=solve([c("change_case:english_capital")])
    assert out["status"]=="CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE"
    assert out["response"].isupper()

def test_lowercase_extension_only_constructs_cased_carrier():
    out=solve([c("change_case:english_lowercase")])
    assert out["status"]=="CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE"
    assert out["response"].islower()

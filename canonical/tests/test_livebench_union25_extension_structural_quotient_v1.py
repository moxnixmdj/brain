from canonical.runtime import livebench_union25_extension_structural_quotient_v1 as q


def test_union25_structural_counts_and_conflict_pairs():
    out = q.verify()
    assert out["scope"]["union25"] == 25
    assert out["scope"]["extension10_count"] == 10
    assert out["scope"]["conflict_pair_count"] == 97
    assert out["structural_universe"]["compatible_set_total"] == 14559
    assert out["structural_universe"]["by_cardinality"] == {
        "1": 25,
        "2": 203,
        "3": 1055,
        "4": 3750,
        "5": 9526,
    }


def test_extension_projection_has_exact_closed_form_157():
    out = q.verify()
    projection = out["extension_projection"]
    assert projection["exact_signature_count"] == 157
    cf = projection["closed_form"]
    assert cf["language_absent_signatures"] == 128
    assert cf["language_present_signatures"] == 32
    assert cf["graph_compatible_before_max_instruction_cap"] == 161
    assert cf["excluded_only_by_size_six"] == 4
    assert cf["admitted_extension_signatures"] == 157
    assert cf["formula"] == "4*2^5 + 2*2^4 + 1 - 4 = 157"


def test_special_branches_are_exactly_isolated():
    out = q.verify()["special_branch_isolation"]
    assert (out["CONSTRAINED"]["structural_set_count"], out["CONSTRAINED"]["extension_signature_count"]) == (1, 1)
    assert (out["JSON"]["structural_set_count"], out["JSON"]["extension_signature_count"]) == (4, 1)
    assert (out["REPEAT"]["structural_set_count"], out["REPEAT"]["extension_signature_count"]) == (8, 2)
    assert (out["TWO"]["structural_set_count"], out["TWO"]["extension_signature_count"]) == (20, 4)
    assert (out["GENERAL"]["structural_set_count"], out["GENERAL"]["extension_signature_count"]) == (14526, 156)


def test_no_credit_is_self_awarded():
    out = q.verify()
    assert out["acceptance_credit"] is False
    assert out["capability_credit"] is False
    assert out["ownership_credit"] is False
    assert out["terminal_rows_used"] is False

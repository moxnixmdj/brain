from canonical.runtime.l1_universal_abc_normal_form_verifier_v1 import verify,logical_collapse,FIXED13,OTHER2,STRUCTURAL4

ROWS=FIXED13|OTHER2|STRUCTURAL4

def test_current_normal_form_verifies():
    x=verify()
    assert x["pass"] is True,x
    assert x["current_row_count"]==19
    assert x["independent_l1_predicate_count"]==1
    assert x["independent_l1_predicates"]==["COMPLETE_SELECTED_CONTEXT_ABC"]
    assert x["D_remains_separate"] is True
    assert x["terminal_credit_delta"]==0

def test_missing_refinement_fails_closed():
    x=logical_collapse(rows=ROWS,refinements_of_u=ROWS-{"AUTOMATIONBENCH_GE_40"})
    assert x["pass"] is False
    assert "AUTOMATIONBENCH_GE_40" in x["reason"]

def test_independent_score_identity_reopens():
    x=logical_collapse(rows=ROWS,refinements_of_u=ROWS,independent_score_identities={"CODING_TB4_GE_66_4"})
    assert x["pass"] is False
    assert "INDEPENDENT_SCORE_IDENTITY_REOPENS" in x["reason"]

def test_all_rows_accounted_exactly():
    assert len(FIXED13)==13
    assert len(OTHER2)==2
    assert len(STRUCTURAL4)==4
    assert len(ROWS)==19

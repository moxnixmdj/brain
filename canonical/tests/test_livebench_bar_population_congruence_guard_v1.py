from canonical.runtime.livebench_bar_population_congruence_guard_v1 import adjudicate

def test_equal_counts_and_tasks_do_not_transfer_bar():
    out=adjudicate({
        "comparator_population_id":"official-2026",
        "subject_population_id":"public-proxy-0868379c",
        "same_counts":True,
        "same_task_labels":True,
    })
    assert out["status"]=="BLOCKED_POPULATION_CONGRUENCE_UNPROVED"
    assert out["threshold_transfer_authorized"] is False

def test_same_exact_population_authorizes_comparison():
    out=adjudicate({
        "comparator_population_id":"sha256:abc",
        "subject_population_id":"sha256:abc",
        "exact_population_identity_proved":True,
    })
    assert out["status"]=="PASS_SAME_POPULATION"
    assert out["threshold_transfer_authorized"] is True

def test_identity_claim_with_different_ids_fails_closed():
    out=adjudicate({
        "comparator_population_id":"sha256:a",
        "subject_population_id":"sha256:b",
        "exact_population_identity_proved":True,
    })
    assert out["status"]=="FAIL_CLOSED"

def test_proved_transfer_theorem_is_valid_escape():
    out=adjudicate({
        "comparator_population_id":"official",
        "subject_population_id":"proxy",
        "score_transfer_theorem_proved":True,
    })
    assert out["status"]=="PASS_PROVED_SCORE_TRANSFER"

def test_official_population_worst_case_theorem_is_valid_escape():
    out=adjudicate({"official_population_worst_case_bound_proved":True})
    assert out["status"]=="PASS_OFFICIAL_POPULATION_WORST_CASE_BOUND"

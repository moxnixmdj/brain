from canonical.runtime import tb_science_acceptance_progress_v1 as p
from canonical.runtime.tb_science_conservative_censoring_reducer_v1 import adjudicate

SLOTS=[f"slot-{i:03d}" for i in range(210)]

def records(successes, failures):
    return (
        [{"slot_id":SLOTS[i],"state":"SUCCESS"} for i in range(successes)]
        + [{"slot_id":SLOTS[successes+i],"state":"FAILURE"} for i in range(failures)]
    )

def test_frozen_constants_match_acceptance_contract():
    assert p.TOTAL_SLOTS==210
    assert p.REQUIRED_SUCCESSES==124
    assert p.FAIL_LOCK_FAILURES==87

def test_one_remaining_slot_is_decisive_both_ways():
    before=p.state(123,86)
    assert before["status"]=="OPEN"
    assert before["unresolved_slots"]==1
    success=p.finalize_one(123,86,"SUCCESS")
    failure=p.finalize_one(123,86,"FINAL_FAILURE")
    assert success["terminal"] is True
    assert success["after"]["status"]=="PASS_LOCK"
    assert failure["terminal"] is True
    assert failure["after"]["status"]=="FAIL_LOCK"

def test_current_eighteen_failure_shape_has_rank_192():
    current=p.state(0,18)
    assert current["status"]=="OPEN"
    assert current["unresolved_slots"]==192
    for outcome in ("SUCCESS","FINAL_FAILURE"):
        step=p.finalize_one(0,18,outcome)
        assert step["terminal"] is False
        assert step["strictly_decreases_measure"] is True
        assert step["after"]["unresolved_slots"]==191
        assert step["rank_delta"]==-1

def test_exhaustive_count_state_proof():
    out=p.prove_all_count_states()
    assert out["pass"] is True
    assert out["valid_count_states_checked"]==22366
    assert out["open_count_states_checked"]>0
    assert out["finalized_outcomes_checked"]==2*out["open_count_states_checked"]
    assert out["every_finalized_outcome_terminal_or_strictly_decreases"] is True
    assert out["current_action_executability_proved"] is False
    assert out["nonconsuming_preexposure_abort_counts_as_progress"] is False

def test_matches_canonical_reducer_on_representative_states():
    for successes,failures in [(0,0),(0,18),(123,0),(123,86),(124,0),(0,87),(100,50)]:
        ours=p.state(successes,failures)
        theirs=adjudicate(SLOTS,records(successes,failures))
        assert ours["status"]==theirs["status"]
        assert ours["unresolved_slots"]==theirs["pending"]

def test_terminal_parent_cannot_be_finalized_again():
    for successes,failures in [(124,0),(0,87)]:
        try:
            p.finalize_one(successes,failures,"SUCCESS")
        except p.ProgressStateError as exc:
            assert str(exc)=="FINALIZATION_REQUIRES_OPEN_PARENT_STATE"
        else:
            raise AssertionError("terminal state accepted a further finalization")

def test_invalid_or_nonfinal_outcomes_fail_closed():
    for args in [(-1,0),(0,-1),(200,11)]:
        try:
            p.state(*args)
        except p.ProgressStateError:
            pass
        else:
            raise AssertionError("invalid count state accepted")
    try:
        p.finalize_one(0,18,"PREEXPOSURE_ABORT")
    except p.ProgressStateError as exc:
        assert str(exc)=="FINALIZED_OUTCOME_INVALID"
    else:
        raise AssertionError("nonconsuming abort received progress credit")

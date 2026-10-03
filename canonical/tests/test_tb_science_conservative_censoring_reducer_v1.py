from canonical.runtime.tb_science_conservative_censoring_reducer_v1 import adjudicate

SLOTS=[f"task-{i:02d}::trial-{j}" for i in range(70) for j in range(3)]

def rows(n,state):
    return [{"slot_id":SLOTS[i],"state":state} for i in range(n)]

def test_pass_lock_at_124_successes():
    out=adjudicate(SLOTS,rows(124,"SUCCESS"))
    assert out["status"]=="PASS_LOCK"
    assert out["successes"]==124
    assert out["lower_bound_rate"] >= 0.587

def test_final_123_successes_fails():
    out=adjudicate(SLOTS,rows(123,"SUCCESS"),final=True)
    assert out["status"]=="FAIL_LOCK"
    assert out["lower_bound_rate"] < 0.587

def test_87_failures_lock_failure():
    out=adjudicate(SLOTS,rows(87,"FAILURE"))
    assert out["status"]=="FAIL_LOCK"

def test_resource_failures_never_create_positive_credit():
    out=adjudicate(SLOTS,rows(100,"RESOURCE_FAILURE"))
    assert out["successes"]==0
    assert out["lower_bound_rate"]==0

def test_duplicate_and_out_of_scope_records_fail_closed():
    try:
        adjudicate(SLOTS,[{"slot_id":SLOTS[0],"state":"SUCCESS"},{"slot_id":SLOTS[0],"state":"SUCCESS"}])
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate accepted")
    try:
        adjudicate(SLOTS,[{"slot_id":"outside-frozen-universe","state":"SUCCESS"}])
    except ValueError:
        pass
    else:
        raise AssertionError("foreign slot accepted")

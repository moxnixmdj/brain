from canonical.runtime.attainability_cut_compiler_v1 import evaluate

def current():
    return {"total_task_count":66,"trials_per_task":5,"required_successes":220,
            "hardware_incompatible_task_identities":[f"I{i}" for i in range(12)],
            "irreversibly_zero_hardware_compatible_tasks":[{"task_identity_sha256":f"Z{i}"} for i in range(18)],
            "completed_creditable_tasks":[]}

def test_current_route_is_impossible():
    out=evaluate(current())
    assert out["pass"]
    assert out["remaining_creditable_task_count"]==36
    assert out["upper_bound_successes"]==180
    assert out["attainability_state"]=="IMPOSSIBLE"
    assert out["reality_execution_authorized"] is False

def test_exact_threshold_stays_open():
    x=current()
    x["irreversibly_zero_hardware_compatible_tasks"]=[{"task_identity_sha256":f"Z{i}"} for i in range(10)]
    out=evaluate(x)
    assert out["upper_bound_successes"]==220
    assert out["attainability_state"]=="OPEN"

def test_lower_bound_can_prove():
    x=current()
    x["hardware_incompatible_task_identities"]=[]
    x["irreversibly_zero_hardware_compatible_tasks"]=[]
    x["completed_creditable_tasks"]=[{"task_identity_sha256":f"C{i}","successes":5} for i in range(44)]
    out=evaluate(x)
    assert out["lower_bound_successes"]==220
    assert out["attainability_state"]=="PROVED"

def test_overlap_fails_closed():
    x=current()
    x["hardware_incompatible_task_identities"]=["X"]
    x["irreversibly_zero_hardware_compatible_tasks"]=[{"task_identity_sha256":"X"}]
    out=evaluate(x)
    assert not out["pass"]
    assert out["reality_execution_authorized"] is False

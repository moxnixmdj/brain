import pytest

from canonical.runtime import continuity_root3_fixed_entry_v2 as entry
from canonical.runtime import same_identity_supervisor_credited_v1 as supervisor

def test_task_path_accepts_canonical_queue_json():
    p=entry._task_path("canonical/same_identity_worker/tasks/example.json")
    assert p == (entry.TASKS_DIR/"example.json").resolve()

@pytest.mark.parametrize("raw",[
    "canonical/same_identity_worker/state/example.json",
    "canonical/governance/example.json",
    "canonical/runtime/example.py",
    "../outside.json",
])
def test_task_path_rejects_non_task_queue(raw):
    with pytest.raises(supervisor.SupervisorError):
        entry._task_path(raw)

def test_task_path_rejects_non_json_inside_queue():
    with pytest.raises(supervisor.SupervisorError):
        entry._task_path("canonical/same_identity_worker/tasks/example.txt")

from canonical.runtime.terminal_authority_epoch_guard_v1 import admit, compute_epoch_id


BINDINGS = [
    {"path": "a", "git_blob_sha": "1"},
    {"path": "b", "git_blob_sha": "2"},
]


def test_epoch_deterministic():
    assert compute_epoch_id(BINDINGS) == compute_epoch_id(BINDINGS)


def test_epoch_changes_on_authority_change():
    changed = [
        {"path": "a", "git_blob_sha": "1"},
        {"path": "b", "git_blob_sha": "3"},
    ]
    assert compute_epoch_id(BINDINGS) != compute_epoch_id(changed)


def test_current_epoch_admitted():
    epoch = compute_epoch_id(BINDINGS)
    out = admit(epoch, epoch)
    assert out["admitted"] is True
    assert out["status"] == "PASS__CURRENT_EPOCH"


def test_stale_epoch_aborts():
    current = compute_epoch_id(BINDINGS)
    out = admit("stale", current)
    assert out["admitted"] is False
    assert out["status"] == "STALE_ABORT__EPOCH_MISMATCH"

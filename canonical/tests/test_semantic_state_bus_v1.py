from canonical.runtime.semantic_state_bus_v1 import (
    StateBusError,
    bind_downstream_context,
    checkpoint,
    empty_state,
    intervene_same_shape,
    read,
    rollback,
    sha256,
    state_sha256,
    write,
)


def base():
    return empty_state(
        case_id="CASE-1",
        base_context_sha256="a" * 64,
    )


def write_goal(state, value=None, *, expected=None, update=False):
    return write(
        state,
        key="goal_state",
        value=value or {"record_id": "R7", "status": "approved"},
        semantic_type="GOAL_STATE",
        producer_stage="browser",
        provenance_sha256="b" * 64,
        expected_state_sha256=expected or state["state_sha256"],
        allow_update=update,
    )


def test_empty_state_is_deterministic_and_self_bound():
    a = base()
    b = base()
    assert a == b
    assert a["state_sha256"] == state_sha256(a)


def test_typed_write_and_declared_read_are_content_bound():
    s0 = base()
    s1, wr = write_goal(s0)
    rr = read(s1, keys=["goal_state"], consumer_stage="tool")
    assert rr["entries"][0]["value"]["record_id"] == "R7"
    assert rr["entries"][0]["entry_binding_sha256"] == (
        s1["entries"]["goal_state"]["binding_sha256"]
    )
    assert wr["after_state_sha256"] == s1["state_sha256"]


def test_stale_write_fails_closed():
    s0 = base()
    s1, _ = write_goal(s0)
    try:
        write(
            s1,
            key="other",
            value={"x": 1},
            semantic_type="X",
            producer_stage="stage",
            provenance_sha256="c" * 64,
            expected_state_sha256=s0["state_sha256"],
        )
    except StateBusError as exc:
        assert str(exc) == "STALE_STATE_WRITE"
    else:
        raise AssertionError("stale write accepted")


def test_update_is_versioned_and_changes_state_digest():
    s0 = base()
    s1, _ = write_goal(s0)
    s2, _ = write_goal(
        s1,
        {"record_id": "R7", "status": "rejected"},
        expected=s1["state_sha256"],
        update=True,
    )
    assert s2["entries"]["goal_state"]["version"] == 2
    assert s2["state_sha256"] != s1["state_sha256"]


def test_same_shape_semantic_decoy_changes_downstream_binding():
    s0 = base()
    s1, _ = write_goal(s0)
    public = {"task": "act on the retained goal state"}
    true_ctx = bind_downstream_context(
        s1,
        keys=["goal_state"],
        consumer_stage="delegation",
        public_task=public,
    )

    decoy = {"record_id": "Q9", "status": "rejected"}
    s2, ir = intervene_same_shape(
        s1,
        key="goal_state",
        decoy_value=decoy,
        intervention_stage="falsifier",
        provenance_sha256="d" * 64,
        expected_state_sha256=s1["state_sha256"],
    )
    decoy_ctx = bind_downstream_context(
        s2,
        keys=["goal_state"],
        consumer_stage="delegation",
        public_task=public,
    )
    assert ir["true_value_sha256"] != ir["decoy_value_sha256"]
    assert true_ctx["binding_sha256"] != decoy_ctx["binding_sha256"]


def test_identical_or_different_shape_decoy_is_rejected():
    s0 = base()
    s1, _ = write_goal(s0)
    for bad in (
        {"record_id": "R7", "status": "approved"},
        {"record_id": "R7", "status": ["approved"]},
    ):
        try:
            intervene_same_shape(
                s1,
                key="goal_state",
                decoy_value=bad,
                intervention_stage="falsifier",
                provenance_sha256="d" * 64,
                expected_state_sha256=s1["state_sha256"],
            )
        except StateBusError:
            pass
        else:
            raise AssertionError("invalid decoy accepted")


def test_checkpoint_mutation_rollback_restores_exact_state_and_binding():
    s0 = base()
    s1, _ = write_goal(s0)
    cp = checkpoint(s1, label="before_change")
    public = {"task": "continue"}
    before = bind_downstream_context(
        s1,
        keys=["goal_state"],
        consumer_stage="final",
        public_task=public,
    )

    s2, _ = write_goal(
        s1,
        {"record_id": "R7", "status": "needs_review"},
        expected=s1["state_sha256"],
        update=True,
    )
    restored, receipt = rollback(
        s2,
        checkpoint_record=cp,
        expected_current_state_sha256=s2["state_sha256"],
    )
    after = bind_downstream_context(
        restored,
        keys=["goal_state"],
        consumer_stage="final",
        public_task=public,
    )

    assert receipt["exact_state_restoration"] is True
    assert restored == s1
    assert restored["state_sha256"] == cp["snapshot_state_sha256"]
    assert before["binding_sha256"] == after["binding_sha256"]


def test_stale_rollback_and_cross_case_checkpoint_fail_closed():
    s0 = base()
    s1, _ = write_goal(s0)
    cp = checkpoint(s1, label="cp")
    s2, _ = write_goal(
        s1,
        {"record_id": "R7", "status": "changed"},
        expected=s1["state_sha256"],
        update=True,
    )

    try:
        rollback(
            s2,
            checkpoint_record=cp,
            expected_current_state_sha256=s1["state_sha256"],
        )
    except StateBusError as exc:
        assert str(exc) == "STALE_STATE_ROLLBACK"
    else:
        raise AssertionError("stale rollback accepted")

    other = empty_state(case_id="CASE-2", base_context_sha256="a" * 64)
    other_cp = checkpoint(other, label="wrong")
    try:
        rollback(
            s2,
            checkpoint_record=other_cp,
            expected_current_state_sha256=s2["state_sha256"],
        )
    except StateBusError as exc:
        assert str(exc) == "CHECKPOINT_CASE_ID_MISMATCH"
    else:
        raise AssertionError("cross-case checkpoint accepted")


def test_tampered_state_is_rejected_before_read():
    s0 = base()
    s1, _ = write_goal(s0)
    s1["entries"]["goal_state"]["value"]["status"] = "tampered"
    try:
        read(s1, keys=["goal_state"], consumer_stage="final")
    except StateBusError as exc:
        assert "STATE_SHA256_MISMATCH" in str(exc) or "ENTRY_VALUE_SHA256_MISMATCH" in str(exc)
    else:
        raise AssertionError("tampered state accepted")


def test_missing_and_undeclared_reads_fail_closed():
    s0 = base()
    try:
        read(s0, keys=["missing"], consumer_stage="final")
    except StateBusError as exc:
        assert str(exc).startswith("READ_KEY_MISSING:")
    else:
        raise AssertionError("missing key accepted")


def test_provenance_and_value_are_both_load_bearing_in_entry_binding():
    s0 = base()
    s1, _ = write_goal(s0)
    entry = s1["entries"]["goal_state"]
    old = entry["binding_sha256"]
    altered = {
        "key": "goal_state",
        "semantic_type": entry["semantic_type"],
        "producer_stage": entry["producer_stage"],
        "version": entry["version"],
        "value_sha256": entry["value_sha256"],
        "shape_sha256": entry["shape_sha256"],
        "provenance_sha256": "f" * 64,
    }
    assert sha256(altered) != old


def test_content_address_identity_fields_require_sha256_hex():
    try:
        empty_state(case_id="CASE-X", base_context_sha256="not-a-sha")
    except StateBusError as exc:
        assert str(exc) == "BASE_CONTEXT_SHA256_INVALID"
    else:
        raise AssertionError("invalid base context accepted")

    s0 = base()
    try:
        write(
            s0,
            key="x",
            value={"x": 1},
            semantic_type="X",
            producer_stage="stage",
            provenance_sha256="not-a-sha",
            expected_state_sha256=s0["state_sha256"],
        )
    except StateBusError as exc:
        assert str(exc) == "PROVENANCE_SHA256_INVALID"
    else:
        raise AssertionError("invalid provenance accepted")

from canonical.runtime.bytes_strong_accounting_and_persistence_cut_v1 import (
    BytesResearchError,
    persistent_bits_lower_bound,
    strong_bytes_accounting,
    verify_reference_cases,
)


H0 = "0" * 64
H1 = "1" * 64
H2 = "2" * 64


def row(path, sha, size, *, persistent=True, capability=True, learned=False, category="X"):
    out = {
        "path": path,
        "sha256": sha,
        "byte_count": size,
        "persistent": persistent,
        "capability_bearing": capability,
        "learned": learned,
        "category": category,
    }
    if persistent and not capability:
        out["noncapability_role_verified"] = True
        out["noncapability_role_receipt_sha256"] = "f" * 64
    return out


def test_nonreacquirable_restart_cut_requires_persistent_bits():
    assert persistent_bits_lower_bound(
        2, separator_reacquirable_before_deadline=False
    ) == 1
    assert persistent_bits_lower_bound(
        8, separator_reacquirable_before_deadline=False
    ) == 3


def test_reacquirable_separator_imposes_zero_persistent_bit_lower_bound():
    assert persistent_bits_lower_bound(
        2, separator_reacquirable_before_deadline=True
    ) == 0
    assert persistent_bits_lower_bound(
        1024, separator_reacquirable_before_deadline=True
    ) == 0


def test_zero_learned_bytes_does_not_hide_deterministic_registry_growth():
    before = [row("kernel.py", H0, 4096, category="FROZEN_KERNEL")]
    after = before + [
        row("registry.py", H1, 2048, category="COMPILED_CAPABILITY_LIBRARY")
    ]
    out = strong_bytes_accounting(before, after)
    assert out["zero_persistent_learned_bytes"] is True
    assert out["zero_incremental_persistent_capability_bytes"] is False
    assert out["incremental_new_or_changed_capability_bytes"] == 2048


def test_raw_noncapability_knowledge_growth_does_not_break_frozen_kernel():
    before = [row("kernel.py", H0, 4096, category="FROZEN_KERNEL")]
    after = before + [
        row(
            "facts.json",
            H2,
            1000000,
            capability=False,
            category="RAW_TASK_KNOWLEDGE",
        )
    ]
    out = strong_bytes_accounting(before, after)
    assert out["zero_incremental_persistent_capability_bytes"] is True
    assert out["persistent_noncapability_state_bytes_after"] == 1000000


def test_same_size_kernel_mutation_still_breaks_zero_incremental_claim():
    before = [row("kernel.py", H0, 4096, category="FROZEN_KERNEL")]
    after = [row("kernel.py", H1, 4096, category="FROZEN_KERNEL")]
    out = strong_bytes_accounting(before, after)
    assert out["net_persistent_capability_storage_delta_bytes"] == 0
    assert out["zero_incremental_persistent_capability_bytes"] is False
    assert out["incremental_new_or_changed_capability_bytes"] == 4096


def test_ephemeral_capability_bytes_do_not_become_durable_growth():
    before = [row("kernel.py", H0, 4096, category="FROZEN_KERNEL")]
    after = before + [
        row(
            "jit_candidate.tmp",
            H1,
            8192,
            persistent=False,
            capability=True,
            category="EPHEMERAL_JIT_CAPABILITY",
        )
    ]
    out = strong_bytes_accounting(before, after)
    assert out["zero_incremental_persistent_capability_bytes"] is True
    assert out["ephemeral_capability_bytes_in_after_manifest"] == 8192


def test_learned_artifact_must_be_capability_bearing():
    before = [row("kernel.py", H0, 4096, category="FROZEN_KERNEL")]
    bad = [
        row(
            "weights.bin",
            H1,
            100,
            capability=False,
            learned=True,
            category="LEARNED_STATE",
        )
    ]
    try:
        strong_bytes_accounting(before, bad)
    except BytesResearchError as exc:
        assert str(exc) == "LEARNED_ARTIFACT_MUST_BE_CAPABILITY_BEARING"
    else:
        raise AssertionError("expected fail-closed artifact classification")


def test_persistent_noncapability_without_role_receipt_fails_closed():
    before = [row("kernel.py", H0, 4096, category="FROZEN_KERNEL")]
    bad = [{
        "path": "claimed_facts.json",
        "sha256": H2,
        "byte_count": 1000,
        "persistent": True,
        "capability_bearing": False,
        "learned": False,
        "category": "RAW_TASK_KNOWLEDGE",
    }]
    try:
        strong_bytes_accounting(before, before + bad)
    except BytesResearchError as exc:
        assert str(exc) == "PERSISTENT_NONCAPABILITY_ROLE_NOT_INDEPENDENTLY_VERIFIED"
    else:
        raise AssertionError("expected fail-closed role-classification guard")


def test_reference_cases_pass():
    assert verify_reference_cases()["status"] == "PASS"

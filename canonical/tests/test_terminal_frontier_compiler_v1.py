from __future__ import annotations

from canonical.runtime.terminal_frontier_compiler_v1 import (
    compile_frontier,
    frontier_epoch,
    root_partition,
    terminal_finality,
)


def test_current_frontier_compiles_without_static_scheduler_counts():
    out = compile_frontier()
    assert out["acceptance"]["proved_atomic"] == 14
    assert out["acceptance"]["unresolved_atomic"] == 24
    assert out["root2_touching_count"] == 18
    assert out["root3_touching_count"] == 9
    assert out["root1_positive_gap_count"] == 0
    assert out["meta_envelope"]["active_version"] >= 5
    assert out["meta_envelope"]["open_count"] >= 1
    assert out["terminal"] is False


def test_current_v5_meta_envelope_is_first_class_finality_input():
    out = compile_frontier()
    assert "ROOT1_TERMINAL_FAMILY_ENVELOPE_AUDIT" in out["meta_envelope"]["activation_path"]
    assert out["meta_envelope"]["family_mappings"]
    assert out["meta_envelope"]["cross_cutting_conditions"]


def test_meta_obligation_blocks_false_38_of_38_finality():
    acceptance = {
        "accepted_families": 19,
        "total_families": 19,
        "proved_atomic": 38,
        "total_atomic": 38,
        "unresolved_atomic": 0,
    }
    assert terminal_finality(
        acceptance, root1_positive_gap_count=0, meta_open_count=1
    ) is False
    assert terminal_finality(
        acceptance, root1_positive_gap_count=0, meta_open_count=0
    ) is True


def test_root_partition_mixed_predicates_count_on_both_sides():
    part = {
        "unresolved_total": 4,
        "root2_only_count": 1,
        "root3_only_count": 1,
        "root2_and_root3_count": 2,
        "root2_only": ["a"],
        "root3_only": ["b"],
        "root2_and_root3": ["c", "d"],
    }
    r2, r3 = root_partition(part)
    assert r2 == {"a", "c", "d"}
    assert r3 == {"b", "c", "d"}


def test_frontier_epoch_changes_on_any_bound_component():
    a = {"x": "1" * 40, "y": "2" * 40}
    b = dict(a)
    b["y"] = "3" * 40
    assert frontier_epoch(a) != frontier_epoch(b)

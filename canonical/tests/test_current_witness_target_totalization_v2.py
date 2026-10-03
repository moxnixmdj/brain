from __future__ import annotations

import copy
import json
from pathlib import Path

from canonical.runtime.current_witness_target_totalization_v2 import (
    ROOT,
    TARGETS,
    TARGET_VERIFY,
    WITNESSES,
    WITNESS_VERIFY,
    git_blob_sha,
    totalize,
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(target=None, target_verify=None, witnesses=None, witness_verify=None):
    return totalize(
        target if target is not None else load(TARGETS),
        target_verify if target_verify is not None else load(TARGET_VERIFY),
        witnesses if witnesses is not None else load(WITNESSES),
        witness_verify if witness_verify is not None else load(WITNESS_VERIFY),
        target_blob_sha=git_blob_sha(TARGETS),
        witness_blob_sha=git_blob_sha(WITNESSES),
    )


def test_current_surface_is_exact_and_zero_direct_reuse():
    out = run()
    assert out["pass"] is True
    assert out["target_count"] == 8
    assert out["witness_count"] == 12
    assert out["pair_count"] == 96
    assert out["target_atom_occurrence_count"] == 37
    assert out["target_metric_occurrence_count"] == 7
    assert out["positive_atom_binding_count"] == 0
    assert out["positive_metric_binding_count"] == 0
    assert out["positive_semantic_edge_count"] == 0
    assert out["closed_target_count"] == 0
    assert out["residual_target_count"] == 8


def test_invented_positive_semantics_fail_closed():
    witnesses = load(WITNESSES)
    mutated = copy.deepcopy(witnesses)
    mutated["witnesses"][0]["normalized_target_atoms"] = [
        "dimension:multi_step_planning_with_at_least_three_distinct_tool_or_action_types"
    ]
    out = run(witnesses=mutated)
    assert out["pass"] is False
    assert "POSITIVE_ATOM_BINDING_PRESENT" in out["errors"]


def test_unverified_target_normalization_fails_closed():
    verify = load(TARGET_VERIFY)
    mutated = copy.deepcopy(verify)
    mutated["verified"]["current_live_target_set_exact"] = False
    out = run(target_verify=mutated)
    assert out["pass"] is False
    assert "TARGET_SET_NOT_INDEPENDENTLY_VERIFIED_EXACT" in out["errors"]


def test_unverified_witness_catalog_fails_closed():
    verify = load(WITNESS_VERIFY)
    mutated = copy.deepcopy(verify)
    mutated["verified"]["exact_all_and_only_proved_claims"] = False
    out = run(witness_verify=mutated)
    assert out["pass"] is False
    assert "WITNESS_SET_NOT_INDEPENDENTLY_VERIFIED_EXACT" in out["errors"]

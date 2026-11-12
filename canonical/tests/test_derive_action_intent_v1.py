"""The intent record's mechanical fields come from git, not from memory.

Round 11's four guard failures were one class: a field that no human should have been typing.
This pins the derivation:

  * the lease key is the same concatenation the guard computes;
  * the two recursive-observation fields the guard compares by equality are forced equal to the
    intent fields they are compared against, so they cannot drift apart;
  * the base commit is the resolved sha, not the ref string (which is how a "stale base" happens);
  * the pointer blob is read from git at the base, not copied from an older record;
  * drift() names a stale field precisely, and returns nothing for a freshly bound record.

Nothing here weakens a check. The guard still decides; this only fills the form.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from derive_action_intent_20261112 import (  # noqa: E402
    POINTER,
    SEMANTIC_FIELDS,
    bind,
    blob_at,
    build,
    drift,
    evidence_paths,
    git,
    lease_key,
)

SPEC = {
    "action_id": "TEST_INTENT_FOR_THE_DERIVER_V1",
    "action_kind": "RECONCILE_FRONTIER",
    "date": "2026-11-12",
    "action_summary": "test",
    "causal_blocker": "A_BLOCKER",
    "selected_route": "A_ROUTE",
    "expected_parent_change": "A_CHANGE",
    "expected_parent_frontier_change": "A_FRONTIER_CHANGE",
    "stop_condition": "A_STOP",
    "falsification_condition": "A_FALSIFIER",
    "measured_effect": "AN_EFFECT",
}


def _base() -> str:
    return git("rev-parse", "origin/main")


def test_the_lease_key_is_the_guards_own_concatenation():
    intent = {"canonical_generation": "gen", "capability_target": "target", "causal_blocker": "block"}
    assert lease_key(intent) == "gen::target::block"
    # The guard builds it from exactly these three fields, so an empty one must still concatenate.
    assert lease_key({"canonical_generation": "g"}) == "g::::"


def test_the_cross_checked_observation_fields_cannot_disagree():
    intent = {
        "canonical_generation": "gen",
        "capability_target": "target",
        "causal_blocker": "block",
        "stop_condition": "STOP_NOW",
        "expected_parent_frontier_change": "FRONTIER_NOW",
        "recursive_obs": {
            "canonical_base_commit": "0" * 40,
            "stop_condition": "SOMETHING_ELSE",
            "expected_parent_level_state_change": "SOMETHING_ELSE_TOO",
        },
    }
    bound = bind(intent, _base())
    assert bound["recursive_obs"]["stop_condition"] == "STOP_NOW"
    assert bound["recursive_obs"]["expected_parent_level_state_change"] == "FRONTIER_NOW"


def test_the_base_commit_is_a_resolved_sha_not_a_ref():
    bound = bind({"canonical_generation": "gen", "capability_target": "t", "causal_blocker": "b"},
                 "origin/main")
    sha = bound["canonical_base_commit"]
    assert len(sha) == 40 and all(c in "0123456789abcdef" for c in sha)
    assert sha == git("rev-parse", "origin/main")
    assert bound["recursive_obs"]["canonical_base_commit"] == sha


def test_the_pointer_blob_is_read_from_git_at_the_base():
    bound = bind(
        {
            "canonical_generation": "gen",
            "capability_target": "t",
            "causal_blocker": "b",
            "v22_prewrite_admission": {"active_pointer_git_blob_sha": "0" * 40},
        },
        "origin/main",
    )
    assert bound["v22_prewrite_admission"]["active_pointer_git_blob_sha"] == blob_at("origin/main", POINTER)


def test_a_stale_base_is_named_precisely():
    bound = bind({"canonical_generation": "gen", "capability_target": "t", "causal_blocker": "b"},
                 "origin/main")
    stale = json.loads(json.dumps(bound))
    stale["canonical_base_commit"] = "0" * 40
    found = {row["field"] for row in drift(stale, "origin/main")}
    assert "canonical_base_commit" in found
    assert "recursive_obs.canonical_base_commit" not in found, (
        "a stale top-level base is one defect, not two"
    )


def test_a_freshly_bound_record_has_no_drift():
    bound = bind(
        {
            "canonical_generation": "gen",
            "capability_target": "t",
            "causal_blocker": "b",
            "stop_condition": "S",
            "expected_parent_frontier_change": "F",
        },
        "origin/main",
    )
    assert drift(bound, "origin/main") == []


def test_build_refuses_a_spec_without_meaning():
    for field in SEMANTIC_FIELDS:
        partial = dict(SPEC)
        partial.pop(field)
        try:
            build(partial, "origin/main")
        except SystemExit as exc:
            assert "SPEC_MISSING" in str(exc), str(exc)
            continue
        raise AssertionError("a spec missing %r was accepted" % field)


def test_build_names_the_record_three_times_consistently():
    intent = build(dict(SPEC), "origin/main")
    assert intent["action_id"] == intent["action_intent_id"] == intent["route_id"]
    assert intent["action_id"] == SPEC["action_id"]
    assert intent["causal_blocker"] == SPEC["causal_blocker"]


def test_evidence_paths_keeps_probes_and_tests_only():
    files = ["gate_accepts_a_failed_repair_probe_20261112.py",
             "canonical/tests/test_gate_accepts_a_failed_repair_v1.py",
             "canonical/runtime/thing.py",
             "SOME_NOTE_20261112_V1.md"]
    assert evidence_paths(files) == [
        "canonical/tests/test_gate_accepts_a_failed_repair_v1.py",
        "gate_accepts_a_failed_repair_probe_20261112.py",
    ]


def test_a_blob_sha_is_the_one_git_reports():
    path = "derive_action_intent_20261112.py"
    expected = subprocess.check_output(["git", "rev-parse", "HEAD:%s" % path],
                                       cwd=ROOT, text=True).strip()
    assert blob_at("HEAD", path) == expected
    assert blob_at("HEAD", "no/such/file.py") is None

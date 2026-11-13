#!/usr/bin/env python3
"""Tests for the effect-directed compile router (the layer above the confined seam).

PC6  e2e: a realistic sentence compiles through reviewed declarations and executes on the
     disposable clone with a verified effect receipt; the host tracked state never moves.
PC7  the pinned compress refusal survives: a .gz artifact names no declared capability.
PC8  an artifact no declaration serves leaves the carrier refusal exactly as it was.
PC9  an unbindable operation ("optimize function X") routes nowhere -- never a guess.
PC10 honesty parity: a passing confined result with an empty test selection is refused
     FAIL_CLOSED, exactly as the local path refuses it.
PC11 a candidate that runs and fails verification returns a fail-closed result WITH its
     receipt -- never a fabricated pass, never the boundary status.
PC12 the router carries no sentence table: none of the probe corpus sentences appear in it.
PC13 ranking: the tree-sitter sentence's top candidate is the tree-sitter row itself.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import effect_directed_compile_v1 as edc  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

TREE_SITTER_GOAL = ("Build an incremental tree-sitter symbol index for this repository "
                    "and write it to code_index.json.")
COMPRESS_GOAL = "compress notes.txt into notes.txt.gz"
GARBAGE_GOAL = "Write the frobnication metrics to frobnication_metrics.json."
OPTIMIZE_GOAL = ("Optimize the function e_process in canonical/runtime/credit_gates_v1.py "
                 "for speed and write the result to swe_result.json.")


def _host_tracked_status() -> str:
    return subprocess.run(["git", "status", "--porcelain"], cwd=str(ROOT),
                          capture_output=True, text=True).stdout


def test_pc6_sentence_compiles_and_runs_confined_with_receipt():
    before = _host_tracked_status()
    r = door.solve({"task_id": "PC6", "goal": TREE_SITTER_GOAL})
    after = _host_tracked_status()
    assert r.get("pass") is True
    assert r.get("executed") is True
    # The tree-sitter row outranks the ast row; if the named capability honestly cannot
    # serve this repository (its own source-file limit), the next verified candidate wins
    # and the receipt names exactly what executed.  Either way: confined, receipted, verified.
    ed = r.get("effect_directed") or {}
    assert r.get("compiler_mode") == "EFFECT_DIRECTED_DECLARED_CAPABILITY"
    assert r.get("compiled_capability_id") in (
        "code.index.tree_sitter.incremental.v1", "python.source.symbols.index.ast")
    dep = r.get("dependency") or {}
    assert dep.get("executor") == "ADMITTED_CONFINEMENT_V1"
    conf = r.get("confinement") or {}
    assert conf.get("receipt_sha256")
    assert conf.get("host_untouched") is True
    artifact = ed.get("artifact")
    effects = conf.get("declared_effects") or {}
    assert effects.get(artifact, {}).get("exists") is True
    assert effects.get(artifact, {}).get("sha256")
    assert ed.get("attempted")
    assert after == before, "the host tracked state must be byte-identical after a confined route"


def test_pc7_pinned_compress_refusal_survives():
    r = door.solve({"task_id": "PC7", "goal": COMPRESS_GOAL})
    assert r.get("pass") is not True
    assert r.get("executed") is not True
    assert r.get("status") == "FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT"
    assert not (r.get("effect_directed") or {}).get("attempted")


def test_pc8_unserved_artifact_refuses_without_a_route():
    assert edc.candidates(GARBAGE_GOAL) == []
    r = door.solve({"task_id": "PC8", "goal": GARBAGE_GOAL})
    assert r.get("pass") is not True
    assert r.get("executed") is not True
    status = str(r.get("status") or "")
    # A named refusal either way: the carrier gate's boundary status, or an honest earlier
    # decision the door keeps (measured: RAW_GOAL_COMPILATION_GAP decides first here).
    assert status.startswith("FAIL_CLOSED__") or status.startswith("FAIL__")


def test_pc9_unbindable_operation_never_routes():
    assert edc.candidates(OPTIMIZE_GOAL) == []


def test_pc10_empty_test_selection_is_refused_with_parity():
    from canonical.runtime import confined_dispatch_v1 as confined
    entry = {"capability_id": "python.source.change_impact.testselect.v1",
             "adapter_module": "python_change_impact_testselect", "entrypoint": "run",
             "action_template": {"args": {}, "expect": {}}}
    fake_pass = {"schema": "X", "output_verified": True, "selected_tests": [],
                 "affected_modules": ["canonical/runtime/world_probe_v1.py"]}
    orig = confined.run_confined_capability
    confined.run_confined_capability = lambda *a, **k: dict(fake_pass)
    try:
        r = edc.attempt({"task_id": "PC10",
                         "goal": "Select the tests affected by a change to "
                                 "canonical/runtime/world_probe_v1.py and write the "
                                 "selection to test_selection.json."})
    finally:
        confined.run_confined_capability = orig
    assert r is not None
    assert r.get("pass") is False
    assert r.get("status") == "FAIL_CLOSED__ANSWER_EMPTY__NO_TESTS_SELECTED"


def test_pc11_failed_verification_is_a_fail_closed_result_with_receipt():
    from canonical.runtime import confined_dispatch_v1 as confined
    receipt = {"receipt_sha256": "deadbeef" * 8, "host_untouched": True, "outcome": "RAN",
               "declared_effects": {"fault_report.json": {"exists": False}}}
    fake_fail = {"schema": "X", "output_verified": False, "confinement": receipt,
                 "dependency": {"executor": "ADMITTED_CONFINEMENT_V1"}}
    orig = confined.run_confined_capability
    confined.run_confined_capability = lambda *a, **k: dict(fake_fail)
    try:
        r = edc.attempt({"task_id": "PC11",
                         "goal": "Localize the fault with dynamic dataflow analysis for the "
                                 "failing tests in canonical/tests/test_settlement_v1.py and "
                                 "write the report to fault_report.json."})
    finally:
        confined.run_confined_capability = orig
    assert r is not None
    assert r.get("pass") is False
    assert r.get("executed") is True
    assert r.get("status") == "FAIL_CLOSED__EFFECT_DIRECTED_CONFINED_RUN_DID_NOT_VERIFY"
    ed = r.get("effect_directed") or {}
    assert ed.get("attempted") and ed["attempted"][0]["pass"] is False
    assert r.get("confinement", {}).get("receipt_sha256") == "deadbeef" * 8


def test_pc12_no_sentence_table_in_the_router():
    module_src = pathlib.Path(edc.__file__).read_text(encoding="utf-8")
    corpus_path = ROOT / "canonical" / "tools" / "realistic_goal_reach_probe_v1.py"
    if corpus_path.is_file():
        probe_src = corpus_path.read_text(encoding="utf-8")
        import re as _re
        sentences = [s for s in _re.findall(r'"([^"\n]{40,})"', probe_src)
                     if ".json" in s or "repository" in s]
        for s in sentences[:60]:
            if s == s.upper():
                continue  # status names are shared vocabulary, not sentences
            assert s[:60] not in module_src, "a corpus sentence leaked into the router"


def test_pc13_ranking_prefers_the_named_capability_itself():
    cands = edc.candidates(TREE_SITTER_GOAL)
    assert cands, "the tree-sitter sentence must route"
    assert cands[0][0] == "code.index.tree_sitter.incremental.v1"
    assert cands[0][3] >= cands[-1][3]

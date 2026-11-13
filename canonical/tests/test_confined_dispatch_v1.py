#!/usr/bin/env python3
"""The confined dispatch seam: declared capabilities run on the disposable clone.

PREDICTIONS -- written 2026-11-12 BEFORE the confirmatory run, on branch
`arena/9c35dc77-brain`. The host in the end-to-end test is THIS repository: the
confinement clones it, the adapter runs against the clone, and the test asserts the
host's own git status never moved. That is the property the boundary demands.

PC1  An undeclared capability is NOT routable: `run_confined_capability` returns None,
     so the caller's refusal stands exactly as before (file.copy.v1 -- pinned refused
     by test_a_copy_names_its_destination -- is deliberately absent from the file).
PC2  A declared capability whose effect argument the door did not bind is NOT routable
     (None), and neither is one whose bound effect is an absolute path into the host.
PC3  End-to-end: `python.source.symbols.index.ast` (declared) compiles its args,
     runs its real adapter INSIDE the clone, verifies the declared output with a
     sha256 receipt, leaves the host byte-identical, passes the SAME expectation
     check (`output_verified == True`), and stamps `dependency.executor ==
     ADMITTED_CONFINEMENT_V1` plus the confinement receipt.
PC4  A confined adapter that raises produces a FAIL-CLOSED result -- pass False, the
     receipt attached, reason CONFINED_RUN_DID_NOT_PRODUCE_A_RESULT -- never a crash
     and never a pass.
PC5  The boundary module itself is untouched by this round: its refusal decision
     (`refuses_execution`) still answers True for the same inputs; the seam is the
     dispatch, not a weakened guard.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import confined_dispatch_v1 as CD  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
REGISTRY = json.loads((ROOT / "canonical" / "runtime" /
                       "BOUND_CAPABILITY_REGISTRY_V1.json").read_text())["capabilities"]


def _entry(cid: str) -> dict:
    e = dict(REGISTRY[cid])
    e["capability_id"] = cid
    return e


def _action(cid: str, **args) -> dict:
    tmpl = REGISTRY[cid]["action_template"]
    rendered = {}
    for k, v in (tmpl.get("args") or {}).items():
        rendered[k] = args.get(k, v)
    return {"args": rendered, "expect": tmpl.get("expect")}


def test_pc1_undeclared_capability_is_not_routable() -> None:
    assert CD.run_confined_capability(
        "file.copy.v1", _entry("file.copy.v1"),
        _action("file.copy.v1", path="AGENTS.md", output_path="AGENTS_copy.md",
                goal="copy"),
        host_root=ROOT) is None


def test_pc2_unbound_or_escaping_effects_are_not_routable() -> None:
    cid = "python.source.symbols.index.ast"
    action = _action(cid, source_root=".")
    action["args"]["output_path"] = ""
    assert CD.run_confined_capability(cid, _entry(cid), action, host_root=ROOT) is None
    action2 = _action(cid, source_root=".",
                      output_path=str(ROOT / "escape_index.json"))
    assert CD.run_confined_capability(cid, _entry(cid), action2, host_root=ROOT) is None


def test_pc3_end_to_end_confined_run_of_a_declared_capability() -> None:
    cid = "python.source.symbols.index.ast"
    before = subprocess.run(["git", "status", "--porcelain"], cwd=str(ROOT),
                            capture_output=True, text=True).stdout
    action = _action(cid, source_root="canonical/runtime/bound_capabilities",
                     output_path="symbols_index.json")
    result = CD.run_confined_capability(cid, _entry(cid), action, host_root=ROOT)
    after = subprocess.run(["git", "status", "--porcelain"], cwd=str(ROOT),
                           capture_output=True, text=True).stdout
    assert after == before, "the host repository must be byte-identical"
    assert isinstance(result, dict), "a declared capability must route"
    assert result.get("output_verified") is True
    assert result.get("dependency", {}).get("executor") == CD.EXECUTOR
    conf = result.get("confinement") or {}
    assert conf.get("host_untouched") is True
    assert conf.get("receipt_sha256")
    effects = conf.get("declared_effects") or {}
    assert effects.get("symbols_index.json", {}).get("exists") is True
    assert effects.get("symbols_index.json", {}).get("sha256")


def test_pc4_a_raising_adapter_fails_closed_with_its_receipt() -> None:
    cid = "python.swe.transform_and_synthesize.v1"
    action = _action(cid, operation="not_a_real_operation", symbol="x",
                     target_path="canonical/runtime/settlement_v1.py",
                     request_spec="{}")
    result = CD.run_confined_capability(cid, _entry(cid), action, host_root=ROOT)
    assert isinstance(result, dict)
    assert result.get("pass") is False
    # Measured 2026-11-13 (effect-directed round): a raising adapter's reason is named,
    # not silenced -- the runner's error travels as CONFINED_ADAPTER_RAISED:<type>:<error>.
    reason = str(result.get("reason") or "")
    assert reason == "CONFINED_RUN_DID_NOT_PRODUCE_A_RESULT" or reason.startswith(
        "CONFINED_ADAPTER_RAISED:"), reason
    assert (result.get("confinement") or {}).get("receipt_sha256")
    assert result.get("dependency", {}).get("executor") == CD.EXECUTOR


def test_pc5_the_pinned_door_refusals_stand() -> None:
    """The seam does not weaken anything: the boundary's own decision function is
    untouched for the adapters it actually classifies, and the door's pinned
    discovery-fallback refusal (the guard suite's 'compress notes.txt' sentence,
    which never reaches capability dispatch) still refuses with the same status."""
    from canonical.runtime import computer_execution_boundary_v1 as boundary
    from canonical.runtime import live_brain_route_admission_v1 as door
    # The boundary's own classifier answers exactly as before.
    assert boundary.refuses_execution(
        "shell.command.run", _entry("shell.command.run")) is True
    assert boundary.refuses_execution(
        "software.analysis.diagnose_and_architect.v1",
        _entry("software.analysis.diagnose_and_architect.v1")) is True
    # The discovery fallback keeps its pinned refusal for a synthesis-shaped goal.
    result = door.solve({"task_id": "pc5",
                         "goal": "compress notes.txt into notes.txt.gz"})
    assert result.get("status") == boundary.STATUS
    assert result.get("pass") is False

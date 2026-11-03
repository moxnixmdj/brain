"""A capability nothing has ever run verifies itself by running.

Each test is written so that breaking the mechanism makes it fail. A test that
passes against a module returning FRESH unconditionally is not evidence.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import capability_self_verification_v1 as S  # noqa: E402
from canonical.runtime import binding_pin_is_current_v1 as P  # noqa: E402


def _repo(tmp_path: Path, *, source: str = "print('ok')\n", module: bytes | None = None) -> Path:
    """A miniature repository: one governed adapter, one bound row."""
    adapter = tmp_path / "canonical/runtime/demo_v1.py"
    adapter.parent.mkdir(parents=True, exist_ok=True)
    adapter.write_bytes(module if module is not None else source.encode())
    reg = {"schema": "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1",
           "capabilities": {"DEMO_V1": {"adapter_module": "demo_v1", "entrypoint": "run",
                                        "verification": {}}}}
    p = tmp_path / P.REGISTRY
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(reg), encoding="utf-8")
    return tmp_path


def test_a_clean_run_moves_a_capability_from_unverified_to_fresh(tmp_path):
    """The measured live fact: 85 of 136 were unverified only because nobody ran them."""
    root = _repo(tmp_path)
    assert S.outcome(root)["counts"][S.UNVERIFIED] == 1

    report = S.verify(root, budget=4)
    assert report["probed"] == 1
    assert report["observations"][0]["observed"] == S.RAN
    assert S.outcome(root)["rows"]["DEMO_V1"]["verdict"] == S.FRESH


def test_editing_the_module_after_the_run_makes_it_stale(tmp_path):
    """The claim is behavioural: it describes the code that ran, and stops describing
    the code once that code moves."""
    root = _repo(tmp_path)
    S.verify(root, budget=4)
    assert S.outcome(root)["rows"]["DEMO_V1"]["verdict"] == S.FRESH

    (root / "canonical/runtime/demo_v1.py").write_text("print('changed')\n", encoding="utf-8")
    row = S.outcome(root)["rows"]["DEMO_V1"]
    assert row["verdict"] == S.STALE
    assert row["reason"] == "THE_MODULE_CHANGED_SINCE_IT_RAN"


def test_changing_the_environment_after_the_run_makes_it_stale(tmp_path, monkeypatch):
    """A dependency that disappears is a change to the thing the observation described."""
    root = _repo(tmp_path)
    S.verify(root, budget=4)
    assert S.outcome(root)["rows"]["DEMO_V1"]["verdict"] == S.FRESH

    monkeypatch.setenv("PATH", os.environ.get("PATH", "") + ":/tmp/definitely-not-a-dep")
    row = S.outcome(root)["rows"]["DEMO_V1"]
    assert row["verdict"] == S.STALE
    assert row["reason"] == "THE_ENVIRONMENT_CHANGED_SINCE_IT_RAN"


def test_deleting_the_module_makes_it_stale_not_fresh(tmp_path):
    root = _repo(tmp_path)
    S.verify(root, budget=4)
    (root / "canonical/runtime/demo_v1.py").unlink()
    row = S.outcome(root)["rows"]["DEMO_V1"]
    assert row["verdict"] == S.STALE
    assert row["reason"] == "THE_RECORDED_MODULE_IS_GONE"


def test_a_failed_run_is_recorded_but_never_counts_as_fresh(tmp_path):
    """A probe that fails is data. It must not become evidence of working."""
    root = _repo(tmp_path, source="raise SystemExit(3)\n")
    report = S.verify(root, budget=4)
    assert report["observations"][0]["observed"] == S.FAILED
    row = S.outcome(root)["rows"]["DEMO_V1"]
    assert row["verdict"] == S.STALE
    assert row["reason"] == "THE_LAST_OBSERVED_RUN_DID_NOT_COMPLETE"


def test_a_missing_dependency_is_distinguished_from_a_crash(tmp_path):
    """42 live capabilities were in this state. Lumping them with a crash would hide
    the fact that they are fine and the host is not."""
    root = _repo(tmp_path, source="import definitely_not_a_real_module_v1\n")
    report = S.verify(root, budget=4)
    assert report["observations"][0]["observed"] == S.MISSING_DEPENDENCY
    assert S.classify("ModuleNotFoundError: no module named 'x'", 1) == S.MISSING_DEPENDENCY
    assert S.classify("", 1) == S.FAILED


def test_a_module_needing_input_is_distinguished_from_both(tmp_path):
    root = _repo(tmp_path, source="import sys\nsys.stderr.write('usage: demo <file>\\n')\nraise SystemExit(2)\n")
    report = S.verify(root, budget=4)
    assert report["observations"][0]["observed"] == S.NEEDS_INPUT


def test_the_budget_is_honoured(tmp_path):
    """The creature must stay able to do work that is not self-measurement."""
    adapter_dir = tmp_path / "canonical/runtime"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    caps = {}
    for i in range(10):
        (adapter_dir / f"demo_{i}_v1.py").write_text("print('ok')\n", encoding="utf-8")
        caps[f"DEMO_{i}_V1"] = {"adapter_module": f"demo_{i}_v1", "verification": {}}
    p = tmp_path / P.REGISTRY
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"capabilities": caps}), encoding="utf-8")

    report = S.verify(tmp_path, budget=3)
    assert report["probed"] == 3
    assert S.outcome(tmp_path)["counts"][S.FRESH] == 3


def test_a_probe_cannot_write_into_the_tree_it_measures(tmp_path):
    """Probing must not change the thing it is measuring."""
    root = _repo(tmp_path, source="open('written_by_probe.txt','w').write('x')\nprint('ok')\n")
    before = sorted(p.name for p in (tmp_path / "canonical/runtime").iterdir())
    S.verify(root, budget=4)
    after = sorted(p.name for p in (tmp_path / "canonical/runtime").iterdir())
    assert before == after
    assert not (tmp_path / "written_by_probe.txt").exists()


def test_a_slow_module_is_a_timeout_not_a_hang(tmp_path):
    root = _repo(tmp_path, source="import time\ntime.sleep(30)\n")
    report = S.verify(root, budget=4, timeout_s=2)
    assert report["observations"][0]["observed"] == S.TIMEOUT


def test_the_registry_is_never_written_by_the_observer(tmp_path):
    """Writing evidence into the claim would be marking its own homework."""
    root = _repo(tmp_path)
    reg = root / P.REGISTRY
    before = reg.read_bytes()
    S.verify(root, budget=4)
    assert reg.read_bytes() == before
    assert (root / S.EVIDENCE_PATH).is_file(), "evidence must live in its own file"


def test_only_unverified_capabilities_are_probed(tmp_path):
    """A fresh capability is not re-run; re-running is the only thing that re-earns it,
    and re-earning must be a deliberate act."""
    root = _repo(tmp_path)
    S.verify(root, budget=4)
    second = S.verify(root, budget=4)
    assert second["probed"] == 0, "an already-verified capability must not be probed again"


def test_the_live_tree_gains_fresh_capabilities_by_running_them(tmp_path, monkeypatch):
    """Against the real registry, with evidence redirected so the test cannot depend on
    what a previous run happened to leave behind.

    An earlier version read and wrote the repository's real evidence file: once all 136
    rows had been observed it asserted `probed > 0` and failed, which made it a test of
    leftover state rather than of the mechanism. Redirection is the fix.
    """
    monkeypatch.setattr(S, "EVIDENCE_PATH", tmp_path / "evidence.json")
    root = REPO
    before = S.outcome(root)["counts"]
    report = S.verify(root, budget=3)
    after = S.outcome(root)["counts"]
    assert report["probed"] > 0
    assert after[S.UNVERIFIED] <= before[S.UNVERIFIED]
    for cid in [o["capability_id"] for o in report["observations"]]:
        assert S.outcome(root)["rows"][cid]["verdict"] in {S.FRESH, S.STALE}


def test_run_contract_returns_a_dict_the_door_can_call():
    out = S.run({"budget": 0}, str(REPO))
    assert isinstance(out, dict)
    assert out["schema"] == S.SCHEMA
    assert out["model_dependency_count"] == 0
    assert out["incremental_spend_usd"] == 0


def test_the_creature_senses_self_verification_in_its_pulse():
    """The mechanism must run in the cycle, not sit on a shelf.

    `sense_reality` already audited stored code rules through rule_expiry_v1. It never
    audited bound capabilities; this pins the extension.
    """
    import tempfile
    from canonical.swe_kernel.autonomous_awake_loop_v1 import AwakeAgencyDaemon

    d = AwakeAgencyDaemon(REPO, ledger_path=Path(tempfile.mkdtemp()) / "l.json")
    assert d.self_verify_budget > 0, "the pulse must carry a bounded budget"
    sensed = d.sense_reality()
    block = sensed.get("self_verified_capabilities")
    assert isinstance(block, dict)
    assert "counts" in block, block
    assert block["counts"].get(S.FRESH, 0) + block["counts"].get(S.STALE, 0) > 0


def test_a_broken_probe_never_stops_the_creature(monkeypatch):
    """Fail open: self-measurement failing must not stop the pulse."""
    import tempfile
    from canonical.swe_kernel.autonomous_awake_loop_v1 import AwakeAgencyDaemon

    d = AwakeAgencyDaemon(REPO, ledger_path=Path(tempfile.mkdtemp()) / "l.json")
    monkeypatch.setattr(S, "verify", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    sensed = d.sense_reality()
    assert sensed.get("self_verified_capabilities", {}).get("error") == "RuntimeError"
    assert "binary_count" in sensed, "the rest of sensing must still have happened"

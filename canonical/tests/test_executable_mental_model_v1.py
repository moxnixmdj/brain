"""Permanent verification suite for Leap 4: Lightweight Executable Mental Models
(Pre-Execution SWE Mental Simulation + CU World-Model Rollout & Counterexample Repair).
Zero external model calls (`model_calls == 0`), zero stored weights (`parameters_stored == 0`).
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

from canonical.runtime import causal_angelic_swe_engine_v1 as PY_SWE
from canonical.runtime import executable_mental_model_v1 as MENTAL


def test_01_swe_mental_simulator_verdicts_and_fuel_safety() -> None:
    """Verify PROMOTE_CLEAN_FLIP, PRUNE_REGRESSION, PRUNE_NOOP, UNCERTAIN (fail-open), and infinite-loop fuel cap."""
    orig = (
        "def clamp_nonneg(x, limit=10):\n"
        "    if x > limit:\n"
        "        return limit\n"
        "    return x\n"
    )
    failing_envs = [{"x": -1, "limit": 10}, {"x": -50, "limit": 10}]
    passing_envs = [{"x": 0, "limit": 10}, {"x": 5, "limit": 10}, {"x": 20, "limit": 10}]

    # 1. Clean fix -> PROMOTE_CLEAN_FLIP in <5ms
    good = (
        "def clamp_nonneg(x, limit=10):\n"
        "    if x < 0:\n"
        "        return 0\n"
        "    if x > limit:\n"
        "        return limit\n"
        "    return x\n"
    )
    r_good = MENTAL.simulate_patch_mental_model(orig, good, failing_envs=failing_envs, passing_envs=passing_envs, hint_lineno=2)
    assert r_good["verdict"] == "PROMOTE_CLEAN_FLIP", r_good
    assert r_good["failing_flips"] == 2
    assert r_good["passing_regressions"] == 0
    assert r_good["model_calls"] == 0 and r_good["parameters_stored"] == 0

    # 2. Regressive patch (breaks x=5 passing test!) -> PRUNE_REGRESSION
    bad_reg = (
        "def clamp_nonneg(x, limit=10):\n"
        "    if x <= 5:\n"
        "        return 0\n"
        "    if x > limit:\n"
        "        return limit\n"
        "    return x\n"
    )
    r_reg = MENTAL.simulate_patch_mental_model(orig, bad_reg, failing_envs=failing_envs, passing_envs=passing_envs, hint_lineno=2)
    assert r_reg["verdict"] == "PRUNE_REGRESSION", r_reg
    assert r_reg["passing_regressions"] >= 1

    # 3. No-op patch on failing inputs -> PRUNE_NOOP
    noop = (
        "def clamp_nonneg(x, limit=10):\n"
        "    if x > 999:\n"
        "        return 999\n"
        "    if x > limit:\n"
        "        return limit\n"
        "    return x\n"
    )
    r_noop = MENTAL.simulate_patch_mental_model(orig, noop, failing_envs=failing_envs, passing_envs=passing_envs, hint_lineno=2)
    assert r_noop["verdict"] == "PRUNE_NOOP", r_noop
    assert r_noop["failing_flips"] == 0

    # 4. External unknown call -> sound fail-open UNCERTAIN (never falsely prunes!)
    ext_orig = "def f(x):\n    return external_repo_helper(x)\n"
    ext_pat = "def f(x):\n    return external_repo_helper(x + 1)\n"
    r_ext = MENTAL.simulate_patch_mental_model(ext_orig, ext_pat, failing_envs=[{"x": 1}], passing_envs=[{"x": 2}])
    assert r_ext["verdict"] == "UNCERTAIN", r_ext

    # 5. Infinite loop in patched candidate -> fuel-bounded safely without hanging!
    inf_loop = (
        "def clamp_nonneg(x, limit=10):\n"
        "    while True:\n"
        "        x = x + 1\n"
        "    return x\n"
    )
    r_inf = MENTAL.simulate_patch_mental_model(orig, inf_loop, failing_envs=failing_envs, passing_envs=passing_envs, max_steps=64)
    assert r_inf["ms"] < 200.0


def test_02_swe_engine_live_solve_with_leap4_mental_prioritization() -> None:
    """Verify Leap 4 mental prioritization integrates cleanly into `causal_angelic_swe_engine_v1.solve_repository`."""
    with tempfile.TemporaryDirectory() as td:
        repo = pathlib.Path(td)
        (repo / "pricing.py").write_text(
            "def apply_discount(price, pct):\n"
            "    if pct > 100:\n"
            "        return 0\n"
            "    return price - (price * pct // 100)\n",
            encoding="utf-8",
        )
        (repo / "test_pricing.py").write_text(
            "from pricing import apply_discount\n"
            "def test_zero():\n"
            "    assert apply_discount(100, 0) == 100\n"
            "def test_half():\n"
            "    assert apply_discount(200, 50) == 100\n"
            "def test_over():\n"
            "    assert apply_discount(100, 120) == 0\n"
            "def test_neg_bug_1():\n"
            "    assert apply_discount(100, -10) == 0\n"
            "def test_neg_bug_2():\n"
            "    assert apply_discount(50, -5) == 0\n",
            encoding="utf-8",
        )
        res = PY_SWE.solve_repository(repo, ["test_pricing.py"], python_exe=sys.executable, timeout_s=30.0)
        assert res["verified"] is True, res
        assert res["model_calls"] == 0
        assert res["parameters_stored"] == 0
        assert res["winner"]["regressions"] == 0


def test_03_cu_pre_execution_mental_rollout_and_auto_repair() -> None:
    """Verify CU mental model catches gzip binary read, missing HTTP auth, and uncheckpointed write BEFORE execution."""
    wm = MENTAL.CUMentalWorldModel()
    init = MENTAL.CUWorldState(
        files={"/data/events.csv": {"exists": True, "compressed": True}},
        auth_tokens={"orders_api": False},
        checkpoints=[],
        http_known_auth_required={"/orders"},
    )
    naive_plan = [
        {"kind": "cli_read_text", "path": "/data/events.csv"},
        {"kind": "http_request", "service": "orders_api", "method": "POST", "target": "/orders"},
        {"kind": "destructive_write", "path": "/data/ledger.db"},
    ]

    # Without auto-repair -> predicts failure BEFORE running step 0
    dry = wm.simulate_and_repair_plan(init, naive_plan, auto_repair=False)
    assert dry["safe_to_execute"] is False
    assert dry["predicted_error"] == "COMPRESSED_BINARY_READ_AS_TEXT"

    # With auto-repair -> injects decompress + http_auth + checkpoint and proves entire rollout safe!
    repaired = wm.simulate_and_repair_plan(init, naive_plan, auto_repair=True)
    assert repaired["safe_to_execute"] is True, repaired
    assert repaired["repaired"] is True
    assert len(repaired["injected_repairs"]) == 3
    kinds = [s["kind"] for s in repaired["final_plan"]]
    assert kinds == [
        "decompress_file",
        "cli_read_text",
        "http_auth",
        "http_request",
        "checkpoint",
        "destructive_write",
    ]
    assert repaired["model_calls"] == 0 and repaired["parameters_stored"] == 0


def test_04_patchworld_counterexample_online_model_repair_and_deletion() -> None:
    """Verify PatchWorld-style counterexample world-model patching and O(1) deletion forgetting."""
    wm = MENTAL.CUMentalWorldModel()
    init = MENTAL.CUWorldState(auth_tokens={"billing": False})
    plan = [{"kind": "http_request", "service": "billing", "method": "GET", "target": "/invoices", "action_key": "http_request:/invoices"}]

    # Before encountering 401 counterexample: mental model believes GET /invoices needs no auth
    r0 = wm.simulate_and_repair_plan(init, plan, auto_repair=False)
    assert r0["safe_to_execute"] is True

    # Live execution returns unexpected HTTP_401 -> patch mental model from counterexample in O(1)!
    rule = wm.patch_from_counterexample(
        "http_request:/invoices",
        observed_error="HTTP_401_UNAUTHORIZED",
        required_precondition={"type": "auth_token", "service": "billing"},
    )
    assert rule["rule_id"].startswith("wm_")
    assert wm.export_rules()["parameters_stored"] == 0

    # Now mental model immediately predicts 401 and auto-repairs with http_auth BEFORE touching server!
    r1 = wm.simulate_and_repair_plan(init, plan, auto_repair=True)
    assert r1["safe_to_execute"] is True and r1["repaired"] is True
    assert [s["kind"] for s in r1["final_plan"]] == ["http_auth", "http_request"]

    # Instant O(1) deletion forgetting -> returns to pre-learning prediction cleanly!
    assert wm.delete_rule("http_request:/invoices") is True
    r2 = wm.simulate_and_repair_plan(init, plan, auto_repair=False)
    assert r2["safe_to_execute"] is True

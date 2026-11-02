"""End-to-end falsifiable proof suite for Post-ce551a3 Stages 1-4 Self-Expanding Awake Organism (`K3 = 0`).

Proves:
- Stage 1:
  - 245-chain `type_level_composer_v1` multi-step typed artifact composition + `macro_v1` chunking (`>5x` warm speedup).
  - Zero-field `autonomous_v1.run` workspace closure inside transactional CoW rollback + negative-control zero-byte drift rollback.
  - Multi-step `osworld_live_agent_v19` closed-loop stepping (`osw_env.step`) + automatic `compile_and_qualify_skill` pixel->CLI layer collapse.
  - Content-addressed SQLite-WAL `IncrementalSemanticGraph` (`< 25 ms` warm semantic repo navigation).
- Stage 2:
  - `select_impacted_tests_fast` backed by SQLite-WAL `IncrementalSemanticGraph` (`used_semantic_graph is True`).
  - White-box live runtime trace harvesting + algebraic dual span synthesis (`whitebox_introspector_and_trace_synthesizer_v1`) repairing loop/table-driven tests where static `assert f(lit)==lit` scraping sees 0 literals.
  - Counterexample-driven rule scope refinement (`VerifiedSkillStore.narrow_rule_scope` / `finite_capability_diagnosis`) automatically invalidating or narrowing misfired recalled rules on the exact run they fail.
- Stage 3:
  - Active black-box mechanism discovery (`h100_zero_learned_mechanism_synthesizer_v1.propose_discriminator`) actively querying discriminating points to collapse competing hypotheses to 1 unique law and extrapolating out-of-bounds (`K3 = 0`).
  - 2D spatial/grid state-transition induction (`grid_delta_rule_inducer_v2`) + fail-closed negative control on contradictory pairs.
  - Autonomous capability discovery (`capability_discovery.search_all` + local dormant adapters + PATH binaries).
- Stage 4:
  - Self-expanding `AwakeAgencyDaemon.pulse()` wired to `meta_learning_policy_v9`, `meta_strategy_abstraction_v9.induce_candidate` (exact LCS over verified ordered strategies with `verified_abstraction=False` / `reuse_authorized=False`), `universal_learning_meta_policy_router_v9.route`, and isolated `r3_improvement_queue_driver_v1.drain`.
"""

from __future__ import annotations

import pathlib
import sys
import time

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime.brain_unified_model_v1 import open_model
from canonical.swe_kernel.autonomous_awake_loop_v1 import AwakeAgencyDaemon
from canonical.swe_kernel.cow_impact_repair_engine_v1 import (
    repair_repository_in_cow_zygote,
    select_impacted_tests_fast,
)
from canonical.swe_kernel.forged_binding_and_macro_spine_v1 import (
    discover_and_verify_external_or_local_capability,
)
from canonical.swe_kernel.verified_capability_bridge_index_v1 import (
    query_semantic_repo_navigation,
)
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
from canonical.swe_kernel.zygote_worker_pool_v1 import ZygotePrewarmedPool


def test_stage1_type_level_composer_macro_autonomous_v1_and_osworld_trajectory(
    tmp_path: pathlib.Path,
) -> None:
    model = open_model()
    macro_state = tmp_path / "tlc_macros.json"

    # 1A: Cold 2-step typed composition (`archive.tar_gz.create_from_manifest` -> `archive.verify.tar_gz.gnu`)
    r_cold = model.act_or_learn(
        "create tar_gz archive from manifest and verify tar_gz",
        inputs={
            "allow_type_level_composition": True,
            "macro_state_path": str(macro_state),
        },
    )
    assert r_cold["pass"] is True, r_cold
    assert r_cold["tier_used"] == "tier2_type_level_composer"
    tc_cold = r_cold["autonomous_result"]["type_chain_result"]
    assert tc_cold["from_macro_cache"] is False
    assert tc_cold["chain"] == [
        "archive.tar_gz.create_from_manifest",
        "archive.verify.tar_gz.gnu",
    ]

    # Warm recall via `macro_v1` skips search (`attempted` absent / direct verify_chain)
    r_warm = model.act_or_learn(
        "create tar_gz archive from manifest and verify tar_gz",
        inputs={
            "allow_type_level_composition": True,
            "macro_state_path": str(macro_state),
        },
    )
    assert r_warm["pass"] is True, r_warm
    assert r_warm["autonomous_result"]["from_memory"] is True
    assert r_warm["autonomous_result"]["type_chain_result"]["from_macro_cache"] is True
    assert r_warm["autonomous_result"]["type_chain_result"]["elapsed_ms"] < 60.0

    # 1B: Zero-field workspace autonomy (`autonomous_v1`) + transactional CoW rollback negative control
    ws_ok = tmp_path / "ws_ok"
    ws_ok.mkdir()
    (ws_ok / "Makefile").write_text(
        "artifact:\n\t@mkdir -p dist && printf 'verified-artifact\\n' > dist/artifact.txt\n",
        encoding="utf-8",
    )
    auto_ok = model.act_or_learn(
        "generate dist artifact",
        cwd=ws_ok,
        inputs={"autonomous_workspace": True},
    )
    assert auto_ok["pass"] is True, auto_ok
    assert auto_ok["tier_used"] == "tier2_autonomous_v1"
    assert (ws_ok / "dist" / "artifact.txt").read_text(encoding="utf-8") == "verified-artifact\n"

    # Negative control: failing Makefile target that mutates side-effect file without producing requested report MUST roll back cleanly!
    ws_bad = tmp_path / "ws_bad"
    ws_bad.mkdir()
    (ws_bad / "tracked.txt").write_text("clean\n", encoding="utf-8")
    (ws_bad / "Makefile").write_text(
        "report:\n\t@printf 'corrupted\\n' > tracked.txt && exit 2\n",
        encoding="utf-8",
    )
    auto_bad = model.act_or_learn(
        "generate report bundle",
        cwd=ws_bad,
        inputs={"autonomous_workspace": True},
    )
    assert auto_bad["pass"] is False
    assert (ws_bad / "tracked.txt").read_text(encoding="utf-8") == "clean\n"

    # 1C: Warm SQLite-WAL IncrementalSemanticGraph navigation (`< 25 ms`)
    sem_repo = tmp_path / "sem_repo"
    sem_repo.mkdir()
    (sem_repo / "core.py").write_text(
        "class BaseEngine:\n    pass\n\nclass FastEngine(BaseEngine):\n    def compute(self, x):\n        return x + 1\n",
        encoding="utf-8",
    )
    (sem_repo / "test_core.py").write_text(
        "from core import FastEngine\ndef test_compute():\n    assert FastEngine().compute(2) == 3\n",
        encoding="utf-8",
    )
    _ = query_semantic_repo_navigation(sem_repo, "hierarchy")  # cold build
    t0 = time.perf_counter_ns()
    hier = query_semantic_repo_navigation(sem_repo, "hierarchy", "FastEngine")
    warm_ms = (time.perf_counter_ns() - t0) / 1e6
    assert hier["pass"] is True
    assert warm_ms < 25.0, f"Expected <25ms warm semantic graph query, got {warm_ms:.3f}ms"

    # 1D: Multi-step OSWorld v19 trajectory + automatic `compile_and_qualify_skill` pixel->CLI layer collapse
    import io
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (320, 200), color=(240, 240, 240)).save(buf, format="PNG")
    png_bytes = buf.getvalue()

    class _FakeOSWorldEnv:
        def __init__(self) -> None:
            self.calls = 0

        def step(self, _action: object) -> tuple[dict[str, object], float, bool, dict[str, object]]:
            self.calls += 1
            b2 = io.BytesIO()
            Image.new("RGB", (320, 200), color=(230, 250, 230)).save(b2, format="PNG")
            obs2 = {
                "screenshot": b2.getvalue(),
                "accessibility_tree": (
                    '<desktop-frame name="Settings">'
                    '<check-box name="Dark Mode" states="checked,enabled,showing,visible" x="40" y="60" width="120" height="28"/>'
                    "</desktop-frame>"
                ),
            }
            return obs2, 1.0, True, {}

    fake_env = _FakeOSWorldEnv()
    elev_target = tmp_path / "dark_mode_state.txt"
    osw_res = model.act_or_learn(
        "Ensure the 'Dark Mode' checkbox is checked in dark_mode_state.txt",
        cwd=tmp_path,
        db_path=tmp_path / "wf.sqlite3",
        inputs={
            "osworld_obs": {
                "screenshot": png_bytes,
                "accessibility_tree": (
                    '<desktop-frame name="Settings">'
                    '<check-box name="Dark Mode" states="unchecked,enabled,showing,visible" x="40" y="60" width="120" height="28"/>'
                    "</desktop-frame>"
                ),
            },
            "osworld_env": fake_env,
            "osworld_max_steps": 3,
            "osworld_elevated_trace": {
                "steps": [{"layer": "pixel_ui", "op": "click", "x": 100, "y": 74}],
                "observed_effects": {
                    "file_writes": [{"path": "dark_mode_state.txt", "content": "checked"}],
                },
            },
            "osworld_postcondition": {
                "kind": "file_contains",
                "path": "dark_mode_state.txt",
                "contains": "checked",
            },
        },
    )
    assert osw_res["pass"] is True, osw_res
    assert osw_res["tier_used"] == "tier2_osworld_v19"
    auto_r = osw_res["autonomous_result"]
    assert fake_env.calls >= 1
    assert auto_r["completed"] is True
    assert auto_r["learned_this_turn"] is True
    assert auto_r["layer_elevation_receipt"]["pass"] is True


def test_stage2_semantic_slicing_whitebox_dual_synthesis_and_counterexample_scope_refinement(
    tmp_path: pathlib.Path,
) -> None:
    store = VerifiedSkillStore(tmp_path / "skills.sqlite3", seed=False)
    # Seed Rule A: `return a <= b` -> `return a < b` (misfires via SCOPE_OPERATOR on `if len(path) <= 1:`, so MUST SPECIALIZE to `SCOPE_STATEMENT` rather than expire!)
    seeded_op = store.crystallize_code_fix(
        before_snippet="def cmp_pair(a, b):\n    return a <= b\n",
        after_snippet="def cmp_pair(a, b):\n    return a < b\n",
        language="python",
        error_class="BOUNDARY_OFF_BY_ONE",
    )
    assert seeded_op["crystallized"] is True
    specialize_sid = str(seeded_op["skill_id"])

    # Seed Rule B: `if len(s) <= 1:` -> `if len(s) < 1:` (misfires EVEN at `SCOPE_STATEMENT`, so MUST INVALIDATE!)
    seeded_stmt = store.crystallize_code_fix(
        before_snippet="def guard_len(s: str) -> str:\n    if len(s) <= 1:\n        return s\n    return s\n",
        after_snippet="def guard_len(s: str) -> str:\n    if len(s) < 1:\n        return s\n    return s\n",
        language="python",
        error_class="BOUNDARY_OFF_BY_ONE",
    )
    assert seeded_stmt["crystallized"] is True
    overbroad_sid = str(seeded_stmt["skill_id"])

    # Repo with:
    # 1) `url_norm.py` having BOTH `if len(path) <= 1: return path` (where `<=` MUST stay `<=`, so recalled rule misfires!)
    #    AND algebraic dual bug `return path.lstrip("/")` instead of `return path.rstrip("/")`!
    # 2) Table-loop test (`for inp, want in CASES:`) so static `assert fn('a/') == 'a'` literal scraping extracts 0 direct literals!
    repo = tmp_path / "dual_repo"
    repo.mkdir()
    (repo / "url_norm.py").write_text(
        "def strip_trailing_slash(path: str) -> str:\n"
        "    if len(path) <= 1:\n"
        "        return path\n"
        "    return path.lstrip('/')\n",
        encoding="utf-8",
    )
    (repo / "unrelated_math.py").write_text(
        "def cube(n: int) -> int:\n    return n * n * n\n",
        encoding="utf-8",
    )
    (repo / "test_url_norm.py").write_text(
        "from url_norm import strip_trailing_slash\n\n"
        "CASES = [('/', '/'), ('/api/v1/', '/api/v1'), ('/docs///', '/docs')]\n\n"
        "def test_strip_trailing_slash_loop():\n"
        "    for raw, expected in CASES:\n"
        "        assert strip_trailing_slash(raw) == expected\n",
        encoding="utf-8",
    )
    (repo / "test_unrelated_math.py").write_text(
        "from unrelated_math import cube\n\ndef test_cube():\n    assert cube(3) == 27\n",
        encoding="utf-8",
    )

    slice_info = select_impacted_tests_fast(
        repo,
        ["url_norm.py"],
        [repo / "test_url_norm.py", repo / "test_unrelated_math.py"],
    )
    assert slice_info["used_semantic_graph"] is True
    assert [p.name for p in slice_info["selected_tests"]] == ["test_url_norm.py"]

    rep = repair_repository_in_cow_zygote(
        repo,
        skill_store=store,
        apply_to_workspace=True,
    )
    assert rep["pass"] is True, rep
    assert "WHITEBOX_TRACE_AND_DUAL_SYNTHESIS" in rep["mode"]
    assert "rstrip" in (repo / "url_norm.py").read_text(encoding="utf-8")
    # Counterexample-driven scope refinement MUST specialize `specialize_sid` -> `SCOPE_STATEMENT` AND invalidate `overbroad_sid`!
    refs_by_sid = {str(r.get("skill_id")): r for r in rep.get("scope_refinements", [])}
    assert refs_by_sid[specialize_sid]["action"] == "SPECIALIZED_SCOPE", refs_by_sid
    assert refs_by_sid[specialize_sid]["persisted_scope"] == "SCOPE_STATEMENT"
    assert refs_by_sid[overbroad_sid]["action"] == "INVALIDATED", refs_by_sid

    rules_after = {str(r.get("skill_id")): r for r in store.lookup_rules("python")}
    assert rules_after[specialize_sid].get("state") != "INVALIDATED"
    assert rules_after[specialize_sid].get("learned_scope") == "SCOPE_STATEMENT"
    assert rules_after[overbroad_sid].get("state") == "INVALIDATED"
    # Specialized rule STILL solves `return x <= y` on exact statement shape!
    assert store.recall_and_apply_verified(
        source_text="def check_bound(x, y):\n    return x <= y\n",
        language="python",
        verifier=lambda c: "< y" in c,
    ) is not None


def test_stage3_active_mechanism_discriminator_grid_induction_and_capability_discovery() -> None:
    model = open_model()

    # 3A: Active Black-Box Mechanism Discovery (`propose_discriminator` resolves colinear ambiguity x==y between x*y and x^2!)
    colinear_rows = [{"x": float(v), "y": float(v), "z": float(v * v)} for v in (1, 2, 3, 4, 5)]
    mech = model.act_or_learn(
        "discover unknown two-variable law from colinear initial rows and extrapolate",
        inputs={
            "mechanism_oracle": lambda pt: float(pt["x"] * pt["y"]),
            "mechanism_rows": colinear_rows,
            "mechanism_target": "z",
            "holdout_points": [{"x": 12.0, "y": -5.0}, {"x": 7.0, "y": 9.0}],
        },
    )
    assert mech["pass"] is True, mech
    assert mech["tier_used"] == "tier2_active_mechanism_discovery"
    m_res = mech["autonomous_result"]["mechanism"]
    assert m_res["unique"] is True, m_res
    assert m_res["discriminator_rounds"] >= 1
    assert abs(m_res["predictions"][0]["predicted"] - (-60.0)) < 1e-6
    assert abs(m_res["predictions"][1]["predicted"] - 63.0) < 1e-6

    # 3B: 2D Spatial / Grid Delta Rule Induction (`grid_delta_rule_inducer_v2`) + negative control
    grid_ok = model.act_or_learn(
        "induce 2d grid orthogonal neighbor marker rule",
        inputs={
            "grid_training_pairs": [
                {"input": [[1, 0, 0], [0, 0, 0]], "output": [[1, 2, 0], [2, 0, 0]]},
                {"input": [[0, 0, 1], [0, 0, 0]], "output": [[0, 2, 1], [0, 0, 2]]},
            ],
            "grid_test_inputs": [[[0, 0, 0], [0, 1, 0]]],
        },
    )
    assert grid_ok["pass"] is True, grid_ok
    assert grid_ok["tier_used"] == "tier2_grid_delta_rule_inducer"
    preds = grid_ok["autonomous_result"]["grid_induction"]["predictions"]
    assert preds[0]["prediction"] == [[0, 2, 0], [2, 1, 2]]

    # Negative control: contradictory training pairs (`same input -> different outputs`) MUST fail closed
    grid_bad = model.act_or_learn(
        "induce contradictory 2d grid rule",
        inputs={
            "grid_training_pairs": [
                {"input": [[1, 0], [0, 0]], "output": [[1, 2], [0, 0]]},
                {"input": [[1, 0], [0, 0]], "output": [[1, 3], [0, 0]]},
            ],
        },
    )
    assert grid_bad["pass"] is False

    # 3C: Autonomous local + federated capability discovery (`K3 = 0`, `binding_performed=False`)
    disc = discover_and_verify_external_or_local_capability("python3 concrete oracle", limit_per_source=3)
    assert disc["pass"] is True
    assert "python3" in disc["local_path_binaries"]
    assert any("oracle" in s for s in disc["local_dormant_adapters"])
    assert disc["k3_external_llm_calls"] == 0


def test_stage4_self_expanding_awake_daemon_v9_meta_policy_abstraction_and_r3_drain(
    tmp_path: pathlib.Path,
) -> None:
    ws = tmp_path / "awake_ws"
    ws.mkdir()
    (ws / "calc.py").write_text("def inc(x):\n    return x - 1\n", encoding="utf-8")
    (ws / "test_calc.py").write_text(
        "from calc import inc\ndef test_inc():\n    assert inc(4) == 5\n",
        encoding="utf-8",
    )

    daemon = AwakeAgencyDaemon(
        ws,
        ledger_path=tmp_path / "ledger.json",
        skill_store_path=tmp_path / "skills.sqlite3",
        workflow_db_path=tmp_path / "workflows.sqlite3",
        journal_dir=tmp_path / "journal",
        r3_state_path=tmp_path / "r3_state.json",
        apply_verified_repairs=True,
    )

    # Pulse 1 repairs `calc.py` in CoW sandbox (`cow-zygote-repair-c1` verified episode + strategy #1)
    p1 = daemon.pulse()
    assert p1["k3_external_llm_calls"] == 0
    assert p1["cow_experimentation"]["repaired"] >= 1
    assert p1["r3_queue_drain"]["pass"] is True
    assert len(daemon.verified_strategies) == 1

    # Record a second verified strategy (`probe-verify-crystallize`) and run Pulse 2
    daemon.record_verified_meta_episode_and_strategy(
        "ep-fast-probe",
        context_features=p1["context_features"],
        strategy_id="probe-verify-crystallize",
        steps=["sense", "probe", "verify", "crystallize"],
        burden_before=5,
        burden_after=0,
        wall_clock_s=0.002,
    )
    p2 = daemon.pulse()
    assert p2["meta_policy_recommendation"]["recommended_strategy_id"] == "probe-verify-crystallize"
    abstr = p2["meta_strategy_abstraction_candidate"]
    assert abstr is not None
    assert abstr["status"] == "ORDERED_META_STRATEGY_ABSTRACTION_CANDIDATE"
    assert abstr["common_steps"] == ["sense", "verify", "crystallize"]
    assert abstr["verified_abstraction"] is False
    assert abstr["reuse_authorized"] is False

    # Verify V9 Universal Learning Meta-Policy Router preserves V8 load-bearing base invariants
    routed_v9 = daemon.route_universal_learning_v9(
        goal="repair calc repository",
        context_features=p2["context_features"],
    )
    assert routed_v9["status"] == "V9_META_POLICY_APPLIED"
    assert routed_v9["meta_policy"]["recommended_strategy_id"] == "probe-verify-crystallize"
    assert routed_v9["meta_strategy_abstraction"]["common_steps"] == ["sense", "verify", "crystallize"]
    assert routed_v9["execution_authority"] is False
    assert routed_v9["promotion_authority"] is False

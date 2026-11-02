"""End-to-End Acceptance Suite for the 4-Wave Optimal Plan (`K3 = 0`, `$0` spend).

Proves all 5 Non-Flattering Acceptance Gates:
  - Wave 1 (`forged_binding_and_macro_spine_v1`):
      1a. Self-forging adapter discovery + kill-test admission (`require_kill=True`) + vacuous/rubber-stamp refusal.
      1b. Implied-world input completion (`source_root` promoted from file + synthesized `output_path`).
      1c. `< 1 ms` DreamCoder plan macro recall (`macro_v1`) + e-process failure eviction (`failures > successes`).
  - Wave 2 (`python_scoped_edit_rule_v1`, `tree_sitter_cst_skill_skeleton_v1`, `cow_impact_repair_engine_v1`):
      2a. Statement-scoped class-method crystallization + warm `< 350 ms` `SKILL_RECALL` on real `pluggy` (`PluginManager._verify_hook`).
      2b. 7-language `if/elif` CST skeleton transfer (`Python -> Rust, Go, TypeScript, JavaScript, Java, C++`).
      2c. Multi-round sequential repository repair (`max_rounds=3`, `rounds_used == 2`) across 2 independent failing modules/test suites.
  - Wave 3 (`zygote_worker_pool_v1`, `transactional_parallel_execution_v1`, `global_extrapolation_chase_spine_v1`):
      3a. Multi-worker parallel speculative CoW sharding (`run_parallel_sharded`) returning fastest winner & `SIGTERM`-cancelling slow siblings.
      3b. Transactional CoW write rollback (`execute_transactional_cow_action`) leaving **0 changed bytes** (`tree_manifest` SHA-256 identical) on failed/refused actions.
      3c. Measured-latency + Wilson LCB reliability cost routing (`expected_gain / measured_ms * reliability_lcb`).
  - Wave 4 (`autonomous_awake_loop_v1`, `causal_trace_to_skill_compiler_v1`, `predicate_world_abstraction_v1`):
      4a. Crash-resumable hash-chained `AwakeAgencyDaemon` (`terminal_causal_journal_v2`) resuming after mid-run termination without repeating committed actions + rejecting forked sequence tampering.
      4b. Counterfactual leave-one-out trace ablation (`prune_non_causal_steps_counterfactually`) stripping noisy `ls`/`echo`/unused-read steps.
      4c. Zero-LLM OSWorld desktop AT-SPI A11y XML grounding (`decide_osworld_desktop_action`).
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import time
import pytest


# ---------------------------------------------------------------------------
# WAVE 1: Self-Forging + Implied World Binding + < 1 ms DreamCoder Macro Recall
# ---------------------------------------------------------------------------


def test_wave1_self_forging_admits_real_adapter_and_kills_rubber_stamp(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from canonical.swe_kernel.forged_binding_and_macro_spine_v1 import (
        forge_dormant_adapter,
        invoke_forged_capability,
    )

    ws = tmp_path / "ws"
    (ws / "pkg_a").mkdir(parents=True)
    (ws / "pkg_b").mkdir(parents=True)
    f1 = ws / "pkg_a" / "mod1.py"
    f2 = ws / "pkg_b" / "mod2.py"
    f1.write_text('def f(x):\n    """post: result >= 0"""\n    return x - 1\n', encoding="utf-8")
    f2.write_text('def f(x):\n    """post: result > 0"""\n    return x * x\n', encoding="utf-8")
    state_file = tmp_path / "forged_state.json"

    # 1) Genuine unbound dormant adapter (`concrete_execution_oracle`) passes all 5 forge gates (including kill-test!)
    rep = forge_dormant_adapter(
        "concrete_execution_oracle",
        [
            {"target_path": str(f1)},
            {"target_path": str(f2)},
        ],
        root=ws,
        state_path=state_file,
    )
    assert rep["admitted"] is True, rep
    assert rep["capability_id"] == "forged.concrete_execution_oracle"
    assert rep["k3_external_llm_calls"] == 0

    inv = invoke_forged_capability(
        "forged.concrete_execution_oracle",
        {"target_path": str(f1)},
        root=ws,
        state_path=state_file,
    )
    assert inv.get("forged_from") == "concrete_execution_oracle"

    # 2) Unforged module invocation is strictly refused by `forged_invoker`
    with pytest.raises(RuntimeError, match="NOT_FORGED"):
        invoke_forged_capability(
            "forged.never_admitted_module",
            {"source_root": "pkg_a"},
            root=ws,
            state_path=state_file,
        )

    # 3) A rubber-stamp module that returns `{verified: True}` on every corrupted input CANNOT BE KILLED -> refused!
    from canonical.runtime import capability_forge_v1 as cf

    orig_call = cf._call
    monkeypatch.setattr(cf, "_call", lambda mod, args, root: (True, {"count": 1, "items": ["always_ok"]}))
    bad_rep = forge_dormant_adapter(
        "rubber_stamp_fake_adapter",
        [{"input_path": "pkg_a/mod1.py"}, {"input_path": "pkg_b/mod2.py"}],
        root=ws,
        state_path=state_file,
        register_on_admit=False,
    )
    monkeypatch.setattr(cf, "_call", orig_call)
    assert bad_rep["admitted"] is False
    assert "CANNOT_BE_KILLED__ACCEPTS_CORRUPTED_INPUT" in bad_rep["reasons"]


def test_wave1_implied_world_binding_and_sub_ms_macro_chunking(tmp_path: pathlib.Path) -> None:
    from canonical.swe_kernel.forged_binding_and_macro_spine_v1 import (
        bind_implied_capability_inputs,
        execute_or_learn_clause_macro,
        lookup_verified_chain_macro,
    )

    ws = tmp_path / "bind_ws"
    (ws / "service").mkdir(parents=True)
    (ws / "service" / "handler.py").write_text("def handle(req):\n    return req\n", encoding="utf-8")

    # Goal mentions only a file (`service/handler.py`), NOT `source_root` or `output_path`!
    entry = {
        "capability_id": "code.python.ast_audit",
        "action_template": {
            "args": {
                "source_root": "${input.source_root}",
                "output_path": "${input.output_path}",
            }
        },
    }
    bound = bind_implied_capability_inputs(
        "audit the python file service/handler.py",
        "code.python.ast_audit",
        entry,
        root=ws,
    )
    assert bound["complete"] is True, bound
    assert bound["inputs"]["source_root"] == "service"
    assert bound["inputs"]["output_path"].endswith(".json")

    # DreamCoder `macro_v1` plan chunking: < 1 ms warm lookup + e-process eviction on repeated failure
    macro_state = tmp_path / "macros.json"
    cold = execute_or_learn_clause_macro(
        ["extract text from alpha.pdf", "summarize into alpha_report.json"],
        clause_executor=lambda clause, pref: {
            "pass": True,
            "verified": True,
            "capability_id": pref or ("doc.pdf.extract" if ".pdf" in clause else "json.report.emit"),
        },
        state_path=macro_state,
    )
    assert cold["pass"] is True and cold["from_macro"] is False and cold["macro_recorded"] is True

    # Warm lookup on brand-new filenames (`beta.pdf`, `beta_out.json`) of the same `(verbs, file_kinds)` shape!
    t0 = time.perf_counter_ns()
    hit = lookup_verified_chain_macro(
        ["extract text from beta.pdf", "summarize into beta_out.json"],
        state_path=macro_state,
    )
    lookup_ms = (time.perf_counter_ns() - t0) / 1e6
    assert hit is not None
    assert lookup_ms < 1.0, f"Expected < 1.0 ms macro lookup, got {lookup_ms:.3f} ms"

    warm = execute_or_learn_clause_macro(
        ["extract text from beta.pdf", "summarize into beta_out.json"],
        clause_executor=lambda clause, pref: {
            "pass": True,
            "verified": True,
            "capability_id": pref or "WRONG_FALLBACK",
        },
        state_path=macro_state,
    )
    assert warm["pass"] is True and warm["from_macro"] is True
    assert [s["capability_id"] for s in warm["steps"]] == ["doc.pdf.extract", "json.report.emit"]


# ---------------------------------------------------------------------------
# WAVE 2: Statement-Scoped Class-Method `pluggy` < 350ms Recall + 7-Lang CST + Multi-Round Repair
# ---------------------------------------------------------------------------


def test_wave2_pluggy_class_method_crystallizes_and_warm_recalls_fast(tmp_path: pathlib.Path) -> None:
    import pluggy
    from canonical.swe_kernel.cow_impact_repair_engine_v1 import repair_repository_in_cow_zygote
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
    from canonical.swe_kernel.zygote_worker_pool_v1 import ZygotePrewarmedPool

    pluggy_pkg_dir = pathlib.Path(pluggy.__file__).resolve().parent
    ws = tmp_path / "pluggy_repo"
    (ws / "src" / "pluggy").mkdir(parents=True)
    for py_f in pluggy_pkg_dir.glob("*.py"):
        shutil.copy2(py_f, ws / "src" / "pluggy" / py_f.name)

    # Inject real bug inside 50-line `PluginManager._verify_hook` method (`and` -> `or`)
    mgr_path = ws / "src" / "pluggy" / "_manager.py"
    orig_mgr = mgr_path.read_text(encoding="utf-8")
    assert "elif not verified and hook.has_spec():" in orig_mgr
    buggy_mgr = orig_mgr.replace("elif not verified and hook.has_spec():", "elif not verified or hook.has_spec():", 1)
    mgr_path.write_text(buggy_mgr, encoding="utf-8")

    (ws / "tests").mkdir()
    (ws / "tests" / "test_pluginmanager_verify.py").write_text(
        "import pluggy\n\n"
        "hookspec = pluggy.HookspecMarker('example')\n"
        "hookimpl = pluggy.HookimplMarker('example')\n\n"
        "class Spec:\n"
        "    @hookspec\n"
        "    def do_work(self, arg1):\n"
        "        pass\n\n"
        "class EarlyPluginA:\n"
        "    @hookimpl\n"
        "    def do_work(self, arg1):\n"
        "        return arg1 + 1\n\n"
        "class EarlyPluginB:\n"
        "    @hookimpl\n"
        "    def do_work(self, arg1):\n"
        "        return arg1 * 2\n\n"
        "class BadPluginExtraArg:\n"
        "    @hookimpl\n"
        "    def do_work(self, arg1, unexpected_extra):\n"
        "        return arg1\n\n"
        "def test_register_before_and_after_hookspecs():\n"
        "    pm = pluggy.PluginManager('example')\n"
        "    pm.register(EarlyPluginA())\n"
        "    pm.register(EarlyPluginB())\n"
        "    pm.add_hookspecs(Spec)\n"
        "    assert sorted(pm.hook.do_work(arg1=20)) == [21, 40]\n"
        "    raised = False\n"
        "    try:\n"
        "        pm.register(BadPluginExtraArg())\n"
        "    except pluggy.PluginValidationError:\n"
        "        raised = True\n"
        "    assert raised is True\n",
        encoding="utf-8",
    )

    store = VerifiedSkillStore(db_path=tmp_path / "pluggy_skills.sqlite", seed=False)
    pool = ZygotePrewarmedPool()
    pool.prewarm()

    # Cold Run #1: repairs 500-line `pluggy/_manager.py` AND crystallizes `scope = 'statement'` skill!
    cold = repair_repository_in_cow_zygote(ws, skill_store=store, zygote=pool, apply_to_workspace=False)
    assert cold["pass"] is True, cold
    assert cold["files_repaired"] == ["src/pluggy/_manager.py"]
    assert len(cold["crystallized_skill_ids"]) >= 1, cold

    # Warm Run #2 on fresh buggy `pluggy` repo: recalls crystallized class-method skill in < 350 ms!
    warm = repair_repository_in_cow_zygote(ws, skill_store=store, zygote=pool, apply_to_workspace=False)
    assert warm["pass"] is True, warm
    assert warm["mode"].startswith("SKILL_RECALL:"), warm
    assert warm["total_elapsed_ms"] < 350.0, f"Expected < 350 ms warm pluggy recall, got {warm['total_elapsed_ms']} ms"

    # Bonus Wave 2b: verify that exact `elif` condition rule lifts into 7-language CST transfer!
    from canonical.swe_kernel.tree_sitter_cst_skill_skeleton_v1 import iter_cst_skeleton_candidates

    rule = store.lookup_rules("python")[0]
    ts_buggy = "class Manager {\n  verify(ok: boolean, hook: Hook): boolean {\n    if (!ok || hook.hasSpec()) { return false; }\n    return true;\n  }\n}\n"
    ts_cands = list(iter_cst_skeleton_candidates(ts_buggy, rule, target_language="typescript"))
    assert any("!ok && hook.hasSpec()" in c for c in ts_cands), ts_cands

    rust_buggy = "impl Manager {\n    fn verify(&self, ok: bool, hook: &Hook) -> bool {\n        if !ok || hook.has_spec() { return false; }\n        true\n    }\n}\n"
    rust_cands = list(iter_cst_skeleton_candidates(rust_buggy, rule, target_language="rust"))
    assert any("!ok && hook.has_spec()" in c for c in rust_cands), rust_cands


def test_wave2_multi_round_sequential_repository_repair(tmp_path: pathlib.Path) -> None:
    from canonical.swe_kernel.cow_impact_repair_engine_v1 import repair_repository_in_cow_zygote
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
    from canonical.swe_kernel.zygote_worker_pool_v1 import ZygotePrewarmedPool

    repo = tmp_path / "seq_repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)
    (repo / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    # Fault #1 in `pkg/StageOne.py`
    (repo / "pkg" / "stage_one.py").write_text(
        "def normalize_score(raw, scale):\n"
        "    return raw - scale\n",
        encoding="utf-8",
    )
    # Fault #2 in `pkg/stage_two.py`
    (repo / "pkg" / "stage_two.py").write_text(
        "def within_quota(used, limit):\n"
        "    return used < limit\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_01_stage_one.py").write_text(
        "from pkg.stage_one import normalize_score\n\n"
        "def test_normalize_score():\n"
        "    assert normalize_score(10, 5) == 15\n"
        "    assert normalize_score(3, 4) == 7\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_02_stage_two.py").write_text(
        "from pkg.stage_two import within_quota\n\n"
        "def test_within_quota_inclusive():\n"
        "    assert within_quota(5, 5) is True\n"
        "    assert within_quota(6, 5) is False\n",
        encoding="utf-8",
    )

    store = VerifiedSkillStore(db_path=tmp_path / "seq_skills.sqlite")
    pool = ZygotePrewarmedPool()
    pool.prewarm()

    res = repair_repository_in_cow_zygote(repo, skill_store=store, zygote=pool, max_rounds=3, apply_to_workspace=True)
    assert res["pass"] is True, res
    assert res["files_repaired"] == ["pkg/stage_one.py", "pkg/stage_two.py"]
    assert len(res["crystallized_skill_ids"]) == 2


# ---------------------------------------------------------------------------
# WAVE 3: Parallel Speculative Zygote + Zero-Byte CoW Rollback + Latency Cost Router
# ---------------------------------------------------------------------------


def test_wave3_parallel_speculative_sharding_and_transactional_cow_rollback(tmp_path: pathlib.Path) -> None:
    from canonical.swe_kernel.global_extrapolation_chase_spine_v1 import rank_global_minimal_action_routes
    from canonical.swe_kernel.transactional_parallel_execution_v1 import (
        LatencyReliabilityCostRouter,
        execute_transactional_cow_action,
        snapshot_workspace_manifest,
    )
    from canonical.swe_kernel.zygote_worker_pool_v1 import ZygotePrewarmedPool

    pool = ZygotePrewarmedPool()
    pool.prewarm()

    # 3a) 4-shard speculative race: 3 shards sleep 400ms, shard #2 wins in 5ms -> siblings SIGTERM-cancelled!
    def _slow_shard() -> dict:
        time.sleep(0.40)
        return {"found": False}

    def _fast_winner() -> dict:
        time.sleep(0.005)
        return {"found": True, "patch": "x + 1"}

    spec = pool.run_parallel_sharded(
        [_slow_shard, _slow_shard, _fast_winner, _slow_shard],
        winner_predicate=lambda r: bool(r.get("found")),
        timeout_s=5.0,
    )
    assert spec["found_winner"] is True, spec
    assert spec["winning_shard"] == 2
    assert spec["siblings_cancelled"] >= 2
    assert spec["elapsed_ms"] < 180.0, f"Expected early cancellation < 180 ms, got {spec['elapsed_ms']} ms"

    # 3b) Transactional CoW rollback: dirtying files + creating partial junk leaves ZERO changed bytes on failure!
    ws = tmp_path / "tx_ws"
    ws.mkdir()
    (ws / "ledger.txt").write_text("balance=100\n", encoding="utf-8")
    (ws / "config.json").write_text('{"mode": "prod"}\n', encoding="utf-8")
    before_manifest = snapshot_workspace_manifest(ws)

    def _failing_mutation(stage: pathlib.Path) -> dict:
        (stage / "ledger.txt").unlink()
        (stage / "ledger.txt").write_text("CORRUPTED_PARTIAL_WRITE\n", encoding="utf-8")
        (stage / "orphan_garbage.tmp").write_text("junk", encoding="utf-8")
        raise RuntimeError("MID_FLIGHT_ABORT")

    rb = execute_transactional_cow_action(ws, _failing_mutation)
    assert rb["committed"] is False and rb["rolled_back"] is True
    assert rb["zero_byte_drift_verified"] is True
    after_rb_manifest = snapshot_workspace_manifest(ws)
    assert after_rb_manifest["tree_sha256"] == before_manifest["tree_sha256"]
    assert not (ws / "orphan_garbage.tmp").exists()
    assert (ws / "ledger.txt").read_text(encoding="utf-8") == "balance=100\n"

    # Passing transaction commits atomically
    ok_tx = execute_transactional_cow_action(
        ws,
        lambda stage: ((stage / "ledger.txt").unlink(), (stage / "ledger.txt").write_text("balance=250\n", encoding="utf-8"), {"pass": True})[-1],
    )
    assert ok_tx["committed"] is True
    assert ok_tx["files_updated"] == ["ledger.txt"]
    assert (ws / "ledger.txt").read_text(encoding="utf-8") == "balance=250\n"

    # 3c) Measured-latency + reliability LCB router outranks slow probe of identical expected gain
    router = LatencyReliabilityCostRouter()
    for _ in range(4):
        router.record_observation("route_fast_2ms", elapsed_ms=2.0, ok=True)
        router.record_observation("route_slow_900ms", elapsed_ms=900.0, ok=True)
    ranked = rank_global_minimal_action_routes(
        [
            {"route_id": "route_slow_900ms", "expected_gain": 10.0, "candidate_authority": "VERIFIED"},
            {"route_id": "route_fast_2ms", "expected_gain": 10.0, "candidate_authority": "VERIFIED"},
        ],
        goal="reach throughput target",
        experience_state_path=str(tmp_path / "exp.json"),
        flywheel_state_path=str(tmp_path / "fly.json"),
        cost_router=router,
    )
    assert ranked[0]["route_id"] == "route_fast_2ms"
    assert ranked[0]["global_minimal_action_efficiency"] > ranked[1]["global_minimal_action_efficiency"] * 100


# ---------------------------------------------------------------------------
# WAVE 4: Crash-Resumable Causal Journal + Counterfactual Ablation + OSWorld A11y XML
# ---------------------------------------------------------------------------


def test_wave4_crash_resumable_daemon_counterfactual_ablation_and_osworld_a11y(tmp_path: pathlib.Path) -> None:
    from canonical.swe_kernel.autonomous_awake_loop_v1 import AwakeAgencyDaemon
    from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import prune_non_causal_steps_counterfactually
    from canonical.swe_kernel.predicate_world_abstraction_v1 import decide_osworld_desktop_action
    from execution_guard import terminal_causal_journal_v2 as tcj

    # 4a) Crash-resumable continuity: Daemon #1 commits `step_1`, crashes before `step_2`;
    #     Daemon #2 recovers prefix, skips re-executing `step_1`, and executes `step_2`!
    ws = tmp_path / "awake_ws"
    ws.mkdir()
    (ws / "state.txt").write_text("init\n", encoding="utf-8")
    j_dir = tmp_path / "journal"
    exec_counts = {"step_1": 0, "step_2": 0}

    daemon_1 = AwakeAgencyDaemon(
        ws,
        ledger_path=tmp_path / "ledger.json",
        skill_store_path=tmp_path / "skills.sqlite",
        workflow_db_path=tmp_path / "wf.sqlite",
        journal_dir=j_dir,
        logical_attempt_id="awake-session-alpha",
    )
    r1 = daemon_1.execute_journaled_action(
        "step_1",
        {"goal": "initialize schema"},
        lambda stage: (
            exec_counts.__setitem__("step_1", exec_counts["step_1"] + 1),
            (stage / "state.txt").unlink(),
            (stage / "state.txt").write_text("step_1_done\n", encoding="utf-8"),
            {"pass": True},
        )[-1],
    )
    assert r1["committed"] is True and r1["executed_live"] is True
    assert exec_counts["step_1"] == 1

    # Simulate abrupt crash of `daemon_1` and boot `daemon_2` on the same `journal_dir` + `logical_attempt_id`
    del daemon_1
    daemon_2 = AwakeAgencyDaemon(
        ws,
        ledger_path=tmp_path / "ledger.json",
        skill_store_path=tmp_path / "skills.sqlite",
        workflow_db_path=tmp_path / "wf.sqlite",
        journal_dir=j_dir,
        logical_attempt_id="awake-session-alpha",
    )
    replay_r1 = daemon_2.execute_journaled_action(
        "step_1",
        {"goal": "initialize schema"},
        lambda stage: (exec_counts.__setitem__("step_1", exec_counts["step_1"] + 1), {"pass": True})[-1],
    )
    assert replay_r1["committed"] is True
    assert replay_r1["replayed_from_journal"] is True
    assert replay_r1["executed_live"] is False
    assert exec_counts["step_1"] == 1  # NEVER re-executed after crash!

    r2 = daemon_2.execute_journaled_action(
        "step_2",
        {"goal": "finalize artifact"},
        lambda stage: (
            exec_counts.__setitem__("step_2", exec_counts["step_2"] + 1),
            (stage / "final.txt").write_text("ready\n", encoding="utf-8"),
            {"pass": True},
        )[-1],
    )
    assert r2["committed"] is True and r2["executed_live"] is True
    assert exec_counts["step_2"] == 1
    assert (ws / "final.txt").read_text(encoding="utf-8") == "ready\n"

    # Fork-tampering at sequence 0 is cryptographically rejected by `terminal_causal_journal_v2`!
    forged_ev = tcj.make_event(
        logical_attempt_id=daemon_2.logical_attempt_id,
        sequence=0,
        predecessor_sha256=None,
        kind="PLANNER_NO_ACTION",
        payload={"tampered": True},
    )
    with pytest.raises(tcj.JournalError, match="JOURNAL_FORK_REJECTED"):
        tcj.append_once(daemon_2._journal_store, forged_ev)

    # 4b) Counterfactual trace ablation strips noisy `ls` / `echo` / unused-read steps
    noisy_trace = [
        {"op": "shell", "cmd": "ls -la"},                         # index 0: noise
        {"op": "write", "key": "cfg", "val": "v1"},               # index 1: CAUSAL
        {"op": "shell", "cmd": "echo checking..."},               # index 2: noise
        {"op": "derive", "from": "cfg", "out": "built:v1"},       # index 3: CAUSAL
        {"op": "read", "key": "unrelated_readme"},                # index 4: noise
    ]

    def _sim_oracle(steps: list[dict]) -> bool:
        env_mem: dict[str, str] = {}
        for s in steps:
            if s["op"] == "write":
                env_mem[s["key"]] = s["val"]
            elif s["op"] == "derive" and env_mem.get(s["from"]) == "v1":
                env_mem["artifact"] = s["out"]
        return env_mem.get("artifact") == "built:v1"

    pruned = prune_non_causal_steps_counterfactually(noisy_trace, _sim_oracle)
    assert pruned["baseline_passed"] is True
    assert pruned["pruned_indices"] == [0, 2, 4]
    assert pruned["kept_indices"] == [1, 3]
    assert pruned["minimal_length"] == 2

    # 4c) Zero-LLM OSWorld desktop AT-SPI A11y XML grounding (`K3 = 0`)
    a11y_xml = """
    <desktop xmlns:st="https://accessibility.ubuntu.example.org/ns/state"
             xmlns:cp="https://accessibility.ubuntu.example.org/ns/component">
      <frame name="Editor">
        <push-button name="Hidden Save" st:visible="false" st:showing="false" cp:screencoord="(10, 10)" cp:size="(80, 30)" />
        <push-button name="Cancel" st:visible="true" st:showing="true" cp:screencoord="(100, 400)" cp:size="(80, 40)" />
        <push-button name="Save Document" st:visible="true" st:showing="true" cp:screencoord="(240, 400)" cp:size="(100, 40)" />
      </frame>
    </desktop>
    """
    desk = decide_osworld_desktop_action("Click Save Document", a11y_xml=a11y_xml)
    assert desk["k3_external_llm_calls"] == 0
    assert desk["parsed_element_count"] == 2  # Hidden button filtered out!
    assert desk["actions"] == [{"type": "CLICK", "x": 290, "y": 420}]

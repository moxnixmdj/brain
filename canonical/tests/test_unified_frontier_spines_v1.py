#!/usr/bin/env python3
"""End-to-end real-execution tests for Unified Front-Door Spines `0E`..`0I`.

Covers:
  - `0E` Environment Discovery & C3AL Conflict-Aware Active Automata (including
         refusal-gated actions and mid-session physics drift) + CoalA alphabet
         partitioning + real CLI census + refusal specification + Markdown guide oracle.
  - `0F` Speculative CoW Rollback Sandbox (DeltaBox/TClone isolation & rollback) +
         CoAct-1 Code-over-GUI delegation + Petri dominator cut-vertices + A11y GUI +
         blind RGB pure-pixel canvas differential tomography.
  - `0G` 5-Timescale Verification-First Memory Bus: AMA-Bench lossless bi-temporal
         causal graph, CDCL negative-space nogoods, Sleep-Time E-Stitch/Plotkin-LGG
         consolidation, O(1) exact selective unlearning with zero collateral damage,
         and JSON persistence.
  - `0H` Dual-Channel Goal-Negation Oracle Audit (kills vacuous tests & hardcoded
         cheats) + live Coq `CAD_NURBS_RCF_V1` certificate verification (`99 Qed.`,
         `0 Admitted.`).
  - `0I` BoundaryRouter Tier-0 -> Tier-1 -> Tier-2 (proposer gated by `0H` + CDCL
         nogoods) with automatic crystallization to Tier-0 solving a fresh unseen
         repo with 0 proposer calls.
  - Full `UnifiedModel.load().act_or_learn(...)` front-door dispatch for `0E`..`0I`.
"""
from __future__ import annotations

import pathlib
from typing import Any

from canonical.runtime.brain_unified_model_v1 import open_model
from canonical.swe_kernel import canonical_boundary_router_v1 as br_spine
from canonical.swe_kernel import canonical_cu_sandbox_spine_v1 as cu_spine
from canonical.swe_kernel import canonical_env_discovery_spine_v1 as env_spine
from canonical.swe_kernel import canonical_memory_crystallizer_v1 as mem_spine
from canonical.swe_kernel import canonical_oracle_vericoding_spine_v1 as oracle_spine
from canonical.swe_kernel import interface_action_grammar_v1 as action_grammar


class _DriftingRefusalLockboxEnv:
    """Zero-instruction black-box interactive puzzle with inert decoys, refusal-gated
    actions, AND mid-session physics drift to test C3AL conflict revision + CoalA."""

    actions = ("nop_a", "nop_b", "flip_breaker", "take_key", "unlock_vault", "open_door")

    def __init__(self, *, drift_on_first_goal_hit: bool = True) -> None:
        self.drift_on_first_goal_hit = drift_on_first_goal_hit
        self.drifted = False
        self.goal_hits = 0
        self.reset()

    def reset(self) -> dict[str, Any]:
        self.breaker = False
        self.has_key = False
        self.vault_open = False
        self.door_open = False
        return self._obs()

    def _obs(self) -> dict[str, Any]:
        return {
            "breaker": self.breaker,
            "has_key": self.has_key,
            "vault_open": self.vault_open,
            "door_open": self.door_open,
        }

    def step(self, action: str) -> dict[str, Any]:
        if action in ("nop_a", "nop_b"):
            return {"obs": self._obs(), "refused": False, "done": False}
        if action == "flip_breaker":
            self.breaker = True
            return {"obs": self._obs(), "refused": False, "done": False}
        if action == "take_key":
            if self.drifted and not self.breaker:
                return {
                    "obs": self._obs(),
                    "refused": True,
                    "refusal_text": "error: requires --breaker active before taking key",
                    "done": False,
                }
            self.has_key = True
            return {"obs": self._obs(), "refused": False, "done": False}
        if action == "unlock_vault":
            if not self.has_key:
                return {
                    "obs": self._obs(),
                    "refused": True,
                    "refusal_text": "error: missing required key operand",
                    "done": False,
                }
            self.vault_open = True
            return {"obs": self._obs(), "refused": False, "done": False}
        if action == "open_door":
            if not self.vault_open:
                return {
                    "obs": self._obs(),
                    "refused": True,
                    "refusal_text": "error: vault must be unlocked first",
                    "done": False,
                }
            self.door_open = True
            self.goal_hits += 1
            if self.drift_on_first_goal_hit and self.goal_hits == 1:
                # Physics shift after first discovery! Verification replay will detect conflict.
                self.drifted = True
            return {"obs": self._obs(), "refused": False, "done": True}
        return {"obs": self._obs(), "refused": True, "refusal_text": "unknown action", "done": False}


class _PureRGBButtonCanvasEnv:
    """Minimal pure-pixel 2D RGB canvas (no DOM, no A11y tree) with two colored buttons.
    Clicking button B (green) after button A (red) turns the indicator region gold."""

    def __init__(self) -> None:
        self.armed = False
        self.done = False

    def reset(self) -> list[list[tuple[int, int, int]]]:
        self.armed = False
        self.done = False
        return self.render()

    def render(self) -> list[list[tuple[int, int, int]]]:
        bg = (20, 20, 20)
        grid = [[bg for _ in range(12)] for _ in range(8)]
        # Button A at rows 1..2, cols 1..3
        col_a = (200, 40, 40) if not self.armed else (80, 200, 80)
        for r in range(1, 3):
            for c in range(1, 4):
                grid[r][c] = col_a
        # Button B at rows 1..2, cols 6..8
        col_b = (40, 90, 210) if not self.done else (240, 210, 40)
        for r in range(1, 3):
            for c in range(6, 9):
                grid[r][c] = col_b
        return grid

    def click(self, x: int, y: int) -> list[list[tuple[int, int, int]]]:
        if 1 <= y <= 2 and 1 <= x <= 3:
            self.armed = True
        elif 1 <= y <= 2 and 6 <= x <= 8 and self.armed:
            self.done = True
        return self.render()


def test_01_env_discovery_c3al_unknown_refusal_automaton_and_rule_drift() -> None:
    env = _DriftingRefusalLockboxEnv(drift_on_first_goal_hit=True)
    res = env_spine.discover_environment(
        blackbox_env=env,
        goal_predicate=lambda obs: bool(isinstance(obs, dict) and obs.get("door_open") is True),
        max_states=32,
        max_depth=6,
        max_queries=300,
    )
    assert res["pass"] is True
    auto = res["automaton"]
    assert auto["goal_verified"] is True
    assert auto["conflicts_resolved"] >= 1  # C3AL caught and revised the mid-session physics drift!
    assert auto["goal_prefix"] == ["flip_breaker", "take_key", "unlock_vault", "open_door"]
    assert set(auto["alphabet_partition"]["inert"]) >= {"nop_a", "nop_b"}
    assert len(auto["refusal_axioms"]) >= 2


def test_02_env_discovery_real_cli_census_refusal_spec_and_markdown_guide(tmp_path: pathlib.Path) -> None:
    # Real mini repo with README containing fenced bash/python transcript
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "mini"\nversion = "0.1.0"\n', encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "# Mini\n\n```python\n>>> 2 + 2\n4\n```\n",
        encoding="utf-8",
    )
    res = env_spine.discover_environment(
        repo_root=tmp_path,
        programs=("ls",),
        refusal_texts=(
            "error: option requires an argument -- 'f'",
            "missing file operand",
        ),
        markdown_guide="# Guide\n\n```python\n>>> len('abc')\n3\n```\n",
    )
    assert res["pass"] is True
    assert res["tool_census"]["total_operations"] > 0
    assert res["repo_survey"]["evidence_digest"]
    assert res["markdown_guide_oracle"]["fenced_block_count"] >= 1
    assert any(r["actionable"] for r in res["refusal_specifications"])


def test_03_cu_sandbox_cow_rollback_leaves_workspace_untouched_on_failure(tmp_path: pathlib.Path) -> None:
    (tmp_path / "important.txt").write_text("ORIGINAL_SECRET_STATE\n", encoding="utf-8")
    (tmp_path / "config.ini").write_text("mode=safe\n", encoding="utf-8")
    before_digest, _ = cu_spine.workspace_tree_digest(tmp_path)

    res = cu_spine.execute_speculative_computer_task(
        workspace_root=tmp_path,
        candidates=[
            {
                "id": "malicious_delete",
                "fn": lambda ws: (ws / "important.txt").unlink(),
            },
            {
                "id": "out_of_scope_write",
                "write_files": {"rogue.txt": "hacked"},
            },
            {
                "id": "wrong_value",
                "write_files": {"config.ini": "mode=broken\n"},
            },
        ],
        postcondition=lambda ws: (ws / "config.ini").read_text(encoding="utf-8").strip() == "mode=verified",
        allowed_write_paths=("config.ini",),
        allow_deletions=False,
    )
    assert res["pass"] is False
    cow = res["cow_sandbox_result"]
    assert cow["workspace_preserved_on_failure"] is True
    after_digest, _ = cu_spine.workspace_tree_digest(tmp_path)
    assert after_digest == before_digest
    assert (tmp_path / "important.txt").read_text(encoding="utf-8") == "ORIGINAL_SECRET_STATE\n"
    assert not (tmp_path / "rogue.txt").exists()


def test_04_cu_sandbox_coact1_programmatic_commit_and_petri_cut_vertices(tmp_path: pathlib.Path) -> None:
    (tmp_path / "config.ini").write_text("mode=draft\n", encoding="utf-8")

    res = cu_spine.execute_speculative_computer_task(
        workspace_root=tmp_path,
        candidates=[
            {"id": "bad_cand", "write_files": {"config.ini": "mode=wrong\n"}},
            {"id": "good_cand", "write_files": {"config.ini": "mode=production\n"}},
        ],
        postcondition=lambda ws: (ws / "config.ini").read_text(encoding="utf-8").strip() == "mode=production",
        allowed_write_paths=("config.ini",),
        petri_edges=[("start", "stage1"), ("stage1", "bottleneck"), ("bottleneck", "goal")],
        petri_start="start",
        petri_goal="goal",
    )
    assert res["pass"] is True
    assert res["route_selected"] == "COACT_1_SPECULATIVE_COW_SANDBOX"
    assert res["cow_sandbox_result"]["winner_id"] == "good_cand"
    assert res["cow_sandbox_result"]["committed"] is True
    assert (tmp_path / "config.ini").read_text(encoding="utf-8").strip() == "mode=production"
    assert "bottleneck" in res["petri_cut_vertices"].get("dominators", res["petri_cut_vertices"].get("cut_vertices", []))


def test_05_cu_sandbox_a11y_gui_and_blind_rgb_canvas_tomography() -> None:
    # Route 2: A11y Tree GUI
    env_a11y = action_grammar.A11yEnvironment(
        [
            action_grammar.A11yNode(
                node_id="submit_btn",
                role="button",
                name="Submit Report",
                bounds=(10, 10, 100, 40),
            )
        ],
        submit_effects={"submit_btn": {"banner": "Report submitted"}},
    )
    a11y_res = cu_spine.execute_speculative_computer_task(
        a11y_env=env_a11y,
        gui_instruction="Click Submit Report",
        gui_goal_check=lambda e: e.status_banner == "Report submitted",
    )
    assert a11y_res["pass"] is True
    assert a11y_res["route_selected"] == "A11Y_TREE_GUI_ACTION_GRAMMAR"

    # Route 3: Blind Pure-Pixel RGB Canvas Differential Tomography
    canvas_env = _PureRGBButtonCanvasEnv()
    canvas_res = cu_spine.execute_speculative_computer_task(
        canvas_env=canvas_env,
        canvas_goal_predicate=lambda frame: frame[1][6] == (240, 210, 40),
    )
    assert canvas_res["pass"] is True
    assert canvas_res["route_selected"] == "BLIND_RGB_CANVAS_TOMOGRAPHY"


def test_06_memory_bus_ama_bench_lossless_bitemporal_causal_graph() -> None:
    bus = mem_spine.VerificationFirstMemoryBus()
    # Episode 1 at t=10..11 (later superseded)
    e_old = bus.record_causal_step(
        episode_id="ep_tls_v1",
        step_idx=0,
        pre_state="server_down",
        action="start_tls",
        exact_args={"port": 8080, "cipher": "TLS1.2"},
        effect={"pid": 1001},
        post_state="server_up",
        valid_at=10.0,
    )
    bus.record_causal_step(
        episode_id="ep_tls_v1",
        step_idx=1,
        pre_state="server_up",
        action="healthcheck",
        exact_args={"path": "/healthz", "timeout_ms": 500},
        effect={"status": 200},
        post_state="healthy",
        valid_at=11.0,
    )
    # Historical query at t=15 sees exact port 8080
    hist = bus.query_causal_chain(start_state="server_down", target_state="healthy", at_ts=15.0)
    assert len(hist) == 2
    assert hist[0]["exact_args"] == {"port": 8080, "cipher": "TLS1.2"}
    assert hist[1]["exact_args"] == {"path": "/healthz", "timeout_ms": 500}

    # Invalidate old edge at t=20 and record updated policy at t=25
    assert bus.invalidate_causal_edge(e_old.edge_id, reason="TLS1.3_UPGRADE", at_ts=20.0) is True
    bus.record_causal_step(
        episode_id="ep_tls_v2",
        step_idx=0,
        pre_state="server_down",
        action="start_tls",
        exact_args={"port": 8443, "cipher": "TLS1.3", "strict": True},
        effect={"pid": 2002},
        post_state="server_up",
        valid_at=25.0,
    )
    # Current-time query returns ONLY lossless TLS 1.3 chain, never stale port 8080
    curr = bus.query_causal_chain(start_state="server_down", target_state="healthy")
    assert len(curr) == 2
    assert curr[0]["exact_args"] == {"port": 8443, "cipher": "TLS1.3", "strict": True}


def test_07_memory_bus_cdcl_negative_space_pruning_and_retraction() -> None:
    bus = mem_spine.VerificationFirstMemoryBus()
    cl = bus.record_conflict("return 42", reason="HARDCODED_CONSTANT", domain="swe_py", context_sig="calc.py")
    survivors = bus.prune_candidates(["return 42", "return x + 1"], domain="swe_py", context_sig="calc.py")
    assert survivors == ["return x + 1"]
    assert bus.retract_conflict(cl.clause_id, reason="SPEC_REVISED") is True
    assert bus.prune_candidates(["return 42", "return x + 1"], domain="swe_py", context_sig="calc.py") == [
        "return 42",
        "return x + 1",
    ]


def test_08_memory_bus_sleep_estitch_crystallization_and_o1_selective_forgetting(tmp_path: pathlib.Path) -> None:
    bus = mem_spine.VerificationFirstMemoryBus()
    sk_a = bus.crystallize_code_repair(
        before_source="def check_limit(v, hi):\n    return v < hi\n",
        after_source="def check_limit(v, hi):\n    return v <= hi\n",
        trigger_key="boundary_cmp",
        provenance_episode_id="ep_a",
    )
    sk_b = bus.crystallize_code_repair(
        before_source="def norm(s):\n    return s.strip().lower()\n",
        after_source="def norm(s):\n    return s.strip().lower().replace('_', '-')\n",
        trigger_key="string_norm",
        provenance_episode_id="ep_b",
    )
    bus.crystallize_action_macro(trigger_key="macro_keep", actions=["a", "b"], provenance_episode_id="ep_keep")

    sleep_res = bus.sleep_consolidate(
        program_sources=[
            "def f1(x, y):\n    return (x + y) * 2\n",
            "def f2(a, b):\n    return (a + b) * 2\n",
        ]
    )
    assert sleep_res["egraph_engine_ready"] is True
    assert sleep_res["active_skill_count"] >= 3

    # O(1) Selective Unlearning of sk_a: 0% leakage for sk_a, 100% retention for sk_b & macro_keep!
    assert bus.forget_skill(sk_a.skill_id, reason="MEMORY_AGENT_BENCH_UNLEARN") is True
    assert bus.lookup_tier0_skills("boundary_cmp") == []
    assert len(bus.lookup_tier0_skills("string_norm")) == 1
    assert bus.lookup_tier0_skills("string_norm")[0]["skill_id"] == sk_b.skill_id
    assert len(bus.lookup_tier0_skills("macro_keep")) == 1

    # Persistence round-trip
    state_file = tmp_path / "memory_bus.json"
    bus.save(state_file)
    reloaded = mem_spine.VerificationFirstMemoryBus(state_path=state_file)
    assert reloaded.lookup_tier0_skills("boundary_cmp") == []
    assert len(reloaded.lookup_tier0_skills("string_norm")) == 1
    assert reloaded.stats()["t3_forgotten_skills"] >= 1


def test_09_oracle_vericoding_dual_channel_rejects_vacuous_test_and_hardcoding(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    before_src = "def score(a, b):\n    return a - b\n"
    true_fix = "def score(a, b):\n    return a + b\n"
    hardcoded_cheat = "def score(a, b):\n    return 5\n"

    (repo / "calc.py").write_text(before_src, encoding="utf-8")
    (repo / "test_real.py").write_text(
        "from calc import score\n\ndef test_score():\n    assert score(2, 3) == 5\n    assert score(10, 4) == 14\n",
        encoding="utf-8",
    )
    (repo / "test_single.py").write_text(
        "from calc import score\n\ndef test_score():\n    assert score(2, 3) == 5\n",
        encoding="utf-8",
    )
    (repo / "test_vacuous.py").write_text(
        "def test_always_true():\n    assert True\n",
        encoding="utf-8",
    )

    # 1. Real fix + real test PASSES all 3 channels (including goal-negation mutant kills!)
    good = oracle_spine.audit_patch_and_oracle(
        repo,
        target_rel="calc.py",
        before_source=before_src,
        after_source=true_fix,
        test_file="test_real.py",
    )
    assert good["pass"] is True
    assert good["channels"]["goal_negation_mutants_killed"] >= 1

    # 2. Vacuous test (`assert True`) REJECTED!
    vac = oracle_spine.audit_patch_and_oracle(
        repo,
        target_rel="calc.py",
        before_source=before_src,
        after_source=true_fix,
        test_file="test_vacuous.py",
    )
    assert vac["pass"] is False
    assert any("VACUOUS_ORACLE" in r or "BEFORE_ALREADY_PASSED" in r for r in vac["reasons"])

    # 3. Hardcoded constant cheat (`return 5`) REJECTED by input-dependency gate!
    cheat = oracle_spine.audit_patch_and_oracle(
        repo,
        target_rel="calc.py",
        before_source=before_src,
        after_source=hardcoded_cheat,
        test_file="test_single.py",
    )
    assert cheat["pass"] is False
    assert any("INPUT_DEPENDENCY_GATE_REJECTED" in r for r in cheat["reasons"])


def test_10_oracle_vericoding_coq_certificate_bundle_99_qed_zero_admitted() -> None:
    res = oracle_spine.audit_oracle_and_vericoding(verify_default_coq=True)
    assert res["pass"] is True
    coq = res["coq_certificate_audit"]
    assert coq["file_count"] == 14
    assert coq["qed_count"] == 99
    assert coq["admitted_count"] == 0


def test_11_boundary_router_tier2_proposer_gated_by_0h_crystallizes_to_tier0(tmp_path: pathlib.Path) -> None:
    router = br_spine.BoundaryRouter()

    # Repo 1: domain-specific business code transformation outside generic zero-model mutations
    repo1 = tmp_path / "repo1"
    repo1.mkdir()
    (repo1 / "invoice.py").write_text(
        "def format_tax_id(code):\n    return code.strip().upper()\n",
        encoding="utf-8",
    )
    (repo1 / "test_invoice.py").write_text(
        "from invoice import format_tax_id\n\n"
        "def test_tax_id():\n"
        "    assert format_tax_id(' de123 ') == 'EU2026:DE123'\n"
        "    assert format_tax_id('fr999') == 'EU2026:FR999'\n",
        encoding="utf-8",
    )

    def _proposer(_ctx: dict[str, Any]) -> list[str]:
        return [
            # Proposal 0: hardcoded constant cheat -> MUST BE REJECTED by `0H` + compiled to CDCL nogood!
            "def format_tax_id(code):\n    return 'EU2026:DE123'\n",
            # Proposal 1: genuine fix -> MUST PASS `0H` + crystallize into Tier 0!
            "def format_tax_id(code):\n    return 'EU2026:' + code.strip().upper()\n",
        ]

    res1 = router.route_swe_repair(
        repo1,
        target_rel="invoice.py",
        test_file="test_invoice.py",
        cluster="eu_tax_prefix",
        untrusted_proposer=_proposer,
    )
    assert res1["pass"] is True
    assert res1["tier_used"] == "TIER_2_PROPOSER_VERIFIED"
    assert res1["proposer_calls"] == 1
    assert len(res1["rejected_proposals"]) == 1  # cheat rejected & logged to CDCL negative space!
    assert router.memory_bus.stats()["t2_active_conflict_clauses"] >= 1
    assert router.memory_bus.stats()["t3_active_skills"] >= 1

    # Repo 2: brand-new unseen repo with a DIFFERENT function & variable name, NO proposer allowed!
    repo2 = tmp_path / "repo2"
    repo2.mkdir()
    (repo2 / "ledger.py").write_text(
        "def normalize_vat(raw):\n    return raw.strip().upper()\n",
        encoding="utf-8",
    )
    (repo2 / "test_ledger.py").write_text(
        "from ledger import normalize_vat\n\n"
        "def test_vat():\n"
        "    assert normalize_vat(' nl777 ') == 'EU2026:NL777'\n"
        "    assert normalize_vat('es404') == 'EU2026:ES404'\n",
        encoding="utf-8",
    )

    res2 = router.route_swe_repair(
        repo2,
        target_rel="ledger.py",
        test_file="test_ledger.py",
        cluster="eu_tax_prefix",
        untrusted_proposer=None,  # ZERO proposer calls permitted!
    )
    assert res2["pass"] is True
    assert res2["tier_used"] == "TIER_0_CRYSTALLIZED_REFLEX"
    assert res2["proposer_calls"] == 0
    assert "EU2026:" in (repo2 / "ledger.py").read_text(encoding="utf-8")


def test_12_unified_model_front_door_wires_all_spines_0d_through_0i(tmp_path: pathlib.Path) -> None:
    model = open_model()

    # 0E via UnifiedModel.act_or_learn
    env = _DriftingRefusalLockboxEnv(drift_on_first_goal_hit=False)
    out_0e = model.act_or_learn(
        "discover unknown lockbox environment",
        inputs={
            "env_discovery_task": {
                "blackbox_env": env,
                "goal_predicate": lambda obs: bool(obs.get("door_open")),
            }
        },
    )
    assert out_0e["pass"] is True
    assert out_0e["operation"] == "DISCOVER_ENVIRONMENT"
    assert out_0e["credit"]["capability_credit_delta"] == 0

    # 0F via UnifiedModel.act_or_learn
    ws = tmp_path / "ws_0f"
    ws.mkdir()
    (ws / "out.txt").write_text("init\n", encoding="utf-8")
    out_0f = model.act_or_learn(
        "speculatively update out.txt",
        inputs={
            "cu_sandbox_task": {
                "workspace_root": ws,
                "candidates": [{"id": "ok", "write_files": {"out.txt": "verified\n"}}],
                "postcondition": lambda p: (p / "out.txt").read_text(encoding="utf-8").strip() == "verified",
                "allowed_write_paths": ("out.txt",),
            }
        },
    )
    assert out_0f["pass"] is True
    assert out_0f["operation"] == "EXECUTE_SPECULATIVE_CU"

    # 0G via UnifiedModel.act_or_learn
    out_0g = model.act_or_learn(
        "crystallize verified macro",
        inputs={
            "memory_bus_op": {
                "operation": "CRYSTALLIZE_MACRO",
                "payload": {
                    "trigger_key": "lockbox_demo",
                    "actions": ["take_key", "unlock_vault", "open_door"],
                    "provenance_episode_id": "ep_front_door",
                },
            }
        },
    )
    assert out_0g["pass"] is True
    out_0g_hit = model.memory_operation("LOOKUP_TIER0", payload={"trigger_key": "lockbox_demo"})
    assert out_0g_hit["pass"] is True

    # 0H via UnifiedModel.act_or_learn
    out_0h = model.act_or_learn(
        "audit Coq formal proof certificates",
        inputs={"oracle_vericoding_task": {"verify_default_coq": True}},
    )
    assert out_0h["pass"] is True
    assert out_0h["oracle_vericoding"]["coq_certificate_audit"]["qed_count"] == 99

    # 0I via UnifiedModel.act_or_learn (env_goal -> Tier 1 learn -> Tier 0 replay!)
    env_br = _DriftingRefusalLockboxEnv(drift_on_first_goal_hit=False)
    out_0i_first = model.act_or_learn(
        "route unknown lockbox via boundary router",
        inputs={
            "boundary_route_task": {
                "kind": "env_goal",
                "blackbox_env": env_br,
                "goal_predicate": lambda obs: bool(obs.get("door_open")),
                "trigger_key": "lockbox_br_goal",
            }
        },
    )
    assert out_0i_first["pass"] is True
    assert out_0i_first["boundary_route"]["tier_used"] == "TIER_1_ENV_C3AL"

    out_0i_second = model.route_with_boundary(
        "env_goal",
        blackbox_env=env_br,
        goal_predicate=lambda obs: bool(obs.get("door_open")),
        trigger_key="lockbox_br_goal",
    )
    assert out_0i_second["pass"] is True
    assert out_0i_second["boundary_route"]["tier_used"] == "TIER_0_CRYSTALLIZED_REFLEX"
    assert out_0i_second["boundary_route"]["queries_executed"] == 3  # instant 3-step replay, 0 exploration!

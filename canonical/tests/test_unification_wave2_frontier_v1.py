#!/usr/bin/env python3
"""Unification Wave 2 Frontier Verification Suite.

End-to-end real-execution tests proving that the previously disconnected hidden
engines are unified live across BOTH:
  - Unified Model (`canonical/runtime/brain_unified_model_v1.py`)
  - Unified Runtime (`canonical/runtime/creature_runtime_v1.py`)
  - Canonical Frontier Spines (`0D`, `0E`, `0G`, `0H`, `0I`)

Covers the exact 2026 frontier failure modes:
  1. SkillEvolBench selective procedural abstraction (Version-Space + Abstain on shift)
  2. Lossless trace-quotient & exact hidden-precondition induction
  3. Semi-Persistent E-Graph (`guarded_meaning_ir_v1`) anti-unification & sleep compression
  4. STING / Terminal-Bench 4.0 anti-vacuity falsification proofs (`verifier_falsification_v1`)
  5. Instruction contract compilation & failing-run AST demand extraction
  6. Error-aware Register-Automaton learning (`SL^lambda_=` / `AL#`) zero-shot transfer to unseen nonces
  7. Key-table splitting (`the_guide_is_a_key_table_v1`), cross-machine frames & aimed geometric actions
  8. Typed multi-step capability chaining (`composer_route_v1`) + Tier-0 recall
  9. Harvested surface execution (`harvested_capability_runtime_v1`) preserving `admitted: False`
 10. UnifiedModel <-> Creature shared persistent `memory_bus_v1.json` across crash/restart
 11. Creature `sovereign_perform` executing real SWE repair & typed chain via unified spines
 12. SWE-Milestone continuous multi-commit invariant preservation via `BoundaryRouter`
 13. Live AST/import wiring check proving the Unified Model <-> Unified Runtime split is closed
"""
from __future__ import annotations

import pathlib
from typing import Any

import pytest

from canonical.runtime import brain_unified_model_v1 as bum
from canonical.runtime import creature_runtime_v1 as creature_rt
from canonical.runtime import self_authored_obligations_v1 as A
from canonical.swe_kernel import canonical_boundary_router_v1 as br_spine
from canonical.swe_kernel import canonical_env_discovery_spine_v1 as env_spine
from canonical.swe_kernel import canonical_memory_crystallizer_v1 as mem_spine
from canonical.swe_kernel import canonical_oracle_vericoding_spine_v1 as oracle_spine
from canonical.tools import the_frame_crosses_the_machine_v1 as cross_frame

ROOT = pathlib.Path(__file__).resolve().parents[2]


class _DynamicTokenLockEnv:
    """Real stateful black-box protocol with a brand-new unseen nonce token on every reset."""

    def __init__(self) -> None:
        self._episode = 0
        self._issued_token: str | None = None
        self._unlocked = False
        self._claimed = False
        self.forced_next_token: str | None = None

    def reset(self) -> dict[str, Any]:
        self._episode += 1
        self._issued_token = None
        self._unlocked = False
        self._claimed = False
        return {"state": "LOCKED", "registers": {}}

    def step(self, action: str, arg: Any = None) -> dict[str, Any]:
        if action == "issue":
            tok = self.forced_next_token or f"tok_ep_{self._episode}"
            self.forced_next_token = None
            self._issued_token = tok
            return {
                "obs": {"state": "TOKEN_ISSUED", "registers": {"token": tok}},
                "refused": False,
            }
        if action == "unlock":
            if self._issued_token is None:
                return {
                    "obs": {"state": "LOCKED", "registers": {}},
                    "refused": True,
                    "refusal": "error: token not issued yet; run issue first",
                }
            if arg != self._issued_token:
                return {
                    "obs": {"state": "TOKEN_ISSUED", "registers": {"token": self._issued_token}},
                    "refused": True,
                    "refusal": "error: invalid token argument; expected matching issued token",
                }
            self._unlocked = True
            return {
                "obs": {"state": "UNLOCKED", "registers": {"token": self._issued_token}},
                "refused": False,
            }
        if action == "claim":
            if not self._unlocked:
                return {
                    "obs": {"state": "TOKEN_ISSUED" if self._issued_token else "LOCKED",
                            "registers": {"token": self._issued_token} if self._issued_token else {}},
                    "refused": True,
                    "refusal": "error: vault is locked; unlock before claim",
                }
            self._claimed = True
            return {
                "obs": {"state": "CLAIMED_GOAL", "registers": {"token": self._issued_token}},
                "refused": False,
            }
        return {"obs": {"state": "LOCKED", "registers": {}}, "refused": True, "refusal": "unknown action"}


def _make_button_obs(utterance: str, labels: list[str]) -> dict[str, Any]:
    return {
        "utterance": utterance,
        "elements": [
            {"id": idx, "tag": "button", "text": lbl, "parent": -1, "can_click": True}
            for idx, lbl in enumerate(labels)
        ],
    }


def test_01_skillevolbench_version_space_abstain_then_act_on_shift() -> None:
    """After 1 demo, shifted layout causes genuine hypothesis disagreement -> ABSTAIN;
    after 2nd discriminating demo, version space converges -> verified ACT on unseen label.
    """
    bus = mem_spine.VerificationFirstMemoryBus()
    router = br_spine.BoundaryRouter(memory_bus=bus)

    obs_demo1 = _make_button_obs('Click the "Submit" button', ["Cancel", "Submit"])
    obs_demo2 = _make_button_obs('Click the "Save" button', ["Save", "Cancel"])
    obs_shifted = _make_button_obs('Click the "Continue" button', ["Continue", "Back"])

    # 1 demo leaves positional (index 1) vs quoted-text hypotheses disagreeing -> MUST ABSTAIN
    r1 = router.route_version_space_task(
        "click_named_btn",
        obs_shifted,
        training_traces=[[(obs_demo1, "click@1")]],
        abstain_on_disagreement=True,
    )
    assert r1["decision"] == "ABSTAIN"
    assert r1["action"] is None
    assert r1["reason"] == "VERSION_SPACE_DISAGREEMENT__PROBE_OR_DEMO_NEEDED"
    assert int(r1["disagreement"]["distinct_actions"]) == 2
    assert r1["disagreement"]["guaranteed_discrimination"] is True

    # 2nd demo eliminates positional hypothesis -> version space agrees and acts on unseen "Continue"
    r2 = router.route_version_space_task(
        "click_named_btn",
        obs_shifted,
        training_traces=[[(obs_demo2, "click@0")]],
        abstain_on_disagreement=True,
    )
    assert r2["pass"] is True
    assert r2["decision"] == "ACT"
    assert r2["action"] == "click@0"
    assert int(r2["disagreement"]["distinct_actions"]) == 1
    assert r2["contract_check"]["check"]["verdict"] == "PASS"


def test_02_trace_quotient_and_exact_precondition_induction() -> None:
    bus = mem_spine.VerificationFirstMemoryBus()
    traces = [
        ((("status", "init"), ("noise", "a")), (("status", "done"), ("noise", "b"))),
        ((("status", "init"), ("noise", "c")), (("status", "done"), ("noise", "d"))),
        ((("status", "init"), ("noise", "a")), (("status", "fail"), ("noise", "b"))),
    ]
    q_res = mem_spine.execute_memory_operation(
        bus,
        "INDUCE_TRACE_QUOTIENT",
        {"traces": traces, "labels": [True, True, False], "max_size": 2},
    )
    assert q_res["pass"] is True
    assert q_res["sufficient_count"] > 0
    assert q_res["smallest_quotient"]["sufficient"] is True
    assert q_res["smallest_quotient"]["collisions"] == 0

    pre_res = mem_spine.execute_memory_operation(
        bus,
        "INDUCE_PRECONDITION",
        {
            "table": [
                (["has_key", "door_closed"], True),
                (["has_key", "door_closed", "rained"], True),
                (["door_closed"], False),
                (["has_key"], False),
            ],
            "vocabulary": ["has_key", "door_closed", "rained"],
        },
    )
    assert pre_res["pass"] is True
    assert sorted(pre_res["precondition"]) == ["door_closed", "has_key"]


def test_03_semi_persistent_egraph_anti_unification_and_sleep_compression() -> None:
    bus = mem_spine.VerificationFirstMemoryBus()
    eq_res = mem_spine.execute_memory_operation(
        bus,
        "EGRAPH_ANTI_UNIFY",
        {"source_a": "def f(x):\n    return x + 0\n", "source_b": "def g(x):\n    return x\n"},
    )
    assert eq_res["pass"] is True
    assert eq_res["semantically_equal"] is True

    au_res = bus.egraph_anti_unify_and_compress(
        "def f(x):\n    return x + 1\n",
        "def g(y):\n    return y + 1\n",
    )
    assert au_res["pass"] is True
    assert au_res["semantically_equal"] is False
    assert au_res["hole_count"] >= 1
    assert "hole" in au_res["schema_repr"]

    sleep_res = bus.sleep_consolidate(
        program_sources=[
            "def f(x):\n    return (x + 1) * 2\n",
            "def g(y):\n    return (y + 1) * 2\n",
        ]
    )
    assert sleep_res["mir_modules_lowered"] == 2
    assert sleep_res["semi_egraph_nodes"] > 0


def test_04_verifier_falsification_catches_sting_vacuous_oracles() -> None:
    # Real discriminating verifier MUST PASS falsification proof
    good = oracle_spine.audit_oracle_and_vericoding(
        falsification_spec={
            "verifier_name": "even_positive_checker",
            "predicate": lambda n: isinstance(n, int) and n > 0 and n % 2 == 0,
            "positive_examples": [2, 4, 18],
            "negative_mutants": [0, -4, 3, "2"],
        }
    )
    assert good["pass"] is True
    vf = good["verifier_falsification"]
    assert vf["falsifiable"] is True
    assert vf["mutation_kill_rate"] == 1.0
    assert vf["surviving_mutants"] == []

    # Vacuous STING-style oracle (`lambda _: True`) MUST FAIL CLOSED
    vacuous = oracle_spine.prove_verifier_can_say_no(
        lambda _x: True,
        positive_examples=[2, 4],
        negative_mutants=[-1, 3],
        verifier_name="vacuous_rubber_stamp",
    )
    assert vacuous["pass"] is False
    assert vacuous["falsifiable"] is False
    assert vacuous["surviving_mutants"] == [0, 1]
    assert vacuous["mutation_kill_rate"] == 0.0


def test_05_instruction_contract_and_failing_run_demand_extraction() -> None:
    obs = _make_button_obs("Click the Submit button", ["Cancel", "Submit"])
    good = oracle_spine.audit_oracle_and_vericoding(
        instruction_utterance="Click the Submit button",
        instruction_observation=obs,
        instruction_trace=[(obs, "click@1")],
        failing_source="def clamp(x, lo, hi):\n    if x < lo:\n        return lo\n    return x\n",
    )
    assert good["pass"] is True
    assert good["instruction_contract"]["check"]["verdict"] == "PASS"
    assert good["failing_run_demands"]["site_count"] >= 3
    assert any(s["text"] == "x < lo" for s in good["failing_run_demands"]["sites"])

    bad = oracle_spine.compile_and_check_instruction_contract(
        "Click the Submit button",
        obs,
        trace=[(obs, "click@0")],
    )
    assert bad["pass"] is False
    assert bad["check"]["verdict"] == "FAIL"


def test_06_register_guard_automaton_transfers_zero_shot_to_unseen_tokens() -> None:
    env = _DynamicTokenLockEnv()
    router = br_spine.BoundaryRouter()

    # Tier-1 discovery learns register-guarded symbolic plan despite dynamic tokens + refusals
    r1 = router.route_register_env_goal(
        env,
        actions=["issue", "unlock", "claim"],
        parameterized_actions=["unlock"],
        goal_predicate=lambda obs: isinstance(obs, dict) and obs.get("state") == "CLAIMED_GOAL",
        trigger_key="vault_token_protocol",
    )
    assert r1["pass"] is True
    assert r1["tier_used"] == "TIER_1_REGISTER_AUTOMATON"
    assert r1["symbolic_plan"] == [["issue", "NONE"], ["unlock", "EQ:token"], ["claim", "NONE"]]
    assert len(r1["register_automaton"]["refusal_guards"]) >= 1

    # Brand-new unseen nonce token -> Tier-0 symbolic replay succeeds in 3 exact steps with ZERO search
    env.forced_next_token = "tok_unseen_99999_xyz"
    r2 = router.route_register_env_goal(
        env,
        actions=["issue", "unlock", "claim"],
        parameterized_actions=["unlock"],
        goal_predicate=lambda obs: isinstance(obs, dict) and obs.get("state") == "CLAIMED_GOAL",
        trigger_key="vault_token_protocol",
    )
    assert r2["pass"] is True
    assert r2["tier_used"] == "TIER_0_CRYSTALLIZED_REFLEX"
    assert r2["replay"]["registers"]["token"] == "tok_unseen_99999_xyz"
    assert len(r2["replay"]["executed"]) == 3


def test_07_key_table_splitting_cross_machine_frame_and_aimed_actions() -> None:
    obs_mid = {
        "utterance": "click on the mid-point between the two points",
        "elements": [
            {"index": 0, "tag": "circle", "box": [10, 20, 10, 10]},
            {"index": 1, "tag": "circle", "box": [110, 20, 10, 10]},
        ],
    }
    state0 = [("file:a.txt", "open"), ("file:b.txt", "closed")]
    goal_obj = cross_frame.Goal(
        machine="m1",
        name="open_a",
        frame=("file:a.txt", "open"),
        slot=None,
        value=True,
        atom="open",
    )
    disc = env_spine.discover_environment(
        aimed_observation=obs_mid,
        key_table_readings={},
        cross_machine_spec={
            "state": state0,
            "goal": goal_obj,
            "runs": [state0, [("file:b.txt", "closed")]],
        },
    )
    assert disc["pass"] is True
    assert disc["aimed_actions"]["actions"] == ["pressat@65.0,25.0"]
    assert disc["key_table_split"]["next_channel"] == "batch"
    assert disc["key_table_split"]["surviving_count"] >= 2
    assert disc["cross_machine_frame"]["surviving_count"] >= 1


def test_08_composer_route_typed_chain_and_tier0_crystallization() -> None:
    model = bum.open_model()
    r1 = model.compose_chain("count lines in README.md")
    assert r1["pass"] is True
    assert r1["typed_chain"]["tier_used"] == "TIER_1_COMPOSER_ROUTE"
    assert len(r1["typed_chain"]["chain"]) >= 1

    # Second identical goal hits Tier-0 crystallized chain immediately
    r2 = model.compose_chain("count lines in README.md")
    assert r2["pass"] is True
    assert r2["typed_chain"]["tier_used"] == "TIER_0_CRYSTALLIZED_REFLEX"
    assert r2["typed_chain"]["chain"] == r1["typed_chain"]["chain"]


def test_09_harvested_surface_execution_through_unified_model_never_claims_admission() -> None:
    model = bum.open_model()
    surfaces = model.harvested_surfaces()
    assert len(surfaces) > 100

    # Positive dry-run (receipt=False): runs a real discovered contract surface, NEVER claims admission
    target_cid = "canonical.runtime.bound_capabilities.code_multilanguage_tree_sitter_v1.hidden.v1"
    r_ok = model.execute_harvested_surface(target_cid, args={}, receipt=False)
    assert r_ok["pass"] is True
    assert r_ok["admitted"] is False
    assert r_ok["admission"] == "NOT_ADMITTED"
    assert r_ok["harvested_execution"]["admitted"] is False
    assert r_ok["harvested_execution"]["harvested_result"]["executed"] is True

    # Negative control: unknown surface fails closed
    r_bad = model.execute_harvested_surface("canonical.nonexistent.surface.hidden.v1", receipt=False)
    assert r_bad["pass"] is False
    assert r_bad["admitted"] is False


def test_10_unified_model_creature_runtime_shared_memory_and_crash_restart_persistence(
    tmp_path: pathlib.Path,
) -> None:
    model = bum.open_model()
    state_dir = tmp_path / "creature_body"
    c1 = model.open_creature(state_dir, identity="wave2-creature", life=25.0)
    assert c1.memory_bus is model.memory_bus
    assert c1.boundary_router is model.boundary_router

    # Induce a version-space skill + typed chain + sleep consolidation through the Creature
    obs1 = _make_button_obs('Click the "Submit" button', ["Cancel", "Submit"])
    obs2 = _make_button_obs('Click the "Save" button', ["Save", "Cancel"])
    c1.memory_bus.induce_version_space_skill("btn_task", [[(obs1, "click@1")], [(obs2, "click@0")]])
    ch = c1.compose_typed_chain("count lines in README.md")
    assert ch["pass"] is True
    consol = c1.sleep_consolidate_memory(
        program_sources=["def a(x):\n    return x + 1\n", "def b(y):\n    return y + 1\n"]
    )
    assert consol["version_space_tasks"] == 1
    assert (state_dir / "memory_bus_v1.json").is_file()

    # Simulate process kill -> fresh Creature instance boots from disk alone
    del c1
    c2 = creature_rt.Creature(identity="wave2-creature", root=state_dir, life_grant=25.0)
    boot_info = c2.boot()
    assert boot_info["resumed"] is True
    obs_unseen = _make_button_obs('Click the "Proceed" button', ["Proceed", "Back"])
    q = c2.memory_bus.query_version_space_or_abstain(obs_unseen, task_id="btn_task")
    assert q["decision"] == "ACT"
    assert q["action"] == "click@0"
    assert c2.memory_bus.stats()["t1_active_causal_edges"] >= 1


def test_11_creature_sovereign_perform_dispatches_unified_spines_end_to_end(
    tmp_path: pathlib.Path,
) -> None:
    # Build a real temporary buggy Python repo
    repo = tmp_path / "buggy_repo"
    repo.mkdir()
    (repo / "math_ops.py").write_text(
        "def add_bonus(a, b):\n    return a - b\n",
        encoding="utf-8",
    )
    (repo / "test_math_ops.py").write_text(
        "from math_ops import add_bonus\n\n"
        "def test_add_bonus():\n"
        "    assert add_bonus(3, 4) == 7\n"
        "    assert add_bonus(10, 5) == 15\n",
        encoding="utf-8",
    )

    state_dir = tmp_path / "creature_swe"
    c = creature_rt.Creature(identity="swe-creature", root=state_dir, life_grant=30.0)
    c.boot()
    c.register_spine_task(
        "fix_math_ops",
        "swe_repair",
        {
            "repo_root": str(repo),
            "target_rel": "math_ops.py",
            "test_file": "test_math_ops.py",
            "cluster": "arith_ops",
        },
    )
    spec = {
        "kind": "slot_equals",
        "namespace": "swe",
        "key": "math_ops_status",
        "expected": "PASS_VERIFIED",
    }
    c.author_board(
        [
            A.Proposal(
                id="fix_math_ops",
                claim="repair add_bonus arithmetic sign defect in math_ops.py",
                source="pytest:test_math_ops.py",
                check=A.compile_predicate_spec(spec),
                predicate_spec=spec,
                value=5.0,
                cost=1.0,
                checkable=True,
            )
        ],
        before={"swe": {"math_ops_status": "FAILING"}},
        done={"swe": {"math_ops_status": "PASS_VERIFIED"}},
    )
    run_rep = c.run(cycles=1, perform=creature_rt.sovereign_perform)
    assert run_rep["closed"] == 1
    assert run_rep["steps"][0]["ok"] is True
    assert "a + b" in (repo / "math_ops.py").read_text(encoding="utf-8")
    assert (state_dir / "memory_bus_v1.json").is_file()
    assert c.memory_bus.stats()["t3_active_skills"] >= 1


def test_12_swe_milestone_continuous_multi_commit_invariant_preservation(
    tmp_path: pathlib.Path,
) -> None:
    """Two-milestone SWE-Milestone evolution: Milestone 2 repair preserves Milestone 1 invariants."""
    repo = tmp_path / "milestone_repo"
    repo.mkdir()
    (repo / "calc.py").write_text(
        "def sum_pair(x, y):\n"
        "    return x - y\n",
        encoding="utf-8",
    )
    (repo / "test_m1.py").write_text(
        "from calc import sum_pair\n\n"
        "def test_m1_sum():\n"
        "    assert sum_pair(4, 9) == 13\n"
        "    assert sum_pair(2, 5) == 7\n",
        encoding="utf-8",
    )
    router = br_spine.BoundaryRouter()

    # Milestone 1: Tier-1 repairs sum_pair and verifies via 0H
    m1 = router.route_swe_repair(
        repo,
        target_rel="calc.py",
        test_file="test_m1.py",
        cluster="milestone_arith",
    )
    assert m1["pass"] is True

    # Milestone 2: Add new feature with bug while keeping test_m1.py as non-regression guard
    (repo / "calc.py").write_text(
        (repo / "calc.py").read_text(encoding="utf-8")
        + "\ndef is_positive(n):\n    return n < 0\n",
        encoding="utf-8",
    )
    (repo / "test_m2.py").write_text(
        "from calc import sum_pair, is_positive\n\n"
        "def test_m2_positive_and_m1_invariant():\n"
        "    assert sum_pair(6, 7) == 13\n"
        "    assert is_positive(5) is True\n"
        "    assert is_positive(-2) is False\n",
        encoding="utf-8",
    )
    m2 = router.route_swe_repair(
        repo,
        target_rel="calc.py",
        test_file="test_m2.py",
        regression_tests=["test_m1.py"],
        cluster="milestone_cmp",
    )
    assert m2["pass"] is True
    final_src = (repo / "calc.py").read_text(encoding="utf-8")
    assert "x + y" in final_src
    assert "n > 0" in final_src


def test_13_ast_wiring_verification_unified_model_and_creature_runtime() -> None:
    model = bum.open_model()
    st = model.status()
    bridge = st["unified_runtime_bridge"]
    assert bridge["creature_runtime"] == "canonical/runtime/creature_runtime_v1.py"
    assert bridge["harvested_runtime"] == "canonical/runtime/harvested_capability_runtime_v1.py"
    assert bridge["composer_route"] == "canonical/runtime/composer_route_v1.py"
    assert bridge["spines"] == ["0D", "0E", "0F", "0G", "0H", "0I"]

    bum_src = (ROOT / "canonical/runtime/brain_unified_model_v1.py").read_text(encoding="utf-8")
    cr_src = (ROOT / "canonical/runtime/creature_runtime_v1.py").read_text(encoding="utf-8")
    assert "creature_runtime_v1" in bum_src
    assert "canonical_boundary_router_v1" in cr_src
    assert "canonical_memory_crystallizer_v1" in cr_src
    assert "canonical_swe_spine_v1" in cr_src
    assert "harvested_capability_runtime_v1" in cr_src
    assert "composer_route_v1" in (ROOT / "canonical/swe_kernel/canonical_boundary_router_v1.py").read_text(encoding="utf-8")

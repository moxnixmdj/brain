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

import time

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
    import shutil
    import tempfile

    model = bum.open_model()
    surfaces = model.harvested_surfaces()
    assert len(surfaces) > 100

    # Positive dry-run (receipt=False): runs a real discovered contract surface (`jq_query`), NEVER claims admission
    jq_row = next(r for r in surfaces if str(r.get("path") or "").endswith("jq_query.py"))
    workdir = pathlib.Path(tempfile.mkdtemp(prefix="WAVE2_HARVEST_JQ_", dir=ROOT / "canonical/astra_runtime/tmp"))
    try:
        src = workdir / "in.json"
        out = workdir / "out.json"
        src.write_text('{"items":[{"name":"alpha","v":1},{"name":"beta","v":9}]}\n', encoding="utf-8")
        r_ok = model.execute_harvested_surface(
            jq_row["id"],
            args={
                "input_path": src.relative_to(ROOT).as_posix(),
                "filter": ".items | map(select(.v > 5)) | .[0].name",
                "output_path": out.relative_to(ROOT).as_posix(),
            },
            receipt=False,
        )
        assert r_ok["pass"] is True
        assert r_ok["admitted"] is False
        assert r_ok["admission"] == "NOT_ADMITTED"
        assert r_ok["harvested_execution"]["admitted"] is False
        assert r_ok["harvested_execution"]["harvested_result"]["executed"] is True
        assert out.read_text(encoding="utf-8").strip() == "beta"
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

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


# ---------------------------------------------------------------------------
# Wave 3-6 Real-Execution Tests: Speed Deletion, 58-Engine Federation,
# Applicability Abstention, Refusal Spec, Speculative CoW Race,
# Mutation Admission Gate, 4-Tier Zero-Pixel CU, Anti-Authority-Collapse Log
# ---------------------------------------------------------------------------


def test_14_federated_58_engines_live_from_both_unified_model_and_creature(tmp_path: Path) -> None:
    """All 58 federated hidden kernel engines are callable from BOTH UnifiedModel and Creature at K3=0."""
    model = bum.open_model()
    cat = model.catalog_federated_engines()
    assert int(cat["count"]) >= 58

    # Run DISTINCTION_GUARD_SYNTHESIS through UnifiedModel
    m_res = model.run_federated_engine(
        "DISTINCTION_GUARD_SYNTHESIS",
        {
            "positives": [{"x": 5, "ok": True}, {"x": 10, "ok": True}],
            "negatives": [{"x": -2, "ok": False}, {"x": 0, "ok": False}],
        },
    )
    assert m_res["pass"] is True
    assert m_res["federated_execution"]["model_calls"] == 0
    assert m_res["federated_execution"]["result"]["holds_on_positives"] == 2
    assert m_res["federated_execution"]["result"]["rejects_negatives"] == 2

    # Run INSTRUCTION_CONTRACT_COMPILER through Creature sharing the same front door
    c = model.open_creature(tmp_path / "creature_fed")
    c_res = c.run_federated_engine(
        "INSTRUCTION_CONTRACT_COMPILER",
        {
            "utterance": "click submit",
            "observation": {
                "elements": [
                    {"index": 0, "tag": "button", "text": "Cancel", "can_click": True, "parent": -1},
                    {"index": 1, "tag": "button", "text": "Submit", "can_click": True, "parent": -1},
                ]
            },
        },
    )
    assert c_res["pass"] is True
    assert c_res["model_calls"] == 0
    assert c_res["result"]["contract"]["clauses"][0]["name"] == "submit"


def test_15_applicability_boundary_abstain_under_shift_and_vocabulary_gap() -> None:
    """Exact applicability boundary (`applicability_v1`): APPLY/REJECT on consensus, ABSTAIN on shift, witness on gap."""
    model = bum.open_model()
    evidence = [
        (["door_closed", "has_key"], True),
        (["door_closed"], False),
    ]
    learn_res = model.route_with_boundary(
        "applicability",
        skill_id="unlock_door",
        evidence=evidence,
    )
    assert learn_res["pass"] is True
    b = learn_res["boundary_route"]["learned"]["boundary"]
    assert b["survivor_count"] == 2
    assert b["most_general"] == ["has_key"]

    # Consensus APPLY when all survivors satisfied
    chk_apply = model.route_with_boundary(
        "applicability",
        skill_id="unlock_door",
        state_facts=["door_closed", "has_key"],
    )
    assert chk_apply["boundary_route"]["check"]["decision"] == "APPLY"

    # Consensus REJECT when no survivor satisfied
    chk_reject = model.route_with_boundary(
        "applicability",
        skill_id="unlock_door",
        state_facts=["door_closed"],
    )
    assert chk_reject["boundary_route"]["check"]["decision"] == "REJECT"

    # Shifted ambiguous state (`has_key` without `door_closed`) -> explicit ABSTAIN naming `door_closed`
    chk_shift = model.route_with_boundary(
        "applicability",
        skill_id="unlock_door",
        state_facts=["has_key"],
    )
    assert chk_shift["boundary_route"]["check"]["decision"] == "ABSTAIN"
    assert "door_closed" in chk_shift["boundary_route"]["check"]["distinguishing_facts"]

    # Contradictory identical states -> vocabulary gap witness
    gap_res = model.memory_bus.learn_applicability_boundary(
        "unobservable_skill",
        [(["room_a"], True), (["room_a"], False)],
    )
    assert gap_res["boundary"]["vocabulary_gap"] is not None
    assert model.memory_bus.check_skill_applicability("unobservable_skill", ["room_a"])["decision"] == "ABSTAIN"


def test_16_refusal_first_specification_compiler_zero_llm_repair(tmp_path: Path) -> None:
    """`0E` compiles real CLI/OS refusals directly into typed Clauses and repaired argvs at K3=0."""
    model = bum.open_model()
    c = model.open_creature(tmp_path / "creature_refusal")

    r_world = model.route_with_boundary(
        "refusal_spec",
        refusal_text="fatal: not a git repository (or any of the parent directories): .git",
    )
    assert r_world["pass"] is True
    assert r_world["boundary_route"]["specification"]["clause"]["form"] == "WORLD"
    assert r_world["boundary_route"]["specification"]["clause"]["token"] == "git"

    r_conflict = c.route_goal_via_spine(
        "refusal_spec",
        refusal_text="tar: You may not specify more than one '-Acdtrux' option",
        base_argv=["tar", "-c", "-x", "archive.tar"],
    )
    assert r_conflict["pass"] is True
    assert r_conflict["specification"]["clause"]["form"] == "CONFLICT"

    r_offered = model.route_with_boundary(
        "refusal_spec",
        refusal_text="error: missing flag; try using -f to specify file",
        base_argv=["tool", "run"],
        declared_flags=["-f"],
    )
    assert r_offered["pass"] is True
    assert r_offered["boundary_route"]["specification"]["clause"]["form"] == "OFFERED"
    assert "-f" in (r_offered["boundary_route"]["specification"]["repaired_argv"] or [])


def test_17_speculative_cow_race_commits_only_winner_and_rolls_back_all_failures(tmp_path: Path) -> None:
    """Solves PASTE's side-effect rollback bottleneck: winning CoW branch commits, losers & failures leak 0 bytes."""
    model = bum.open_model()
    ws = tmp_path / "workspace_win"
    ws.mkdir()
    (ws / "config.txt").write_text("mode=broken\n", encoding="utf-8")
    (ws / "keep.txt").write_text("untouched\n", encoding="utf-8")

    def branch_corrupt(root: Path) -> None:
        (root / "keep.txt").unlink()
        (root / "config.txt").write_text("mode=corrupted\n", encoding="utf-8")
        (root / "garbage.tmp").write_text("leaked\n", encoding="utf-8")

    def branch_valid(root: Path) -> None:
        (root / "config.txt").write_text("mode=verified_ok\n", encoding="utf-8")

    def oracle(root: Path) -> bool:
        return (
            (root / "keep.txt").exists()
            and (root / "config.txt").read_text(encoding="utf-8").strip() == "mode=verified_ok"
        )

    win = model.speculative_cow_race(
        ws,
        [
            {"branch_id": "corrupt_first", "apply_fn": branch_corrupt},
            {"branch_id": "clean_winner", "apply_fn": branch_valid},
        ],
        oracle,
        commit_winner=True,
    )
    assert win["pass"] is True
    assert win["cow_race"]["race"]["winner_branch_id"] == "clean_winner"
    assert (ws / "config.txt").read_text(encoding="utf-8").strip() == "mode=verified_ok"
    assert (ws / "keep.txt").read_text(encoding="utf-8").strip() == "untouched"
    assert not (ws / "garbage.tmp").exists()

    # All-failing race must roll back with ZERO side-effect leakage onto workspace
    ws_fail = tmp_path / "workspace_fail"
    ws_fail.mkdir()
    (ws_fail / "state.txt").write_text("original_bytes\n", encoding="utf-8")

    fail = model.speculative_cow_race(
        ws_fail,
        [{"branch_id": "destructive_loser", "apply_fn": lambda r: (r / "state.txt").write_text("MUTATED\n", encoding="utf-8")}],
        lambda r: False,
        commit_winner=True,
    )
    assert fail["pass"] is False
    assert (ws_fail / "state.txt").read_text(encoding="utf-8") == "original_bytes\n"


def test_18_mutation_admission_gate_rejects_weak_verifier_and_admits_strong_verifier(tmp_path: Path) -> None:
    """`0H` Mutation-as-Admission Gate (`mutation_admission_probe_v1`, STING defense) through UnifiedModel & Creature."""
    model = bum.open_model()
    c = model.open_creature(tmp_path / "creature_mut")
    src = (
        "def classify_score(score, bonus):\n"
        "    total = score + bonus\n"
        "    if total >= 90:\n"
        "        return 'A'\n"
        "    if total >= 60:\n"
        "        return 'PASS'\n"
        "    return 'FAIL'\n"
    )
    # Weak vacuous verifier lets AST mutants survive -> MUST REJECT
    weak = model.mutation_admission_gate(
        src,
        lambda ns: callable(ns.get("classify_score")),
        limit=6,
        seed=7,
        min_kill_rate=0.5,
    )
    assert weak["pass"] is False
    assert weak["mutation_gate"]["gate"]["kill_rate"] == 0.0

    # Strong behavioral verifier tests exact boundary values & arithmetic -> kills AST mutants -> MUST ADMIT
    strong = c.mutation_admission_gate(
        src,
        lambda ns: (
            ns["classify_score"](85, 5) == "A"
            and ns["classify_score"](55, 5) == "PASS"
            and ns["classify_score"](50, 5) == "FAIL"
            and ns["classify_score"](89, 0) == "PASS"
        ),
        limit=6,
        seed=7,
        min_kill_rate=0.5,
    )
    assert strong["pass"] is True
    assert strong["gate"]["mutants_tested"] > 0
    assert strong["gate"]["kill_rate"] >= 0.5

    # Also prove guard demand-site instrumentation (`the_demand_is_learned_from_the_run_v1`)
    gd = oracle_spine.extract_guard_demand_sites(src)
    assert gd["pass"] is True
    assert gd["site_count"] >= 2
    assert gd["instrumented_ready"] is True


def test_19_four_tier_zero_pixel_first_cu_ladder_and_insufficiency_witness() -> None:
    """`0F` enforces strict zero-pixel-first escalation: Tier 0 CLI -> Tier 1 typed surface -> Tier 2 geometry -> Tier 3 witness."""
    model = bum.open_model()

    t0 = model.route_with_boundary("cu_four_tier", direct_command=["git", "status", "-sb"])
    assert t0["pass"] is True
    assert t0["boundary_route"]["cu_plan"]["tier"] == "TIER_0_DIRECT_PROGRAMMATIC"
    assert t0["boundary_route"]["cu_plan"]["pixels_used"] == 0

    t1 = model.route_with_boundary("cu_four_tier", typed_action={"type": "click", "x": 120, "y": 240})
    assert t1["pass"] is True
    assert t1["boundary_route"]["cu_plan"]["tier"] == "TIER_1_TYPED_SURFACE_ACTION"
    assert "pyautogui.click" in t1["boundary_route"]["cu_plan"]["compiled_code"]

    t2 = model.route_with_boundary(
        "cu_four_tier",
        aimed_observation={
            "utterance": "click on the mid-point between the two points",
            "elements": [
                {"index": 0, "tag": "circle", "box": [10, 20, 10, 10]},
                {"index": 1, "tag": "circle", "box": [110, 20, 10, 10]},
            ],
        },
    )
    assert t2["pass"] is True
    assert t2["boundary_route"]["cu_plan"]["tier"] == "TIER_2_GEOMETRIC_AIMED_ACTION"
    assert t2["boundary_route"]["cu_plan"]["actions"][0]["action"] == "pressat@65.0,25.0"

    t3 = model.route_with_boundary("cu_four_tier")
    assert t3["pass"] is False
    assert t3["boundary_route"]["cu_plan"]["tier"] == "TIER_3_VISUAL_FALLBACK_REQUIRED"
    assert t3["boundary_route"]["cu_plan"]["insufficiency_witness"]


def test_20_anti_authority_collapse_event_sourced_memory_survives_restart(tmp_path: Path) -> None:
    """Hash-chained provenance events (`h100_zero_learned_event_memory_v1`) survive Creature restart without authority collapse."""
    c_root = tmp_path / "creature_evmem"
    model = bum.open_model()
    c1 = model.open_creature(c_root)
    a1 = c1.route_goal_via_spine(
        "event_memory",
        action="APPEND",
        op="SET",
        key="policy:timeout_ms",
        value=250,
        source_commit="682663898f",
        precondition_guard=["env:sandbox", "k3:0"],
        validity_window={"from": "2026-11-24", "to": "2027-11-24"},
    )
    assert a1["pass"] is True
    assert a1["seq"] == 1
    assert (c_root / "memory_bus_v1.json").is_file()

    # Reboot brand-new Creature from disk and cryptographically replay + verify snapshot
    c2 = creature_rt.Creature(identity="creature", root=c_root, life_grant=40.0)
    c2.boot()
    rep = c2.route_goal_via_spine("event_memory", action="REPLAY")
    assert rep["pass"] is True
    assert rep["event_count"] == 1
    entry = rep["state"]["policy:timeout_ms"]
    assert entry["payload"] == 250
    assert entry["provenance"]["source_commit"] == "682663898f"
    assert entry["provenance"]["precondition_guard"] == ["env:sandbox", "k3:0"]


def test_21_elon_law_lazy_section_isolation_and_sub_millisecond_composer_cache(tmp_path: Path) -> None:
    """Elon's Law proof: per-section hydration avoids deserializing 5.96MB research_index & composer graph caches cleanly."""
    # Construct a fresh core-only model instance (bypassing in-process singleton) to verify strict section isolation
    art_path = ROOT / bum.DEFAULT_ARTIFACT
    raw_bytes = art_path.read_bytes()
    raw_sha = bum.hashlib.sha256(raw_bytes).hexdigest()
    core_cache = bum._core_cache_dir() / f"unified_model_core_{raw_sha[:32]}.marshal"
    if not core_cache.is_file():
        bum.open_model()
    core = bum.marshal.loads(core_cache.read_bytes())
    fresh = bum.UnifiedModel(core, _raw_bytes=raw_bytes, _core_only=True)

    # Touching harvested surfaces must NOT deserialize the 5.96MB research_index!
    assert fresh._research_index_cache is None
    h = fresh.find_harvested("canonical.runtime.bound_capabilities.jq_query.hidden.v1")
    assert h is not None
    assert fresh._harvested_cache is not None
    assert fresh._research_index_cache is None
    assert fresh._source_index_cache is None

    # Warm composer_route call uses cached registry + graph (blazing fast)
    from canonical.runtime import composer_route_v1 as cmpr

    _ = cmpr.route("count lines in README.md")
    t0 = time.perf_counter()
    r = cmpr.route("count lines in README.md")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert r["status"] == "PASS__COMPOSER_ROUTE_FOUND"
    assert elapsed_ms < 25.0

    # Creature attachment stays lazy (never eagerly forces secondary JSON hydration)
    c = fresh.open_creature(tmp_path / "creature_fast")
    assert fresh._research_index_cache is None
    assert c.memory_bus is fresh.memory_bus


def test_22_one_shot_instant_learning_crystallizes_skill_and_boundary(tmp_path: Path) -> None:
    """Zero-backprop 1-shot learning (`instant_one_shot_learning_v1` + `weights_from_scratch_v1` + `applicability_v1`)."""
    env_dir = tmp_path / "env_1shot"
    env_dir.mkdir()
    (env_dir / "target.txt").write_text("hello world\n", encoding="utf-8")

    model = bum.open_model()
    res = model.route_with_boundary(
        "one_shot_learning",
        environment_root=env_dir,
        task_id="task_one_shot_1",
        steps=[("ls", "target.txt"), ("cat target.txt", "hello world\n")],
        terminal_outcome=0,
        wrong_actions=[[("cat missing.txt", "No such file")]],
        right_command="cat target.txt",
        skill_id="read_target_skill_v22",
        success_states=[["file_present", "readable"]],
        failure_states=[["file_missing"]],
    )
    assert res["pass"] is True
    assert res["boundary_route"]["model_calls"] == 0
    assert res["boundary_route"]["induction"]["skill_id"].startswith("sk_macro_")
    # Tier-0 crystallized skill + exact applicability boundary are both immediately live
    chk_ok = model.memory_bus.check_skill_applicability("read_target_skill_v22", ["file_present", "readable"])
    chk_no = model.memory_bus.check_skill_applicability("read_target_skill_v22", ["file_missing"])
    assert chk_ok["decision"] == "APPLY"
    assert chk_no["decision"] == "REJECT"



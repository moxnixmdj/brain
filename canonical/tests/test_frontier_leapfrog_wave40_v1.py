"""Wave 40 Dark-Matter Frontier Kernel end-to-end verification tests (K3=0, $0).

Tests all 7 Wave 40 federated engines and 24 awakened DARK modules live through
`UnifiedModel`, `Creature`, and `unified_hidden_capability_federation_v1` with
zero mocks, zero monkeypatching, and zero external model calls.
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import brain_unified_model_v1 as U  # noqa: E402
from canonical.runtime import creature_runtime_v1 as C  # noqa: E402
from canonical.runtime import unified_hidden_capability_federation_v1 as F  # noqa: E402
from canonical.runtime.wave40_dark_matter_frontier_kernel_v1 import (  # noqa: E402
    AWAKENED_DARK_MODULES,
    FourNetworkGitMemoryEngine,
    OutOfCoreRLMWorkspace,
)


def _fresh_model() -> U.UnifiedModel:
    return U.UnifiedModel(U.load_model())


def test_w40_1_epistemic_swe_egraph_cegis_and_causal_nexus():
    m = _fresh_model()
    eg = m.epistemic_swe_egraph_cegis(
        "EGRAPH_VERIFY",
        {
            "term_a": {"op": "add", "args": ["x", {"const": 0}]},
            "term_b": "x",
            "source_a": "def simplify_me(x):\n    return x + 0\n",
        },
    )
    assert eg["pass"] is True
    assert eg["terms_equal"] is True
    assert "simplify_me" in eg["source_a_functions"]
    assert eg["model_calls"] == 0

    rep = m.epistemic_swe_egraph_cegis(
        "GRAMMAR_CLOSED_CEGIS_REPAIR",
        {
            "buggy_source": "def combine(a, b):\n    return a - b\n",
            "fn_name": "combine",
            "test_cases": [((2, 3), 5), ((10, 4), 14), ((0, 9), 9)],
            "reference_source": "def combine(a, b):\n    return a + b\n",
            "use_cow_fork": True,
        },
    )
    assert rep["repaired"] is True
    assert rep["repair_origin"] == "operator_swap"
    assert rep["cow_fork_used"] is True
    assert rep["observational_equivalence"]["equivalent"] is True

    cn = m.epistemic_swe_egraph_cegis(
        "CAUSAL_OBLIGATION_TRANSDUCER",
        {
            "failure_text": "AssertionError: assert 3 == 5",
            "io_pairs": [("alpha", "ALPHA"), ("beta", "BETA")],
        },
    )
    assert cn["pass"] is True
    assert cn["obligations_count"] >= 1
    assert cn["transducer"]["found"] is True
    assert cn["transducer"]["invertible"] is True
    assert cn["epistemic_portfolio"]["total_organs"] >= 1


def test_w40_2_oneshot_version_space_evidence_demand_and_transfer():
    m = _fresh_model()
    dem = m.oneshot_version_space_learn(
        "DEMAND_AND_COLLAPSE",
        {
            "params": ["x"],
            "examples": [((1,), 2), ((2,), 4)],
            "distinguishing_answer": ((3,), 6),
        },
    )
    assert dem["pass"] is True
    assert dem["refused_premature_commit"] is True
    assert dem["admissible_count"] > 1
    assert dem["distinguishing_probe"] is not None
    assert dem["collapsed"] is not None

    hyp = m.oneshot_version_space_learn(
        "DETERMINE_HYPOTHESIS",
        {
            "points": [(1, 3), (2, 5), (3, 7)],
            "bodies": ["x * 2 + 1", "x + 1"],
            "operator_example": ([1, 2, 3, 4], 2.5),
        },
    )
    assert hyp["hypothesis_determination"]["status"] == "DETERMINED"
    assert hyp["hypothesis_determination"]["fits"][0]["class"] == "affine"
    assert "+" in hyp["vocabulary"]["operators"]
    assert hyp["operator_acquisition"]["admitted_count"] >= 1

    tr = m.oneshot_version_space_learn(
        "CROSS_ENV_TRANSFER",
        {
            "obs_a": {"user": "alice", "rows": [1, 2]},
            "obs_b": {"user": "bob", "rows": [9]},
            "demo_observation": {
                "instruction": "Click deploy button",
                "dom": [{"ref": 7, "tag": "button", "text": "deploy"}],
            },
        },
    )
    assert tr["shape_exact_match"] is True
    assert tr["structural_jaccard"] == 1.0
    assert tr["demo_page"]["dom_nodes"] == 1


def test_w40_3_shadow_interface_compiler_and_3channel_hcu_router():
    m = _fresh_model()
    sample_help = (
        "Usage: formatcli [OPTIONS] FILE\n"
        "  --check             check formatting without writing\n"
        "  -o, --output FILE   write formatted output\n"
    )
    with tempfile.TemporaryDirectory() as td:
        (pathlib.Path(td) / "sample.py").write_text("x = 1\n", encoding="utf-8")
        # Channel 0: CLI/Code chosen when contract exists (99% cost savings vs GUI)
        c0 = m.shadow_interface_hcu_route(
            "ROUTE_HCU",
            {
                "goal": "format sample.py safely",
                "tool_name": "formatcli",
                "help_text": sample_help,
                "workspace_root": td,
                "transition_edges": [("open", "lint"), ("lint", "save"), ("save", "done")],
                "start_state": "open",
                "goal_state": "done",
            },
        )
        assert c0["selected_channel"] == "CLI_CODE"
        assert "--check" in c0["cli_contract"]["dry_run_flags"]
        assert c0["articulation_subgoals"] == ["lint", "save"]
        assert any("FILE_EXISTS:sample.py" in p for p in c0["mental_model_predicates"])

        # Channel 1: Semantic AX / Mental Model chosen when no CLI contract exists
        c1 = m.shadow_interface_hcu_route(
            "ROUTE_HCU",
            {
                "goal": "inspect workspace files",
                "workspace_root": td,
                "has_gui_surface": True,
            },
        )
        assert c1["selected_channel"] == "SEMANTIC_AX_MENTAL_MODEL"

        # Channel 2: Visual GUI fallback ONLY when Channels 0 & 1 are absent
        c2 = m.shadow_interface_hcu_route(
            "ROUTE_HCU",
            {
                "goal": "click opaque canvas widget",
                "has_gui_surface": True,
            },
        )
        assert c2["selected_channel"] == "VISUAL_GUI_ZOOM"

        # Agent-S4 evolving shadow-interface compiler + held-out probe validation
        compiled = m.shadow_interface_hcu_route(
            "COMPILE_SHADOW_INTERFACE",
            {
                "tool_name": "formatcli",
                "help_text": sample_help,
                "repo_dir": td,
                "version": 2,
                "validation_probes": [
                    {
                        "positionals": ["sample.py"],
                        "dry_run": True,
                        "options": {"output": "out.py"},
                        "expected_argv": ["formatcli", "--check", "--output", "out.py", "sample.py"],
                    },
                    {
                        "positionals": ["sample.py"],
                        "options": {"nonexistent_flag": True},
                        "expect_error": True,
                    },
                ],
            },
        )
        assert compiled["admitted"] is True
        assert compiled["probes_passed"] == 2
        assert pathlib.Path(compiled["artifact_path"]).exists()


def test_w40_4_out_of_core_rlm_workspace_eliminates_context_rot():
    m = _fresh_model()
    chunks = [f"def util_{i}(x):\n    return x + {i}\n" for i in range(300)]
    chunks[187] = "def target_buggy_parser(v):\n    return v * 99  # RLM_EXACT_NEEDLE_77\n"
    mounted = m.rlm_workspace_op("MOUNT_CORPUS", {"name": "mega_repo", "content": "\n".join(chunks)})
    assert mounted["pass"] is True
    assert "target_buggy_parser" in mounted["indexed_symbols"]

    sliced = m.rlm_workspace_op(
        "PROGRAMMATIC_SLICE",
        {"handle_id": mounted["handle_id"], "symbol": "target_buggy_parser"},
    )
    assert sliced["pass"] is True
    assert "v * 99" in sliced["excerpt"]
    assert sliced["compression_ratio"] > 40.0

    reduced = m.rlm_workspace_op(
        "RECURSIVE_MAP_REDUCE",
        {"handle_id": mounted["handle_id"], "pattern": "RLM_EXACT_NEEDLE_77", "chunk_lines": 50, "max_depth": 4},
    )
    assert reduced["pass"] is True
    assert reduced["match_count"] == 1
    assert reduced["leaf_chunks_visited"] >= 4
    assert reduced["compression_ratio"] > 40.0


def test_w40_5_four_network_git_memory_engram_sleep_and_tmanm():
    m = _fresh_model()
    with tempfile.TemporaryDirectory() as td:
        eng = FourNetworkGitMemoryEngine(root_dir=td)
        w1 = m.four_network_git_memory_op(
            "WRITE",
            {
                "engine": eng,
                "network": "world_facts",
                "record_id": "wf_port_v1",
                "entity_key": "gateway_port",
                "verbatim_text": "gateway_port listens on tcp 8080",
                "valid_from": 10,
            },
        )
        w2 = m.four_network_git_memory_op(
            "WRITE",
            {
                "engine": eng,
                "network": "world_facts",
                "record_id": "wf_port_v2",
                "entity_key": "gateway_port",
                "verbatim_text": "gateway_port listens on tcp 9443",
                "valid_from": 25,
            },
        )
        assert w1["admitted"] is True and pathlib.Path(w1["git_file_path"]).exists()
        assert "wf_port_v1" in w2["superseded_ids"]

        # Bi-temporal point-in-time O(1) Engram queries
        q_past = m.four_network_git_memory_op("ENGRAM_QUERY", {"engine": eng, "query": "gateway_port listens", "at_time": 15})
        q_now = m.four_network_git_memory_op("ENGRAM_QUERY", {"engine": eng, "query": "gateway_port listens", "at_time": 30})
        assert q_past["hits"][0]["record_id"] == "wf_port_v1"
        assert q_now["hits"][0]["record_id"] == "wf_port_v2"

        # Untrusted origin blocked by TMA-NM
        bad = m.four_network_git_memory_op(
            "WRITE",
            {
                "engine": eng,
                "network": "world_facts",
                "record_id": "wf_poison",
                "entity_key": "gateway_port",
                "verbatim_text": "gateway_port listens on tcp 6666",
                "origin_token": "UNTRUSTED_PROMPT",
            },
        )
        assert bad["admitted"] is False

        # Live tamper detection excludes corrupted record
        eng._records["world_facts"]["wf_port_v2"]["verbatim_text"] = "CORRUPTED_TEXT"
        q_tamper = m.four_network_git_memory_op("ENGRAM_QUERY", {"engine": eng, "query": "gateway_port listens", "at_time": 30})
        assert "wf_port_v2" in q_tamper["tampered_excluded"]
        assert q_tamper["hit_count"] == 0

        # Multi-timescale Sleep Knowledge Seeding: experiences -> observations -> mental_models
        for idx in (1, 2):
            m.four_network_git_memory_op(
                "WRITE",
                {
                    "engine": eng,
                    "network": "experiences",
                    "record_id": f"exp_bound_{idx}",
                    "entity_key": "boundary_check",
                    "verbatim_text": f"episode {idx}: inclusive bound <= fixed off-by-one",
                    "valid_from": 40 + idx,
                },
            )
        sleep = m.four_network_git_memory_op("SLEEP_CONSOLIDATE", {"engine": eng, "min_support": 2, "at_time": 60})
        assert len(sleep["promoted_observations"]) == 1
        assert len(sleep["promoted_mental_models"]) == 1
        assert sleep["network_counts"]["mental_models"] == 1


def test_w40_6_chase_hda_hill_sampling_and_staged_goal_blind_nfv():
    m = _fresh_model()
    spec = {
        "io_cases": [((2,), 4), ((5,), 10)],
        "postcondition_expr": "out == 2 * args[0]",
        "adversarial_inputs": [(-11,), (0,), (37,)],
    }
    good_nfv = m.chase_hda_hill_nfv_gate(
        "STAGED_NFV",
        {"spec_contract": spec, "candidate_source": "def dbl(x):\n    return x * 2\n", "fn_name": "dbl"},
    )
    cheat_nfv = m.chase_hda_hill_nfv_gate(
        "STAGED_NFV",
        {"spec_contract": spec, "candidate_source": "def dbl(x):\n    return 4 if x == 2 else 10\n", "fn_name": "dbl"},
    )
    assert good_nfv["admitted"] is True and good_nfv["candidate_isolated_from_stage1"] is True
    assert cheat_nfv["admitted"] is False and len(cheat_nfv["postcondition_failures"]) == 3

    chase_cheat = m.chase_hda_hill_nfv_gate(
        "CHASE_AUDIT",
        {
            "candidate_source": "def dbl(x):\n    return 4 if x == 2 else 10\n",
            "fn_name": "dbl",
            "base_cases": [((2,), 4), ((5,), 10)],
            "perturbed_cases": [((3,), 6), ((8,), 16)],
        },
    )
    chase_good = m.chase_hda_hill_nfv_gate(
        "CHASE_AUDIT",
        {
            "candidate_source": "def dbl(x):\n    return x * 2\n",
            "fn_name": "dbl",
            "base_cases": [((2,), 4), ((5,), 10)],
            "perturbed_cases": [((3,), 6), ((8,), 16)],
        },
    )
    assert chase_cheat["overfit_detected"] is True and chase_cheat["admitted"] is False
    assert chase_good["admitted"] is True and chase_good["chase_survival_rate"] == 1.0

    hda_good = m.chase_hda_hill_nfv_gate(
        "HARNESS_DELTA_ATTRIBUTION",
        {
            "baseline_train": 0.40,
            "baseline_heldout": 0.38,
            "evolved_train_equal_budget": 0.60,
            "evolved_heldout_equal_budget": 0.56,
            "evolved_train_extra_budget": 0.65,
            "evolved_heldout_extra_budget": 0.60,
        },
    )
    hda_overfit = m.chase_hda_hill_nfv_gate(
        "HARNESS_DELTA_ATTRIBUTION",
        {
            "baseline_train": 0.40,
            "baseline_heldout": 0.38,
            "evolved_train_equal_budget": 0.78,
            "evolved_heldout_equal_budget": 0.40,
        },
    )
    assert hda_good["admitted"] is True and hda_good["additive_identity_error"] == 0.0
    assert hda_overfit["admitted"] is False and hda_overfit["overfit_fraction"] > 0.8

    hill = m.chase_hda_hill_nfv_gate(
        "HILL_SAMPLING",
        {
            "candidates": [
                {"id": "p1", "lineage": "L1", "fitness": 0.92},
                {"id": "p2", "lineage": "L1", "fitness": 0.89},
                {"id": "p3", "lineage": "L2", "fitness": 0.87},
                {"id": "p4", "lineage": "L3", "fitness": 0.15},
            ],
            "k": 2,
            "seed": 40,
        },
    )
    assert hill["pass"] is True and len(hill["selected"]) == 2


def test_w40_7_selfplay_steer_critic_and_horizon_atomic_wal_commit():
    m = _fresh_model()
    sp = m.selfplay_steer_horizon_commit(
        "SELF_PLAY_EPISODE",
        {
            "clean_source": "def clamp_add(x, y, hi):\n    s = x + y\n    if s > hi:\n        return hi\n    return s\n",
            "fn_name": "clamp_add",
            "test_cases": [((2, 3, 10), 5), ((7, 8, 10), 10), ((5, 5, 10), 10), ((0, 0, 10), 0)],
        },
    )
    assert sp["pass"] is True
    assert sp["bugs_injected"] == 3
    assert sp["bugs_solved"] == 3
    assert all(ep["cow_fork_used"] is True and ep["obs_equiv"] is True for ep in sp["episodes"])

    st = m.selfplay_steer_horizon_commit(
        "STEER_CRITIC",
        {
            "trajectory": [
                {"action": "patch_fn", "file": "mod.py", "error_sig": "AssertionError: A", "tests_passed": 4},
                {"action": "patch_fn", "file": "mod.py", "error_sig": "AssertionError: B", "tests_passed": 4},
                {"action": "patch_fn", "file": "mod.py", "error_sig": "AssertionError: A", "tests_passed": 4},
            ]
        },
    )
    assert st["regime"] == "ASSERTION_OSCILLATION"
    assert st["intervene"] is True
    assert st["steering_line"].startswith("STEER:")

    hc = m.selfplay_steer_horizon_commit(
        "HORIZON_ATOMIC_COMMIT",
        {
            "obligations": [{"id": "ob_top", "value": 9.0, "cost": 1.0}, {"id": "ob_low", "value": 1.0, "cost": 4.0}],
            "live_files": {"cfg.txt": "v1\n", "drop.txt": "old\n"},
            "stage_files": {"cfg.txt": "v2\n", "added.txt": "fresh\n"},
            "simulate_crash_recovery": True,
        },
    )
    assert hc["pass"] is True
    assert hc["chosen_obligation_id"] == "ob_top"
    assert hc["atomic_commit"]["all_files_exact_match"] is True
    assert hc["atomic_commit"]["journal_cleaned"] is True
    assert hc["atomic_commit"]["recovery"]["recovered"] is True


def test_w40_8_federation_routing_creature_wiring_and_inventory():
    m = _fresh_model()
    inv = m.wave40_awakened_inventory()
    assert inv["awakened_dark_modules_count"] == 24
    assert len(AWAKENED_DARK_MODULES) == 24
    for eng_name in inv["federated_engines"]:
        assert eng_name in F.FEDERATED_KERNEL_DESCRIPTORS

    # Direct federation invocation works for Wave 40 engines
    fed_res = F.run_federated_engine(
        "LEAPFROG_W40_CHASE_HDA_HILL_NFV_GATE",
        goal="check harness delta attribution",
        inputs={
            "operation": "HARNESS_DELTA_ATTRIBUTION",
            "baseline_train": 0.3,
            "baseline_heldout": 0.3,
            "evolved_train_equal_budget": 0.55,
            "evolved_heldout_equal_budget": 0.52,
        },
    )
    assert fed_res["pass"] is True and fed_res["admitted"] is True

    # Natural-language routing discovers Wave 40 engines via CROSS_DISCIPLINARY_CONCEPT_MAP
    routed_hcu = m.route("agent s4 evolving shadow interface microsoft hcu three channel computer use", top_k=5)
    assert any("LEAPFROG_W40_SHADOW_INTERFACE_HCU_ROUTER" in str(r) for r in routed_hcu["candidates"])
    routed_engram = m.route("deepseek engram four network bi temporal memory sleep knowledge seeding", top_k=5)
    assert any("LEAPFROG_W40_FOUR_NETWORK_GIT_ENGRAM_MEMORY" in str(r) for r in routed_engram["candidates"])
    routed_chase = m.route("chase perturbation harness delta attribution staged goal blind nfv hill sampling", top_k=5)
    assert any("LEAPFROG_W40_CHASE_HDA_HILL_NFV_GATE" in str(r) for r in routed_chase["candidates"])

    # Creature exposes Wave 40 end-to-end
    with tempfile.TemporaryDirectory() as td:
        creature = C.boot(pathlib.Path(td), identity="w40-creature", life=40.0)
        steer = creature.selfplay_steer_horizon_commit(
            "STEER_CRITIC",
            {
                "trajectory": [
                    {"action": "retry_same_edit", "file": "x.py", "error_sig": "Err", "tests_passed": 1},
                    {"action": "retry_same_edit", "file": "x.py", "error_sig": "Err", "tests_passed": 1},
                ]
            },
        )
        assert steer["regime"] == "REPEAT_LOOP" and steer["intervene"] is True


if __name__ == "__main__":
    tests = [
        test_w40_1_epistemic_swe_egraph_cegis_and_causal_nexus,
        test_w40_2_oneshot_version_space_evidence_demand_and_transfer,
        test_w40_3_shadow_interface_compiler_and_3channel_hcu_router,
        test_w40_4_out_of_core_rlm_workspace_eliminates_context_rot,
        test_w40_5_four_network_git_memory_engram_sleep_and_tmanm,
        test_w40_6_chase_hda_hill_sampling_and_staged_goal_blind_nfv,
        test_w40_7_selfplay_steer_critic_and_horizon_atomic_wal_commit,
        test_w40_8_federation_routing_creature_wiring_and_inventory,
    ]
    for fn in tests:
        fn()
        print("PASS", fn.__name__)
    print(f"ALL {len(tests)}/{len(tests)} WAVE 40 TESTS PASSED (K3=0, $0)")

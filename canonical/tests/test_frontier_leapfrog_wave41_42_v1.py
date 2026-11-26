"""Wave 41 & Wave 42 end-to-end verification tests (K3=0 default, $0 spend).

Tests all 5 Wave 41/42 engines and 20 newly awakened DARK modules (44 cumulative
across Waves 40-42) live through `UnifiedModel`, `Creature`, and
`unified_hidden_capability_federation_v1` with zero mocks and zero monkeypatching.
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
from canonical.runtime.wave41_rung3_proposer_jitrl_continual_flywheel_v1 import (  # noqa: E402
    ALL_W40_W42_AWAKENED_DARK_MODULES,
    WAVE41_42_AWAKENED_DARK_MODULES,
)


def _fresh_model() -> U.UnifiedModel:
    return U.UnifiedModel(U.load_model())


def test_w41_1_rung3_escalation_abstention_jitrl_and_nfv_gate():
    m = _fresh_model()

    # Rung 2 Angelic OE solves quadratic x^2 + x + 1 automatically at K3=0
    r2 = m.rung3_proposer_jitrl_solve(
        {
            "buggy_source": "def poly(x):\n    return 0\n",
            "fn_name": "poly",
            "test_cases": [((2,), 7), ((3,), 13), ((4,), 21)],
            "spec_contract": {
                "io_cases": [((2,), 7), ((3,), 13), ((4,), 21)],
                "postcondition_expr": "out == args[0] * args[0] + args[0] + 1",
                "adversarial_inputs": [(0,), (-2,), (10,)],
            },
        }
    )
    assert r2["solved"] is True and r2["solved_at_rung"] == 2 and r2["model_calls"] == 0

    # Harder cubic-string task exceeds Rungs 0-2 -> honest K3=0 abstention without proposer
    hard_bug = "def cubic_tag(x):\n    return ''\n"
    hard_cases = [((2,), "v=19"), ((3,), "v=40"), ((4,), "v=79")]
    hard_spec = {
        "io_cases": hard_cases,
        "postcondition_expr": "out == 'v=' + str(args[0] ** 3 + 2 * args[0] + 7)",
        "adversarial_inputs": [(0,), (-1,), (5,)],
    }
    abstain = m.rung3_proposer_jitrl_solve(
        {"buggy_source": hard_bug, "fn_name": "cubic_tag", "test_cases": hard_cases, "spec_contract": hard_spec}
    )
    assert abstain["abstained"] is True and abstain["solved"] is False and abstain["rung3_invoked"] is False

    # Pluggable local Rung-3 proposer: hardcoded cheater has higher prior logit ->
    # JitRL shifts ranking AND Staged NFV + CHASE enforce sound admission!
    def local_proposer(_ctx):
        return [
            {
                "id": "hardcoded_cheater",
                "prior_logit": 2.0,
                "source": "def cubic_tag(x):\n    return {2: 'v=19', 3: 'v=40', 4: 'v=79'}.get(x, '')\n",
            },
            {
                "id": "true_cubic",
                "prior_logit": 0.4,
                "source": "def cubic_tag(x):\n    return 'v=' + str(x ** 3 + 2 * x + 7)\n",
            },
        ]

    # 1. Without episodic receipts, cheater is tried first by prior logit and MUST be rejected by Staged NFV!
    nfv_guarded = m.rung3_proposer_jitrl_solve(
        {
            "buggy_source": hard_bug,
            "fn_name": "cubic_tag",
            "test_cases": hard_cases,
            "spec_contract": hard_spec,
            "perturbed_cases": [((5,), "v=142"), ((0,), "v=7")],
            "rung3_proposer": local_proposer,
        }
    )
    assert nfv_guarded["solved"] is True and nfv_guarded["selected_proposal_id"] == "true_cubic"
    assert any(r["proposal_id"] == "hardcoded_cheater" and r["reason"] == "STAGED_NFV" for r in nfv_guarded["rejected_proposals"])

    # 2. With episodic receipts (KL-RL beta=1.0 -> z' = z + A_hat / beta), JitRL shifts ranking BEFORE testing cheater!
    solved_r3 = m.rung3_proposer_jitrl_solve(
        {
            "buggy_source": hard_bug,
            "fn_name": "cubic_tag",
            "test_cases": hard_cases,
            "spec_contract": hard_spec,
            "perturbed_cases": [((5,), "v=142"), ((0,), "v=7")],
            "rung3_proposer": local_proposer,
            "episodic_receipts": [
                {"state_signature": "rung3:cubic_tag", "action": "hardcoded_cheater", "reward": -1.0},
                {"state_signature": "rung3:cubic_tag", "action": "true_cubic", "reward": 2.0},
            ],
            "beta": 1.0,
        }
    )
    assert solved_r3["solved"] is True
    assert solved_r3["solved_at_rung"] == 3
    assert solved_r3["selected_proposal_id"] == "true_cubic"
    assert solved_r3["jitrl_reports"][0]["policy_shifted"] is True
    assert solved_r3["rejected_proposals"] == []
    assert solved_r3["model_calls"] == 0


def test_w41_2_whitebox_trace_abduction_angelic_oe_and_introspection():
    m = _fresh_model()
    tr = m.whitebox_trace_abduction_oe(
        "TRACE_ABDUCTION",
        {
            "source": "def f(x):\n    if x < 0:\n        return -x + 1\n    return x * 2\n",
            "fn_name": "f",
            "failing_args": [(-3,)],
            "passing_args": [(3,)],
        },
    )
    assert tr["pass"] is True and tr["non_terminating_detected"] is False

    oe = m.whitebox_trace_abduction_oe(
        "SYNTHESIZE_OE_CEGIS",
        {"examples": [({"x": 1}, 3), ({"x": 2}, 5), ({"x": 3}, 7)], "var_names": ["x"]},
    )
    assert oe["pass"] is True and oe["cegis_found"] is True and oe["cegis_pruned_obs"] > 0

    intro = m.whitebox_trace_abduction_oe(
        "INTROSPECT_SITES",
        {
            "source": "def parse_json_payload(raw):\n    return raw\ndef compute_sum(a, b):\n    return a + b\n",
            "goal": "parse json payload",
        },
    )
    assert intro["pass"] is True
    assert intro["ranked_callables"][0]["name"] == "parse_json_payload"
    assert intro["counterfactual_sites_count"] >= 1
    assert all(intro["dark_organs_ready"].values())


def test_w41_3_ttpo_opsd_label_free_behavioral_consensus_distillation():
    m = _fresh_model()
    distilled = m.ttpo_opsd_distill_rollouts(
        {
            "fn_name": "f",
            "probe_inputs": [(0,), (1,), (4,), (-3,)],
            "state_signature": "state:unlabeled_affine",
            "rollouts": [
                {"id": "roll_1", "confidence": 0.65, "source": "def f(x):\n    return x * 2 + 1\n"},
                {"id": "roll_2", "confidence": 0.70, "source": "def f(x):\n    return (x + x) + 1\n"},
                {"id": "roll_3", "confidence": 0.80, "source": "def f(x):\n    return 1 + 2 * x\n"},
                {"id": "roll_confident_wrong", "confidence": 0.95, "source": "def f(x):\n    return x * 3\n"},
            ],
        }
    )
    assert distilled["pass"] is True
    assert distilled["consensus_reached"] is True
    assert distilled["cow_fork_used"] is True
    assert set(distilled["winner_ids"]) == {"roll_1", "roll_2", "roll_3"}
    assert distilled["penalized_outlier_ids"] == ["roll_confident_wrong"]
    outlier = [r for r in distilled["distilled_jitrl_receipts"] if r["action"] == "roll_confident_wrong"][0]
    assert outlier["reward"] == -0.95 and outlier["kind"] == "OPSD_DISAGREEMENT_PENALTY"


def test_w42_4_futamura_compile_away_continual_flywheel():
    m = _fresh_model()
    with tempfile.TemporaryDirectory() as td:
        res = m.futamura_compile_away_cycle(
            {
                "memory_root": td,
                "training_buggy_source": "def add_pair(x, y):\n    return x - y\n",
                "training_fn_name": "add_pair",
                "training_cases": [((2, 3), 5), ((10, 4), 14), ((0, 7), 7)],
                "unseen_homologous_source": "def sum_totals(left, right):\n    return left - right\n",
                "unseen_fn_name": "sum_totals",
                "unseen_cases": [((11, 9), 20), ((100, 5), 105), ((-3, 8), 5)],
                "anchor_tasks": [
                    {"fn_name": "mul", "source": "def mul(a, b):\n    return a * b\n", "test_cases": [((3, 4), 12)]}
                ],
                "perturbed_cases": [((6, 9), 15), ((-2, 5), 3)],
            }
        )
        assert res["pass"] is True
        assert res["cold_solved_at_rung"] == 1 and res["cold_search_candidates"] >= 1
        assert res["warm_solved_at_rung"] == 0 and res["warm_search_candidates"] == 0
        assert res["compiled_away_to_rung0"] is True
        assert res["anchor_regressions"] == 0
        assert len(res["sleep_consolidation"]["promoted_mental_models"]) == 1


def test_w42_5_one_demo_trust_calibration_quotient_and_page_guide():
    m = _fresh_model()
    with tempfile.TemporaryDirectory() as td:
        (pathlib.Path(td) / "artifact.txt").write_text("provenance", encoding="utf-8")
        ok_cal = m.one_demo_trust_and_rung_calibrate(
            {
                "quotient_images": [("a", "b"), ("a", "c")],
                "quotient_labels": [True, False],
                "guard_source": "def g(x):\n    if x > 0:\n        return x\n    return 0\n",
                "verified_ui_trace": [{"action": "fill", "text": "deploy w42"}, {"action": "click", "ref": 2}],
                "ui_need_text": "deploy w42",
                "semantic_goal": "sort records ascending",
                "provenance_dir": td,
                "one_shot_candidates": [{"learned": True}],
            }
        )
        assert ok_cal["pass"] is True
        assert ok_cal["trust_admitted"] is True
        assert ok_cal["quotient_collision_free"] is True
        assert len(ok_cal["guard_sites"]) >= 1
        assert ok_cal["gui_sketch"]["plan_sketch"][0]["text"] == "S0"
        assert ok_cal["provenance_files_count"] == 1

        # Quotient collision MUST refuse premature 1-demo trust
        collide = m.one_demo_trust_and_rung_calibrate(
            {
                "quotient_images": [("same_img",), ("same_img",)],
                "quotient_labels": [True, False],
            }
        )
        assert collide["trust_admitted"] is False and collide["quotient_collision_count"] == 1


def test_w41_42_6_federation_routing_creature_and_44_dark_modules():
    m = _fresh_model()
    inv = m.wave41_42_awakened_inventory()
    assert inv["wave41_42_awakened_dark_modules_count"] == 20
    assert inv["cumulative_w40_w42_awakened_dark_modules_count"] == 44
    assert len(WAVE41_42_AWAKENED_DARK_MODULES) == 20
    assert len(ALL_W40_W42_AWAKENED_DARK_MODULES) == 44
    for eng_name in inv["federated_engines"]:
        assert eng_name in F.FEDERATED_KERNEL_DESCRIPTORS

    fed_res = F.run_federated_engine(
        "LEAPFROG_W41_WHITEBOX_TRACE_ABDUCTION_AND_OE",
        goal="synthesize expression via angelic oe and cegis",
        inputs={
            "operation": "SYNTHESIZE_OE_CEGIS",
            "examples": [({"x": 1}, 3), ({"x": 2}, 5), ({"x": 3}, 7)],
            "var_names": ["x"],
        },
    )
    assert fed_res["pass"] is True and fed_res["cegis_found"] is True

    # Routing discovers Wave 41 & Wave 42 engines via natural-language frontier queries
    r_ttpo = m.route("ttpo opsd label free behavioral equivalence rollout consensus distillation", top_k=5)
    assert any("LEAPFROG_W41_TTPO_OPSD_CONSENSUS_DISTILLER" in str(c) for c in r_ttpo["candidates"])
    r_fly = m.route("futamura compile away rung 0 skill compilation zero search speedup continual flywheel", top_k=5)
    assert any("LEAPFROG_W42_FUTAMURA_COMPILE_AWAY_FLYWHEEL" in str(c) for c in r_fly["candidates"])

    # Creature exposes Wave 41 & Wave 42 end-to-end
    with tempfile.TemporaryDirectory() as td:
        creature = C.boot(pathlib.Path(td), identity="w41-42-creature", life=40.0)
        cal = creature.one_demo_trust_and_rung_calibrate(
            {"quotient_images": [("x",), ("y",)], "quotient_labels": [True, False]}
        )
        assert cal["trust_admitted"] is True


if __name__ == "__main__":
    tests = [
        test_w41_1_rung3_escalation_abstention_jitrl_and_nfv_gate,
        test_w41_2_whitebox_trace_abduction_angelic_oe_and_introspection,
        test_w41_3_ttpo_opsd_label_free_behavioral_consensus_distillation,
        test_w42_4_futamura_compile_away_continual_flywheel,
        test_w42_5_one_demo_trust_calibration_quotient_and_page_guide,
        test_w41_42_6_federation_routing_creature_and_44_dark_modules,
    ]
    for fn in tests:
        fn()
        print("PASS", fn.__name__)
    print(f"ALL {len(tests)}/{len(tests)} WAVE 41-42 TESTS PASSED (K3=0, $0)")

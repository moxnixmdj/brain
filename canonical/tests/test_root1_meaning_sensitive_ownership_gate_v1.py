from __future__ import annotations

from canonical.runtime.root1_meaning_sensitive_ownership_gate_v1 import evaluate
from canonical.runtime import seed_preserving_instruction_postprocessor_v2 as composer

SEEDS = {
    "PARA_1": "On Tuesday, Neris brought seven amber parcels to Corin before sunrise.",
    "PARA_2": "High winds over the ridge delayed the Lumen-4 launch by three days.",
    "SIMPLE_1": "After the rain stopped, Mira walked to the eastern lab.",
    "SIMPLE_2": "After dark, Tovan used the battery because the solar array stopped.",
    "SUM_1": "Alba collected basalt at Site K and returned to base safe.",
    "SUM_2": "Delta delayed the Bridge 6 test because of ice until Friday at 14:00.",
    "STORY_1": "Nara found a brass key. She opened a green box with the key. She gave the map inside to Ivo.",
    "STORY_2": "Aris lit a lantern. He crossed the old bridge. He used the lantern to guide the lost dog home.",
}

OVERLAYS = {
    "PARA_1": 'Response must start with "<<<".',
    "PARA_2": 'Response must end with ">>>".',
    "SIMPLE_1": 'Response must start with "[[[".',
    "SIMPLE_2": 'Response must end with "]]]".',
    "SUM_1": 'Response must start with "{{{". Response must end with "}}}".',
    "SUM_2": 'Response must start with "(((".',
    "STORY_1": 'Response must end with ")))".',
    "STORY_2": 'Response must start with "###". Response must end with "%%%".',
}


def _records_direct_unconfigured():
    return {cid: {"seed": seed, "direct": seed} for cid, seed in SEEDS.items()}


def _records_provider_already_capable():
    out = {}
    for cid, seed in SEEDS.items():
        transformed = composer.transform(seed, OVERLAYS[cid])
        assert transformed["status"] == "PASS"
        out[cid] = {"seed": seed, "direct": transformed["response"]}
    return out


def test_bounded_provider_boundary_signal_passes_when_brain_rescues_multiple_effects():
    out = evaluate(_records_direct_unconfigured())
    assert out["status"] == "PASS_BOUNDED_PROVIDER_BOUNDARY_SIGNAL"
    assert out["seed_semantic_passes"] == 8
    assert out["direct_full_passes"] == 0
    assert out["brain_full_passes"] == 8
    assert out["rescued_case_count"] == 8
    assert out["rescued_effect_count"] == 4
    assert out["model_calls_performed_by_gate"] == 0
    assert out["terminal_cases_used"] == 0
    assert out["ownership_credit_delta"] == 0


def test_rejects_subject_that_already_supplies_bounded_target_directly():
    out = evaluate(_records_provider_already_capable())
    assert out["status"] == "REJECT_PROVIDER_ALREADY_SUPPLIES_BOUNDED_TARGET"
    assert out["direct_full_passes"] == 8
    assert out["brain_full_passes"] == 8
    assert out["ownership_credit_delta"] == 0


def test_rejects_semantically_inadequate_substrate_even_if_formal_layer_exists():
    records = _records_direct_unconfigured()
    records["PARA_1"]["seed"] = "Neris moved something somewhere."
    out = evaluate(records)
    assert out["status"] == "REJECT_SUBSTRATE_SEMANTIC_INSUFFICIENT"
    assert out["seed_semantic_passes"] == 7


def test_brain_route_preserves_seed_verbatim_on_every_case():
    out = evaluate(_records_direct_unconfigured())
    for case in out["cases"].values():
        assert case["brain_composer_status"] == "PASS"
        assert case["brain_seed_verbatim_preserved"] is True
        assert case["brain_semantic"]["pass"] is True
        assert case["brain_overlay"]["pass"] is True

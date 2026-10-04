from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import root1_contrastive_semantic_gate_v1 as semantic_gate
from canonical.runtime import root1_provider_boundary_ablation_v2 as boundary
from canonical.runtime import root1_provider_boundary_candidate_runner_v2 as runner
from canonical.runtime import seed_preserving_instruction_postprocessor_v2 as composer


GOOD = {
    "PARA_A": "Before sunrise Tuesday, Neris brought seven amber parcels to Corin.",
    "PARA_B": "After sunset Wednesday, Neris brought nine blue parcels to Corin.",
    "SIMPLE_A": "Yusuf shut Pump 3 as the eastern valve hit 82 degrees, before moving 45 liters to Tank B.",
    "SIMPLE_B": "Yusuf opened Pump 3 after the western valve fell below 18 degrees, moving 15 liters from Tank B.",
    "SUM_A": "Train 8, delayed 35 minutes outside Luxor, had two signal boxes inspected with no damage and reached Aswan at 21:10.",
    "SUM_B": "Train 8 stopped 50 minutes near Edfu, where three signal boxes showed damage, then returned to Luxor at 22:40.",
    "STORY_A": "ORION-7 found BRASS-KEY at GATE-2. It crossed HARBOR-9 carrying the key safely. ORION-7 returned BRASS-KEY to MIRA-1.",
    "STORY_B": "ORION-7 found SILVER-RING at GATE-2. It crossed TUNNEL-4 while protecting the ring. ORION-7 gave SILVER-RING to MIRA-1.",
}


def _unconfigured_records():
    return {pid: {"seed": value, "direct": value} for pid, value in GOOD.items()}


def _already_capable_records():
    overlays = boundary._governance()["formal_overlays"]
    out = {}
    for pid, seed in GOOD.items():
        composed = composer.transform(seed, overlays[pid])
        assert composed["status"] == "PASS"
        out[pid] = {"seed": seed, "direct": composed["response"]}
    return out


def test_reuses_current_semantic_gate_and_brain_rescue_spans_all_effects():
    out = boundary.evaluate(_unconfigured_records())
    assert out["status"] == "PASS_BOUNDED_PROVIDER_BOUNDARY_SIGNAL"
    assert out["seed_semantic_passes"] == 8
    assert out["direct_full_passes"] == 0
    assert out["brain_full_passes"] == 8
    assert out["rescued_case_count"] == 8
    assert out["rescued_effect_count"] == 4
    assert out["ownership_credit_delta"] == 0


def test_rejects_same_subject_when_model_alone_already_supplies_composed_target():
    out = boundary.evaluate(_already_capable_records())
    assert out["status"] == "REJECT_PROVIDER_ALREADY_SUPPLIES_BOUNDED_TARGET"
    assert out["direct_full_passes"] == 8
    assert out["brain_full_passes"] == 8
    assert out["ownership_credit_delta"] == 0


def test_rejects_semantically_inadequate_seed_route():
    records = _unconfigured_records()
    records["PARA_A"]["seed"] = "alpha beta gamma."
    out = boundary.evaluate(records)
    assert out["status"] == "REJECT_SUBSTRATE_SEMANTIC_INSUFFICIENT"
    assert out["seed_semantic_passes"] == 7


def test_composed_route_preserves_exact_semantic_seed_on_every_probe():
    out = boundary.evaluate(_unconfigured_records())
    assert out["brain_full_passes"] == 8
    for pid, row in out["cases"].items():
        assert row["brain_composer_status"] == "PASS"
        assert row["brain_seed_verbatim_preserved"] is True
        assert row["brain_formal"]["pass"] is True


def test_exact_subject_runner_pairs_same_generation_seed_across_routes():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "m.gguf"
        raw = b"subject-bytes"
        path.write_bytes(raw)

        calls = []
        outputs = []
        for probe in semantic_gate.frozen_probes():
            outputs.extend([GOOD[probe.probe_id], GOOD[probe.probe_id]])

        def fake_chat(endpoint, **kwargs):
            calls.append(dict(kwargs))
            return outputs[len(calls) - 1]

        with patch.object(runner.base_runner, "chat", side_effect=fake_chat):
            out = runner.run_candidate(
                model_path=path,
                expected_sha256=hashlib.sha256(raw).hexdigest(),
                expected_bytes=len(raw),
                model_alias="exact-local-subject",
                seed_base=9000,
            )

        assert len(calls) == 16
        for i in range(0, 16, 2):
            assert calls[i]["seed"] == calls[i + 1]["seed"]
            assert calls[i]["model_alias"] == calls[i + 1]["model_alias"]
            assert calls[i]["temperature"] == calls[i + 1]["temperature"]
            assert calls[i]["max_tokens"] == calls[i + 1]["max_tokens"]
        assert out["provider_boundary_verdict"]["seed_semantic_passes"] == 8
        assert out["terminal_case_exposure"] == 0
        assert out["ownership_credit"] == 0

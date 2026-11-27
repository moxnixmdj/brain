from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime import whitebox_semantic_text_core_v1 as core

ROOT = Path(__file__).resolve().parents[1]
PRE = ROOT / "governance" / "WHITEBOX_SEMANTIC_TEXT_CORE_PREEXPOSURE_V1.json"


def _pre():
    doc = json.loads(PRE.read_text(encoding="utf-8"))
    assert doc["status"] == "FROZEN_BEFORE_IMPLEMENTATION_OUTCOMES__PUBLIC_SYNTHETIC_NONTERMINAL__ZERO_CREDIT"
    assert doc["terminal_cases_consumed"] == 0
    assert doc["terminal_prompt_content_used"] is False
    return doc


def test_population_was_frozen_and_has_four_by_four_shape():
    doc = _pre()
    assert set(doc["task_families"]) == {
        "paraphrase", "simplify", "summarize", "story_generation"
    }
    assert all(len(v["tasks"]) == 4 for v in doc["task_families"].values())


def test_frozen_paraphrase_population_exact_declared_rules():
    rows = _pre()["task_families"]["paraphrase"]["tasks"]
    for row in rows:
        out = core.paraphrase(row["text"])
        assert out["status"] == "PASS", (row, out)
        assert out["rule"] == row["required_rule"], (row, out)
        assert out["response"] != row["text"]
        assert out["persistent_learned_bytes"] == 0
        assert out["network_used"] is False


def test_paraphrase_abstains_outside_proved_rewrite_grammar():
    out = core.paraphrase("Please write a broad essay about an arbitrary topic.")
    assert out["status"] == "ABSTAIN_UNSUPPORTED"
    assert out["response"] is None


def test_frozen_simplify_population_preserves_normalized_content_and_reduces_complexity():
    rows = _pre()["task_families"]["simplify"]["tasks"]
    for row in rows:
        out = core.simplify(row["text"])
        assert out["status"] == "PASS", (row, out)
        assert core._normalized_content_tokens(row["text"]) == core._normalized_content_tokens(out["response"])
        assert tuple(out["complexity_after"]) < tuple(out["complexity_before"])
        assert ";" not in out["response"]
        assert out["persistent_learned_bytes"] == 0


def test_simplify_abstains_when_no_proved_rule_applies():
    out = core.simplify("This sentence is already simple.")
    assert out["status"] == "ABSTAIN_UNSUPPORTED"


def test_frozen_summarize_population_is_strictly_extractive_and_compressive():
    rows = _pre()["task_families"]["summarize"]["tasks"]
    for row in rows:
        source_sentences = core._sentences_verbatim(row["text"])
        out = core.summarize(row["text"], row["max_sentences"])
        assert out["status"] == "PASS", (row, out)
        summary_sentences = core._sentences_verbatim(out["response"])
        assert 1 <= len(summary_sentences) <= row["max_sentences"]
        assert len(summary_sentences) < len(source_sentences)
        assert len(out["response"]) < len(row["text"])
        assert all(sentence in source_sentences for sentence in summary_sentences)
        assert out["compression_ratio"] < 1.0
        assert out["persistent_learned_bytes"] == 0


def test_frozen_story_population_is_grounded_in_all_explicit_slots():
    rows = _pre()["task_families"]["story_generation"]["tasks"]
    for row in rows:
        out = core.story_generation(
            character=row["character"],
            goal=row["goal"],
            obstacle=row["obstacle"],
            setting=row["setting"],
        )
        assert out["status"] == "PASS", (row, out)
        assert out["all_grounded_fields_verbatim"] is True
        for key in ("character", "goal", "obstacle", "setting"):
            assert row[key] in out["response"]
            assert out["grounded_fields"][key] == row[key]
        assert out["persistent_learned_bytes"] == 0
        assert out["network_used"] is False


def test_shared_dispatcher_routes_all_four_families():
    assert core.produce("paraphrase", {"text": "Mira is not late."})["status"] == "PASS"
    assert core.produce("simplify", {"text": "One clause; another clause."})["status"] == "PASS"
    assert core.produce(
        "summarize",
        {"text": "One fact appears here. A second fact appears here. A third fact appears here.", "max_sentences": 1},
    )["status"] == "PASS"
    assert core.produce(
        "story_generation",
        {"character": "Ari", "goal": "find the marker", "obstacle": "dense fog", "setting": "a quiet harbor"},
    )["status"] == "PASS"


def test_unknown_family_fails_closed():
    out = core.produce("freeform_everything", {"text": "x"})
    assert out["status"] == "ABSTAIN_UNSUPPORTED"
    assert out["response"] is None


def test_zero_learned_zero_network_accounting_on_passes():
    outs = [
        core.paraphrase("All robins are birds."),
        core.simplify("Alpha remains; beta changes."),
        core.summarize("Alpha is first. Beta is second. Gamma is third.", 1),
        core.story_generation(
            character="Ari",
            goal="find the marker",
            obstacle="dense fog",
            setting="a quiet harbor",
        ),
    ]
    for out in outs:
        assert out["status"] == "PASS", out
        assert out["persistent_learned_bytes"] == 0
        assert out["external_frontier_model_calls"] == 0
        assert out["external_learned_capability_calls"] == 0
        assert out["network_used"] is False
        assert out["incremental_spend_usd"] == 0
        assert out["terminal_cases_used"] == 0

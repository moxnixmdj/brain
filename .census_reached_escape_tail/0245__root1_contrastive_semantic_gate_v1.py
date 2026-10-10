#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Mapping
import re

SCHEMA = "PROJECT_BRAIN_ROOT1_CONTRASTIVE_SEMANTIC_GATE_V1"


@dataclass(frozen=True)
class Probe:
    probe_id: str
    pair_id: str
    effect: str
    source: str
    prompt: str
    required_groups: tuple[tuple[str, ...], ...]
    forbidden_groups: tuple[tuple[str, ...], ...] = ()
    ordered_groups: tuple[tuple[str, ...], ...] = ()
    min_words: int = 1
    max_words: int = 128
    exact_sentences: int | None = None
    max_sentences: int | None = None
    require_surface_change: bool = False


def _has(value: str, group: tuple[str, ...]) -> bool:
    return any(re.search(pattern, value, flags=re.I) for pattern in group)


def _first_pos(value: str, group: tuple[str, ...], start: int = 0) -> int:
    positions: list[int] = []
    for pattern in group:
        match = re.search(pattern, value[start:], flags=re.I)
        if match:
            positions.append(start + match.start())
    return min(positions) if positions else -1


def _words(value: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'_-]*", value)


def _sentences(value: str) -> int:
    pieces = [
        x.strip()
        for x in re.split(r"(?<=[.!?])\s+|\n+", value.strip())
        if x.strip()
    ]
    return len(pieces)


def _surface_changed(source: str, output: str) -> bool:
    a = " ".join(source.lower().split())
    b = " ".join(output.lower().split())
    if not a or not b or a == b:
        return False
    return SequenceMatcher(None, a, b).ratio() < 0.96


def evaluate_output(probe: Probe, output: str) -> dict:
    value = str(output or "").strip()
    wc = len(_words(value))
    checks: dict[str, bool] = {
        "nonempty": bool(value),
        "required_semantic_facts": all(_has(value, g) for g in probe.required_groups),
        "counterfactual_facts_absent": all(
            not _has(value, g) for g in probe.forbidden_groups
        ),
        "word_range": probe.min_words <= wc <= probe.max_words,
    }

    if probe.ordered_groups:
        cursor = 0
        ordered_ok = True
        for group in probe.ordered_groups:
            pos = _first_pos(value, group, cursor)
            if pos < 0:
                ordered_ok = False
                break
            cursor = pos + 1
        checks["semantic_event_order"] = ordered_ok

    sc = _sentences(value)
    if probe.exact_sentences is not None:
        checks["exact_sentence_count"] = sc == probe.exact_sentences
    if probe.max_sentences is not None:
        checks["max_sentence_count"] = sc <= probe.max_sentences
    if probe.require_surface_change:
        checks["surface_changed"] = _surface_changed(probe.source, value)

    return {
        "schema": SCHEMA,
        "probe_id": probe.probe_id,
        "pair_id": probe.pair_id,
        "effect": probe.effect,
        "pass": all(checks.values()),
        "checks": checks,
        "word_count": wc,
        "sentence_count": sc,
    }


def frozen_probes() -> tuple[Probe, ...]:
    return (
        Probe(
            probe_id="PARA_A",
            pair_id="PARA",
            effect="text.paraphrase.semantic_preserving",
            source="On Tuesday, Neris delivered seven amber parcels to Corin before sunrise.",
            prompt="Paraphrase without changing any fact. One sentence, at most 24 words.",
            required_groups=(
                (r"\bneris\b",),
                (r"\bcorin\b",),
                (r"\btuesday\b",),
                (r"\b(?:seven|7)\b",),
                (r"\bamber\b",),
                (r"\bparcels?\b",),
                (r"\b(?:before|prior to)\b.*\bsunrise\b",),
            ),
            forbidden_groups=(
                (r"\bwednesday\b",),
                (r"\b(?:nine|9)\b",),
                (r"\bblue\b",),
                (r"\bafter\b.*\bsunset\b",),
            ),
            max_words=24,
            max_sentences=1,
            require_surface_change=True,
        ),
        Probe(
            probe_id="PARA_B",
            pair_id="PARA",
            effect="text.paraphrase.semantic_preserving",
            source="On Wednesday, Neris delivered nine blue parcels to Corin after sunset.",
            prompt="Paraphrase without changing any fact. One sentence, at most 24 words.",
            required_groups=(
                (r"\bneris\b",),
                (r"\bcorin\b",),
                (r"\bwednesday\b",),
                (r"\b(?:nine|9)\b",),
                (r"\bblue\b",),
                (r"\bparcels?\b",),
                (r"\bafter\b.*\bsunset\b",),
            ),
            forbidden_groups=(
                (r"\btuesday\b",),
                (r"\b(?:seven|7)\b",),
                (r"\bamber\b",),
                (r"\bbefore\b.*\bsunrise\b",),
            ),
            max_words=24,
            max_sentences=1,
            require_surface_change=True,
        ),
        Probe(
            probe_id="SIMPLE_A",
            pair_id="SIMPLE",
            effect="text.simplify.semantic_preserving",
            source="Because the eastern valve exceeded 82 degrees, Yusuf closed Pump 3 before transferring 45 liters to Tank B.",
            prompt="Rewrite in simple everyday English without losing any fact. One sentence, at most 24 words.",
            required_groups=(
                (r"\byusuf\b",),
                (r"\b(?:east|eastern)\b",),
                (r"\b82\b",),
                (r"\b(?:closed|shut)\b",),
                (r"\bpump[- ]?3\b",),
                (r"\bbefore\b",),
                (r"\b45\b",),
                (r"\btank[- ]?b\b",),
            ),
            forbidden_groups=(
                (r"\b(?:west|western)\b",),
                (r"\b18\b",),
                (r"\bopened\b",),
                (r"\bafter\b",),
                (r"\b15\b",),
            ),
            max_words=24,
            max_sentences=1,
            require_surface_change=True,
        ),
        Probe(
            probe_id="SIMPLE_B",
            pair_id="SIMPLE",
            effect="text.simplify.semantic_preserving",
            source="Because the western valve fell below 18 degrees, Yusuf opened Pump 3 after transferring 15 liters from Tank B.",
            prompt="Rewrite in simple everyday English without losing any fact. One sentence, at most 24 words.",
            required_groups=(
                (r"\byusuf\b",),
                (r"\b(?:west|western)\b",),
                (r"\b18\b",),
                (r"\bopened\b",),
                (r"\bpump[- ]?3\b",),
                (r"\bafter\b",),
                (r"\b15\b",),
                (r"\btank[- ]?b\b",),
            ),
            forbidden_groups=(
                (r"\b(?:east|eastern)\b",),
                (r"\b82\b",),
                (r"\b(?:closed|shut)\b",),
                (r"\bbefore\b",),
                (r"\b45\b",),
            ),
            max_words=24,
            max_sentences=1,
            require_surface_change=True,
        ),
        Probe(
            probe_id="SUM_A",
            pair_id="SUM",
            effect="text.summarize.faithful",
            source="Train 8 was delayed 35 minutes outside Luxor. Engineers inspected two signal boxes. No damage was found. Train 8 reached Aswan at 21:10.",
            prompt="Summarize in one sentence of at most 30 words while preserving the key outcome.",
            required_groups=(
                (r"\btrain[- ]?8\b",),
                (r"\bluxor\b",),
                (r"\b35\b",),
                (r"\b(?:two|2)\b",),
                (r"\bno damage\b|\bundamaged\b",),
                (r"\baswan\b",),
                (r"\b21:10\b",),
            ),
            forbidden_groups=(
                (r"\b50\b",),
                (r"\bedfu\b",),
                (r"\b(?:three|3)\b.*\bsignal",),
                (r"\bdamaged\b",),
                (r"\b22:40\b",),
            ),
            max_words=30,
            max_sentences=1,
        ),
        Probe(
            probe_id="SUM_B",
            pair_id="SUM",
            effect="text.summarize.faithful",
            source="Train 8 stopped for 50 minutes near Edfu. Engineers inspected three signal boxes and found damage. Train 8 returned to Luxor at 22:40.",
            prompt="Summarize in one sentence of at most 30 words while preserving the key outcome.",
            required_groups=(
                (r"\btrain[- ]?8\b",),
                (r"\b50\b",),
                (r"\bedfu\b",),
                (r"\b(?:three|3)\b",),
                (r"\bdamage\b",),
                (r"\bluxor\b",),
                (r"\b22:40\b",),
            ),
            forbidden_groups=(
                (r"\b35\b",),
                (r"\baswan\b",),
                (r"\bno damage\b|\bundamaged\b",),
                (r"\b21:10\b",),
            ),
            max_words=30,
            max_sentences=1,
        ),
        Probe(
            probe_id="STORY_A",
            pair_id="STORY",
            effect="text.story.generate_instruction_grounded",
            source="",
            prompt="Write exactly three short sentences. ORION-7 finds BRASS-KEY at GATE-2, then crosses HARBOR-9, then returns BRASS-KEY to MIRA-1.",
            required_groups=(
                (r"\borion-7\b",),
                (r"\bbrass-key\b",),
                (r"\bgate-2\b",),
                (r"\bharbor-9\b",),
                (r"\bmira-1\b",),
            ),
            forbidden_groups=((r"\bsilver-ring\b",), (r"\btunnel-4\b",)),
            ordered_groups=(
                (r"\borion-7\b.*\bbrass-key\b",),
                (r"\bgate-2\b",),
                (r"\bharbor-9\b",),
                (r"\bbrass-key\b.*\bmira-1\b",),
            ),
            min_words=12,
            max_words=80,
            exact_sentences=3,
        ),
        Probe(
            probe_id="STORY_B",
            pair_id="STORY",
            effect="text.story.generate_instruction_grounded",
            source="",
            prompt="Write exactly three short sentences. ORION-7 finds SILVER-RING at GATE-2, then crosses TUNNEL-4, then gives SILVER-RING to MIRA-1.",
            required_groups=(
                (r"\borion-7\b",),
                (r"\bsilver-ring\b",),
                (r"\bgate-2\b",),
                (r"\btunnel-4\b",),
                (r"\bmira-1\b",),
            ),
            forbidden_groups=((r"\bbrass-key\b",), (r"\bharbor-9\b",)),
            ordered_groups=(
                (r"\borion-7\b.*\bsilver-ring\b",),
                (r"\bgate-2\b",),
                (r"\btunnel-4\b",),
                (r"\bsilver-ring\b.*\bmira-1\b",),
            ),
            min_words=12,
            max_words=80,
            exact_sentences=3,
        ),
    )


def evaluate_suite(outputs: Mapping[str, str]) -> dict:
    probes = frozen_probes()
    results = [evaluate_output(p, str(outputs.get(p.probe_id, ""))) for p in probes]
    by_pair: dict[str, list[Probe]] = {}
    for p in probes:
        by_pair.setdefault(p.pair_id, []).append(p)

    pair_checks: dict[str, bool] = {}
    for pair_id, members in by_pair.items():
        values = [
            " ".join(str(outputs.get(p.probe_id, "")).lower().split())
            for p in members
        ]
        pair_checks[pair_id] = (
            len(values) == 2 and bool(values[0]) and bool(values[1]) and values[0] != values[1]
        )

    effects = {p.effect for p in probes}
    effect_pass = {
        effect: all(r["pass"] for r in results if r["effect"] == effect)
        for effect in sorted(effects)
    }
    passed = (
        all(r["pass"] for r in results)
        and all(pair_checks.values())
        and all(effect_pass.values())
    )
    return {
        "schema": SCHEMA,
        "status": "PASS" if passed else "FAIL",
        "pass": passed,
        "case_pass_count": sum(1 for r in results if r["pass"]),
        "case_count": len(results),
        "pair_distinction_checks": pair_checks,
        "effect_pass": effect_pass,
        "results": results,
        "claim_scope": "BOUNDED_CONTRASTIVE_NONTERMINAL_SEMANTIC_TRANSFORMATION_GATE_ONLY",
        "terminal_credit": 0,
        "acceptance_credit": 0,
    }


def run(args: dict | None = None, root=None) -> dict:
    return evaluate_suite((args or {}).get("outputs") or {})

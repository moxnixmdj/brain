#!/usr/bin/env python3
"""Meaning-sensitive provider-boundary gate for Root1 substrate selection.

This scorer never calls a model. It evaluates a frozen pair of outputs from the
same exact candidate subject:

1. semantic seed: subject receives only the semantic request;
2. direct: subject receives semantic request + frozen formal overlay;
3. Brain-composed: deterministic seed-preserving postprocessor receives (1).

A passing bounded signal requires the semantic seed to remain valid, the exact
Brain route to pass every paired case, and the direct model-only route to lose
enough cases that the Brain-owned layer is materially causal. This is a
substrate-selection gate, not LiveBench acceptance evidence.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from canonical.runtime import instruction_constraint_compiler_v1 as compiler
from canonical.runtime import seed_preserving_instruction_postprocessor_v2 as composer

SCHEMA = "PROJECT_BRAIN_ROOT1_MEANING_SENSITIVE_OWNERSHIP_GATE_RUNTIME_V1"
ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "canonical/governance/ROOT1_MEANING_SENSITIVE_OWNERSHIP_GATE_V1.json"
SUITE_PATH = ROOT / "canonical/governance/LIVEBENCH_ROOT1_QWEN38_4B_SEMANTIC_SEED_PRECOMMIT_V1.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _norm(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _words(text: str) -> list[str]:
    return re.findall(r"\b\w+(?:[-']\w+)*\b", str(text or ""), flags=re.UNICODE)


def _sentence_count(text: str) -> int:
    value = str(text or "").strip()
    if not value:
        return 0
    marks = re.findall(r"[.!?]+(?=\s|$)", value)
    return len(marks) if marks else 1


def _group_positions(value: str, group: list[str]) -> tuple[int, int] | None:
    v = _norm(value)
    positions = []
    for term in group:
        p = v.find(_norm(term))
        if p < 0:
            return None
        positions.append(p)
    return min(positions), max(positions)


def semantic_case_check(case: dict[str, Any], output: str) -> dict[str, Any]:
    value = str(output or "").strip()
    errors: list[str] = []
    low = _norm(value)

    for i, group in enumerate(case.get("required_groups") or []):
        if not any(_norm(term) in low for term in group):
            errors.append(f"REQUIRED_GROUP_{i}")

    ordered = case.get("ordered_groups") or []
    if ordered:
        spans = [_group_positions(value, list(group)) for group in ordered]
        if any(span is None for span in spans):
            errors.append("ORDERED_GROUP_MISSING")
        else:
            assert all(span is not None for span in spans)
            for left, right in zip(spans, spans[1:]):
                if left[1] >= right[0]:
                    errors.append("ORDERED_GROUP_SEQUENCE")
                    break

    source = str(case.get("source") or "").strip()
    if case.get("forbidden_exact") and source and _norm(value) == _norm(source):
        errors.append("FORBIDDEN_EXACT_SOURCE")
    if case.get("min_source_change") and source and _norm(value) == _norm(source):
        errors.append("MIN_SOURCE_CHANGE")

    wc = len(_words(value))
    if case.get("max_words") is not None and wc > int(case["max_words"]):
        errors.append("MAX_WORDS")
    sc = _sentence_count(value)
    if case.get("max_sentences") is not None and sc > int(case["max_sentences"]):
        errors.append("MAX_SENTENCES")
    if case.get("exact_sentences") is not None and sc != int(case["exact_sentences"]):
        errors.append("EXACT_SENTENCES")

    return {
        "pass": not errors,
        "errors": errors,
        "word_count": wc,
        "sentence_count": sc,
    }


def formal_overlay_check(overlay: str, output: str) -> dict[str, Any]:
    constraints = compiler.compile_constraints(overlay)
    ok, errors = compiler.validate_response(str(output or ""), constraints)
    return {"pass": bool(ok), "errors": list(errors)}


def evaluate(records: dict[str, dict[str, str]]) -> dict[str, Any]:
    gate = _load_json(GATE_PATH)
    suite = _load_json(SUITE_PATH)
    overlays = dict(gate["formal_overlays"])
    cases = list(suite["frozen_nonterminal_suite"])

    by_case: dict[str, Any] = {}
    seed_semantic_passes = 0
    direct_full_passes = 0
    brain_full_passes = 0
    rescue_ids: list[str] = []
    rescue_effects: set[str] = set()

    for case in cases:
        cid = str(case["id"])
        rec = dict((records or {}).get(cid) or {})
        seed = str(rec.get("seed") or "")
        direct = str(rec.get("direct") or "")
        overlay = str(overlays[cid])

        seed_sem = semantic_case_check(case, seed)
        direct_sem = semantic_case_check(case, direct)
        direct_formal = formal_overlay_check(overlay, direct)

        composed = composer.transform(seed, overlay)
        composed_text = str(composed.get("response") or "")
        # Semantic truth is evaluated on the original seed nucleus. The composer
        # is separately required to preserve that seed byte-for-byte. Structural
        # punctuation wrappers must never perturb semantic scoring.
        brain_sem = seed_sem if composed.get("status") == "PASS" else {
            "pass": False,
            "errors": ["COMPOSER_FAIL_CLOSED"],
        }
        brain_formal = formal_overlay_check(overlay, composed_text) if composed.get("status") == "PASS" else {
            "pass": False,
            "errors": ["COMPOSER_FAIL_CLOSED"],
        }

        seed_ok = bool(seed_sem["pass"])
        direct_full = bool(direct_sem["pass"] and direct_formal["pass"])
        brain_full = bool(
            composed.get("status") == "PASS"
            and composed.get("seed_verbatim_preserved") is True
            and brain_sem["pass"]
            and brain_formal["pass"]
        )

        seed_semantic_passes += int(seed_ok)
        direct_full_passes += int(direct_full)
        brain_full_passes += int(brain_full)

        rescued = bool(seed_ok and not direct_full and brain_full)
        if rescued:
            rescue_ids.append(cid)
            rescue_effects.add(str(case["effect"]))

        by_case[cid] = {
            "effect": case["effect"],
            "seed_semantic": seed_sem,
            "direct_semantic": direct_sem,
            "direct_overlay": direct_formal,
            "brain_composer_status": composed.get("status"),
            "brain_seed_verbatim_preserved": composed.get("seed_verbatim_preserved") is True,
            "brain_semantic": brain_sem,
            "brain_overlay": brain_formal,
            "direct_full_pass": direct_full,
            "brain_full_pass": brain_full,
            "rescued": rescued,
        }

    total = len(cases)
    if seed_semantic_passes != total:
        verdict = "REJECT_SUBSTRATE_SEMANTIC_INSUFFICIENT"
    elif brain_full_passes != total:
        verdict = "REJECT_BRAIN_COMPOSITION_INSUFFICIENT"
    elif direct_full_passes >= total - 1:
        verdict = "REJECT_PROVIDER_ALREADY_SUPPLIES_BOUNDED_TARGET"
    elif len(rescue_ids) < 2 or len(rescue_effects) < 2:
        verdict = "REJECT_CAUSAL_RESCUE_NOT_MATERIAL"
    else:
        verdict = "PASS_BOUNDED_PROVIDER_BOUNDARY_SIGNAL"

    return {
        "schema": SCHEMA,
        "status": verdict,
        "case_count": total,
        "seed_semantic_passes": seed_semantic_passes,
        "direct_full_passes": direct_full_passes,
        "brain_full_passes": brain_full_passes,
        "rescued_case_count": len(rescue_ids),
        "rescued_cases": rescue_ids,
        "rescued_effect_count": len(rescue_effects),
        "rescued_effects": sorted(rescue_effects),
        "cases": by_case,
        "model_calls_performed_by_gate": 0,
        "network_used_by_gate": False,
        "incremental_spend_usd": 0,
        "terminal_cases_used": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "hard_nonclaim": "BOUNDED_PUBLIC_PROVIDER_BOUNDARY_SIGNAL_ONLY__NOT_LIVEBENCH_OR_OPEN_WORLD_SEMANTIC_ACCEPTANCE",
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return evaluate(dict((args or {}).get("records") or {}))

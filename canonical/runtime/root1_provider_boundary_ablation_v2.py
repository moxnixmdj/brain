#!/usr/bin/env python3
"""Causal external-provider boundary gate over the current Root1 semantic gate.

This module deliberately owns no semantic ontology. Meaning-sensitive truth comes
from root1_contrastive_semantic_gate_v1. The Brain layer under test is the
content-bound seed-preserving formal composer.

For each frozen semantic probe it compares:
  seed   = exact candidate subject on semantic request only
  direct = same exact subject on semantic request + frozen formal overlay
  brain  = deterministic Brain composer(seed, overlay), with zero model calls

A PASS is only a bounded substrate-selection/provider-boundary signal.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import instruction_constraint_compiler_v1 as compiler
from canonical.runtime import root1_contrastive_semantic_gate_v1 as semantic_gate
from canonical.runtime import seed_preserving_instruction_postprocessor_v2 as composer

SCHEMA = "PROJECT_BRAIN_ROOT1_PROVIDER_BOUNDARY_ABLATION_RUNTIME_V2"
ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE = ROOT / "canonical/governance/ROOT1_PROVIDER_BOUNDARY_ABLATION_V2.json"


def _governance() -> dict[str, Any]:
    return json.loads(GOVERNANCE.read_text(encoding="utf-8"))


def formal_check(instruction: str, output: str) -> dict[str, Any]:
    constraints = compiler.compile_constraints(str(instruction))
    ok, errors = compiler.validate_response(str(output or ""), constraints)
    return {"pass": bool(ok), "errors": list(errors)}


def evaluate(records: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
    cfg = _governance()
    overlays = dict(cfg["formal_overlays"])
    probes = semantic_gate.frozen_probes()

    rows: dict[str, Any] = {}
    seed_semantic_passes = 0
    direct_full_passes = 0
    brain_full_passes = 0
    rescued: list[str] = []
    rescue_effects: set[str] = set()

    for probe in probes:
        pid = probe.probe_id
        rec = dict(records.get(pid) or {})
        seed = str(rec.get("seed") or "")
        direct = str(rec.get("direct") or "")
        overlay = str(overlays[pid])

        seed_sem = semantic_gate.evaluate_output(probe, seed)
        direct_sem = semantic_gate.evaluate_output(probe, direct)
        direct_formal = formal_check(overlay, direct)

        composed = composer.transform(seed, overlay)
        composed_text = str(composed.get("response") or "")
        brain_formal = (
            formal_check(overlay, composed_text)
            if composed.get("status") == "PASS"
            else {"pass": False, "errors": ["COMPOSER_FAIL_CLOSED"]}
        )

        seed_ok = bool(seed_sem["pass"])
        direct_full = bool(direct_sem["pass"] and direct_formal["pass"])
        brain_full = bool(
            seed_ok
            and composed.get("status") == "PASS"
            and composed.get("seed_verbatim_preserved") is True
            and seed in composed_text
            and brain_formal["pass"]
        )

        seed_semantic_passes += int(seed_ok)
        direct_full_passes += int(direct_full)
        brain_full_passes += int(brain_full)

        is_rescue = bool(seed_ok and not direct_full and brain_full)
        if is_rescue:
            rescued.append(pid)
            rescue_effects.add(probe.effect)

        rows[pid] = {
            "pair_id": probe.pair_id,
            "effect": probe.effect,
            "seed_semantic": seed_sem,
            "direct_semantic": direct_sem,
            "direct_formal": direct_formal,
            "direct_full_pass": direct_full,
            "brain_composer_status": composed.get("status"),
            "brain_seed_verbatim_preserved": composed.get("seed_verbatim_preserved") is True,
            "brain_formal": brain_formal,
            "brain_full_pass": brain_full,
            "rescued": is_rescue,
        }

    total = len(probes)
    if seed_semantic_passes != total:
        status = "REJECT_SUBSTRATE_SEMANTIC_INSUFFICIENT"
    elif brain_full_passes != total:
        status = "REJECT_BRAIN_COMPOSITION_INSUFFICIENT"
    elif direct_full_passes >= total - 1:
        status = "REJECT_PROVIDER_ALREADY_SUPPLIES_BOUNDED_TARGET"
    elif len(rescued) < 2 or len(rescue_effects) < 2:
        status = "REJECT_CAUSAL_RESCUE_NOT_MATERIAL"
    else:
        status = "PASS_BOUNDED_PROVIDER_BOUNDARY_SIGNAL"

    return {
        "schema": SCHEMA,
        "status": status,
        "case_count": total,
        "seed_semantic_passes": seed_semantic_passes,
        "direct_full_passes": direct_full_passes,
        "brain_full_passes": brain_full_passes,
        "rescued_case_count": len(rescued),
        "rescued_cases": rescued,
        "rescued_effect_count": len(rescue_effects),
        "rescued_effects": sorted(rescue_effects),
        "cases": rows,
        "model_calls_performed_by_gate": 0,
        "network_used_by_gate": False,
        "incremental_spend_usd": 0,
        "terminal_cases_used": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "hard_nonclaim": (
            "BOUNDED_PROVIDER_BOUNDARY_SIGNAL_ONLY__NOT_LIVEBENCH_ACCEPTANCE_"
            "OR_OPEN_WORLD_SEMANTIC_OWNERSHIP"
        ),
    }


def run(args: dict[str, Any] | None = None, root=None) -> dict[str, Any]:
    return evaluate(dict((args or {}).get("records") or {}))

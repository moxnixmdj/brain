"""Fail-closed guard for the OpenAI-math -> Astra qualitative calibration relation.

Official OpenAI pages support a cross-page reference from the Oct 6 mathematics
release to the Sep 8 internal-model report, where OpenAI describes the model used
for Navier-Stokes as significantly more capable than GPT-6 Astra.

That is useful evidence, but it is not a proof of checkpoint identity, per-context
distributional dominance, or any transitive terminal relation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_OPENAI_MATH_ASTRA_CALIBRATION_GUARD_V1"
WITNESS_SCHEMA = "PROJECT_BRAIN_OPENAI_MATH_ASTRA_QUALITATIVE_CALIBRATION_WITNESS_V1"
ROOT = Path(__file__).resolve().parents[2]
LIVE_WITNESS = ROOT / "canonical/governance/OPENAI_MATH_ASTRA_QUALITATIVE_CALIBRATION_20261007_V1.json"


def evaluate(witness: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(witness, Mapping):
        return _fail(["WITNESS_NOT_OBJECT"])
    if witness.get("schema") != WITNESS_SCHEMA:
        errors.append("WITNESS_SCHEMA_MISMATCH")
    linkage = witness.get("official_cross_page_linkage")
    if not isinstance(linkage, Mapping):
        errors.append("OFFICIAL_CROSS_PAGE_LINKAGE_MISSING")
    else:
        if linkage.get("oct6_internal_frontier_anchor_targets_sep8_navier_page") is not True:
            errors.append("OFFICIAL_LINKAGE_NOT_CAPTURED")
        if linkage.get("sep8_astra_superiority_statement_present") is not True:
            errors.append("ASTRA_SUPERIORITY_STATEMENT_NOT_CAPTURED")

    boundaries = witness.get("semantic_boundaries")
    if not isinstance(boundaries, Mapping):
        errors.append("SEMANTIC_BOUNDARIES_MISSING")
    else:
        if boundaries.get("exact_checkpoint_identity_proved") is not False:
            errors.append("EXACT_CHECKPOINT_IDENTITY_MUST_REMAIN_UNPROVED")
        if boundaries.get("per_context_distributional_dominance_proved") is not False:
            errors.append("DISTRIBUTIONAL_DOMINANCE_MUST_REMAIN_UNPROVED")
        if boundaries.get("target_opus_relation_proved") is not False:
            errors.append("OPUS_RELATION_MUST_REMAIN_UNPROVED")
        if boundaries.get("external_page_immutability_proved") is not False:
            errors.append("EXTERNAL_PAGE_IMMUTABILITY_MUST_REMAIN_UNPROVED")

    if witness.get("qualitative_calibration_use") != "ASTRA_SUPERIOR_INTERNAL_MODEL_LINEAGE_EVIDENCE_ONLY":
        errors.append("QUALITATIVE_CALIBRATION_SCOPE_MISMATCH")

    if errors:
        return _fail(sorted(set(errors)))
    return {
        "schema": SCHEMA,
        "status": "PASS__QUALITATIVE_ASTRA_SUPERIOR_LINEAGE_EVIDENCE_ONLY__ZERO_CREDIT",
        "official_cross_page_linkage_supported": True,
        "qualitative_astra_superiority_statement_supported": True,
        "exact_checkpoint_identity_proved": False,
        "per_context_distributional_dominance_proved": False,
        "target_opus_relation_proved": False,
        "may_rank_corpus_as_frontier_beyond_astra_signal": True,
        "may_use_as_matched_astra_dominance_certificate": False,
        "may_use_for_terminal_transitivity": False,
        "must_revalidate_external_pages_before_load_bearing_use": True,
        "terminal_credit_delta": 0,
        "capability_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "errors": [],
    }


def _fail(errors: list[str]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "terminal_credit_delta": 0,
        "capability_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "errors": errors,
    }


def evaluate_live() -> dict[str, Any]:
    return evaluate(json.loads(LIVE_WITNESS.read_text(encoding="utf-8")))


def main() -> int:
    out = evaluate_live()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["status"].startswith("PASS__") else 1


if __name__ == "__main__":
    raise SystemExit(main())

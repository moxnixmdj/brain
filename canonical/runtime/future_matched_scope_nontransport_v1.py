"""Future-matched-population scope non-transport gate v1.

A finite empirical population observed before the frozen matched target cases
exist cannot, by itself, prove EXACT or SUPERSET coverage of those future cases.
Only an independently verified universal/exhaustive scope proof may bypass this
gate. This is proof-routing authority only and grants zero capability credit.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SUPER = ROOT / "canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json"

SCHEMA = "PROJECT_BRAIN_FUTURE_MATCHED_SCOPE_NONTRANSPORT_V1"
ALLOWED_ESCAPE_BASES = {"UNIVERSAL_FORMAL_SCOPE_PROOF", "EXHAUSTIVE_FINITE_SUPERSET"}


def _valid_escape(cert: Mapping[str, Any] | None) -> bool:
    if not isinstance(cert, Mapping):
        return False
    if cert.get("verified") is not True or cert.get("independent") is not True:
        return False
    basis = cert.get("basis")
    if basis == "UNIVERSAL_FORMAL_SCOPE_PROOF":
        return (
            cert.get("all_admissible_target_inputs_proved") is True
            and cert.get("formal_completeness") is True
            and isinstance(cert.get("receipt"), str)
            and bool(cert.get("receipt"))
        )
    if basis == "EXHAUSTIVE_FINITE_SUPERSET":
        return (
            cert.get("exhaustive") is True
            and cert.get("target_subset_proved") is True
            and isinstance(cert.get("receipt"), str)
            and bool(cert.get("receipt"))
        )
    return False


def evaluate(
    superportfolio: Mapping[str, Any],
    scope_completeness_by_family: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    cg = superportfolio.get("case_generation")
    adm = superportfolio.get("comparator_admissibility")
    core = superportfolio.get("core_families")
    if not isinstance(cg, Mapping):
        errors.append("CASE_GENERATION_MISSING")
    if not isinstance(adm, Mapping):
        errors.append("COMPARATOR_ADMISSIBILITY_MISSING")
    if not isinstance(core, list) or not core:
        errors.append("CORE_FAMILIES_MISSING")
    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": errors,
            "family_results": [],
            "execution_authority": False,
            "promotion_authority": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "new_reality_units_consumed": 0,
        }

    target_uninstantiated = (
        cg.get("generated_now") is False
        and cg.get("exposed_now") is False
        and cg.get("beacon_known_now") is False
    )
    comparator_blocked = adm.get("current_state") == "BLOCKED"
    certs = scope_completeness_by_family or {}
    rows = []
    for row in core:
        if not isinstance(row, Mapping) or not isinstance(row.get("family"), str):
            errors.append("MALFORMED_CORE_FAMILY")
            continue
        family = row["family"]
        escape = certs.get(family)
        escape_ok = _valid_escape(escape)
        if target_uninstantiated and not escape_ok:
            disposition = "FINITE_EMPIRICAL_SCOPE_TRANSPORT_FORBIDDEN"
            exact_or_superset_from_observed_sample = False
        elif escape_ok:
            disposition = "UNIVERSAL_OR_EXHAUSTIVE_SCOPE_ESCAPE_VERIFIED"
            exact_or_superset_from_observed_sample = None
        else:
            disposition = "TARGET_POPULATION_INSTANTIATED__THIS_GATE_NO_LONGER_DECIDES_SCOPE"
            exact_or_superset_from_observed_sample = None
        rows.append({
            "family": family,
            "target_population_instantiated": not target_uninstantiated,
            "comparator_currently_blocked": comparator_blocked,
            "scope_escape_verified": escape_ok,
            "finite_observed_sample_can_establish_future_exact_or_superset_scope": exact_or_superset_from_observed_sample,
            "disposition": disposition,
        })

    return {
        "schema": SCHEMA,
        "status": "PASS__FUTURE_MATCHED_SCOPE_NONTRANSPORT_COMPILED__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "future_target_population_uninstantiated": target_uninstantiated,
        "future_beacon_unknown": cg.get("beacon_known_now") is False,
        "matched_cases_generated_now": cg.get("generated_now") is True,
        "exact_comparator_current_state": adm.get("current_state"),
        "family_count": len(rows),
        "blocked_finite_empirical_transport_count": sum(
            r["disposition"] == "FINITE_EMPIRICAL_SCOPE_TRANSPORT_FORBIDDEN" for r in rows
        ),
        "family_results": rows,
        "rule": (
            "UNKNOWN_FUTURE_BEACON_SELECTED_TARGET_CASES_CANNOT_BE_PROVED_EXACT_OR_SUBSET_OF_"
            "AN_ALREADY_OBSERVED_FINITE_SAMPLE_BY_SAMPLE_SUCCESS_ALONE__"
            "ONLY_INDEPENDENT_UNIVERSAL_FORMAL_OR_EXHAUSTIVE_SUPERSET_SCOPE_PROOF_MAY_BYPASS"
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
    }


def main() -> int:
    doc = json.loads(SUPER.read_text(encoding="utf-8"))
    out = evaluate(doc)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

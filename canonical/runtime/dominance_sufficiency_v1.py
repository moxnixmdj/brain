from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence
import re

INPUT_SCHEMA = "PROJECT_BRAIN_DOMINANCE_SUFFICIENCY_INPUT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_DOMINANCE_SUFFICIENCY_OUTPUT_V1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")


class DominanceSufficiencyError(ValueError):
    pass


def _token(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DominanceSufficiencyError(field + "_INVALID")
    return value.strip()


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool):
        raise DominanceSufficiencyError(field + "_INVALID")
    try:
        out = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise DominanceSufficiencyError(field + "_INVALID") from exc
    if not out.is_finite():
        raise DominanceSufficiencyError(field + "_NONFINITE")
    return out


def _receipt(value: Any, field: str, required_true: Sequence[str] = ()) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DominanceSufficiencyError(field + "_INVALID")
    path = _token(value.get("path"), field + "_PATH")
    sha = _token(value.get("git_blob_sha"), field + "_SHA").lower()
    if not HEX40.fullmatch(sha):
        raise DominanceSufficiencyError(field + "_SHA_INVALID")
    for key in required_true:
        if value.get(key) is not True:
            raise DominanceSufficiencyError(field + "_" + key.upper() + "_NOT_TRUE")
    return {"path": path, "git_blob_sha": sha, **{k: True for k in required_true}}


def compile_dominance_sufficiency(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
            raise DominanceSufficiencyError("SCHEMA_INVALID")

        coverage = _receipt(
            doc.get("hypothesis_coverage_receipt"),
            "HYPOTHESIS_COVERAGE_RECEIPT",
            ("scope_complete", "independent_or_objective"),
        )

        raw_hypotheses = doc.get("hypotheses")
        if not isinstance(raw_hypotheses, list):
            raise DominanceSufficiencyError("HYPOTHESES_INVALID")
        live: list[str] = []
        seen_h: set[str] = set()
        for index, raw in enumerate(raw_hypotheses):
            if not isinstance(raw, Mapping):
                raise DominanceSufficiencyError(f"HYPOTHESIS_{index}_INVALID")
            hid = _token(raw.get("id"), f"HYPOTHESIS_{index}_ID")
            if hid in seen_h:
                raise DominanceSufficiencyError("HYPOTHESIS_ID_DUPLICATE:" + hid)
            seen_h.add(hid)
            plausible = raw.get("plausible")
            if not isinstance(plausible, bool):
                raise DominanceSufficiencyError(f"HYPOTHESIS_{index}_PLAUSIBLE_INVALID")
            if plausible:
                live.append(hid)
        if not live:
            raise DominanceSufficiencyError("NO_LIVE_HYPOTHESES")

        raw_configs = doc.get("configurations")
        if not isinstance(raw_configs, list) or not raw_configs:
            raise DominanceSufficiencyError("CONFIGURATIONS_INVALID")

        seen_c: set[str] = set()
        candidates: list[dict[str, Any]] = []
        for index, raw in enumerate(raw_configs):
            if not isinstance(raw, Mapping):
                raise DominanceSufficiencyError(f"CONFIGURATION_{index}_INVALID")
            cid = _token(raw.get("id"), f"CONFIGURATION_{index}_ID")
            if cid in seen_c:
                raise DominanceSufficiencyError("CONFIGURATION_ID_DUPLICATE:" + cid)
            seen_c.add(cid)

            brain_owned = raw.get("brain_owned")
            if not isinstance(brain_owned, bool):
                raise DominanceSufficiencyError(f"CONFIGURATION_{index}_BRAIN_OWNED_INVALID")
            if not brain_owned:
                continue

            ownership = _receipt(
                raw.get("ownership_receipt"),
                f"CONFIGURATION_{index}_OWNERSHIP_RECEIPT",
                ("donor_independent", "independent_or_objective"),
            )
            bounds = raw.get("bounds")
            if not isinstance(bounds, Mapping):
                raise DominanceSufficiencyError(f"CONFIGURATION_{index}_BOUNDS_INVALID")
            if set(map(str, bounds.keys())) != set(live):
                raise DominanceSufficiencyError(
                    f"CONFIGURATION_{index}_LIVE_HYPOTHESIS_BOUND_SET_MISMATCH"
                )

            margins: dict[str, Decimal] = {}
            bound_receipts: dict[str, dict[str, Any]] = {}
            for hid in live:
                cell = bounds.get(hid)
                if not isinstance(cell, Mapping):
                    raise DominanceSufficiencyError(
                        f"CONFIGURATION_{index}_{hid}_BOUND_INVALID"
                    )
                brain_lower = _decimal(
                    cell.get("brain_lower"),
                    f"CONFIGURATION_{index}_{hid}_BRAIN_LOWER",
                )
                comparator_upper = _decimal(
                    cell.get("comparator_upper"),
                    f"CONFIGURATION_{index}_{hid}_COMPARATOR_UPPER",
                )
                receipt = _receipt(
                    cell.get("bound_receipt"),
                    f"CONFIGURATION_{index}_{hid}_BOUND_RECEIPT",
                    ("scope_complete", "independent_or_objective"),
                )
                margins[hid] = brain_lower - comparator_upper
                bound_receipts[hid] = receipt

            worst = min(margins.values())
            candidates.append(
                {
                    "id": cid,
                    "worst_case_margin": worst,
                    "margins": margins,
                    "ownership_receipt": ownership,
                    "bound_receipts": bound_receipts,
                }
            )

        robust = [c for c in candidates if c["worst_case_margin"] >= 0]
        if not robust:
            return {
                "schema": OUTPUT_SCHEMA,
                "status": "OPEN__NO_ROBUST_NONINFERIOR_BRAIN_OWNED_CONFIGURATION",
                "live_hypotheses": sorted(live),
                "hypothesis_coverage_receipt": coverage,
                "robust_configuration_exists": False,
                "additional_target_information_required_by_this_certificate": True,
                "acceptance_credit_delta": 0,
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
                "execution_authority": False,
                "promotion_authority": False,
                "fresh_reality_authority": False,
            }

        robust.sort(key=lambda c: (-c["worst_case_margin"], c["id"]))
        winner = robust[0]
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "PASS__DOMINANCE_SUFFICIENT_WITHOUT_HYPOTHESIS_DISAMBIGUATION",
            "live_hypotheses": sorted(live),
            "hypothesis_coverage_receipt": coverage,
            "robust_configuration_exists": True,
            "selected_configuration": winner["id"],
            "worst_case_margin": str(winner["worst_case_margin"]),
            "margin_by_hypothesis": {
                hid: str(winner["margins"][hid]) for hid in sorted(winner["margins"])
            },
            "ownership_receipt": winner["ownership_receipt"],
            "bound_receipts": {
                hid: winner["bound_receipts"][hid] for hid in sorted(winner["bound_receipts"])
            },
            "additional_target_information_required_by_this_certificate": False,
            "theorem": (
                "IF_THE_HYPOTHESIS_SET_IS_SCOPE_COMPLETE_AND_ONE_DURABLY_BRAIN_OWNED_"
                "CONFIGURATION_HAS_A_VERIFIED_BRAIN_LOWER_BOUND_NOT_BELOW_THE_VERIFIED_"
                "COMPARATOR_UPPER_BOUND_IN_EVERY_LIVE_HYPOTHESIS_THEN_NO_HYPOTHESIS_"
                "DISAMBIGUATION_IS_REQUIRED_TO_CERTIFY_NONINFERIORITY"
            ),
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }
    except DominanceSufficiencyError as exc:
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }

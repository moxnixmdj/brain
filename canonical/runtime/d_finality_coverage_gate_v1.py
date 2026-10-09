"""Fail-closed D-finality coverage reducer V1.

This reducer separates structural live admission from D-final ownership.

Provider-level execution theorems may be reused across capability rows, but every
live capability identity still requires its own current D-final certificate and
member material certificate. This prevents executor-class reuse from laundering
different material/dependency closures into one ownership claim.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_D_FINALITY_COVERAGE_GATE_V1"
REGISTRY_SCHEMA = "PROJECT_BRAIN_D_FINALITY_CERTIFICATE_REGISTRY_V1"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


class DFinalityCoverageError(ValueError):
    pass


def _ids(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise DFinalityCoverageError(label + "_NOT_SEQUENCE")
    out: list[str] = []
    for raw in value:
        cid = str(raw or "").strip()
        if not cid:
            raise DFinalityCoverageError(label + "_ITEM_INVALID")
        out.append(cid)
    if len(out) != len(set(out)):
        raise DFinalityCoverageError(label + "_DUPLICATE")
    return sorted(out)


def _hex64(value: Any, label: str) -> str:
    text = str(value or "").lower()
    if not _HEX64.fullmatch(text):
        raise DFinalityCoverageError(label + "_INVALID")
    return text


def _hex40(value: Any, label: str) -> str:
    text = str(value or "").lower()
    if not _HEX40.fullmatch(text):
        raise DFinalityCoverageError(label + "_INVALID")
    return text


def evaluate(
    live_admitted_capability_ids: Sequence[str],
    registry: Mapping[str, Any],
) -> dict[str, Any]:
    live = _ids(live_admitted_capability_ids, "LIVE_ADMITTED_CAPABILITY_IDS")
    if not isinstance(registry, Mapping):
        raise DFinalityCoverageError("REGISTRY_NOT_OBJECT")
    if registry.get("schema") != REGISTRY_SCHEMA:
        raise DFinalityCoverageError("REGISTRY_SCHEMA_INVALID")
    if registry.get("status") != "ACTIVE_FAIL_CLOSED":
        raise DFinalityCoverageError("REGISTRY_NOT_ACTIVE")
    if registry.get("default") != "NOT_D_FINAL_UNLESS_EXACT_CURRENT_ROW":
        raise DFinalityCoverageError("REGISTRY_DEFAULT_NOT_FAIL_CLOSED")

    rows = registry.get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        raise DFinalityCoverageError("REGISTRY_ROWS_NOT_SEQUENCE")

    by_id: dict[str, dict[str, Any]] = {}
    provider_theorem_to_members: dict[str, list[str]] = {}
    for index, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise DFinalityCoverageError(f"ROW_NOT_OBJECT:{index}")
        cid = str(raw.get("capability_id") or "").strip()
        if not cid:
            raise DFinalityCoverageError(f"ROW_CAPABILITY_ID_INVALID:{index}")
        if cid in by_id:
            raise DFinalityCoverageError("DUPLICATE_CAPABILITY_ROW:" + cid)
        if raw.get("status") != "VERIFIED_D_FINAL_CURRENT":
            continue

        d_cert = _hex64(raw.get("d_certificate_sha256"), "D_CERTIFICATE_SHA256")
        material_theorem = _hex40(
            raw.get("member_material_theorem_git_blob_sha"), "MEMBER_MATERIAL_THEOREM_GIT_BLOB_SHA"
        )
        provider_theorem = _hex40(
            raw.get("provider_theorem_git_blob_sha"), "PROVIDER_THEOREM_GIT_BLOB_SHA"
        )
        policy = _hex64(raw.get("policy_sha256"), "POLICY_SHA256")
        epoch = _hex64(raw.get("execution_epoch_sha256"), "EXECUTION_EPOCH_SHA256")
        closure = _hex64(raw.get("material_closure_root"), "MATERIAL_CLOSURE_ROOT")

        if raw.get("fresh_replay_pass") is not True:
            raise DFinalityCoverageError("ROW_FRESH_REPLAY_NOT_PASS:" + cid)
        if raw.get("independent_replay_pass") is not True:
            raise DFinalityCoverageError("ROW_INDEPENDENT_REPLAY_NOT_PASS:" + cid)
        if raw.get("donor_authority_zero") is not True:
            raise DFinalityCoverageError("ROW_DONOR_AUTHORITY_NOT_ZERO:" + cid)
        if int(raw.get("undeclared_dependency_count", -1)) != 0:
            raise DFinalityCoverageError("ROW_UNDECLARED_DEPENDENCY_COUNT_NOT_ZERO:" + cid)

        by_id[cid] = {
            "capability_id": cid,
            "d_certificate_sha256": d_cert,
            "member_material_theorem_git_blob_sha": material_theorem,
            "provider_theorem_git_blob_sha": provider_theorem,
            "policy_sha256": policy,
            "execution_epoch_sha256": epoch,
            "material_closure_root": closure,
        }
        provider_theorem_to_members.setdefault(provider_theorem, []).append(cid)

    covered = sorted(set(live) & set(by_id))
    missing = sorted(set(live) - set(by_id))
    stale = sorted(set(by_id) - set(live))
    passed = not missing

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__ALL_LIVE_ADMITTED_CAPABILITIES_CURRENT_D_FINAL"
            if passed
            else "FAIL_CLOSED__LIVE_D_FINAL_COVERAGE_INCOMPLETE"
        ),
        "pass": passed,
        "live_admitted_capability_count": len(live),
        "d_final_owned_capability_count": len(covered),
        "d_final_owned_capability_ids": covered,
        "missing_d_certificate_count": len(missing),
        "missing_d_certificate_ids": missing,
        "stale_nonlive_certificate_count": len(stale),
        "stale_nonlive_certificate_ids": stale,
        "provider_theorem_count": len(provider_theorem_to_members),
        "provider_theorem_reuse": [
            {
                "provider_theorem_sha256": theorem,
                "member_count": len(ids),
                "member_capability_ids": sorted(ids),
            }
            for theorem, ids in sorted(provider_theorem_to_members.items())
        ],
        "member_material_certificate_required_even_under_provider_reuse": True,
        "ownership_equation": "LIVE_D_FINAL_OWNED = LIVE_ADMITTED INTERSECT CURRENT_D_FINAL_CERTIFIED",
        "execution_authority": False,
        "promotion_authority": False,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
    }

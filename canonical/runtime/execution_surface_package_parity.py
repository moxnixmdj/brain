"""Fail-closed execution-surface parity checker for Stage-B prequalification.

This does not prove task capability. It only prevents a preflight performed on
one package/runtime policy from authorizing execution on a materially different
task surface.
"""
from __future__ import annotations
from typing import Any

REQUIRED_EXACT_FIELDS = (
    "os_image",
    "architecture",
    "python_provenance",
    "environment_management_policy",
    "package_install_policy",
)

def _norm(v: Any) -> str:
    return str(v).strip().lower()

def assess_surface_parity(preflight: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    mismatches: list[str] = []
    unknown: list[str] = []

    for field in REQUIRED_EXACT_FIELDS:
        p = _norm(preflight.get(field, ""))
        a = _norm(actual.get(field, ""))
        if not p or p in {"unknown", "unspecified"} or not a or a in {"unknown", "unspecified"}:
            unknown.append(field)
            continue
        if p != a:
            mismatches.append(f"{field}:{p}!={a}")

    required_native = {_norm(x) for x in actual.get("required_native_libraries", []) if _norm(x)}
    proven_native = {_norm(x) for x in preflight.get("available_native_libraries", []) if _norm(x)}
    missing_native = sorted(required_native - proven_native)
    if missing_native:
        mismatches.append("missing_native_libraries:" + ",".join(missing_native))

    actual_pep668 = actual.get("pep668_externally_managed")
    preflight_pep668 = preflight.get("pep668_externally_managed")
    if actual_pep668 is None or preflight_pep668 is None:
        unknown.append("pep668_externally_managed")
    elif bool(actual_pep668) != bool(preflight_pep668):
        mismatches.append(
            f"pep668_externally_managed:{bool(preflight_pep668)}!={bool(actual_pep668)}"
        )

    passed = not mismatches and not unknown
    return {
        "schema": "BRAIN_EXECUTION_SURFACE_PACKAGE_POLICY_PARITY_V1",
        "pass": passed,
        "mismatches": sorted(mismatches),
        "unknown": sorted(set(unknown)),
        "authorization": "STAGE_B_PACKAGE_POLICY_PARITY_PASS" if passed else "FAIL_CLOSED",
    }

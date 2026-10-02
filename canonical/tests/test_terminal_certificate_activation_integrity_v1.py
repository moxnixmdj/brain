from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTIVATION = ROOT / "canonical/governance/TERMINAL_CERTIFICATE_CUT_ACTIVATION_V2.json"
LEGACY = ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V1.json"


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def main() -> int:
    activation = json.loads(ACTIVATION.read_text(encoding="utf-8"))
    frontier_path = activation["frontier"]
    frontier = load(frontier_path)
    legacy = json.loads(LEGACY.read_text(encoding="utf-8"))

    errors = []
    status = str(frontier.get("status", ""))
    if "NONCANONICAL" in status or "SUPERSEDED" in status:
        errors.append("ACTIVE_FRONTIER_SELF_DECLARES_NONCANONICAL_OR_SUPERSEDED")
    if frontier.get("superseded_by"):
        errors.append("ACTIVE_FRONTIER_HAS_SUPERSEDED_BY_POINTER")

    expected = activation["exact_state"]
    if len(frontier.get("unresolved_predicates", [])) != expected["unresolved_predicate_count"]:
        errors.append("ACTIVE_FRONTIER_UNRESOLVED_COUNT_MISMATCH")
    if len(frontier.get("certificates", [])) != expected["certificate_candidate_count"]:
        errors.append("ACTIVE_FRONTIER_CERTIFICATE_COUNT_MISMATCH")

    ids = {row.get("id") for row in frontier.get("certificates", [])}
    for required in (
        "MATCHED_SCOPE_BINDING_CERTIFICATE",
        "TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE",
        "DELEGATION_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE",
    ):
        if required not in ids:
            errors.append("ACTIVE_FRONTIER_MISSING_REQUIRED_CERTIFICATE:" + required)

    legacy_status = str(legacy.get("status", ""))
    if "SUPERSEDED" not in legacy_status or "NONCANONICAL" not in legacy_status:
        errors.append("LEGACY_FRONTIER_NOT_EXPLICITLY_SUPERSEDED")
    if legacy.get("superseded_by") != frontier_path:
        errors.append("LEGACY_FRONTIER_SUPERSESSION_POINTER_MISMATCH")

    out = {
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "errors": errors,
        "frontier": frontier_path,
        "frontier_status": status,
        "legacy_status": legacy_status,
        "unresolved_predicate_count": len(frontier.get("unresolved_predicates", [])),
        "certificate_count": len(frontier.get("certificates", [])),
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

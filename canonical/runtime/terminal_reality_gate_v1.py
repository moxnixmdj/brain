from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from canonical.runtime.terminal_closure_reducer import evaluate_manifest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json"


def _int(value: Any, default: int = 0) -> int:
    return value if type(value) is int and value >= 0 else default


def evaluate(manifest: dict[str, Any]) -> dict[str, Any]:
    """Evaluate the actual frozen 19-family terminal contract.

    Universal observable-trace coverage remains an optional stronger proof route,
    not a mandatory terminal conjunct. The authoritative terminal truth is the
    fail-closed terminal_closure_reducer over the frozen family manifest.
    """
    verdict = evaluate_manifest(manifest)

    acceptance = manifest.get("opus55_acceptance_summary")
    if not isinstance(acceptance, dict):
        acceptance = {}
    ownership = manifest.get("ownership_summary")
    if not isinstance(ownership, dict):
        ownership = {}
    predicates = manifest.get("terminal_predicates")
    if not isinstance(predicates, dict):
        predicates = {}

    pending_acceptance = _int(acceptance.get("pending_family_count"), 19)
    atomic = acceptance.get("atomic_predicates")
    if not isinstance(atomic, dict):
        atomic = {}
    unresolved_atoms = _int(atomic.get("unresolved"), 38)
    accepted_families = _int(acceptance.get("calibrated_family_count"), 0)
    verified_owned = _int(ownership.get("verified_owned_families"), 0)

    summarized_blockers: list[str] = []
    if pending_acceptance:
        summarized_blockers.append(
            f"FROZEN_ACCEPTANCE_FAMILIES_OPEN:{pending_acceptance}"
        )
    if unresolved_atoms:
        summarized_blockers.append(
            f"FROZEN_ACCEPTANCE_ATOMS_OPEN:{unresolved_atoms}"
        )
    if verified_owned < 19:
        summarized_blockers.append(
            f"VERIFIED_OWNERSHIP_FAMILIES_OPEN:{19 - verified_owned}"
        )
    if predicates.get("final_donor_deletion_cleanroom_pass") is not True:
        summarized_blockers.append("FINAL_DONOR_DELETION_CLEANROOM_OPEN")
    if predicates.get("proof_bundle_frozen") is not True:
        summarized_blockers.append("PROOF_BUNDLE_NOT_FROZEN")

    if verdict["achieved"]:
        phase = "TERMINAL"
        summarized_blockers = []
    elif pending_acceptance or unresolved_atoms:
        phase = "FROZEN_ACCEPTANCE_CLOSURE"
    elif verified_owned < 19:
        phase = "OWNERSHIP_FINALITY"
    else:
        phase = "FINAL_TERMINAL_REDUCTION"

    return {
        "schema": "PROJECT_BRAIN_TERMINAL_REALITY_GATE_V3",
        "terminal_real": bool(verdict["achieved"]),
        "phase": phase,
        "blockers": summarized_blockers,
        "failed_predicates": verdict["failed_predicates"],
        "frozen_family_count": 19,
        "accepted_family_count": accepted_families,
        "acceptance_family_open_count": pending_acceptance,
        "verified_owned_family_count": verified_owned,
        "atomic_acceptance_proved": _int(atomic.get("proved"), 0),
        "atomic_acceptance_unresolved": unresolved_atoms,
        "rule": (
            "TERMINAL_IFF_TERMINAL_CLOSURE_REDUCER_ACHIEVED_TRUE_OVER_"
            "THE_EXACT_FROZEN_19_FAMILY_MANIFEST"
        ),
        "anti_bureaucracy": {
            "universal_trace_not_x_is_optional_stronger_route_not_mandatory": True,
            "generic_router_or_global_trace_cover_is_not_an_extra_terminal_conjunct": True,
            "only_frozen_acceptance_ownership_and_finality_predicates_count": True,
        },
    }


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    out = evaluate(manifest)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["terminal_real"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

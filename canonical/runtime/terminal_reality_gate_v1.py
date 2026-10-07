from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from canonical.runtime.terminal_closure_reducer import evaluate_manifest

ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
MANIFEST = ROOT / "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json"
MANDATORY_PREDICATE = "TERMINAL_CLOSURE_REDUCER_ACHIEVED_TRUE"


def evaluate(pointer: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    hard_failures: list[str] = []
    override = pointer.get("terminal_semantics_override")
    if not isinstance(override, dict):
        hard_failures.append("TERMINAL_SEMANTICS_OVERRIDE_MISSING")
        override = {}
    if override.get("mandatory_terminal_predicate") != MANDATORY_PREDICATE:
        hard_failures.append("MANDATORY_TERMINAL_PREDICATE_DRIFT")
    if pointer.get("live_truth", {}).get("terminal_root_semantics") != "FROZEN_19_FAMILY_ACCEPTANCE_AND_OWNERSHIP_FINALITY":
        hard_failures.append("TERMINAL_ROOT_SEMANTICS_DRIFT")

    verdict = evaluate_manifest(manifest)
    reducer_failures = list(verdict.get("failed_predicates") or [])
    terminal_real = bool(verdict.get("achieved") is True and not hard_failures)

    live = pointer.get("live_truth", {})
    blockers = sorted(set(hard_failures + reducer_failures))
    if terminal_real:
        phase = "TERMINAL"
    elif live.get("frozen_terminal_family_open_count", 1) > 0:
        phase = "FROZEN_ACCEPTANCE_CLOSURE"
    else:
        phase = "FINAL_OWNERSHIP_AND_PROOF_BUNDLE_CLOSURE"

    declared_terminal = live.get("terminal") is True
    declaration_warnings: list[str] = []
    if declared_terminal and not terminal_real:
        blockers.append("DECLARED_TERMINAL_INCONSISTENT_WITH_FROZEN_REDUCER")
        blockers = sorted(set(blockers))
    elif terminal_real and not declared_terminal:
        declaration_warnings.append(
            "DECLARED_TERMINAL_FALSE_BUT_FROZEN_REDUCER_ACHIEVED_TRUE__METADATA_OUT_OF_SYNC"
        )

    return {
        "schema": "PROJECT_BRAIN_TERMINAL_REALITY_GATE_V3",
        "terminal_real": terminal_real,
        "declared_terminal": declared_terminal,
        "phase": phase,
        "blockers": blockers,
        "declaration_warnings": declaration_warnings,
        "mandatory_terminal_predicate": MANDATORY_PREDICATE,
        "frozen_family_count": verdict.get("family_count"),
        "frozen_family_pass_count": verdict.get("closed_family_count"),
        "frozen_atomic_predicates_proved": live.get("frozen_atomic_predicates_proved"),
        "frozen_atomic_predicates_unresolved": live.get("frozen_atomic_predicates_unresolved"),
        "universal_trace_not_x_required_for_terminal": False,
        "optional_stronger_route": override.get("optional_stronger_route"),
        "anti_bureaucracy": {
            "demoted_universal_trace_root_is_not_a_mandatory_terminal_conjunct": True,
            "terminal_truth_is_reduced_only_from_frozen_19_family_acceptance_and_finality": True,
            "manual_terminal_declaration_cannot_override_failed_reducer": True,
        },
    }


def main() -> int:
    pointer = json.loads(POINTER.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    out = evaluate(pointer, manifest)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["terminal_real"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

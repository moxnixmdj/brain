"""Fail-closed CC_R3 mission-scope bridge guard (issue #3732).

Checkpoint single-U emptiness does not prove the real-mission terminal
closure root CC_R3 (B_plus_real SUBSETEQ G_minus_real): the historical
checkpoint-scoped single-ABC frontier lives in a smaller semantic universe.
This guard keeps that reduction impossible:

- the CC_R3 certificate slot may only be PROVED_CURRENT when its bound claim
  is declared non-real-mission-closure in the content-addressed bridge
  status artifact, or a proved mission-scope bridge with content-addressed
  theorem and independent verification covers it;
- while no bridge is proved, the live terminal truth must keep the
  real-mission conjunct open (complete_selected_context_ABC_closed false,
  terminal false);
- the recorded finite countermodel must remain internally consistent.

Zero credit. Fail closed everywhere. Not a new peer root.
"""

from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]

STATUS_PATH = ROOT / "canonical/governance/COVERAGE_CC_R3_MISSION_SCOPE_BRIDGE_STATUS_V1.json"
REGISTRY_PATH = ROOT / "canonical/governance/COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1.json"
TERMINAL_AUTHORITY_PATH = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"

R3_ROOT_ID = "CC_R3_TERMINAL_CLOSURE_V1"
SCHEMA = "PROJECT_BRAIN_COVERAGE_CC_R3_MISSION_SCOPE_BRIDGE_STATUS_V1"
BRIDGE_OPEN_STATUS = "NO_MISSION_SCOPE_BRIDGE_PROVED__CC_R3_REAL_MISSION_CONJUNCT_OPEN__ZERO_CREDIT"
REAL_MISSION_CONJUNCT_OPEN = "OPEN__UNKNOWN"


class CC_R3ScopeBridgeError(RuntimeError):
    """Raised fail-closed on any scope-bridge violation."""


def _fail(reason: str) -> None:
    raise CC_R3ScopeBridgeError(reason)


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    digest = sha1()
    digest.update(f"blob {len(data)}".encode("ascii") + bytes([0]))
    digest.update(data)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        _fail(f"SOURCE_READ_FAILED:{path.name}:{exc}")
    if not isinstance(data, dict):
        _fail(f"SOURCE_NOT_OBJECT:{path.name}")
    return data


def _hex40(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _hex64(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _validate_countermodel(model: Mapping[str, Any]) -> None:
    universe = model.get("universe")
    checkpoint = model.get("checkpoint_scope")
    b_plus = model.get("B_plus_real")
    g_minus = model.get("G_minus_real")
    witness = model.get("witness")
    for label, value in (
        ("universe", universe),
        ("checkpoint_scope", checkpoint),
        ("B_plus_real", b_plus),
        ("G_minus_real", g_minus),
        ("witness", witness),
    ):
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            _fail(f"COUNTERMODEL_{label.upper()}_INVALID")
    if set(checkpoint) - set(universe) or set(b_plus) - set(universe) or set(g_minus) - set(universe):
        _fail("COUNTERMODEL_SETS_ESCAPE_UNIVERSE")
    if set(checkpoint) - set(g_minus):
        _fail("COUNTERMODEL_U_CHECKPOINT_NOT_EMPTY")
    if model.get("U_checkpoint_empty") is not True:
        _fail("COUNTERMODEL_U_EMPTINESS_NOT_RECORDED")
    if set(b_plus) <= set(g_minus):
        _fail("COUNTERMODEL_REAL_MISSION_CLOSURE_ACCIDENTALLY_TRUE")
    if set(witness) != set(b_plus) - set(g_minus):
        _fail("COUNTERMODEL_WITNESS_INVALID")
    if model.get("B_plus_real_subseteq_G_minus_real") is not False:
        _fail("COUNTERMODEL_CLOSURE_FLAG_INVALID")


def _validate_bridge(bridge: Mapping[str, Any]) -> bool:
    """Return True iff a proved, fully content-addressed bridge is bound."""
    if bridge.get("proved") is not True:
        return False
    form = bridge.get("form")
    if form not in {"SCOPE_CONTAINMENT", "REAL_MISSION_U"}:
        _fail("BRIDGE_FORM_INVALID")
    for field in (
        "theorem_path",
        "theorem_git_blob_sha",
        "independent_verification_path",
        "independent_verification_git_blob_sha",
    ):
        if not isinstance(bridge.get(field), str) or not bridge[field].strip():
            _fail(f"BRIDGE_{field.upper()}_MISSING_FOR_PROVED_BRIDGE")
    if not _hex40(bridge.get("theorem_git_blob_sha")) or not _hex40(
        bridge.get("independent_verification_git_blob_sha")
    ):
        _fail("BRIDGE_BLOB_SHA_INVALID")
    theorem_path = (ROOT / str(bridge["theorem_path"])).resolve()
    verification_path = (ROOT / str(bridge["independent_verification_path"])).resolve()
    for path, blob_field in (
        (theorem_path, "theorem_git_blob_sha"),
        (verification_path, "independent_verification_git_blob_sha"),
    ):
        try:
            path.relative_to(ROOT.resolve())
        except ValueError:
            _fail(f"BRIDGE_PATH_ESCAPES_REPOSITORY:{blob_field}")
        if not path.is_file():
            _fail(f"BRIDGE_BOUND_FILE_MISSING:{blob_field}")
        if _git_blob_sha(path) != bridge[blob_field]:
            _fail(f"BRIDGE_BLOB_STALE:{blob_field}")
    return True


def validate(
    status: Mapping[str, Any] | None = None,
    *,
    registry: Mapping[str, Any] | None = None,
    terminal_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    owns_status = status is None
    if status is None:
        status = _load_json(STATUS_PATH)
    if registry is None:
        registry = _load_json(REGISTRY_PATH)
    if terminal_authority is None:
        terminal_authority = _load_json(TERMINAL_AUTHORITY_PATH)
    if not isinstance(status, Mapping):
        _fail("STATUS_NOT_OBJECT")

    if status.get("schema") != SCHEMA:
        errors.append("SCHEMA_DRIFT")

    # Countermodel must stay truthful.
    model = status.get("defect_record", {}).get("countermodel")
    if not isinstance(model, Mapping):
        errors.append("COUNTERMODEL_MISSING")
    else:
        try:
            _validate_countermodel(model)
        except CC_R3ScopeBridgeError as exc:
            errors.append(str(exc))

    # Content-addressed bindings against live bytes (only when reading files).
    if owns_status:
        bindings = status.get("bindings") or {}
        reg_sha = bindings.get("root_registry_git_blob_sha")
        if not _hex40(reg_sha):
            errors.append("REGISTRY_BINDING_INVALID")
        elif _git_blob_sha(REGISTRY_PATH) != reg_sha:
            errors.append("REGISTRY_BINDING_STALE")
        r4 = (terminal_authority.get("r4_live_binding_currentness") or {})
        if r4.get("root_registry_sha") != reg_sha:
            errors.append("R4_LIVE_BINDING_REGISTRY_MISMATCH")
        if r4.get("active_claim") != bindings.get("r4_live_binding_active_claim_id"):
            errors.append("R4_ACTIVE_CLAIM_MISMATCH")

    # Real-mission conjunct posture.
    conjunct = status.get("cc_r3_real_mission_conjunct") or {}
    if conjunct.get("closed_by_checkpoint_u_empty_alone") is not False:
        errors.append("CHECKPOINT_U_EMPTY_GRANTED_REAL_MISSION_CLOSURE_AUTHORITY")
    bridge = status.get("mission_scope_bridge") or {}
    try:
        bridge_proved = _validate_bridge(bridge)
    except CC_R3ScopeBridgeError as exc:
        errors.append(str(exc))
        bridge_proved = False

    if not bridge_proved:
        if status.get("status") != BRIDGE_OPEN_STATUS:
            errors.append("BRIDGE_STATUS_TEXT_DRIFT")
        if conjunct.get("status") != REAL_MISSION_CONJUNCT_OPEN:
            errors.append("REAL_MISSION_CONJUNCT_NOT_OPEN")
        live = terminal_authority.get("live_truth") or {}
        if live.get("complete_selected_context_ABC_closed") is not False:
            errors.append("LIVE_ABC_CLOSED_WITHOUT_BRIDGE")
        if live.get("terminal") is not False:
            errors.append("LIVE_TERMINAL_TRUE_WITHOUT_BRIDGE")

    # CC_R3 slot posture: proved slot claims must be cleared as non-real-mission
    # closure (or covered by the proved bridge).
    declared = status.get("declared_non_real_mission_closure_claims")
    if not isinstance(declared, list):
        errors.append("DECLARED_CLAIMS_INVALID")
        declared = []
    declared_scopes = {
        row.get("scope_sha256")
        for row in declared
        if isinstance(row, Mapping)
        and row.get("real_mission_closure_claimed") is False
        and _hex64(row.get("scope_sha256"))
    }
    slots = registry.get("certificate_slots")
    r3_slot = None
    if isinstance(slots, list):
        for slot in slots:
            if isinstance(slot, Mapping) and slot.get("root_id") == R3_ROOT_ID:
                r3_slot = slot
                break
    if r3_slot is None:
        errors.append("CC_R3_SLOT_MISSING")
    elif r3_slot.get("status") == "PROVED_CURRENT":
        claim_binding = (r3_slot.get("certificate") or {}).get("claim_binding") or {}
        scope = claim_binding.get("scope_sha256")
        if scope not in declared_scopes and not bridge_proved:
            errors.append("CC_R3_CLAIM_SCOPE_NOT_CLEARED_FOR_REAL_MISSION_POSTURE")

    # Zero credit.
    accounting = status.get("accounting") or {}
    for key in (
        "incremental_spend_usd",
        "terminal_credit_delta",
        "acceptance_credit_delta",
        "ownership_credit_delta",
    ):
        if accounting.get(key, 1) != 0:
            errors.append(f"NONZERO_ACCOUNTING:{key}")

    return {
        "pass": not errors,
        "status": "PASS__CC_R3_SCOPE_BRIDGE_CONSTRAINT_HELD" if not errors else "FAIL_CLOSED",
        "errors": errors,
        "mission_scope_bridge_proved": bridge_proved,
        "cc_r3_real_mission_conjunct": REAL_MISSION_CONJUNCT_OPEN if not bridge_proved else "BRIDGE_COVERED",
        "checkpoint_u_empty_real_mission_closure_authority": False,
        "global_mission_completion_derivable": False,
        "terminal_credit_delta": 0,
    }


def main() -> int:
    result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

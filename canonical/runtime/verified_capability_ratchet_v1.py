"""Verified deterministic capability ratchet for the sub-100MB program.

A successfully induced program may become a reusable macro primitive only after a
held-out verification receipt passes. The macro is executable deterministic code,
not learned parameters, so capability-library growth does not increase persistent
learned-state bytes.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.mdl_program_induction_v1 import (
    Primitive,
    ProgramInductionError,
    compile_program,
    execute,
)


class CapabilityRatchetError(ValueError):
    pass


@dataclass(frozen=True)
class PromotedPrimitive:
    primitive: Primitive
    manifest: Mapping[str, Any]


def _registry(primitives: Sequence[Primitive]) -> dict[str, Primitive]:
    out: dict[str, Primitive] = {}
    for primitive in primitives:
        if not isinstance(primitive, Primitive):
            raise CapabilityRatchetError("PRIMITIVE_INVALID")
        if primitive.primitive_id in out:
            raise CapabilityRatchetError("PRIMITIVE_ID_DUPLICATE")
        out[primitive.primitive_id] = primitive
    if not out:
        raise CapabilityRatchetError("PRIMITIVES_REQUIRED")
    return out


def _sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def promote_verified_program(
    *,
    primitive_id: str,
    program: Sequence[str],
    primitives: Sequence[Primitive],
    verification_receipt: Mapping[str, Any],
    macro_cost: int = 1,
) -> PromotedPrimitive:
    pid = str(primitive_id or "").strip()
    if not pid:
        raise CapabilityRatchetError("PRIMITIVE_ID_REQUIRED")
    if isinstance(macro_cost, bool) or not isinstance(macro_cost, int) or macro_cost <= 0:
        raise CapabilityRatchetError("MACRO_COST_INVALID")

    registry = _registry(primitives)
    if pid in registry:
        raise CapabilityRatchetError("PRIMITIVE_ID_COLLISION")
    compiled = compile_program(program=program, primitives=primitives)

    if verification_receipt.get("schema") != "PROJECT_BRAIN_MDL_PROGRAM_VERIFICATION_V1":
        raise CapabilityRatchetError("VERIFICATION_SCHEMA_INVALID")
    if verification_receipt.get("pass") is not True:
        raise CapabilityRatchetError("VERIFICATION_NOT_PASS")
    if list(verification_receipt.get("program") or []) != list(program):
        raise CapabilityRatchetError("VERIFICATION_PROGRAM_MISMATCH")
    if verification_receipt.get("registry_fingerprint") != compiled["registry_fingerprint"]:
        raise CapabilityRatchetError("VERIFICATION_REGISTRY_MISMATCH")
    case_count = verification_receipt.get("case_count")
    if isinstance(case_count, bool) or not isinstance(case_count, int) or case_count < 1:
        raise CapabilityRatchetError("VERIFICATION_CASE_COUNT_INVALID")

    frozen_program = tuple(program)
    frozen_registry = dict(registry)

    def macro(value: Any) -> Any:
        return execute(frozen_program, value, frozen_registry)

    manifest = {
        "schema": "PROJECT_BRAIN_VERIFIED_CAPABILITY_MACRO_V1",
        "primitive_id": pid,
        "source_program": list(frozen_program),
        "source_description_length": compiled["description_length"],
        "macro_description_length": macro_cost,
        "source_registry_fingerprint": compiled["registry_fingerprint"],
        "verification_case_count": case_count,
        "verification_pass": True,
        "program_sha256": _sha(
            {
                "program": list(frozen_program),
                "registry_fingerprint": compiled["registry_fingerprint"],
            }
        ),
        "persistent_learned_state_bytes": 0,
        "requires_retraining_for_reuse": False,
        "promotion_authority": False,
    }
    return PromotedPrimitive(
        primitive=Primitive(pid, macro_cost, macro),
        manifest=manifest,
    )


def extend_registry(
    primitives: Sequence[Primitive],
    promoted: Sequence[PromotedPrimitive],
) -> list[Primitive]:
    base = _registry(primitives)
    out = list(primitives)
    for item in promoted:
        if not isinstance(item, PromotedPrimitive):
            raise CapabilityRatchetError("PROMOTED_PRIMITIVE_INVALID")
        pid = item.primitive.primitive_id
        if pid in base:
            raise CapabilityRatchetError("PROMOTED_PRIMITIVE_COLLISION:" + pid)
        if item.manifest.get("verification_pass") is not True:
            raise CapabilityRatchetError("PROMOTED_PRIMITIVE_UNVERIFIED:" + pid)
        if item.manifest.get("persistent_learned_state_bytes") != 0:
            raise CapabilityRatchetError("PROMOTED_PRIMITIVE_LEARNED_STATE_NONZERO:" + pid)
        base[pid] = item.primitive
        out.append(item.primitive)
    return out

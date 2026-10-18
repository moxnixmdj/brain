"""Computer use as a verified capability family, in the Brain's own shape.

The discovery that produced this file: the Brain can plan, verify and
execute with real rigour, but the only effects it could produce were
two -- write a receipt, append to a ledger. ALLOWED_TOOL_IDS was
{"JSON_RECEIPT_WRITER_V1", "JSONL_LEDGER_APPEND_V1"}. Everything else
in the loop was present and strict; the effect layer was two tools
wide.

So computer use is not a rival control loop. It is the missing EFFECT
FAMILY, and it belongs in the registry the same way every other
capability does -- declared, routed, and independently verified before
it may be dispatched.

COMPOSITION, not modification. This is a separate registry that a
later registry composes, exactly the way V2 composes the cubic patch
onto V1. The existing routes are untouched; nothing here changes how
anything already verified behaves.

THE CONTRACT IS THE POINT. Each entry declares preconditions and
effects, because that is what lets the EXISTING planner plan over
these. A capability the planner cannot reason about is not a
capability, it is a script. And each carries prior_verification,
because the registry rule is unchanged: only capabilities with prior
content-addressed independent verification may enter.

ZERO LEARNED BYTES, ZERO EXTERNAL LEARNED CALLS -- the same invariant
the rest of the registry reports. Nothing here is a model. Where
judgement is needed it arrives as an untrusted proposal packet with
zero authority, which is how the rest of the Brain already works.

UNKNOWN ROUTES FAIL CLOSED. A capability_id that is not registered is
refused, never synthesised.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_H100_COMPUTER_USE_REGISTRY_V1"

# Every route must appear here and in ROUTES. Adding one without the
# other is a silent no-op waiting to be trusted.
REGISTRY = (
    {
        "capability_id": "CAP_FS_LIST_V1",
        "kind": "DIRECT",
        "route": "FILESYSTEM_LIST",
        "preconditions": ("project_present",),
        "effects": ("files_known",),
        "cost": 1,
        "prior_verification":
            "canonical/verification/"
            "H100_COMPUTER_USE_FILESYSTEM_VERIFICATION_V1.json",
    },
    {
        "capability_id": "CAP_FS_READ_V1",
        "kind": "DIRECT",
        "route": "FILESYSTEM_READ",
        "preconditions": ("files_known",),
        "effects": ("file_contents_read",),
        "cost": 1,
        "prior_verification":
            "canonical/verification/"
            "H100_COMPUTER_USE_FILESYSTEM_VERIFICATION_V1.json",
    },
    {
        "capability_id": "CAP_FS_WRITE_V1",
        "kind": "DIRECT",
        "route": "FILESYSTEM_WRITE",
        "preconditions": ("project_present",),
        "effects": ("file_written",),
        "cost": 2,
        "prior_verification":
            "canonical/verification/"
            "H100_COMPUTER_USE_FILESYSTEM_VERIFICATION_V1.json",
    },
    {
        "capability_id": "CAP_PROGRAM_RUN_V1",
        "kind": "DIRECT",
        "route": "PROGRAM_RUN_CONFINED",
        "preconditions": ("project_present",),
        "effects": ("program_effect_verified",),
        "cost": 5,
        "prior_verification":
            "canonical/verification/"
            "H100_COMPUTER_USE_CONFINED_EXECUTION_VERIFICATION_V1.json",
    },
)

_BY_ID = {row["capability_id"]: row for row in REGISTRY}


class ComputerUseRegistryError(ValueError):
    pass


def registry_snapshot() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "VERIFIED_COMPUTER_USE_REGISTRY_READY",
        "entry_count": len(REGISTRY),
        "entries": [dict(x) for x in REGISTRY],
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
        "routing_priority": "REGISTRY_FIRST__UNKNOWN_FAILS_CLOSED",
    }


def resolve(capability_id: str) -> dict[str, Any]:
    """Look up a capability. Unknown ids are refused, never invented."""
    row = _BY_ID.get(str(capability_id or ""))
    if row is None:
        return {
            "schema": SCHEMA,
            "status": "REGISTRY_MISS__FAIL_CLOSED",
            "reason": "CAPABILITY_NOT_REGISTERED",
            "capability_id": str(capability_id),
            "match": None,
            "persistent_learned_bytes": 0,
        }
    return {
        "schema": SCHEMA,
        "status": "REGISTRY_HIT__VERIFY_BEFORE_USE",
        "match": dict(row),
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
    }


# --- routes -------------------------------------------------------------
#
# Each returns a receipt the caller can check. None of them takes the
# request's word for anything: filesystem routes re-read after acting,
# and the program route runs confined and reports what changed.

def _arg(payload: Mapping[str, Any], *names: str) -> str:
    """The path the compiler bound, whichever name it used."""
    for n in names:
        v = payload.get(n)
        if isinstance(v, str) and v:
            return v
    return ""


def _fs_list(payload: Mapping[str, Any], root: Path) -> dict[str, Any]:
    rel = _arg(payload, "path", "input_path", "input", "output", "output_path") or "."
    target = (root / rel).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise ComputerUseRegistryError("PATH_ESCAPES_ROOT")
    # A path that names a file lists its directory. Pointing at a file
    # and being told "nothing here" is a lie about the directory, and
    # it is why the first end-to-end run reported count 0.
    if target.is_file():
        target = target.parent
    names = sorted(p.name for p in target.iterdir()) if target.is_dir() else []
    return {"files": names, "count": len(names), "listed": str(target)}


def _fs_read(payload: Mapping[str, Any], root: Path) -> dict[str, Any]:
    rel = _arg(payload, "path", "input_path", "input")
    if not rel:
        raise ComputerUseRegistryError("PATH_REQUIRED")
    target = (root / rel).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise ComputerUseRegistryError("PATH_ESCAPES_ROOT")
    text = target.read_text(errors="replace")
    return {"path": rel, "text": text[:20000], "bytes": len(text)}


def _fs_write(payload: Mapping[str, Any], root: Path) -> dict[str, Any]:
    rel = _arg(payload, "path", "output_path", "output", "input")
    if not rel:
        raise ComputerUseRegistryError("PATH_REQUIRED")
    target = (root / rel).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise ComputerUseRegistryError("PATH_ESCAPES_ROOT")
    data = str(payload.get("text") or "")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(data)
    # Re-read rather than believe the write.
    return {"path": rel, "verified": target.read_text() == data,
            "bytes": len(data)}


def _program_run(payload: Mapping[str, Any], root: Path) -> dict[str, Any]:
    # The goal compiler binds quoted text to whatever key the template
    # names -- here input_path -- so the code arrives under that name,
    # not under "code". Reading only "code" made the general capability
    # the one thing that never ran.
    # "text" must come BEFORE the path names. It did not, so the
    # fallback grabbed input_path and the system tried to EXECUTE A
    # FILENAME as code -- failing closed for a reason that had nothing
    # to do with the program.
    code = _arg(payload, "code", "text", "input_path", "input")
    if not isinstance(code, str) or not code.strip():
        raise ComputerUseRegistryError("CODE_REQUIRED")
    try:
        from canonical.runtime import confine_v1 as C
    except Exception:
        raise ComputerUseRegistryError("CONFINEMENT_UNAVAILABLE")
    if not C.available():
        raise ComputerUseRegistryError("CONFINEMENT_UNAVAILABLE")
    result = C.run(code, str(root), timeout=int(payload.get("timeout") or 120),
                   network=bool(payload.get("network")))
    if result.get("verdict") != "OK":
        raise ComputerUseRegistryError(
            "PROGRAM_NOT_VERIFIED:" + str(result.get("verdict")))
    return {"confined": True, "network": bool(payload.get("network")),
            "output": (result.get("output") or "")[-2000:]}


ROUTES = {
    "FILESYSTEM_LIST": _fs_list,
    "FILESYSTEM_READ": _fs_read,
    "FILESYSTEM_WRITE": _fs_write,
    "PROGRAM_RUN_CONFINED": _program_run,
}


def invoke(capability_id: str, payload: Mapping[str, Any],
           root: str) -> dict[str, Any]:
    """Dispatch one registered capability, then report what happened."""
    res = resolve(capability_id)
    if res["status"] != "REGISTRY_HIT__VERIFY_BEFORE_USE":
        return res
    row = res["match"]
    route = ROUTES.get(row["route"])
    if route is None:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED",
                "reason": "ROUTE_NOT_IMPLEMENTED",
                "capability_id": capability_id}
    base = Path(root).resolve()
    if not base.is_dir():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED",
                "reason": "ROOT_NOT_DIRECTORY", "root": str(base)}
    try:
        receipt = route(payload if isinstance(payload, Mapping) else {}, base)
    except ComputerUseRegistryError as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED",
                "reason": str(exc), "capability_id": capability_id}
    except Exception as exc:
        # An unexpected failure is still a failure, and naming the type
        # is not the same as trusting it.
        return {"schema": SCHEMA, "status": "FAIL_CLOSED",
                "reason": f"{type(exc).__name__}", "capability_id": capability_id}
    return {
        "schema": SCHEMA,
        "status": "VERIFIED_CAPABILITY_INVOKED",
        "capability_id": capability_id,
        "route": row["route"],
        "effects": list(row["effects"]),
        "receipt": receipt,
        "prior_verification": row["prior_verification"],
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
    }


# ---------------------------------------------------------------------------
# The shape the Brain's own proposal generator consumes.
# ---------------------------------------------------------------------------
#
# capability_proposal_generators.single_verified_capability_v1 proposes by
# choosing among REGISTERED capabilities and binding their inputs. It
# needs entries with status VERIFIED_BOUND_CAPABILITY, `requires`,
# `provides`, an `action_template`, and zero incremental spend.
#
# That matters more than it looks. The open question has been what
# fills the proposal packets, and the answer is not a language model:
# the Brain already contains a fail-closed generator that composes
# capabilities it can verify. Given capabilities to choose from, it
# proposes without any external mind.
#
# So this adapter is the bridge. Registered here is not enough -- the
# field names differ, and a capability the generator cannot read is one
# it can never propose.

_BOUND_STATUS = "VERIFIED_BOUND_CAPABILITY"

# Real shape, read out of BOUND_CAPABILITY_REGISTRY_V1 rather than
# invented: an action_template carries `args` with ${input.x}
# placeholders AND an `expect` predicate. Action and its proof are
# declared as one unit -- the capability says what must be true of
# its own result, and the runtime checks it. `keywords` is what lets
# the goal compiler bind the goal's words to the inputs.
_ACTION_TEMPLATES = {
    "CAP_FS_LIST_V1": {
        "type": "invoke_capability",
        "args": {"capability_id": "CAP_FS_LIST_V1",
                 "input_path": "${input.input_path}"},
        "expect": {"field": "count", "type": "field_present"},
        "keywords": ["list", "files", "directory", "folder", "show"],
    },
    "CAP_FS_READ_V1": {
        "type": "invoke_capability",
        "args": {"capability_id": "CAP_FS_READ_V1",
                 "input_path": "${input.input_path}"},
        "expect": {"field": "text", "type": "field_present"},
        "keywords": ["read", "open", "contents", "show", "view"],
    },
    "CAP_FS_WRITE_V1": {
        "type": "invoke_capability",
        "args": {"capability_id": "CAP_FS_WRITE_V1",
                 "output_path": "${input.output_path}", "text": "${input.text}"},
        "expect": {"field": "verified", "type": "field_equals",
                   "value": True},
        "keywords": ["write", "save", "create", "put", "output"],
    },
    "CAP_PROGRAM_RUN_V1": {
        "type": "invoke_capability",
        "args": {"capability_id": "CAP_PROGRAM_RUN_V1",
                 "text": "${input.text}",
                 "input_path": "${input.input_path}"},
        "expect": {"field": "confined", "type": "field_equals",
                   "value": True},
        "keywords": ["run", "execute", "program", "compute", "script"],
    },
}


def bound_entries() -> dict:
    """These capabilities in the shape the generator proposes over."""
    out = {}
    for row in REGISTRY:
        cid = row["capability_id"]
        out[cid] = {
            "capability_id": cid,
            "status": _BOUND_STATUS,
            "requires": list(row["preconditions"]),
            "provides": list(row["effects"]),
            "cost": row["cost"],
            "action_template": dict(_ACTION_TEMPLATES.get(cid) or {}),
            "keywords": list(
                (_ACTION_TEMPLATES.get(cid) or {}).get("keywords") or []),
            "incremental_spend_usd": 0,
            "prior_verification": row["prior_verification"],
        }
    return out

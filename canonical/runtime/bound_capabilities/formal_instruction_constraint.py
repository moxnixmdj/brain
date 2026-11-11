#!/usr/bin/env python3
"""Zero-spend bound capability for exact formal instruction satisfaction.

This wrapper exposes the independently verified instruction constraint compiler
through Brain's bound-capability interface. It deliberately accepts only
responses that require no semantic seed. Structural constraints that still need
semantic content remain blocked.
"""
from __future__ import annotations

from canonical.runtime import instruction_constraint_compiler_v1 as compiler


class FormalInstructionCapabilityError(RuntimeError):
    pass


def run(args, root=None):
    instruction=str((args or {}).get("instruction") or "").strip()
    if not instruction:
        raise FormalInstructionCapabilityError("INSTRUCTION_REQUIRED")
    out=compiler.synthesize_formal_only(instruction)
    if out.get("status")!="PASS" or out.get("semantic_seed_required") is not False:
        raise FormalInstructionCapabilityError(
            "SEMANTIC_SEED_OR_UNPROVED_FORMAL_ROUTE_REQUIRED:"
            +str(out.get("status") or "UNKNOWN")
        )
    response=str(out.get("response") or "")
    ok,errors=compiler.validate_response(
        response,
        compiler.compile_constraints(instruction),
    )
    if not ok:
        raise FormalInstructionCapabilityError(
            "POSTVALIDATION_FAILED:"+",".join(str(x) for x in errors)
        )
    return {
        "status":"PASS",
        "response":response,
        "semantic_seed_required":False,
        "model_dependency_count":0,
        "network_used":False,
        "incremental_spend_usd":0,
    }

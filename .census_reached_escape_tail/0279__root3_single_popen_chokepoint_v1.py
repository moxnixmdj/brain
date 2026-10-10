"""Root3 29-to-1 subprocess mediation reduction.

The current Brain runtime has already been reduced to 29 direct process-creation
sites, all late-bound through subprocess.run or subprocess.Popen. This module
checks the additional runtime premise needed to collapse those two attributes
to one: the active Python stdlib subprocess.run function must itself resolve the
module-global name Popen at call time.

If that premise holds, replacing subprocess.Popen before credited execution
intercepts both direct Popen calls and all current subprocess.run calls. This is
a structural mediation reduction only. It does not prove child-internal,
native-extension, or semantic authorization soundness.
"""
from __future__ import annotations

import dis
import hashlib
import inspect
import json
import subprocess
import sys
from types import FunctionType
from typing import Any, Mapping

from canonical.runtime.root3_global_subprocess_chokepoint_v1 import audit as audit_repo_chokepoints

SCHEMA = "PROJECT_BRAIN_ROOT3_SINGLE_POPEN_CHOKEPOINT_V1"


class SingleChokepointError(RuntimeError):
    pass


def analyze_run_delegation(
    run_fn: Any = subprocess.run,
    module_globals: Mapping[str, Any] = subprocess.__dict__,
) -> dict[str, Any]:
    if not isinstance(run_fn, FunctionType):
        raise SingleChokepointError("SUBPROCESS_RUN_NOT_PYTHON_FUNCTION")
    if run_fn.__globals__ is not module_globals:
        raise SingleChokepointError("SUBPROCESS_RUN_GLOBALS_NOT_MODULE_DICT")
    if run_fn.__closure__ not in (None, ()):
        raise SingleChokepointError("SUBPROCESS_RUN_HAS_CLOSURE")

    instructions = list(dis.get_instructions(run_fn))
    popen_loads = [
        {
            "opname": ins.opname,
            "argval": ins.argval,
            "offset": ins.offset,
        }
        for ins in instructions
        if ins.opname in {"LOAD_GLOBAL", "LOAD_NAME"} and ins.argval == "Popen"
    ]
    if not popen_loads:
        raise SingleChokepointError("SUBPROCESS_RUN_DOES_NOT_LOAD_GLOBAL_POPEN")

    current_popen = module_globals.get("Popen")
    if current_popen is not subprocess.Popen:
        raise SingleChokepointError("SUBPROCESS_MODULE_POPEN_BINDING_DRIFT")

    try:
        source = inspect.getsource(run_fn).encode("utf-8")
        source_sha256 = hashlib.sha256(source).hexdigest()
    except (OSError, TypeError):
        source_sha256 = None

    code = run_fn.__code__
    code_sha256 = hashlib.sha256(
        code.co_code
        + repr(code.co_consts).encode("utf-8")
        + repr(code.co_names).encode("utf-8")
    ).hexdigest()

    return {
        "python_version": sys.version,
        "python_executable": sys.executable,
        "run_function_module": run_fn.__module__,
        "run_globals_is_subprocess_module_dict": True,
        "run_closure_free": True,
        "global_popen_load_count": len(popen_loads),
        "global_popen_loads": popen_loads,
        "run_source_sha256": source_sha256,
        "run_code_identity_sha256": code_sha256,
        "current_popen_type": getattr(subprocess.Popen, "__qualname__", type(subprocess.Popen).__name__),
    }


def audit() -> dict[str, Any]:
    prior = audit_repo_chokepoints()
    if prior.get("direct_process_call_site_count") != 29:
        raise SingleChokepointError("PRIOR_DIRECT_PROCESS_UNIVERSE_NOT_29")
    if prior.get("minimum_direct_python_mediation_chokepoints") != [
        "subprocess.run",
        "subprocess.Popen",
    ]:
        raise SingleChokepointError("PRIOR_TWO_CHOKEPOINT_REDUCTION_DRIFT")

    delegation = analyze_run_delegation()

    return {
        "schema": SCHEMA,
        "status": "PASS__CURRENT_29_DIRECT_PROCESS_SITES_COLLAPSE_TO_ONE_MODULE_GLOBAL_POPEN_MEDIATION_POINT",
        "prior_direct_process_call_site_count": 29,
        "prior_chokepoints": ["subprocess.run", "subprocess.Popen"],
        "new_minimum_structural_chokepoints": ["subprocess.Popen"],
        "wiring_actions_before": 29,
        "wiring_actions_after": 1,
        "wiring_actions_deleted": 28,
        "reduction_percent": 28 / 29 * 100.0,
        "stdlib_run_delegation": delegation,
        "deduction": (
            "ALL_29_CURRENT_BOUND_DIRECT_PROCESS_CREATION_SITES_USE_LATE_MODULE_ATTRIBUTE_LOOKUPS; "
            "27_CALL_subprocess.run_AND_2_CALL_subprocess.Popen; THE_ACTIVE_STDLIB_subprocess.run "
            "LOADS_THE_MODULE_GLOBAL_Popen_AT_CALL_TIME; THEREFORE_INSTALLING_A_FAIL_CLOSED "
            "MEDIATION_REPLACEMENT_AT_subprocess.Popen_BEFORE_CREDITED_EXECUTION_INTERCEPTS "
            "ALL_29_CURRENT_DIRECT_PYTHON_PROCESS_CREATION_PATHS."
        ),
        "runtime_fail_closed_requirement": (
            "BEFORE_INSTALL_OR_CREDIT, RE-RUN_THIS DELEGATION CHECK; ANY PYTHON_RUNTIME_OR_STDLIB "
            "CHANGE_THAT_BREAKS_GLOBAL_Popen_DELEGATION_INVALIDATES_THE_29_TO_1_REDUCTION."
        ),
        "remaining_after_single_chokepoint": [
            "IMPLEMENT_CALLER_COMPATIBLE_FAIL_CLOSED_POPEN_MEDIATION_CLASS",
            "BIND_EACH_PROCESS_REQUEST_TO_FINAL_EFFECT_AUTHORIZER_SEMANTICS",
            "INSTALL_BEFORE_ANY_CREDITED_RUNTIME_EXECUTION",
            "PROVE_CHILD_PROGRAM_INTERNAL_EFFECTS_ARE_SANDBOXED_OR_SEPARATELY_MEDIATED",
            "PROVE_NATIVE_EXTENSION_AND_NON_PYTHON_PROCESS_CREATION_ROUTES",
            "INDEPENDENTLY_VERIFY_EXACT_REPO_BYTES_AND_RUNTIME_DELEGATION_PREMISE",
        ],
        "hard_nonclaims": [
            "NO_CLAIM_CHILD_INTERNAL_EFFECTS_ARE_CONTROLLED_BY_THE_POPEN_CHOKEPOINT",
            "NO_CLAIM_NATIVE_EXTENSION_PROCESS_CREATION_IS_INTERCEPTED",
            "NO_CLAIM_SEMANTIC_EFFECT_AUTHORIZATION_IS_IMPLEMENTED",
            "NO_CLAIM_C1_C2_OR_C3_COMPLETE",
            "NO_ROOT3_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "new_reality_units_consumed": 0,
            "terminal_cases_consumed": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))

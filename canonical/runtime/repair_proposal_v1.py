"""Offer repairs as PROPOSALS; let the universal solver's verifier decide.

The brain already contains the general control loop --
universal_verified_adaptive_solver_v1. It converges on any task by proposing
and verifying against an immutable, module-owned verifier, which is why it
generalises without having seen the task. Proposals have zero authority there.

So this module does not decide anything. repair_v1 proposes a candidate --
"run it this way instead" -- and the solver's TYPED_ACCEPTANCE_PROGRAM_V1
verifier accepts or falsifies it. If the program is not satisfied, the
proposal is worth nothing, whatever repair_v1 thought of it.

Before this existed, repair_v1 scored its own results with its own gates.
That was a second, weaker authority running beside the one that is
immutable by design.
"""
from __future__ import annotations

import re

try:  # works both as a package and as a sibling on sys.path
    from canonical.runtime.typed_acceptance_program_v1 import PROGRAM_SCHEMA
except ImportError:  # pragma: no cover
    from typed_acceptance_program_v1 import PROGRAM_SCHEMA

SCHEMA = "PROJECT_BRAIN_REPAIR_PROPOSAL_V1"

# A real test run, stated as a typed acceptance program. Nothing here says
# how to run tests -- only what counts as having run them. The how is
# repair_v1's proposal; the whether is the solver's.


def program(min_tests: int = 1) -> dict:
    """The typed program: at least N tests ran, and the run was OK."""
    return {
        "schema": PROGRAM_SCHEMA,
        "fields": [
            {"id": "tests_ran", "type": "number", "dimension": "count",
             "source": "candidate"},
            {"id": "ok", "type": "boolean", "dimension": "dimensionless",
             "source": "candidate"},
        ],
        "accept_when": {"op": "and", "args": [
            {"op": "ge",
             "left": {"op": "ref", "id": "tests_ran"},
             "right": {"op": "const", "type": "number", "dimension": "count",
                       "value": float(min_tests)}},
            {"op": "ref", "id": "ok"},
        ]},
    }


def observe(output: str, exited_zero: bool | None = None) -> dict:
    """Read what a command actually produced. Facts only, no verdict.

    How many tests ran is read from the output, structurally -- no
    framework's wording is assumed. Whether the run was sound comes from
    the exit status when it is known, which the machine attests, rather
    than from a word in the output, which the program chose to print. When
    no exit status is available the fallback is that tests ran and none
    were reported failed; that is weaker, and it is not silently presented
    as equal to the attested case.
    """
    try:
        from canonical.runtime import repair_v1
    except ImportError:  # pragma: no cover
        import repair_v1
    ran, n, _kind = repair_v1.tests_ran(output)
    if exited_zero is not None:
        ok = bool(exited_zero)
    else:
        ok = bool(ran) and repair_v1.failure_count(output) == 0
    return {"tests_ran": n, "ok": ok}


def problem(min_tests: int = 1, trusted: dict | None = None) -> dict:
    """The task contract handed to the universal solver."""
    return {
        "schema": SCHEMA,
        "capabilities": [{
            "id": "tests_were_run",
            # `provides` is what makes the capability plannable: the planner
            # searches backwards from target_effects over these.
            "provides": ["tests_were_run"],
            "action": {
                "type": "verify",
                "verifier_id": "TYPED_ACCEPTANCE_PROGRAM_V1",
                "verifier_payload": {
                    "program": program(min_tests),
                    "trusted_values": dict(trusted or {}),
                },
            },
        }],
        "initial_facts": [],
        "target_effects": ["tests_were_run"],
    }


def propose(command: str, root: str, min_tests: int = 1, timeout: int = 300) -> dict:
    """Repair a command, then let the solver's verifier judge the result.

    repair_v1 proposes how to run it. The observed facts come from what
    actually ran. The decision belongs entirely to the solver.
    """
    try:
        from canonical.runtime import repair_v1
        from canonical.runtime.universal_verified_adaptive_solver_v1 import run
    except ImportError:  # pragma: no cover
        import repair_v1
        from universal_verified_adaptive_solver_v1 import run

    res = repair_v1.attempt(command, root, timeout=timeout)
    observed = observe(res.get("output") or "", exited_zero=bool(res.get("ok")))
    pr = problem(min_tests)
    verdict = run(pr, proposal_packets={"tests_were_run": [{"candidate_values": observed}]})
    return {
        "schema": SCHEMA,
        "command": command,
        "repaired_command": res.get("command"),
        "observed": observed,
        "output": res.get("output") or "",
        "repair_trace": res.get("attempts", []),
        "solver": verdict,
    }

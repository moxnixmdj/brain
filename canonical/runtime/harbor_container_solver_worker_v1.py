#!/usr/bin/env python3
"""Container-side Brain solve worker. Never grants authority or verifies isolation.

This program must only be dispatched inside a suitably confined task container.
The experimental Harbor path checks Docker configuration but has not been
independently verified. The JSON output is an untrusted raw solver response,
not a verified effect.
"""
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

MARKER = "BRAIN_CONTAINER_SOLVE_V1:"
MAX_REQUEST_BYTES = 64_000


def main() -> int:
    if len(sys.argv) != 2:
        raise ValueError("REQUEST_ARGUMENT_REQUIRED")
    raw = base64.b64decode(sys.argv[1], validate=True)
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError("REQUEST_TOO_LARGE")
    request = json.loads(raw)
    if not isinstance(request, dict) or not isinstance(request.get("goal"), str):
        raise ValueError("REQUEST_INVALID")
    inputs = request.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("INPUTS_INVALID")
    mode = request.get("mode")
    if not isinstance(mode, str) or len(mode) > 64:
        raise ValueError("MODE_INVALID")

    # This file is invoked as a script under an externally read-only Brain
    # root. -I -B is used by the dispatcher; never rely on task PYTHONPATH.
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    # Try only the narrow, exact terminal grammar before ordinary model routing.
    # The bridge reads the task workspace and proposes an action; it does not
    # execute the copy or call solve. Unknown tasks use the existing route.
    if inputs.get("harbor_suite") == "terminal-bench-4":
        from canonical.runtime.harbor_terminal_copy_bridge_v1 import propose
        proposal = propose(inputs.get("harbor_task"), inputs.get("observations"), os.getcwd())
        if proposal is not None:
            proposal["proposal_source"] = "DETERMINISTIC_TERMINAL_COPY_V1"
            print(MARKER + json.dumps(proposal, sort_keys=True), flush=True)
            return 0

    # Inspect only through this container worker; these hints are untrusted
    # observations, not an executable plan or evidence of a failing test.
    grounding = None
    if inputs.get("harbor_suite") == "pro-v2" and inputs.get("observations") == []:
        from canonical.runtime.harbor_pro_grounding_v1 import ground
        grounding = ground(inputs.get("harbor_task"), inputs.get("harbor_repo"))

    from canonical.runtime.brain_unified_model_v1 import open_model

    # Keep the routing ledger out of the read-only Brain tree. This setting
    # alone cannot constrain all writes made by every route.
    inputs = dict(inputs)
    if grounding is not None:
        inputs["harbor_grounding"] = grounding
    inputs["ledger_db_path"] = "/tmp/brain-harbor-routing.sqlite"
    result = open_model(root=root).solve(
        request["goal"], inputs=inputs, mode=mode, context_paths=[], cwd=os.getcwd()
    )
    if not isinstance(result, dict):
        raise ValueError("SOLVER_RESULT_NOT_OBJECT")
    if grounding is not None:
        result["harbor_grounding"] = grounding
    print(MARKER + json.dumps(result, sort_keys=True, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

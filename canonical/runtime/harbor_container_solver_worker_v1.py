#!/usr/bin/env python3
"""Container-side Brain solve worker. Never grants authority or verifies isolation.

This program must only be dispatched inside an independently checked task
container. The production Harbor entry point stays disabled until that check,
read-only staging, and benchmark-specific artifact verification are integrated.
The JSON output is an untrusted raw solver response, not a verified effect.
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
    from canonical.runtime.brain_unified_model_v1 import open_model

    # Keep the routing ledger out of the read-only Brain tree. This setting
    # alone cannot constrain all writes made by every route.
    inputs = dict(inputs)
    inputs["ledger_db_path"] = "/tmp/brain-harbor-routing.sqlite"
    result = open_model(root=root).solve(
        request["goal"], inputs=inputs, mode=mode, context_paths=[], cwd=os.getcwd()
    )
    if not isinstance(result, dict):
        raise ValueError("SOLVER_RESULT_NOT_OBJECT")
    print(MARKER + json.dumps(result, sort_keys=True, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Zero-authority finite-domain probe for executable-refinement proof routing."""
from __future__ import annotations

SCHEMA = "PROJECT_BRAIN_FINITE_DOMAIN_REFINEMENT_PROBE_V1"

def run(value: str) -> dict[str, object]:
    if value == "A":
        return {"schema": SCHEMA, "status": "PASS_A", "value": 1, "terminal_authority": False}
    if value == "B":
        return {"schema": SCHEMA, "status": "PASS_B", "value": 2, "terminal_authority": False}
    if value == "C":
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "value": None, "terminal_authority": False}
    raise ValueError("INPUT_OUTSIDE_CERTIFIED_DOMAIN")

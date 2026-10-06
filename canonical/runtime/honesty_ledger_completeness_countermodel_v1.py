from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from canonical.runtime import honesty_envelope_v1 as honesty

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_HONESTY_LEDGER_COMPLETENESS_COUNTERMODEL_RESULT_V1"
ENVELOPE = "canonical/runtime/honesty_envelope_v1.py"
EXPECTED_BLOB = "1ff02d62322b76068933498e869b1ee22949b991"


def _blob(path: str) -> str:
    raw = (ROOT / path).read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode() + b"\0" + raw
    ).hexdigest()


def _record() -> dict[str, Any]:
    return {
        "schema": "PROJECT_BRAIN_HONESTY_ENVELOPE_INPUT_V1",
        "task_contract": {
            "task_id": "COUNTERMODEL",
            "required_obligations": ["o1"],
        },
        "obligations": [
            {
                "id": "o1",
                "state": "VERIFIED",
                "receipts": [hashlib.sha256(b"o1").hexdigest()],
            }
        ],
        "completion_claim": "COMPLETE",
        "provenance_events": [],
        "material_claims": [],
        "belief_assertions": [],
    }


def evaluate() -> dict[str, Any]:
    errors: list[str] = []
    if _blob(ENVELOPE) != EXPECTED_BLOB:
        errors.append("HONESTY_ENVELOPE_BLOB_DRIFT")

    record = _record()
    verdict_a = honesty.adjudicate(record)
    verdict_b = honesty.adjudicate(record)

    # World B contains omitted semantic facts outside the sidecar record.
    world_a = {
        "external_payload": "fixed nonassertive token",
        "omitted_material_claims": [],
        "omitted_material_provenance": [],
    }
    world_b = {
        "external_payload": "The experiment succeeded.",
        "omitted_material_claims": ["experiment_succeeded"],
        "omitted_material_provenance": ["preexisting_hidden_answer"],
    }

    if verdict_a.get("status") != "PASS":
        errors.append("WORLD_A_DID_NOT_PASS")
    if verdict_b.get("status") != "PASS":
        errors.append("WORLD_B_DID_NOT_PASS")
    if verdict_a != verdict_b:
        errors.append("ENVELOPE_VERDICTS_NOT_IDENTICAL")
    if not world_b["omitted_material_claims"]:
        errors.append("WORLD_B_MATERIAL_CLAIM_NOT_CONSTRUCTED")
    if not world_b["omitted_material_provenance"]:
        errors.append("WORLD_B_MATERIAL_PROVENANCE_NOT_CONSTRUCTED")

    ok = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__TWO_WORLD_LEDGER_COMPLETENESS_NON_IDENTIFIABILITY_CONFIRMED__ZERO_CREDIT"
            if ok else "FAIL_CLOSED"
        ),
        "pass": ok,
        "errors": errors,
        "same_envelope_input": True,
        "same_envelope_verdict": verdict_a == verdict_b,
        "world_a": world_a,
        "world_b": world_b,
        "ledger_completeness_identified": False if ok else None,
        "repair_required": "LEDGER_FIRST_CONSTRUCTION_OR_EQUIVALENT_TOTALIZATION",
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


if __name__ == "__main__":
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)

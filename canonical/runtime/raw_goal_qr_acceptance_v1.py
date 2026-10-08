"""Independent raw acceptance for strict QR image generation goals.

Admitted language:
  Generate a QR code image for the text "<payload>" and save it to
  canonical/astra_runtime/tmp/<name>.png

Preflight recompiles the goal through the existing deterministic goal compiler
and requires the verified qrencode capability with exact bound inputs.
Acceptance freshly decodes the produced PNG through the separately verified
zbar decoder and compares the decoded payload exactly. Generator success alone
is never acceptance.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping

from canonical.runtime import goal_compiler
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.verified_bound_capability_execution_adapter_v1 import execute as execute_bound

SCHEMA = "PROJECT_BRAIN_RAW_GOAL_QR_ACCEPTANCE_V1"
ROUTING_EFFECT = "image.qr.generate"
QR_CAPABILITY_ID = "image.qr.generate.qrencode"
DECODER_CAPABILITY_ID = "image.code.decode.zbarimg"
ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

GRAMMAR = re.compile(
    r'^Generate a QR code image for the text "(?P<payload>[^"\r\n]{1,2048})" '
    r'and save it to (?P<output>canonical/astra_runtime/tmp/[A-Za-z0-9_.-]+\.png)\.?$'
)


def _registry() -> Mapping[str, Any]:
    doc = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    caps = doc.get("capabilities")
    if not isinstance(caps, Mapping):
        raise ValueError("BOUND_CAPABILITY_REGISTRY_INVALID")
    return caps


def preflight(goal: str, *, root: str | Path = ROOT) -> dict[str, Any]:
    text = str(goal or "")
    match = GRAMMAR.fullmatch(text)
    if match is None:
        return {
            "schema": SCHEMA,
            "status": "NO_MATCH",
            "pass": False,
            "matched": False,
            "semantic_acceptance_complete": False,
            "terminal_authority": False,
        }

    payload = match.group("payload")
    output_path = match.group("output")
    pp = PurePosixPath(output_path)
    if pp.is_absolute() or ".." in pp.parts or pp.suffix.lower() != ".png":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "matched": False,
            "reason": "QR_OUTPUT_PATH_OUTSIDE_ADMITTED_SCOPE",
            "semantic_acceptance_complete": False,
            "terminal_authority": False,
        }

    try:
        compiled = goal_compiler.compile_goal(text, _registry(), Path(root))
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "matched": False,
            "reason": "QR_GOAL_COMPILATION_FAILED:" + type(exc).__name__ + ":" + str(exc),
            "semantic_acceptance_complete": False,
            "terminal_authority": False,
        }

    if (
        compiled.get("compiler_mode") != "DETERMINISTIC_VERIFIED_CAPABILITY_MATCH"
        or compiled.get("selected_capability") != QR_CAPABILITY_ID
        or compiled.get("inputs") != {"output_path": output_path, "text": payload}
        or compiled.get("target_effects") != [ROUTING_EFFECT]
    ):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "matched": False,
            "reason": "QR_COMPILED_CONTRACT_MISMATCH",
            "compiled": compiled,
            "semantic_acceptance_complete": False,
            "terminal_authority": False,
        }

    return {
        "schema": SCHEMA,
        "status": "QR_RAW_GOAL_MATCHED",
        "pass": False,
        "matched": True,
        "goal_sha256": sha256(text.encode("utf-8")).hexdigest(),
        "payload": payload,
        "payload_sha256": sha256(payload.encode("utf-8")).hexdigest(),
        "output_path": output_path,
        "capability_id": QR_CAPABILITY_ID,
        "decoder_capability_id": DECODER_CAPABILITY_ID,
        "compiler_mode": compiled["compiler_mode"],
        "preflight_execution_authority": False,
        "semantic_acceptance_complete": False,
        "terminal_authority": False,
    }


def verify(
    *, goal: str, raw_result: Mapping[str, Any], root: str | Path = ROOT
) -> dict[str, Any]:
    pf = preflight(goal, root=root)
    if pf.get("matched") is not True:
        return {
            **pf,
            "status": "FAIL_CLOSED__QR_GOAL_NOT_MATCHED",
            "accepted_obligation_ids": [],
        }
    if not isinstance(raw_result, Mapping):
        return {
            **pf,
            "status": "FAIL_CLOSED__RAW_RESULT_NOT_OBJECT",
            "accepted_obligation_ids": [],
        }

    contract = compile_contract(
        str(goal),
        source_id="user",
        routing_target_effects=[ROUTING_EFFECT],
    )
    if contract.get("pass") is not True:
        return {
            **pf,
            "status": "FAIL_CLOSED__LOSSLESS_RAW_CONTRACT_INVALID",
            "accepted_obligation_ids": [],
            "contract_errors": contract.get("errors"),
        }

    decode = execute_bound(
        DECODER_CAPABILITY_ID,
        inputs={"path": pf["output_path"]},
    )
    observed = None
    if decode.get("pass") is True:
        result = decode.get("result")
        if isinstance(result, Mapping) and isinstance(result.get("stdout"), str):
            observed = result["stdout"].rstrip("\r\n")

    obligations = contract["acceptance_contract"]["obligations"]
    required_ids = list(contract["acceptance_contract"]["required_obligation_ids"])
    exact_decode = observed == pf["payload"]
    full = (
        raw_result.get("pass") is True
        and raw_result.get("compiler_mode") == "DETERMINISTIC_VERIFIED_CAPABILITY_MATCH"
        and raw_result.get("compiled_capability_id") == QR_CAPABILITY_ID
        and raw_result.get("raw_goal_sha256") == pf["goal_sha256"]
        and raw_result.get("raw_task_contract_sha256") == contract["task_contract_sha256"]
        and raw_result.get("raw_source_coverage_complete") is True
        and raw_result.get("raw_acceptance_obligation_count") == len(obligations)
        and raw_result.get("model_dependency_count") == 0
        and raw_result.get("cognition_dependency_class") == "MODEL_INDEPENDENT"
        and decode.get("pass") is True
        and exact_decode
        and len(required_ids) == len(obligations)
        and len(required_ids) > 0
    )

    if not full:
        return {
            "schema": SCHEMA,
            "status": "OPEN__QR_RAW_ACCEPTANCE_NOT_VERIFIED",
            "pass": False,
            "matched": True,
            "goal_sha256": pf["goal_sha256"],
            "payload_sha256": pf["payload_sha256"],
            "output_path": pf["output_path"],
            "decoder_pass": decode.get("pass") is True,
            "decoded_payload_exact": exact_decode,
            "required_obligation_count": len(required_ids),
            "accepted_obligation_ids": [],
            "semantic_acceptance_complete": False,
            "actual_goal_satisfaction_verified": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS__QR_RAW_GOAL_ACCEPTED",
        "pass": True,
        "matched": True,
        "goal_sha256": pf["goal_sha256"],
        "payload_sha256": pf["payload_sha256"],
        "output_path": pf["output_path"],
        "decoder_capability_id": DECODER_CAPABILITY_ID,
        "decoder_result_sha256": decode.get("result_sha256"),
        "decoded_payload_exact": True,
        "required_obligation_count": len(required_ids),
        "accepted_obligation_ids": required_ids,
        "semantic_acceptance_complete": True,
        "actual_goal_satisfaction_verified": True,
        "routing_success_authority": False,
        "acceptance_basis": (
            "STRICT_QR_GOAL_GRAMMAR__DETERMINISTIC_VERIFIED_QR_CAPABILITY_BINDING__"
            "LOSSLESS_RAW_SOURCE_COVERAGE__FRESH_INDEPENDENT_ZBAR_DECODE_EQUALS_REQUESTED_PAYLOAD"
        ),
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }

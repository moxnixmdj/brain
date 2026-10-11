"""Fail-closed Inspect ModelAPI adapter for Brain Chartography evaluation.

This module is plumbing only. It does not provide a multimodal capability.
It will not initialize unless a separately verified, Brain-controlled,
zero-incremental-spend multimodal backend binding is supplied.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from inspect_ai.model import (
    ChatMessage,
    ChatMessageUser,
    ContentImage,
    ContentText,
    GenerateConfig,
    ModelAPI,
    ModelOutput,
    modelapi,
)
from inspect_ai.tool import ToolChoice, ToolInfo

ROOT = Path(__file__).resolve().parents[3]
BINDING_SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_MULTIMODAL_BACKEND_BINDING_V1"
REQUEST_SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_MULTIMODAL_REQUEST_V1"
RESPONSE_SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_MULTIMODAL_RESPONSE_V1"
REQUIRED_BACKEND_STATUS = "VERIFIED_BOUND_MULTIMODAL_BACKEND"


class ChartographyAdapterError(RuntimeError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_repo_path(raw: str) -> Path:
    value = str(raw or "").strip()
    if not value:
        raise ChartographyAdapterError("PATH_REQUIRED")
    p = Path(value)
    if not p.is_absolute():
        p = ROOT / p
    p = p.resolve()
    root = ROOT.resolve()
    if p == root or root not in p.parents:
        raise ChartographyAdapterError("PATH_OUTSIDE_BRAIN_ROOT")
    return p


def _load_binding(binding_path: str) -> dict[str, Any]:
    path = _safe_repo_path(binding_path)
    try:
        binding = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ChartographyAdapterError("BACKEND_BINDING_UNREADABLE") from exc
    if binding.get("schema") != BINDING_SCHEMA:
        raise ChartographyAdapterError("BACKEND_BINDING_SCHEMA_INVALID")
    if binding.get("status") != REQUIRED_BACKEND_STATUS:
        raise ChartographyAdapterError("BACKEND_NOT_INDEPENDENTLY_VERIFIED")
    if binding.get("input_contract") != "QUESTION_PLUS_IMAGE_BYTES_V1":
        raise ChartographyAdapterError("BACKEND_INPUT_CONTRACT_MISMATCH")
    if binding.get("output_contract") != "ANSWER_TEXT_V1":
        raise ChartographyAdapterError("BACKEND_OUTPUT_CONTRACT_MISMATCH")
    if binding.get("capability_internalization_status") != "INTERNALIZED_CONFIGURED":
        raise ChartographyAdapterError("CAPABILITY_NOT_INTERNALIZED")
    if binding.get("brain_controlled") is not True:
        raise ChartographyAdapterError("BACKEND_NOT_BRAIN_CONTROLLED")
    if binding.get("external_model_dependency_count") != 0:
        raise ChartographyAdapterError("EXTERNAL_MODEL_DEPENDENCY_FORBIDDEN")
    if binding.get("network_required") is not False:
        raise ChartographyAdapterError("NETWORK_DEPENDENCY_FORBIDDEN")
    if binding.get("fallback_allowed") is not False:
        raise ChartographyAdapterError("BACKEND_FALLBACK_FORBIDDEN")
    try:
        spend = float(binding.get("incremental_spend_usd"))
    except Exception as exc:
        raise ChartographyAdapterError("BACKEND_SPEND_INVALID") from exc
    if spend != 0.0:
        raise ChartographyAdapterError("NONZERO_INCREMENTAL_SPEND_FORBIDDEN")

    backend_id = str(binding.get("backend_id") or "").strip()
    if not backend_id:
        raise ChartographyAdapterError("BACKEND_ID_REQUIRED")
    program = _safe_repo_path(str(binding.get("program_path") or ""))
    if not program.is_file():
        raise ChartographyAdapterError("BACKEND_PROGRAM_MISSING")
    expected = str(binding.get("program_sha256") or "").lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise ChartographyAdapterError("BACKEND_PROGRAM_SHA256_INVALID")
    actual = _sha256(program.read_bytes())
    if actual != expected:
        raise ChartographyAdapterError("BACKEND_PROGRAM_HASH_MISMATCH")
    timeout_s = binding.get("timeout_s", 120)
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)):
        raise ChartographyAdapterError("BACKEND_TIMEOUT_INVALID")
    if timeout_s <= 0 or timeout_s > 600:
        raise ChartographyAdapterError("BACKEND_TIMEOUT_OUT_OF_RANGE")

    out = dict(binding)
    out["_binding_path"] = path.as_posix()
    out["_program"] = program.as_posix()
    out["_timeout_s"] = float(timeout_s)
    return out


def _image_bytes(image_ref: str) -> bytes:
    ref = str(image_ref or "")
    if not ref:
        raise ChartographyAdapterError("IMAGE_REFERENCE_EMPTY")
    if ref.startswith("data:"):
        head, sep, payload = ref.partition(",")
        if not sep or ";base64" not in head.lower():
            raise ChartographyAdapterError("ONLY_BASE64_DATA_URI_SUPPORTED")
        try:
            return base64.b64decode(payload, validate=True)
        except Exception as exc:
            raise ChartographyAdapterError("IMAGE_DATA_URI_INVALID") from exc
    if ref.startswith(("http://", "https://")):
        raise ChartographyAdapterError("REMOTE_IMAGE_FETCH_FORBIDDEN")
    p = Path(ref)
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    else:
        p = p.resolve()
    if not p.is_file():
        raise ChartographyAdapterError("IMAGE_FILE_MISSING")
    return p.read_bytes()


def _extract_exact_request(input: list[ChatMessage]) -> dict[str, Any]:
    if len(input) != 1 or not isinstance(input[0], ChatMessageUser):
        raise ChartographyAdapterError("EXACT_SINGLE_USER_MESSAGE_REQUIRED")
    content = input[0].content
    if not isinstance(content, list) or len(content) != 2:
        raise ChartographyAdapterError("EXACT_TEXT_IMAGE_CONTENT_REQUIRED")
    text, image = content
    if not isinstance(text, ContentText) or not isinstance(image, ContentImage):
        raise ChartographyAdapterError("CONTENT_ORDER_MUST_BE_TEXT_THEN_IMAGE")
    question = text.text
    if not isinstance(question, str) or not question:
        raise ChartographyAdapterError("QUESTION_EMPTY")
    raw = _image_bytes(image.image)
    return {
        "question": question,
        "question_sha256": _sha256(question.encode("utf-8")),
        "image_original_ref": image.image,
        "image_detail": image.detail,
        "image_sha256": _sha256(raw),
        "image_bytes_b64": base64.b64encode(raw).decode("ascii"),
    }


def _invoke_backend(binding: dict[str, Any], request: dict[str, Any]) -> str:
    envelope = {
        "schema": REQUEST_SCHEMA,
        "backend_id": binding["backend_id"],
        **request,
    }
    # The backend is required to be offline and Brain-controlled by its separately
    # verified binding. Do not forward provider/API credentials into the process.
    allowed_env = {}
    for key in ("PATH", "HOME", "TMPDIR", "TEMP", "TMP", "PYTHONPATH"):
        if key in os.environ:
            allowed_env[key] = os.environ[key]
    allowed_env["PROJECT_BRAIN_OFFLINE"] = "1"
    proc = subprocess.run(
        [sys.executable, binding["_program"]],
        input=json.dumps(envelope, sort_keys=True, separators=(",", ":")),
        text=True,
        capture_output=True,
        cwd=ROOT,
        env=allowed_env,
        timeout=binding["_timeout_s"],
        check=False,
    )
    if proc.returncode != 0:
        raise ChartographyAdapterError(
            "BACKEND_EXECUTION_FAILED:" + proc.stderr[-1000:].replace("\n", " ")
        )
    try:
        response = json.loads(proc.stdout)
    except Exception as exc:
        raise ChartographyAdapterError("BACKEND_RESPONSE_NOT_JSON") from exc
    if response.get("schema") != RESPONSE_SCHEMA:
        raise ChartographyAdapterError("BACKEND_RESPONSE_SCHEMA_INVALID")
    if response.get("backend_id") != binding["backend_id"]:
        raise ChartographyAdapterError("BACKEND_RESPONSE_ID_MISMATCH")
    if response.get("question_sha256") != request["question_sha256"]:
        raise ChartographyAdapterError("BACKEND_QUESTION_BINDING_MISMATCH")
    if response.get("image_sha256") != request["image_sha256"]:
        raise ChartographyAdapterError("BACKEND_IMAGE_BINDING_MISMATCH")
    if response.get("fallback_used") is not False:
        raise ChartographyAdapterError("BACKEND_FALLBACK_USED")
    try:
        spend = float(response.get("incremental_spend_usd"))
    except Exception as exc:
        raise ChartographyAdapterError("BACKEND_RESPONSE_SPEND_INVALID") from exc
    if spend != 0.0:
        raise ChartographyAdapterError("BACKEND_RESPONSE_NONZERO_SPEND")
    answer = response.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ChartographyAdapterError("BACKEND_ANSWER_EMPTY")
    return answer


@modelapi(name="brain-chartography")
class BrainChartographyModelAPI(ModelAPI):
    """Inspect provider for a separately verified internal Brain multimodal backend."""

    def __init__(
        self,
        model_name: str,
        base_url: str | None = None,
        api_key: str | None = None,
        config: GenerateConfig = GenerateConfig(),
        binding_path: str | None = None,
        **model_args: Any,
    ) -> None:
        if base_url:
            raise ChartographyAdapterError("EXTERNAL_BASE_URL_FORBIDDEN")
        if api_key:
            raise ChartographyAdapterError("EXTERNAL_API_KEY_FORBIDDEN")
        super().__init__(model_name, None, None, [], config)
        path = binding_path or os.environ.get(
            "PROJECT_BRAIN_CHARTOGRAPHY_BACKEND_BINDING", ""
        )
        if not path:
            raise ChartographyAdapterError("VERIFIED_BACKEND_BINDING_REQUIRED")
        self.binding = _load_binding(path)
        self.model_args = model_args

    def connection_key(self) -> str:
        return str(self.binding["backend_id"])

    async def generate(
        self,
        input: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        if tools:
            raise ChartographyAdapterError("TOOLS_NOT_ALLOWED_IN_CHARTOGRAPHY_MODEL_CALL")
        request = _extract_exact_request(input)
        answer = _invoke_backend(self.binding, request)
        model = self.qualified_model_name or self.model_name
        return ModelOutput.from_content(model=model, content=answer)

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Protocol

from canonical.runtime.chartography_crop_tool_v1 import crop_image

class VisualInfer(Protocol):
    def __call__(
        self,
        image_path: str,
        prompt: str,
        transcript: list[dict[str, Any]],
    ) -> str: ...

def _parse_action(raw: str) -> dict[str, Any]:
    try:
        obj = json.loads(raw)
    except Exception as exc:
        raise ValueError("MODEL_ACTION_MUST_BE_JSON") from exc
    if not isinstance(obj, dict):
        raise ValueError("MODEL_ACTION_OBJECT_REQUIRED")
    keys = set(obj)
    if keys == {"final"} and isinstance(obj["final"], str) and obj["final"].strip():
        return {"kind": "final", "answer": obj["final"].strip()}
    allowed = {"tool", "left", "top", "right", "bottom"}
    if keys == allowed and obj.get("tool") == "crop":
        vals = [obj[k] for k in ("left", "top", "right", "bottom")]
        if any(type(v) is not int for v in vals):
            raise ValueError("CROP_COORDINATES_MUST_BE_INTEGERS")
        return {"kind": "crop", "box": tuple(vals)}
    raise ValueError("UNSUPPORTED_MODEL_ACTION")

def run_with_tools(
    image_path: str | Path,
    prompt: str,
    infer: VisualInfer,
    *,
    workdir: str | Path,
    max_crop_calls: int = 8,
) -> dict[str, Any]:
    src = Path(image_path).resolve(strict=True)
    outdir = Path(workdir)
    outdir.mkdir(parents=True, exist_ok=True)
    transcript: list[dict[str, Any]] = []
    current = src
    crop_calls = 0
    while True:
        raw = infer(str(current), prompt, list(transcript))
        action = _parse_action(raw)
        if action["kind"] == "final":
            transcript.append({
                "step": len(transcript),
                "image": str(current),
                "model_raw": raw,
                "final": action["answer"],
            })
            return {
                "status": "PASS__FINAL",
                "answer": action["answer"],
                "crop_calls": crop_calls,
                "transcript": transcript,
            }
        if crop_calls >= max_crop_calls:
            raise RuntimeError("CROP_CALL_LIMIT_EXCEEDED")
        box = action["box"]
        dst = outdir / f"crop_{crop_calls:02d}.png"
        receipt = crop_image(current, dst, *box)
        transcript.append({
            "step": len(transcript),
            "image": str(current),
            "model_raw": raw,
            "tool": "crop",
            "crop_receipt": receipt,
        })
        current = dst.resolve()
        crop_calls += 1

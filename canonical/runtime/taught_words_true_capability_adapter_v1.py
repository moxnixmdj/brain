"""True-capability adapter for the taught-words row (canonical/laws/TRUE_CAPABILITY_TEST_LAW_V1.md).

One described instance is written to a scratch file inside the repository and its sentence is asked
through the one front door, `live_brain_route_admission_v1.solve`, so the exact live route is what
is measured.  No reading logic is in this file.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import live_brain_route_admission_v1 as _door

_SCRATCH = "canonical/astra_runtime/tmp/taught_words_true_capability"


def solve_through_the_front_door(instance: Mapping[str, Any]) -> dict[str, Any]:
    name = str(instance["file_name"])
    if not name or "/" in name or "\\" in name or name.startswith("."):
        raise ValueError("FILE_NAME_MUST_BE_A_BARE_NAME")
    folder = _door.ROOT / _SCRATCH
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(str(instance["file_text"]).encode("utf-8"))
    try:
        sentence = str(instance["sentence"]).replace("{file}", _SCRATCH + "/" + name)
        result = _door.solve({"task_id": "true_capability_taught_words", "goal": sentence})
        answered = result.get("pass") is True
        answer = result.get("answer")
        if isinstance(answer, Mapping):
            answer = answer.get("value")
        if isinstance(answer, str) and answer.lstrip("-").isdigit():
            answer = int(answer)
        return {
            "answered": answered,
            "answer": answer if answered else None,
            "capability": result.get("compiled_capability_id") if answered else None,
            "status": str(result.get("status"))[:120],
        }
    finally:
        try:
            path.unlink()
        except OSError:
            pass

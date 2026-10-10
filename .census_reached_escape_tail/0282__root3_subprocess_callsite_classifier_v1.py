"""Runtime join from intercepted subprocess calls to the exact Root3 effect-class registry.

The current Root3 universe is already frozen as 18 exact Python process-creation
sites keyed by (repository-relative module path, source line, process API).
This module turns that static proof artifact into a runtime guard without
modifying the 18 callers: an interceptor walks the live Python frame chain and
requires exactly one exact registry key match. Unknown, shifted, outside-repo,
or ambiguous callers fail closed.
"""
from __future__ import annotations

import inspect
from pathlib import Path
from types import FrameType
from typing import Any

from canonical.runtime.root3_subprocess_effect_class_registry_v1 import (
    CLASSES,
    EXPECTED,
)

ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_APIS = {"subprocess.run", "subprocess.Popen"}


class RuntimeCallsiteClassificationError(PermissionError):
    pass


def _repo_relative(filename: str, root: Path) -> str | None:
    try:
        path = Path(filename).resolve()
        resolved_root = root.resolve()
        rel = path.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError):
        return None
    return rel.as_posix()


def classify_frame_chain(
    api: str,
    frame: FrameType | None,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    api = str(api)
    if api not in SUPPORTED_APIS:
        raise RuntimeCallsiteClassificationError("PROCESS_API_UNSUPPORTED:" + api)
    if len(EXPECTED) != 18 or set(EXPECTED.values()) - CLASSES:
        raise RuntimeCallsiteClassificationError("EFFECT_CLASS_REGISTRY_INVARIANT_FAILED")

    matches: list[dict[str, Any]] = []
    observed_repo_frames: list[dict[str, Any]] = []
    cursor = frame
    while cursor is not None:
        rel = _repo_relative(cursor.f_code.co_filename, root)
        if rel is not None:
            line = int(cursor.f_lineno)
            function = str(cursor.f_code.co_name)
            key = (rel, line, api)
            observed_repo_frames.append({
                "module_path": rel,
                "lineno": line,
                "function": function,
            })
            effect_class = EXPECTED.get(key)
            if effect_class is not None:
                matches.append({
                    "module_path": rel,
                    "lineno": line,
                    "process_api": api,
                    "function": function,
                    "effect_class": effect_class,
                })
        cursor = cursor.f_back

    if not matches:
        tail = observed_repo_frames[:8]
        raise RuntimeCallsiteClassificationError(
            "UNREGISTERED_PROCESS_CALLSITE:" + repr(tail)
        )
    unique = {
        (m["module_path"], m["lineno"], m["process_api"], m["effect_class"])
        for m in matches
    }
    if len(unique) != 1:
        raise RuntimeCallsiteClassificationError(
            "AMBIGUOUS_REGISTERED_PROCESS_CALLSITE:" + repr(sorted(unique))
        )
    result = dict(matches[0])
    if result["effect_class"] not in CLASSES:
        raise RuntimeCallsiteClassificationError("UNKNOWN_EFFECT_CLASS")
    result["registry_site_count"] = len(EXPECTED)
    result["runtime_join"] = "EXACT_PATH_LINE_API"
    return result


def detect_effect_class(api: str, *, root: Path = ROOT) -> dict[str, Any]:
    frame = inspect.currentframe()
    try:
        # Skip this helper's own frame; classify the complete outer chain so
        # intermediary wrappers do not need to be trusted or specially named.
        return classify_frame_chain(api, frame.f_back if frame else None, root=root)
    finally:
        del frame

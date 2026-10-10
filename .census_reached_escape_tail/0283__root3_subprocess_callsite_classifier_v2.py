"""Runtime callsite classifier over Root3 whole-runtime process registry V2."""
from __future__ import annotations

import inspect
from pathlib import Path
from types import FrameType
from typing import Any

from canonical.runtime.root3_subprocess_effect_class_registry_v2 import (
    ROOT,
    compile_effect_classes,
)

SUPPORTED_APIS = {"subprocess.run", "subprocess.Popen"}


class RuntimeCallsiteClassificationV2Error(PermissionError):
    pass


_REGISTRY = compile_effect_classes(ROOT)
_REGISTRY_SHA256 = _REGISTRY["registry_sha256"]
_ROWS = _REGISTRY["classified_sites"]
EXPECTED: dict[tuple[str, int, str], dict[str, Any]] = {}
for _row in _ROWS:
    _key = (
        str(_row["module_path"]),
        int(_row["lineno"]),
        str(_row["interception_api"]),
    )
    if _key in EXPECTED:
        raise RuntimeCallsiteClassificationV2Error(
            "INTERCEPTION_KEY_COLLISION:" + repr(_key)
        )
    EXPECTED[_key] = dict(_row)


def _repo_relative(filename: str, root: Path) -> str | None:
    try:
        path = Path(filename).resolve()
        rel = path.relative_to(Path(root).resolve())
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
        raise RuntimeCallsiteClassificationV2Error(
            "PROCESS_API_UNSUPPORTED:" + api
        )

    matches: list[dict[str, Any]] = []
    observed_repo_frames: list[dict[str, Any]] = []
    cursor = frame
    while cursor is not None:
        rel = _repo_relative(cursor.f_code.co_filename, root)
        if rel is not None:
            line = int(cursor.f_lineno)
            fn = str(cursor.f_code.co_name)
            observed_repo_frames.append({
                "module_path": rel,
                "lineno": line,
                "function": fn,
            })
            row = EXPECTED.get((rel, line, api))
            if row is not None:
                matches.append({**row, "runtime_function": fn})
        cursor = cursor.f_back

    if not matches:
        raise RuntimeCallsiteClassificationV2Error(
            "UNREGISTERED_PROCESS_CALLSITE:" + repr(observed_repo_frames[:8])
        )

    identities = {
        (x["module_path"], x["lineno"], x["interception_api"])
        for x in matches
    }
    if len(identities) != 1:
        raise RuntimeCallsiteClassificationV2Error(
            "AMBIGUOUS_REGISTERED_PROCESS_CALLSITE:" + repr(sorted(identities))
        )

    row = dict(matches[0])
    return {
        "module_path": row["module_path"],
        "lineno": int(row["lineno"]),
        "process_api": api,
        "source_api": row["source_api"],
        "function": row["runtime_function"],
        "effect_class": row["effect_class"],
        "classification_provenance": row["classification_provenance"],
        "registry_site_count": len(EXPECTED),
        "registry_sha256": _REGISTRY_SHA256,
        "runtime_join": "EXACT_PATH_LINE_INTERCEPTION_API",
    }


def detect_effect_class(api: str, *, root: Path = ROOT) -> dict[str, Any]:
    frame = inspect.currentframe()
    try:
        return classify_frame_chain(
            api, frame.f_back if frame else None, root=root
        )
    finally:
        del frame


def registry_status() -> dict[str, Any]:
    return {
        "registry_site_count": len(EXPECTED),
        "registry_sha256": _REGISTRY_SHA256,
        "minimum_chokepoints": sorted(SUPPORTED_APIS),
    }

"""True-capability adapter for the copy / rename / append rows (canonical/laws/TRUE_CAPABILITY_TEST_LAW_V1.md).

One described instance is a small folder of files and one English request.  The folder is written to
a scratch path inside the repository, the request is asked through the one front door,
`live_brain_route_admission_v1.solve`, and the folder is read back byte for byte.  No file-changing
logic is in this file: it reports what the door did and what the folder holds afterwards.
"""
from __future__ import annotations

import shutil
from typing import Any, Mapping

from canonical.runtime import live_brain_route_admission_v1 as _door

_SCRATCH = "canonical/astra_runtime/tmp/zqfc"


def _bare(name: Any) -> str:
    name = str(name)
    if not name or "/" in name or "\\" in name or name.startswith("."):
        raise ValueError("NAME_MUST_BE_A_BARE_NAME")
    return name


def solve_through_the_front_door(instance: Mapping[str, Any]) -> dict[str, Any]:
    folder = _door.ROOT / _SCRATCH / _bare(instance["folder"])
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    try:
        for name, text in instance["files"].items():
            (folder / _bare(name)).write_bytes(str(text).encode("utf-8"))
        rel = _SCRATCH + "/" + str(instance["folder"]) + "/"
        sentence = str(instance["sentence"])
        for key in ("src", "dst", "file"):
            if instance.get(key) is not None:
                sentence = sentence.replace("{" + key + "}", rel + _bare(instance[key]))
        result = _door.solve({"task_id": "true_capability_file_change", "goal": sentence})
        answered = result.get("pass") is True
        state = {path.name: path.read_bytes().decode("utf-8", "surrogateescape")
                 for path in sorted(folder.iterdir()) if path.is_file()}
        others = sorted(path.name for path in folder.iterdir() if not path.is_file())
        return {
            "answered": answered,
            "capability": result.get("compiled_capability_id") if answered else None,
            "state": state,
            "not_files": others,
            "status": str(result.get("status"))[:120],
        }
    finally:
        shutil.rmtree(folder, ignore_errors=True)

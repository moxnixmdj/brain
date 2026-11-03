#!/usr/bin/env python3
"""Report metadata about one repository-local file. Python stdlib, nothing else.

The companion of `file_line_count`: the other half of the ordinary questions the
front door could not route on `ec94c97` ("what is the size of a.txt", "what are
the file permissions of a.txt"). Both were refused with the computer-execution
boundary while no capability had been proposed at all -- the boundary was the
last tier answering for an absent row, not a safety decision.

This adapter answers from metadata only. It never reads the file's contents,
never writes, never spawns a process, and refuses any path that resolves outside
the repository root. Every field it returns is read from `os.lstat`-style
metadata through `Path.stat`, so a symlink is reported as the link target's
metadata only after the resolved path has been checked to stay inside the root.
"""
from __future__ import annotations

import pathlib
import stat as statmod


def _safe(root: pathlib.Path, raw: str) -> pathlib.Path:
    p = (root / str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _describe_path(p: pathlib.Path, root: pathlib.Path) -> dict:
    st = p.stat()
    return {
        "path": p.relative_to(root).as_posix(),
        "size_bytes": int(st.st_size),
        "permissions_octal": format(statmod.S_IMODE(st.st_mode), "04o"),
        "is_file": p.is_file(),
        "is_dir": p.is_dir(),
        "is_symlink": p.is_symlink(),
    }


def run(args, root):
    # This capability is registered read-only. A report path would make it a
    # writer and may be synthesized by the binder, so refuse it before reads.
    if args.get("output_path"):
        raise RuntimeError("READ_ONLY_CAPABILITY_REFUSES_OUTPUT_PATH")
    root = pathlib.Path(root).resolve()
    target = _safe(root, args.get("path") or args.get("input_path") or "")
    if not target.name:
        raise RuntimeError("PATH_REQUIRED")
    if not target.exists():
        raise RuntimeError("PATH_NOT_FOUND")
    payload = {
        "schema": "PROJECT_BRAIN_FILE_STAT_V1",
        "adapter": "file_stat",
        **_describe_path(target, root),
    }
    payload.update({"output_path": None, "output_verified": True})
    return payload

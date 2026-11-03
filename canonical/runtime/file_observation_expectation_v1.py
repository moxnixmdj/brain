"""Recheck read-only file metadata and line counts from the stated input.

The verifier reads the file or metadata itself rather than accepting the
adapter's success bit. It does not write a report. This is code-independent
verification, not independent-personnel verification.
"""
from __future__ import annotations

import hashlib
import pathlib
import stat
from collections.abc import Mapping
from typing import Any


def verify(expect: Mapping[str, Any], result: Mapping[str, Any],
           args: Mapping[str, Any], root: pathlib.Path | str) -> tuple[bool, str]:
    try:
        if not isinstance(expect, Mapping) or not isinstance(result, Mapping) or not isinstance(args, Mapping):
            raise ValueError("INVALID_CONTRACT")
        if result.get("output_verified") is not True:
            raise ValueError("PRODUCER_DID_NOT_VERIFY")
        if args.get("output_path") or result.get("output_path") is not None:
            raise ValueError("READ_ONLY_OUTPUT_PATH")
        raw = args.get("path")
        reported = result.get("path")
        if not isinstance(raw, str) or not raw.strip() or not isinstance(reported, str) or not reported.strip():
            raise ValueError("PATH_REQUIRED")
        root = pathlib.Path(root).resolve()
        target = (root / raw).resolve()
        claimed = (root / reported).resolve()
        if target == root or root not in target.parents or claimed != target:
            raise ValueError("PATH_OUTSIDE_ROOT_OR_MISMATCH")
        mode = expect.get("observation")
        if mode == "line_count":
            if expect.get("field") != "line_count":
                raise ValueError("OBSERVATION_FIELD_INVALID")
            if not target.is_file():
                raise ValueError("PATH_NOT_REGULAR_FILE")
            raw_bytes = target.read_bytes()
            text = raw_bytes.decode("utf-8")
            count = len(text.splitlines())
            expected = {"line_count": count, "newline_count": raw_bytes.count(b"\n"),
                        "ends_with_newline": text.endswith("\n"), "byte_count": len(raw_bytes),
                        "source_sha256": hashlib.sha256(raw_bytes).hexdigest(), "answer": count}
        elif mode == "stat":
            if expect.get("field") != "size_bytes":
                raise ValueError("OBSERVATION_FIELD_INVALID")
            info = target.stat()
            expected = {"size_bytes": int(info.st_size),
                        "permissions_octal": format(stat.S_IMODE(info.st_mode), "04o"),
                        "is_file": target.is_file(), "is_dir": target.is_dir(),
                        "is_symlink": target.is_symlink()}
        else:
            raise ValueError("OBSERVATION_UNSUPPORTED")
        for key, value in expected.items():
            observed = result.get(key)
            if type(observed) is not type(value) or observed != value:
                raise ValueError("OBSERVATION_MISMATCH:" + key)
        return True, "FILE_OBSERVATION_REVERIFIED"
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        return False, "FILE_OBSERVATION_REFUSED:" + str(exc)[:200]

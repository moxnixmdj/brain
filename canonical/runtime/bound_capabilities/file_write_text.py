#!/usr/bin/env python3
"""Write text to a repository-local file. Python stdlib, nothing else.

This is the base case the whole registry was missing. Every other capability
consumes a file and none of them produces one, so a chain could never start:
seventy capabilities, all waiting for an input nobody could create. The
machine could read, convert, verify and archive -- but only files a human had
already put there.

With this, a goal can bootstrap its own inputs. That is the difference
between a library of tools and a machine that can act.
"""
from __future__ import annotations
import hashlib
import pathlib


def _safe(root, raw):
    root = pathlib.Path(root).resolve()
    p = (root / str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def run(args, root):
    root = pathlib.Path(root).resolve()
    content = args.get("content")
    output_path = _safe(root, args.get("output_path"))
    if content is None or str(content) == "":
        raise RuntimeError("CONTENT_REQUIRED")
    if not output_path.name or output_path.is_dir():
        raise RuntimeError("OUTPUT_PATH_REQUIRED")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw = str(content).encode("utf-8")
    output_path.write_bytes(raw)
    # read it back: a write that is never read is a claim, not a write
    check = output_path.read_bytes()
    if check != raw:
        raise RuntimeError("WRITE_DID_NOT_ROUNDTRIP")
    return {
        "adapter": "file_write_text",
        "output_path": str(output_path.relative_to(root)),
        "output_bytes": len(check),
        "output_sha256": hashlib.sha256(check).hexdigest(),
        "output_verified": True,
        "content_sha256": hashlib.sha256(raw).hexdigest(),
    }

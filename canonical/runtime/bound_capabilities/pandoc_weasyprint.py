#!/usr/bin/env python3
"""Verified Markdown-to-PDF conversion with typed parent finalization."""
from __future__ import annotations
import pathlib
import subprocess
from canonical.runtime import root3_pandoc_pdf_parent_v1 as parent

def _safe_path(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def run(args, root):
    root=pathlib.Path(root).resolve()
    src=_safe_path(root,args.get("markdown_path"))
    ctx=parent.prepare(args,root,src)
    argv=ctx["argv"]
    try:
        timeout=max(1,min(int(args.get("timeout_s",120)),300))
        binary_mode=False
        capture=True
        proc=subprocess.run(
            argv,cwd=root,text=binary_mode,capture_output=capture,
            timeout=timeout
        )
    except Exception:
        parent.abort(ctx)
        raise
    return parent.finish(ctx,proc)

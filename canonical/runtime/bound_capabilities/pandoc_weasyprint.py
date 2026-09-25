#!/usr/bin/env python3
"""Verified Markdown-to-PDF conversion using Pandoc + WeasyPrint."""
from __future__ import annotations
import hashlib
import pathlib
import subprocess

def _safe_path(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def run(args, root):
    src=_safe_path(root,args.get("markdown_path"))
    dst=_safe_path(root,args.get("output_path"))
    if not src.is_file() or src.suffix.lower() not in {".md",".markdown"}:
        raise RuntimeError("MARKDOWN_INPUT_REQUIRED")
    if dst.suffix.lower()!=".pdf":
        raise RuntimeError("PDF_OUTPUT_REQUIRED")
    dst.parent.mkdir(parents=True,exist_ok=True)
    argv=["pandoc",str(src),"-o",str(dst),"--pdf-engine=weasyprint"]
    proc=subprocess.run(
        argv,cwd=root,text=True,capture_output=True,
        timeout=max(1,min(int(args.get("timeout_s",120)),300))
    )
    if proc.returncode!=0:
        raise RuntimeError("PANDOC_PDF_FAILED:"+proc.stderr[-2000:])
    if not dst.is_file():
        raise RuntimeError("PDF_OUTPUT_MISSING")
    raw=dst.read_bytes()
    if not raw.startswith(b"%PDF-"):
        raise RuntimeError("PDF_MAGIC_MISMATCH")
    return {
      "adapter":"pandoc_weasyprint",
      "argv":argv,
      "returncode":0,
      "input_path":str(src.relative_to(pathlib.Path(root).resolve())),
      "output_path":str(dst.relative_to(pathlib.Path(root).resolve())),
      "output_bytes":len(raw),
      "output_sha256":hashlib.sha256(raw).hexdigest(),
      "output_verified":True,
      "stderr":proc.stderr[-4000:]
    }

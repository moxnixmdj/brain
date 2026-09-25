#!/usr/bin/env python3
"""Generic bounded adapter for verified jq JSON transformations."""
from __future__ import annotations
import hashlib
import pathlib
import re
import subprocess

FORBIDDEN_FILTER_PATTERNS=(
    r"(?<![A-Za-z0-9_.])import\s+",
    r"(?<![A-Za-z0-9_.])include\s+",
    r"(?<![A-Za-z0-9_.])module\s+",
    r"(?<![A-Za-z0-9_.])input\s*\(",
    r"(?<![A-Za-z0-9_.])inputs\b",
    r"(?<![A-Za-z0-9_])env\.",
    r"\$ENV\b",
)

def _safe_path(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def run(args, root):
    src=_safe_path(root,args.get("input_path"))
    if not src.is_file():
        raise RuntimeError("JQ_INPUT_MISSING")
    filt=str(args.get("filter") or "").strip()
    if not filt or len(filt)>8000:
        raise RuntimeError("JQ_FILTER_REQUIRED")
    if any(re.search(pattern,filt,flags=re.IGNORECASE) for pattern in FORBIDDEN_FILTER_PATTERNS):
        raise RuntimeError("JQ_FILTER_FORBIDDEN")
    out=_safe_path(root,args.get("output_path"))
    out.parent.mkdir(parents=True,exist_ok=True)
    argv=["jq"]
    if args.get("raw_output",True):
        argv.append("-r")
    argv.extend([filt,str(src)])
    proc=subprocess.run(
        argv,cwd=root,text=True,capture_output=True,
        timeout=max(1,min(int(args.get("timeout_s",60)),180))
    )
    if proc.returncode!=0:
        raise RuntimeError("JQ_FAILED:"+proc.stderr[-1600:])
    text=proc.stdout
    if args.get("require_nonempty",True) and not text.strip():
        raise RuntimeError("JQ_OUTPUT_EMPTY")
    out.write_text(text,encoding="utf-8")
    raw=out.read_bytes()
    return {
      "adapter":"jq_query",
      "argv":["jq","-r" if args.get("raw_output",True) else "",filt,str(src)],
      "returncode":0,
      "input_path":str(src.relative_to(pathlib.Path(root).resolve())),
      "output_path":str(out.relative_to(pathlib.Path(root).resolve())),
      "output_bytes":len(raw),
      "output_sha256":hashlib.sha256(raw).hexdigest(),
      "output_text_utf8_verified":True,
      "output_text_excerpt":text[:4000],
      "output_verified":True,
      "stderr":proc.stderr[-4000:]
    }

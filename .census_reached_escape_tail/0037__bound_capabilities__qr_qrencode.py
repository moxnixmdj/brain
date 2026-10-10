#!/usr/bin/env python3
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
    text=str(args.get("text") or "")
    if not text:
        raise RuntimeError("QR_TEXT_REQUIRED")
    out=_safe_path(root,args.get("output_path"))
    if out.suffix.lower()!=".png":
        raise RuntimeError("QR_OUTPUT_MUST_BE_PNG")
    out.parent.mkdir(parents=True,exist_ok=True)
    proc=subprocess.run(
        ["qrencode","-o",str(out),text],
        text=True,capture_output=True,timeout=60
    )
    if proc.returncode!=0:
        raise RuntimeError("QRENCODE_FAILED:"+proc.stderr[-1200:])
    raw=out.read_bytes()
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("QR_OUTPUT_NOT_PNG")
    return {
      "adapter":"bound_capability",
      "capability_id":"image.qr.generate.qrencode",
      "output_path":str(out.relative_to(pathlib.Path(root).resolve())),
      "output_bytes":len(raw),
      "output_sha256":hashlib.sha256(raw).hexdigest(),
      "png_signature_valid":True
    }

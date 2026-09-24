#!/usr/bin/env python3
"""Generic zero-shell adapter for verified local command-line suppliers."""
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
    argv=args.get("argv")
    if not isinstance(argv,list) or not argv or any(not isinstance(x,str) or not x for x in argv):
        raise RuntimeError("CLI_ARGV_REQUIRED")
    if len(argv)>64:
        raise RuntimeError("CLI_ARGV_TOO_LARGE")
    output_path=args.get("output_path")
    out=None
    if output_path:
        out=_safe_path(root,output_path)
        out.parent.mkdir(parents=True,exist_ok=True)
    proc=subprocess.run(
        argv,cwd=root,text=False,capture_output=True,timeout=max(1,min(int(args.get("timeout_s",60)),300))
    )
    result={
      "adapter":"bound_capability_cli",
      "argv":argv,
      "returncode":proc.returncode,
      "stdout":proc.stdout[-12000:].decode("utf-8","replace"),
      "stderr":proc.stderr[-12000:].decode("utf-8","replace")
    }
    if proc.returncode!=0:
        raise RuntimeError("CLI_COMMAND_FAILED:"+result["stderr"][-1200:])
    if out is not None:
        if not out.is_file():
            raise RuntimeError("CLI_EXPECTED_OUTPUT_MISSING")
        raw=out.read_bytes()
        prefix=str(args.get("output_prefix_hex") or "").strip().lower()
        if prefix:
            try:
                expected=bytes.fromhex(prefix)
            except ValueError as exc:
                raise RuntimeError("CLI_OUTPUT_PREFIX_HEX_INVALID") from exc
            if not raw.startswith(expected):
                raise RuntimeError("CLI_OUTPUT_PREFIX_MISMATCH")
        if args.get("output_text_utf8") is True:
            try:
                decoded=raw.decode("utf-8","strict")
            except UnicodeDecodeError as exc:
                raise RuntimeError("CLI_OUTPUT_NOT_UTF8") from exc
            if not decoded.strip():
                raise RuntimeError("CLI_OUTPUT_TEXT_EMPTY")
            result["output_text_utf8_verified"]=True
            result["output_text_excerpt"]=decoded[:4000]
        result.update({
          "output_path":str(out.relative_to(pathlib.Path(root).resolve())),
          "output_bytes":len(raw),
          "output_sha256":hashlib.sha256(raw).hexdigest(),
          "output_verified":True
        })
    return result

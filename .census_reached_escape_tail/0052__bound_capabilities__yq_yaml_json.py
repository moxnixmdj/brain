#!/usr/bin/env python3
"""Convert repository-local YAML to canonical JSON using verified Ubuntu yq."""
from __future__ import annotations
import hashlib,json,pathlib,subprocess

def _safe(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p!=root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def run(args, root):
    root=pathlib.Path(root).resolve()
    src=_safe(root,args.get("yaml_path"))
    out=_safe(root,args.get("output_path"))
    if not src.is_file() or src.suffix.lower() not in {".yml",".yaml"}:
        raise RuntimeError("YAML_INPUT_REQUIRED")
    if out.suffix.lower()!=".json":
        raise RuntimeError("JSON_OUTPUT_REQUIRED")
    proc=subprocess.run(
        ["yq",".",str(src)],
        cwd=root,text=True,capture_output=True,
        timeout=max(1,min(int(args.get("timeout_s",60)),120))
    )
    if proc.returncode!=0:
        raise RuntimeError("YQ_FAILED:"+proc.stderr[-1600:])
    try:
        parsed=json.loads(proc.stdout)
    except Exception as exc:
        raise RuntimeError("YQ_OUTPUT_NOT_JSON:"+type(exc).__name__) from exc
    # Serialize deterministically so downstream transforms and hashes do not
    # depend on yq whitespace.
    raw=(json.dumps(parsed,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(raw)
    return {
      "adapter":"yq_yaml_json",
      "input_path":str(src.relative_to(root)),
      "input_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
      "output_path":str(out.relative_to(root)),
      "output_bytes":len(raw),
      "output_sha256":hashlib.sha256(raw).hexdigest(),
      "top_level_type":type(parsed).__name__,
      "output_verified":True,
    }

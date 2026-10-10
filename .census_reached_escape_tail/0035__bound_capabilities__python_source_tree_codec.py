#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,subprocess,sys

def _safe_path(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p!=root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def run(args,root):
    root=pathlib.Path(root).resolve()
    source_root=pathlib.Path(str(args.get("_source_root") or "")).resolve()
    if not source_root.is_dir():
        raise RuntimeError("SOURCE_TREE_ROOT_MISSING")
    mode=str(args.get("mode") or "encode").strip().lower()
    runner=root/"canonical"/"runtime"/"github_source_codec_runner.py"
    if not runner.is_file():
        raise RuntimeError("SOURCE_CODEC_RUNNER_MISSING")
    cfg={
      "source_root":str(source_root),
      "mode":mode,
      "module":str(args.get("module") or ""),
      "encode_callable":args.get("encode_callable"),
      "decode_callable":args.get("decode_callable"),
      "encode_kwargs":args.get("encode_kwargs") or {},
      "decode_kwargs":args.get("decode_kwargs") or {},
      "envelope_key":args.get("envelope_key"),
    }
    if mode=="encode":
        src=_safe_path(root,args.get("json_path"))
        out=_safe_path(root,args.get("output_path"))
        if not src.is_file():
            raise RuntimeError("SOURCE_CODEC_JSON_MISSING")
        out.parent.mkdir(parents=True,exist_ok=True)
        cfg["json_path"]=str(src)
        cfg["output_path"]=str(out)
    elif mode=="decode_verify":
        src=_safe_path(root,args.get("json_path"))
        binary=_safe_path(root,args.get("binary_path"))
        if not src.is_file() or not binary.is_file():
            raise RuntimeError("SOURCE_CODEC_VERIFY_INPUT_MISSING")
        cfg["mode"]="decode"
        cfg["binary_path"]=str(binary)
    else:
        raise RuntimeError("SOURCE_CODEC_MODE_UNSUPPORTED:"+mode)
    proc=subprocess.run(
        [sys.executable,str(runner)],
        cwd=root,text=True,input=json.dumps(cfg),capture_output=True,timeout=90
    )
    if proc.returncode!=0:
        raise RuntimeError("SOURCE_CODEC_RUNNER_FAILED:"+proc.stderr[-1200:])
    try:
        observed=json.loads((proc.stdout or "").strip().splitlines()[-1])
    except Exception as exc:
        raise RuntimeError("SOURCE_CODEC_RUNNER_RESULT_INVALID") from exc
    if observed.get("ok") is not True:
        raise RuntimeError("SOURCE_CODEC_RUNNER_REJECTED:"+json.dumps(observed,sort_keys=True)[:1200])
    if mode=="decode_verify":
        expected=json.loads(src.read_text(encoding="utf-8"))
        return {
          "adapter":"python_source_tree_codec",
          "mode":"decode_verify",
          "verified":observed.get("observed")==expected,
          "module":cfg["module"],
          "decode_callable":cfg["decode_callable"],
        }
    raw=out.read_bytes()
    return {
      "adapter":"python_source_tree_codec",
      "module":cfg["module"],
      "encode_callable":cfg["encode_callable"],
      "source_path":str(src.relative_to(root)),
      "output_path":str(out.relative_to(root)),
      "output_sha256":hashlib.sha256(raw).hexdigest(),
      "output_bytes":len(raw),
      "output_verified":bool(raw) and int(observed.get("bytes") or -1)==len(raw),
    }

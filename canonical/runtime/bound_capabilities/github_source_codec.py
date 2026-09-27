#!/usr/bin/env python3
from __future__ import annotations
import json,pathlib,subprocess,sys

def _inside(root,raw):
    p=(pathlib.Path(root)/str(raw)).resolve()
    rr=pathlib.Path(root).resolve()
    if p!=rr and rr not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def run(args,root):
    root=pathlib.Path(root).resolve()
    source_root=pathlib.Path(str(args.get("_source_root") or "")).resolve()
    if not source_root.is_dir():
        raise RuntimeError("GITHUB_SOURCE_ROOT_MISSING")
    runner=root/"canonical"/"runtime"/"github_source_codec_runner.py"
    common={
      "source_root":str(source_root),
      "module":str(args.get("module") or ""),
      "encode_callable":str(args.get("encode_callable") or ""),
      "decode_callable":str(args.get("decode_callable") or ""),
    }
    if str(args.get("mode") or "")=="decode_verify":
        binary=_inside(root,args.get("binary_path"))
        cfg={**common,"mode":"decode","binary_path":str(binary)}
        p=subprocess.run([sys.executable,str(runner)],input=json.dumps(cfg),text=True,capture_output=True,cwd=root,timeout=60)
        if p.returncode!=0:
            raise RuntimeError("GITHUB_SOURCE_DECODE_FAILED:"+p.stderr[-1200:])
        out=json.loads(p.stdout)
        return {"verified":out.get("ok") is True,"observed":out.get("observed")}
    src=_inside(root,args.get("json_path"))
    out=_inside(root,args.get("output_path"))
    out.parent.mkdir(parents=True,exist_ok=True)
    cfg={**common,"mode":"encode","json_path":str(src),"output_path":str(out)}
    p=subprocess.run([sys.executable,str(runner)],input=json.dumps(cfg),text=True,capture_output=True,cwd=root,timeout=60)
    if p.returncode!=0:
        raise RuntimeError("GITHUB_SOURCE_ENCODE_FAILED:"+p.stderr[-1200:])
    payload=json.loads(p.stdout)
    if payload.get("ok") is not True or not out.is_file() or out.stat().st_size<=0:
        raise RuntimeError("GITHUB_SOURCE_ENCODE_EFFECT_MISSING")
    return {"output_verified":True,"output_path":str(out.relative_to(root)),"output_bytes":out.stat().st_size}

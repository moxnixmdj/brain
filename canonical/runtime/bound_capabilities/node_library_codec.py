#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,subprocess,sys


def _safe(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw)).resolve()
    if p!=root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _run_node(root,cfg,timeout=60):
    runner=pathlib.Path(root)/"canonical"/"runtime"/"node_codec_runner.js"
    proc=subprocess.run(
        ["node",str(runner)],
        input=json.dumps(cfg),text=True,capture_output=True,cwd=root,timeout=timeout
    )
    if proc.returncode!=0:
        raise RuntimeError("NODE_CODEC_RUNNER_FAILED:"+proc.stderr[-1600:])
    try:
        out=json.loads(proc.stdout)
    except Exception as exc:
        raise RuntimeError("NODE_CODEC_RUNNER_JSON_INVALID") from exc
    if out.get("ok") is not True:
        raise RuntimeError("NODE_CODEC_RUNNER_NOT_OK")
    return out


def run(args,root):
    package_root=str(args.get("_package_root") or "").strip()
    if not package_root:
        raise RuntimeError("NODE_CODEC_PACKAGE_ROOT_REQUIRED")
    package_root=str(pathlib.Path(package_root).resolve())
    root_selector=str(args.get("root_selector") or "module")
    encode_export=str(args.get("encode_export") or "")
    decode_export=str(args.get("decode_export") or "")
    if root_selector not in {"module","default"} or not encode_export or not decode_export:
        raise RuntimeError("NODE_CODEC_CONTRACT_INCOMPLETE")
    mode=str(args.get("mode") or "encode")
    json_path=_safe(root,args.get("json_path",""))
    if not json_path.is_file():
        raise RuntimeError("NODE_CODEC_JSON_SOURCE_MISSING")
    if mode=="decode_verify":
        binary_path=_safe(root,args.get("binary_path",""))
        if not binary_path.is_file():
            raise RuntimeError("NODE_CODEC_BINARY_MISSING")
        observed=_run_node(root,{
          "mode":"decode","package_root":package_root,"root_selector":root_selector,
          "decode_export":decode_export,"binary_path":str(binary_path)
        })
        expected=json.loads(json_path.read_text(encoding="utf-8"))
        value=observed.get("observed")
        return {
          "adapter":"node_library_codec","mode":"decode_verify",
          "verified":value==expected,"record_count":len(expected) if isinstance(expected,list) else None,
          "source_path":str(json_path.relative_to(root)),
          "binary_path":str(binary_path.relative_to(root)),
          "decode_export":decode_export
        }
    if mode!="encode":
        raise RuntimeError("NODE_CODEC_MODE_UNSUPPORTED:"+mode)
    output=_safe(root,args.get("output_path",""))
    output.parent.mkdir(parents=True,exist_ok=True)
    encoded=_run_node(root,{
      "mode":"encode","package_root":package_root,"root_selector":root_selector,
      "encode_export":encode_export,"json_path":str(json_path),"output_path":str(output)
    })
    if not output.is_file() or output.stat().st_size<=0:
        raise RuntimeError("NODE_CODEC_OUTPUT_MISSING")
    # Output verification uses a second fresh Node process.
    observed=_run_node(root,{
      "mode":"decode","package_root":package_root,"root_selector":root_selector,
      "decode_export":decode_export,"binary_path":str(output)
    })
    expected=json.loads(json_path.read_text(encoding="utf-8"))
    raw=output.read_bytes()
    return {
      "adapter":"node_library_codec","output_verified":observed.get("observed")==expected,
      "source_path":str(json_path.relative_to(root)),
      "output_path":str(output.relative_to(root)),
      "output_sha256":hashlib.sha256(raw).hexdigest(),
      "output_bytes":len(raw),
      "encode_export":encode_export,"decode_export":decode_export
    }

#!/usr/bin/env python3
from __future__ import annotations
import hashlib,importlib,json,pathlib


def _safe_path(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p!=root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _resolve_callable(module,name):
    current=module
    for part in str(name or "").split("."):
        if not part or not hasattr(current,part):
            raise RuntimeError("PYTHON_CODEC_CALLABLE_MISSING:"+str(name))
        current=getattr(current,part)
    if not callable(current):
        raise RuntimeError("PYTHON_CODEC_CALLABLE_NOT_CALLABLE:"+str(name))
    return current


def run(args,root):
    module_name=str(args.get("module") or "").strip()
    mode=str(args.get("mode") or "encode").strip().lower()
    if not module_name:
        raise RuntimeError("PYTHON_CODEC_CONTRACT_INCOMPLETE")
    if mode=="decode_verify":
        decode_name=str(args.get("decode_callable") or "").strip()
        if not decode_name:
            raise RuntimeError("PYTHON_CODEC_DECODE_CALLABLE_REQUIRED")
        src=_safe_path(root,args.get("json_path"))
        binary=_safe_path(root,args.get("binary_path"))
        if not src.is_file() or not binary.is_file():
            raise RuntimeError("PYTHON_CODEC_VERIFY_INPUT_MISSING")
        expected=json.loads(src.read_text(encoding="utf-8"))
        module=importlib.import_module(module_name)
        fn=_resolve_callable(module,decode_name)
        kwargs=args.get("decode_kwargs") or {}
        if not isinstance(kwargs,dict):
            raise RuntimeError("PYTHON_CODEC_DECODE_KWARGS_INVALID")
        observed=fn(binary.read_bytes(),**kwargs)
        envelope_key=args.get("envelope_key")
        if envelope_key is not None:
            key=str(envelope_key)
            if not isinstance(observed,dict) or key not in observed:
                raise RuntimeError("PYTHON_CODEC_ENVELOPE_MISSING:"+key)
            observed=observed[key]
        return {
          "adapter":"python_library_codec",
          "mode":"decode_verify",
          "module":module_name,
          "decode_callable":decode_name,
          "source_path":str(src.relative_to(pathlib.Path(root).resolve())),
          "binary_path":str(binary.relative_to(pathlib.Path(root).resolve())),
          "verified":observed==expected,
          "record_count":len(observed) if isinstance(observed,list) else None,
        }
    if mode!="encode":
        raise RuntimeError("PYTHON_CODEC_MODE_UNSUPPORTED:"+mode)
    encode_name=str(args.get("encode_callable") or "").strip()
    if not encode_name:
        raise RuntimeError("PYTHON_CODEC_ENCODE_CALLABLE_REQUIRED")
    src=_safe_path(root,args.get("json_path"))
    out=_safe_path(root,args.get("output_path"))
    if not src.is_file():
        raise RuntimeError("PYTHON_CODEC_SOURCE_JSON_MISSING")
    payload=json.loads(src.read_text(encoding="utf-8"))
    envelope_key=args.get("envelope_key")
    if envelope_key is not None:
        payload={str(envelope_key):payload}
    module=importlib.import_module(module_name)
    fn=_resolve_callable(module,encode_name)
    kwargs=args.get("encode_kwargs") or {}
    if not isinstance(kwargs,dict):
        raise RuntimeError("PYTHON_CODEC_KWARGS_INVALID")
    encoded=fn(payload,**kwargs)
    if isinstance(encoded,memoryview):
        encoded=encoded.tobytes()
    if isinstance(encoded,bytearray):
        encoded=bytes(encoded)
    if not isinstance(encoded,bytes) or not encoded:
        raise RuntimeError("PYTHON_CODEC_OUTPUT_NOT_BYTES")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(encoded)
    raw=out.read_bytes()
    return {
      "adapter":"python_library_codec",
      "module":module_name,
      "encode_callable":encode_name,
      "source_path":str(src.relative_to(pathlib.Path(root).resolve())),
      "output_path":str(out.relative_to(pathlib.Path(root).resolve())),
      "output_sha256":hashlib.sha256(raw).hexdigest(),
      "output_bytes":len(raw),
      "output_verified":raw==encoded and len(raw)>0,
    }

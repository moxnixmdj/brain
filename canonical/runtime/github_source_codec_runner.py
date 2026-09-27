#!/usr/bin/env python3
from __future__ import annotations
import importlib, json, pathlib, sys

def _resolve(module,name):
    cur=module
    for part in str(name or "").split("."):
        cur=getattr(cur,part)
    if not callable(cur):
        raise RuntimeError("SOURCE_CODEC_CALLABLE_INVALID:"+str(name))
    return cur

def _norm(v):
    if isinstance(v,bytes):
        try: return v.decode("utf-8")
        except Exception: return {"__bytes_hex__":v.hex()}
    if isinstance(v,list): return [_norm(x) for x in v]
    if isinstance(v,tuple): return [_norm(x) for x in v]
    if isinstance(v,dict): return {_norm(k):_norm(x) for k,x in v.items()}
    return v

def main():
    cfg=json.loads(sys.stdin.read())
    root=pathlib.Path(cfg["source_root"]).resolve()
    if not root.is_dir(): raise RuntimeError("SOURCE_ROOT_MISSING")
    sys.path.insert(0,str(root))
    mode=str(cfg.get("mode") or "probe")
    modules=cfg.get("modules") or []
    if mode=="probe":
        fixture=cfg.get("fixture")
        pairs=[("encode","decode"),("dumps","loads"),("serialize","deserialize"),("pack","unpack")]
        attempts=[]
        for module_name in modules:
            try:
                module=importlib.import_module(module_name)
            except Exception as exc:
                attempts.append({"module":module_name,"status":"IMPORT_FAILED","error":type(exc).__name__})
                continue
            for enc_name,dec_name in pairs:
                try:
                    enc=_resolve(module,enc_name); dec=_resolve(module,dec_name)
                except Exception:
                    continue
                try:
                    payload=enc(fixture)
                    if isinstance(payload,memoryview): payload=payload.tobytes()
                    if isinstance(payload,bytearray): payload=bytes(payload)
                    if isinstance(payload,str): payload=payload.encode("utf-8")
                    if not isinstance(payload,bytes) or not payload: continue
                    observed=_norm(dec(payload))
                except Exception as exc:
                    attempts.append({"module":module_name,"encode":enc_name,"decode":dec_name,"status":"ROUNDTRIP_ERROR","error":type(exc).__name__})
                    continue
                if observed==_norm(fixture):
                    print(json.dumps({"ok":True,"module":module_name,"encode_callable":enc_name,"decode_callable":dec_name,"probe_output_bytes":len(payload)}))
                    return
        print(json.dumps({"ok":False,"attempts":attempts[:80]}))
        return
    module=importlib.import_module(str(cfg["module"]))
    enc=_resolve(module,cfg.get("encode_callable")) if cfg.get("encode_callable") else None
    dec=_resolve(module,cfg.get("decode_callable")) if cfg.get("decode_callable") else None
    if mode=="encode":
        source=json.loads(pathlib.Path(cfg["json_path"]).read_text(encoding="utf-8"))
        envelope_key=cfg.get("envelope_key")
        if envelope_key is not None:
            source={str(envelope_key):source}
        kwargs=cfg.get("encode_kwargs") or {}
        if not isinstance(kwargs,dict): raise RuntimeError("SOURCE_CODEC_ENCODE_KWARGS_INVALID")
        payload=enc(source,**kwargs)
        if isinstance(payload,memoryview): payload=payload.tobytes()
        if isinstance(payload,bytearray): payload=bytes(payload)
        if isinstance(payload,str): payload=payload.encode("utf-8")
        if not isinstance(payload,bytes) or not payload: raise RuntimeError("SOURCE_CODEC_OUTPUT_NOT_BYTES")
        pathlib.Path(cfg["output_path"]).write_bytes(payload)
        print(json.dumps({"ok":True,"bytes":len(payload)})); return
    if mode=="decode":
        kwargs=cfg.get("decode_kwargs") or {}
        if not isinstance(kwargs,dict): raise RuntimeError("SOURCE_CODEC_DECODE_KWARGS_INVALID")
        observed=_norm(dec(pathlib.Path(cfg["binary_path"]).read_bytes(),**kwargs))
        envelope_key=cfg.get("envelope_key")
        if envelope_key is not None:
            key=str(envelope_key)
            if not isinstance(observed,dict) or key not in observed:
                raise RuntimeError("SOURCE_CODEC_ENVELOPE_MISSING:"+key)
            observed=observed[key]
        print(json.dumps({"ok":True,"observed":observed})); return
    raise RuntimeError("SOURCE_CODEC_MODE_UNSUPPORTED:"+mode)

if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""Bounded semantic discovery and round-trip probing for Python byte codecs."""
from __future__ import annotations
import hashlib, importlib, json, pathlib, re, sys

FIXTURE=[{"id":1,"text":"alpha"},{"id":2,"text":"beta"}]
ENVELOPE_KEY="__project_brain_payload__"
REPRESENTATIONS=[
    ("direct",FIXTURE,None),
    ("mapping_envelope",{ENVELOPE_KEY:FIXTURE},ENVELOPE_KEY),
]

_PRODUCER_PREFIXES=("encode","dump","pack","serial","to_bytes","tobytes")
_CONSUMER_PREFIXES=("decode","load","unpack","deserial","from_bytes","frombytes")
_BASELINE_PAIRS=(
    ("packb","unpackb"),
    ("dumps","loads"),
    ("encode","decode"),
    ("serialize","deserialize"),
)

def _public_callable_names(module):
    out=[]
    for name in dir(module):
        if name.startswith("_"):
            continue
        try:
            value=getattr(module,name)
        except Exception:
            continue
        if callable(value):
            out.append(name)
    return sorted(set(out))[:96]

def _role(name,prefixes):
    low=str(name).lower()
    return next((p for p in prefixes if low.startswith(p)),None)

def _suffix(name,prefix):
    return re.sub(r"[^a-z0-9]+","",str(name).lower()[len(prefix):])

def discover_pairs(module):
    names=_public_callable_names(module)
    producers=[]
    consumers=[]
    for name in names:
        p=_role(name,_PRODUCER_PREFIXES)
        if p:
            producers.append((name,p,_suffix(name,p)))
        c=_role(name,_CONSUMER_PREFIXES)
        if c:
            consumers.append((name,c,_suffix(name,c)))

    ranked=[]
    seen=set()
    for pair in _BASELINE_PAIRS:
        if pair[0] in names and pair[1] in names:
            ranked.append((0,pair[0],pair[1]))
            seen.add(pair)

    complementary={
        "encode":"decode","dump":"load","pack":"unpack","serial":"deserial",
        "to_bytes":"from_bytes","tobytes":"frombytes",
    }
    for enc,ep,es in producers:
        for dec,dp,ds in consumers:
            pair=(enc,dec)
            if pair in seen:
                continue
            score=10
            if complementary.get(ep)==dp:
                score-=5
            if es==ds:
                score-=3
            if es and ds and (es.endswith(ds) or ds.endswith(es)):
                score-=1
            ranked.append((score,enc,dec))
            seen.add(pair)

    ranked.sort(key=lambda x:(x[0],x[1],x[2]))
    return [(enc,dec) for _,enc,dec in ranked[:64]]

def _resolve(module,name):
    current=module
    for part in str(name).split("."):
        current=getattr(current,part)
    if not callable(current):
        raise TypeError(name)
    return current

def probe_modules(site,modules):
    site=pathlib.Path(site).resolve()
    sys.path.insert(0,str(site))
    attempts=[]
    for module_name in modules:
        try:
            module=importlib.import_module(module_name)
        except Exception as exc:
            attempts.append({"module":module_name,"status":"IMPORT_FAILED","error":type(exc).__name__+":"+str(exc)})
            continue
        pairs=discover_pairs(module)
        if not pairs:
            attempts.append({"module":module_name,"status":"NO_SEMANTIC_CODEC_CALLABLE_PAIRS"})
            continue
        for enc_name,dec_name in pairs:
            try:
                enc=_resolve(module,enc_name); dec=_resolve(module,dec_name)
            except Exception:
                continue
            for representation,probe_value,unwrap_key in REPRESENTATIONS:
                for enc_kwargs in ({},{"use_bin_type":True}):
                    try:
                        payload=enc(probe_value,**enc_kwargs)
                    except Exception:
                        continue
                    if isinstance(payload,memoryview): payload=payload.tobytes()
                    if isinstance(payload,bytearray): payload=bytes(payload)
                    if not isinstance(payload,bytes) or not payload:
                        continue
                    for dec_kwargs in ({},{"raw":False}):
                        try:
                            observed=dec(payload,**dec_kwargs)
                        except Exception:
                            continue
                        semantic=observed
                        if unwrap_key is not None:
                            if not isinstance(observed,dict) or unwrap_key not in observed:
                                continue
                            semantic=observed[unwrap_key]
                        if semantic==FIXTURE:
                            return {
                                "ok":True,
                                "module":module_name,
                                "encode_callable":enc_name,
                                "decode_callable":dec_name,
                                "encode_kwargs":enc_kwargs,
                                "decode_kwargs":dec_kwargs,
                                "fixture":FIXTURE,
                                "representation":representation,
                                "envelope_key":unwrap_key,
                                "probe_output_sha256":hashlib.sha256(payload).hexdigest(),
                                "probe_output_bytes":len(payload),
                                "pair_discovery":"bounded_public_semantic_callables",
                            }
            attempts.append({"module":module_name,"encode":enc_name,"decode":dec_name,"status":"ROUNDTRIP_REJECTED"})
    return {"ok":False,"attempts":attempts}

def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if len(argv)!=2:
        print(json.dumps({"ok":False,"error":"USAGE"}))
        return 2
    result=probe_modules(argv[0],json.loads(argv[1]))
    print(json.dumps(result,sort_keys=True))
    return 0 if result.get("ok") is True else 3

if __name__=="__main__":
    raise SystemExit(main())

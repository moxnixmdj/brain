#!/usr/bin/env python3
"""Fetch JSON over HTTPS from a URL named inside repository-local structured state."""
from __future__ import annotations
import hashlib,json,pathlib,urllib.parse,urllib.request

def _safe(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p!=root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def _find_key(value,key,path=()):
    hits=[]
    if isinstance(value,dict):
        for k,v in value.items():
            p=path+(str(k),)
            if str(k)==key and isinstance(v,str):
                hits.append((p,v))
            hits.extend(_find_key(v,key,p))
    elif isinstance(value,list):
        for i,v in enumerate(value):
            hits.extend(_find_key(v,key,path+(str(i),)))
    return hits

def run(args, root):
    root=pathlib.Path(root).resolve()
    src=_safe(root,args.get("source_json_path"))
    out=_safe(root,args.get("output_path"))
    key=str(args.get("url_key") or "").strip()
    if not src.is_file() or src.suffix.lower()!=".json":
        raise RuntimeError("SOURCE_JSON_REQUIRED")
    if not key:
        raise RuntimeError("URL_KEY_REQUIRED")
    data=json.loads(src.read_text(encoding="utf-8"))
    hits=_find_key(data,key)
    if len(hits)!=1:
        raise RuntimeError("URL_KEY_NOT_UNIQUE:"+str(len(hits)))
    field_path,url=hits[0]
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise RuntimeError("HTTPS_URL_REQUIRED")
    if parsed.hostname.lower() in {"localhost","localhost.localdomain"}:
        raise RuntimeError("LOCALHOST_URL_REJECTED")
    req=urllib.request.Request(url,headers={
      "User-Agent":"ProjectBrain-VerifiedHTTPJSON/1",
      "Accept":"application/json",
    })
    max_bytes=max(1024,min(int(args.get("max_bytes",5000000)),12000000))
    with urllib.request.urlopen(req,timeout=max(1,min(int(args.get("timeout_s",30)),60))) as resp:
        if getattr(resp,"status",200)!=200:
            raise RuntimeError("HTTP_STATUS:"+str(getattr(resp,"status",None)))
        raw=resp.read(max_bytes+1)
        final_url=resp.geturl()
        content_type=str(resp.headers.get("Content-Type") or "")
    if len(raw)>max_bytes:
        raise RuntimeError("HTTP_BODY_TOO_LARGE")
    # Parsing is the semantic gate. Preserve exact fetched bytes for later
    # independent hash/provenance checks instead of reserializing JSON.
    parsed_json=json.loads(raw.decode("utf-8"))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(raw)
    return {
      "adapter":"http_json_fetch",
      "source_json_path":str(src.relative_to(root)),
      "url_key":key,
      "url_field_path":list(field_path),
      "requested_url":url,
      "final_url":final_url,
      "status":200,
      "content_type":content_type,
      "output_path":str(out.relative_to(root)),
      "output_bytes":len(raw),
      "output_sha256":hashlib.sha256(raw).hexdigest(),
      "json_top_level_type":type(parsed_json).__name__,
      "output_verified":True,
    }

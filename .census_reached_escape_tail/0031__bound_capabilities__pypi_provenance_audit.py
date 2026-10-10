#!/usr/bin/env python3
"""Verify a pinned PyPI artifact against live metadata and downloaded bytes."""
from __future__ import annotations
import hashlib,json,pathlib,urllib.parse,urllib.request

def _safe(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p!=root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def _https(url):
    p=urllib.parse.urlsplit(str(url or ""))
    if p.scheme!="https" or not p.hostname or p.username or p.password or p.fragment:
        raise RuntimeError("HTTPS_URL_REQUIRED")
    return str(url)

def run(args, root):
    root=pathlib.Path(root).resolve()
    selection_path=_safe(root,args.get("selection_path"))
    metadata_path=_safe(root,args.get("metadata_path"))
    report_path=_safe(root,args.get("report_path"))
    if not selection_path.is_file() or not metadata_path.is_file():
        raise RuntimeError("PROVENANCE_INPUT_MISSING")
    selection=json.loads(selection_path.read_text(encoding="utf-8"))
    cid=str(selection.get("id") or "")
    record=selection.get("record") or {}
    source=record.get("source") or {}
    if source.get("type")!="pypi":
        raise RuntimeError("PYPI_SOURCE_REQUIRED")
    project=str(source.get("project") or "")
    pinned_version=str(source.get("version") or "")
    wheel_filename=str(source.get("wheel_filename") or "")
    recorded_hash=str(source.get("wheel_sha256") or "").lower()
    metadata_url=_https(source.get("metadata_url"))
    if not all((cid,project,pinned_version,wheel_filename)) or len(recorded_hash)!=64:
        raise RuntimeError("PYPI_SOURCE_METADATA_INCOMPLETE")

    metadata_raw=metadata_path.read_bytes()
    metadata=json.loads(metadata_raw.decode("utf-8"))
    info=metadata.get("info") or {}
    if str(info.get("name") or "").lower()!=project.lower():
        raise RuntimeError("PYPI_PROJECT_MISMATCH")
    if str(info.get("version") or "")!=pinned_version:
        raise RuntimeError("PYPI_PINNED_VERSION_NOT_LIVE")
    matches=[x for x in metadata.get("urls",[]) if x.get("filename")==wheel_filename]
    if len(matches)!=1:
        raise RuntimeError("PYPI_WHEEL_NOT_UNIQUE:"+str(len(matches)))
    artifact=matches[0]
    artifact_url=_https(artifact.get("url"))
    live_metadata_hash=str((artifact.get("digests") or {}).get("sha256") or "").lower()
    if len(live_metadata_hash)!=64:
        raise RuntimeError("PYPI_LIVE_DIGEST_MISSING")

    req=urllib.request.Request(artifact_url,headers={"User-Agent":"ProjectBrain-PyPIProvenance/1"})
    max_bytes=max(1024,min(int(args.get("max_bytes",20000000)),50000000))
    with urllib.request.urlopen(req,timeout=max(1,min(int(args.get("timeout_s",60)),120))) as resp:
        raw=resp.read(max_bytes+1)
    if len(raw)>max_bytes:
        raise RuntimeError("PYPI_ARTIFACT_TOO_LARGE")
    downloaded_hash=hashlib.sha256(raw).hexdigest()
    verified=(recorded_hash==live_metadata_hash==downloaded_hash)

    report={
      "schema":"PROJECT_BRAIN_PYPI_PROVENANCE_AUDIT_V1",
      "capability_id":cid,
      "project":project,
      "pinned_version":pinned_version,
      "wheel_filename":wheel_filename,
      "recorded_hash":recorded_hash,
      "live_metadata_hash":live_metadata_hash,
      "downloaded_artifact_hash":downloaded_hash,
      "metadata_response_hash":hashlib.sha256(metadata_raw).hexdigest(),
      "metadata_url":metadata_url,
      "artifact_url":artifact_url,
      "artifact_bytes":len(raw),
      "verified":verified,
    }
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return {
      "adapter":"pypi_provenance_audit",
      "report_path":str(report_path.relative_to(root)),
      "capability_id":cid,
      "project":project,
      "recorded_hash":recorded_hash,
      "live_metadata_hash":live_metadata_hash,
      "downloaded_artifact_hash":downloaded_hash,
      "artifact_bytes":len(raw),
      "verified":verified,
    }

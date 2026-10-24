#!/usr/bin/env python3
"""Create a repository-local tar.gz bundle from a JSON manifest using Python stdlib."""
from __future__ import annotations
import hashlib,json,pathlib,tarfile

def _safe(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p!=root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def _manifest_paths(manifest):
    """The repository paths a manifest lists, in manifest order.

    A manifest whose top level is not a mapping -- a bare JSON array, which is a
    perfectly ordinary thing to write and what a caller reaches for first -- used
    to die here with ``AttributeError: 'list' object has no attribute 'get'``.  The
    adapter validated its input PATHS carefully (MANIFEST_INPUT_REQUIRED,
    TAR_GZ_OUTPUT_REQUIRED) but never their STRUCTURE, so a wrong-shaped manifest
    escaped as an uncaught Python traceback and surfaced one layer up as an opaque
    LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE.  It now fails closed with a
    named contract error like every other rejection in this file.  ``records``
    absent or null stays legal and yields no paths, exactly as before.
    """
    if not isinstance(manifest,dict):
        raise RuntimeError("MANIFEST_RECORDS_REQUIRED")
    records=manifest.get("records")
    if records is None:
        return []
    if not isinstance(records,list):
        raise RuntimeError("MANIFEST_RECORDS_REQUIRED")
    out=[]
    for rec in records:
        if not isinstance(rec,dict):
            raise RuntimeError("MANIFEST_RECORDS_REQUIRED")
        for p in rec.get("verification_paths") or []:
            if isinstance(p,str) and p.startswith("canonical/") and p not in out:
                out.append(p)
    return out

def run(args, root):
    root=pathlib.Path(root).resolve()
    manifest_path=_safe(root,args.get("manifest_path"))
    output_path=_safe(root,args.get("output_path"))
    if not manifest_path.is_file() or manifest_path.suffix.lower()!=".json":
        raise RuntimeError("MANIFEST_INPUT_REQUIRED")
    if not str(output_path).endswith(".tar.gz"):
        raise RuntimeError("TAR_GZ_OUTPUT_REQUIRED")
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    members=[str(manifest_path.relative_to(root))]+_manifest_paths(manifest)
    if len(set(members))!=len(members):
        raise RuntimeError("ARCHIVE_MEMBER_DUPLICATE")
    source_hashes={}
    for rel in members:
        p=_safe(root,rel)
        if not p.is_file():
            raise RuntimeError("ARCHIVE_MEMBER_SOURCE_MISSING:"+rel)
        source_hashes[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    output_path.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(output_path,"w:gz") as tf:
        for rel in sorted(members):
            tf.add(_safe(root,rel),arcname=rel,recursive=False)
    raw=output_path.read_bytes()
    return {
      "adapter":"archive_tarfile",
      "output_path":str(output_path.relative_to(root)),
      "output_bytes":len(raw),
      "output_sha256":hashlib.sha256(raw).hexdigest(),
      "member_count":len(members),
      "members":sorted(members),
      "source_sha256":source_hashes,
      "output_verified":True,
    }

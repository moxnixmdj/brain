#!/usr/bin/env python3
"""Independently verify a tar.gz bundle with GNU tar plus source SHA-256 comparison."""
from __future__ import annotations
import hashlib,json,pathlib,subprocess,tempfile

def _safe(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p!=root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def _manifest_paths(manifest):
    out=[]
    for rec in manifest.get("records") or []:
        for p in rec.get("verification_paths") or []:
            if isinstance(p,str) and p.startswith("canonical/") and p not in out:
                out.append(p)
    return out

def run(args, root):
    root=pathlib.Path(root).resolve()
    manifest_path=_safe(root,args.get("manifest_path"))
    archive_path=_safe(root,args.get("archive_path"))
    if not manifest_path.is_file():
        raise RuntimeError("MANIFEST_INPUT_REQUIRED")
    if not archive_path.is_file():
        raise RuntimeError("ARCHIVE_INPUT_REQUIRED")
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    expected=[str(manifest_path.relative_to(root))]+_manifest_paths(manifest)
    expected=sorted(expected)
    listing=subprocess.run(["tar","-tzf",str(archive_path)],text=True,capture_output=True,timeout=60)
    if listing.returncode!=0:
        raise RuntimeError("GNU_TAR_LIST_FAILED:"+listing.stderr[-1200:])
    observed=sorted([x.rstrip("/") for x in listing.stdout.splitlines() if x.strip()])
    if observed!=expected:
        raise RuntimeError("ARCHIVE_MEMBER_SET_MISMATCH:"+json.dumps({"expected":expected,"observed":observed},sort_keys=True)[:3000])
    mismatches=[]
    with tempfile.TemporaryDirectory() as td:
        extract=subprocess.run(["tar","-xzf",str(archive_path),"-C",td],text=True,capture_output=True,timeout=60)
        if extract.returncode!=0:
            raise RuntimeError("GNU_TAR_EXTRACT_FAILED:"+extract.stderr[-1200:])
        base=pathlib.Path(td)
        for rel in expected:
            src=_safe(root,rel)
            ext=(base/rel).resolve()
            if base.resolve() not in ext.parents:
                raise RuntimeError("EXTRACT_PATH_OUTSIDE_TEMP")
            if not ext.is_file():
                mismatches.append({"path":rel,"reason":"missing_extracted"})
                continue
            a=hashlib.sha256(src.read_bytes()).hexdigest()
            b=hashlib.sha256(ext.read_bytes()).hexdigest()
            if a!=b:
                mismatches.append({"path":rel,"source_sha256":a,"archive_sha256":b})
    if mismatches:
        raise RuntimeError("ARCHIVE_HASH_MISMATCH:"+json.dumps(mismatches,sort_keys=True)[:3000])
    return {
      "adapter":"archive_verify_gnu_tar",
      "verified":True,
      "member_count":len(expected),
      "members":expected,
      "archive_path":str(archive_path.relative_to(root)),
      "manifest_path":str(manifest_path.relative_to(root)),
    }

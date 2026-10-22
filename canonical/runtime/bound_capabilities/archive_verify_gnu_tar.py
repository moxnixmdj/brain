#!/usr/bin/env python3
"""Independently verify a tar.gz bundle with GNU tar plus source SHA-256 comparison."""
from __future__ import annotations
import hashlib,json,pathlib,subprocess,tarfile

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
    try:
        with tarfile.open(archive_path,"r:gz") as tf:
            py_members={m.name.rstrip("/"):m for m in tf.getmembers() if m.name.strip()}
            if sorted(py_members)!=expected:
                raise RuntimeError("PY_TAR_MEMBER_SET_MISMATCH")
            for rel in expected:
                src=_safe(root,rel)
                member=py_members.get(rel)
                if member is None or not member.isfile() or member.issym() or member.islnk():
                    mismatches.append({"path":rel,"reason":"non_regular_or_missing_archive_member"})
                    continue
                fh=tf.extractfile(member)
                if fh is None:
                    mismatches.append({"path":rel,"reason":"archive_member_unreadable"})
                    continue
                data=fh.read()
                a=hashlib.sha256(src.read_bytes()).hexdigest()
                b=hashlib.sha256(data).hexdigest()
                if a!=b:
                    mismatches.append({"path":rel,"source_sha256":a,"archive_sha256":b})
    except (tarfile.TarError,OSError) as exc:
        raise RuntimeError("PY_TAR_READ_FAILED:"+type(exc).__name__) from exc
    if mismatches:
        raise RuntimeError("ARCHIVE_HASH_MISMATCH:"+json.dumps(mismatches,sort_keys=True)[:3000])
    return {
      "adapter":"archive_verify_gnu_tar",
      "verified":True,
      "member_count":len(expected),
      "members":expected,
      "archive_path":str(archive_path.relative_to(root)),
      # The digest of the archive this capability just verified, from its real
      # bytes. Without it the success had no durable artifact anyone could
      # re-hash, so it could never become verified experience even though the
      # members had all been checked one by one above.
      "archive_sha256":hashlib.sha256(archive_path.read_bytes()).hexdigest(),
      "manifest_path":str(manifest_path.relative_to(root)),
      "manifest_sha256":hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }

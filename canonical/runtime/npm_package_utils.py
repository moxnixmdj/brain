#!/usr/bin/env python3
"""Safe npm registry artifact verification and materialization helpers."""
from __future__ import annotations
import base64,hashlib,io,json,pathlib,re,tarfile,urllib.parse,urllib.request


class NpmPackageFailure(RuntimeError):
    pass


def _inside(base,child):
    base=pathlib.Path(base).resolve()
    child=pathlib.Path(child).resolve()
    if child!=base and base not in child.parents:
        raise NpmPackageFailure("NPM_ARCHIVE_PATH_ESCAPE")
    return child


def fetch_version_metadata(package,version,timeout_s=20):
    package=str(package or "").strip()
    version=str(version or "").strip()
    if not package or not version:
        raise NpmPackageFailure("NPM_PACKAGE_IDENTITY_REQUIRED")
    encoded=urllib.parse.quote(package,safe="")
    url="https://registry.npmjs.org/"+encoded+"/"+urllib.parse.quote(version,safe="")
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-NpmAcquisition/1"})
    try:
        with urllib.request.urlopen(req,timeout=timeout_s) as resp:
            raw=resp.read(4_000_000)
        payload=json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise NpmPackageFailure("NPM_METADATA_FETCH_FAILED:"+type(exc).__name__+":"+str(exc)) from exc
    if str(payload.get("name") or "")!=package or str(payload.get("version") or "")!=version:
        raise NpmPackageFailure("NPM_METADATA_IDENTITY_MISMATCH")
    return url,payload


def verify_integrity(raw,integrity):
    tokens=[x for x in str(integrity or "").split() if "-" in x]
    strong=[]
    for token in tokens:
        alg,b64=token.split("-",1)
        if alg in {"sha512","sha384","sha256"}:
            strong.append((alg,b64))
    if not strong:
        raise NpmPackageFailure("NPM_STRONG_INTEGRITY_REQUIRED")
    order={"sha512":3,"sha384":2,"sha256":1}
    alg,b64=max(strong,key=lambda x:order[x[0]])
    try:
        expected=base64.b64decode(b64,validate=True)
    except Exception as exc:
        raise NpmPackageFailure("NPM_INTEGRITY_BASE64_INVALID") from exc
    actual=hashlib.new(alg,raw).digest()
    if actual!=expected:
        raise NpmPackageFailure("NPM_TARBALL_INTEGRITY_MISMATCH")
    return {
      "algorithm":alg,
      "digest_hex":actual.hex(),
      "integrity":alg+"-"+base64.b64encode(actual).decode("ascii"),
    }


def fetch_verified_tarball(package,version,tarball_url,integrity,timeout_s=30,max_bytes=30_000_000):
    metadata_url,meta=fetch_version_metadata(package,version,timeout_s=timeout_s)
    dist=meta.get("dist") or {}
    official_url=str(dist.get("tarball") or "")
    official_integrity=str(dist.get("integrity") or "")
    if official_url!=str(tarball_url or "") or not official_url.startswith("https://"):
        raise NpmPackageFailure("NPM_TARBALL_URL_MISMATCH")
    if official_integrity!=str(integrity or ""):
        raise NpmPackageFailure("NPM_TARBALL_INTEGRITY_METADATA_MISMATCH")
    req=urllib.request.Request(official_url,headers={"User-Agent":"ProjectBrain-NpmAcquisition/1"})
    try:
        with urllib.request.urlopen(req,timeout=timeout_s) as resp:
            raw=resp.read(max_bytes+1)
    except Exception as exc:
        raise NpmPackageFailure("NPM_TARBALL_DOWNLOAD_FAILED:"+type(exc).__name__+":"+str(exc)) from exc
    if len(raw)>max_bytes:
        raise NpmPackageFailure("NPM_TARBALL_TOO_LARGE")
    verified=verify_integrity(raw,official_integrity)
    return {
      "raw":raw,
      "metadata":meta,
      "metadata_url":metadata_url,
      "tarball_url":official_url,
      **verified,
      "bytes":len(raw),
    }


def safe_extract_package(raw,destination,max_files=6000,max_unpacked_bytes=80_000_000):
    destination=pathlib.Path(destination).resolve()
    destination.mkdir(parents=True,exist_ok=True)
    count=0
    total=0
    try:
        tf=tarfile.open(fileobj=io.BytesIO(raw),mode="r:gz")
    except Exception as exc:
        raise NpmPackageFailure("NPM_TARBALL_INVALID:"+type(exc).__name__) from exc
    with tf:
        for member in tf.getmembers():
            name=str(member.name or "").replace("\\","/")
            if not name.startswith("package/"):
                continue
            rel=name[len("package/"):]
            if not rel:
                continue
            if member.issym() or member.islnk() or member.isdev():
                raise NpmPackageFailure("NPM_TARBALL_UNSAFE_MEMBER:"+name)
            if pathlib.PurePosixPath(rel).is_absolute() or ".." in pathlib.PurePosixPath(rel).parts:
                raise NpmPackageFailure("NPM_TARBALL_PATH_TRAVERSAL:"+name)
            count+=1
            if count>max_files:
                raise NpmPackageFailure("NPM_TARBALL_FILE_LIMIT")
            if member.isfile():
                total+=int(member.size or 0)
                if total>max_unpacked_bytes:
                    raise NpmPackageFailure("NPM_TARBALL_UNPACKED_BYTES_LIMIT")
            target=_inside(destination,destination/rel)
            if member.isdir():
                target.mkdir(parents=True,exist_ok=True)
                continue
            if not member.isfile():
                continue
            target.parent.mkdir(parents=True,exist_ok=True)
            src=tf.extractfile(member)
            if src is None:
                raise NpmPackageFailure("NPM_TARBALL_MEMBER_UNREADABLE:"+name)
            target.write_bytes(src.read())
    package_json=destination/"package.json"
    if not package_json.is_file():
        raise NpmPackageFailure("NPM_PACKAGE_JSON_MISSING")
    return {
      "package_root":str(destination),
      "file_count":count,
      "unpacked_bytes":total,
      "package_json":json.loads(package_json.read_text(encoding="utf-8")),
    }


def validate_zero_dependency_package(meta):
    dependency_fields=("dependencies","optionalDependencies","peerDependencies")
    for field in dependency_fields:
        deps=meta.get(field) or {}
        if not isinstance(deps,dict):
            raise NpmPackageFailure("NPM_"+field.upper()+"_INVALID")
        if deps:
            raise NpmPackageFailure(
                "NPM_RUNTIME_DEPENDENCIES_UNSUPPORTED:"
                +field+":"+json.dumps(sorted(deps))[:800]
            )
    bundled=meta.get("bundledDependencies")
    if bundled is None:
        bundled=meta.get("bundleDependencies")
    if bundled not in (None,[],{}):
        raise NpmPackageFailure("NPM_BUNDLED_DEPENDENCIES_UNSUPPORTED")
    scripts=meta.get("scripts") or {}
    if not isinstance(scripts,dict):
        scripts={}
    forbidden=[k for k in ("preinstall","install","postinstall") if str(scripts.get(k) or "").strip()]
    if forbidden:
        raise NpmPackageFailure("NPM_LIFECYCLE_SCRIPTS_REJECTED:"+",".join(forbidden))
    return {
      "dependency_count":0,
      "lifecycle_scripts_rejected":False,
    }


def cache_key(package,version,integrity):
    raw=(str(package)+"\n"+str(version)+"\n"+str(integrity)).encode("utf-8")
    slug=re.sub(r"[^A-Za-z0-9_.-]+","_",str(package)).strip("_") or "package"
    return slug+"__"+str(version)+"__"+hashlib.sha256(raw).hexdigest()[:16]

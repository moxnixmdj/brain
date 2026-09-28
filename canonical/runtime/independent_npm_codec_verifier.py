#!/usr/bin/env python3
"""Acquire and execute a producer-independent npm codec verifier."""
from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import re
import subprocess
import tempfile

import auto_npm_library_acquisition as npm_acq
import astra_runtime
import npm_package_utils


class IndependentNpmCodecVerifierFailure(RuntimeError):
    pass


def _norm(value):
    return re.sub(r"[-_.@/]+","-",str(value or "").strip()).strip("-").lower()


def _format_search_hints(fmt):
    aliases={
        "ubj": ["ubjson", "ubj"],
    }
    raw=aliases.get(str(fmt or "").strip().lower(), [str(fmt or "").strip().lower()])
    out=[]
    for value in raw:
        value=str(value or "").strip().lower()
        if value and value not in out:
            out.append(value)
    return out


def _inside(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw)).resolve()
    if p!=root and root not in p.parents:
        raise IndependentNpmCodecVerifierFailure("PATH_OUTSIDE_REPOSITORY")
    return p


def _metadata_allow_dependencies(raw):
    package=str(raw.get("package") or raw.get("name") or "").strip()
    version=str(raw.get("version") or "").strip()
    if not package or not version:
        raise IndependentNpmCodecVerifierFailure("NPM_VERIFIER_CANDIDATE_IDENTITY_INVALID")
    metadata_url,payload=npm_package_utils.fetch_version_metadata(package,version)
    dist=payload.get("dist") or {}
    tarball=str(dist.get("tarball") or "")
    integrity=str(dist.get("integrity") or "")
    if not tarball.startswith("https://") or not integrity:
        raise IndependentNpmCodecVerifierFailure("NPM_VERIFIER_DIST_METADATA_INCOMPLETE")
    dependencies={}
    for field in ("dependencies","optionalDependencies","peerDependencies"):
        value=payload.get(field) or {}
        if not isinstance(value,dict):
            raise IndependentNpmCodecVerifierFailure("NPM_VERIFIER_DEPENDENCY_METADATA_INVALID:"+field)
        dependencies[field]=value
    bundled=payload.get("bundledDependencies")
    if bundled is None:
        bundled=payload.get("bundleDependencies")
    if bundled not in (None,[],{}):
        raise IndependentNpmCodecVerifierFailure("NPM_VERIFIER_BUNDLED_DEPENDENCIES_UNSUPPORTED")
    dependency_count=sum(len(x) for x in dependencies.values())
    return {
        **raw,
        "package":package,
        "version":version,
        "metadata_url":metadata_url,
        "tarball_url":tarball,
        "integrity":integrity,
        "package_json":payload,
        "runtime_dependencies":dependencies,
        "dependency_count":dependency_count,
    }


def _safe_install_path(site,raw):
    text=str(raw or "").strip().replace("\\","/")
    rel=pathlib.PurePosixPath(text)
    if not text or rel.is_absolute() or ".." in rel.parts:
        raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_INSTALL_PATH_INVALID")
    if not rel.parts or rel.parts[0]!="node_modules":
        raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_INSTALL_PATH_INVALID")
    site=pathlib.Path(site).resolve()
    out=(site/pathlib.Path(*rel.parts)).resolve()
    if site not in out.parents:
        raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_INSTALL_PATH_ESCAPE")
    return out


def _materialize_npm_closure(closure,site,candidate):
    if not isinstance(closure,dict) or closure.get("schema")!="PROJECT_BRAIN_EXTERNAL_NPM_PACKAGE_CLOSURE_V1":
        raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_SCHEMA_INVALID")
    package=str(candidate.get("package") or "")
    version=str(candidate.get("version") or "")
    if closure.get("root_package")!=package or str(closure.get("root_version") or "")!=version:
        raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_ROOT_IDENTITY_MISMATCH")
    rows=closure.get("packages")
    if not isinstance(rows,list) or not rows or len(rows)>32:
        raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_PACKAGE_COUNT_INVALID")
    if int(closure.get("package_count") or -1)!=len(rows):
        raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_PACKAGE_COUNT_MISMATCH")
    site=pathlib.Path(site).resolve()
    site.mkdir(parents=True,exist_ok=True)
    root_record=None
    total=0
    seen=set()
    for row in rows:
        if not isinstance(row,dict):
            raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_RECORD_INVALID")
        install_path=str(row.get("install_path") or "")
        if install_path in seen:
            raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_INSTALL_PATH_DUPLICATE")
        seen.add(install_path)
        try:
            raw=base64.b64decode(str(row.get("content_b64") or ""),validate=True)
        except Exception as exc:
            raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_TARBALL_BASE64_INVALID") from exc
        total+=len(raw)
        if total>80_000_000:
            raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_TOTAL_BYTES_LIMIT")
        if int(row.get("bytes") or -1)!=len(raw):
            raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_TARBALL_BYTES_MISMATCH")
        if hashlib.sha256(raw).hexdigest()!=str(row.get("sha256") or ""):
            raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_TARBALL_SHA256_MISMATCH")
        verified=npm_package_utils.verify_integrity(raw,row.get("integrity"))
        if verified["algorithm"]!=row.get("integrity_algorithm"):
            raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_INTEGRITY_ALGORITHM_MISMATCH")
        if verified["digest_hex"]!=row.get("integrity_digest_hex"):
            raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_INTEGRITY_DIGEST_MISMATCH")
        destination=_safe_install_path(site,install_path)
        extracted=npm_package_utils.safe_extract_package(raw,destination)
        package_json=extracted["package_json"]
        if str(package_json.get("name") or "")!=str(row.get("package") or ""):
            raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_PACKAGE_NAME_MISMATCH")
        if str(package_json.get("version") or "")!=str(row.get("version") or ""):
            raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_PACKAGE_VERSION_MISMATCH")
        if install_path=="node_modules/"+package:
            root_record={**row,"verified":verified}
    if int(closure.get("total_bytes") or -1)!=total:
        raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_TOTAL_BYTES_MISMATCH")
    if root_record is None:
        raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_ROOT_MISSING")
    if root_record["version"]!=version or root_record["integrity"]!=candidate["integrity"]:
        raise IndependentNpmCodecVerifierFailure("NPM_CLOSURE_ROOT_METADATA_MISMATCH")
    return site/pathlib.Path(*pathlib.PurePosixPath("node_modules/"+package).parts),root_record


def verify(format_name,json_path,binary_path,producer_project,root):
    # Independent verification is a fresh subprocess and must explicitly inherit
    # the provider-neutral external-tool transport when its executor has no direct network.
    astra_runtime._activate_external_http_bridge()
    root=pathlib.Path(root).resolve()
    src=_inside(root,json_path)
    binary=_inside(root,binary_path)
    if not src.is_file() or not binary.is_file():
        raise IndependentNpmCodecVerifierFailure("VERIFIER_INPUT_MISSING")

    fmt=str(format_name or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._+-]{0,40}",fmt):
        raise IndependentNpmCodecVerifierFailure("FORMAT_INVALID")

    goal=(
        "Independently decode "+fmt+" binary data from "
        "canonical/astra_runtime/tmp/INDEPENDENT_VERIFIER."+fmt
    )
    candidates=[]
    seen_packages=set()
    discovery_errors=[]
    for hint in _format_search_hints(fmt):
        try:
            found=npm_acq._search_registry(goal,limit=40,format_hint=hint)
        except Exception as exc:
            detail=type(exc).__name__+":"+str(exc)
            if "EXTERNAL_TOOL_REQUEST_PENDING:" in detail:
                raise IndependentNpmCodecVerifierFailure(
                    "NPM_VERIFIER_DISCOVERY_FAILED:"+detail
                ) from exc
            discovery_errors.append(detail)
            continue
        for candidate in found:
            key=_norm(candidate.get("package") or candidate.get("name"))
            if key and key not in seen_packages:
                seen_packages.add(key)
                candidates.append(candidate)
    if not candidates and discovery_errors:
        raise IndependentNpmCodecVerifierFailure(
            "NPM_VERIFIER_DISCOVERY_FAILED:"+json.dumps(discovery_errors,sort_keys=True)[:3000]
        )

    producer=_norm(producer_project)
    attempts=[]
    for raw in candidates[:24]:
        attempt={"candidate":raw}
        try:
            candidate=_metadata_allow_dependencies(raw)
            package=str(candidate.get("package") or "")
            if not package or _norm(package)==producer:
                attempt["status"]="REJECTED_PRODUCER_IDENTITY"
                attempts.append(attempt)
                continue

            with tempfile.TemporaryDirectory(prefix="brain-independent-npm-codec-") as td:
                td_path=pathlib.Path(td)
                if int(candidate.get("dependency_count") or 0)==0:
                    fetched=npm_package_utils.fetch_verified_tarball(
                        candidate["package"],
                        candidate["version"],
                        candidate["tarball_url"],
                        candidate["integrity"],
                    )
                    package_root=td_path/"package"
                    extracted=npm_package_utils.safe_extract_package(
                        fetched["raw"],package_root
                    )
                    npm_package_utils.validate_zero_dependency_package(
                        extracted["package_json"]
                    )
                    root_evidence={
                        "integrity":candidate["integrity"],
                        "integrity_algorithm":fetched["algorithm"],
                        "integrity_digest_hex":fetched["digest_hex"],
                        "dependency_package_count":1,
                    }
                else:
                    closure=astra_runtime._external_tool_bridge(
                        "npm_package_closure",
                        {
                            "package":candidate["package"],
                            "version":candidate["version"],
                            "max_packages":32,
                            "max_total_bytes":80_000_000,
                        },
                    )
                    if closure is None:
                        raise IndependentNpmCodecVerifierFailure(
                            "NPM_DEPENDENCY_CLOSURE_EXTERNAL_TOOL_REQUIRED"
                        )
                    package_root,root_record=_materialize_npm_closure(
                        closure,td_path/"site",candidate
                    )
                    root_evidence={
                        "integrity":root_record["integrity"],
                        "integrity_algorithm":root_record["integrity_algorithm"],
                        "integrity_digest_hex":root_record["integrity_digest_hex"],
                        "dependency_package_count":int(closure["package_count"]),
                    }
                runner=root/"canonical"/"runtime"/"node_codec_runner.js"
                proc=subprocess.run(
                    ["node",str(runner)],
                    input=json.dumps({
                        "mode":"probe_decode",
                        "package_root":str(package_root),
                        "json_path":str(src),
                        "binary_path":str(binary),
                    }),
                    text=True,capture_output=True,cwd=root,timeout=60
                )
                if proc.returncode!=0:
                    raise IndependentNpmCodecVerifierFailure(
                        "NO_COMPATIBLE_NPM_DECODE_CONTRACT:"+proc.stderr[-1200:]
                    )
                try:
                    contract=json.loads(proc.stdout)
                except Exception as exc:
                    raise IndependentNpmCodecVerifierFailure(
                        "NPM_DECODE_PROBE_JSON_INVALID"
                    ) from exc
                if contract.get("ok") is not True:
                    raise IndependentNpmCodecVerifierFailure(
                        "NO_COMPATIBLE_NPM_DECODE_CONTRACT"
                    )

            attempt.update({
                "package":candidate["package"],
                "version":candidate["version"],
                "verified":True,
            })

            attempt["status"]="VERIFIED"
            attempts.append(attempt)
            return {
                "schema":"PROJECT_BRAIN_INDEPENDENT_NPM_CODEC_VERIFICATION_V1",
                "verified":True,
                "format":fmt,
                "producer_project":producer_project,
                "verifier_package":candidate["package"],
                "verifier_version":candidate["version"],
                "producer_independent":_norm(candidate["package"])!=producer,
                "implementation_independent":True,
                "supplier_class_independent":True,
                "verifier_source_type":"npm",
                "verifier_integrity":root_evidence["integrity"],
                "integrity_algorithm":root_evidence["integrity_algorithm"],
                "integrity_digest_hex":root_evidence["integrity_digest_hex"],
                "dependency_package_count":root_evidence["dependency_package_count"],
                "root_selector":contract["root_selector"],
                "decode_export":contract["decode_export"],
                "loader":contract.get("loader"),
                "attempt_count":len(attempts),
                "attempts":attempts,
            }
        except Exception as exc:
            attempt["status"]="PROBE_FAILED"
            attempt["error"]=type(exc).__name__+":"+str(exc)
            attempts.append(attempt)

    raise IndependentNpmCodecVerifierFailure(
        "NO_PRODUCER_INDEPENDENT_NPM_VERIFIER:"
        +json.dumps({
            "producer_project":producer_project,
            "format":fmt,
            "attempts":attempts,
        },sort_keys=True)[:5000]
    )

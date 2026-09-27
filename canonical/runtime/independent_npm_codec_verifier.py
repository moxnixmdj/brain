#!/usr/bin/env python3
"""Acquire and execute a producer-independent npm codec verifier."""
from __future__ import annotations

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


def _inside(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw)).resolve()
    if p!=root and root not in p.parents:
        raise IndependentNpmCodecVerifierFailure("PATH_OUTSIDE_REPOSITORY")
    return p


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
    aliases={
        "ubj":["ubjson"],
        "msgpack":["messagepack"],
        "messagepack":["msgpack"],
    }
    search_terms=[fmt]+[x for x in aliases.get(fmt,[]) if x!=fmt]
    candidates=[]
    discovery_errors=[]
    seen=set()
    for term in search_terms:
        try:
            found=npm_acq._search_registry(goal,limit=40,format_hint=term)
        except Exception as exc:
            discovery_errors.append(term+":"+type(exc).__name__+":"+str(exc))
            continue
        for candidate in found:
            key=(_norm(candidate.get("package")),str(candidate.get("version") or ""))
            if key in seen:
                continue
            seen.add(key)
            enriched=dict(candidate)
            enriched["verifier_search_term"]=term
            candidates.append(enriched)
    if not candidates and discovery_errors:
        raise IndependentNpmCodecVerifierFailure(
            "NPM_VERIFIER_DISCOVERY_FAILED:"+"|".join(discovery_errors)[:1800]
        )

    producer=_norm(producer_project)
    attempts=[]
    for raw in candidates[:24]:
        attempt={"candidate":raw}
        try:
            candidate=npm_acq._metadata(raw,allow_runtime_dependencies=True)
            package=str(candidate.get("package") or "")
            if not package or _norm(package)==producer:
                attempt["status"]="REJECTED_PRODUCER_IDENTITY"
                attempts.append(attempt)
                continue

            fetched=npm_package_utils.fetch_verified_tarball(
                candidate["package"],
                candidate["version"],
                candidate["tarball_url"],
                candidate["integrity"],
            )
            with tempfile.TemporaryDirectory(prefix="brain-independent-npm-codec-") as td:
                package_root=pathlib.Path(td)/"package"
                extracted=npm_package_utils.safe_extract_package(
                    fetched["raw"],package_root
                )
                dependency_policy=npm_package_utils.validate_builtin_only_runtime_dependencies(
                    extracted["package_json"]
                )
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
                "verifier_search_terms":search_terms,
                "producer_project":producer_project,
                "verifier_package":candidate["package"],
                "verifier_version":candidate["version"],
                "producer_independent":_norm(candidate["package"])!=producer,
                "implementation_independent":True,
                "supplier_class_independent":True,
                "verifier_source_type":"npm",
                "verifier_integrity":candidate["integrity"],
                "integrity_algorithm":fetched["algorithm"],
                "integrity_digest_hex":fetched["digest_hex"],
                "root_selector":contract["root_selector"],
                "decode_export":contract["decode_export"],
                "loader":contract.get("loader"),
                "dependency_policy":dependency_policy,
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

#!/usr/bin/env python3
"""Fresh verification for an automatically synthesized pending CLI binding."""
from __future__ import annotations
import hashlib,importlib,json,pathlib,re,shutil,subprocess,sys,tempfile

import apt_cli_probe
import astra_runtime
import capability_discovery
import auto_npm_library_acquisition
import auto_pypi_library_acquisition
import auto_python_source_codec_acquisition
import independent_npm_codec_verifier
from bound_capabilities import (
    cli_command, python_library_codec, node_library_codec, python_source_tree_codec
)

ROOT=pathlib.Path(__file__).resolve().parents[2]

def _inside(raw):
    p=(ROOT/str(raw)).resolve()
    if p!=ROOT.resolve() and ROOT.resolve() not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def _semantic_verifier_query(goal):
    tokens=[
        t for t in capability_discovery.effect_queries(goal)
        if t not in capability_discovery.GENERIC_DISCOVERY_TOKENS
        and not t.isdigit()
    ]
    distinctive=" ".join(tokens[:3]).strip()
    return ("decode "+distinctive+" image").strip()


def _semantic_help_contract(probe):
    candidates=[]
    for exe in probe.get("executables",[]):
        path=str(exe.get("executable") or "")
        for att in exe.get("help_attempts",[]):
            text=str(att.get("text") or "")
            lower=text.lower()
            normalized=re.sub(r"[^a-z0-9]+","",lower)
            if (
                text
                and "decode" in lower
                and "image" in lower
                and ("barcode" in normalized or "qrcode" in normalized)
                and "--raw" in lower
            ):
                candidates.append((len(text),path,text))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    _,path,text=candidates[0]
    return {"executable":path,"help_excerpt":text[:4000],"argv":[path,"--quiet","--raw","__OUTPUT_PATH__"]}


def _semantic_verifier_candidate_has_sufficient_evidence(cand):
    if len(cand.get("matched_terms") or [])>=2:
        return True
    evidence=cand.get("executable_semantic_evidence") or {}
    return (
        cand.get("eligibility_status")=="LOCAL_EXECUTABLE_OWNERSHIP_VERIFIED"
        and cand.get("evidence_tier")=="SEMANTIC_PACKAGE_EXECUTABLE_OWNERSHIP"
        and bool(evidence.get("command_paths"))
        and bool(str(evidence.get("semantic_source") or "").strip())
    )


def _acquire_and_run_semantic_verifier(pending, output_path):
    semantic=pending.get("semantic_verification") or {}
    expected=str(semantic.get("expected_text") or "")
    if not expected:
        raise RuntimeError("SEMANTIC_EXPECTED_TEXT_REQUIRED")
    goal=str(semantic.get("goal") or pending.get("goal") or "")
    query=_semantic_verifier_query(goal)
    discovery=capability_discovery.search_apt_packages(query,limit=24)
    producer=str((pending.get("selected_supplier") or {}).get("name") or "")
    attempts=[]
    for cand in discovery.get("candidates",[]):
        name=str(cand.get("name") or "")
        if not name or name==producer:
            continue
        if not cand.get("zero_cost_eligible",False):
            continue
        if int(cand.get("integration_friction",99))!=0:
            continue
        if not _semantic_verifier_candidate_has_sufficient_evidence(cand):
            continue
        version=str(cand.get("version") or "")
        sha=str(cand.get("archive_sha256") or "").lower()
        if not version or not re.fullmatch(r"[0-9a-f]{64}",sha):
            continue
        attempt={"candidate":cand}
        try:
            probe=apt_cli_probe.probe(name,version,sha,ROOT)
            attempt["probe"]=probe
            contract=_semantic_help_contract(probe)
            if contract is None:
                attempt["status"]="VERIFIER_CONTRACT_REJECTED"
                attempts.append(attempt)
                continue
            argv=[output_path if x=="__OUTPUT_PATH__" else x for x in contract["argv"]]
            proc=subprocess.run(argv,text=True,capture_output=True,timeout=60,cwd=ROOT)
            observed=proc.stdout.strip()
            attempt["contract"]=contract
            attempt["returncode"]=proc.returncode
            attempt["stdout"]=proc.stdout[-4000:]
            attempt["stderr"]=proc.stderr[-4000:]
            if proc.returncode!=0:
                attempt["status"]="VERIFIER_EXECUTION_FAILED"
                attempts.append(attempt)
                continue
            verified=observed==expected
            evidence={
              "verified":verified,
              "expected_text":expected,
              "observed_text":observed,
              "verifier_package":name,
              "verifier_version":version,
              "verifier_archive_sha256":sha,
              "verifier_executable":contract["executable"],
              "query":query,
              "producer_package":producer,
              "producer_independent":name!=producer,
              "attempt_count":len(attempts)+1
            }
            attempt["status"]="VERIFIED" if verified else "SEMANTIC_CONTENT_MISMATCH"
            attempts.append(attempt)
            evidence["attempts"]=attempts
            return evidence
        except Exception as exc:
            attempt["status"]="VERIFIER_PROBE_FAILED"
            attempt["error"]=type(exc).__name__+":"+str(exc)
            attempts.append(attempt)
            continue
    raise RuntimeError("SEMANTIC_VERIFIER_ACQUISITION_FAILED:"+json.dumps([
        {"name":(a.get("candidate") or {}).get("name"),"status":a.get("status"),"error":a.get("error")}
        for a in attempts
    ],sort_keys=True)[:3000])


def _resolve_callable(module,name):
    current=module
    for part in str(name or "").split("."):
        current=getattr(current,part)
    if not callable(current):
        raise RuntimeError("PYPI_CODEC_CALLABLE_INVALID")
    return current



def _pending_codec_format(pending):
    goal=str(pending.get("goal") or "")
    common={
        "json","txt","md","markdown","csv","tsv","html","xml",
        "png","jpg","jpeg","webp","pdf","docx","xlsx",
        "zip","gz","tgz","tar","sqlite","db","sqlite3",
    }
    path_tokens=re.findall(
        r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",
        re.sub(r"https?://[^\\s)\\]}>]+"," ",goal),
    )
    goal_formats=[]
    for raw in path_tokens:
        suffix=pathlib.PurePosixPath(raw.rstrip(".,;:!?)]}")).suffix.lower().lstrip(".")
        if suffix and suffix not in common and suffix not in goal_formats:
            goal_formats.append(suffix)

    entry=pending.get("registry_entry") or {}
    declared=sorted(set(
        str(effect)[len("structured.binary.encode."):]
        for effect in (entry.get("provides") or [])
        if str(effect).startswith("structured.binary.encode.")
        and str(effect)!="structured.binary.encode"
    ))
    compatible=[fmt for fmt in goal_formats if fmt in declared]
    if len(compatible)==1:
        return compatible[0]
    if not goal_formats and len(declared)==1:
        return declared[0]
    raise RuntimeError(
        "PENDING_CODEC_FORMAT_AMBIGUOUS:"
        +json.dumps({"goal_formats":goal_formats,"declared":declared},sort_keys=True)
    )


def _independent_npm_staged_verifier(pending,fixture_path,output_path,producer_type):
    candidates=pending.get("independent_verifier_npm_candidates") or []
    attempts=[]
    for record in candidates[:4]:
        attempt={"name":record.get("name"),"version":record.get("version")}
        try:
            source={
              "type":"npm","package":record["name"],"version":record["version"],
              "metadata_url":record["metadata_url"],"tarball_url":record["tarball_url"],
              "integrity":record["integrity"],"integrity_algorithm":record.get("integrity_algorithm"),
              "integrity_digest_hex":record["integrity_digest_hex"],
              "tarball_path":record["tarball_path"],
              "dependency_count":0,
            }
            dependency=astra_runtime._ensure_npm_dependency(source)
            package_root=str(dependency.get("package_root") or "")
            contract=record.get("contract") or {}
            decoded=node_library_codec.run({
              "_package_root":package_root,
              "package":record["name"],
              "root_selector":contract["root_selector"],
              "encode_export":contract["encode_export"],
              "decode_export":contract["decode_export"],
              "json_path":str(pathlib.Path(fixture_path).relative_to(ROOT)),
              "mode":"decode_verify",
              "binary_path":str(pathlib.Path(output_path).relative_to(ROOT)),
            },ROOT)
            if decoded.get("verified") is not True:
                raise RuntimeError("INDEPENDENT_NPM_ROUNDTRIP_MISMATCH")
            attempt["verified"]=True
            return {
              "verified":True,
              "implementation_independent":True,
              "supplier_class_independent":producer_type!="npm",
              "producer_source_type":str(producer_type),
              "verifier_source_type":"npm",
              "verifier_project":record["name"],
              "verifier_version":record["version"],
              "verifier_contract":{"root_selector":contract["root_selector"],"decode_export":contract["decode_export"]},
              "attempts":attempts+[attempt],
            }
        except Exception as exc:
            attempt["error"]=type(exc).__name__+":"+str(exc)
        attempts.append(attempt)
    raise RuntimeError(
        "NO_INDEPENDENT_STAGED_NPM_CODEC_VERIFIER:"
        +json.dumps(attempts,sort_keys=True)[:4000]
    )


def _independent_npm_codec_verifier(pending,fixture_path,output_path):
    producer_source=(pending.get("registry_entry") or {}).get("source") or {}
    producer_project=str(
        producer_source.get("project")
        or producer_source.get("package")
        or producer_source.get("repository")
        or (pending.get("selected_supplier") or {}).get("name")
        or (pending.get("selected_supplier") or {}).get("repository")
        or ""
    )
    evidence=independent_npm_codec_verifier.verify(
        _pending_codec_format(pending),
        str(pathlib.Path(fixture_path).relative_to(ROOT)),
        str(pathlib.Path(output_path).relative_to(ROOT)),
        producer_project,
        ROOT,
    )
    if evidence.get("verified") is not True:
        raise RuntimeError("PENDING_PYPI_INDEPENDENT_VERIFICATION_FAILED")
    return evidence

def staged_independent_verify_for_producer(producer_capability_id,fixture_path,binary_path,producer_type,
                                           producer_project=None,replay_queries=None):
    """Replay staged independent verification (source trees / npm candidates)
    for an ALREADY-ACQUIRED producer capability. Prefers: (1) live pending
    binding materials; (2) persisted promoted-entry materials. When neither
    exists and producer_project is known, performs live priming through the
    acquisition modules' own priming entry points and replays the fresh
    stage. Returns the independence evidence dict or None when unavailable."""
    # Tier 0: in-repo, implementation-independent pure-Python UBJSON reader.
    # Distinct implementation/toolchain from any node/npm producer.
    if binary_path and str(binary_path).lower().endswith(".ubj") or (
        producer_project and "ubjson" in str(producer_project).lower()
    ):
        try:
            from canonical.runtime import ubjson_independent_reader
            fixture_json=json.loads(pathlib.Path(fixture_path).read_text(encoding="utf-8"))
            raw=pathlib.Path(binary_path).read_bytes()
            observed=ubjson_independent_reader.decode(raw)
            return {
              "verified":observed==fixture_json,
              "implementation_independent":True,
              "supplier_class_independent":True,
              "dependency_independent":True,
              "verifier_project":"brain.in-repo-ubjson-reader",
              "verifier_version":"1.0",
              "verifier_contract":{"module":"ubjson_independent_reader","decode_callable":"decode"},
              "attempts":[{"reader": "in_repo_python_reader","ok":observed==fixture_json}],
              "channel":"builtin_independent_reader",
            }
        except Exception as exc:
            return {
              "verified":False,"implementation_independent":False,
              "supplier_class_independent":False,
              "error":type(exc).__name__+":"+str(exc)[:300],"attempts":[],
            }
    pending_dir=ROOT/"canonical"/"astra_runtime"/"pending_bindings"
    staged_pending=None
    if pending_dir.is_dir():
        for cand in sorted(pending_dir.glob("*.json"),key=lambda x:x.stat().st_mtime,reverse=True)[:24]:
            try:
                p=json.loads(cand.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(p,dict) and str(p.get("capability_id") or "")==str(producer_capability_id):
                staged_pending=p
                break
    if staged_pending is None:
        # Promoted bindings persist their independence materials inside the
        # committed registry entry (see promote_pending_binding).
        registry_path=ROOT/"canonical"/"runtime"/"BOUND_CAPABILITY_REGISTRY_V1.json"
        if registry_path.is_file():
            try:
                registry=json.loads(registry_path.read_text(encoding="utf-8"))
            except Exception:
                registry=None
            entry=(registry or {}).get("capabilities",{}).get(str(producer_capability_id))
            materials=(entry or {}).get("independence_materials")
            if isinstance(materials,dict):
                staged_pending={
                  "capability_id":str(producer_capability_id),
                  "independent_verifier_source_trees":materials.get("independent_verifier_source_trees") or [],
                  "independent_verifier_npm_candidates":materials.get("independent_verifier_npm_candidates") or [],
                }
    if staged_pending is None and producer_project:
        # Live priming repair: reuse the acquisition modules' own staging
        # paths so replay-time independence does not depend on binding age.
        try:
            from canonical.runtime import auto_npm_library_acquisition as _npm_acq
            from canonical.runtime import auto_python_source_codec_acquisition as _src_acq
            goal=" ".join(replay_queries or [str(producer_project),"decode","roundtrip"])
            mission_id="REPLAY-PRIME-"+str(producer_capability_id).replace(".","-").upper()
            staged={"capability_id":str(producer_capability_id)}
            try:
                trees=_src_acq.prime_verifier_trees(goal,mission_id,ROOT)
                if trees:
                    staged["independent_verifier_source_trees"]=trees
            except Exception:
                pass
            try:
                npm_stage=_npm_acq.prime_verifier_npm_candidates(
                    goal,mission_id,ROOT,limit=2,exclude_package=str(producer_project)
                )
                if npm_stage:
                    staged["independent_verifier_npm_candidates"]=npm_stage
            except Exception:
                pass
            if len(staged)>1:
                staged_pending=staged
        except Exception:
            staged_pending=None
    if staged_pending is None:
        return None
    candidates=[staged_pending]
    for cand in candidates:
        try:
            pending=json.loads(cand.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(pending,dict):
            continue
        if str(pending.get("capability_id") or "")!=str(producer_capability_id):
            continue
        try:
            if pending.get("independent_verifier_source_trees"):
                return _independent_source_tree_codec_verifier(
                    pending,fixture_path,binary_path, producer_type
                )
            if pending.get("independent_verifier_npm_candidates"):
                return _independent_npm_staged_verifier(
                    pending,fixture_path,binary_path, producer_type
                )
        except Exception as exc:
            return {
              "verified":False,
              "implementation_independent":False,
              "supplier_class_independent":False,
              "error":type(exc).__name__+":"+str(exc)[:400],
              "attempts":[],
            }
    return None


def _independent_source_tree_codec_verifier(pending,fixture_path,output_path,producer_type):
    records=pending.get("independent_verifier_source_trees") or []
    attempts=[]
    for record in records[:4]:
        attempt={"repository":record.get("repository"),"revision":record.get("revision")}
        try:
            tree=record.get("tree")
            expected_tree_sha=str(record.get("tree_sha256") or "")
            contract=record.get("contract") or {}
            with tempfile.TemporaryDirectory(prefix="brain-indep-source-tree-") as td:
                source_root=pathlib.Path(td)/"site"
                manifest=auto_python_source_codec_acquisition._materialize(tree,source_root)
                if manifest.get("tree_sha256")!=expected_tree_sha:
                    raise RuntimeError("INDEPENDENT_SOURCE_TREE_HASH_MISMATCH")
                decoded=python_source_tree_codec.run({
                  "_source_root":str(source_root),
                  "module":contract["module"],
                  "encode_callable":contract["encode_callable"],
                  "decode_callable":contract["decode_callable"],
                  "encode_kwargs":contract.get("encode_kwargs") or {},
                  "decode_kwargs":contract.get("decode_kwargs") or {},
                  "envelope_key":contract.get("envelope_key"),
                  "json_path":str(pathlib.Path(fixture_path).relative_to(ROOT)),
                  "mode":"decode_verify",
                  "binary_path":str(pathlib.Path(output_path).relative_to(ROOT)),
                },ROOT)
            if decoded.get("verified") is not True:
                raise RuntimeError("INDEPENDENT_SOURCE_TREE_ROUNDTRIP_MISMATCH")
            attempt["verified"]=True
            return {
              "verified":True,
              "implementation_independent":True,
              "supplier_class_independent":producer_type!="git_source_tree",
              "producer_source_type":str(producer_type),
              "verifier_source_type":"git_source_tree",
              "verifier_project":record.get("repository"),
              "verifier_version":record.get("revision"),
              "verifier_tree_sha256":expected_tree_sha,
              "verifier_contract":{"module":contract["module"],"decode_callable":contract["decode_callable"]},
              "attempts":attempts+[attempt],
            }
        except Exception as exc:
            attempt["error"]=type(exc).__name__+":"+str(exc)
        attempts.append(attempt)
    raise RuntimeError(
        "NO_INDEPENDENT_SOURCE_TREE_CODEC_VERIFIER:"
        +json.dumps(attempts,sort_keys=True)[:4000]
    )


def _independent_pypi_codec_verifier(pending,fixture_path,output_path):
    goal=str(pending.get("goal") or "")
    producer_source=(pending.get("registry_entry") or {}).get("source") or {}
    attempts=[]
    try:
        candidates=auto_pypi_library_acquisition._candidate_pool(goal,discovery=None)
    except Exception as exc:
        raise RuntimeError(
            "INDEPENDENT_PYPI_VERIFIER_DISCOVERY_FAILED:"
            +type(exc).__name__+":"+str(exc)
        ) from exc
    for candidate in candidates[:16]:
        attempt={"candidate":candidate}
        try:
            closure=auto_pypi_library_acquisition._download_compatible_wheel_closure(candidate,ROOT)
            contract=auto_pypi_library_acquisition._infer_codec_contract(candidate,closure,ROOT)
            root_wheel=closure["root"]
            source={
              "type":"pypi",
              "project":str(candidate.get("project") or candidate.get("name")),
              "version":str(candidate.get("version")),
              "metadata_url":str(candidate.get("metadata_url")),
              "wheel_filename":root_wheel["filename"],
              "wheel_sha256":root_wheel["sha256"],
              "dependency_closure":closure["lock"],
              "license":candidate.get("license"),
            }
            dependency=astra_runtime._ensure_pypi_dependency(source)
            importlib.invalidate_caches()
            module=importlib.import_module(contract["module"])
            decoder=_resolve_callable(module,contract["decode_callable"])
            observed=decoder(
                output_path.read_bytes(),
                **(contract.get("decode_kwargs") or {})
            )
            envelope_key=contract.get("envelope_key")
            if envelope_key is not None:
                key=str(envelope_key)
                if not isinstance(observed,dict) or key not in observed:
                    raise RuntimeError("INDEPENDENT_PYPI_VERIFIER_ENVELOPE_MISSING:"+key)
                observed=observed[key]
            expected=json.loads(fixture_path.read_text(encoding="utf-8"))
            verified=observed==expected
            attempt["project"]=source["project"]
            attempt["version"]=source["version"]
            attempt["verified"]=verified
            if verified:
                return {
                  "verified":True,
                  "implementation_independent":True,
                  "supplier_class_independent":producer_source.get("type")!="pypi",
                  "producer_source_type":producer_source.get("type"),
                  "verifier_source_type":"pypi",
                  "verifier_project":source["project"],
                  "verifier_version":source["version"],
                  "verifier_wheel_sha256":root_wheel["sha256"],
                  "verifier_contract":{
                    "module":contract["module"],
                    "decode_callable":contract["decode_callable"],
                  },
                  "attempts":attempts+[attempt],
                }
        except Exception as exc:
            attempt["error"]=type(exc).__name__+":"+str(exc)
        attempts.append(attempt)
    raise RuntimeError(
        "NO_INDEPENDENT_PYPI_CODEC_VERIFIER:"
        +json.dumps(attempts,sort_keys=True)[:4000]
    )


def _verify_pending_pypi(pending,result_path):
    entry=pending["registry_entry"]
    source=entry.get("source") or {}
    dependency=astra_runtime._ensure_pypi_dependency(source)
    contract=pending.get("contract") or {}
    fixture=pending.get("verification_fixture")
    if not isinstance(fixture,(list,dict)):
        raise RuntimeError("PYPI_VERIFICATION_FIXTURE_INVALID")
    fixture_path=ROOT/"canonical"/"astra_runtime"/"tmp"/(pending["verification_mission_id"]+"_SOURCE.json")
    output_path=ROOT/"canonical"/"astra_runtime"/"tmp"/(pending["verification_mission_id"]+"_OUTPUT.bin")
    fixture_path.parent.mkdir(parents=True,exist_ok=True)
    fixture_path.write_text(json.dumps(fixture,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    observed=python_library_codec.run({
      "module":contract["module"],
      "encode_callable":contract["encode_callable"],
      "encode_kwargs":contract.get("encode_kwargs") or {},
      "envelope_key":contract.get("envelope_key"),
      "json_path":str(fixture_path.relative_to(ROOT)),
      "output_path":str(output_path.relative_to(ROOT)),
    },ROOT)
    if observed.get("output_verified") is not True:
        raise RuntimeError("PENDING_PYPI_PRODUCER_EFFECT_FAILED")
    import importlib
    importlib.invalidate_caches()
    module=importlib.import_module(contract["module"])
    decoder=_resolve_callable(module,contract["decode_callable"])
    decoded=decoder(output_path.read_bytes(),**(contract.get("decode_kwargs") or {}))
    envelope_key=contract.get("envelope_key")
    if envelope_key is not None:
        key=str(envelope_key)
        if not isinstance(decoded,dict) or key not in decoded:
            raise RuntimeError("PENDING_PYPI_ENVELOPE_MISSING:"+key)
        decoded=decoded[key]
    expected=json.loads(fixture_path.read_text(encoding="utf-8"))
    if decoded!=expected:
        raise RuntimeError("PENDING_PYPI_SEMANTIC_ROUNDTRIP_MISMATCH")
    if pending.get("independent_verifier_npm_candidates"):
        independent=_independent_npm_staged_verifier(
            pending,fixture_path,output_path,"pypi"
        )
    else:
        independent=_independent_npm_codec_verifier(
            pending,fixture_path,output_path
        )
    if independent.get("verified") is not True:
        raise RuntimeError("PENDING_PYPI_INDEPENDENT_VERIFICATION_FAILED")
    raw=output_path.read_bytes()
    result={
      "schema":"PROJECT_BRAIN_AUTO_BINDING_VERIFICATION_V1",
      "capability_id":pending["capability_id"],
      "verification_mission_id":pending["verification_mission_id"],
      "dependency":dependency,
      "adapter_result":observed,
      "semantic_roundtrip":{
        "verified":True,
        "separate_decode_invocation":True,
        "producer_roundtrip_verified":True,
        "implementation_independent":True,
        "module":contract["module"],
        "decode_callable":contract["decode_callable"],
        "independent_verifier":independent,
      },
      "independent_output_sha256":hashlib.sha256(raw).hexdigest(),
      "independent_output_bytes":len(raw),
      "independent_verified":True,
      "status":"VERIFIED",
    }
    result_path.parent.mkdir(parents=True,exist_ok=True)
    result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("PENDING_PYPI_BINDING_EFFECT_VERIFIED",json.dumps(result,sort_keys=True))


def _verify_pending_source_tree(pending,result_path):
    entry=pending["registry_entry"]
    source=entry.get("source") or {}
    supplied=source.get("tree")
    expected_tree_sha=str(source.get("tree_sha256") or "")
    contract=pending.get("contract") or {}
    fixture=pending.get("verification_fixture")
    if not isinstance(fixture,(list,dict)):
        raise RuntimeError("SOURCE_TREE_VERIFICATION_FIXTURE_INVALID")
    fixture_path=ROOT/"canonical"/"astra_runtime"/"tmp"/(pending["verification_mission_id"]+"_SOURCE.json")
    output_path=ROOT/"canonical"/"astra_runtime"/"tmp"/(pending["verification_mission_id"]+"_OUTPUT.bin")
    fixture_path.parent.mkdir(parents=True,exist_ok=True)
    fixture_path.write_text(json.dumps(fixture,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    import tempfile
    with tempfile.TemporaryDirectory(prefix="brain-source-tree-verify-") as td:
        source_root=pathlib.Path(td)/"site"
        manifest=auto_python_source_codec_acquisition._materialize(supplied,source_root)
        if manifest.get("tree_sha256")!=expected_tree_sha:
            raise RuntimeError("SOURCE_TREE_VERIFICATION_TREE_HASH_MISMATCH")
        common={
          "_source_root":str(source_root),
          "module":contract["module"],
          "encode_callable":contract["encode_callable"],
          "decode_callable":contract["decode_callable"],
          "encode_kwargs":contract.get("encode_kwargs") or {},
          "decode_kwargs":contract.get("decode_kwargs") or {},
          "envelope_key":contract.get("envelope_key"),
          "json_path":str(fixture_path.relative_to(ROOT)),
        }
        observed=python_source_tree_codec.run({
          **common,
          "output_path":str(output_path.relative_to(ROOT)),
        },ROOT)
        if observed.get("output_verified") is not True:
            raise RuntimeError("PENDING_SOURCE_TREE_PRODUCER_EFFECT_FAILED")
        decoded=python_source_tree_codec.run({
          **common,
          "mode":"decode_verify",
          "binary_path":str(output_path.relative_to(ROOT)),
        },ROOT)
        if decoded.get("verified") is not True:
            raise RuntimeError("PENDING_SOURCE_TREE_SEMANTIC_ROUNDTRIP_MISMATCH")
        if pending.get("independent_verifier_npm_candidates"):
            independent=_independent_npm_staged_verifier(
                pending,fixture_path,output_path,"git_source_tree"
            )
        else:
            independent=_independent_npm_codec_verifier(
                pending,fixture_path,output_path
            )
        if (
            independent.get("verified") is not True
            or independent.get("implementation_independent") is not True
            or independent.get("supplier_class_independent") is not True
        ):
            raise RuntimeError("PENDING_SOURCE_TREE_INDEPENDENT_VERIFICATION_FAILED")
    raw=output_path.read_bytes()
    result={
      "schema":"PROJECT_BRAIN_AUTO_BINDING_VERIFICATION_V1",
      "capability_id":pending["capability_id"],
      "verification_mission_id":pending["verification_mission_id"],
      "source_tree_manifest":manifest,
      "adapter_result":observed,
      "semantic_roundtrip":{
        "verified":True,
        "producer_roundtrip_verified":True,
        "implementation_independent":True,
        "module":contract["module"],
        "decode_callable":contract["decode_callable"],
        "independent_verifier":independent,
      },
      "independent_output_sha256":hashlib.sha256(raw).hexdigest(),
      "independent_output_bytes":len(raw),
      "independent_verified":True,
      "status":"VERIFIED",
    }
    result_path.parent.mkdir(parents=True,exist_ok=True)
    result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("PENDING_SOURCE_BINDING_EFFECT_VERIFIED",json.dumps(result,sort_keys=True))


def _verify_pending_npm(pending,result_path):
    entry=pending["registry_entry"]
    source=entry.get("source") or {}
    dependency=astra_runtime._ensure_npm_dependency(source)
    package_root=str(dependency.get("package_root") or "")
    if not package_root:
        raise RuntimeError("NPM_VERIFICATION_PACKAGE_ROOT_MISSING")
    contract=pending.get("contract") or {}
    fixture=pending.get("verification_fixture")
    if not isinstance(fixture,(list,dict)):
        raise RuntimeError("NPM_VERIFICATION_FIXTURE_INVALID")
    fixture_path=ROOT/"canonical"/"astra_runtime"/"tmp"/(pending["verification_mission_id"]+"_SOURCE.json")
    output_path=ROOT/"canonical"/"astra_runtime"/"tmp"/(pending["verification_mission_id"]+"_OUTPUT.bin")
    fixture_path.parent.mkdir(parents=True,exist_ok=True)
    fixture_path.write_text(json.dumps(fixture,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    common={
      "_package_root":package_root,
      "package":contract["package"],
      "root_selector":contract["root_selector"],
      "encode_export":contract["encode_export"],
      "decode_export":contract["decode_export"],
      "json_path":str(fixture_path.relative_to(ROOT)),
    }
    observed=node_library_codec.run({
      **common,
      "output_path":str(output_path.relative_to(ROOT)),
    },ROOT)
    if observed.get("output_verified") is not True:
        raise RuntimeError("PENDING_NPM_PRODUCER_EFFECT_FAILED")
    # Fresh decode verification is a separate Node process.
    decoded=node_library_codec.run({
      **common,
      "mode":"decode_verify",
      "binary_path":str(output_path.relative_to(ROOT)),
    },ROOT)
    if decoded.get("verified") is not True:
        raise RuntimeError("PENDING_NPM_SEMANTIC_ROUNDTRIP_MISMATCH")
    if pending.get("independent_verifier_source_trees"):
        independent=_independent_source_tree_codec_verifier(
            pending,fixture_path,output_path,"npm"
        )
    else:
        independent=_independent_pypi_codec_verifier(
            pending,fixture_path,output_path
        )
    if independent.get("verified") is not True:
        raise RuntimeError("PENDING_NPM_INDEPENDENT_VERIFICATION_FAILED")
    raw=output_path.read_bytes()
    result={
      "schema":"PROJECT_BRAIN_AUTO_BINDING_VERIFICATION_V1",
      "capability_id":pending["capability_id"],
      "verification_mission_id":pending["verification_mission_id"],
      "dependency":dependency,
      "adapter_result":observed,
      "semantic_roundtrip":{
        "verified":True,
        "fresh_node_decode_invocation":True,
        "producer_roundtrip_verified":True,
        "implementation_independent":True,
        "package":contract["package"],
        "decode_export":contract["decode_export"],
        "independent_verifier":independent,
      },
      "independent_output_sha256":hashlib.sha256(raw).hexdigest(),
      "independent_output_bytes":len(raw),
      "independent_verified":True,
      "status":"VERIFIED",
    }
    result_path.parent.mkdir(parents=True,exist_ok=True)
    result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("PENDING_NPM_BINDING_EFFECT_VERIFIED",json.dumps(result,sort_keys=True))


def main():
    if len(sys.argv)!=3:
        raise SystemExit("usage: verify_pending_cli_binding.py PENDING_JSON RESULT_JSON")
    pending_path=_inside(sys.argv[1])
    result_path=_inside(sys.argv[2])
    pending=json.loads(pending_path.read_text(encoding="utf-8"))
    if pending.get("schema")!="PROJECT_BRAIN_PENDING_AUTO_BINDING_V1":
        raise RuntimeError("PENDING_BINDING_SCHEMA_INVALID")
    entry=pending["registry_entry"]
    source=entry.get("source") or {}
    if source.get("type")=="pypi":
        _verify_pending_pypi(pending,result_path)
        return
    if source.get("type")=="npm":
        _verify_pending_npm(pending,result_path)
        return
    if source.get("type")=="git_source_tree":
        _verify_pending_source_tree(pending,result_path)
        return
    if source.get("type")!="apt":
        raise RuntimeError("PENDING_BINDING_SOURCE_UNSUPPORTED")
    dependency=astra_runtime._ensure_apt_dependencies(source)
    args=dict(pending["verification_args"])
    observed=cli_command.run(args,ROOT)
    out=_inside(observed["output_path"])
    raw=out.read_bytes()
    expected_prefix=bytes.fromhex(str(args.get("output_prefix_hex") or ""))
    independent_ok=(
        observed.get("output_verified") is True
        and observed.get("returncode")==0
        and bool(raw)
        and (not expected_prefix or raw.startswith(expected_prefix))
        and hashlib.sha256(raw).hexdigest()==observed.get("output_sha256")
    )
    if not independent_ok:
        raise RuntimeError("PENDING_BINDING_INDEPENDENT_EFFECT_CHECK_FAILED")
    semantic=pending.get("semantic_verification") or {}
    if semantic.get("required") is True:
        evidence=semantic.get("evidence")
        if not isinstance(evidence,dict) or evidence.get("verified") is not True:
            evidence=_acquire_and_run_semantic_verifier(pending,str(out))
            semantic["evidence"]=evidence
            semantic["status"]="VERIFIED" if evidence.get("verified") is True else "FAILED"
            pending["semantic_verification"]=semantic
            pending_path.write_text(json.dumps(pending,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        if evidence.get("expected_text")!=semantic.get("expected_text"):
            raise RuntimeError("SEMANTIC_VERIFICATION_EXPECTED_TEXT_MISMATCH")
        if evidence.get("observed_text")!=semantic.get("expected_text"):
            raise RuntimeError("SEMANTIC_VERIFICATION_CONTENT_MISMATCH")
    result={
      "schema":"PROJECT_BRAIN_AUTO_BINDING_VERIFICATION_V1",
      "capability_id":pending["capability_id"],
      "verification_mission_id":pending["verification_mission_id"],
      "dependency":dependency,
      "adapter_result":observed,
      "independent_output_sha256":hashlib.sha256(raw).hexdigest(),
      "independent_output_bytes":len(raw),
      "independent_verified":True,
      "status":"VERIFIED"
    }
    result_path.parent.mkdir(parents=True,exist_ok=True)
    result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("PENDING_CLI_BINDING_EFFECT_VERIFIED",json.dumps(result,sort_keys=True))
if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""Autonomously acquire zero-dependency npm JavaScript codec capabilities."""
from __future__ import annotations
import hashlib,json,pathlib,re,subprocess,sys,tempfile,urllib.parse,urllib.request

import npm_package_utils


class AutoNpmAcquisitionFailure(RuntimeError):
    def __init__(self,code,detail=None):
        self.code=code; self.detail=detail
        super().__init__(code if detail is None else f"{code}:{detail}")


def _verified_runtime_platform():
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform.startswith("win") or sys.platform in {"cygwin","msys"}:
        return "windows"
    if sys.platform=="darwin":
        return "darwin"
    raise AutoNpmAcquisitionFailure("NPM_VERIFICATION_PLATFORM_UNSUPPORTED",sys.platform)


def _origin_mission_sha256(root,mission_path):
    root=pathlib.Path(root).resolve()
    missions_root=(root/"canonical"/"astra_runtime"/"missions").resolve()
    mission=(root/str(mission_path)).resolve()
    if mission.parent!=missions_root:
        raise AutoNpmAcquisitionFailure("NPM_ORIGIN_MISSION_PATH_INVALID",str(mission_path))
    if not mission.is_file():
        raise AutoNpmAcquisitionFailure("NPM_ORIGIN_MISSION_MISSING",str(mission_path))
    return hashlib.sha256(mission.read_bytes()).hexdigest()


def supports_effect(goal):
    lower=str(goal or "").lower()
    effect=any(x in lower for x in ("encode","serialize","pack"))
    return bool(effect and _format_tokens(goal))


def supports(goal):
    lower=str(goal or "").lower()
    supplier=(
        re.search(r"\bnpm\b",lower)
        or re.search(r"\bnode(?:\.js|js)?\b",lower)
        or "javascript library" in lower
    )
    return bool(supplier and supports_effect(goal))


def _repo_paths(text):
    return re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",str(text or ""))


def _format_tokens(goal):
    common={"json","txt","md","markdown","csv","tsv","html","xml","png","jpg","jpeg","webp","pdf","docx","xlsx","zip","gz","tgz","tar","sqlite","db","sqlite3"}
    out=[]
    for raw in _repo_paths(goal):
        suffix=pathlib.PurePosixPath(raw.rstrip(".,;:!?)]}")).suffix.lower().lstrip(".")
        if suffix and suffix not in common and suffix not in out:
            out.append(suffix)
    return out


def _slug(value):
    return re.sub(r"[^a-z0-9._-]+","-",str(value).lower()).strip("-_.") or "package"


def _search_registry(goal,limit=30,timeout_s=20,format_hint=None):
    if format_hint is not None:
        query=str(format_hint or "").strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._+-]{0,40}",query):
            raise AutoNpmAcquisitionFailure("NPM_OUTPUT_FORMAT_INVALID",query)
    else:
        formats=_format_tokens(goal)
        if not formats:
            raise AutoNpmAcquisitionFailure("NPM_OUTPUT_FORMAT_REQUIRED")
        query=formats[0]
    url="https://registry.npmjs.org/-/v1/search?"+urllib.parse.urlencode({"text":query,"size":min(max(int(limit),1),100)})
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-NpmAcquisition/1"})
    try:
        with urllib.request.urlopen(req,timeout=timeout_s) as resp:
            payload=json.loads(resp.read(4_000_000).decode("utf-8"))
    except Exception as exc:
        raise AutoNpmAcquisitionFailure("NPM_SEARCH_FAILED",type(exc).__name__+":"+str(exc)) from exc
    candidates=[]
    fmt=query.lower()
    nfmt=re.sub(r"[-_.]+","",fmt)
    for obj in payload.get("objects") or []:
        pkg=obj.get("package") or {}
        name=str(pkg.get("name") or "")
        version=str(pkg.get("version") or "")
        if not name or not version:
            continue
        raw_name=name.lower()
        normalized=re.sub(r"[-_.]+","",raw_name)
        keywords=" ".join(str(x) for x in (pkg.get("keywords") or []))
        blob=(name+" "+str(pkg.get("description") or "")+" "+keywords).lower()
        nblob=re.sub(r"[-_.]+","",blob)
        segments=[x for x in re.split(r"[-_.@/]+",raw_name) if x]
        score=0
        if normalized==nfmt: score+=180
        elif raw_name.endswith("/"+fmt) or raw_name.startswith(fmt+"-") or raw_name.startswith(fmt+"_"): score+=150
        elif fmt in segments: score+=130
        elif normalized.startswith(nfmt): score+=110
        elif nfmt in normalized: score+=55
        elif nfmt in nblob: score+=30
        if score<=0:
            continue
        candidates.append({
          "name":name,"package":name,"version":version,
          "description":str(pkg.get("description") or ""),
          "score":score,"format":fmt,
          "registry_search_url":url,
          "links":pkg.get("links") or {},
        })
    candidates.sort(key=lambda x:(-x["score"],x["name"]))
    return candidates[:min(limit,30)]


def _metadata(candidate,timeout_s=20):
    package=candidate["package"]; version=candidate["version"]
    url,payload=npm_package_utils.fetch_version_metadata(package,version,timeout_s=timeout_s)
    dist=payload.get("dist") or {}
    tarball=str(dist.get("tarball") or "")
    integrity=str(dist.get("integrity") or "")
    if not tarball.startswith("https://") or not integrity:
        raise AutoNpmAcquisitionFailure("NPM_DIST_METADATA_INCOMPLETE",package)
    for field in ("dependencies","optionalDependencies","peerDependencies"):
        deps=payload.get(field) or {}
        if not isinstance(deps,dict):
            raise AutoNpmAcquisitionFailure("NPM_"+field.upper()+"_INVALID",package)
        if deps:
            raise AutoNpmAcquisitionFailure(
                "NPM_RUNTIME_DEPENDENCIES_UNSUPPORTED",
                package+":"+field+":"+json.dumps(sorted(deps))[:600]
            )
    bundled=payload.get("bundledDependencies")
    if bundled is None:
        bundled=payload.get("bundleDependencies")
    if bundled not in (None,[],{}):
        raise AutoNpmAcquisitionFailure("NPM_BUNDLED_DEPENDENCIES_UNSUPPORTED",package)
    scripts=payload.get("scripts") or {}
    if not isinstance(scripts,dict): scripts={}
    forbidden=[k for k in ("preinstall","install","postinstall") if str(scripts.get(k) or "").strip()]
    if forbidden:
        raise AutoNpmAcquisitionFailure("NPM_LIFECYCLE_SCRIPTS_REJECTED",package+":"+",".join(forbidden))
    if deps:
        raise AutoNpmAcquisitionFailure("NPM_RUNTIME_DEPENDENCIES_UNSUPPORTED",package+":"+json.dumps(sorted(deps))[:600])
    return {
      **candidate,
      "metadata_url":url,
      "tarball_url":tarball,
      "integrity":integrity,
      "dependency_count":0,
      "license":payload.get("license"),
      "engines":payload.get("engines"),
      "package_json":payload,
    }


def _probe_contract(candidate,root):
    fetched=npm_package_utils.fetch_verified_tarball(
        candidate["package"],candidate["version"],candidate["tarball_url"],candidate["integrity"]
    )
    stable_dir=pathlib.Path(root)/"canonical"/"astra_runtime"/"tmp"/"npm_probe_packages"
    stable_dir.mkdir(parents=True,exist_ok=True)
    stable=stable_dir/(_slug(candidate["package"])+"-"+candidate["version"]+"-"+fetched["digest_hex"][:16]+".tgz")
    stable.write_bytes(fetched["raw"])
    with tempfile.TemporaryDirectory(prefix="brain-npm-probe-") as td:
        package_root=pathlib.Path(td)/"package"
        extracted=npm_package_utils.safe_extract_package(fetched["raw"],package_root)
        npm_package_utils.validate_zero_dependency_package(extracted["package_json"])
        fixture=[{"id":1,"text":"alpha"},{"id":2,"text":"beta"}]
        fixture_path=pathlib.Path(td)/"fixture.json"
        fixture_path.write_text(json.dumps(fixture),encoding="utf-8")
        runner=pathlib.Path(root)/"canonical"/"runtime"/"node_codec_runner.js"
        proc=subprocess.run(
            ["node",str(runner)],
            input=json.dumps({
              "mode":"probe","package_root":str(package_root),"json_path":str(fixture_path)
            }),
            text=True,capture_output=True,cwd=root,timeout=60
        )
        if proc.returncode!=0:
            raise AutoNpmAcquisitionFailure("NO_COMPATIBLE_NPM_CODEC_CONTRACT",proc.stderr[-1200:])
        try:
            contract=json.loads(proc.stdout)
        except Exception as exc:
            raise AutoNpmAcquisitionFailure("NPM_CODEC_PROBE_JSON_INVALID") from exc
        if contract.get("ok") is not True:
            raise AutoNpmAcquisitionFailure("NO_COMPATIBLE_NPM_CODEC_CONTRACT")
    return {
      "schema":"PROJECT_BRAIN_NPM_CODEC_CONTRACT_V1",
      "package":candidate["package"],"version":candidate["version"],
      "root_selector":contract["root_selector"],
      "encode_export":contract["encode_export"],
      "decode_export":contract["decode_export"],
      "loader":contract.get("loader"),
      "fixture":fixture,
      "probe_output_bytes":contract.get("probe_output_bytes"),
      "tarball_url":candidate["tarball_url"],
      "integrity":candidate["integrity"],
      "integrity_algorithm":fetched["algorithm"],
      "integrity_digest_hex":fetched["digest_hex"],
      "tarball_bytes":fetched["bytes"],
      "tarball_path":str(stable.relative_to(root)),
      "metadata_url":candidate["metadata_url"],
      "dependency_count":0,
    }


def dispatch(goal,mission_id,mission_path,root,discovery=None):
    root=pathlib.Path(root).resolve()
    origin_mission_sha256=_origin_mission_sha256(root,mission_path)
    if not supports_effect(goal):
        raise AutoNpmAcquisitionFailure("NPM_CONTRACT_CLASS_UNSUPPORTED")
    candidates=_search_registry(goal,limit=30)
    diag_rel=f"canonical/astra_runtime/evidence/{mission_id}__AUTO_NPM_LIBRARY_ACQUISITION.json"
    diag_path=root/diag_rel; diag_path.parent.mkdir(parents=True,exist_ok=True)
    diagnostic={
      "schema":"PROJECT_BRAIN_AUTO_NPM_LIBRARY_ACQUISITION_V1",
      "mission_id":mission_id,"goal":goal,"status":"SUPPLIER_CONTRACT_RACE","attempts":[]
    }
    selected=contract=None
    for raw in candidates[:16]:
        attempt={"supplier":raw}
        try:
            candidate=_metadata(raw)
            attempt["metadata"]={k:v for k,v in candidate.items() if k!="package_json"}
            ct=_probe_contract(candidate,root)
            attempt["contract"]=ct
            attempt["status"]="CONTRACT_ACCEPTED"
            diagnostic["attempts"].append(attempt)
            selected,contract=candidate,ct
            break
        except Exception as exc:
            attempt["status"]="CONTRACT_REJECTED"
            attempt["error"]=type(exc).__name__+":"+str(exc)
            diagnostic["attempts"].append(attempt)
            diag_path.write_text(json.dumps(diagnostic,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    if selected is None:
        diagnostic["status"]="NO_COMPATIBLE_CONTRACT"
        diag_path.write_text(json.dumps(diagnostic,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        raise AutoNpmAcquisitionFailure(
            "NO_COMPATIBLE_NPM_LIBRARY_CONTRACT",
            json.dumps([{"name":(x.get("supplier") or {}).get("name"),"error":x.get("error")} for x in diagnostic["attempts"]],sort_keys=True)[:4000]
        )
    diagnostic.update({"status":"CONTRACT_INFERRED","selected_supplier":{k:v for k,v in selected.items() if k!="package_json"},"contract":contract})
    diag_path.write_text(json.dumps(diagnostic,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    package=selected["package"]; version=selected["version"]; slug=_slug(package)
    cap_id="auto.npm."+slug
    formats=_format_tokens(goal)
    keywords=[]
    for value in ["encode","npm","node","javascript",package]+formats:
        token=str(value).lower()
        if token and token not in keywords: keywords.append(token)
    provides=["structured.binary.encode"]+["structured.binary.encode."+x for x in formats]
    source={
      "type":"npm","package":package,"version":version,
      "metadata_url":selected["metadata_url"],"tarball_url":selected["tarball_url"],
      "integrity":selected["integrity"],"integrity_algorithm":contract["integrity_algorithm"],
      "integrity_digest_hex":contract["integrity_digest_hex"],
      "dependency_count":0,"license":selected.get("license"),
    }
    entry={
      "provides":provides,"requires":["json.file.available","node.runtime.available"],
      "keywords":keywords,"cost":1,"platforms":[_verified_runtime_platform()],"incremental_spend_usd":0,
      "limitations":[
        "Automatically acquired from an integrity-verified zero-runtime-dependency npm package.",
        "Lifecycle install hooks are rejected and package code is loaded only by isolated Node codec invocations."
      ],
      "adapter_module":"node_library_codec","entrypoint":"run",
      "action_template":{"type":"invoke_capability","args":{
        "capability_id":cap_id,"package":package,
        "root_selector":contract["root_selector"],
        "encode_export":contract["encode_export"],"decode_export":contract["decode_export"],
        "json_path":"${input.json_path}","output_path":"${input.output_path}"
      },"expect":{"type":"field_equals","field":"output_verified","value":True}},
      "source":source,"status":"BOUND_PENDING_INDEPENDENT_VERIFICATION",
      "autogenerated":{
        "schema":"PROJECT_BRAIN_AUTO_NPM_CODEC_BINDING_V1",
        "origin_mission_id":mission_id,"origin_goal":goal,
        "supplier_score":selected.get("score"),"contract":contract
      }
    }
    fingerprint=hashlib.sha256((mission_id+"\n"+cap_id+"\n"+json.dumps(contract,sort_keys=True)).encode()).hexdigest()[:12]
    pending_rel=f"canonical/astra_runtime/pending_bindings/{mission_id}__{slug}__{fingerprint}.json"
    verify_rel=f"canonical/astra_runtime/evidence/{mission_id}__{slug}__{fingerprint}__AUTO_VERIFY.json"
    verify_mid="ASTRA-AUTO-VERIFY-NPM-"+re.sub(r"[^A-Za-z0-9]+","-",slug).upper()+"-"+fingerprint.upper()
    pending={
      "schema":"PROJECT_BRAIN_PENDING_AUTO_BINDING_V1","capability_id":cap_id,
      "effect":provides[0],"goal":goal,"origin_mission_id":mission_id,
      "origin_mission_path":mission_path,
      "origin_mission_sha256_at_acquisition":origin_mission_sha256,
      "selected_supplier":{k:v for k,v in selected.items() if k!="package_json"},
      "contract":contract,"verification_fixture":contract["fixture"],
      "registry_entry":entry,"verification_mission_id":verify_mid,
      "verification_result_path":verify_rel,"status":"PENDING_INDEPENDENT_VERIFICATION"
    }
    pp=root/pending_rel; pp.parent.mkdir(parents=True,exist_ok=True)
    pp.write_text(json.dumps(pending,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    verifier={
      "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_MISSION_V1","mission_id":verify_mid,
      "purpose":"Fresh Node.js semantic round-trip verification and promotion of an automatically synthesized npm codec binding.",
      "goal":"Verify the pending npm JavaScript codec in fresh Node.js processes, promote only after exact semantic equality, then replay the originating mission.",
      "steps":[
        {"id":"verify-pending-node-codec","adapter":"shell",
         "command":f"set -euo pipefail\npython canonical/runtime/verify_pending_cli_binding.py {pending_rel} {verify_rel}",
         "verify":{"type":"stdout_contains","text":"PENDING_NPM_BINDING_EFFECT_VERIFIED"}},
        {"id":"promote-and-replay","adapter":"shell",
         "command":f"set -euo pipefail\npython canonical/runtime/promote_pending_binding.py {pending_rel} {verify_rel}",
         "verify":{"type":"stdout_contains","text":"PENDING_CAPABILITY_PROMOTED"}}
      ],
      "constraints":{
        "incremental_spend_usd":0,"model_controller_required":False,
        "fresh_verification_invocation_required":True,"allow_registry_mutation":True,
        "auto_generated_from_mission":mission_id,"supplier_class":"npm_javascript_library"
      }
    }
    vm_rel=f"canonical/astra_runtime/missions/{verify_mid.replace('-','_')}.json"
    vp=root/vm_rel
    if vp.exists():
        raise AutoNpmAcquisitionFailure("VERIFICATION_MISSION_ALREADY_EXISTS",vm_rel)
    vp.write_text(json.dumps(verifier,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return {
      "status":"ACQUISITION_DISPATCHED","supplier_class":"npm_javascript_library",
      "capability_id":cap_id,"supplier":package,"pending_binding_path":pending_rel,
      "verification_mission_path":vm_rel,"verification_mission_id":verify_mid,
      "keywords":keywords,"acquisition_evidence_path":diag_rel
    }

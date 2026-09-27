#!/usr/bin/env python3
"""Autonomously acquire a zero-cost Python-library structured codec from PyPI."""
from __future__ import annotations
import base64,hashlib,importlib,json,pathlib,re,subprocess,sys,tempfile,urllib.parse,urllib.request,zipfile

import capability_discovery


class AutoPyPIAcquisitionFailure(RuntimeError):
    def __init__(self,code,detail=None):
        self.code=code; self.detail=detail
        super().__init__(code if detail is None else f"{code}:{detail}")


_EXTERNAL_WHEEL_CLOSURE_PROVIDER=None

def set_external_wheel_closure_provider(provider):
    global _EXTERNAL_WHEEL_CLOSURE_PROVIDER
    _EXTERNAL_WHEEL_CLOSURE_PROVIDER=provider


def _verified_runtime_platform():
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform.startswith("win") or sys.platform in {"cygwin","msys"}:
        return "windows"
    if sys.platform=="darwin":
        return "darwin"
    raise AutoPyPIAcquisitionFailure("PYPI_VERIFICATION_PLATFORM_UNSUPPORTED",sys.platform)


def _origin_mission_sha256(root,mission_path):
    root=pathlib.Path(root).resolve()
    missions_root=(root/"canonical"/"astra_runtime"/"missions").resolve()
    mission=(root/str(mission_path)).resolve()
    if mission.parent!=missions_root:
        raise AutoPyPIAcquisitionFailure("PYPI_ORIGIN_MISSION_PATH_INVALID",str(mission_path))
    if not mission.is_file():
        raise AutoPyPIAcquisitionFailure("PYPI_ORIGIN_MISSION_MISSING",str(mission_path))
    return hashlib.sha256(mission.read_bytes()).hexdigest()


COMMON_NON_CODEC_EXTENSIONS={
    ".json",".txt",".md",".markdown",".csv",".tsv",".html",".xml",
    ".png",".jpg",".jpeg",".webp",".pdf",".docx",".xlsx",
    ".zip",".gz",".tgz",".tar",".sqlite",".db",".sqlite3",
}


def _slug(value):
    out=re.sub(r"[^a-z0-9]+","-",str(value).lower()).strip("-")
    if not out:
        raise AutoPyPIAcquisitionFailure("PYPI_ACQUISITION_SLUG_EMPTY")
    return out[:80]


def _repo_paths(goal):
    text=re.sub(r"https?://[^\s)\]}>]+"," ",str(goal or ""))
    return [raw.rstrip(".,;:!?)]}") for raw in re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",text)]


def supports(goal):
    lower=str(goal or "").lower()
    if not any(x in lower for x in ("encode","serialize","serialise","pack","binary")):
        return False
    suffixes=[pathlib.Path(x).suffix.lower() for x in _repo_paths(goal)]
    return any(s and s not in COMMON_NON_CODEC_EXTENSIONS for s in suffixes)


def _candidate_pool(goal,discovery=None):
    # Federated discovery is intentionally truncated across supplier classes
    # and is suitable for routing, not for a supplier-local contract race.
    # Always refresh the supplier's own authoritative candidate surface, then
    # merge any already-known PyPI candidates and rank the union.
    fresh=(capability_discovery.search_pypi_packages(goal,limit=32).get("candidates") or [])
    inherited=[
        x for x in (discovery or {}).get("candidates",[])
        if x.get("discovery_source")=="PYPI"
    ]
    merged={}
    for cand in inherited+fresh:
        key=str(cand.get("project") or cand.get("name") or "").strip().lower()
        if not key:
            continue
        prior=merged.get(key)
        if prior is None or float(cand.get("score",0))>float(prior.get("score",0)):
            merged[key]=cand
    candidates=list(merged.values())
    viable=[]
    for cand in candidates:
        if not cand.get("zero_cost_eligible",False): continue
        if int(cand.get("required_secret_count",0))!=0: continue
        dependency_count=int(cand.get("dependency_count",0))
        if dependency_count<0 or dependency_count>24: continue
        if float(cand.get("score",0))<20: continue
        viable.append(cand)
    viable.sort(key=lambda x:(
        -float(x.get("score",0)),
        int(x.get("dependency_count",0)),
        str(x.get("name",""))
    ))
    if not viable:
        raise AutoPyPIAcquisitionFailure("NO_BOUNDED_PYPI_CANDIDATE")
    return viable[:16]


def _wheel_identity(wheel_path):
    with zipfile.ZipFile(wheel_path,"r") as z:
        metadata_names=[n for n in z.namelist() if n.endswith(".dist-info/METADATA")]
        if len(metadata_names)!=1:
            raise AutoPyPIAcquisitionFailure("PYPI_WHEEL_METADATA_FILE_NOT_UNIQUE",wheel_path.name)
        text=z.read(metadata_names[0]).decode("utf-8","replace")
    name=version=None
    for line in text.splitlines():
        if line.startswith("Name:") and name is None:
            name=line.split(":",1)[1].strip()
        elif line.startswith("Version:") and version is None:
            version=line.split(":",1)[1].strip()
        if name and version:
            break
    if not name or not version:
        raise AutoPyPIAcquisitionFailure("PYPI_WHEEL_IDENTITY_MISSING",wheel_path.name)
    return name,version


def _pypi_release_metadata(name,version,timeout_s=20):
    url="https://pypi.org/pypi/"+urllib.parse.quote(str(name),safe="")+"/"+urllib.parse.quote(str(version),safe="")+"/json"
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-PyPIDependencyClosure/1"})
    try:
        with urllib.request.urlopen(req,timeout=timeout_s) as resp:
            raw=resp.read(3000000)
        payload=json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise AutoPyPIAcquisitionFailure(
            "PYPI_DEPENDENCY_METADATA_FETCH_FAILED",
            str(name)+"=="+str(version)+":"+type(exc).__name__+":"+str(exc)
        ) from exc
    return url,payload


def _verify_wheel_against_official_metadata(wheel_path):
    name,version=_wheel_identity(wheel_path)
    metadata_url,payload=_pypi_release_metadata(name,version)
    raw=wheel_path.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    matches=[
        item for item in (payload.get("urls") or [])
        if str(item.get("filename") or "")==wheel_path.name
    ]
    if len(matches)!=1:
        raise AutoPyPIAcquisitionFailure(
            "PYPI_DEPENDENCY_WHEEL_NOT_IN_OFFICIAL_METADATA",
            name+"=="+version+":"+wheel_path.name
        )
    artifact=matches[0]
    expected=str((artifact.get("digests") or {}).get("sha256") or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}",expected) or expected!=digest:
        raise AutoPyPIAcquisitionFailure(
            "PYPI_DEPENDENCY_WHEEL_HASH_MISMATCH",
            name+"=="+version+":"+wheel_path.name
        )
    url=str(artifact.get("url") or "")
    if not url.startswith("https://"):
        raise AutoPyPIAcquisitionFailure("PYPI_DEPENDENCY_WHEEL_URL_INVALID",wheel_path.name)
    return {
      "project":name,
      "version":version,
      "filename":wheel_path.name,
      "sha256":digest,
      "bytes":len(raw),
      "url":url,
      "metadata_url":metadata_url,
    }


def _finalize_wheel_closure(wheels,target,name,version,resolver):
    if not wheels:
        raise AutoPyPIAcquisitionFailure("PYPI_WHEEL_CLOSURE_EMPTY")
    if len(wheels)>32:
        raise AutoPyPIAcquisitionFailure("PYPI_WHEEL_CLOSURE_TOO_LARGE",str(len(wheels)))
    verified=[]
    total_bytes=0
    for wheel in wheels:
        total_bytes+=wheel.stat().st_size
        if total_bytes>160000000:
            raise AutoPyPIAcquisitionFailure("PYPI_WHEEL_CLOSURE_BYTES_LIMIT")
        record=_verify_wheel_against_official_metadata(wheel)
        stable=target/wheel.name
        stable.write_bytes(wheel.read_bytes())
        record["path"]=str(stable)
        verified.append(record)
    normalized_root=re.sub(r"[-_.]+","-",name).lower()
    roots=[
        x for x in verified
        if re.sub(r"[-_.]+","-",x["project"]).lower()==normalized_root
        and x["version"]==version
    ]
    if len(roots)!=1:
        raise AutoPyPIAcquisitionFailure(
            "PYPI_ROOT_WHEEL_NOT_UNIQUE",
            json.dumps([{"project":x["project"],"version":x["version"],"filename":x["filename"]} for x in roots],sort_keys=True)
        )
    closure=sorted(
        [{k:v for k,v in x.items() if k!="path"} for x in verified],
        key=lambda x:(re.sub(r"[-_.]+","-",x["project"]).lower(),x["version"],x["filename"])
    )
    lock={
      "schema":"PROJECT_BRAIN_PYPI_WHEEL_CLOSURE_V1",
      "root_project":roots[0]["project"],
      "root_version":roots[0]["version"],
      "root_filename":roots[0]["filename"],
      "wheel_count":len(closure),
      "wheels":closure,
      "source_only_artifacts_allowed":False,
      "resolver":resolver,
      "network_required_for_install":False,
    }
    lock_sha=hashlib.sha256(json.dumps(lock,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    lock["closure_sha256"]=lock_sha
    return {"root":roots[0],"wheels":verified,"lock":lock}


def _materialize_external_wheel_closure(candidate,root,target):
    provider=_EXTERNAL_WHEEL_CLOSURE_PROVIDER
    if not callable(provider):
        return None
    response=provider(candidate=candidate,root=str(root))
    if response is None:
        return None
    artifacts=response.get("artifacts") if isinstance(response,dict) else None
    if not isinstance(artifacts,list) or not artifacts:
        raise AutoPyPIAcquisitionFailure("PYPI_EXTERNAL_WHEEL_CLOSURE_INVALID")
    if len(artifacts)>32:
        raise AutoPyPIAcquisitionFailure("PYPI_WHEEL_CLOSURE_TOO_LARGE",str(len(artifacts)))
    with tempfile.TemporaryDirectory(prefix="brain-pypi-external-closure-") as td:
        wheels=[]; total=0
        for item in artifacts:
            if not isinstance(item,dict):
                raise AutoPyPIAcquisitionFailure("PYPI_EXTERNAL_WHEEL_RECORD_INVALID")
            filename=str(item.get("filename") or "").strip()
            expected=str(item.get("sha256") or "").strip().lower()
            encoded=str(item.get("content_b64") or "")
            if pathlib.PurePath(filename).name!=filename or not filename.endswith(".whl"):
                raise AutoPyPIAcquisitionFailure("PYPI_EXTERNAL_WHEEL_FILENAME_INVALID",filename)
            if not re.fullmatch(r"[0-9a-f]{64}",expected):
                raise AutoPyPIAcquisitionFailure("PYPI_EXTERNAL_WHEEL_HASH_INVALID",filename)
            try:
                raw=base64.b64decode(encoded,validate=True)
            except Exception as exc:
                raise AutoPyPIAcquisitionFailure("PYPI_EXTERNAL_WHEEL_BASE64_INVALID",filename) from exc
            total+=len(raw)
            if total>160000000:
                raise AutoPyPIAcquisitionFailure("PYPI_WHEEL_CLOSURE_BYTES_LIMIT")
            actual=hashlib.sha256(raw).hexdigest()
            if actual!=expected:
                raise AutoPyPIAcquisitionFailure("PYPI_EXTERNAL_WHEEL_HASH_MISMATCH",filename)
            wheel=pathlib.Path(td)/filename
            wheel.write_bytes(raw); wheels.append(wheel)
        return _finalize_wheel_closure(
            wheels,target,
            str(candidate.get("project") or candidate.get("name") or ""),
            str(candidate.get("version") or ""),
            "external-content-addressed-wheel-closure",
        )


def _download_compatible_wheel_closure(candidate,root):
    name=str(candidate.get("project") or candidate.get("name") or "")
    version=str(candidate.get("version") or "")
    if not name or not version:
        raise AutoPyPIAcquisitionFailure("PYPI_CANDIDATE_METADATA_INCOMPLETE")
    target=pathlib.Path(root)/"canonical"/"astra_runtime"/"tmp"/"pypi_probe_wheels"
    target.mkdir(parents=True,exist_ok=True)
    external=_materialize_external_wheel_closure(candidate,root,target)
    if external is not None:
        return external
    with tempfile.TemporaryDirectory(prefix="brain-pypi-wheel-closure-") as td:
        proc=subprocess.run(
            [
              sys.executable,"-m","pip","download",
              "--disable-pip-version-check",
              "--only-binary=:all:",
              "--dest",td,
              f"{name}=={version}",
            ],
            cwd=root,text=True,capture_output=True,timeout=180
        )
        if proc.returncode!=0:
            raise AutoPyPIAcquisitionFailure(
                "PYPI_WHEEL_CLOSURE_RESOLUTION_FAILED",
                proc.stderr[-1800:]
            )
        wheels=sorted(pathlib.Path(td).glob("*.whl"))
        return _finalize_wheel_closure(wheels,target,name,version,"pip-download-only-binary")



def _module_candidates(wheel_path):
    out=[]
    with zipfile.ZipFile(wheel_path,"r") as z:
        names=z.namelist()
        for name in names:
            if name.endswith(".dist-info/top_level.txt"):
                raw=z.read(name).decode("utf-8","replace")
                for line in raw.splitlines():
                    mod=line.strip()
                    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",mod) and mod not in out:
                        out.append(mod)
        for name in names:
            first=name.split("/",1)[0]
            if first.endswith((".dist-info",".data")): continue
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",first) and first not in out:
                out.append(first)
            if "/" not in name and name.endswith(".py"):
                mod=name[:-3]
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",mod) and mod not in out:
                    out.append(mod)
    return out[:12]


def _resolve(module,name):
    current=module
    for part in name.split("."):
        current=getattr(current,part)
    if not callable(current): raise TypeError("not callable")
    return current


def _infer_codec_contract(candidate,wheel_closure,root):
    fixture=[{"id":1,"text":"alpha"},{"id":2,"text":"beta"}]
    root_wheel=wheel_closure["root"]
    closure_wheels=wheel_closure["wheels"]
    with tempfile.TemporaryDirectory(prefix="brain-pypi-probe-") as td:
        site=pathlib.Path(td)/"site"; site.mkdir()
        wheelhouse=pathlib.Path(td)/"wheelhouse"; wheelhouse.mkdir()
        for item in closure_wheels:
            src=pathlib.Path(item["path"])
            (wheelhouse/src.name).write_bytes(src.read_bytes())
        proc=subprocess.run(
            [
              sys.executable,"-m","pip","install",
              "--disable-pip-version-check","--quiet",
              "--no-index","--find-links",str(wheelhouse),
              "--target",str(site),
              str(wheelhouse/root_wheel["filename"]),
            ],
            cwd=root,text=True,capture_output=True,timeout=180
        )
        if proc.returncode!=0:
            raise AutoPyPIAcquisitionFailure("PYPI_PROBE_INSTALL_FAILED",proc.stderr[-1200:])

        modules=_module_candidates(root_wheel["path"])
        probe_helper=(pathlib.Path(root)/"canonical"/"runtime"/"python_codec_probe.py").resolve()
        if not probe_helper.is_file():
            raise AutoPyPIAcquisitionFailure("PYPI_PROBE_HELPER_MISSING",str(probe_helper))
        probe=subprocess.run(
            [sys.executable,str(probe_helper),str(site),json.dumps(modules)],
            cwd=root,text=True,capture_output=True,timeout=90
        )
        try:
            observed=json.loads((probe.stdout or "").strip().splitlines()[-1])
        except Exception as exc:
            raise AutoPyPIAcquisitionFailure(
                "PYPI_PROBE_RESULT_INVALID",
                (probe.stderr or probe.stdout or "")[-1200:]
            ) from exc
        if probe.returncode!=0 or observed.get("ok") is not True:
            raise AutoPyPIAcquisitionFailure(
                "NO_COMPATIBLE_PYPI_CODEC_CONTRACT",
                json.dumps(observed.get("attempts") or [],sort_keys=True)[:2500]
            )

        return {
          "schema":"PROJECT_BRAIN_PYPI_CODEC_CONTRACT_V1",
          "module":observed["module"],
          "encode_callable":observed["encode_callable"],
          "decode_callable":observed["decode_callable"],
          "encode_kwargs":observed.get("encode_kwargs") or {},
          "decode_kwargs":observed.get("decode_kwargs") or {},
          "fixture":observed["fixture"],
          "representation":observed["representation"],
          "envelope_key":observed.get("envelope_key"),
          "probe_output_sha256":observed["probe_output_sha256"],
          "probe_output_bytes":observed["probe_output_bytes"],
          "wheel_filename":root_wheel["filename"],
          "wheel_sha256":root_wheel["sha256"],
          "dependency_closure_sha256":wheel_closure["lock"]["closure_sha256"],
          "dependency_wheel_count":wheel_closure["lock"]["wheel_count"],
          "project":candidate.get("project") or candidate.get("name"),
          "version":candidate.get("version"),
          "probe_isolation":"fresh_child_python_process",
          "pair_discovery":observed.get("pair_discovery","legacy_baseline"),
        }

def dispatch(goal,mission_id,mission_path,root,discovery=None):
    root=pathlib.Path(root).resolve()
    origin_mission_sha256=_origin_mission_sha256(root,mission_path)
    if not supports(goal): raise AutoPyPIAcquisitionFailure("PYPI_CONTRACT_CLASS_UNSUPPORTED")
    candidates=_candidate_pool(goal,discovery)
    diag_rel=f"canonical/astra_runtime/evidence/{mission_id}__AUTO_PYPI_LIBRARY_ACQUISITION.json"
    diag_path=root/diag_rel; diag_path.parent.mkdir(parents=True,exist_ok=True)
    diagnostic={"schema":"PROJECT_BRAIN_AUTO_PYPI_LIBRARY_ACQUISITION_V1","mission_id":mission_id,
                "goal":goal,"status":"SUPPLIER_CONTRACT_RACE","attempts":[]}
    selected=wheel_closure=contract=None
    for candidate in candidates:
        attempt={"supplier":candidate}
        try:
            whc=_download_compatible_wheel_closure(candidate,root)
            attempt["dependency_closure"]=whc["lock"]
            ct=_infer_codec_contract(candidate,whc,root)
            attempt["contract"]=ct; attempt["status"]="CONTRACT_ACCEPTED"
            selected,wheel_closure,contract=candidate,whc,ct
            diagnostic["attempts"].append(attempt); break
        except Exception as exc:
            attempt["status"]="CONTRACT_REJECTED"; attempt["error"]=type(exc).__name__+":"+str(exc)
            diagnostic["attempts"].append(attempt)
            diag_path.write_text(json.dumps(diagnostic,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    if selected is None:
        diagnostic["status"]="NO_COMPATIBLE_CONTRACT"
        diag_path.write_text(json.dumps(diagnostic,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        raise AutoPyPIAcquisitionFailure("NO_COMPATIBLE_PYPI_LIBRARY_CONTRACT",
            json.dumps([{"name":(x.get("supplier") or {}).get("name"),"error":x.get("error")} for x in diagnostic["attempts"]],sort_keys=True)[:3000])

    root_wheel=wheel_closure["root"]
    dependency_lock=wheel_closure["lock"]
    diagnostic.update({"status":"CONTRACT_INFERRED","selected_supplier":selected,
                       "wheel":{k:v for k,v in root_wheel.items() if k!="path"},
                       "dependency_closure":dependency_lock,
                       "contract":contract})
    diag_path.write_text(json.dumps(diagnostic,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    project=str(selected.get("project") or selected.get("name")); version=str(selected.get("version")); slug=_slug(project)
    cap_id="auto.pypi."+slug
    suffixes=[pathlib.Path(x).suffix.lower() for x in _repo_paths(goal)]
    format_terms=[]
    for suffix in suffixes:
        if not suffix or suffix in COMMON_NON_CODEC_EXTENSIONS:
            continue
        token=suffix.lstrip(".")
        if token and token not in format_terms:
            format_terms.append(token)
    if len(format_terms)!=1:
        raise AutoPyPIAcquisitionFailure(
            "PYPI_OUTPUT_FORMAT_AMBIGUOUS",
            json.dumps(format_terms,sort_keys=True)
        )
    keywords=[]
    for value in capability_discovery.effect_queries(goal)+format_terms+[project]:
        token=str(value).lower()
        if token and token not in keywords: keywords.append(token)
    provides=["structured.binary.encode"]+["structured.binary.encode."+x for x in format_terms]
    entry={
      "provides":provides,"requires":["json.file.available"],"keywords":keywords,"cost":1,"platforms":[_verified_runtime_platform()],
      "limitations":["Automatically acquired from a hash-pinned wheel-only PyPI dependency closure.",
                     "Initial generic contract class is structured JSON value to binary bytes with semantic round-trip decoding."],
      "adapter_module":"python_library_codec","entrypoint":"run",
      "action_template":{"type":"invoke_capability","args":{
          "capability_id":cap_id,"module":contract["module"],"encode_callable":contract["encode_callable"],
          "decode_callable":contract["decode_callable"],"encode_kwargs":contract["encode_kwargs"],
          "decode_kwargs":contract["decode_kwargs"],"envelope_key":contract.get("envelope_key"),
          "json_path":"${input.json_path}","output_path":"${input.output_path}"
      },"expect":{"type":"field_equals","field":"output_verified","value":True}},
      "source":{"type":"pypi","project":project,"version":version,"metadata_url":str(selected.get("metadata_url")),
                "wheel_filename":root_wheel["filename"],"wheel_sha256":root_wheel["sha256"],
                "dependency_closure":dependency_lock,"license":selected.get("license")},
      "incremental_spend_usd":0,"status":"BOUND_PENDING_INDEPENDENT_VERIFICATION",
      "autogenerated":{"schema":"PROJECT_BRAIN_AUTO_PYPI_CODEC_BINDING_V1","origin_mission_id":mission_id,
                       "origin_goal":goal,"supplier_score":selected.get("score"),"contract":contract}
    }
    fingerprint=hashlib.sha256((mission_id+"\n"+cap_id+"\n"+json.dumps(contract,sort_keys=True)).encode()).hexdigest()[:12]
    pending_rel=f"canonical/astra_runtime/pending_bindings/{mission_id}__{slug}__{fingerprint}.json"
    verify_rel=f"canonical/astra_runtime/evidence/{mission_id}__{slug}__{fingerprint}__AUTO_VERIFY.json"
    verify_mid="ASTRA-AUTO-VERIFY-PYPI-"+slug.upper()+"-"+fingerprint.upper()
    pending={"schema":"PROJECT_BRAIN_PENDING_AUTO_BINDING_V1","capability_id":cap_id,"effect":provides[0],"goal":goal,
             "origin_mission_id":mission_id,"origin_mission_path":mission_path,
      "origin_mission_sha256_at_acquisition":origin_mission_sha256,"selected_supplier":selected,
             "contract":contract,"verification_fixture":contract["fixture"],"registry_entry":entry,
             "verification_mission_id":verify_mid,"verification_result_path":verify_rel,
             "status":"PENDING_INDEPENDENT_VERIFICATION"}
    pp=root/pending_rel; pp.parent.mkdir(parents=True,exist_ok=True)
    pp.write_text(json.dumps(pending,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    verifier={"schema":"PROJECT_BRAIN_ASTRA_RUNTIME_MISSION_V1","mission_id":verify_mid,
      "purpose":"Fresh semantic round-trip verification and promotion of an automatically synthesized PyPI Python-library capability binding.",
      "goal":"Verify the pending Python-library codec effect in a fresh process, promote only after semantic round-trip equality, then replay the originating mission.",
      "steps":[
        {"id":"verify-pending-python-codec","adapter":"shell",
         "command":f"set -euo pipefail\npython canonical/runtime/verify_pending_cli_binding.py {pending_rel} {verify_rel}",
         "verify":{"type":"stdout_contains","text":"PENDING_PYPI_BINDING_EFFECT_VERIFIED"}},
        {"id":"promote-and-replay","adapter":"shell",
         "command":f"set -euo pipefail\npython canonical/runtime/promote_pending_binding.py {pending_rel} {verify_rel}",
         "verify":{"type":"stdout_contains","text":"PENDING_CAPABILITY_PROMOTED"}}
      ],
      "constraints":{"incremental_spend_usd":0,"model_controller_required":False,
                     "fresh_verification_invocation_required":True,"allow_registry_mutation":True,
                     "auto_generated_from_mission":mission_id,"supplier_class":"pypi_python_library"}}
    vm_rel=f"canonical/astra_runtime/missions/{verify_mid.replace('-','_')}.json"
    vp=root/vm_rel
    if vp.exists(): raise AutoPyPIAcquisitionFailure("VERIFICATION_MISSION_ALREADY_EXISTS",vm_rel)
    vp.write_text(json.dumps(verifier,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return {"status":"ACQUISITION_DISPATCHED","supplier_class":"pypi_python_library","capability_id":cap_id,
            "supplier":project,"pending_binding_path":pending_rel,"verification_mission_path":vm_rel,
            "verification_mission_id":verify_mid,"keywords":keywords,"acquisition_evidence_path":diag_rel}

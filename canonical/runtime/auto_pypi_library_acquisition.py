#!/usr/bin/env python3
"""Autonomously acquire a zero-cost Python-library structured codec from PyPI."""
from __future__ import annotations
import hashlib,importlib,json,pathlib,re,subprocess,sys,tempfile,zipfile

import capability_discovery


class AutoPyPIAcquisitionFailure(RuntimeError):
    def __init__(self,code,detail=None):
        self.code=code; self.detail=detail
        super().__init__(code if detail is None else f"{code}:{detail}")


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
    if discovery is None:
        candidates=(capability_discovery.search_pypi_packages(goal,limit=16).get("candidates") or [])
    else:
        candidates=[x for x in discovery.get("candidates",[]) if x.get("discovery_source")=="PYPI"]
        if not candidates:
            candidates=(capability_discovery.search_pypi_packages(goal,limit=16).get("candidates") or [])
    viable=[]
    for cand in candidates:
        if not cand.get("zero_cost_eligible",False): continue
        if int(cand.get("required_secret_count",0))!=0: continue
        if int(cand.get("dependency_count",0))!=0: continue
        if float(cand.get("score",0))<20: continue
        viable.append(cand)
    viable.sort(key=lambda x:(-float(x.get("score",0)),str(x.get("name",""))))
    if not viable:
        raise AutoPyPIAcquisitionFailure("NO_ZERO_DEPENDENCY_PYPI_CANDIDATE")
    return viable[:12]


def _download_compatible_wheel(candidate,root):
    name=str(candidate.get("project") or candidate.get("name") or "")
    version=str(candidate.get("version") or "")
    if not name or not version:
        raise AutoPyPIAcquisitionFailure("PYPI_CANDIDATE_METADATA_INCOMPLETE")
    with tempfile.TemporaryDirectory(prefix="brain-pypi-wheel-") as td:
        proc=subprocess.run(
            [sys.executable,"-m","pip","download","--disable-pip-version-check","--no-deps",
             "--only-binary=:all:","--dest",td,f"{name}=={version}"],
            cwd=root,text=True,capture_output=True,timeout=120
        )
        if proc.returncode!=0:
            raise AutoPyPIAcquisitionFailure("PYPI_WHEEL_DOWNLOAD_FAILED",proc.stderr[-1200:])
        wheels=list(pathlib.Path(td).glob("*.whl"))
        if len(wheels)!=1:
            raise AutoPyPIAcquisitionFailure("PYPI_COMPATIBLE_WHEEL_NOT_UNIQUE",str(len(wheels)))
        wheel=wheels[0]
        raw=wheel.read_bytes()
        digest=hashlib.sha256(raw).hexdigest()
        metadata_matches=[x for x in candidate.get("wheels") or [] if x.get("filename")==wheel.name and x.get("sha256")==digest]
        if len(metadata_matches)!=1:
            raise AutoPyPIAcquisitionFailure("PYPI_WHEEL_METADATA_HASH_MISMATCH",wheel.name)
        target=pathlib.Path(root)/"canonical"/"astra_runtime"/"tmp"/"pypi_probe_wheels"
        target.mkdir(parents=True,exist_ok=True)
        stable=target/wheel.name
        stable.write_bytes(raw)
        return {"path":str(stable),"filename":wheel.name,"sha256":digest,"bytes":len(raw),"url":metadata_matches[0].get("url")}


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


def _infer_codec_contract(candidate,wheel,root):
    pairs=[("packb","unpackb"),("dumps","loads"),("encode","decode"),("serialize","deserialize")]
    fixture=[{"id":1,"text":"alpha"},{"id":2,"text":"beta"}]
    attempts=[]
    with tempfile.TemporaryDirectory(prefix="brain-pypi-probe-") as td:
        site=pathlib.Path(td)/"site"; site.mkdir()
        proc=subprocess.run(
            [sys.executable,"-m","pip","install","--disable-pip-version-check","--quiet","--no-deps","--target",str(site),wheel["path"]],
            cwd=root,text=True,capture_output=True,timeout=120
        )
        if proc.returncode!=0:
            raise AutoPyPIAcquisitionFailure("PYPI_PROBE_INSTALL_FAILED",proc.stderr[-1200:])
        modules=_module_candidates(wheel["path"])
        sys.path.insert(0,str(site))
        try:
            for module_name in modules:
                for key in list(sys.modules):
                    if key==module_name or key.startswith(module_name+"."): sys.modules.pop(key,None)
                try:
                    module=importlib.import_module(module_name)
                except Exception as exc:
                    attempts.append({"module":module_name,"status":"IMPORT_FAILED","error":type(exc).__name__}); continue
                for enc_name,dec_name in pairs:
                    try:
                        enc=_resolve(module,enc_name); dec=_resolve(module,dec_name)
                    except Exception:
                        continue
                    for enc_kwargs in ({},{"use_bin_type":True}):
                        try: payload=enc(fixture,**enc_kwargs)
                        except Exception: continue
                        if isinstance(payload,memoryview): payload=payload.tobytes()
                        if isinstance(payload,bytearray): payload=bytes(payload)
                        if not isinstance(payload,bytes) or not payload: continue
                        for dec_kwargs in ({},{"raw":False}):
                            try: observed=dec(payload,**dec_kwargs)
                            except Exception: continue
                            if observed==fixture:
                                return {
                                  "schema":"PROJECT_BRAIN_PYPI_CODEC_CONTRACT_V1",
                                  "module":module_name,"encode_callable":enc_name,"decode_callable":dec_name,
                                  "encode_kwargs":enc_kwargs,"decode_kwargs":dec_kwargs,"fixture":fixture,
                                  "probe_output_sha256":hashlib.sha256(payload).hexdigest(),
                                  "probe_output_bytes":len(payload),"wheel_filename":wheel["filename"],
                                  "wheel_sha256":wheel["sha256"],"project":candidate.get("project") or candidate.get("name"),
                                  "version":candidate.get("version"),
                                }
                    attempts.append({"module":module_name,"encode":enc_name,"decode":dec_name,"status":"ROUNDTRIP_REJECTED"})
        finally:
            try: sys.path.remove(str(site))
            except ValueError: pass
    raise AutoPyPIAcquisitionFailure("NO_COMPATIBLE_PYPI_CODEC_CONTRACT",json.dumps(attempts,sort_keys=True)[:2500])


def dispatch(goal,mission_id,mission_path,root,discovery=None):
    root=pathlib.Path(root).resolve()
    if not supports(goal): raise AutoPyPIAcquisitionFailure("PYPI_CONTRACT_CLASS_UNSUPPORTED")
    candidates=_candidate_pool(goal,discovery)
    diag_rel=f"canonical/astra_runtime/evidence/{mission_id}__AUTO_PYPI_LIBRARY_ACQUISITION.json"
    diag_path=root/diag_rel; diag_path.parent.mkdir(parents=True,exist_ok=True)
    diagnostic={"schema":"PROJECT_BRAIN_AUTO_PYPI_LIBRARY_ACQUISITION_V1","mission_id":mission_id,
                "goal":goal,"status":"SUPPLIER_CONTRACT_RACE","attempts":[]}
    selected=wheel=contract=None
    for candidate in candidates:
        attempt={"supplier":candidate}
        try:
            wh=_download_compatible_wheel(candidate,root)
            attempt["wheel"]={k:v for k,v in wh.items() if k!="path"}
            ct=_infer_codec_contract(candidate,wh,root)
            attempt["contract"]=ct; attempt["status"]="CONTRACT_ACCEPTED"
            selected,wheel,contract=candidate,wh,ct
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

    diagnostic.update({"status":"CONTRACT_INFERRED","selected_supplier":selected,
                       "wheel":{k:v for k,v in wheel.items() if k!="path"},"contract":contract})
    diag_path.write_text(json.dumps(diagnostic,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    project=str(selected.get("project") or selected.get("name")); version=str(selected.get("version")); slug=_slug(project)
    cap_id="auto.pypi."+slug
    suffixes=[pathlib.Path(x).suffix.lower().lstrip(".") for x in _repo_paths(goal)]
    format_terms=[x for x in suffixes if x]
    keywords=[]
    for value in capability_discovery.effect_queries(goal)+format_terms+[project]:
        token=str(value).lower()
        if token and token not in keywords: keywords.append(token)
    provides=["structured.binary.encode"]+["structured.binary.encode."+x for x in format_terms]
    entry={
      "provides":provides,"requires":["json.file.available"],"keywords":keywords,"cost":1,"platforms":["linux"],
      "limitations":["Automatically acquired from a hash-pinned dependency-free PyPI wheel.",
                     "Initial generic contract class is structured JSON value to binary bytes with semantic round-trip decoding."],
      "adapter_module":"python_library_codec","entrypoint":"run",
      "action_template":{"type":"invoke_capability","args":{
          "capability_id":cap_id,"module":contract["module"],"encode_callable":contract["encode_callable"],
          "decode_callable":contract["decode_callable"],"encode_kwargs":contract["encode_kwargs"],
          "decode_kwargs":contract["decode_kwargs"],"json_path":"${input.json_path}","output_path":"${input.output_path}"
      },"expect":{"type":"field_equals","field":"output_verified","value":True}},
      "source":{"type":"pypi","project":project,"version":version,"metadata_url":str(selected.get("metadata_url")),
                "wheel_filename":wheel["filename"],"wheel_sha256":wheel["sha256"],"license":selected.get("license")},
      "incremental_spend_usd":0,"status":"BOUND_PENDING_INDEPENDENT_VERIFICATION",
      "autogenerated":{"schema":"PROJECT_BRAIN_AUTO_PYPI_CODEC_BINDING_V1","origin_mission_id":mission_id,
                       "origin_goal":goal,"supplier_score":selected.get("score"),"contract":contract}
    }
    fingerprint=hashlib.sha256((mission_id+"\n"+cap_id+"\n"+json.dumps(contract,sort_keys=True)).encode()).hexdigest()[:12]
    pending_rel=f"canonical/astra_runtime/pending_bindings/{mission_id}__{slug}__{fingerprint}.json"
    verify_rel=f"canonical/astra_runtime/evidence/{mission_id}__{slug}__{fingerprint}__AUTO_VERIFY.json"
    verify_mid="ASTRA-AUTO-VERIFY-PYPI-"+slug.upper()+"-"+fingerprint.upper()
    pending={"schema":"PROJECT_BRAIN_PENDING_AUTO_BINDING_V1","capability_id":cap_id,"effect":provides[0],"goal":goal,
             "origin_mission_id":mission_id,"origin_mission_path":mission_path,"selected_supplier":selected,
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

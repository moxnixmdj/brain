#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,re,subprocess,tempfile,urllib.parse,urllib.request

class AutoGitHubSourceAcquisitionFailure(RuntimeError):
    def __init__(self,code,detail=None):
        self.code=code; self.detail=detail
        super().__init__(code if detail is None else f"{code}:{detail}")

def supports(goal):
    lower=str(goal or "").lower()
    explicit=("github-hosted source" in lower or "github source library" in lower or "github-hosted python source" in lower)
    effect=any(x in lower for x in ("encode","serialize","pack"))
    return bool(explicit and effect)

def _repo_paths(text):
    return re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",str(text or ""))

def _format(goal):
    common={"json","txt","md","csv","html","xml","png","pdf","docx","xlsx","zip","tar","db"}
    for raw in _repo_paths(goal):
        s=pathlib.PurePosixPath(raw.rstrip(".,;:!?)]}")).suffix.lower().lstrip(".")
        if s and s not in common: return s
    raise AutoGitHubSourceAcquisitionFailure("GITHUB_SOURCE_OUTPUT_FORMAT_REQUIRED")

def _get(url,limit=5_000_000,timeout=20):
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-GitHubSourceAcquisition/1","Accept":"application/vnd.github+json"})
    with urllib.request.urlopen(req,timeout=timeout) as resp: return resp.read(limit)

def _json(url,limit=5_000_000): return json.loads(_get(url,limit).decode("utf-8"))

def _git_blob_sha1(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _search(goal,limit=20):
    fmt=_format(goal)
    q=f"{fmt} encode decode language:Python"
    url="https://api.github.com/search/repositories?"+urllib.parse.urlencode({"q":q,"sort":"stars","order":"desc","per_page":min(max(limit,1),30)})
    payload=_json(url)
    out=[]
    for item in payload.get("items") or []:
        full=str(item.get("full_name") or "")
        if not full or item.get("archived") or item.get("fork"): continue
        blob=(str(item.get("name") or "")+" "+str(item.get("description") or "")).lower()
        nfmt=re.sub(r"[-_.]+","",fmt)
        normalized=re.sub(r"[-_.]+","",blob)
        score=(160 if str(item.get("name") or "").lower().startswith(fmt) else 0)+(80 if nfmt in normalized else 0)+min(int(item.get("stargazers_count") or 0),50)
        if score<=0: continue
        out.append({"repo":full,"default_branch":str(item.get("default_branch") or "main"),"description":str(item.get("description") or ""),"score":score,"html_url":str(item.get("html_url") or ""),"license":(item.get("license") or {}).get("spdx_id")})
    out.sort(key=lambda x:(-x["score"],x["repo"]))
    return out[:limit]

def _materialize_candidate(cand,root):
    repo=cand["repo"]; branch=cand["default_branch"]
    commit=_json("https://api.github.com/repos/"+repo+"/commits/"+urllib.parse.quote(branch,safe=""),limit=3_000_000)
    sha=str(commit.get("sha") or "")
    if not re.fullmatch(r"[0-9a-f]{40}",sha): raise AutoGitHubSourceAcquisitionFailure("GITHUB_SOURCE_COMMIT_SHA_INVALID",repo)
    tree=_json("https://api.github.com/repos/"+repo+"/git/trees/"+sha+"?recursive=1",limit=8_000_000)
    if tree.get("truncated") is True: raise AutoGitHubSourceAcquisitionFailure("GITHUB_SOURCE_TREE_TRUNCATED",repo)
    py=[x for x in tree.get("tree") or [] if x.get("type")=="blob" and str(x.get("path") or "").endswith(".py") and int(x.get("size") or 0)<=120000]
    py=[x for x in py if not any(seg in str(x.get("path") or "").lower() for seg in ("/test","tests/","/vendor","vendored/","site-packages/"))]
    if not py or len(py)>40: raise AutoGitHubSourceAcquisitionFailure("GITHUB_SOURCE_PYTHON_SURFACE_INVALID",repo)
    total=sum(int(x.get("size") or 0) for x in py)
    if total>800000: raise AutoGitHubSourceAcquisitionFailure("GITHUB_SOURCE_BYTES_LIMIT",str(total))
    stable=pathlib.Path(root)/"canonical"/"astra_runtime"/"tmp"/"github_source_probe"/(re.sub(r"[^A-Za-z0-9_.-]+","_",repo)+"__"+sha[:12])
    if stable.exists():
        import shutil; shutil.rmtree(stable)
    stable.mkdir(parents=True,exist_ok=True)
    records=[]; modules=[]
    for item in py:
        path=str(item["path"]); raw_url="https://raw.githubusercontent.com/"+repo+"/"+sha+"/"+path
        raw=_get(raw_url,limit=150000)
        if len(raw)!=int(item.get("size") or len(raw)): raise AutoGitHubSourceAcquisitionFailure("GITHUB_SOURCE_SIZE_MISMATCH",path)
        if _git_blob_sha1(raw)!=str(item.get("sha") or ""): raise AutoGitHubSourceAcquisitionFailure("GITHUB_SOURCE_BLOB_SHA1_MISMATCH",path)
        dst=stable/path; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(raw)
        records.append({"path":path,"git_blob_sha1":str(item.get("sha")),"sha256":hashlib.sha256(raw).hexdigest(),"size":len(raw),"raw_url":raw_url})
        if "/" not in path and path.endswith(".py") and pathlib.Path(path).stem!="__init__":
            modules.append(pathlib.Path(path).stem)
    return {"repo":repo,"commit_sha":sha,"source_root":stable,"files":records,"modules":modules[:20],"license":cand.get("license"),"html_url":cand.get("html_url")}

def _probe(mat,root):
    fixture=[1,2,3,5,8]
    runner=pathlib.Path(root)/"canonical"/"runtime"/"github_source_codec_runner.py"
    p=subprocess.run(["python",str(runner)],input=json.dumps({"mode":"probe","source_root":str(mat["source_root"]),"modules":mat["modules"],"fixture":fixture}),text=True,capture_output=True,cwd=root,timeout=60)
    if p.returncode!=0: raise AutoGitHubSourceAcquisitionFailure("GITHUB_SOURCE_PROBE_FAILED",p.stderr[-1200:])
    try: out=json.loads(p.stdout)
    except Exception as exc: raise AutoGitHubSourceAcquisitionFailure("GITHUB_SOURCE_PROBE_JSON_INVALID") from exc
    if out.get("ok") is not True: raise AutoGitHubSourceAcquisitionFailure("NO_COMPATIBLE_GITHUB_SOURCE_CODEC_CONTRACT",json.dumps(out)[:1600])
    return {"schema":"PROJECT_BRAIN_GITHUB_SOURCE_CODEC_CONTRACT_V1","module":out["module"],"encode_callable":out["encode_callable"],"decode_callable":out["decode_callable"],"fixture":fixture,"probe_output_bytes":out.get("probe_output_bytes")}

def dispatch(goal,mission_id,mission_path,root,discovery=None):
    root=pathlib.Path(root).resolve()
    if not supports(goal): raise AutoGitHubSourceAcquisitionFailure("GITHUB_SOURCE_CONTRACT_CLASS_UNSUPPORTED")
    candidates=_search(goal,20)
    diag_rel=f"canonical/astra_runtime/evidence/{mission_id}__AUTO_GITHUB_SOURCE_ACQUISITION.json"
    diag=root/diag_rel; diag.parent.mkdir(parents=True,exist_ok=True)
    evidence={"schema":"PROJECT_BRAIN_AUTO_GITHUB_SOURCE_ACQUISITION_V1","mission_id":mission_id,"goal":goal,"status":"SUPPLIER_CONTRACT_RACE","attempts":[]}
    selected=mat=contract=None
    for cand in candidates[:12]:
        att={"supplier":cand}
        try:
            m=_materialize_candidate(cand,root); ct=_probe(m,root)
            att["status"]="CONTRACT_ACCEPTED"; att["contract"]=ct; att["commit_sha"]=m["commit_sha"]
            evidence["attempts"].append(att); selected,mat,contract=cand,m,ct; break
        except Exception as exc:
            att["status"]="CONTRACT_REJECTED"; att["error"]=type(exc).__name__+":"+str(exc); evidence["attempts"].append(att)
            diag.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    if selected is None:
        evidence["status"]="NO_COMPATIBLE_CONTRACT"; diag.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        raise AutoGitHubSourceAcquisitionFailure("NO_COMPATIBLE_GITHUB_SOURCE_CONTRACT",json.dumps([{"repo":(x.get("supplier") or {}).get("repo"),"error":x.get("error")} for x in evidence["attempts"]],sort_keys=True)[:3500])
    evidence.update({"status":"CONTRACT_INFERRED","selected_supplier":selected,"commit_sha":mat["commit_sha"],"contract":contract}); diag.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    fmt=_format(goal); slug=re.sub(r"[^a-z0-9]+","-",selected["repo"].lower()).strip("-")[:90]; cap_id="auto.github."+slug
    source={"type":"github_source","repository":selected["repo"],"commit_sha":mat["commit_sha"],"html_url":selected["html_url"],"license":mat.get("license"),"files":mat["files"],"dependency_count":0}
    entry={"provides":["structured.binary.encode","structured.binary.encode."+fmt],"requires":["json.file.available","python.runtime.available"],"keywords":["encode","github","source",fmt,selected["repo"].lower()],"cost":1,"platforms":["linux"],"incremental_spend_usd":0,"limitations":["Automatically acquired from pinned public GitHub Python source.","No build/install hooks or third-party dependencies are executed by this supplier class."],"adapter_module":"github_source_codec","entrypoint":"run","action_template":{"type":"invoke_capability","args":{"capability_id":cap_id,"module":contract["module"],"encode_callable":contract["encode_callable"],"decode_callable":contract["decode_callable"],"json_path":"${input.json_path}","output_path":"${input.output_path}"},"expect":{"type":"field_equals","field":"output_verified","value":True}},"source":source,"status":"BOUND_PENDING_INDEPENDENT_VERIFICATION","autogenerated":{"schema":"PROJECT_BRAIN_AUTO_GITHUB_SOURCE_CODEC_BINDING_V1","origin_mission_id":mission_id,"origin_goal":goal,"contract":contract}}
    fingerprint=hashlib.sha256((mission_id+"\n"+cap_id+"\n"+json.dumps(contract,sort_keys=True)).encode()).hexdigest()[:12]
    pending_rel=f"canonical/astra_runtime/pending_bindings/{mission_id}__{slug}__{fingerprint}.json"; verify_rel=f"canonical/astra_runtime/evidence/{mission_id}__{slug}__{fingerprint}__AUTO_VERIFY.json"; verify_mid="ASTRA-AUTO-VERIFY-GITHUB-"+re.sub(r"[^A-Za-z0-9]+","-",slug).upper()+"-"+fingerprint.upper()
    pending={"schema":"PROJECT_BRAIN_PENDING_AUTO_BINDING_V1","capability_id":cap_id,"effect":"structured.binary.encode","goal":goal,"origin_mission_id":mission_id,"origin_mission_path":mission_path,"selected_supplier":selected,"contract":contract,"verification_fixture":contract["fixture"],"registry_entry":entry,"verification_mission_id":verify_mid,"verification_result_path":verify_rel,"status":"PENDING_INDEPENDENT_VERIFICATION"}
    pp=root/pending_rel; pp.parent.mkdir(parents=True,exist_ok=True); pp.write_text(json.dumps(pending,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    verifier={"schema":"PROJECT_BRAIN_ASTRA_RUNTIME_MISSION_V1","mission_id":verify_mid,"purpose":"Fresh-process semantic verification and promotion of an automatically synthesized GitHub-source Python codec binding.","goal":"Verify the pending pinned GitHub-source codec in fresh Python processes, promote only after exact semantic equality, then replay the originating mission.","steps":[{"id":"verify-pending-github-source-codec","adapter":"shell","command":f"set -euo pipefail\npython canonical/runtime/verify_pending_cli_binding.py {pending_rel} {verify_rel}","verify":{"type":"stdout_contains","text":"PENDING_GITHUB_SOURCE_BINDING_EFFECT_VERIFIED"}},{"id":"promote-and-replay","adapter":"shell","command":f"set -euo pipefail\npython canonical/runtime/promote_pending_binding.py {pending_rel} {verify_rel}","verify":{"type":"stdout_contains","text":"PENDING_CAPABILITY_PROMOTED"}}],"constraints":{"incremental_spend_usd":0,"model_controller_required":False,"fresh_verification_invocation_required":True,"allow_registry_mutation":True,"auto_generated_from_mission":mission_id,"supplier_class":"github_source_python"}}
    vm_rel=f"canonical/astra_runtime/missions/{verify_mid.replace('-','_')}.json"; vp=root/vm_rel
    if vp.exists(): raise AutoGitHubSourceAcquisitionFailure("VERIFICATION_MISSION_ALREADY_EXISTS",vm_rel)
    vp.write_text(json.dumps(verifier,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return {"status":"ACQUISITION_DISPATCHED","supplier_class":"github_source_python","capability_id":cap_id,"supplier":selected["repo"],"pending_binding_path":pending_rel,"verification_mission_path":vm_rel,"verification_mission_id":verify_mid,"keywords":["github","source",fmt],"acquisition_evidence_path":diag_rel}

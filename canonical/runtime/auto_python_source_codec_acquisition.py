#!/usr/bin/env python3
"""Acquire a Python structured-codec capability from a content-addressed source tree.

Safety boundary:
- no setup.py / pyproject build hooks are executed;
- only bounded UTF-8 .py files under one top-level import package are materialized;
- every file is Git-blob verified before materialization;
- contract inference happens in a fresh child Python process;
- acquisition yields only a pending binding, never self-promotion.
"""
from __future__ import annotations
import hashlib,json,pathlib,re,subprocess,sys,tempfile

class AutoPythonSourceCodecFailure(RuntimeError):
    def __init__(self,code,detail=None):
        self.code=code; self.detail=detail
        super().__init__(code if detail is None else f"{code}:{detail}")

_EXTERNAL_SOURCE_TREE_PROVIDER=None

def set_external_source_tree_provider(provider):
    global _EXTERNAL_SOURCE_TREE_PROVIDER
    _EXTERNAL_SOURCE_TREE_PROVIDER=provider

def supports(goal):
    lower=str(goal or "").lower()
    return any(x in lower for x in ("encode","serialize","serialise","pack","binary"))

def _git_blob_sha(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

COMMON_NON_CODEC_EXTENSIONS={
    ".json",".txt",".md",".markdown",".csv",".tsv",".html",".xml",
    ".png",".jpg",".jpeg",".webp",".pdf",".docx",".xlsx",
    ".zip",".gz",".tgz",".tar",".sqlite",".db",".sqlite3",
}

def _slug(value):
    out=re.sub(r"[^a-z0-9]+","-",str(value).lower()).strip("-")
    return out[:80] or "source"

def _repo_paths(goal):
    text=re.sub(r"https?://[^\\s)\\]}>]+"," ",str(goal or ""))
    return [raw.rstrip(".,;:!?)]}") for raw in re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",text)]

def _format_terms(goal):
    suffixes=[pathlib.Path(x).suffix.lower() for x in _repo_paths(goal)]
    out=[]
    for suffix in suffixes:
        if not suffix or suffix in COMMON_NON_CODEC_EXTENSIONS:
            continue
        token=suffix.lstrip(".")
        if token and token not in out:
            out.append(token)
    if len(out)!=1:
        raise AutoPythonSourceCodecFailure(
            "SOURCE_OUTPUT_FORMAT_AMBIGUOUS",json.dumps(out,sort_keys=True)
        )
    return out

def _safe_rel(raw):
    text=str(raw or "").strip().replace("\\","/")
    p=pathlib.PurePosixPath(text)
    if not text or p.is_absolute() or ".." in p.parts:
        raise AutoPythonSourceCodecFailure("SOURCE_TREE_PATH_INVALID",text)
    if p.suffix!=".py":
        raise AutoPythonSourceCodecFailure("SOURCE_TREE_NON_PYTHON_FILE",text)
    if len(p.parts)<2:
        raise AutoPythonSourceCodecFailure("SOURCE_TREE_TOP_LEVEL_MODULE_UNSUPPORTED",text)
    return p

def _materialize(tree,destination):
    if not isinstance(tree,dict) or tree.get("schema")!="PROJECT_BRAIN_EXTERNAL_SOURCE_TREE_V1":
        raise AutoPythonSourceCodecFailure("SOURCE_TREE_SCHEMA_INVALID")
    files=tree.get("files")
    if not isinstance(files,list) or not files or len(files)>128:
        raise AutoPythonSourceCodecFailure("SOURCE_TREE_FILE_COUNT_INVALID")
    repository=str(tree.get("repository") or "").strip()
    revision=str(tree.get("revision") or "").strip()
    if not repository or not re.fullmatch(r"[0-9a-f]{40}",revision):
        raise AutoPythonSourceCodecFailure("SOURCE_TREE_IDENTITY_INVALID")
    total=0; top_levels=set(); records=[]
    destination=pathlib.Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    for item in files:
        if not isinstance(item,dict):
            raise AutoPythonSourceCodecFailure("SOURCE_TREE_RECORD_INVALID")
        rel=_safe_rel(item.get("path"))
        expected=str(item.get("git_blob_sha") or "").strip().lower()
        if not re.fullmatch(r"[0-9a-f]{40}",expected):
            raise AutoPythonSourceCodecFailure("SOURCE_TREE_GIT_BLOB_INVALID",str(rel))
        content=item.get("content")
        if not isinstance(content,str):
            raise AutoPythonSourceCodecFailure("SOURCE_TREE_CONTENT_INVALID",str(rel))
        raw=content.encode("utf-8")
        total+=len(raw)
        if total>2_000_000:
            raise AutoPythonSourceCodecFailure("SOURCE_TREE_BYTES_LIMIT")
        actual=_git_blob_sha(raw)
        if actual!=expected:
            raise AutoPythonSourceCodecFailure("SOURCE_TREE_GIT_BLOB_MISMATCH",str(rel))
        top_levels.add(rel.parts[0])
        out=(destination/pathlib.Path(*rel.parts)).resolve()
        root=destination.resolve()
        if root not in out.parents:
            raise AutoPythonSourceCodecFailure("SOURCE_TREE_PATH_ESCAPE",str(rel))
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_bytes(raw)
        records.append({"path":rel.as_posix(),"git_blob_sha":actual,"bytes":len(raw)})
    if len(top_levels)!=1:
        raise AutoPythonSourceCodecFailure("SOURCE_TREE_IMPORT_ROOT_NOT_UNIQUE",json.dumps(sorted(top_levels)))
    package=next(iter(top_levels))
    init=destination/package/"__init__.py"
    if not init.is_file():
        raise AutoPythonSourceCodecFailure("SOURCE_TREE_PACKAGE_INIT_MISSING",package)
    manifest={
      "schema":"PROJECT_BRAIN_CONTENT_ADDRESSED_PYTHON_SOURCE_TREE_V1",
      "repository":repository,"revision":revision,"package":package,
      "files":sorted(records,key=lambda x:x["path"]),"total_bytes":total,
    }
    manifest["tree_sha256"]=hashlib.sha256(
        json.dumps(manifest,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()
    return manifest

def _origin_mission_sha256(root,mission_path):
    root=pathlib.Path(root).resolve()
    missions=(root/"canonical"/"astra_runtime"/"missions").resolve()
    mission=(root/str(mission_path)).resolve()
    if mission.parent!=missions or not mission.is_file():
        raise AutoPythonSourceCodecFailure("SOURCE_ORIGIN_MISSION_INVALID",str(mission_path))
    return hashlib.sha256(mission.read_bytes()).hexdigest()

def _write_generated_verification_mission(root,vm_rel,verifier,origin_mission_id):
    root=pathlib.Path(root).resolve()
    vp=root/vm_rel
    encoded=json.dumps(verifier,indent=2,sort_keys=True)+"\n"
    if not vp.exists():
        vp.parent.mkdir(parents=True,exist_ok=True)
        vp.write_text(encoded,encoding="utf-8")
        return "CREATED"

    try:
        existing=json.loads(vp.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AutoPythonSourceCodecFailure("VERIFICATION_MISSION_EXISTING_INVALID",vm_rel) from exc
    if existing==verifier:
        return "REUSED_IDENTICAL"
    constraints=existing.get("constraints") if isinstance(existing,dict) else None
    if (
        not isinstance(existing,dict)
        or existing.get("schema")!="PROJECT_BRAIN_ASTRA_RUNTIME_MISSION_V1"
        or existing.get("mission_id")!=verifier.get("mission_id")
        or not isinstance(constraints,dict)
        or constraints.get("auto_generated_from_mission")!=origin_mission_id
    ):
        raise AutoPythonSourceCodecFailure("VERIFICATION_MISSION_AUTHORITY_CONFLICT",vm_rel)

    state_path=root/"canonical"/"astra_runtime"/"state"/(str(verifier.get("mission_id"))+".json")
    prior_status=None
    if state_path.is_file():
        try:
            prior_state=json.loads(state_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise AutoPythonSourceCodecFailure("VERIFICATION_MISSION_STATE_INVALID",str(state_path)) from exc
        prior_status=str(prior_state.get("status") or "")
        if prior_status!="BLOCKED":
            raise AutoPythonSourceCodecFailure(
                "VERIFICATION_MISSION_NONBLOCKED_CONFLICT",
                str(prior_status or "UNKNOWN")
            )

    old_raw=vp.read_bytes()
    old_sha=hashlib.sha256(old_raw).hexdigest()
    new_raw=encoded.encode("utf-8")
    new_sha=hashlib.sha256(new_raw).hexdigest()
    vp.write_bytes(new_raw)
    evidence_path=root/"canonical"/"astra_runtime"/"evidence"/(
        str(verifier.get("mission_id"))+"__GENERATED_MISSION_RECOVERY.json"
    )
    evidence_path.parent.mkdir(parents=True,exist_ok=True)
    evidence_path.write_text(json.dumps({
      "schema":"PROJECT_BRAIN_GENERATED_VERIFICATION_MISSION_RECOVERY_V1",
      "verification_mission_id":verifier.get("mission_id"),
      "origin_mission_id":origin_mission_id,
      "prior_status":prior_status or "UNEXECUTED",
      "prior_mission_sha256":old_sha,
      "replacement_mission_sha256":new_sha,
      "policy":"ONLY_SAME_ORIGIN_AUTO_GENERATED_BLOCKED_OR_UNEXECUTED_MISSION_MAY_BE_REPLACED",
    },indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return "REPLACED_BLOCKED" if prior_status=="BLOCKED" else "REPLACED_UNEXECUTED"


def dispatch(goal,mission_id,mission_path,root,discovery=None):
    if not supports(goal):
        raise AutoPythonSourceCodecFailure("SOURCE_CODEC_CONTRACT_UNSUPPORTED")
    provider=_EXTERNAL_SOURCE_TREE_PROVIDER
    if not callable(provider):
        raise AutoPythonSourceCodecFailure("SOURCE_TREE_PROVIDER_UNAVAILABLE")
    root=pathlib.Path(root).resolve()
    origin_sha=_origin_mission_sha256(root,mission_path)
    response=provider(goal=goal,mission_id=mission_id)
    if response is None:
        raise AutoPythonSourceCodecFailure("SOURCE_TREE_PROVIDER_NO_RESULT")
    trees=response.get("trees") if isinstance(response,dict) else None
    if not isinstance(trees,list) or not trees:
        raise AutoPythonSourceCodecFailure("SOURCE_TREE_PROVIDER_RESULT_INVALID")
    probe_helper=root/"canonical"/"runtime"/"python_codec_probe.py"
    if not probe_helper.is_file():
        raise AutoPythonSourceCodecFailure("SOURCE_CODEC_PROBE_HELPER_MISSING")
    attempts=[]
    for supplied in trees[:12]:
        try:
            with tempfile.TemporaryDirectory(prefix="brain-source-codec-") as td:
                site=pathlib.Path(td)/"site"
                manifest=_materialize(supplied,site)
                probe=subprocess.run(
                    [sys.executable,str(probe_helper),str(site),json.dumps([manifest["package"]])],
                    cwd=root,text=True,capture_output=True,timeout=90
                )
                try:
                    observed=json.loads((probe.stdout or "").strip().splitlines()[-1])
                except Exception as exc:
                    raise AutoPythonSourceCodecFailure("SOURCE_CODEC_PROBE_RESULT_INVALID",(probe.stderr or probe.stdout or "")[-1200:]) from exc
                if probe.returncode!=0 or observed.get("ok") is not True:
                    raise AutoPythonSourceCodecFailure("SOURCE_CODEC_NO_COMPATIBLE_CONTRACT",json.dumps(observed.get("attempts") or [])[:1800])
                contract={
                  "schema":"PROJECT_BRAIN_PYTHON_SOURCE_CODEC_CONTRACT_V1",
                  "module":observed["module"],
                  "encode_callable":observed["encode_callable"],
                  "decode_callable":observed["decode_callable"],
                  "encode_kwargs":observed.get("encode_kwargs") or {},
                  "decode_kwargs":observed.get("decode_kwargs") or {},
                  "envelope_key":observed.get("envelope_key"),
                  "fixture":observed["fixture"],
                  "probe_output_sha256":observed["probe_output_sha256"],
                  "probe_output_bytes":observed["probe_output_bytes"],
                  "pair_discovery":observed.get("pair_discovery"),
                  "probe_isolation":"fresh_child_python_process",
                  "source_tree":manifest,
                }
                repository=manifest["repository"]; revision=manifest["revision"]
                format_terms=_format_terms(goal)
                provides=["structured.binary.encode"]+[
                    "structured.binary.encode."+x for x in format_terms
                ]
                cap_id="auto.source."+_slug(repository.split("/")[-1])
                pending_rel=f"canonical/astra_runtime/pending_bindings/{mission_id}__{_slug(repository)}__{manifest['tree_sha256'][:12]}.json"
                verify_rel=f"canonical/astra_runtime/evidence/{mission_id}__{_slug(repository)}__{manifest['tree_sha256'][:12]}__AUTO_VERIFY.json"
                verify_mid="ASTRA-AUTO-VERIFY-SOURCE-"+_slug(repository).upper()+"-"+manifest["tree_sha256"][:12].upper()
                entry={
                  "status":"BOUND_PENDING_INDEPENDENT_VERIFICATION",
                  "platforms":["linux","windows","darwin"],
                  "provides":provides,
                  "requires":["json.file.available"],
                  "keywords":["encode","binary",*format_terms,repository.lower()],
                  "adapter_module":"python_source_tree_codec",
                  "source":{
                    "type":"git_source_tree",
                    "repository":repository,
                    "revision":revision,
                    "tree_sha256":manifest["tree_sha256"],
                    "tree":supplied,
                  },
                  "action_template":{"type":"invoke_capability","args":{
                    "capability_id":cap_id,"module":contract["module"],
                    "encode_callable":contract["encode_callable"],"decode_callable":contract["decode_callable"],
                    "encode_kwargs":contract["encode_kwargs"],"decode_kwargs":contract["decode_kwargs"],
                    "envelope_key":contract.get("envelope_key"),
                    "json_path":"${input.json_path}","output_path":"${input.output_path}"
                  },"expect":{"type":"field_equals","field":"output_verified","value":True}},
                  "incremental_spend_usd":0,
                }
                pending={
                  "schema":"PROJECT_BRAIN_PENDING_AUTO_BINDING_V1",
                  "capability_id":cap_id,"effect":provides[0],"goal":goal,
                  "origin_mission_id":mission_id,"origin_mission_path":mission_path,
                  "origin_mission_sha256_at_acquisition":origin_sha,
                  "selected_supplier":{"repository":repository,"revision":revision},
                  "contract":contract,"verification_fixture":contract["fixture"],
                  "independent_verifier_source_trees":[
                    other for other in trees[:8]
                    if isinstance(other,dict)
                    and str(other.get("repository") or "").strip()!=repository
                  ][:4],
                  "registry_entry":entry,"verification_mission_id":verify_mid,
                  "verification_result_path":verify_rel,
                  "status":"PENDING_INDEPENDENT_VERIFICATION",
                }
                pp=root/pending_rel; pp.parent.mkdir(parents=True,exist_ok=True)
                pp.write_text(json.dumps(pending,indent=2,sort_keys=True)+"\n",encoding="utf-8")
                verifier={
                  "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_MISSION_V1",
                  "mission_id":verify_mid,
                  "purpose":"Fresh semantic round-trip verification and supplier-independent verification of an automatically acquired content-addressed Python source-tree codec.",
                  "goal":"Verify the pending source-tree codec in a fresh process, require a different supplier-class verifier, promote only after exact semantic equality, then replay the originating mission.",
                  "steps":[
                    {"id":"verify-pending-source-codec","adapter":"shell",
                     "command":f"set -euo pipefail\npython canonical/runtime/verify_pending_cli_binding.py {pending_rel} {verify_rel}",
                     "verify":{"type":"stdout_contains","text":"PENDING_SOURCE_BINDING_EFFECT_VERIFIED"}},
                    {"id":"promote-and-replay","adapter":"shell",
                     "command":f"set -euo pipefail\npython canonical/runtime/promote_pending_binding.py {pending_rel} {verify_rel}",
                     "verify":{"type":"stdout_contains","text":"PENDING_CAPABILITY_PROMOTED"}}
                  ],
                  "constraints":{
                    "incremental_spend_usd":0,
                    "model_controller_required":False,
                    "fresh_verification_invocation_required":True,
                    "allow_registry_mutation":True,
                    "auto_generated_from_mission":mission_id,
                    "supplier_class":"content_addressed_python_source_tree",
                    "independent_verifier_supplier_class_required":True,
                  }
                }
                vm_rel=f"canonical/astra_runtime/missions/{verify_mid.replace('-','_')}.json"
                verification_mission_recovery=_write_generated_verification_mission(
                    root,vm_rel,verifier,mission_id
                )
                return {
                  "status":"ACQUISITION_DISPATCHED",
                  "supplier_class":"content_addressed_python_source_tree",
                  "capability_id":cap_id,"supplier":repository+"@"+revision,
                  "pending_binding_path":pending_rel,
                  "verification_mission_path":vm_rel,
                  "verification_mission_id":verify_mid,
                  "verification_result_path":verify_rel,
                  "verification_mission_recovery":verification_mission_recovery,
                  "source_tree_sha256":manifest["tree_sha256"],
                  "incremental_spend_usd":0,
                }
        except Exception as exc:
            attempts.append({"error":type(exc).__name__+":"+str(exc)})
    raise AutoPythonSourceCodecFailure("NO_COMPATIBLE_SOURCE_CODEC_CONTRACT",json.dumps(attempts,sort_keys=True)[:3000])

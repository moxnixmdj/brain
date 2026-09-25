#!/usr/bin/env python3
"""Acquire and execute a producer-independent PyPI codec verifier."""
from __future__ import annotations
import importlib,json,pathlib,re,subprocess,sys,tempfile

import auto_pypi_library_acquisition as pypi_acq
import capability_discovery


class IndependentCodecVerifierFailure(RuntimeError):
    pass


def _norm(value):
    return re.sub(r"[-_.]+","-",str(value or "").strip()).lower()


def _module_candidates(wheel_path):
    return pypi_acq._module_candidates(wheel_path)


def _resolve(module,name):
    return pypi_acq._resolve(module,name)


def _candidate_pool(fmt,producer_project,root):
    effect=(
      "Independently decode "+fmt+" binary data from "
      "canonical/astra_runtime/tmp/INDEPENDENT_VERIFIER."+fmt
    )
    discovered=capability_discovery.search_pypi_packages(effect,limit=40,timeout_s=20)
    producer=_norm(producer_project)
    candidates=[]
    for cand in discovered.get("candidates") or []:
        project=str(cand.get("project") or cand.get("name") or "")
        if not project or _norm(project)==producer:
            continue
        if not cand.get("zero_cost_eligible",False):
            continue
        if int(cand.get("required_secret_count",0))!=0:
            continue
        if int(cand.get("dependency_count",0))>24:
            continue
        candidates.append(cand)
    candidates.sort(key=lambda x:(
      -float(x.get("score",0)),
      int(x.get("dependency_count",0)),
      str(x.get("name","")),
    ))
    return candidates[:20],discovered


def _install_isolated(closure,root):
    td=tempfile.TemporaryDirectory(prefix="brain-independent-codec-")
    base=pathlib.Path(td.name)
    site=base/"site"; site.mkdir()
    wheelhouse=base/"wheelhouse"; wheelhouse.mkdir()
    for item in closure["wheels"]:
        src=pathlib.Path(item["path"])
        (wheelhouse/src.name).write_bytes(src.read_bytes())
    root_wheel=closure["root"]
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
        td.cleanup()
        raise IndependentCodecVerifierFailure("VERIFIER_ISOLATED_INSTALL_FAILED:"+proc.stderr[-1200:])
    return td,site


def _semantic_match(observed,expected):
    if observed==expected:
        return True,None
    if isinstance(observed,dict):
        matches=[str(k) for k,v in observed.items() if v==expected]
        if len(matches)==1:
            return True,matches[0]
    return False,None


def verify(format_name,json_path,binary_path,producer_project,root):
    root=pathlib.Path(root).resolve()
    src=(root/str(json_path)).resolve()
    binary=(root/str(binary_path)).resolve()
    if root not in src.parents or root not in binary.parents:
        raise IndependentCodecVerifierFailure("PATH_OUTSIDE_REPOSITORY")
    if not src.is_file() or not binary.is_file():
        raise IndependentCodecVerifierFailure("VERIFIER_INPUT_MISSING")
    expected=json.loads(src.read_text(encoding="utf-8"))
    fmt=str(format_name or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._+-]{0,40}",fmt):
        raise IndependentCodecVerifierFailure("FORMAT_INVALID")
    candidates,discovery=_candidate_pool(fmt,producer_project,root)
    attempts=[]
    decode_names=("unpackb","loads","decode","deserialize")
    for candidate in candidates:
        attempt={"supplier":{
          "name":candidate.get("name"),
          "project":candidate.get("project"),
          "version":candidate.get("version"),
          "score":candidate.get("score"),
        }}
        try:
            closure=pypi_acq._download_compatible_wheel_closure(candidate,root)
            if any(_norm(x.get("project"))==_norm(producer_project) for x in closure["lock"]["wheels"]):
                attempt["status"]="REJECTED_PRODUCER_DEPENDENCY"
                attempts.append(attempt)
                continue
            td,site=_install_isolated(closure,root)
            try:
                modules=_module_candidates(closure["root"]["path"])
                sys.path.insert(0,str(site))
                try:
                    for module_name in modules:
                        for key in list(sys.modules):
                            if key==module_name or key.startswith(module_name+"."):
                                sys.modules.pop(key,None)
                        try:
                            module=importlib.import_module(module_name)
                        except Exception as exc:
                            attempt.setdefault("module_errors",[]).append({
                              "module":module_name,"error":type(exc).__name__
                            })
                            continue
                        for decode_name in decode_names:
                            try:
                                fn=_resolve(module,decode_name)
                            except Exception:
                                continue
                            for kwargs in ({},{"raw":False}):
                                try:
                                    observed=fn(binary.read_bytes(),**kwargs)
                                except Exception:
                                    continue
                                ok,unwrap_key=_semantic_match(observed,expected)
                                if not ok:
                                    continue
                                evidence={
                                  "schema":"PROJECT_BRAIN_INDEPENDENT_PYPI_CODEC_VERIFICATION_V1",
                                  "verified":True,
                                  "format":fmt,
                                  "producer_project":producer_project,
                                  "verifier_project":candidate.get("project") or candidate.get("name"),
                                  "verifier_version":candidate.get("version"),
                                  "producer_independent":_norm(candidate.get("project") or candidate.get("name"))!=_norm(producer_project),
                                  "dependency_independent":all(
                                    _norm(x.get("project"))!=_norm(producer_project)
                                    for x in closure["lock"]["wheels"]
                                  ),
                                  "module":module_name,
                                  "decode_callable":decode_name,
                                  "decode_kwargs":kwargs,
                                  "unwrap_key":unwrap_key,
                                  "dependency_closure":closure["lock"],
                                  "candidate_score":candidate.get("score"),
                                  "attempt_count":len(attempts)+1,
                                }
                                attempt["status"]="VERIFIED"
                                attempts.append(attempt)
                                evidence["attempts"]=attempts
                                return evidence
                finally:
                    try: sys.path.remove(str(site))
                    except ValueError: pass
            finally:
                td.cleanup()
            attempt["status"]="NO_SEMANTIC_DECODE_CONTRACT"
        except Exception as exc:
            attempt["status"]="PROBE_FAILED"
            attempt["error"]=type(exc).__name__+":"+str(exc)
        attempts.append(attempt)
    raise IndependentCodecVerifierFailure(
      "NO_PRODUCER_INDEPENDENT_VERIFIER:"+json.dumps({
        "producer_project":producer_project,
        "format":fmt,
        "candidate_names":[str(x.get("name") or "") for x in candidates],
        "attempts":attempts,
        "discovery_queries":discovery.get("queries"),
      },sort_keys=True)[:5000]
    )

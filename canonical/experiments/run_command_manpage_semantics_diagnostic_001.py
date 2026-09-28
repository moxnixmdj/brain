#!/usr/bin/env python3
from __future__ import annotations
import gzip,json,pathlib,re,shutil,subprocess,sys,tempfile,time

ROOT=pathlib.Path(__file__).resolve().parents[2]
SPEC=ROOT/"canonical"/"experiments"/"COMMAND_MANPAGE_SEMANTICS_DIAGNOSTIC_001.json"
OUT=ROOT/"canonical"/"astra_runtime"/"evidence"/"COMMAND_MANPAGE_SEMANTICS_DIAGNOSTIC_001__RESULT.json"

def norm_tokens(text):
    return set(re.findall(r"[a-z0-9]+",str(text or "").lower()))

def read_manpage(path):
    raw=path.read_bytes()
    if path.suffix==".gz":
        raw=gzip.decompress(raw)
    text=raw.decode("utf-8","replace")
    # Preserve source evidence while stripping the most obvious roff control noise.
    lines=[]
    for line in text.splitlines():
        if line.startswith("."):
            line=re.sub(r"^\.[A-Za-z]+\s*","",line)
        line=line.replace("\\-","-").replace("\\&"," ")
        if line.strip():
            lines.append(line.strip())
    return "\n".join(lines)

def apt_candidate_version(package):
    p=subprocess.run(["apt-cache","policy",package],text=True,capture_output=True,timeout=20)
    for line in p.stdout.splitlines():
        s=line.strip()
        if s.startswith("Candidate:"):
            v=s.split(":",1)[1].strip()
            if v and v!="(none)":
                return v
    return None

def package_manpage_text(package,expected_command,tmp):
    version=apt_candidate_version(package)
    if not version:
        return {"error":"NO_APT_CANDIDATE_VERSION"}
    dl=pathlib.Path(tmp)/"download"
    dl.mkdir(parents=True,exist_ok=True)
    p=subprocess.run(
        ["apt-get","download",f"{package}={version}"],
        cwd=dl,text=True,capture_output=True,timeout=120
    )
    debs=sorted(dl.glob("*.deb"))
    if p.returncode!=0 or not debs:
        return {"error":"APT_DOWNLOAD_FAILED","returncode":p.returncode,"stderr":p.stderr[-1200:]}
    root=pathlib.Path(tmp)/"extract"
    root.mkdir(parents=True,exist_ok=True)
    x=subprocess.run(["dpkg-deb","-x",str(debs[0]),str(root)],text=True,capture_output=True,timeout=60)
    if x.returncode!=0:
        return {"error":"DPKG_DEB_EXTRACT_FAILED","stderr":x.stderr[-1200:]}
    mans=[]
    for path in root.rglob("*.1*"):
        name=path.name.lower()
        if expected_command.lower() in name:
            try:
                mans.append({"path":str(path.relative_to(root)),"text":read_manpage(path)[:20000]})
            except Exception as exc:
                mans.append({"path":str(path.relative_to(root)),"error":type(exc).__name__+":"+str(exc)})
    if not mans:
        return {"version":version,"manpages":[],"error":"EXPECTED_COMMAND_MANPAGE_NOT_FOUND"}
    return {"version":version,"manpages":mans}

def main():
    spec=json.loads(SPEC.read_text())
    results=[]
    t0=time.monotonic()
    for case in spec["cases"]:
        t=time.monotonic()
        terms=[str(x).lower() for x in case["semantic_terms"]]
        cmd_tokens=norm_tokens(case["expected_command"].replace("-"," "))
        command_hits=sorted(t for t in terms if t in cmd_tokens or t.replace("-","") in case["expected_command"].lower().replace("-",""))
        with tempfile.TemporaryDirectory(prefix="pb-manmeta-") as td:
            meta=package_manpage_text(case["package"],case["expected_command"],td)
        mantext="\n".join(x.get("text","") for x in meta.get("manpages",[]) if isinstance(x,dict))
        man_tokens=norm_tokens(mantext)
        man_hits=sorted(t for t in terms if t in man_tokens)
        added=sorted(set(man_hits)-set(command_hits))
        results.append({
          "effect_id":case["effect_id"],
          "package":case["package"],
          "expected_command":case["expected_command"],
          "semantic_terms":terms,
          "command_name_hits":command_hits,
          "command_name_coverage":len(command_hits)/len(terms),
          "manpage_hits":man_hits,
          "manpage_coverage":len(man_hits)/len(terms),
          "added_semantic_terms":added,
          "manpage_metadata":meta,
          "wall_s":round(time.monotonic()-t,6),
        })
    improved=sum(1 for r in results if r["manpage_coverage"]>r["command_name_coverage"])
    complete=sum(1 for r in results if r["manpage_coverage"]>=0.75)
    out={
      "schema":"PROJECT_BRAIN_COMMAND_MANPAGE_SEMANTICS_DIAGNOSTIC_RESULT_V1",
      "diagnostic_id":spec["diagnostic_id"],
      "runtime_mutated":False,
      "candidate_packages_installed":False,
      "candidate_binaries_executed":False,
      "package_download_for_metadata_only":True,
      "results":results,
      "coverage_improved_cases":improved,
      "coverage_improved_fraction":improved/len(results) if results else 0,
      "high_semantic_coverage_cases":complete,
      "high_semantic_coverage_fraction":complete/len(results) if results else 0,
      "manpage_semantics_supported":improved>=3 and complete>=3,
      "promotion_authorized":False,
      "required_next_action":"RECONCILE__NO_RUNTIME_REPAIR_ON_THIS_BRANCH",
      "wall_s":round(time.monotonic()-t0,6)
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,indent=2,sort_keys=True))

if __name__=="__main__":
    main()

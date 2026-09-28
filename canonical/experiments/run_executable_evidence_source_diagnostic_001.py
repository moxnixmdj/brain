#!/usr/bin/env python3
from __future__ import annotations
import collections,json,pathlib,re,subprocess,sys,time

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical"/"runtime"
sys.path.insert(0,str(RUNTIME))
import capability_discovery as d

SPEC=ROOT/"canonical"/"experiments"/"EXECUTABLE_EVIDENCE_SOURCE_DIAGNOSTIC_001.json"
OUT=ROOT/"canonical"/"astra_runtime"/"evidence"/"EXECUTABLE_EVIDENCE_SOURCE_DIAGNOSTIC_001__RESULT.json"

GENERIC=set(d.GENERIC_DISCOVERY_TOKENS)|{
    "plain","document","file","using","report","technical","vector","raster",
    "inspect","compress","compression"
}

def fam_match(name,families):
    n=str(name or "").lower()
    for f in families:
        f=str(f).lower()
        if n==f or n.startswith(f+"-") or f.startswith(n+"-"):
            return True
    return False

def command_terms(goal):
    out=[]
    for token in d.effect_queries(goal):
        t=re.sub(r"[^a-z0-9]+","",str(token).lower())
        if len(t)<3 or t in GENERIC:
            continue
        if t not in out:
            out.append(t)
    return out[:6]

def apt_file_query(term):
    # Search only packaged executable paths. apt-file metadata is diagnostic
    # evidence; no candidate package is installed or executed.
    pattern=rf"/usr/bin/[^/]*{re.escape(term)}[^/]*$"
    p=subprocess.run(
        ["apt-file","search","-x",pattern],
        text=True,capture_output=True,timeout=60
    )
    rows=[]
    if p.returncode not in (0,1):
        return rows,{"term":term,"returncode":p.returncode,"stderr":p.stderr[-1000:]}
    for line in p.stdout.splitlines():
        if ": " not in line:
            continue
        package,path=line.split(": ",1)
        package=package.strip(); path=path.strip()
        if not package or not path.startswith("/usr/bin/"):
            continue
        rows.append((package,path))
    return rows,{"term":term,"returncode":p.returncode,"match_count":len(rows)}

def main():
    spec=json.loads(SPEC.read_text())
    results=[]
    total_oracle_hits=0
    t0=time.monotonic()
    for item in spec["effects"]:
        t=time.monotonic()
        terms=command_terms(item["goal"])
        evidence=collections.defaultdict(lambda:{"paths":set(),"terms":set()})
        query_diag=[]
        for term in terms:
            rows,diag=apt_file_query(term)
            query_diag.append(diag)
            for package,path in rows:
                evidence[package]["paths"].add(path)
                evidence[package]["terms"].add(term)

        ranked=[]
        for package,ev in evidence.items():
            paths=sorted(ev["paths"]); matched=sorted(ev["terms"])
            score=100*len(matched)+20*len(paths)
            # Prefer exact command/effect evidence over package lexical weight.
            for path in paths:
                cmd=path.rsplit("/",1)[-1].lower()
                for term in matched:
                    if cmd==term:
                        score+=80
                    elif cmd.startswith(term) or cmd.endswith(term):
                        score+=30
            ranked.append({
                "package":package,
                "command_paths":paths,
                "matched_terms":matched,
                "evidence_score":score,
            })
        ranked.sort(key=lambda x:(-x["evidence_score"],x["package"]))

        oracle_rows=[
            (idx,c) for idx,c in enumerate(ranked,1)
            if fam_match(c["package"],item["oracle_families"])
        ]
        hit=bool(oracle_rows)
        if hit:
            total_oracle_hits+=1
            oracle_rank,oracle=oracle_rows[0]
            oracle_detail={
                "surfaced":True,
                "rank":oracle_rank,
                "package":oracle["package"],
                "command_paths":oracle["command_paths"],
                "matched_terms":oracle["matched_terms"],
                "evidence_score":oracle["evidence_score"],
            }
        else:
            oracle_detail={"surfaced":False,"rank":None,"package":None,"command_paths":[],"matched_terms":[]}

        results.append({
            "effect_id":item["effect_id"],
            "goal":item["goal"],
            "terms":terms,
            "queries":query_diag,
            "candidate_count":len(ranked),
            "oracle":oracle_detail,
            "top12":ranked[:12],
            "wall_s":round(time.monotonic()-t,6),
        })

    recall=total_oracle_hits/len(results) if results else 0.0
    out={
        "schema":"PROJECT_BRAIN_EXECUTABLE_EVIDENCE_SOURCE_DIAGNOSTIC_RESULT_V1",
        "diagnostic_id":spec["diagnostic_id"],
        "source_type":"APT_FILE_PACKAGE_CONTENTS_INDEX",
        "runtime_mutated":False,
        "candidate_packages_installed":False,
        "candidate_binaries_executed":False,
        "diagnostic_dependency":"apt-file",
        "results":results,
        "oracle_family_recall":recall,
        "oracle_hits":total_oracle_hits,
        "oracle_total":len(results),
        "operation_evidence_source_supported":recall>=0.75,
        "promotion_authorized":False,
        "required_next_action":"RECONCILE__NO_RUNTIME_REPAIR_ON_THIS_BRANCH",
        "wall_s":round(time.monotonic()-t0,6),
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,indent=2,sort_keys=True))

if __name__=="__main__":
    main()

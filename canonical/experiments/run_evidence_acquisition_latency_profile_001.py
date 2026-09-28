#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical"/"runtime"
sys.path.insert(0,str(RUNTIME))
import capability_discovery as d

SPEC=ROOT/"canonical"/"experiments"/"EVIDENCE_ACQUISITION_LATENCY_PROFILE_001.json"
OUT=ROOT/"canonical"/"astra_runtime"/"evidence"/"EVIDENCE_ACQUISITION_LATENCY_PROFILE_001__RESULT.json"
SETUP_METRICS=pathlib.Path("/tmp/apt_file_setup_wall.json")


def fam_match(name,families):
    n=str(name or "").lower()
    for raw in families:
        f=str(raw or "").lower()
        if n==f or n.startswith(f+"-") or f.startswith(n+"-"):
            return True
    return False


def parse_rows(stdout):
    rows=[]
    for line in str(stdout or "").splitlines():
        if ": " not in line:
            continue
        package,path=line.split(": ",1)
        package=package.strip()
        path=path.strip()
        if package and path.startswith("/usr/bin/"):
            rows.append((package,path))
    return rows


def apt_file_query(pattern,timeout_s):
    t0=time.monotonic()
    try:
        p=subprocess.run(
            ["apt-file","search","-x",pattern],
            text=True,capture_output=True,timeout=timeout_s
        )
        wall=time.monotonic()-t0
        return {
            "returncode":p.returncode,
            "wall_s":round(wall,6),
            "rows":parse_rows(p.stdout),
            "stderr_tail":p.stderr[-600:],
            "timed_out":False,
        }
    except subprocess.TimeoutExpired as exc:
        wall=time.monotonic()-t0
        stdout=exc.stdout.decode("utf-8","replace") if isinstance(exc.stdout,bytes) else (exc.stdout or "")
        stderr=exc.stderr.decode("utf-8","replace") if isinstance(exc.stderr,bytes) else (exc.stderr or "")
        return {
            "returncode":None,
            "wall_s":round(wall,6),
            "rows":parse_rows(stdout),
            "stderr_tail":str(stderr)[-600:],
            "timed_out":True,
        }


def add_rows(evidence,rows,terms):
    for package,path in rows:
        ev=evidence.setdefault(package,{"paths":set(),"terms":set()})
        ev["paths"].add(path)
        cmd=path.rsplit("/",1)[-1].lower()
        compact=re.sub(r"[^a-z0-9]+","",cmd)
        matched=False
        for term in terms:
            t=str(term).lower()
            tc=re.sub(r"[^a-z0-9]+","",t)
            if t in cmd or (tc and tc in compact):
                ev["terms"].add(t)
                matched=True
        if not matched and len(terms)==1:
            ev["terms"].add(str(terms[0]).lower())


def ranked(evidence):
    out=[]
    for package,ev in evidence.items():
        paths=sorted(ev["paths"])
        hits=sorted(ev["terms"])
        score=100*len(hits)+20*len(paths)
        for path in paths:
            cmd=path.rsplit("/",1)[-1].lower()
            for term in hits:
                if cmd==term:
                    score+=80
                elif cmd.startswith(term) or cmd.endswith(term):
                    score+=30
        out.append({
            "package":package,
            "paths":paths,
            "matched_terms":hits,
            "score":score,
        })
    out.sort(key=lambda x:(-x["score"],x["package"]))
    return out


def oracle_info(items,families):
    for i,item in enumerate(items,1):
        if fam_match(item["package"],families):
            return {
                "found":True,
                "rank":i,
                "package":item["package"],
                "score":item["score"],
            }
    return {"found":False,"rank":None,"package":None,"score":None}


def ubuntu_codename():
    try:
        text=pathlib.Path("/etc/os-release").read_text(encoding="utf-8")
        m=re.search(r"^VERSION_CODENAME=([A-Za-z0-9._-]+)$",text,re.MULTILINE)
        if m:
            return m.group(1).lower()
    except Exception:
        pass
    return "noble"


def manpage_url(command):
    return (
        "https://manpages.ubuntu.com/manpages/"
        +urllib.parse.quote(ubuntu_codename(),safe="")
        +"/man1/"
        +urllib.parse.quote(command,safe="")
        +".1.html"
    )


def fetch_url(url,timeout_s):
    t0=time.monotonic()
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-LatencyProfile/1"})
    try:
        with urllib.request.urlopen(req,timeout=timeout_s) as resp:
            raw=resp.read(180000)
        return {
            "ok":True,
            "wall_s":round(time.monotonic()-t0,6),
            "bytes":len(raw),
            "status":getattr(resp,"status",None),
            "error":None,
        }
    except Exception as exc:
        return {
            "ok":False,
            "wall_s":round(time.monotonic()-t0,6),
            "bytes":0,
            "status":None,
            "error":type(exc).__name__+":"+str(exc),
        }


def profile_case(case,cfg):
    goal=case["goal"]
    families=case["oracle_families"]
    terms=d.effect_queries(goal)[:int(cfg["max_semantic_terms_per_case"])]
    timeout=float(cfg["apt_file_query_timeout_s"])

    sequential=[]
    seq_evidence={}
    prefix_oracles=[]
    for term in terms:
        pattern=rf"/usr/bin/[^/]*{re.escape(term)}[^/]*$"
        q=apt_file_query(pattern,timeout)
        add_rows(seq_evidence,q["rows"],[term])
        info=oracle_info(ranked(seq_evidence),families)
        prefix_oracles.append({
            "terms_used":len(prefix_oracles)+1,
            "oracle_rank":info["rank"],
            "oracle_found":info["found"],
        })
        sequential.append({
            "term":term,
            "pattern":pattern,
            "wall_s":q["wall_s"],
            "returncode":q["returncode"],
            "row_count":len(q["rows"]),
            "timed_out":q["timed_out"],
        })

    repeat=None
    if terms:
        pattern=rf"/usr/bin/[^/]*{re.escape(terms[0])}[^/]*$"
        q=apt_file_query(pattern,timeout)
        repeat={
            "term":terms[0],
            "wall_s":q["wall_s"],
            "returncode":q["returncode"],
            "row_count":len(q["rows"]),
            "timed_out":q["timed_out"],
        }

    batch_alt="|".join(re.escape(t) for t in terms)
    batch_pattern=rf"/usr/bin/[^/]*({batch_alt})[^/]*$" if batch_alt else r"/usr/bin/$a"
    batch=apt_file_query(batch_pattern,max(timeout,18.0))
    batch_evidence={}
    add_rows(batch_evidence,batch["rows"],terms)

    seq_ranked=ranked(seq_evidence)
    batch_ranked=ranked(batch_evidence)
    seq_oracle=oracle_info(seq_ranked,families)
    batch_oracle=oracle_info(batch_ranked,families)

    seq_packages=set(seq_evidence)
    batch_packages=set(batch_evidence)
    union=seq_packages|batch_packages
    overlap=len(seq_packages&batch_packages)/len(union) if union else 1.0
    seq_wall=sum(float(x["wall_s"]) for x in sequential)
    batch_wall=float(batch["wall_s"])
    batch_speedup=(seq_wall/batch_wall) if batch_wall>0 else None
    first_wall=float(sequential[0]["wall_s"]) if sequential else 0.0
    repeat_speedup=(first_wall/float(repeat["wall_s"])) if repeat and float(repeat["wall_s"])>0 else None

    min_terms_top20=None
    for item in prefix_oracles:
        if item["oracle_rank"] is not None and item["oracle_rank"]<=20:
            min_terms_top20=item["terms_used"]
            break

    commands=[]
    for item in batch_ranked:
        for path in item["paths"]:
            command=path.rsplit("/",1)[-1]
            if command not in commands:
                commands.append(command)
            if len(commands)>=int(cfg["max_manpage_commands_per_case"]):
                break
        if len(commands)>=int(cfg["max_manpage_commands_per_case"]):
            break

    urls=[manpage_url(c) for c in commands]
    sequential_fetch=[]
    t0=time.monotonic()
    for url in urls:
        sequential_fetch.append({"url":url,**fetch_url(url,float(cfg["manpage_fetch_timeout_s"]))})
    man_seq_wall=time.monotonic()-t0

    parallel_fetch=[]
    t0=time.monotonic()
    if urls:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8,len(urls))) as pool:
            future_map={pool.submit(fetch_url,url,float(cfg["manpage_fetch_timeout_s"])):url for url in urls}
            for future in concurrent.futures.as_completed(future_map):
                url=future_map[future]
                try:
                    row=future.result()
                except Exception as exc:
                    row={"ok":False,"wall_s":0.0,"bytes":0,"status":None,"error":type(exc).__name__+":"+str(exc)}
                parallel_fetch.append({"url":url,**row})
    man_parallel_wall=time.monotonic()-t0

    man_repeat=None
    if urls:
        man_repeat={"url":urls[0],**fetch_url(urls[0],float(cfg["manpage_fetch_timeout_s"]))}

    naive_fetch_count=len(urls)
    unique_fetch_count=len(set(urls))
    man_speedup=(man_seq_wall/man_parallel_wall) if man_parallel_wall>0 else None

    projected_current=seq_wall+man_seq_wall
    projected_batched_parallel=batch_wall+man_parallel_wall
    projected_speedup=(projected_current/projected_batched_parallel) if projected_batched_parallel>0 else None

    return {
        "effect_id":case["effect_id"],
        "goal":goal,
        "semantic_terms":terms,
        "sequential_apt_file":sequential,
        "repeat_same_query":repeat,
        "batched_apt_file":{
            "pattern":batch_pattern,
            "wall_s":batch["wall_s"],
            "returncode":batch["returncode"],
            "row_count":len(batch["rows"]),
            "timed_out":batch["timed_out"],
        },
        "sequential_package_count":len(seq_packages),
        "batched_package_count":len(batch_packages),
        "package_set_jaccard":round(overlap,6),
        "sequential_apt_wall_s":round(seq_wall,6),
        "batched_apt_wall_s":round(batch_wall,6),
        "sequential_vs_batched_speedup":round(batch_speedup,6) if batch_speedup is not None else None,
        "first_vs_repeat_query_speedup":round(repeat_speedup,6) if repeat_speedup is not None else None,
        "sequential_direct_evidence_oracle":seq_oracle,
        "batched_direct_evidence_oracle":batch_oracle,
        "minimum_term_prefix_for_top20_oracle":min_terms_top20,
        "prefix_oracle_trace":prefix_oracles,
        "manpage_commands":commands,
        "manpage_sequential_wall_s":round(man_seq_wall,6),
        "manpage_parallel_wall_s":round(man_parallel_wall,6),
        "manpage_parallel_speedup":round(man_speedup,6) if man_speedup is not None else None,
        "manpage_repeat":man_repeat,
        "manpage_sequential_results":sequential_fetch,
        "manpage_parallel_results":parallel_fetch,
        "naive_manpage_fetch_count":naive_fetch_count,
        "unique_manpage_fetch_count":unique_fetch_count,
        "projected_current_evidence_wall_s":round(projected_current,6),
        "projected_batched_parallel_wall_s":round(projected_batched_parallel,6),
        "projected_speedup":round(projected_speedup,6) if projected_speedup is not None else None,
    }


def main():
    spec=json.loads(SPEC.read_text(encoding="utf-8"))
    cfg=spec["constraints"]
    setup={}
    if SETUP_METRICS.exists():
        try:
            setup=json.loads(SETUP_METRICS.read_text(encoding="utf-8"))
        except Exception:
            setup={}

    t0=time.monotonic()
    cases=[profile_case(case,cfg) for case in spec["cases"]]
    total=time.monotonic()-t0

    seq_apt=sum(x["sequential_apt_wall_s"] for x in cases)
    batch_apt=sum(x["batched_apt_wall_s"] for x in cases)
    man_seq=sum(x["manpage_sequential_wall_s"] for x in cases)
    man_parallel=sum(x["manpage_parallel_wall_s"] for x in cases)
    current_total=sum(x["projected_current_evidence_wall_s"] for x in cases)
    projected_total=sum(x["projected_batched_parallel_wall_s"] for x in cases)
    direct_top20=sum(
        1 for x in cases
        if x["batched_direct_evidence_oracle"]["rank"] is not None
        and x["batched_direct_evidence_oracle"]["rank"]<=20
    )
    avg_overlap=sum(x["package_set_jaccard"] for x in cases)/len(cases)
    aggregate_speedup=(current_total/projected_total) if projected_total>0 else None
    batch_speedup=(seq_apt/batch_apt) if batch_apt>0 else None
    man_speedup=(man_seq/man_parallel) if man_parallel>0 else None

    per_task_components={
        "sequential_apt_file_queries":seq_apt,
        "sequential_manpage_fetches":man_seq,
    }
    dominant=max(per_task_components,key=per_task_components.get) if per_task_components else None

    structural_findings={
        "batch_queries_supported":bool(batch_speedup is not None and batch_speedup>=1.5 and avg_overlap>=0.8),
        "parallel_manpages_supported":bool(man_speedup is not None and man_speedup>=1.3),
        "direct_evidence_top20_fraction":direct_top20/len(cases),
        "defer_manpages_candidate":bool(direct_top20>=2),
        "projected_combined_speedup":aggregate_speedup,
    }

    result={
        "schema":"PROJECT_BRAIN_EVIDENCE_ACQUISITION_LATENCY_PROFILE_RESULT_V1",
        "profile_id":spec["profile_id"],
        "runtime_mutated":False,
        "candidate_packages_installed":False,
        "candidate_binaries_executed":False,
        "setup_metrics":setup,
        "cases":cases,
        "aggregate":{
            "profile_wall_s":round(total,6),
            "sequential_apt_file_wall_s":round(seq_apt,6),
            "batched_apt_file_wall_s":round(batch_apt,6),
            "apt_file_batch_speedup":round(batch_speedup,6) if batch_speedup is not None else None,
            "sequential_manpage_wall_s":round(man_seq,6),
            "parallel_manpage_wall_s":round(man_parallel,6),
            "manpage_parallel_speedup":round(man_speedup,6) if man_speedup is not None else None,
            "average_package_set_jaccard":round(avg_overlap,6),
            "current_style_projected_wall_s":round(current_total,6),
            "batched_parallel_projected_wall_s":round(projected_total,6),
            "projected_combined_speedup":round(aggregate_speedup,6) if aggregate_speedup is not None else None,
            "dominant_per_task_component":dominant,
        },
        "structural_findings":structural_findings,
        "promotion_authorized":False,
        "required_next_action":"RECONCILE_PARENT_FRONTIER__NO_RUNTIME_REPAIR_ON_THIS_BRANCH",
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__=="__main__":
    main()

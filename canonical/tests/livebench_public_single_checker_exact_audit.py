#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, pathlib, subprocess, sys, tempfile, urllib.request
from collections import Counter, defaultdict

IFBENCH_URL="https://raw.githubusercontent.com/allenai/IFBench/1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/data/IFBench_test.jsonl"
IFBENCH_BLOB="a8e343ed928d8b4e649b9dba651fed7757ccacc3"
LIVEBENCH_REPO="https://github.com/LiveBench/LiveBench.git"
LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
RECEIPT=pathlib.Path("livebench_public_single_checker_exact_audit_receipt.json")

def fetch(url:str)->bytes:
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-public-audit"})
    with urllib.request.urlopen(req,timeout=60) as r:
        return r.read()

def git_blob_sha(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def main()->int:
    raw=fetch(IFBENCH_URL)
    assert git_blob_sha(raw)==IFBENCH_BLOB,(git_blob_sha(raw),IFBENCH_BLOB)
    rows=[json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    assert len(rows)==300

    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["git","clone","--quiet","--filter=blob:none","--no-checkout",LIVEBENCH_REPO,td],check=True)
        subprocess.run(["git","-C",td,"checkout","--quiet",LIVEBENCH_COMMIT],check=True)
        sys.path.insert(0,td)

        import nltk
        for pkg in ["punkt","punkt_tab","stopwords","averaged_perceptron_tagger","averaged_perceptron_tagger_eng"]:
            try:
                nltk.download(pkg,quiet=True)
            except Exception:
                pass

        from livebench.if_runner.ifbench import evaluation_lib
        from canonical.runtime.livebench_if_single_checker_solver_v1 import detect, solve

        total_single=0
        exact_detect=0
        solver_candidate=0
        exact_pass=0
        by_family=defaultdict(lambda:Counter(total=0,detected=0,candidate=0,passed=0,failed=0))
        failures=[]

        for row in rows:
            ids=list(row.get("instruction_id_list") or [])
            if len(ids)!=1:
                continue
            total_single+=1
            iid=ids[0]
            rec=by_family[iid]
            rec["total"]+=1

            detected=detect(str(row["prompt"]))
            if detected==ids:
                exact_detect+=1
                rec["detected"]+=1

            out=solve(str(row["prompt"]))
            response=out.get("response")
            if out.get("status")=="PASS_CANDIDATE_SINGLE_CHECKER_WITNESS" and response:
                solver_candidate+=1
                rec["candidate"]+=1
                try:
                    inp=evaluation_lib.InputExample(
                        key=row.get("key",row.get("question_id",0)),
                        instruction_id_list=ids,
                        prompt=str(row["prompt"]),
                        kwargs=row["kwargs"],
                    )
                    scored=evaluation_lib.test_instruction_following_strict(inp,str(response))
                    passed=bool(scored.follow_all_instructions)
                except Exception as e:
                    passed=False
                    failures.append({
                        "key":str(row.get("key")),
                        "checker":iid,
                        "stage":"exact_checker_exception",
                        "exception":type(e).__name__+":"+str(e)[:300],
                        "solver_status":out.get("status"),
                    })
                if passed:
                    exact_pass+=1
                    rec["passed"]+=1
                else:
                    rec["failed"]+=1
                    if not any(x.get("key")==str(row.get("key")) for x in failures):
                        failures.append({
                            "key":str(row.get("key")),
                            "checker":iid,
                            "stage":"exact_checker_false",
                            "solver_status":out.get("status"),
                            "response_preview":str(response)[:240],
                        })
            else:
                rec["failed"]+=1
                failures.append({
                    "key":str(row.get("key")),
                    "checker":iid,
                    "stage":"solver_no_candidate",
                    "solver_status":out.get("status"),
                    "error":out.get("error"),
                })

        assert total_single==256
        family_rows={k:dict(v) for k,v in sorted(by_family.items())}
        fully_passing=[k for k,v in family_rows.items() if v["passed"]==v["total"]]
        fully_passing_rows=sum(family_rows[k]["total"] for k in fully_passing)
        threshold_needed=198

        receipt={
            "schema":"PROJECT_BRAIN_LIVEBENCH_PUBLIC_SINGLE_CHECKER_EXACT_AUDIT_V1",
            "status":"MEASURED_PUBLIC_EXACT_CHECKER_AUDIT__ZERO_TERMINAL_CASES__ZERO_ACCEPTANCE_CREDIT",
            "sources":{
                "ifbench_blob":git_blob_sha(raw),
                "livebench_commit":LIVEBENCH_COMMIT,
            },
            "counts":{
                "public_rows":len(rows),
                "single_checker_rows":total_single,
                "exact_instruction_set_detected":exact_detect,
                "solver_candidate_rows":solver_candidate,
                "exact_frozen_checker_pass_rows":exact_pass,
                "exact_frozen_checker_fail_or_no_candidate_rows":total_single-exact_pass,
                "threshold_single_rows_needed":threshold_needed,
                "threshold_crossed_by_current_single_solver":exact_pass>=threshold_needed,
                "public_score_percent_from_single_rows_only":100.0*exact_pass/len(rows),
                "fully_passing_family_count":len(fully_passing),
                "fully_passing_family_rows":fully_passing_rows,
            },
            "family_rows":family_rows,
            "fully_passing_families":fully_passing,
            "failures":failures,
            "hard_nonclaims":[
                "NO_TERMINAL_LIVEBENCH_CASE_CONTENT_READ",
                "NO_TERMINAL_POPULATION_EQUIVALENCE_CLAIM",
                "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
            ],
        }
        RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
        print(json.dumps(receipt,sort_keys=True,ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

"""Measure frozen verifier-suite wall-clock for non-synthetic H100 capabilities."""
from __future__ import annotations
import json, os, re, statistics, subprocess, sys, time
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_NON_SYNTHETIC_VERIFIER_COST_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_NON_SYNTHETIC_VERIFIER_COST_RESULT_V1"

class VerifierCostError(RuntimeError):
    pass

def module_from_test_path(path:str)->str:
    p=Path(path)
    if p.suffix!=".py":
        raise VerifierCostError("TEST_PATH_NOT_PY")
    return ".".join(p.with_suffix("").parts)

def _once(module:str)->dict[str,Any]:
    env=dict(os.environ)
    env["PYTHONPATH"]=str(ROOT)+(os.pathsep+env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    start=time.perf_counter()
    proc=subprocess.run(
        [sys.executable,"-m","unittest",module,"-q"],
        cwd=ROOT,env=env,text=True,capture_output=True
    )
    elapsed=time.perf_counter()-start
    output=(proc.stdout or "")+"\n"+(proc.stderr or "")
    m=re.search(r"Ran\s+(\d+)\s+tests?",output)
    test_count=int(m.group(1)) if m else None
    if proc.returncode!=0:
        raise VerifierCostError(f"VERIFIER_FAILED:{module}:{proc.returncode}:{output[-2000:]}")
    return {"seconds":elapsed,"test_count":test_count}

def measure_subject(row:dict[str,Any],repetitions:int)->dict[str,Any]:
    module=module_from_test_path(row["tests"])
    warm=_once(module)
    timed=[_once(module) for _ in range(repetitions)]
    counts={x["test_count"] for x in timed if x["test_count"] is not None}
    if len(counts)>1:
        raise VerifierCostError("TEST_COUNT_CHANGED")
    vals=[x["seconds"] for x in timed]
    return {
        "id":row["id"],
        "runtime":row["runtime"],
        "tests":row["tests"],
        "prior_verification":row["prior_verification"],
        "test_count":next(iter(counts)) if counts else warm["test_count"],
        "median_verifier_seconds":statistics.median(vals),
        "min_verifier_seconds":min(vals),
        "max_verifier_seconds":max(vals),
        "repetitions":repetitions,
    }

def run()->dict[str,Any]:
    pre=json.loads(PRE.read_text())
    if pre.get("status")!="FROZEN_BEFORE_TIMING_OUTCOMES__EXACT_PRIOR_VERIFIED_SUBJECTS__ZERO_CREDIT":
        raise VerifierCostError("PRECOMMIT_NOT_FROZEN")
    reps=int(pre["measurement"]["repetitions"])
    rows=[measure_subject(dict(x),reps) for x in pre["cohort"]]
    meds=[x["median_verifier_seconds"] for x in rows]
    return {
        "schema":SCHEMA,
        "status":"NON_SYNTHETIC_VERIFIER_COSTS_MEASURED__FOUR_CAPABILITY_CLASSES__ZERO_CREDIT",
        "subjects":rows,
        "summary":{
            "subject_count":len(rows),
            "median_of_subject_medians_seconds":statistics.median(meds),
            "min_subject_median_seconds":min(meds),
            "max_subject_median_seconds":max(meds),
        },
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "UNIT_TEST_WALL_CLOCK_IS_A_CAPABILITY_VERIFICATION_COST_PROXY",
            "DESCRIPTION_LENGTH_FOR_THIS_COHORT_REMAINS_UNMEASURED",
            "NO_H100_TERMINAL_CREDIT"
        ],
        "h100_terminal_credit_delta":0
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))

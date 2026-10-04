#!/usr/bin/env python3
"""Exact public IFBench scorer audit for Brain single-checker witnesses.

Reads only the pinned public AllenAI IFBench test population. Emits aggregate
family statistics only: no prompt text, response text, or terminal data.
"""
from __future__ import annotations
import argparse
import collections
import json
import pathlib
import sys

from canonical.runtime import livebench_if_single_checker_solver_v1 as solver


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--ifbench-root", required=True)
    ns=ap.parse_args()
    root=pathlib.Path(ns.ifbench_root).resolve()
    sys.path.insert(0,str(root))
    from ifbench import instructions_registry

    rows=[
        json.loads(line)
        for line in (root/"data"/"IFBench_test.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    single=[row for row in rows if len(row.get("instruction_id_list") or [])==1]
    family=collections.defaultdict(lambda:{"total":0,"pass":0,"solver_fail":0,"scorer_exception":0})
    total_pass=0
    status_counts=collections.Counter()
    exception_types=collections.Counter()

    for row in single:
        iid=str(row["instruction_id_list"][0])
        family[iid]["total"]+=1
        out=solver.solve(str(row.get("prompt") or ""))
        status=str(out.get("status") or "")
        status_counts[status]+=1
        if status!="PASS_CANDIDATE_SINGLE_CHECKER_WITNESS":
            family[iid]["solver_fail"]+=1
            continue
        try:
            instruction_cls=instructions_registry.INSTRUCTION_DICT[iid]
            instruction=instruction_cls(iid)
            kwargs={
                key:value for key,value in dict((row.get("kwargs") or [{}])[0]).items()
                if value is not None
            }
            instruction.build_description(**kwargs)
            args=instruction.get_instruction_args()
            if args and "prompt" in args:
                instruction.build_description(prompt=str(row.get("prompt") or ""))
            ok=bool(instruction.check_following(str(out.get("response") or "")))
        except Exception as exc:
            family[iid]["scorer_exception"]+=1
            exception_types[type(exc).__name__]+=1
            ok=False
        if ok:
            family[iid]["pass"]+=1
            total_pass+=1

    failing={
        iid:stats for iid,stats in sorted(family.items())
        if stats["pass"]!=stats["total"]
    }
    result={
        "schema":"PROJECT_BRAIN_PUBLIC_IFBENCH_SINGLE_CHECKER_EXACT_SCORER_AUDIT_V1",
        "ifbench_commit":"1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d",
        "public_rows":len(rows),
        "single_checker_rows":len(single),
        "single_checker_pass":total_pass,
        "single_checker_fail":len(single)-total_pass,
        "strict_pass_rate":total_pass/len(single) if single else 0.0,
        "families_total":len(family),
        "families_all_rows_pass":sum(1 for x in family.values() if x["pass"]==x["total"]),
        "families_with_any_failure":len(failing),
        "failing_families":failing,
        "solver_status_counts":dict(sorted(status_counts.items())),
        "scorer_exception_types":dict(sorted(exception_types.items())),
        "terminal_case_content_read":False,
        "model_dependency_count":0,
        "incremental_spend_usd":0,
        "acceptance_credit_delta":0,
    }
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())

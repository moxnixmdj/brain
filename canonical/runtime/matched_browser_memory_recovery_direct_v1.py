from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from canonical.runtime import browser_goal_grounding_recovery_candidate as candidate
from canonical.runtime import browser_goal_grounding_recovery_proof as proof
from canonical.runtime import composition_state_capsule_v2 as capsule

SCHEMA="PROJECT_BRAIN_MATCHED_BROWSER_MEMORY_RECOVERY_DIRECT_V1"

def _canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def _sha(v:Any)->str:
    return hashlib.sha256(_canon(v)).hexdigest()

class MemoryBackedSolver:
    def __init__(self, *, ablate_memory_before_stage2:bool=False):
        self.cap=capsule.empty_capsule()
        self.ablate=bool(ablate_memory_before_stage2)
        self.calls=0
        self.events=[]
        self.memory_goal_sha=None
        self.stage2_goal_source=None

    def __call__(self, public:Mapping[str,Any])->dict[str,Any]:
        self.calls+=1
        stage=int(public.get("stage") or 0)
        if stage==1:
            goal=str(public.get("goal") or "")
            browser_state_id="browser-state:"+_sha(public.get("elements") or [])[:16]
            goal_sha=hashlib.sha256(goal.encode()).hexdigest()
            self.cap=capsule.append_macrostep(
                self.cap,
                producer_ref="browser-memory",
                producer_descriptor={"kind":"brain_owned_browser_memory","stage":1},
                action_ref="remember-browser-goal",
                action_descriptor={"type":"remember_goal","goal_sha256":goal_sha},
                requires=[],
                provides=["browser.goal"],
                values={"browser.goal":goal},
                evidence_values={"goal_input":{"goal_sha256":goal_sha}},
                lineage={
                    "browser.goal":[
                        "evidence:goal_input",
                        "action:remember-browser-goal",
                        "producer:browser-memory",
                    ]
                },
            )
            self.memory_goal_sha=goal_sha
            self.events.extend([
                {"type":"BROWSER_STATE","event_id":browser_state_id,"elements_sha256":_sha(public.get("elements") or [])},
                {"type":"MEMORY_WRITE","state_ref":browser_state_id,"key":"browser.goal","value_sha256":goal_sha},
            ])
            return candidate.solve(public)

        if stage==2:
            receipt=public.get("receipt") or {}
            self.events.append({
                "type":"FAILURE",
                "reason":str(receipt.get("kind") or "UNKNOWN"),
                "previous_element_id":str(receipt.get("previous_element_id") or ""),
            })
            cap=self.cap
            if self.ablate:
                cap=capsule.empty_capsule()
            try:
                remembered=capsule.project_context(cap,["browser.goal"])["values"]["browser.goal"]
            except Exception:
                self.stage2_goal_source="MEMORY_MISSING"
                return {
                    "status":"ESCALATE",
                    "reason":"BROWSER_GOAL_MEMORY_UNAVAILABLE",
                    "observed_receipt_kind":receipt.get("kind"),
                }
            self.stage2_goal_source="CAPSULE_ONLY"
            remembered_sha=hashlib.sha256(str(remembered).encode()).hexdigest()
            self.events.append({"type":"MEMORY_READ","key":"browser.goal","value_sha256":remembered_sha})
            # The evaluator's repeated goal is deliberately discarded. The candidate
            # receives only the goal recovered from Brain-owned capsule state.
            stage2=dict(public)
            stage2.pop("goal",None)
            stage2["goal"]=remembered
            out=candidate.solve(stage2)
            self.events.append({
                "type":"RECOVERY",
                "recovered_element_id":str(out.get("element_id") or ""),
                "observed_receipt_kind":out.get("observed_receipt_kind"),
            })
            return out

        return {"status":"ESCALATE","reason":"UNEXPECTED_STAGE"}

def execute_case(seed:int,ordinal:int,*,ablate_memory:bool=False)->dict[str,Any]:
    case=proof.generate_case(seed,ordinal)
    solver=MemoryBackedSolver(ablate_memory_before_stage2=ablate_memory)
    try:
        verdict=proof.score_episode(case,solver)
    except Exception as exc:
        verdict={"pass":False,"reason":"HARNESS_EXCEPTION:"+type(exc).__name__+":"+str(exc)}
    passed=verdict.get("pass") is True
    events=[]
    for i,row in enumerate(solver.events):
        events.append({"seq":i,"source":"HARNESS",**row})
    events.append({"seq":len(events),"type":"TERMINAL","source":"HARNESS","success":passed})
    return {
        "schema":SCHEMA+"_RESULT",
        "case_id":case["case_id"],
        "case_class":case["case_class"],
        "pass":passed,
        "reason":verdict.get("reason"),
        "memory_ablated":bool(ablate_memory),
        "stage2_goal_source":solver.stage2_goal_source,
        "memory_goal_sha256":solver.memory_goal_sha,
        "solver_call_count":solver.calls,
        "objective_trace":{"trace_source":"HARNESS_OBJECTIVE","events":events},
        "terminal_authority":False,
        "fresh_reality_authority":False,
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }

def causal_ablation(seed:int,ordinal:int)->dict[str,Any]:
    full=execute_case(seed,ordinal,ablate_memory=False)
    ablated=execute_case(seed,ordinal,ablate_memory=True)
    return {
        "full_pass":full["pass"],
        "ablated_pass":ablated["pass"],
        "memory_is_load_bearing":full["pass"] is True and ablated["pass"] is False,
        "full_stage2_goal_source":full["stage2_goal_source"],
        "ablated_stage2_goal_source":ablated["stage2_goal_source"],
        "terminal_credit_delta":0,
    }

def run_batch(seed:int,count:int=12)->dict[str,Any]:
    rows=[]
    for i in range(count):
        try: rows.append(execute_case(seed+i*1009,i))
        except Exception as exc:
            rows.append({"case_id":f"ERR-{i}","pass":False,"error":type(exc).__name__+":"+str(exc)})
    passed=sum(int(x.get("pass") is True) for x in rows)
    return {
        "schema":SCHEMA+"_BATCH_RESULT",
        "case_count":count,
        "passed":passed,
        "failed":count-passed,
        "all_pass":passed==count,
        "case_classes":sorted({x.get("case_class") for x in rows if x.get("case_class")}),
        "failures":[x for x in rows if x.get("pass") is not True][:20],
        "terminal_authority":False,
        "fresh_reality_authority":False,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(run_batch(20261007,12),indent=2,sort_keys=True))

#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def L(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
def verify():
 h=L("canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json"); p=L("canonical/CANONICAL_POINTER.json")
 s=L("canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json"); q=L("canonical/capabilities/FRONTIER_CAPABILITY_OBSOLESCENCE_QUEUE_V1.json")
 g=L("canonical/governance/GLOBAL_TERMINAL_OBLIGATION_GRAPH_V1.json"); t=L("canonical/capabilities/frontier/"+h["active_capability_target"]+".json")
 f=[]; eq=lambda n,a,b: f.append({"invariant":n,"left":a,"right":b}) if a!=b else None
 b=h["current_parent_blocker"]; n=h["next_required_action_class"]; e=h["next_progress_event_target"]; a=s["active_frontier_accounting"]; i=q["immediate_frontier"]; c=p["current_frontier"]
 eq("pointer.blocker",c["critical_blocker"],b); eq("pointer.gap",c["highest_leverage_capability_gap"],b); eq("pointer.next",c["next_step"],n)
 eq("queue.blocker",i["exact_blocker"],b); eq("queue.next",i["next_action"],n)
 eq("queue.residual_count",i.get("open_mechanism_residual_count"),g["open_mechanism_residual_count"]); eq("queue.residuals",i.get("open_mechanism_residuals"),g["open_mechanism_residuals"])
 eq("scoreboard.blocker",a["current_parent_blocker"],b); eq("scoreboard.gap",a["residual_gap"],b); eq("scoreboard.next",a["next_required_action"],n); eq("scoreboard.top_next",s["next_required_action"],n); eq("scoreboard.event",s["next_progress_event_target"],e)
 eq("target.blocker",t["current_atomic_blocker"],b); eq("target.next",t["current_atomic_next_action"],n)
 return {"schema":"PROJECT_BRAIN_FRONTIER_STATE_CONSISTENCY_V1","status":"PASS" if not f else "FAIL_CLOSED","failures":f}
if __name__=="__main__":
 r=verify(); print(json.dumps(r,indent=2,sort_keys=True)); raise SystemExit(0 if r["status"]=="PASS" else 1)

#!/usr/bin/env python3
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PKG_ROOT = ROOT / "canonical/capabilities/internalized/causal_falsification/agent_replay_v1"
sys.path.insert(0, str(PKG_ROOT))

from agent_replay import attribute, record

VENDOR = PKG_ROOT / "agent_replay"
FORBIDDEN_ROOTS = {"requests","urllib","httpx","openai","anthropic","google","socket","subprocess"}

def verify_no_external_runtime_route():
    bad=[]
    for path in sorted(VENDOR.glob("*.py")):
        tree=ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    root=n.name.split(".")[0]
                    if root in FORBIDDEN_ROOTS:
                        bad.append((path.name,root))
            elif isinstance(node, ast.ImportFrom) and node.level==0 and node.module:
                root=node.module.split(".")[0]
                if root in FORBIDDEN_ROOTS:
                    bad.append((path.name,root))
    assert not bad, bad

def verifier(result):
    return 1.0 if result.get("ok") else 0.0

def make_agent(n_steps, fail_step, fail_prob):
    def agent(ctx, task="fresh"):
        trace=[]
        for i in range(n_steps):
            def produce(step=i):
                if step == fail_step:
                    return "BAD" if ctx.rng.random() < fail_prob else "OK"
                return "OK"
            kind=ctx.tool if i == fail_step else ctx.llm
            trace.append(kind(f"fresh_step_{i}", produce=produce))
        return {"trace":trace, "ok":"BAD" not in trace}
    return agent

def record_failure(agent, name):
    for seed in range(1000):
        traj=record(agent, {"task":name}, session_id=name, seed=seed, verifier=verifier)
        if traj.outcome_score is not None and traj.outcome_score < 0.5:
            return traj
    raise AssertionError("no failing seed")

def verify_fresh_transfer():
    specs=[
        ("fresh3-first",3,0,0.65),
        ("fresh5-mid",5,2,0.65),
        ("fresh5-last",5,4,0.65),
        ("fresh7-early",7,1,0.65),
        ("fresh7-late",7,5,0.65),
        ("fresh9-mid",9,4,0.65),
        ("fresh9-last",9,8,0.65),
        ("fresh11-early",11,2,0.65),
        ("fresh11-mid",11,6,0.65),
        ("fresh11-last",11,10,0.65),
    ]
    rows=[]
    for name,n,truth,p in specs:
        agent=make_agent(n,truth,p)
        traj=record_failure(agent,name)
        result=attribute(traj,agent,verifier,rollouts=80,method="contrastive",base_seed=7000+n+truth)
        rows.append((name,truth,result.culprit_index,result.point_of_commitment))
    wrong=[r for r in rows if r[1]!=r[2]]
    assert not wrong, rows
    return rows

if __name__ == "__main__":
    verify_no_external_runtime_route()
    rows=verify_fresh_transfer()
    print("BRAIN_OWNED_CAUSAL_FALSIFICATION_PASS")
    for row in rows:
        print(*row)

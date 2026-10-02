from canonical.runtime.shared_decision_primitives import *

# Tool choice: never pick unknown/unauthorized and choose cheapest sufficient verified route.
routes=[
    ToolRoute("a",frozenset({"read","write"}),3),
    ToolRoute("b",frozenset({"read","write"}),1),
    ToolRoute("c",frozenset({"read","write"}),0,verified=False),
    ToolRoute("d",frozenset({"read","write"}),0,authorized=False),
]
assert select_verified_tool({"write"},routes).route_id=="b"
assert select_verified_tool({"execute"},routes).status=="ESCALATE"

# Delegation: dependencies and worker capability are hard gates; critical-path work wins.
tasks=[
    Task("root",frozenset(),frozenset({"plan"})),
    Task("long",frozenset({"root"}),frozenset({"code"})),
    Task("tail",frozenset({"long"}),frozenset({"test"})),
    Task("side",frozenset(),frozenset({"write"}),priority=2),
]
workers=[Worker("w1",frozenset({"plan","code"})),Worker("w2",frozenset({"write","test"}))]
a=assign_ready_tasks(tasks,workers,completed=set())
assert a["root"]=="w1" and a["side"]=="w2"
a=assign_ready_tasks(tasks,workers,completed={"root","side"})
assert a=={"long":"w1"}

# Research control: stop exactly at full material coverage; otherwise maximize verified coverage/cost.
acts=[
    ResearchAction("broad",frozenset({"r1","r2"}),2,1),
    ResearchAction("cheap",frozenset({"r1"}),0.2,1),
    ResearchAction("unknown",frozenset({"r1","r2","r3"}),0.01,1,verified=False),
]
assert next_research_action({"r1","r2"},set(),acts).action_id=="cheap"
assert next_research_action({"r1","r2"},{"r1"},acts).action_id=="broad"
assert next_research_action({"r1"},{"r1"},acts).status=="STOP"

# Evidence synthesis: exact minimum complete nonconflicting support.
units=[
    EvidenceUnit("e1",frozenset({"c1"}),1),
    EvidenceUnit("e2",frozenset({"c2"}),1),
    EvidenceUnit("e12",frozenset({"c1","c2"}),1.5),
    EvidenceUnit("bad",frozenset({"c1","c2"}),0.1,conflicts_with=frozenset({"e1"})),
]
d=minimal_support_bundle({"c1","c2"},units)
assert d.status=="PASS" and d.evidence_ids==("bad",)
d=minimal_support_bundle({"missing"},units)
assert d.status=="ESCALATE" and "missing" in d.unsupported_claims

# Repair: earliest supported causal target beats downstream symptom.
cs=[
    FailureCandidate("symptom",8,True,True,.9,.9),
    FailureCandidate("root",2,True,True,.7,.6),
    FailureCandidate("guess",1,False,True,1,1),
]
assert select_repair_target(cs).candidate_id=="root"

# Exhaustive tiny tool-routing invariant: selected route is always verified, available, authorized and sufficient.
caps=[frozenset(),frozenset({"x"}),frozenset({"x","y"})]
for required in caps:
    rr=[]
    for i,c in enumerate(caps):
        rr.append(ToolRoute(str(i),c,float(i),available=(i!=0),authorized=True,verified=True))
    dec=select_verified_tool(required,rr)
    if dec.status=="SELECT":
        chosen=next(r for r in rr if r.route_id==dec.route_id)
        assert chosen.available and chosen.authorized and chosen.verified and required.issubset(chosen.capabilities)

print("shared_decision_primitives: PASS")

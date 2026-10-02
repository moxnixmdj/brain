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


# Regression: exact support optimization minimizes COST globally, not cardinality.
units_cost=[
    EvidenceUnit("expensive",frozenset({"c1","c2"}),100,1),
    EvidenceUnit("cheap1",frozenset({"c1"}),1,1),
    EvidenceUnit("cheap2",frozenset({"c2"}),1,1),
]
d=minimal_support_bundle({"c1","c2"},units_cost)
assert d.status=="PASS" and d.evidence_ids==("cheap1","cheap2"), d

# Duplicate identities and invalid numeric state fail closed.
assert select_verified_tool({"x"},[
    ToolRoute("dup",frozenset({"x"}),1),
    ToolRoute("dup",frozenset({"x"}),0),
]).status=="ESCALATE"
assert next_research_action({"r"},set(),[
    ResearchAction("dup",frozenset({"r"}),1),
    ResearchAction("dup",frozenset({"r"}),1),
]).status=="ESCALATE"
assert minimal_support_bundle({"c"},[
    EvidenceUnit("e",frozenset({"c"}),-1,1),
]).status=="ESCALATE"
assert select_repair_target([
    FailureCandidate("dup",1,True,True,.9,.9),
    FailureCandidate("dup",2,True,True,.9,.9),
]).status=="ESCALATE"

print("shared_decision_primitives_hardening: PASS")

# Artifact planning: global minimum total cost across all subset cardinalities.
ops=[
    ArtifactOperation("text",frozenset({"replace_text"}),1),
    ArtifactOperation("table",frozenset({"edit_table"}),1),
    ArtifactOperation("both",frozenset({"replace_text","edit_table"}),3),
    ArtifactOperation("destructive",frozenset({"replace_text","edit_table"}),0,preserves_unrequested_structure=False),
]
p=plan_artifact_operations({"replace_text","edit_table"},ops)
assert p.status=="PASS" and p.operation_ids==("table","text")
assert plan_artifact_operations({"pdf_redaction"},ops).status=="ESCALATE"
assert plan_artifact_operations({"replace_text"},[
    ArtifactOperation("dup",frozenset({"replace_text"})),
    ArtifactOperation("dup",frozenset({"replace_text"})),
]).status=="ESCALATE"

# Non-replayable failure candidates: complete prior decision set without causal overclaim.
td=[
    TraceDecision("d1",1),
    TraceDecision("d2",2,intervenable=False),
    TraceDecision("d3",3),
    TraceDecision("after",5),
]
fc=enumerate_nonreplayable_failure_candidates(td,4)
assert fc.status=="CANDIDATES" and fc.candidate_ids==("d1","d3")
assert "NO_CAUSAL_CLAIM" in fc.reason
assert enumerate_nonreplayable_failure_candidates(td,1).status=="ESCALATE"
assert enumerate_nonreplayable_failure_candidates([TraceDecision("x",-1)],2).status=="ESCALATE"

print("shared_decision_primitives_m2_m4_m5: PASS")


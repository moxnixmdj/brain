"""Measurement: can a created distinction recover a condition selection cannot?

Protocol, stated so it can be attacked:
  * Each case is a real condition of the kind a fix introduces.
  * The synthesiser sees ONLY labelled examples. It never sees `human`.
  * Evidence is sampled two ways: random (no edge), and edge-inclusive.
  * Scoring is on a 500-value holdout, exhaustive over the domain where small.
  * The loop condition is: after answering the guard's own next_probes, does the
    guard agree with the human everywhere?
"""
import json, random
from canonical.swe_kernel import distinction_creation_v1 as dc

CASES=[
 ("byte 0..255","n",lambda v:0<=v<=255, (-1,256), (0,1,128,255)),
 ("percent 0..100","p",lambda v:0<=v<=100, (-1,101), (0,1,50,100)),
 ("port 1..65535","p",lambda v:1<=v<=65535, (0,65536), (1,80,443,65535)),
 ("positive int","d",lambda v:v>=1, (0,-1,-99), (1,2,99)),
]

def to_guard(r):
    return dc.Guard([(a["feature"],a["op"],tuple(a["operand"]) if a["op"]=="between" else a["operand"]) for a in r["guard"]["atoms"]])

def score(g,feat,human,lo,hi):
    vals=list(range(lo,hi)) if hi-lo<=5000 else [random.randrange(lo,hi) for _ in range(500)]
    agree=sum(1 for v in vals if g.holds({feat:v})==human(v))
    return agree,len(vals)

rows=[]
for name,feat,human,edge,posvals in CASES:
    # RANDOM evidence: negatives drawn far from the edge
    rnd=random.Random(7)
    far=[e for e in edge]
    r_neg=[{feat:far[0]-1-rnd.randrange(0,500)} if rnd.random()<0.5 else {feat:far[1]+rnd.randrange(0,5000)} for _ in range(3)]
    r_pos=[{feat:v} for v in posvals]
    # EDGE evidence: negatives exactly at the boundary
    e_neg=[{feat:e} for e in edge]
    out={}
    for label,pos,neg in (("random",r_pos,r_neg),("edge",r_pos,e_neg)):
        got=dc.synthesise_guard(pos,neg)
        if got["status"]!="PASS__GUARD_SYNTHESISED":
            out[label]=(got["status"],"n/a"); continue
        g=to_guard(got); a,t=score(g,feat,human,min(edge)-300,max(edge)+300)
        out[label]=(got["guard"]["render"],f"{a}/{t}")
    # THE LOOP: random evidence, then answer the module's own probes
    got=dc.synthesise_guard(r_pos,r_neg)
    looped="n/a"
    if got["status"]=="PASS__GUARD_SYNTHESISED":
        cur_neg=list(r_neg)
        probes=got["next_probes"]
        if probes:
            # the world answers with the human's rule
            for pr in probes[:1]:
                val=int(pr["ask"].split("=")[1].split()[0])
                if not human(val): cur_neg.append({feat:val})
            g2=dc.synthesise_guard(r_pos,cur_neg)
            if g2["status"]=="PASS__GUARD_SYNTHESISED":
                a,t=score(to_guard(g2),feat,human,min(edge)-300,max(edge)+300)
                looped=f"{g2['guard']['render']} {a}/{t}"
    rows.append({"case":name,"random":out["random"],"edge":out["edge"],"after_one_probe":looped})

print(json.dumps(rows,indent=2))
edge_ok=sum(1 for r in rows if r["edge"][1].split("/")[0]==r["edge"][1].split("/")[1])
print(f"\nedge evidence exact: {edge_ok}/{len(rows)}")

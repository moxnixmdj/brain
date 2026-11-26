"""The closed loop: synthesise, ask, answer honestly, re-synthesise. Repeat.

The world here is the human's condition, used ONLY to answer questions -- never
to pick the guard. This is the honest form of 'the test supplies the distinction'.
"""
import random
from canonical.swe_kernel import distinction_creation_v1 as dc

def to_guard(r):
    return dc.Guard([(a["feature"],a["op"],tuple(a["operand"]) if a["op"]=="between" else a["operand"]) for a in r["guard"]["atoms"]])

def score(g,feat,human,lo,hi):
    vals=list(range(lo,hi))
    return sum(1 for v in vals if g.holds({feat:v})==human(v)), len(vals)

CASES=[
 ("byte 0..255","n",lambda v:0<=v<=255,(-1,256),(0,1,128,255)),
 ("percent 0..100","p",lambda v:0<=v<=100,(-1,101),(0,1,50,100)),
 ("port 1..65535","p",lambda v:1<=v<=65535,(0,65536),(1,80,443,65535)),
 ("positive int","d",lambda v:v>=1,(-99,1000),(1,2,99)),
]

for name,feat,human,(lo_n,hi_n),posvals in CASES:
    rnd=random.Random(7)
    pos=[{feat:v} for v in posvals]
    neg=[{feat:lo_n-1-rnd.randrange(0,50)} for _ in range(2)]+[{feat:hi_n+rnd.randrange(0,50)}]
    asked=[]; rounds=0
    cur=(pos,neg)
    while rounds<8:
        rounds+=1
        got=dc.synthesise_guard(*cur)
        if got["status"]!="PASS__GUARD_SYNTHESISED": break
        probes=got["next_probes"]
        if not probes: break
        pr=probes[0]
        val=int(pr["ask"].split("=")[1].split()[0])
        asked.append(val)
        # the world answers with the human rule
        (cur[0] if human(val) else cur[1]).append({feat:val})
    g=to_guard(got)
    a,t=score(g,feat,human,lo_n-200,hi_n+200)
    print(f"{name:16s} round {rounds}  {g.render():26s} {a}/{t}  asked={asked}")

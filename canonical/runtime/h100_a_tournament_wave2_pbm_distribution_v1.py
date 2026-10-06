"""Frozen Wave2 PBM bar-chart task distribution. Evaluation-only generator."""
from __future__ import annotations

MASK=(1<<64)-1

class Rng:
    def __init__(self,seed:int):
        self.state=int(seed)&MASK
    def next(self)->int:
        self.state=(self.state+0x9E3779B97F4A7C15)&MASK
        z=self.state
        z=(z^(z>>30))*0xBF58476D1CE4E5B9&MASK
        z=(z^(z>>27))*0x94D049BB133111EB&MASK
        return (z^(z>>31))&MASK
    def randrange(self,lo:int,hi:int)->int:
        if hi<=lo: raise ValueError("RANGE")
        return lo+self.next()%(hi-lo)

def _unique_values(r:Rng,n:int)->list[int]:
    out=[]
    while len(out)<n:
        v=r.randrange(10,91)
        if v not in out: out.append(v)
    return out

def _pbm(pix:list[list[int]])->str:
    h=len(pix); w=len(pix[0])
    return "P1\n%d %d\n"%(w,h)+"\n".join(" ".join(map(str,row)) for row in pix)+"\n"

def generate(seed:int)->dict:
    r=Rng(seed)
    w=80; h=50
    n=r.randrange(3,8)
    orientation="VERTICAL" if r.randrange(0,2)==0 else "HORIZONTAL"
    values=_unique_values(r,n)
    pix=[[0]*w for _ in range(h)]
    bar_thickness=r.randrange(3,7)
    gap=r.randrange(3,7)

    if orientation=="VERTICAL":
        axis_x=r.randrange(3,8)
        baseline=r.randrange(40,46)
        for y in range(3,baseline+1): pix[y][axis_x]=1
        for x in range(axis_x,w-3): pix[baseline][x]=1
        max_len=max(8,baseline-8)
        start=axis_x+3
        step=bar_thickness+gap
        if start+(n-1)*step+bar_thickness>=w-3:
            gap=3; step=bar_thickness+gap
        lengths=[]
        for i,v in enumerate(values):
            length=max(2,round(v/90*max_len))
            lengths.append(length)
            x0=start+i*step
            bottom=baseline-2
            top=bottom-length+1
            for y in range(top,bottom+1):
                for x in range(x0,x0+bar_thickness): pix[y][x]=1
    else:
        axis_x=r.randrange(5,10)
        top_axis=r.randrange(3,7)
        for y in range(top_axis,h-3): pix[y][axis_x]=1
        for x in range(axis_x,w-3): pix[h-4][x]=1
        max_len=w-axis_x-8
        start_y=top_axis+2
        step=bar_thickness+gap
        if start_y+(n-1)*step+bar_thickness>=h-5:
            gap=2; step=bar_thickness+gap
        lengths=[]
        for i,v in enumerate(values):
            length=max(2,round(v/90*max_len))
            lengths.append(length)
            y0=start_y+i*step
            x0=axis_x+2
            for y in range(y0,y0+bar_thickness):
                for x in range(x0,x0+length): pix[y][x]=1

    qtype=("ARGMAX_INDEX","ARGMIN_INDEX","COUNT_BARS","COMPARE_I_GT_J")[r.randrange(0,4)]
    question={"type":qtype}
    if qtype=="COMPARE_I_GT_J":
        i=r.randrange(0,n); j=r.randrange(0,n-1)
        if j>=i: j+=1
        question.update({"i":i,"j":j})
    if qtype=="ARGMAX_INDEX": answer=max(range(n),key=lambda i:values[i])
    elif qtype=="ARGMIN_INDEX": answer=min(range(n),key=lambda i:values[i])
    elif qtype=="COUNT_BARS": answer=n
    else: answer=values[question["i"]]>values[question["j"]]

    return {
        "seed":int(seed)&MASK,
        "media_type":"image/x-portable-bitmap",
        "pbm_text":_pbm(pix),
        "question":question,
        "oracle":{"orientation":orientation,"values":values,"lengths":lengths,"answer":answer},
    }

from __future__ import annotations
import math

XS=[-4,-3.5,-3,-2.5,-2,-1.5,-1,-0.6,-0.2,0,0.4,0.8,1,1.5,2,2.5,3,3.5,4]

OPS={
 "square":lambda v:v*v,
 "log1p_abs":lambda v:math.log1p(abs(v)),
 "sqrt_abs":lambda v:math.sqrt(abs(v)),
 "sat":lambda v:v/(1.0+abs(v)),
}

TASKS=[
 ("A",["square","log1p_abs","sqrt_abs","sat"],(-0.7,0.31,-0.85)),
 ("B",["sat","square","log1p_abs","sqrt_abs"],(0.9,-0.22,1.4)),
 ("C",["log1p_abs","sat","sqrt_abs","log1p_abs"],(-0.35,-0.08,0.72)),
]

def apply(x,seq):
    v=float(x)
    for op in seq: v=OPS[op](v)
    return v

def nrmse(actual,pred):
    mean=sum(actual)/len(actual)
    spread=math.sqrt(sum((x-mean)**2 for x in actual)/len(actual))
    scale=max(spread,max(abs(x) for x in actual)*1e-9,1e-12)
    return math.sqrt(sum((a-b)**2 for a,b in zip(actual,pred))/len(actual))/scale

def quantize(v,fractional_bits):
    step=2.0**(-fractional_bits)
    q=round(v/step)*step
    if not (-2.0<=q<2.0): raise ValueError("COEFF_RANGE")
    return q

def measure_task(task,fractional_bits):
    tid,seq,coeff=task
    q=tuple(quantize(v,fractional_bits) for v in coeff)
    actual=[coeff[0]+coeff[1]*x+coeff[2]*apply(x,seq) for x in XS]
    pred=[q[0]+q[1]*x+q[2]*apply(x,seq) for x in XS]
    return {"task":tid,"fractional_bits":fractional_bits,"quantized_coefficients":q,"nrmse":nrmse(actual,pred)}

def minimum_fractional_bits(task,threshold=1e-8,max_bits=40):
    for q in range(max_bits+1):
        r=measure_task(task,q)
        if r["nrmse"]<=threshold:
            return r
    raise ValueError("NO_PASS")

def description_bits(result):
    q=result["fractional_bits"]
    return 11+3*(q+2)

def run():
    rows=[]
    for task in TASKS:
        r=minimum_fractional_bits(task)
        r["target_adapted_description_bits"]=description_bits(r)
        rows.append(r)
    return {
      "rows":rows,
      "max_target_adapted_description_bits":max(r["target_adapted_description_bits"] for r in rows),
      "mean_target_adapted_description_bits":sum(r["target_adapted_description_bits"] for r in rows)/len(rows),
      "persistent_learned_bytes":0
    }

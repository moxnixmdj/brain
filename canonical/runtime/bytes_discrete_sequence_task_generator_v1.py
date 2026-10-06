from __future__ import annotations
import hashlib,json

K="141f0d17efddb7f3401659c348713eb9a5e996d03b2480f12a49353660a69546"
O=("rev","sort","uniq","rotl","rotr","neg","abs","inc","dec","dbl","pos","negonly","even","odd")

class S:
 def __init__(self):self.i=0
 def n(self):
  b=hashlib.sha256((K+":"+str(self.i)).encode()).digest();self.i+=1
  return int.from_bytes(b[:8],"big")
 def p(self,x):return x[self.n()%len(x)]

def a(o,x):
 if o=="rev":return x[::-1]
 if o=="sort":return sorted(x)
 if o=="uniq":return list(dict.fromkeys(x))
 if not x and o in ("rotl","rotr"):return []
 if o=="rotl":return x[1:]+x[:1]
 if o=="rotr":return x[-1:]+x[:-1]
 if o=="neg":return [-v for v in x]
 if o=="abs":return [abs(v) for v in x]
 if o=="inc":return [v+1 for v in x]
 if o=="dec":return [v-1 for v in x]
 if o=="dbl":return [2*v for v in x]
 if o=="pos":return [v for v in x if v>0]
 if o=="negonly":return [v for v in x if v<0]
 if o=="even":return [v for v in x if v%2==0]
 if o=="odd":return [v for v in x if v%2!=0]
 raise ValueError(o)

def run(p,x):
 y=list(x)
 for o in p:y=a(o,y)
 return y

BASE=[
 [3,-1,3,0,-2,4],[-4,2,-4,1,0],[5,1,-3,2,-1],[2,2,0,-2,-2,3],
 [1,-5,4,1,-1,2],[-3,0,3,-3,6,2],[4,-2,1,4,0,-1],[0,5,-5,2,2,-4],
 [6,1,-2,6,-3,0],[-1,-1,4,3,-2,5]
]
HOLD=[
 [7,-2,7,1,-6,0],[-5,3,0,-5,2,8],[2,-7,4,2,-1,6],[9,0,-3,3,-9,1],
 [-4,5,-4,0,7,-2],[1,8,-6,1,2,-3]
]

def behavior(p,xs):return tuple(tuple(run(p,x)) for x in xs)

def generate():
 s=S();tasks=[];seen=set();identity=behavior((),BASE)
 while len(tasks)<8:
  n=1+s.n()%3;p=tuple(s.p(O) for _ in range(n));b=behavior(p,BASE)
  if b==identity or b in seen or all(len(z)==0 for z in b):continue
  seen.add(b);i=len(tasks)+1
  tasks.append({
   "id":f"SEQ_V1_T{i}",
   "train":[{"input":x,"output":run(p,x)} for x in BASE],
   "holdout":[{"input":x,"output":run(p,x)} for x in HOLD],
   "truth_program":list(p)
  })
 return {
  "schema":"PROJECT_BRAIN_BYTES_DISCRETE_SEQUENCE_PROSPECTIVE_TASKS_V1",
  "kernel_sha256":K,
  "derivation":"SHA256_COUNTER_STREAM_FROM_FROZEN_KERNEL_SHA256",
  "task_count":len(tasks),
  "success":{"all_tasks_required":True,"all_holdouts_exact":True},
  "tasks":tasks
 }

if __name__=="__main__":print(json.dumps(generate(),sort_keys=True,separators=(",",":")))

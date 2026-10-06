from __future__ import annotations
import hashlib,json,itertools

K="4ebd2d8ae5a540af3c0df0dc001fc857d54423394082d967c774ed9866d01904"
O="naid2pmeoq"
TRAIN=(-9,-7,-5,-3,-2,-1,0,1,2,4,6,8)
HOLD=(-10,-8,-6,-4,3,5,7,9,11)
TARGET_DEPTHS=(1,2,3,1,2,3,2,3,3)

class S:
 def __init__(self):self.i=0
 def n(self):
  b=hashlib.sha256((K+":"+str(self.i)).encode()).digest();self.i+=1
  return int.from_bytes(b[:8],"big")
 def p(self,x):return x[self.n()%len(x)]

def f(o,x):
 if o=="n":return -x
 if o=="a":return abs(x)
 if o=="i":return x+1
 if o=="d":return x-1
 if o=="2":return 2*x
 if o=="p":return x>0
 if o=="m":return x<0
 if o=="e":return x%2==0
 if o=="o":return x%2!=0
 if o=="q":return x*x
 raise ValueError(o)

def run(p,x):
 y=x
 for o in p:y=f(o,y)
 return y

def beh(p,xs):return tuple(run(p,x) for x in xs)

def min_depth_for(b):
 for d in range(4):
  for p in itertools.product(O,repeat=d):
   if beh(p,TRAIN)==b:return d
 return None

def generate():
 s=S();tasks=[];seen=set()
 for target_depth in TARGET_DEPTHS:
  while True:
   p=tuple(s.p(O) for _ in range(target_depth))
   b=beh(p,TRAIN)
   if b in seen or b==TRAIN:continue
   if min_depth_for(b)!=target_depth:continue
   if len(set(b))<2:continue
   seen.add(b);break
  tasks.append({
   "id":f"SCALAR_V1_T{len(tasks)+1}",
   "minimal_depth":target_depth,
   "train":[{"input":x,"output":run(p,x)} for x in TRAIN],
   "holdout":[{"input":x,"output":run(p,x)} for x in HOLD],
   "truth_program":list(p)
  })
 return {
  "schema":"PROJECT_BRAIN_BYTES_SCALAR_EXACT_PROSPECTIVE_TASKS_V1",
  "kernel_sha256":K,
  "derivation":"SHA256_COUNTER_STREAM_FROM_FROZEN_V7_KERNEL_SHA256",
  "operator_alphabet":O,
  "task_count":len(tasks),
  "required_depths":list(TARGET_DEPTHS),
  "success":{"all_tasks_required":True,"all_holdouts_exact":True},
  "tasks":tasks
 }

if __name__=="__main__":print(json.dumps(generate(),sort_keys=True,separators=(",",":")))

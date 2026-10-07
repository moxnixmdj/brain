from __future__ import annotations
import hashlib,itertools,json
K="e6e5b85368d8e87f82754e86663270315e4d7f059602e6190e9dc4a685bcc139"
A="+-<>[]";T=(0,1,2,3,5);H=(4,6,7,9)
def v(p):
 d=0
 for o in p:
  d+=(o=="[")-(o=="]")
  if d<0:return 0
 return d==0
def r(p,x,s=512):
 t={0:x%256};q=i=n=0
 while i<len(p) and n<s:
  o=p[i];z=t.get(q,0)
  if o=="+":t[q]=(z+1)%256
  elif o=="-":t[q]=(z-1)%256
  elif o==">":q+=1
  elif o=="<":q-=1
  elif o=="[" and z==0:
   d=1
   while d:i+=1;d+=(p[i]=="[")-(p[i]=="]")
  elif o=="]" and z:
   d=1
   while d:i-=1;d+=(p[i]=="]")-(p[i]=="[")
  i+=1;n+=1
 if i<len(p):return
 return (t.get(0,0),t.get(1,0))
class S:
 def __init__(self):self.i=0
 def n(self):
  b=hashlib.sha256((K+":LOOP_TARGET:"+str(self.i)).encode()).digest();self.i+=1
  return int.from_bytes(b[:8],"big")
def generate():
 P=[]
 for n in range(7):
  for q in itertools.product(A,repeat=n):
   p="".join(q)
   if not v(p):continue
   y=[r(p,x) for x in T+H]
   if None in y:continue
   P.append((p,tuple(y[:len(T)]),tuple(y[len(T):])))
 g={}
 for p,t,h in P:g.setdefault(t,[]).append((p,h))
 C=[]
 for t,z in g.items():
  hs={h for _,h in z};ps=[p for p,_ in z]
  if len(hs)!=1 or any("[" not in p for p in ps) or len(set(t))<2:continue
  m=min(map(len,ps))
  if m<4:continue
  C.append((repr(t),t,next(iter(hs)),sorted(ps),m))
 C.sort()
 s=S();tasks=[];used=set()
 while len(tasks)<8:
  c=C[s.n()%len(C)]
  if c[0] in used:continue
  used.add(c[0]);_,t,h,ps,m=c;p=ps[s.n()%len(ps)]
  tasks.append({"id":f"VM_V1_T{len(tasks)+1}","train":[{"input":x,"output":list(y)} for x,y in zip(T,t)],"holdout":[{"input":x,"output":list(y)} for x,y in zip(H,h)],"truth_program":p,"minimum_program_length_in_closure":m,"matching_program_count":len(ps)})
 return {"schema":"PROJECT_BRAIN_BYTES_LOWLEVEL_VM_PROSPECTIVE_TASKS_V1","kernel_sha256":K,"derivation":"HASH_SELECTED_STRICT_LOOP_REQUIRED_HOLDOUT_DETERMINATE_BEHAVIOR_CLASSES","task_count":len(tasks),"search_max_program_length":6,"step_limit":512,"success":{"all_tasks_required":True,"all_holdouts_exact":True},"tasks":tasks}
if __name__=="__main__":print(json.dumps(generate(),sort_keys=True,separators=(",",":")))

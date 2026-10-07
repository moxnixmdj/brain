from __future__ import annotations
import hashlib,itertools,json
K="e0e612fce8309dce1e744e4d694a45413d815846368ef911e20daec2418a195e"
L="RSu<>NADI2PMEO"
A=([3,-1,3,0,-2,4],[-4,2,-4,1,0],[5,1,-3,2,-1],[2,2,0,-2,-2,3],[1,-5,4,1,-1,2],[-3,0,3,-3,6,2],[4,-2,1,4,0,-1],[0,5,-5,2,2,-4],[6,1,-2,6,-3,0],[-1,-1,4,3,-2,5])
H=([7,-2,7,1,-6,0],[-5,3,0,-5,2,8],[2,-7,4,2,-1,6],[9,0,-3,3,-9,1],[-4,5,-4,0,7,-2],[1,8,-6,1,2,-3])
def f(o,x):
 if o=="R":return x[::-1]
 if o=="S":return sorted(x)
 if o=="u":return list(dict.fromkeys(x))
 if not x and o in"<>":return []
 if o=="<":return x[1:]+x[:1]
 if o==">":return x[-1:]+x[:-1]
 if o in"NADI2":
  q={"N":lambda v:-v,"A":abs,"D":lambda v:v-1,"I":lambda v:v+1,"2":lambda v:2*v}[o];return [q(v) for v in x]
 if o in"PMEO":
  q={"P":lambda v:v>0,"M":lambda v:v<0,"E":lambda v:v%2==0,"O":lambda v:v%2!=0}[o];return [v for v in x if q(v)]
 raise ValueError(o)
def r(p,x):
 y=list(x)
 for o in p:y=f(o,y)
 return y
def b(p,xs):return tuple(tuple(r(p,x)) for x in xs)
class S:
 def __init__(self):self.i=0
 def n(self):
  z=hashlib.sha256((K+":V9_TARGET:"+str(self.i)).encode()).digest();self.i+=1
  return int.from_bytes(z[:8],"big")
def generate():
 P=[p for d in range(4) for p in itertools.product(L,repeat=d)]
 g={}
 for p in P:g.setdefault(b(p,A),[]).append(p)
 C=[ps for ps in g.values() if len({b(p,H) for p in ps})>1]
 C.sort(key=lambda ps:repr(sorted(ps)))
 s=S();tasks=[]
 for i,ps in enumerate(C,1):
  ps=sorted(ps);t=ps[s.n()%len(ps)]
  tasks.append({"id":f"HBLIND_V1_T{i}","train":[{"input":list(x),"output":r(t,x)} for x in A],"holdout":[{"input":list(x),"output":r(t,x)} for x in H],"truth_program":list(t),"passive_class_program_count":len(ps),"passive_holdout_variant_count":len({b(p,H) for p in ps})})
 return {"schema":"PROJECT_BRAIN_BYTES_HBLIND_ACTIVE_QUERY_TASKS_V1","kernel_sha256":K,"derivation":"ONE_HASH_SELECTED_TARGET_FROM_EACH_PASSIVELY_AMBIGUOUS_DEPTH_LTE_3_SEQUENCE_CLASS","task_count":len(tasks),"query_pool":{"persistent":False,"size":2000,"derivation":"SHA256_KERNEL_HASH_PLUS_HBLIND_AQ_COUNTER","lengths":[6,7,8],"integer_range":[-8,8]},"success":{"all_tasks_required":True,"all_holdouts_exact":True,"max_adaptive_queries_per_task":4},"tasks":tasks}
if __name__=="__main__":print(json.dumps(generate(),sort_keys=True,separators=(",",":")))

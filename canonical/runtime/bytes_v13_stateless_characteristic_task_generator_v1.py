from __future__ import annotations
import hashlib,itertools,json
K="9bcefc2f199f507e5085b60d5055e160542b8d25c3e77ee6fa55691e70c55378"
L="RSu<>NADI2PMEO"
BASE=([3,-1,3,0,-2,4],[-4,2,-4,1,0],[5,1,-3,2,-1],[2,2,0,-2,-2,3],[1,-5,4,1,-1,2],[-3,0,3,-3,6,2],[4,-2,1,4,0,-1],[0,5,-5,2,2,-4],[6,1,-2,6,-3,0],[-1,-1,4,3,-2,5])
HOLD=([7,-2,7,1,-6,0],[-5,3,0,-5,2,8],[2,-7,4,2,-1,6],[9,0,-3,3,-9,1],[-4,5,-4,0,7,-2],[1,8,-6,1,2,-3])
def f(o,x):
 if o=="R":return x[::-1]
 if o=="S":return sorted(x)
 if o=="u":return list(dict.fromkeys(x))
 if not x and o in"<>":return []
 if o=="<":return x[1:]+x[:1]
 if o==">":return x[-1:]+x[:-1]
 if o=="N":return [-v for v in x]
 if o=="A":return [abs(v) for v in x]
 if o=="D":return [v-1 for v in x]
 if o=="I":return [v+1 for v in x]
 if o=="2":return [2*v for v in x]
 if o=="P":return [v for v in x if v>0]
 if o=="M":return [v for v in x if v<0]
 if o=="E":return [v for v in x if v%2==0]
 if o=="O":return [v for v in x if v%2!=0]
 raise ValueError(o)
def run(p,x):
 y=list(x)
 for o in p:y=f(o,y)
 return y
def beh(p,xs):return tuple(tuple(run(p,x)) for x in xs)
def generate():
 P=[p for d in range(4) for p in itertools.product(L,repeat=d)]
 g={}
 for p in P:g.setdefault(beh(p,BASE),[]).append(p)
 C=[ps for ps in g.values() if len({beh(p,HOLD) for p in ps})>1]
 C.sort(key=lambda ps:repr(sorted(ps)))
 tasks=[]
 for i,ps in enumerate(C,1):
  ps=sorted(ps);h=hashlib.sha256((K+":V13_TARGET:"+str(i)).encode()).digest();target=ps[int.from_bytes(h[:8],"big")%len(ps)]
  tasks.append({"id":f"V13_T{i}","train":[{"input":list(x),"output":run(target,x)} for x in BASE],"holdout":[{"input":list(x),"output":run(target,x)} for x in HOLD],"truth_program":list(target),"passive_class_program_count":len(ps),"passive_holdout_variant_count":len({beh(p,HOLD) for p in ps})})
 return {"schema":"PROJECT_BRAIN_BYTES_V13_GENERATED_CHARACTERISTIC_PROSPECTIVE_TASKS_V1","kernel_sha256":K,"derivation":"ONE_V13_HASH_SELECTED_TARGET_FROM_EACH_PASSIVELY_AMBIGUOUS_DEPTH_LTE_3_SEQUENCE_CLASS","task_count":len(tasks),"success":{"all_tasks_required":True,"all_holdouts_exact":True,"characteristic_queries_per_task":105},"tasks":tasks}
if __name__=="__main__":print(json.dumps(generate(),sort_keys=True,separators=(",",":")))

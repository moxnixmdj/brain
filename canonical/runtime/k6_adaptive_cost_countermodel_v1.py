from functools import lru_cache

W=("00","01","10","11")
A={w:{"a"+w} for w in W}
D={
 "r":(1,{"00":0,"01":0,"10":1,"11":1}),
 "l":(1,{"00":0,"01":1,"10":0,"11":0}),
 "q":(1,{"00":0,"01":0,"10":0,"11":1}),
}

def common(cell):
 s=set(A[cell[0]])
 for w in cell[1:]: s&=A[w]
 return bool(s)

@lru_cache(None)
def adaptive(cell,remaining):
 if common(cell): return 0
 best=None
 for d in remaining:
  groups={}
  for w in cell: groups.setdefault(D[d][1][w],[]).append(w)
  if len(groups)<2: continue
  rem=tuple(x for x in remaining if x!=d)
  vals=[adaptive(tuple(g),rem) for g in groups.values()]
  if any(v is None for v in vals): continue
  cost=D[d][0]+max(vals)
  best=cost if best is None else min(best,cost)
 return best

def static():
 import itertools
 for k in range(4):
  for c in itertools.combinations(D,k):
   groups={}
   for w in W: groups.setdefault(tuple(D[d][1][w] for d in c),[]).append(w)
   if all(common(tuple(g)) for g in groups.values()): return sum(D[d][0] for d in c)
 raise AssertionError

def verify():
 a=adaptive(W,tuple(D)); s=static()
 assert a==2 and s==3
 return {"adaptive_worst_case_cost":a,"static_cost":s,"strict_improvement":True,"terminal_credit_delta":0}

if __name__=="__main__":
 import json; print(json.dumps(verify(),sort_keys=True))

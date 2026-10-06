import math
U=("neg","abs","square","sqrt_abs","log1p_abs","sat")
B=("add","sub","mul","stable_div")

def u(o,x):
 try:
  if o=="neg": y=-x
  elif o=="abs": y=abs(x)
  elif o=="square": y=x*x
  elif o=="sqrt_abs": y=math.sqrt(abs(x))
  elif o=="log1p_abs": y=math.log1p(abs(x))
  elif o=="sat": y=x/(1+abs(x))
  else:return None
  return y if math.isfinite(y) else None
 except:return None

def b(o,x,y):
 try:
  if o=="add": z=x+y
  elif o=="sub": z=x-y
  elif o=="mul": z=x*y
  elif o=="stable_div": z=x/(1+abs(y))
  else:return None
  return z if math.isfinite(z) else None
 except:return None

def e(t,r):
 o=t[0]
 if o=="v": return float(r[t[1]])
 if len(t)==2:
  x=e(t[1],r); y=u(o,x)
 else:
  x=e(t[1],r); y=e(t[2],r); y=b(o,x,y)
 if y is None: raise ValueError
 return y

def solve(a,v):
 n=len(v); a=[list(map(float,a[i]))+[float(v[i])] for i in range(n)]
 for c in range(n):
  q=max(range(c,n),key=lambda r:abs(a[r][c]))
  if abs(a[q][c])<1e-10:return
  a[c],a[q]=a[q],a[c]; z=a[c][c]; a[c]=[x/z for x in a[c]]
  for r in range(n):
   if r==c:continue
   z=a[r][c]
   if abs(z)>1e-12:a[r]=[x-z*y for x,y in zip(a[r],a[c])]
 return [a[i][-1] for i in range(n)]

def fit(fs,y):
 n=len(y); p=len(fs)+1; a=[[0.0]*p for _ in range(p)]; v=[0.0]*p
 for k in range(n):
  q=[1.0]+[f[k] for f in fs]
  for i in range(p):
   v[i]+=q[i]*y[k]
   for j in range(p):a[i][j]+=q[i]*q[j]
 for i in range(p):a[i][i]+=1e-12
 return solve(a,v)

def er(y,p):
 m=sum(y)/len(y); s=(sum((x-m)**2 for x in y)/len(y))**.5
 s=max(s,max(abs(x) for x in y)*1e-9,1e-12)
 return (sum((a-b)**2 for a,b in zip(y,p))/len(y))**.5/s

def discover(rows,target="y",inputs=None,unary_depth=2,pool=48,exact=1e-8):
 names=tuple(inputs or sorted(k for k in rows[0] if k!=target))
 tr=[r for i,r in enumerate(rows) if i%4!=3]; va=[r for i,r in enumerate(rows) if i%4==3]
 yt=[float(r[target]) for r in tr]; ya=[float(r[target]) for r in rows]; yv=[float(r[target]) for r in va]
 base=[("v",n) for n in names]; layer=base[:]
 for _ in range(unary_depth):
  layer=[(o,t) for t in layer for o in U]; base+=layer
 rec=[]; seen=set()
 def add(t,kind):
  try:v=[e(t,r) for r in rows]
  except:return
  s=max(1.0,max(abs(x) for x in v)); k=tuple(round(x/s,10) for x in v)
  if k in seen:return
  seen.add(k); q=[e(t,r) for r in tr]; c=fit([q],yt)
  if c is None:return
  w=[e(t,r) for r in va]; z=[c[0]+c[1]*x for x in w]
  rec.append((er(yv,z),repr(t),t,v,q,kind))
 for t in base:add(t,0)
 for i,x in enumerate(base):
  for j,y in enumerate(base):
   for o in B:
    if o in ("add","mul") and j<i:continue
    add((o,x,y),1)
 rec.sort(key=lambda x:(x[0],x[1]))
 cand=[x for x in rec if x[5]==0]+rec[:pool]
 q=[]; have=set()
 for x in cand:
  if x[1] not in have:have.add(x[1]);q.append(x)
 best=None
 def score(z):
  fs=[x[4] for x in z]; c=fit(fs,yt)
  if c is None:return
  ts=[x[2] for x in z]
  pa=[c[0]+sum(c[j+1]*e(t,r) for j,t in enumerate(ts)) for r in rows]
  pv=[c[0]+sum(c[j+1]*e(t,r) for j,t in enumerate(ts)) for r in va]
  return max(er(ya,pa),er(yv,pv)),repr(ts),{"features":ts,"coefficients":c,"nrmse":er(ya,pa),"validation_nrmse":er(yv,pv)}
 for x in q:
  z=score([x])
  if z and (best is None or z[:2]<best[:2]):best=z
 for i,x in enumerate(q):
  for y in q[i+1:]:
   z=score([x,y])
   if z and (best is None or z[:2]<best[:2]):best=z
 c=None if best is None else best[2]
 return {"status":"EXACT_CANDIDATE_FOUND" if best and best[0]<=exact else "MISS","best_candidate":c,"feature_count":len(rec)}

def predict(c,r):
 return c["coefficients"][0]+sum(c["coefficients"][i+1]*e(t,r) for i,t in enumerate(c["features"]))

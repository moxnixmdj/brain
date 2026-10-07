import math
U="naqrlt"
B="+-*/"
L="RSu<>NADI2PMEO"
G=L+"naqrltid2pmeo"
def f(o,x,y=None):
 try:
  if isinstance(x,list):
   if o=="R":return x[::-1]
   if o=="S":return sorted(x)
   if o=="u":return list(dict.fromkeys(x))
   if not x and o in"<>":return []
   if o=="<":return x[1:]+x[:1]
   if o==">":return x[-1:]+x[:-1]
   if o in"NADI2":return [f(o.lower(),v) for v in x]
   if o in"PMEO":return [v for v in x if f(o.lower(),v)]
  elif y is None:
   if o=="n":z=-x
   elif o=="a":z=abs(x)
   elif o=="q":z=x*x
   elif o=="r":z=math.sqrt(abs(x))
   elif o=="l":z=math.log1p(abs(x))
   elif o=="t":z=x/(1+abs(x))
   elif o=="i":z=x+1
   elif o=="d":z=x-1
   elif o=="2":z=2*x
   elif o=="p":return x>0
   elif o=="m":return x<0
   elif o=="e":return x%2==0
   elif o=="o":return x%2!=0
   else:return
   return z if math.isfinite(z) else None
  else:
   if o=="+":z=x+y
   elif o=="-":z=x-y
   elif o=="*":z=x*y
   elif o=="/":z=x/(1+abs(y))
   else:return
   return z if math.isfinite(z) else None
 except:return
def ev(t,r):
 if t[0]=="v":
  z=r[t[1]];return list(z) if isinstance(z,list) else float(z)
 if len(t)==2:return f(t[0],ev(t[1],r))
 return f(t[0],ev(t[1],r),ev(t[2],r))
def sl(a,v):
 n=len(v);a=[list(map(float,a[i]))+[float(v[i])] for i in range(n)]
 for c in range(n):
  p=max(range(c,n),key=lambda r:abs(a[r][c]))
  if abs(a[p][c])<1e-10:return
  a[c],a[p]=a[p],a[c];z=a[c][c];a[c]=[x/z for x in a[c]]
  for r in range(n):
   if r!=c:
    z=a[r][c]
    if abs(z)>1e-12:a[r]=[x-z*y for x,y in zip(a[r],a[c])]
 return [a[i][-1] for i in range(n)]
def ft(fs,y):
 n=len(y);p=len(fs)+1;a=[[0.]*p for _ in range(p)];v=[0.]*p
 for k in range(n):
  q=[1.]+[x[k] for x in fs]
  for i in range(p):
   v[i]+=q[i]*y[k]
   for j in range(p):a[i][j]+=q[i]*q[j]
 for i in range(p):a[i][i]+=1e-12
 return sl(a,v)
def er(y,p):
 m=sum(y)/len(y);s=max((sum((x-m)**2 for x in y)/len(y))**.5,max(abs(x) for x in y)*1e-9,1e-12)
 return (sum((a-b)**2 for a,b in zip(y,p))/len(y))**.5/s
def dx(rows,target="y",inputs=None,pool=1):
 ns=tuple(inputs or sorted(k for k in rows[0] if k!=target));tr=[r for i,r in enumerate(rows) if i%4!=3];va=[r for i,r in enumerate(rows) if i%4==3]
 yt=[float(r[target]) for r in tr];ya=[float(r[target]) for r in rows];yv=[float(r[target]) for r in va]
 bs=[("v",n) for n in ns];la=bs[:]
 for _ in range(2):la=[(o,t) for t in la for o in U];bs+=la
 z=[];seen=set()
 def ad(t,k):
  try:v=[ev(t,r) for r in rows]
  except:return
  s=max(1.,max(abs(x) for x in v));h=tuple(round(x/s,10) for x in v)
  if h in seen:return
  seen.add(h);q=[ev(t,r) for r in tr];c=ft([q],yt)
  if c is None:return
  w=[ev(t,r) for r in va];z.append((er(yv,[c[0]+c[1]*x for x in w]),repr(t),t,q,k))
 for t in bs:ad(t,0)
 for i,x in enumerate(bs):
  for j,y in enumerate(bs):
   for o in B:
    if o in"+*" and j<i:continue
    ad((o,x,y),1)
 z.sort();q=[];h=set()
 for x in [x for x in z if x[4]==0]+z[:pool]:
  if x[1] not in h:h.add(x[1]);q.append(x)
 best=None
 def sc(w):
  c=ft([x[3] for x in w],yt)
  if c is None:return
  ts=[x[2] for x in w]
  pa=[c[0]+sum(c[j+1]*ev(t,r) for j,t in enumerate(ts)) for r in rows];pv=[c[0]+sum(c[j+1]*ev(t,r) for j,t in enumerate(ts)) for r in va]
  return max(er(ya,pa),er(yv,pv)),repr(ts),{"f":ts,"c":c}
 for x in q:
  w=sc([x])
  if w and(best is None or w[:2]<best[:2]):best=w
 for i,x in enumerate(q):
  for y in q[i+1:]:
   w=sc([x,y])
   if w and(best is None or w[:2]<best[:2]):best=w
 return {"status":"EXACT" if best and best[0]<=1e-8 else "MISS","c":None if best is None else best[2]}
def px(c,r):return c["c"][0]+sum(c["c"][i+1]*ev(t,r) for i,t in enumerate(c["f"]))
def rp(p,x):
 for o in p:x=f(o,x)
 return x
def ds(ex,d=3):
 q=[()]
 for _ in range(d+1):
  n=[]
  for p in q:
   if all(rp(p,x)==y for x,y in ex):return {"status":"EXACT","t":p}
   n += [p+(o,) for o in G]
  q=n
 return {"status":"MISS","t":None}
def ps(c,x):return rp(c["t"],x)
def ci():
 for i in range(14):yield[(j*(2*j+10*i+16)+i*(6-5*i)+10)%33-16 for j in range(10)]
 yield[-4,-3];yield[1,2]
def aq(ex,d=3):
 q=[()];v=[]
 for _ in range(d+1):
  w=[]
  for p in q:
   if all(rp(p,x)==y for x,y in ex):v.append(p)
   w += [p+(o,) for o in G]
  q=w
 if len(v)<2:return
 b=None
 for x in ci():
  z={}
  for p in v:
   y=str(rp(p,x));z[y]=z.get(y,0)+1
  if len(z)>1:
   w=(max(z.values()),-len(z))
   if b is None or w<b[0]:b=(w,x)
   if w[0]==1:return x
 return b and b[1]

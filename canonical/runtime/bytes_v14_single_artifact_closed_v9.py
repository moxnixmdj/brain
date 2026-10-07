import math
U="naqrlt"
B="+-*/";a=[[(i&j+i|j)%17-8 for j in range(7)]for i in range(105)]
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
  elif y==None:
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
def V(t,r):
 if t[0]=="v":
  z=r[t[1]];return list(z) if isinstance(z,list) else float(z)
 if len(t)==2:return f(t[0],V(t[1],r))
 return f(t[0],V(t[1],r),V(t[2],r))
def T(fs,y):
 n=len(y);p=len(fs)+1;a=[[0.]*p for _ in range(p)];v=[0.]*p
 for k in range(n):
  q=[1.]+[x[k] for x in fs]
  for i in range(p):
   v[i]+=q[i]*y[k]
   for j in range(p):a[i][j]+=q[i]*q[j]
 for i in range(p):a[i][i]+=1e-12
 a=[a[i]+[v[i]] for i in range(p)]
 for c in range(p):
  z=a[c][c];a[c]=[x/z for x in a[c]]
  for r in range(p):
   if r-c:
    z=a[r][c];a[r]=[x-z*y for x,y in zip(a[r],a[c])]
 return [a[i][-1] for i in range(p)]
def E(y,p):
 m=sum(y)/len(y);s=max((sum((x-m)**2 for x in y)/len(y))**.5,max(abs(x) for x in y)*1e-9,1e-12)
 return (sum((a-b)**2 for a,b in zip(y,p))/len(y))**.5/s
def dx(rows,target="y",inputs=None,pool=1):
 ns=tuple(inputs or sorted(k for k in rows[0] if k!=target));tr=[r for i,r in enumerate(rows) if i%4!=3];va=[r for i,r in enumerate(rows) if i%4==3]
 yt=[float(r[target]) for r in tr];ya=[float(r[target]) for r in rows];yv=[float(r[target]) for r in va]
 bs=[("v",n) for n in ns];la=bs[:]
 for _ in range(2):la=[(o,t) for t in la for o in U];bs+=la
 z=[];seen=set()
 def ad(t,k):
  try:v=[V(t,r) for r in rows]
  except:return
  s=max(1.,max(abs(x) for x in v));h=tuple(round(x/s,10) for x in v)
  if h in seen:return
  seen.add(h);q=[V(t,r) for r in tr];c=T([q],yt)
  if c==None:return
  w=[V(t,r) for r in va];z.append((E(yv,[c[0]+c[1]*x for x in w]),repr(t),t,q,k))
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
  c=T([x[3] for x in w],yt)
  if c==None:return
  ts=[x[2] for x in w]
  pa=[c[0]+sum(c[j+1]*V(t,r) for j,t in enumerate(ts)) for r in rows];pv=[c[0]+sum(c[j+1]*V(t,r) for j,t in enumerate(ts)) for r in va]
  return max(E(ya,pa),E(yv,pv)),repr(ts),{"f":ts,"c":c}
 for x in q:
  w=sc([x])
  if w and(best==None or w[:2]<best[:2]):best=w
 for i,x in enumerate(q):
  for y in q[i+1:]:
   w=sc([x,y])
   if w and(best==None or w[:2]<best[:2]):best=w
 return {"status":"EXACT" if best and best[0]<=1e-8 else "MISS","c":None if best==None else best[2]}
def px(c,r):return c["c"][0]+sum(c["c"][i+1]*V(t,r) for i,t in enumerate(c["f"]))
def r(p,x):
 for o in p:x=f(o,x)
 return x
def ds(ex,d=3):
 q=[()]
 for _ in range(d+1):
  n=[]
  for p in q:
   if all(r(p,x)==y for x,y in ex):return {"status":"EXACT","t":p}
   n+=[p+(o,) for o in G]
  q=n
 return {"status":"MISS","t":None}
def ps(c,x):return r(c["t"],x)

from itertools import product as Z
P,M,I,J,F="R<>","NADI2","DI2","NDI2","PMEO";S=set(M+F)
def ws(A):return [""]+list(A)+["".join(x) for n in(2,3) for x in Z(A,repeat=n)]
def pv(q,x):
 p=x&1;k=(x-p)//2
 for P,L,H,a,b in q:
  if P==p and(L is None or k>=L)and(H is None or k<=H):return a*k+b
def sg(w):
 q=p(w);return tuple(pv(q,x) for x in range(-3,3))+tuple(t(q,x,d) for d in(-1,1) for x in(0,1))
def law(U):
 N=set()
 def a(x,y):N.add((x,y))
 for p in P:
  for m in M:a(p+m,m+p)
 for f in F:
  for x in (("S"+f,f+"S"),("R"+f,f+"R"),("u"+f,f+"u")):a(*x)
 for p in P:a(p+"S","S")
 a("SS","S")
 for m in I:a("S"+m,m+"S")
 for m in J:a("u"+m,m+"u")
 a("uS","Su");a("uu","u")
 for p in P:a("u"+p+"u","u"+p)
 for m in M:a("u"+m+"u",m+"u")
 z=sg("2O")
 for w in U:
  if w and sg("".join(c for c in w if c in S))==z:a(w,"2O")
 N={x for x in N if x[0]!=x[1]}
 return N
def e():
 A=L;U=ws(A);W=ws(S)
 g={};E=[]
 for w in W:g.setdefault(sg(w),[]).append(w)
 for q in g.values():E += [(w,q[0]) for w in q[1:]]
 E += [("<>",""),("><",""),("RR",""),("R<",">R"),("R>","<R")]
 E += [("NSN","SR"),("NSR","SN"),("SNR","NS"),("SNS","NS")]
 E += [("A"+x+"A","A"+x) for x in"Su"]
 E += [("S"+m+"S",m+"S") for m in M]
 E += [(f+p+f,f+p) for f in F for p in P]
 E += [("SuR","SRu"),("Su>","S>u"),("SAR","NSA"),("S<M","MS<"),("S>P","PS>")]
 return U,set(E)|law(U)
def base():
 U,E=e();ix={w:i for i,w in enumerate(U)};p=list(range(len(U)))
 def f(x):
  while p[x]!=x:p[x]=p[p[x]];x=p[x]
  return x
 for w in U:
  for a,b in E:
   for x,y in((a,b),(b,a)):
    if not x:continue
    k=0
    while 1:
     k=w.find(x,k)
     if k<0:break
     v=w[:k]+y+w[k+len(x):]
     if len(v)<=3 and v in ix:
      A,B=f(ix[w]),f(ix[v])
      if A!=B:p[B]=A
     k+=1
 assert len({f(i) for i in range(len(U))})==809
 sig={w:tuple(tuple(r(w,x)) for x in globals()["a"]) for w in U}
 assert len(set(sig.values()))==809
 d={}
 for w in U:d.setdefault(f(ix[w]),set()).add(sig[w])
 assert all(len(x)==1 for x in d.values())

from inspect import getsource
from math import ceil,floor
def h():
 x=getsource(f).replace(" ","")
 for q in('ifo=="R":returnx[::-1]','ifo=="S":returnsorted(x)','ifo=="u":returnlist(dict.fromkeys(x))','ifnotxandoin"<>":return[]','ifo=="<":returnx[1:]+x[:1]','ifo==">":returnx[-1:]+x[:-1]','ifoin"NADI2":return[f(o.lower(),v)forvinx]','ifoin"PMEO":return[vforvinxiff(o.lower(),v)]','ifo=="n":z=-x','elifo=="a":z=abs(x)','elifo=="d":z=x-1','elifo=="i":z=x+1','elifo=="2":z=2*x','elifo=="p":returnx>0','elifo=="m":returnx<0','elifo=="e":returnx%2==0','elifo=="o":returnx%2!=0'):assert q in x
def l():
 U=ws(L);N=law(U)
 assert len(N)==280
 for o in L:assert globals()["f"](o,[])==[]
 return len(N)
def i(l,h,a=None,b=None):
 if a is not None:l=a if l is None else max(l,a)
 if b is not None:h=b if h is None else min(h,b)
 return None if l is not None and h is not None and l>h else(l,h)
def rr(l,h,a,b,k):
 if k==0:return i(l,h,ceil(-b/a),None)if a>0 else i(l,h,None,floor(-b/a))
 if k==1:return i(l,h,floor(-b/a)+1,None)if a>0 else i(l,h,None,ceil(-b/a)-1)
 return i(l,h,None,ceil(-b/a)-1)if a>0 else i(l,h,floor(-b/a)+1,None)
def p(w):
 q=[(x,None,None,2,x)for x in(0,1)]
 for o in w:
  z=[]
  for x,L,H,a,b in q:
   if o=="N":z+=[(x,L,H,-a,-b)]
   elif o=="D":z+=[(x,L,H,a,b-1)]
   elif o=="I":z+=[(x,L,H,a,b+1)]
   elif o=="2":z+=[(x,L,H,2*a,2*b)]
   elif o=="A":
    for y,c in((rr(L,H,a,b,0),1),(rr(L,H,a,b,2),-1)):
     if y:z+=[(x,*y,c*a,c*b)]
   elif o in"PM":
    y=rr(L,H,a,b,1 if o=="P"else 2)
    if y:z+=[(x,*y,a,b)]
   elif o in"EO":
    if(b&1)==(0 if o=="E"else 1):z+=[(x,L,H,a,b)]
  q=z
 return q
def t(q,x,d):
 k=(-4-x)//2 if d<0 else ceil((3-x)/2);z=[y for y in q if y[0]==x and(y[1] is None or k>=y[1])and(y[2] is None or k<=y[2])]
 if not z:return
 _,L,H,A,B=z[0];assert L is None if d<0 else H is None
 a=A//2;return a,B-a*x
def check():
 h();assert l()==280;base()

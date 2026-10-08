import math,hashlib
U="naqrlt"
B="+-*/";a=[[(i&j+i|j)%17-8 for j in range(7)]for i in range(105)]
L="RSu<>NADI2PMEO"
G=L+U+"id2pmeo"
def f(o,x,y=None):
 try:
  if type(x)==list:
   if o in"R<>Su":return (x[::-1],x[1:]+x[:1],x[-1:]+x[:-1],sorted(x),list(dict.fromkeys(x)))["R<>Su".index(o)]
   if o in"NADI2":return [f(o.lower(),v) for v in x]
   if o in"PMEO":return [v for v in x if f(o.lower(),v)]
  elif y==None:
   if o in"nadi2":z=(-x,abs(x),x-1,x+1,2*x)["nadi2".index(o)]
   elif o=="q":z=x*x
   elif o=="r":z=math.sqrt(abs(x))
   elif o=="l":z=math.log1p(abs(x))
   elif o=="t":z=x/(1+abs(x))
   elif o in"pmeo":return (x>0,x<0,x%2==0,x%2!=0)["pmeo".index(o)]
   else:return
  else:z=(x+y,x-y,x*y,x/(1+abs(y)))[B.index(o)]
  return z if math.isfinite(z) else None
 except:return

def V(t,r):
 if t[0]=="v":
  z=r[t[1]];return list(z) if type(z)==list else float(z)
 if len(t)<3:return f(t[0],V(t[1],r))
 return f(t[0],V(t[1],r),V(t[2],r))
def T(fs,y):
 p=len(fs)+1;a=[[0.]*p for _ in range(p)];v=[0.]*p
 for k in range(len(y)):
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
 ns=inputs or sorted(set(rows[0])-{target});ya=[float(r[target]) for r in rows];yv=ya[3::4];yt=[x for i,x in enumerate(ya) if i%4<3]
 bs=[("v",n) for n in ns];la=bs[:]
 for _ in"12":la=[(o,t) for t in la for o in U];bs+=la
 z=[];seen=set()
 def ad(t):
  try:v=[V(t,r) for r in rows]
  except:return
  s=max(1.,max(map(abs,v)));h=tuple(round(x/s,10) for x in v)
  if h in seen:return
  seen.add(h);q=[x for i,x in enumerate(v) if i%4<3];c=T([q],yt)
  w=v[3::4];z.append((E(yv,[c[0]+c[1]*x for x in w]),t,q))
 for t in bs:ad(t)
 for i,x in enumerate(bs):
  for j,y in enumerate(bs):
   for o in B:
    if o in"+*" and j<i:continue
    ad((o,x,y))
 z.sort();q=list({x[1]:x for x in [x for x in z if len(x[1])<3]+z[:pool]}.values())
 best=None
 def sc(w):
  c=T([x[2] for x in w],yt)
  ts=[x[1] for x in w]
  pa=[c[0]+sum(c[j+1]*V(t,r) for j,t in enumerate(ts)) for r in rows];pv=pa[3::4]
  return max(E(ya,pa),E(yv,pv)),ts,{"f":ts,"c":c}
 for v in [[x] for x in q]+[[x,y] for i,x in enumerate(q) for y in q[i+1:]]:
  w=sc(v)
  if not best or w[:2]<best[:2]:best=w
 return {"status":"EXACT" if best and best[0]<=1e-8 else "MISS","c":best and best[2]}
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
P,M,F="R<>","NADI2","PMEO";S=M+F
def ws(A):return["".join(x)for n in range(4)for x in Z(A,repeat=n)]
def v(q,p,k):
 for P,L,H,a,b in q:
  if P==p and(L is None or k>=L)and(H is None or k<=H):return a,b
def pv(q,x):
 p=x&1;k=(x-p)//2;z=v(q,p,k)
 return z and z[0]*k+z[1]
def sg(w):
 q=p(w);return tuple(pv(q,x) for x in range(-3,3))+tuple(t(q,x,d) for d in(-1,1) for x in(0,1))
def law(U):
 N=set()
 def a(x,y):N.add((x,y))
 for p in P:
  for m in M:a(p+m,m+p)
 for f in F:
  for p in"SRu":a(p+f,f+p)
 for p in P+"S":a(p+"S","S")
 for m in"DI2":a("S"+m,m+"S")
 for m in"NDI2":a("u"+m,m+"u")
 a("uS","Su");a("uu","u")
 for x in P+M:a("u"+x+"u","u"*(x in P)+x+"u"*(x in M))
 z=sg("2O")
 for w in U:
  if w!="2O"and sg("".join(c for c in w if c in S))==z:a(w,"2O")
 assert len(N)==280
 return N
def e():
 U=ws(L)
 g={};E=[]
 for w in ws(S):g.setdefault(sg(w),[]).append(w)
 for q in g.values():E+=[(w,q[0]) for w in q[1:]]
 E+=[("<>",""),("><",""),("RR",""),("R<",">R"),("R>","<R")]
 E+=[("NSN","SR"),("NSR","SN"),("SNR","NS")]
 E+=[("A"+x+"A","A"+x) for x in"Su"]
 E+=[("S"+m+"S",m+"S") for m in M]
 E+=[(f+p+f,f+p) for f in F for p in P]
 E+=[("SuR","SRu"),("Su>","S>u"),("SAR","NSA"),("S<M","MS<"),("S>P","PS>")]
 return U,set(E)|law(U)
def base():
 U,E=e();p=list(range(len(U)))
 def f(x):
  while p[x]-x:x=p[x]
  return x
 for a,b in E:
  for c in U:
   if len(c)<4-max(len(a),len(b)):
    for k in range(len(c)+1):
     A=c[:k]+a+c[k:];B=c[:k]+b+c[k:]
     A,B=f(U.index(A)),f(U.index(B))
     if A-B:p[B]=A
 sig=[tuple(tuple(r(w,x))for x in globals()["a"])for w in U]
 q=list(map(f,range(len(U))));assert len(set(q))==len(set(sig))==len(set(zip(q,sig)))==809

from inspect import getsource
def h():assert hashlib.sha256(getsource(f).encode()).hexdigest()=="773a7bf6038771e9bed21753f4fef1b3003a0f0a211d455b934053fb4d05a90d"
def i(l,h,a=None,b=None):
 if a!=None:l=a if l is None else max(l,a)
 if b!=None:h=b if h is None else min(h,b)
 return None if l!=None!=h and l>h else(l,h)
def rr(l,h,a,b,k):
 if k==0:return i(l,h,-(b//a))if a>0 else i(l,h,b=-b//a)
 if k==1:return i(l,h,-b//a+1)if a>0 else i(l,h,b=-(b//a)-1)
 return i(l,h,b=-(b//a)-1)if a>0 else i(l,h,-b//a+1)
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
    y=rr(L,H,a,b,2-(o=="P"))
    if y:z+=[(x,*y,a,b)]
   elif o in"EO":
    if(b&1)==(o=="O"):z+=[(x,L,H,a,b)]
  q=z
 return q
def t(q,x,d):
 k=(-4-x)//2 if d<0 else (4-x)//2;z=v(q,x,k)
 if not z:return
 A,B=z;a=A//2;return a,B-a*x
def check():
 h();assert all(f(o,[])==[] for o in L);base()

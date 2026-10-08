R=range;from math import*;from hashlib import*;from itertools import*;from inspect import*;O=enumerate;l=len
U="naqrlt"
B="+-*/";a=[[(i&j+i|j)%17-8 for j in R(7)]for i in R(105)]
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
   elif o=="r":z=sqrt(abs(x))
   elif o=="l":z=log1p(abs(x))
   elif o=="t":z=x/(1+abs(x))
   elif o in"pmeo":return (x>0,x<0,x%2==0,x%2!=0)["pmeo".index(o)]
   else:return
  else:z=(x+y,x-y,x*y,x/(1+abs(y)))[B.index(o)]
  return z if isfinite(z) else None
 except:return

def V(t,r):
 if t[0]=="v":
  z=r[t[1]];return list(z) if type(z)==list else float(z)
 return f(t[0],*(V(x,r)for x in t[1:]))
def T(fs,y):
 p=l(fs)+1;a=[[0.]*(p+1)for _ in R(p)]
 for k in R(l(y)):
  q=[1.,*(x[k]for x in fs),y[k]]
  for i in R(p):
   for j in R(p+1):a[i][j]+=q[i]*q[j]
 for i in R(p):a[i][i]+=1e-12
 for c in R(p):
  a[c]=[x/a[c][c]for x in a[c]]
  for r in R(p):
   if r-c:a[r]=[x-a[r][c]*y for x,y in zip(a[r],a[c])]
 return [x[-1]for x in a]
def E(y,p):
 m=sum(y)/l(y);s=max((sum((x-m)**2 for x in y)/l(y))**.5,max(map(abs,y))*1e-9,1e-12)
 return (sum((a-b)**2 for a,b in zip(y,p))/l(y))**.5/s
def dx(rows,target="y",inputs=None,pool=1):
 N=inputs or sorted(set(rows[0])-{target});Y=[float(r[target]) for r in rows];W=Y[3::4];J=[x for i,x in O(Y) if i%4<3]
 Q=[("v",n) for n in N];R=Q[:]
 for _ in"12":R=[(o,t) for t in R for o in U];Q+=R
 z=[];H=set()
 def A(t):
  try:v=[V(t,r) for r in rows]
  except:return
  s=max(1.,*map(abs,v));h=tuple(round(x/s,10) for x in v)
  if h in H:return
  H.add(h);q=[x for i,x in O(v) if i%4<3];c=T([q],J)
  w=v[3::4];z.append((E(W,[c[0]+c[1]*x for x in w]),t,q))
 for t in Q:A(t)
 for i,x in O(Q):
  for j,y in O(Q):
   for o in B:
    if o in"-/"or j>=i:A((o,x,y))
 z.sort();q=list({x[1]:x for x in [x for x in z if l(x[1])<3]+z[:pool]}.values())
 b=None
 def K(w):
  c=T([x[2] for x in w],J)
  C=[x[1] for x in w]
  D=[c[0]+sum(c[j+1]*V(t,r) for j,t in O(C)) for r in rows];X=D[3::4]
  return max(E(Y,D),E(W,X)),C,{"f":C,"c":c}
 for v in [[x] for x in q]+[[x,y] for i,x in O(q) for y in q[i+1:]]:
  w=K(v)
  if not b or w[:2]<b[:2]:b=w
 return {"status":"EXACT" if b and b[0]<=1e-8 else "MISS","c":b and b[2]}
def px(c,r):return c["c"][0]+sum(c["c"][i+1]*V(t,r) for i,t in O(c["f"]))
def r(p,x):
 for o in p:x=f(o,x)
 return x
def ds(ex,d=3):
 for n in R(d+1):
  for p in product(G,repeat=n):
   if all(r(p,x)==y for x,y in ex):return {"status":"EXACT","t":p}
 return {"status":"MISS","t":None}
def ps(c,x):return r(c["t"],x)

P,M,F="R<>","NADI2","PMEO";S=M+F
def W(A):return["",*A,*("".join(x)for n in(2,3)for x in product(A,repeat=n))]
def c(w,s,p):
 a,b=1,0;x=4*s-p
 for o in w:
  if o in"NDI2":a,b=((-a,-b),(a,b-1),(a,b+1),(2*a,2*b))["NDI2".index(o)]
  elif o in"APM":
   z=a*x+b;assert z*a*s>0
   if o=="A"and z<0:a,b=-a,-b
   elif o!="A"and(z>0)!=(o=="P"):return
  elif o in"EO"and(a*p+b)%2!=(o=="O"):return
 return a,b
def g(w):return tuple(tuple(r(w,[x]))for x in R(-3,3))+tuple(c(w,s,p)for s in(-1,1)for p in(0,1))
def e():
 U=W(L);d={};E=set()
 for w in W(S):
  x=d.setdefault(g(w),w)
  if x!=w:E.add((w,x))
 E|={("<>",""),("><",""),("RR",""),("R<",">R"),("R>","<R"),("NSN","SR"),("NSR","SN"),("SNR","NS"),("SNS","NS"),("SuR","SRu"),("Su>","S>u"),("SAR","NSA"),("S<M","MS<"),("S>P","PS>")}|{("A"+x+"A","A"+x)for x in"Su"}|{("S"+m+"S",m+"S")for m in M}|{(f+p+f,f+p)for f in F for p in P}
 N={(p+m,m+p)for p in P for m in M}|{(p+f,f+p)for p in"SRu"for f in F}|{(p+"S","S")for p in P+"S"}|{("S"+m,m+"S")for m in"DI2"}|{("u"+m,m+"u")for m in"NDI2"}|{("uS","Su"),("uu","u")}|{("u"+x+"u","u"+x)for x in P}|{("u"+x+"u",x+"u")for x in M}
 z=g("2O");N|={(w,"2O")for w in U if w!="2O"and g("".join(c for c in w if c in S))==z}
 assert l(N)==280
 return U,E|N
def k():
 U,E=e();p={x:x for x in U}
 def f(x):
  while p[x]!=x:x=p[x]
  return x
 for u,v in E:
  for c in U:
   if l(c)<4-max(l(u),l(v)):
    for k in R(l(c)+1):
     A=f(c[:k]+u+c[k:]);B=f(c[:k]+v+c[k:])
     if A!=B:p[B]=A
 s=[tuple(tuple(r(w,x))for x in a)for w in U];q=[*map(f,U)]
 assert l(set(q))==l(set(s))==l(set(zip(q,s)))==809

def check():
 assert sha256(getsource(f).encode()).hexdigest()=="b2f77fbbf8b00f664d64c81046801b4bfe18c6f2be47751d02316fab8f81aad0";assert all(f(o,[])==[]for o in L);k()

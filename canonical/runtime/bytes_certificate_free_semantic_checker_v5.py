from itertools import product
class Q:
 def __init__(s,a=1,b=0,z=1,p=0):s.a,s.b,s.z,s.p=a,b,z,p
 def __neg__(s):return Q(-s.a,-s.b,s.z,s.p)
 def __abs__(s):return s if s.a*s.z>0 else -s
 def __add__(s,x):return Q(s.a,s.b+x,s.z,s.p)
 def __sub__(s,x):return Q(s.a,s.b-x,s.z,s.p)
 def __rmul__(s,x):return Q(s.a*x,s.b*x,s.z,s.p)
 def __gt__(s,x):return s.a*s.z>0
 def __lt__(s,x):return s.a*s.z<0
 def __mod__(s,x):return (s.a*s.p+s.b)%x
 def __float__(s):return 0.
def roles(K):
 A=K.L;T=[[3,1,2,0],[2,0,2,1]]
 F=[lambda x:x[::-1],lambda x:sorted(x),lambda x:list(dict.fromkeys(x)),lambda x:x[1:]+x[:1] if x else [],lambda x:x[-1:]+x[:-1] if x else []]
 R={}
 for o in A:
  q=[K.f(o,list(x)) for x in T]
  for i,g in enumerate(F):
   if q==[g(list(x)) for x in T]:R[i]=o
 if len(R)!=5:raise ValueError("STRUCT")
 Z=set(R.values());M=[];P=[];x=[-2,-1,0,1,2]
 for o in A:
  if o in Z:continue
  y=K.f(o,list(x));(M if len(y)==len(x) else P).append(o)
 return A,R,M,P
def tq(K,w,z,p):
 x=Q(z=z,p=p)
 for o in w:
  y=K.f(o.lower(),x)
  if isinstance(y,bool):
   if not y:return
  elif y is None:return
  else:x=y
 return (x.a,x.b)
def bound(K,M):
 b=3
 for n in range(4):
  for w in product(M,repeat=n):
   for z in(-1,1):
    q=tq(K,w,z,0)
    if q and q[0]:b=max(b,(abs(q[1])+abs(q[0])-1)//abs(q[0])+2)
 return b
def sg(K,w,B):
 c=[]
 for x in range(-B,B+1):
  a=1
  for o in w:
   y=K.f(o.lower(),x)
   if isinstance(y,bool):
    if not y:a=0;break
   elif y is None:a=0;break
   else:x=y
  c.append(x if a else None)
 for z in(-1,1):
  for p in(0,1):c.append(tq(K,w,z,p))
 return tuple(c)
def props(K,M,F,B):
 se=lambda a,b:sg(K,a,B)==sg(K,b,B);inc=[];dec=[];idem=[];up=[];down=[]
 for m in M:
  v=[K.f(m.lower(),x) for x in range(-B,B+1)];t=[tq(K,m,z,p) for z in(-1,1) for p in(0,1)]
  if all(v[i]<v[i+1] for i in range(len(v)-1)) and all(q and q[0]>0 for q in t):inc.append(m)
  if all(v[i]>v[i+1] for i in range(len(v)-1)) and all(q and q[0]<0 for q in t):dec.append(m)
  if se(m+m,m):idem.append(m)
 for f in F:
  v=[bool(K.f(f.lower(),x)) for x in range(-B,B+1)];t=[tq(K,f,z,p) for z in(-1,1) for p in(0,1)]
  n=all(q is not None for q in t[:2]);p=all(q is not None for q in t[2:])
  if not n and p and all((not v[i])or v[i+1] for i in range(len(v)-1)):up.append(f)
  if n and not p and all(v[i]or(not v[i+1]) for i in range(len(v)-1)):down.append(f)
 return set(inc),set(dec),set(idem),set(up),set(down)
def equations(K):
 A,R,M,F=roles(K);B=bound(K,M);rv,so,uq,le,ri=[R[i] for i in range(5)];P=rv+le+ri;S=set(M+F)
 U=[""]+list(A)+["".join(x) for n in(2,3) for x in product(A,repeat=n)]
 W=[""]+list(S)+["".join(x) for n in(2,3) for x in product(S,repeat=n)]
 g={};E=[];se=lambda a,b:sg(K,a,B)==sg(K,b,B)
 for w in W:g.setdefault(sg(K,w,B),[]).append(w)
 for q in g.values():E += [(w,q[0]) for w in q[1:]]
 inc,dec,idem,up,down=props(K,M,F,B);inj=inc|dec
 E += [(le+ri,""),(ri+le,""),(rv+rv,""),(rv+le,ri+rv),(rv+ri,le+rv)]
 E += [(p+m,m+p) for p in P for m in M]+[(p+so,so) for p in P]+[(so+so,so)]
 E += [(so+m,m+so) for m in inc]
 E += [x for f in F for x in ((so+f,f+so),(rv+f,f+rv),(uq+f,f+uq))]
 E += [(uq+m,m+uq) for m in inj]+[(uq+so,so+uq),(uq+uq,uq)]
 for n in dec:
  if se(n+n,""):E += [(n+so+n,so+rv),(n+so+rv,so+n),(so+n+rv,n+so),(so+n+so,n+so)]
 E += [(uq+p+uq,uq+p) for p in P]
 for a in idem:E += [(a+so+a,a+so),(so+a+so,a+so),(a+uq+a,a+uq),(uq+a+uq,a+uq)]
 E += [(so+m+so,m+so) for m in M]+[(uq+m+uq,m+uq) for m in M]
 z=None
 for w in U:
  q=sg(K,"".join(c for c in w if c in S),B)
  if q and all(x is None for x in q):z=w;break
 if z:
  Z=sg(K,z,B);E += [(w,z) for w in U if w and sg(K,"".join(c for c in w if c in S),B)==Z]
 E += [(f+p+f,f+p) for f in F for p in P]+[(so+uq+rv,so+rv+uq),(so+uq+ri,so+ri+uq)]
 for a in idem:
  for n in dec:
   if se(n+n,"") and se(n+a,a):E += [(so+a+rv,n+so+a)]
 for f in down:E += [(so+le+f,f+so+le)]
 for f in up:E += [(so+ri+f,f+so+ri)]
 return U,list(dict.fromkeys(E)),B
def check(K):
 U,E,B=equations(K);ix={w:i for i,w in enumerate(U)};p=list(range(len(U)))
 def f(x):
  while p[x]!=x:p[x]=p[p[x]];x=p[x]
  return x
 def j(a,b):
  a,b=f(a),f(b)
  if a!=b:p[b]=a
 z=1
 while z:
  n=len({f(i) for i in range(len(U))})
  for w in U:
   for a,b in E:
    for x,y in((a,b),(b,a)):
     if not x:continue
     k=0
     while 1:
      k=w.find(x,k)
      if k<0:break
      v=w[:k]+y+w[k+len(x):]
      if len(v)<=3 and v in ix:j(ix[w],ix[v])
      k+=1
  z=len({f(i) for i in range(len(U))})<n
 roots={}
 for w in U:roots.setdefault(f(ix[w]),w)
 R=list(roots.values());C=len(R);sig={w:[] for w in R}
 base=range(-4,5);X=[()]
 for n in range(1,4):X+=list(product(base,repeat=n))
 X += [(-4,-4,-4,-3),(-4,-3,-4,-2),(-4,-3,-2,-3)]
 for v in range(5,B+1):X += [(v,),(-v,)]
 V=list(range(-B,B+1));X += [x for n in(2,4) for x in product(V,repeat=n)]
 used=0
 for x in X:
  for w in R:sig[w].append(tuple(K.rp(tuple(w),list(x))))
  used+=1
  if len({tuple(v) for v in sig.values()})==C:break
 assert len({tuple(v) for v in sig.values()})==C
 return {"status":"PASS","programs":len(U),"equations":len(E),"classes":C,"witnesses_used":used,"bound":B}

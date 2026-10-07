from itertools import product
def parse(t):return [tuple(z.split("=")) for z in t.splitlines()]
def check(t,k):
 E=parse(t);L=k.L
 U=[""]+list(L)+["".join(x) for x in product(L,repeat=2)]+["".join(x) for x in product(L,repeat=3)]
 I={w:i for i,w in enumerate(U)};P=list(range(len(U)))
 def f(a):
  while P[a]!=a:P[a]=P[P[a]];a=P[a]
  return a
 def j(a,b):
  a,b=f(a),f(b)
  if a!=b:P[b]=a
 z=True
 while z:
  n=len({f(i) for i in range(len(U))})
  for w in U:
   for a,b in E:
    for x,y in ((a,b),(b,a)):
     if not x:continue
     q=0
     while 1:
      p=w.find(x,q)
      if p<0:break
      v=w[:p]+y+w[p+len(x):]
      if len(v)<=3 and v in I:j(I[w],I[v])
      q=p+1
  z=len({f(i) for i in range(len(U))})<n
 C=len({f(i) for i in range(len(U))})
 X=list(k.ci());S={w:tuple(tuple(k.rp(tuple(w),x)) for x in X) for w in U}
 W=len(set(S.values()))
 Q={}
 for w in U:Q.setdefault(f(I[w]),set()).add(S[w])
 return C,W,len(X),all(len(x)==1 for x in Q.values())

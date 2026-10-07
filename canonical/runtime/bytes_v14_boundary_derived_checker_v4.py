def st(q,o):
 a,b,d,p=q
 if not d:return q
 if o=="N":return(-a,-b,d,p)
 if o=="D":return(a,b-1,d,p)
 if o=="I":return(a,b+1,d,p)
 if o=="2":return(2*a,2*b,d,p)
 s=1 if a*d>0 else -1
 if o=="A":return(a,b,d,p) if s>0 else(-a,-b,d,p)
 if o=="P":return(a,b,d if s>0 else 0,p)
 if o=="M":return(a,b,d if s<0 else 0,p)
 y=(a*p+b)&1
 if o=="E":return(a,b,d if y==0 else 0,p)
 if o=="O":return(a,b,d if y==1 else 0,p)
def tail(w,d,p):
 q=(1,0,d,p)
 for o in w:q=st(q,o)
 return q[:3] if q[2] else None
def pt(w,x):
 for o in w:
  if o=="N":x=-x
  elif o=="A":x=abs(x)
  elif o=="D":x-=1
  elif o=="I":x+=1
  elif o=="2":x*=2
  elif o=="P":
   if x<=0:return
  elif o=="M":
   if x>=0:return
  elif o=="E":
   if x&1:return
  elif o=="O":
   if not x&1:return
 return x
def eq(a,b):
 return all(pt(a,x)==pt(b,x) for x in range(-3,3)) and all(tail(a,d,p)==tail(b,d,p) for d in(-1,1) for p in(0,1))
def dead(w):
 return all(pt(w,x) is None for x in range(-3,3)) and all(tail(w,d,p) is None for d in(-1,1) for p in(0,1))
def mono(w,s):
 if any(pt(w,x) is None for x in range(-4,4)):return False
 y=[pt(w,x) for x in range(-4,4)]
 if not all((y[i+1]-y[i])*s>0 for i in range(len(y)-1)):return False
 for d in(-1,1):
  q=tail(w,d,0)
  if q is None or q[0]*s<=0:return False
 return True
def inj(w):return mono(w,1) or mono(w,-1)
def nonneg(w):
 if any((z:=pt(w,x)) is None or z<0 for x in range(-3,3)):return False
 return all((q:=tail(w,d,p)) is not None and q[0]*d>0 for d in(-1,1) for p in(0,1))
def even(w):
 if any((z:=pt(w,x)) is None or z&1 for x in range(-3,3)):return False
 return all((q:=tail(w,d,p)) is not None and ((q[0]*p+q[1])&1)==0 for d in(-1,1) for p in(0,1))
def C(a,b):return tuple(sorted((a,b)))
def gen(k):
 z=set()
 def add(a,b):z.add(C(a,b))
 T="R<>";O=[o for o in k.L if o not in "RSu<>"]
 F=[o for o in O if isinstance(k.f(o.lower(),0),bool)];M=[o for o in O if o not in F]
 INC=[o for o in M if mono(o,1)];INJ=[o for o in M if inj(o)]
 A=[o for o in M if nonneg(o) and eq(o+o,o)][0]
 N=[o for o in M if mono(o,-1)][0]
 D=[o for o in M if even(o)][0]
 ODD=[o for o in F if dead(D+o)][0]
 comp=[(a,b) for a in F for b in F if a!=b and dead(a+b)]
 add("<>","");add("><","");add("RR","");add("R<",">R");add("R>","<R")
 for q in T:
  for m in M:add(m+q,q+m)
 for q in T:add(q+"S","S")
 add("SS","S")
 for m in INC:add("S"+m,m+"S")
 for f in F:add("S"+f,f+"S");add("R"+f,f+"R")
 for m in INJ:add("u"+m,m+"u")
 for f in F:add("u"+f,f+"u")
 add("uS","Su");add("uu","u")
 for a,b in ((N+"S"+N,"SR"),(N+"SR","S"+N),("S"+N+"R",N+"S"),("S"+N+"S",N+"S")):add(a,b)
 for q in T:add("u"+q+"u","u"+q)
 add(A+"S"+A,A+"S");add(A+"u"+A,A+"u");add("S"+A+"S",A+"S");add("u"+A+"u",A+"u")
 for q in "<>":add(D+q+ODD,D+ODD)
 for q in "<>RSu":add(D+ODD+q,D+ODD)
 for a,b in comp:
  if {a,b} in ({'P','M'},{'E','O'}):
   for q in "<>":add(a+q+b,D+ODD)
 for f in F:
  for q in "<>":add(f+q+f,f+q)
 add("S"+A+"R",N+"S"+A)
 for q in T:
  if k.r("Su"+q,[0,0,1])==k.r("S"+q+"u",[0,0,1]):add("Su"+q,"S"+q+"u")
  for f in F:
   if q!="R" and all(k.r("S"+q+f,x)==k.r(f+"S"+q,x) for x in([-3,-2,-1,0],[-2,-1,2,3])):add("S"+q+f,f+"S"+q)
 return z

from itertools import product
def parse(t):return [tuple(z.split("=")) for z in t.splitlines()]
def cl(t,k):
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
 X=k.a;S={w:tuple(tuple(k.r(tuple(w),x)) for x in X) for w in U}
 W=len(set(S.values()))
 Q={}
 for w in U:Q.setdefault(f(I[w]),set()).add(S[w])
 return C,W,len(X),all(len(x)==1 for x in Q.values())

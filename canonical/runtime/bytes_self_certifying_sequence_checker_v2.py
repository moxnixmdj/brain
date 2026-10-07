from itertools import product
A="RSu<>NADI2PMEO";P="R<>";M="NADI2";I="DI2";J="NDI2";F="PMEO";S=set(M+F)
def sp(w,x):
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
   if x%2:return
  elif o=="O":
   if x%2==0:return
 return x
def st(w,s,p):
 q=(1,0)
 for o in w:
  if q is None:return
  a,b=q
  if o=="N":q=(-a,-b)
  elif o=="D":q=(a,b-1)
  elif o=="I":q=(a,b+1)
  elif o=="2":q=(2*a,2*b)
  elif o=="A":q=(a,b) if a*s>0 else(-a,-b)
  elif o=="P" and a*s<0:q=None
  elif o=="M" and a*s>0:q=None
  elif o=="E" and((a*p+b)&1):q=None
  elif o=="O" and not((a*p+b)&1):q=None
 return q
def sg(w):return tuple(sp(w,x) for x in range(-3,3))+tuple(st(w,s,p) for s in(-1,1) for p in(0,1))
def equations():
 U=[""]+list(A)+["".join(x) for n in(2,3) for x in product(A,repeat=n)]
 W=[""]+list(S)+["".join(x) for n in(2,3) for x in product(S,repeat=n)]
 g={};E=[]
 for w in W:g.setdefault(sg(w),[]).append(w)
 for q in g.values():E += [(w,q[0]) for w in q[1:]]
 E += [("<>",""),("><",""),("RR",""),("R<",">R"),("R>","<R")]
 E += [(p+m,m+p) for p in P for m in M]
 E += [(p+"S","S") for p in P]+[("SS","S")]
 E += [("S"+m,m+"S") for m in I]
 E += [x for f in F for x in (("S"+f,f+"S"),("R"+f,f+"R"),("u"+f,f+"u"))]
 E += [("u"+m,m+"u") for m in J]+[("uS","Su"),("uu","u")]
 E += [("NSN","SR"),("NSR","SN"),("SNR","NS"),("SNS","NS")]
 E += [("u"+p+"u","u"+p) for p in P]+[("A"+x+"A","A"+x) for x in"Su"]
 E += [("S"+m+"S",m+"S") for m in M]+[("u"+m+"u",m+"u") for m in M]
 z=sg("2O")
 E += [(w,"2O") for w in U if w and sg("".join(c for c in w if c in S))==z]
 E += [(f+p+f,f+p) for f in F for p in P]
 E += [("SuR","SRu"),("Su>","S>u"),("SAR","NSA"),("S<M","MS<"),("S>P","PS>")]
 return U,list(dict.fromkeys(E))
def check(K):
 U,E=equations();ix={w:i for i,w in enumerate(U)};p=list(range(len(U)))
 def f(x):
  while p[x]!=x:p[x]=p[p[x]];x=p[x]
  return x
 def j(a,b):
  a,b=f(a),f(b)
  if a!=b:p[b]=a
 n=1
 while n:
  c=len({f(i) for i in range(len(U))})
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
  n=len({f(i) for i in range(len(U))})<c
 assert len({f(i) for i in range(len(U))})==809
 X=[()]
 for n in range(1,4):X+=list(product(range(-4,5),repeat=n))
 X += [(-4,-4,-4,-3),(-4,-3,-4,-2),(-4,-3,-2,-3)]
 sig={w:[] for w in U};by=[[w for w in U if len(w)==n] for n in range(4)]
 for x in X:
  o={"":list(x)};sig[""].append(tuple(x))
  for n in range(1,4):
   for w in by[n]:o[w]=K.f(w[-1],o[w[:-1]]);sig[w].append(tuple(o[w]))
 sig={w:tuple(v) for w,v in sig.items()}
 assert len(set(sig.values()))==809
 d={}
 for w in U:d.setdefault(f(ix[w]),set()).add(sig[w])
 assert all(len(x)==1 for x in d.values())
 return {"status":"PASS","programs":len(U),"equations":len(E),"classes":809,"witnesses":len(X)}

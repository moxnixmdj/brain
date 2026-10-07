from itertools import product
A="RSu<>NADI2PMEO";P="R<>";M="NADI2";I="DI2";J="NDI2";F="PMEO";S=set(M+F);O="naid2pmeoq"
def tr(p):
 if p is None:return
 p=list(p)
 while len(p)>1 and not p[-1]:p.pop()
 return tuple(p)
def ps(p,k):return tr(tuple(k*x for x in p))
def pa(p,k):
 q=list(p);q[0]+=k;return tr(q)
def pq(p):
 q=[0]*(2*len(p)-1)
 for i,a in enumerate(p):
  for j,b in enumerate(p):q[i+j]+=a*b
 return tr(q)
def es(p,s):
 if not any(p):return 0
 d=max(i for i,x in enumerate(p) if x);z=1 if p[d]>0 else -1
 return -z if s<0 and d%2 else z
def pp(p,r):return (p[0] if not r else sum(p))&1
def ts(p,o,s,r):
 if p is None:return
 k=o.lower()
 if k=="n":return ps(p,-1)
 if k=="a":return p if es(p,s)>=0 else ps(p,-1)
 if k=="i":return pa(p,1)
 if k=="d":return pa(p,-1)
 if k=="2":return ps(p,2)
 if k=="q":return pq(p)
 if k in"pmeo":
  if k=="p":t=es(p,s)>0
  elif k=="m":t=es(p,s)<0
  elif k=="e":t=pp(p,r)==0
  else:t=pp(p,r)==1
  return (p if t else None) if o.isupper() else (int(t),)
def sv(o,x):
 if x is None:return
 k=o.lower()
 if k=="n":return -x
 if k=="a":return abs(x)
 if k=="i":return x+1
 if k=="d":return x-1
 if k=="2":return 2*x
 if k=="q":return x*x
 if k in"pmeo":
  if k=="p":t=x>0
  elif k=="m":t=x<0
  elif k=="e":t=x%2==0
  else:t=x%2!=0
  return x if o.isupper() and t else (None if o.isupper() else t)
def sg(w):
 c=[]
 for x in range(-3,4):
  y=x
  for o in w:y=sv(o,y)
  c.append(y)
 for s in(-1,1):
  for r in(0,1):
   p=(0,1)
   for o in w:p=ts(p,o,s,r)
   c.append(p)
 return tuple(c)
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
def scalar_check():
 W=[""]+list(O)+["".join(x) for n in(2,3) for x in product(O,repeat=n)]
 Q=set()
 for n in range(3):
  for w in product(O,repeat=n):
   for s in(-1,1):
    for r in(0,1):
     p=(0,1)
     for o in w:p=ts(p,o,s,r)
     if p is not None:Q.add(p)
 for p in Q:
  if len(p)>1:assert max((abs(x) for x in p[:-1]),default=0)<=2*abs(p[-1])
 G=[sg(w) for w in W]
 assert len({g[:7] for g in G})==len(set(G))==203
 return len(W)
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
 return {"status":"PASS","sequence_programs":len(U),"sequence_equations":len(E),"sequence_classes":809,"sequence_witnesses":len(X),"scalar_programs":scalar_check(),"scalar_classes":203,"scalar_characteristic_inputs":7}

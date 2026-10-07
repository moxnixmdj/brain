from itertools import product
P=set("R<>");M=set("NADI2");I=set("DI2");J=set("NDI2");F=set("PMEO");S=M|F
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
def se(a,b):
 return all(sp(a,x)==sp(b,x) for x in range(-3,3)) and all(st(a,s,p)==st(b,s,p) for s in(-1,1) for p in(0,1))
def c2(a,b,A,B):return len(a)==len(b)==2 and a[0] in A and a[1] in B and b==a[::-1]
def ok(a,b):
 e=lambda w:se(''.join(x for x in w if x in S),"2O")
 return (a,b) in {("<>",""),("><",""),("RR",""),("R<",">R"),("R>","<R")} or c2(a,b,P,M) or c2(a,b,M,P) or((len(a)==2 and a[1]=="S" and a[0] in P and b=="S")or(a,b)==("SS","S")) or c2(a,b,{"S"},I) or c2(a,b,I,{"S"}) or c2(a,b,{"S"},F) or c2(a,b,F,{"S"}) or c2(a,b,{"R"},F) or c2(a,b,F,{"R"}) or c2(a,b,{"u"},J) or c2(a,b,J,{"u"}) or c2(a,b,{"u"},F) or c2(a,b,F,{"u"}) or set((a,b))=={"uS","Su"} or(a,b)==("uu","u") or(a,b) in {("NSN","SR"),("NSR","SN"),("SNR","NS"),("SNS","NS")} or(len(a)==3 and a[0]==a[2]=="u" and a[1] in P and b==a[:2]) or(a in("ASA","AuA")and b==a[:2]) or(len(a)==3 and a[0]==a[2]=="S" and a[1] in M and b==a[1:]) or(len(a)==3 and a[0]==a[2]=="u" and a[1] in M and b==a[1:]) or(e(a)and e(b)) or(len(a)==3 and a[0] in F and a[2]==a[0] and a[1] in P and b==a[:2]) or(a,b) in {("SuR","SRu"),("Su>","S>u"),("SAR","NSA"),("S<M","MS<"),("S>P","PS>")}
def check(K,C):
 h,E=C.strip().split("\n",1);A,D,N=h.split("|");D=int(D);N=int(N)
 Q=[tuple(x.split("=")) for x in E.split(",")]
 assert all(se(a,b) if set(a+b)<=S else ok(a,b) for a,b in Q)
 U=[""]+list(A)+["".join(x) for n in(2,3) for x in product(A,repeat=n)]
 ix={w:i for i,w in enumerate(U)};p=list(range(len(U)))
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
   for a,b in Q:
    for x,y in((a,b),(b,a)):
     if not x:continue
     k=0
     while 1:
      k=w.find(x,k)
      if k<0:break
      v=w[:k]+y+w[k+len(x):]
      if len(v)<=D and v in ix:j(ix[w],ix[v])
      k+=1
  z=len({f(i) for i in range(len(U))})<n
 assert len({f(i) for i in range(len(U))})==N
 X=[()]
 for n in range(1,4):X+=list(product(range(-4,5),repeat=n))
 X += [(-4,-4,-4,-3),(-4,-3,-4,-2),(-4,-3,-2,-3)]
 sig={w:tuple(tuple(K.rp(tuple(w),list(x))) for x in X) for w in U}
 assert len(set(sig.values()))==N
 d={}
 for w in U:d.setdefault(f(ix[w]),set()).add(sig[w])
 assert all(len(x)==1 for x in d.values())
 return {"status":"PASS","programs":len(U),"classes":N,"witnesses":len(X),"equations":len(Q)}

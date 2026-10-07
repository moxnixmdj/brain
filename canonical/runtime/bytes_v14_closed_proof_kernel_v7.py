from inspect import getsource
from math import ceil,floor
from itertools import product as Z
def s(K):
 x=getsource(K.f).replace(" ","")
 for q in('ifo=="R":returnx[::-1]','ifo=="S":returnsorted(x)','ifo=="u":returnlist(dict.fromkeys(x))','ifnotxandoin"<>":return[]','ifo=="<":returnx[1:]+x[:1]','ifo==">":returnx[-1:]+x[:-1]','ifoin"NADI2":return[f(o.lower(),v)forvinx]','ifoin"PMEO":return[vforvinxiff(o.lower(),v)]','ifo=="n":z=-x','elifo=="a":z=abs(x)','elifo=="d":z=x-1','elifo=="i":z=x+1','elifo=="2":z=2*x','elifo=="p":returnx>0','elifo=="m":returnx<0','elifo=="e":returnx%2==0','elifo=="o":returnx%2!=0'):assert q in x
def l(K,C):
 U,E=C.e(K);A={tuple(sorted(x))for x in E};N=set()
 def a(x,y):N.add(tuple(sorted((x,y))))
 for p in"R<>":
  for m in"NADI2":a(p+m,m+p)
 for f in"PMEO":a("R"+f,f+"R")
 for p in"R<>":a(p+"S","S")
 a("SS","S")
 for m in"DI2":a("S"+m,m+"S")
 for f in"PMEO":a("S"+f,f+"S")
 for m in"NDI2":a("u"+m,m+"u")
 for f in"PMEO":a("u"+f,f+"u")
 a("uS","Su");a("uu","u")
 for p in"R<>":a("u"+p+"u","u"+p)
 for m in"NADI2":a("u"+m+"u",m+"u")
 z=C.sg(K,"2O")
 for w in U:
  if w and C.sg(K,"".join(c for c in w if c in C.S))==z:a(w,"2O")
 N={x for x in N if x[0]!=x[1]};assert N<=A
 for o in K.L:assert K.f(o,[])==[]
 return len(N)
def i(l,h,a=None,b=None):
 if a is not None:l=a if l is None else max(l,a)
 if b is not None:h=b if h is None else min(h,b)
 return None if l is not None and h is not None and l>h else(l,h)
def r(l,h,a,b,k):
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
    for y,c in((r(L,H,a,b,0),1),(r(L,H,a,b,2),-1)):
     if y:z+=[(x,*y,c*a,c*b)]
   elif o in"PM":
    y=r(L,H,a,b,1 if o=="P"else 2)
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
def m(K,C):
 W=[""]+list(C.S)+["".join(x)for n in(2,3)for x in Z(C.S,repeat=n)]
 for w in W:
  q=p(w)
  for x in(0,1):
   for d in(-1,1):assert t(q,x,d)==C.st(w,d,x)
 return len(W)
def check(K,C):
 s(K);assert(l(K,C),m(K,C))==(280,820);C.check(K)

import inspect
def q(K,C):
 s=inspect.getsource(K.f).replace(" ","")
 for x in('ifo=="R":returnx[::-1]','ifo=="S":returnsorted(x)','ifo=="u":returnlist(dict.fromkeys(x))','ifnotxandoin"<>":return[]','ifo=="<":returnx[1:]+x[:1]','ifo==">":returnx[-1:]+x[:-1]','ifoin"NADI2":return[f(o.lower(),v)forvinx]','ifoin"PMEO":return[vforvinxiff(o.lower(),v)]','elifo=="d":z=x-1','elifo=="i":z=x+1','elifo=="2":z=2*x'):assert x in s
 U,E=C.e(K);A={tuple(sorted(x))for x in E};N=set()
 def add(a,b):N.add(tuple(sorted((a,b))))
 for p in"R<>":
  for m in"NADI2":add(p+m,m+p)
 for f in"PMEO":add("R"+f,f+"R")
 for p in"R<>":add(p+"S","S")
 add("SS","S")
 for m in"DI2":add("S"+m,m+"S")
 for f in"PMEO":add("S"+f,f+"S")
 for m in"NDI2":add("u"+m,m+"u")
 for f in"PMEO":add("u"+f,f+"u")
 add("uS","Su");add("uu","u")
 for p in"R<>":add("u"+p+"u","u"+p)
 for m in"NADI2":add("u"+m+"u",m+"u")
 z=C.sg(K,"2O")
 for w in U:
  if w and C.sg(K,"".join(c for c in w if c in C.S))==z:add(w,"2O")
 N={x for x in N if x[0]!=x[1]}
 assert N<=A,(len(N-A),sorted(N-A)[:10])
 for o in K.L:assert K.f(o,[])==[]
 return N
def check(K,C):
 n=q(K,C);assert len(n)==280;C.check(K);return {"status":"PASS","derived_equations":len(n)}

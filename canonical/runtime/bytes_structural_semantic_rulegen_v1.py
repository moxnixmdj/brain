import scalar_props as s
def C(a,b):return tuple(sorted((a,b)))
def gen(k):
 z=set()
 def add(a,b):z.add(C(a,b))
 T="R<>";O=[o for o in k.L if o not in "RSu<>"]
 F=[o for o in O if isinstance(k.f(o.lower(),0),bool)];M=[o for o in O if o not in F]
 INC=[o for o in M if s.mono(o,1)];INJ=[o for o in M if s.inj(o)]
 A=[o for o in M if s.nonneg(o) and s.eq(o+o,o)][0]
 N=[o for o in M if s.mono(o,-1)][0]
 D=[o for o in M if s.even(o)][0]
 ODD=[o for o in F if s.dead(D+o)][0]
 comp=[(a,b) for a in F for b in F if a!=b and s.dead(a+b)]
 P=[o for o in F if s.pred(o)[0]==(False,False,True)][0]
 Q=[o for o in F if s.pred(o)[0]==(True,False,False)][0]
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
 add("SuR","SRu");add("Su>","S>u");add("S"+A+"R",N+"S"+A)
 add("S<"+Q,Q+"S<");add("S>"+P,P+"S>")
 return z
def check(E,k,S):
 g=gen(k);q=[e for e in E if not(set(e[0]+e[1])<=S)];u={C(*e) for e in q}
 return len(q),len(g),[e for e in q if C(*e) not in g],sorted(g-u)

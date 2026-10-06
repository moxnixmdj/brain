O=("rev","sort","uniq","rotl","rotr","neg","abs","inc","dec","dbl","pos","negonly","even","odd")
def a(o,x):
 if o=="rev":return x[::-1]
 if o=="sort":return sorted(x)
 if o=="uniq":return list(dict.fromkeys(x))
 if not x and o in ("rotl","rotr"):return []
 if o=="rotl":return x[1:]+x[:1]
 if o=="rotr":return x[-1:]+x[:-1]
 if o=="neg":return [-v for v in x]
 if o=="abs":return [abs(v) for v in x]
 if o=="inc":return [v+1 for v in x]
 if o=="dec":return [v-1 for v in x]
 if o=="dbl":return [2*v for v in x]
 if o=="pos":return [v for v in x if v>0]
 if o=="negonly":return [v for v in x if v<0]
 if o=="even":return [v for v in x if v%2==0]
 if o=="odd":return [v for v in x if v%2!=0]
 raise ValueError(o)
def r(p,x):
 y=list(x)
 for o in p:y=a(o,y)
 return y
def discover(examples,depth=3):
 e=[(list(x),list(y)) for x,y in examples]
 seen=set()
 q=[()]
 for d in range(depth+1):
  n=[]
  for p in q:
   sig=tuple(tuple(r(p,x)) for x,_ in e)
   if sig in seen:continue
   seen.add(sig)
   if all(list(s)==y for s,(_,y) in zip(sig,e)):return {"status":"EXACT_PROGRAM_FOUND","program":p,"states":len(seen)}
   if d<depth:
    for o in O:n.append(p+(o,))
  q=n
 return {"status":"MISS","program":None,"states":len(seen)}
def predict(c,x):return r(c["program"],x)

from itertools import product
def r(p,x,d):
 for o in p:x=d[o][x]
 return x
def s(d,y,n=4):
 m=range(len(y))
 for k in range(n+1):
  for p in product(range(len(d)),repeat=k):
   if [r(p,x,d) for x in m]==y:return p

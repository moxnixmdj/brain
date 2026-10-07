import itertools as I
A="+-<>[]"
def v(p):
 d=0
 for o in p:
  d+=(o=="[")-(o=="]")
  if d<0:return 0
 return d==0
def r(p,x,s=512):
 t={0:x%256};q=i=n=0
 while i<len(p) and n<s:
  o=p[i];z=t.get(q,0)
  if o=="+":t[q]=(z+1)%256
  elif o=="-":t[q]=(z-1)%256
  elif o==">":q+=1
  elif o=="<":q-=1
  elif o=="[" and z==0:
   d=1
   while d:i+=1;d+=(p[i]=="[")-(p[i]=="]")
  elif o=="]" and z:
   d=1
   while d:i-=1;d+=(p[i]=="]")-(p[i]=="[")
  i+=1;n+=1
 if i<len(p):return
 return (t.get(0,0),t.get(1,0))
def d(ex,m=6):
 for n in range(m+1):
  for p in I.product(A,repeat=n):
   if v(p) and all(r(p,x)==tuple(y) for x,y in ex):return "".join(p)

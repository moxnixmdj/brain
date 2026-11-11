from itertools import*
def r(p,x,d):
 for o in p:x=d[o][x]
 return x
def s(q,h=4):
 m,n=q[0]>>4,q[0]&15;z=int.from_bytes(q[1:],"little");a=[]
 for _ in range((n+1)*m):z,v=divmod(z,m);a+=[v]
 d=[a[i*m:i*m+m]for i in range(n)];y=a[n*m:]
 for k in range(h+1):
  for p in product(range(n),repeat=k):
   if all(r(p,x,d)==y[x]for x in range(m)):return p

from itertools import*
def r(p,x,d):
 for o in p:x=d[o][x]
 return x
def s(q,h=4):
 m,n=q[:2];b=(m-1).bit_length();z=int.from_bytes(q[2:],"little");a=[z>>b*i&(1<<b)-1 for i in range((n+1)*m)];d=[a[i*m:i*m+m]for i in range(n)];y=a[n*m:]
 for k in range(h+1):
  for p in product(range(n),repeat=k):
   if all(r(p,x,d)==y[x]for x in range(m)):return p

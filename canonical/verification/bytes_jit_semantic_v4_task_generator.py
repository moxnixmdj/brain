import hashlib,itertools,json
K="3ed44200c7fa8d1af27133302fd97e7527e79eb69e57c95c8f96ebeb5ed6d102"
def r(p,x,d):
 for o in p:x=d[o][x]
 return x
def h(d,y,n):
 m=range(len(y))
 for k in range(n+1):
  for p in itertools.product(range(len(d)),repeat=k):
   if [r(p,x,d)for x in m]==y:return p
def pack(d,y):
 m=len(y);n=len(d);a=sum(d,[])+y;z=sum(v*m**i for i,v in enumerate(a));return (bytes(((m<<4)|n,))+z.to_bytes((z.bit_length()+7)//8,"little")).hex()
def t(i):
 m=(5,7,11,13)[i%4];n=2+i%4;q=2+i%3;s=0
 while 1:
  b=hashlib.shake_256(f"{K}:V4:{i}:{s}".encode()).digest(n*m+q)
  d=[[v%m for v in b[j*m:(j+1)*m]]for j in range(n)];p=[b[n*m+j]%n for j in range(q)];y=[r(p,x,d)for x in range(m)]
  if h(d,y,q-1)==None:return {"id":f"V4_{i:02d}","minimal_depth":q,"packet_hex":pack(d,y)}
  s+=1
def g():return {"schema":"PROJECT_BRAIN_BYTES_JIT_SEMANTIC_V4_TASKS","kernel_sha256":K,"task_count":24,"tasks":[t(i)for i in range(1,25)]}
if __name__=="__main__":print(json.dumps(g(),sort_keys=True,separators=(",",":")))

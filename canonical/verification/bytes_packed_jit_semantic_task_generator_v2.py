import hashlib,itertools,json
K="a515bdc16ccce028e1696cd2315b1dbea7f69221a14547846dde997b3e256ed2"
def r(p,x,d):
 for o in p:x=d[o][x]
 return x
def h(d,y,n):
 m=range(len(y))
 for k in range(n+1):
  for p in itertools.product(range(len(d)),repeat=k):
   if [r(p,x,d)for x in m]==y:return p
def pack(d,y):
 m=len(y);n=len(d);b=(m-1).bit_length();a=sum(d,[])+y;z=sum(v<<(b*i)for i,v in enumerate(a));return (bytes((m,n))+z.to_bytes((len(a)*b+7)//8,"little")).hex()
def t(i):
 m=(5,7,11,13)[i%4];n=2+i%4;q=2+i%3;s=0
 while 1:
  b=hashlib.shake_256(f"{K}:PJIT:{i}:{s}".encode()).digest(n*m+q)
  d=[[v%m for v in b[j*m:(j+1)*m]]for j in range(n)];p=[b[n*m+j]%n for j in range(q)];y=[r(p,x,d)for x in range(m)]
  if h(d,y,q-1)==None:return {"id":f"PJST_{i:02d}","minimal_depth":q,"packet_hex":pack(d,y)}
  s+=1
def g():return {"schema":"PROJECT_BRAIN_BYTES_PACKED_JIT_SEMANTIC_TASKS_V2","kernel_sha256":K,"task_count":24,"tasks":[t(i)for i in range(1,25)]}
if __name__=="__main__":print(json.dumps(g(),sort_keys=True,separators=(",",":")))

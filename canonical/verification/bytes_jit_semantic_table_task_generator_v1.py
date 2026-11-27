import hashlib,itertools,json
K="499e40e9c9b5d6c42417b67c8eea47e229f68e58c011e46883f2fd0c979cab2d"
def r(p,x,d):
 for o in p:x=d[o][x]
 return x
def h(d,y,n):
 m=range(len(y))
 for k in range(n+1):
  for p in itertools.product(range(len(d)),repeat=k):
   if [r(p,x,d) for x in m]==y:return p
def t(i):
 m=(5,7,11,13)[i%4];n=2+i%4;q=2+i%3;s=0
 while 1:
  b=hashlib.shake_256(f"{K}:JITSEM:{i}:{s}".encode()).digest(n*m+q)
  d=[[v%m for v in b[j*m:(j+1)*m]] for j in range(n)]
  p=[b[n*m+j]%n for j in range(q)];y=[r(p,x,d) for x in range(m)]
  if h(d,y,q-1)==None:return {"id":f"JST_{i:02d}","domain_size":m,"primitive_tables":d,"target_table":y,"depth_limit":4}
  s+=1
def g():return {"schema":"PROJECT_BRAIN_BYTES_JIT_SEMANTIC_TABLE_TASKS_V1","kernel_sha256":K,"task_count":24,"tasks":[t(i) for i in range(1,25)]}
if __name__=="__main__":print(json.dumps(g(),sort_keys=True,separators=(",",":")))

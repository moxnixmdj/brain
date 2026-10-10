import json, sys, os
from exact_symbolic_route_v1 import execute
for line in open(sys.argv[1]):
    execute(json.loads(line))
root=os.path.realpath(sys.argv[2]) + os.sep
files=[]
for m in list(sys.modules.values()):
    p=getattr(m,'__file__',None)
    if p and p.endswith('.py'):
        rp=os.path.realpath(p)
        if rp.startswith(root):
            files.append(rp)
files=sorted(set(files))
open(sys.argv[3],'w').write('\n'.join(files)+'\n')
print(json.dumps({'files':len(files),'raw_bytes':sum(os.path.getsize(p) for p in files)}))

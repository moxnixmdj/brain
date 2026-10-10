import json, sys, time
from exact_symbolic_route_v1 import execute
from semantic_digest_v1 import digest
path=sys.argv[1]
passed=0; total=0; fail=[]; t0=time.time()
with open(path) as f:
    for line in f:
        c=json.loads(line); total+=1
        try:
            got=digest(execute(c))
            if got==c['expected']: passed+=1
            elif len(fail)<5: fail.append((total,c['op'],'MISMATCH'))
        except Exception as e:
            if len(fail)<5: fail.append((total,c['op'],type(e).__name__,str(e)[:200]))
print(json.dumps({'passed':passed,'total':total,'seconds':time.time()-t0,'fail':fail}))
raise SystemExit(0 if passed==total else 1)

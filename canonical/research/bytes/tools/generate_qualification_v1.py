import json, random, hashlib, sys
from exact_symbolic_route_v1 import execute
from semantic_digest_v1 import digest as h

def nonzero(r, vals):
    return r.choice([v for v in vals if v])

def gen(seed, per=70):
    r=random.Random(seed); cases=[]
    def add(op,p): cases.append({'op':op,'p':p,'expected':h(execute({'op':op,'p':p}))})
    for _ in range(per):
        vals=list(range(-9,10))
        a=nonzero(r,vals); b=r.randint(1,9); c=nonzero(r,vals); d=r.randint(1,9); e=nonzero(r,vals); f=r.randint(1,9)
        add('rat',[a,b,c,d,e,f])
    for _ in range(per):
        # mix arbitrary small polynomials and products with known factors
        deg=r.choice([2,3,4,5,6]); coeffs=[nonzero(r,range(-4,5))]+[r.randint(-5,5) for _ in range(deg)]
        add('factor',coeffs)
    for _ in range(per):
        deg=r.choice([2,3,4,5,6,7]); coeffs=[nonzero(r,range(-6,7))]+[r.randint(-7,7) for _ in range(deg)]; k=r.randint(0,deg)
        add('coeff',[coeffs,k])
    for _ in range(per):
        deg=r.choice([2,3,4]); coeffs=[nonzero(r,range(-4,5))]+[r.randint(-6,6) for _ in range(deg)]
        add('roots',coeffs)
    for _ in range(per):
        terms=[]
        for e in range(r.randint(2,8)+1):
            c=r.randint(-7,7)
            if c: terms.append([c,e])
        add('diff',[terms,r.randint(1,3)])
    for _ in range(per): add('sin_even_integral',[r.randint(0,16)])
    for _ in range(max(20,per//2)): add('hilbert_det',[r.randint(1,7)])
    for _ in range(per): add('binomial_identity',[r.randint(0,40)])
    for _ in range(per):
        a=nonzero(r,range(-8,9)); d=nonzero(r,range(-8,9)); add('limit_poly_ratio',[a,r.randint(-8,8),r.randint(-8,8),d,r.randint(-8,8)])
    for _ in range(per): add('limit_sinx',[nonzero(r,range(-12,13))])
    made=0
    while made<per:
        n=r.choice([2,3,4]); A=[r.randint(-5,5) for _ in range(n*n)]; vec=[r.randint(-6,6) for _ in range(n)]
        try:
            add('linear_solve',[n,A,vec]); made+=1
        except Exception:
            pass
    for _ in range(per):
        coeffs=[r.randint(-5,5) for _ in range(r.randint(2,6))]; add('series_coeff',[coeffs,r.randint(0,9)])
    return cases

if __name__=='__main__':
    seed=int(sys.argv[1]); out=sys.argv[2]; per=int(sys.argv[3]) if len(sys.argv)>3 else 70
    cases=gen(seed,per)
    data=('\n'.join(json.dumps(c,separators=(',',':')) for c in cases)+'\n').encode()
    open(out,'wb').write(data)
    print(json.dumps({'path':out,'cases':len(cases),'sha256':hashlib.sha256(data).hexdigest(),'seed':seed,'per':per}))

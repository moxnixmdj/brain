from fractions import Fraction as Q

def q(x):
    return x if isinstance(x,Q) else Q(x)

def exp(p,f):
    return sum((q(a)*q(b) for a,b in zip(p,f)),Q(0))

def pull(k,g):
    out=[]
    for row in k:
        r=[q(x) for x in row]
        if len(r)!=len(g) or sum(r,Q(0))!=1 or any(x<0 for x in r):
            raise ValueError("KERNEL")
        out.append(sum((r[j]*q(g[j]) for j in range(len(g))),Q(0)))
    return out

def push(p,k):
    if len(p)!=len(k): raise ValueError("DIM")
    m=len(k[0]); out=[Q(0)]*m
    for i,row in enumerate(k):
        r=[q(x) for x in row]
        if len(r)!=m or sum(r,Q(0))!=1 or any(x<0 for x in r):
            raise ValueError("KERNEL")
        for j in range(m): out[j]+=q(p[i])*r[j]
    return out

def identity(p,k,g):
    return exp(push(p,k),g)==exp(p,pull(k,g))

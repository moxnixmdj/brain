from itertools import combinations
from math import ceil, log2

class CoverError(ValueError): pass

def normalize(x):
    if not x: raise CoverError("EMPTY_WORLDS")
    y={w:set(a) for w,a in x.items()}
    if any(not a for a in y.values()): raise CoverError("EMPTY_ACCEPTABLE_SET")
    return y

def min_cover(x):
    x=normalize(x); worlds=set(x)
    actions=sorted(set().union(*x.values()),key=repr)
    support={a:{w for w,s in x.items() if a in s} for a in actions}
    for k in range(1,len(actions)+1):
        for c in combinations(actions,k):
            if set().union(*(support[a] for a in c))==worlds: return c
    raise CoverError("NO_COVER")

def cells(x): return len(min_cover(x))
def bits(x):
    k=cells(x)
    return 0 if k==1 else ceil(log2(k))

def verify():
    a={"w0":{"a","b"},"w1":{"a","c"},"w2":{"a"}}
    b={"w0":{"a"},"w1":{"b"},"w2":{"a","b"}}
    c={"w0":{"a","b"},"w1":{"b","c"},"w2":{"c","d"}}
    assert cells(a)==1 and bits(a)==0
    assert cells(b)==2 and bits(b)==1
    assert cells(c)==2 and cells(c)<len(c)
    return {"min_cells_equal_min_action_cover":True,
            "full_world_identification_not_required":True,
            "terminal_credit_delta":0}

if __name__=="__main__":
    import json; print(json.dumps(verify(),sort_keys=True))

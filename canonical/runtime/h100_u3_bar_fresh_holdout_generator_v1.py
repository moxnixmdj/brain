from __future__ import annotations

MASK=0xffffffff
SEED=2667241387
BACKGROUNDS=[46,48,120,32,126]
SYMBOLS=[*range(49,58),*range(65,91),*range(97,123),64,35,36,37,38]

class XorShift32:
    def __init__(self,seed:int=SEED):
        self.x=seed&MASK
        if self.x==0: raise ValueError("ZERO_SEED")
    def next(self)->int:
        x=self.x
        x=(x^((x<<13)&MASK))&MASK
        x=(x^(x>>17))&MASK
        x=(x^((x<<5)&MASK))&MASK
        self.x=x
        return x
    def randint(self,lo:int,hi:int)->int:
        if hi<lo: raise ValueError("RANGE")
        return lo+self.next()%(hi-lo+1)
    def choice(self,seq):
        if not seq: raise ValueError("EMPTY")
        return seq[self.next()%len(seq)]

def _distinct_symbols(rng,count,bg):
    out=[];used={bg}
    while len(out)<count:
        s=rng.choice(SYMBOLS)
        if s not in used:
            used.add(s);out.append(s)
    return out

def generate(case_count:int=10):
    rng=XorShift32()
    cases=[]
    for i in range(case_count):
        vertical=(i%2==0)
        bg=rng.choice(BACKGROUNDS)
        count=rng.randint(2,6)
        syms=_distinct_symbols(rng,count,bg)
        if vertical:
            widths=[rng.randint(2,4) for _ in range(count)]
            gaps=[rng.randint(2,5) for _ in range(count-1)]
            values=[rng.randint(3,14) for _ in range(count)]
            w=2+sum(widths)+sum(gaps)+rng.randint(2,5)
            h=max(max(values)+3,rng.randint(18,30))
            grid=[[bg]*w for _ in range(h)]
            baseline=h-2;x=2
            for j,(bw,val,s) in enumerate(zip(widths,values,syms)):
                for y in range(baseline-val+1,baseline+1):
                    for xx in range(x,x+bw): grid[y][xx]=s
                x+=bw+(gaps[j] if j<count-1 else 0)
            gold=[0,count,*values]
        else:
            heights=[rng.randint(2,3) for _ in range(count)]
            gaps=[rng.randint(2,4) for _ in range(count-1)]
            values=[rng.randint(4,18) for _ in range(count)]
            h=2+sum(heights)+sum(gaps)+rng.randint(2,5)
            w=max(max(values)+4,rng.randint(24,38))
            grid=[[bg]*w for _ in range(h)]
            y=2
            for j,(bh,val,s) in enumerate(zip(heights,values,syms)):
                for yy in range(y,y+bh):
                    for x in range(2,2+val): grid[yy][x]=s
                y+=bh+(gaps[j] if j<count-1 else 0)
            gold=[1,count,*values]
        inp=[h,w]+[v for row in grid for v in row]
        cases.append({"id":f"U3_BAR_FRESH_{i+1:02d}","input":inp,"gold":gold,"height":h,"width":w})
    return cases

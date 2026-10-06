from __future__ import annotations
import hashlib, json

SEED_COMMIT="35ebf135e63459d413aae8b843e875b081463069"
W=32; H=20

class Stream:
    def __init__(self,seed:bytes):
        self.seed=seed; self.counter=0; self.buf=b""
    def _fill(self):
        self.buf+=hashlib.sha256(self.seed+self.counter.to_bytes(8,"big")).digest()
        self.counter+=1
    def take(self,n:int)->bytes:
        while len(self.buf)<n: self._fill()
        out,self.buf=self.buf[:n],self.buf[n:]
        return out
    def below(self,n:int)->int:
        if n<1: raise ValueError("N_INVALID")
        # rejection to avoid modulo bias
        lim=(1<<32)-((1<<32)%n)
        while True:
            v=int.from_bytes(self.take(4),"big")
            if v<lim: return v%n
    def choice(self,seq):
        return seq[self.below(len(seq))]

def bits15(v:int):
    return [1 if v & (1<<s) else 0 for s in range(14,-1,-1)]

def generate():
    s=Stream(bytes.fromhex(SEED_COMMIT))
    patterns=[]
    while len(patterns)<10:
        v=int.from_bytes(s.take(2),"big") & 0x7fff
        if v and v not in patterns: patterns.append(v)
    digits=list(range(10))
    for i in range(9,0,-1):
        j=s.below(i+1); digits[i],digits[j]=digits[j],digits[i]
    atlas=list(zip(patterns,digits))
    d2p={d:p for p,d in atlas}
    tasks=[]
    for ti in range(6):
        axis_x=s.choice([5,6,7])
        baseline=s.choice([15,16,17])
        tick=s.choice([6,7,8,9])
        legend=s.below(10)
        n=s.choice([2,3,4])
        vals=[2+s.below(min(tick,baseline-2)-1) for _ in range(n)]
        widths=[s.choice([2,3,4]) for _ in range(n)]
        gaps=[s.choice([2,3]) for _ in range(max(0,n-1))]
        grid=[["0"]*W for _ in range(H)]
        for y in range(1,baseline+1): grid[y][axis_x]="1"
        for x in range(axis_x,30): grid[baseline][x]="1"
        b=bits15(d2p[tick]); k=0; tx=axis_x-4
        for yy in range(1,6):
            for xx in range(tx,tx+3):
                if b[k]: grid[yy][xx]="3"
                k+=1
        x=axis_x+3; actual=[]
        for j,(v,wid) in enumerate(zip(vals,widths)):
            if x+wid>=21: break
            for yy in range(baseline-v,baseline):
                for xx in range(x,x+wid): grid[yy][xx]="2"
            actual.append(v)
            if j<len(gaps): x+=wid+gaps[j]
        swx=s.choice([21,22,23])
        for yy in range(2,4):
            for xx in range(swx,swx+2): grid[yy][xx]="4"
        lx=swx+4; b=bits15(d2p[legend]); k=0
        for yy in range(1,6):
            for xx in range(lx,lx+3):
                if b[k]: grid[yy][xx]="3"
                k+=1
        tasks.append({
            "id":f"FRESH_CHART_{ti+1}",
            "public_input":{"rows":["".join(r) for r in grid],"atlas":[list(x) for x in atlas]},
            "gold":{"tick":tick,"legend":legend,"bar_count":len(actual),"values":actual},
            "meta":{"axis_x":axis_x,"baseline":baseline,"swatch_x":swx}
        })
    return {
      "schema":"PROJECT_BRAIN_H100_U1_CHART_FRESH_WORLD_V1",
      "seed_commit":SEED_COMMIT,
      "atlas":[list(x) for x in atlas],
      "tasks":tasks
    }

def canonical_bytes():
    return json.dumps(generate(),sort_keys=True,separators=(",",":")).encode()

if __name__=="__main__":
    b=canonical_bytes()
    print(hashlib.sha256(b).hexdigest())
    print(b.decode())

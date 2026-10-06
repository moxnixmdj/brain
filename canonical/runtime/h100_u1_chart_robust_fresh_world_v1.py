from __future__ import annotations
import hashlib,json

SEED_COMMIT="3d129f132ef82a35220dc07a6a4cd1077c89ef8c"
W=32;H=20

class Stream:
 def __init__(self,seed): self.seed=seed;self.c=0;self.buf=b""
 def fill(self): self.buf+=hashlib.sha256(self.seed+self.c.to_bytes(8,"big")).digest();self.c+=1
 def take(self,n):
  while len(self.buf)<n:self.fill()
  o,self.buf=self.buf[:n],self.buf[n:];return o
 def below(self,n):
  lim=(1<<32)-((1<<32)%n)
  while True:
   v=int.from_bytes(self.take(4),"big")
   if v<lim:return v%n
 def choice(self,a): return a[self.below(len(a))]

def bits15(v): return [1 if v&(1<<s) else 0 for s in range(14,-1,-1)]

def generate():
 s=Stream(bytes.fromhex(SEED_COMMIT))
 pats=[]
 while len(pats)<10:
  v=int.from_bytes(s.take(2),"big")&0x7fff
  if v and v not in pats:pats.append(v)
 digs=list(range(10))
 for i in range(9,0,-1):
  j=s.below(i+1);digs[i],digs[j]=digs[j],digs[i]
 atlas=list(zip(pats,digs));d2p={d:p for p,d in atlas}
 tasks=[]
 for ti in range(6):
  ax=s.choice([4,5,6,7,8]);base=s.choice([14,15,16,17,18]);tick=s.choice([5,6,7,8,9]);legend=s.below(10);n=s.choice([2,3,4])
  vals=[2+s.below(min(tick,base-2)-1) for _ in range(n)]
  widths=[s.choice([2,3,4]) for _ in range(n)];gaps=[s.choice([2,3]) for _ in range(max(0,n-1))]
  g=[["0"]*W for _ in range(H)]
  for y in range(1,base+1):g[y][ax]="1"
  for x in range(ax,30):g[base][x]="1"
  b=bits15(d2p[tick]);k=0;tx=ax-4
  for y in range(1,6):
   for x in range(tx,tx+3):
    if b[k]:g[y][x]="3"
    k+=1
  x=ax+3;actual=[]
  for j,(v,wid) in enumerate(zip(vals,widths)):
   if x+wid>=21:break
   for y in range(base-v,base):
    for xx in range(x,x+wid):g[y][xx]="2"
   actual.append(v)
   if j<len(gaps):x+=wid+gaps[j]
  swx=s.choice([20,21,22,23])
  for y in range(2,4):
   for x in range(swx,swx+2):g[y][x]="4"
  lx=swx+4;b=bits15(d2p[legend]);k=0
  for y in range(1,6):
   for x in range(lx,lx+3):
    if x<W and b[k]:g[y][x]="3"
    k+=1

  kind=["MONOCHROME","NONZERO_BACKGROUND_PALETTE","TICK_TWO_PIXEL_DAMAGE","LEGEND_SHIFT_DAMAGE","MONOCHROME_NONZERO_BG","SPARSE_PIXEL_NOISE"][ti]
  if kind=="MONOCHROME":
   for y in range(H):
    for x in range(W):
     if g[y][x]!="0":g[y][x]="1"
  elif kind=="NONZERO_BACKGROUND_PALETTE":
   mp={"0":"5","1":"9","2":"7","3":"6","4":"8"}
   for y in range(H):
    for x in range(W):g[y][x]=mp[g[y][x]]
  elif kind=="TICK_TWO_PIXEL_DAMAGE":
   removed=0
   for y in range(1,6):
    for x in range(max(0,tx),min(W,tx+3)):
     if g[y][x]=="3" and removed<2:g[y][x]="0";removed+=1
  elif kind=="LEGEND_SHIFT_DAMAGE":
   pts=[]
   for y in range(H):
    for x in range(max(0,swx),W):
     if g[y][x] in ("3","4"):pts.append((y,x,g[y][x]));g[y][x]="0"
   for y,x,ch in pts:
    if y+2<H and x+1<W:g[y+2][x+1]=ch
   removed=False
   for y in range(2,min(9,H)):
    for x in range(ax+8,W):
     if g[y][x]=="3" and not removed:g[y][x]="0";removed=True;break
    if removed:break
  elif kind=="MONOCHROME_NONZERO_BG":
   for y in range(H):
    for x in range(W):g[y][x]="5" if g[y][x]=="0" else "8"
  else:
   for y,x in [(0,W-1),(H-1,0),(0,0)]:
    if g[y][x]=="0":g[y][x]="9"

  tasks.append({"id":f"ROBUST_FRESH_{ti+1}_{kind}","public_input":{"rows":["".join(r) for r in g],"atlas":[list(z) for z in atlas]},"gold":{"tick":tick,"legend":legend,"bar_count":len(actual),"values":actual},"meta":{"axis_x":ax,"baseline":base,"kind":kind}})
 return {"schema":"PROJECT_BRAIN_H100_U1_CHART_ROBUST_FRESH_WORLD_V1","seed_commit":SEED_COMMIT,"tasks":tasks}

if __name__=="__main__":print(json.dumps(generate(),indent=2,sort_keys=True))

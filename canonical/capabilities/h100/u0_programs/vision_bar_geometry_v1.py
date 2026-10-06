def _variance(v):
 n=len(v)
 s=0
 for x in v:
  s=s+x
 m=s/n
 q=0
 for x in v:
  d=x-m
  q=q+d*d
 return q/n

def solve(inp):
 rows=inp["rows"]
 h=len(rows)
 if h<2:
  return {"status":"ABSTAIN_SHAPE"}
 w=len(rows[0])
 if w<2:
  return {"status":"ABSTAIN_SHAPE"}
 for r in rows:
  if len(r)!=w:
   return {"status":"ABSTAIN_SHAPE"}

 counts={}
 for y in range(h):
  for x in range(w):
   ch=rows[y][x]
   if ch in counts:
    counts[ch]=counts[ch]+1
   else:
    counts[ch]=1
 bg=None
 best=-1
 for ch in counts:
  if counts[ch]>best:
   bg=ch
   best=counts[ch]

 seen={}
 comps=[]
 for y in range(h):
  for x in range(w):
   k=y*w+x
   if rows[y][x]==bg or k in seen:
    continue
   q=[(y,x)]
   seen[k]=1
   qi=0
   area=0
   x0=x
   x1=x
   y0=y
   y1=y
   while qi<len(q):
    yy=q[qi][0]
    xx=q[qi][1]
    qi=qi+1
    area=area+1
    if xx<x0:
     x0=xx
    if xx>x1:
     x1=xx
    if yy<y0:
     y0=yy
    if yy>y1:
     y1=yy
    for d in ((1,0),(-1,0),(0,1),(0,-1)):
     ny=yy+d[0]
     nx=xx+d[1]
     if ny>=0 and ny<h and nx>=0 and nx<w:
      nk=ny*w+nx
      if rows[ny][nx]!=bg and nk not in seen:
       seen[nk]=1
       q=q+[(ny,nx)]
   bw=x1-x0+1
   bh=y1-y0+1
   if area>=4 and area*100>=95*bw*bh:
    comps=comps+[(x0,y0,x1,y1,bw,bh)]

 if len(comps)<2:
  return {"status":"ABSTAIN_COMPONENTS"}

 bottoms=[]
 lefts=[]
 tall=0
 wide=0
 for c in comps:
  bottoms=bottoms+[c[3]]
  lefts=lefts+[c[0]]
  wide=wide+c[4]
  tall=tall+c[5]
 vs=_variance(bottoms)
 hs=_variance(lefts)

 if vs<hs:
  orientation="vertical"
 elif hs<vs:
  orientation="horizontal"
 elif tall>=wide:
  orientation="vertical"
 else:
  orientation="horizontal"

 ordered=[]
 if orientation=="vertical":
  for c in comps:
   ordered=ordered+[(c[0],c[5])]
 else:
  for c in comps:
   ordered=ordered+[(c[1],c[4])]
 ordered=sorted(ordered)
 values=[]
 for p in ordered:
  values=values+[p[1]]
 return {"orientation":orientation,"bar_count":len(values),"values":values}

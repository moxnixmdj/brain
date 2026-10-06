from __future__ import annotations
from collections import Counter

FONT={
0:["01110","10001","10001","10001","10001","10001","01110"],
1:["00100","01100","00100","00100","00100","00100","01110"],
2:["01110","10001","00001","00010","00100","01000","11111"],
3:["11110","00001","00001","01110","00001","00001","11110"],
4:["00010","00110","01010","10010","11111","00010","00010"],
5:["11111","10000","10000","11110","00001","00001","11110"],
6:["01110","10000","10000","11110","10001","10001","01110"],
7:["11111","00001","00010","00100","01000","01000","01000"],
8:["01110","10001","10001","01110","10001","10001","01110"],
9:["01110","10001","10001","01111","00001","00001","01110"],
}

class ChartParserError(ValueError): pass

def _norm_template(rows):
 pts={(y,x) for y,r in enumerate(rows) for x,b in enumerate(r) if b=="1"}
 miny=min(y for y,x in pts); minx=min(x for y,x in pts)
 maxy=max(y for y,x in pts); maxx=max(x for y,x in pts)
 return (maxx-minx+1,maxy-miny+1,tuple(sorted((y-miny,x-minx) for y,x in pts)))

TEMPLATES={d:_norm_template(r) for d,r in FONT.items()}

def _max_run(rows,ch):
 h=len(rows); w=len(rows[0]); best=0
 for y in range(h):
  cur=0
  for x in range(w):
   if rows[y][x]==ch: cur+=1; best=max(best,cur)
   else: cur=0
 for x in range(w):
  cur=0
  for y in range(h):
   if rows[y][x]==ch: cur+=1; best=max(best,cur)
   else: cur=0
 return best

def _runs(vals):
 vals=sorted(set(vals))
 if not vals: return []
 out=[]; start=prev=vals[0]
 for v in vals[1:]:
  if v==prev+1: prev=v
  else: out.append((start,prev)); start=prev=v
 out.append((start,prev))
 return out

def _ocr_band(rows,ink,xlo,xhi,ylo,yhi):
 cols=[x for x in range(xlo,xhi+1) if any(rows[y][x]==ink for y in range(ylo,yhi+1))]
 digits=[]
 for xa,xb in _runs(cols):
  pts={(y,x) for y in range(ylo,yhi+1) for x in range(xa,xb+1) if rows[y][x]==ink}
  if not pts: continue
  miny=min(y for y,x in pts); minx=min(x for y,x in pts)
  maxy=max(y for y,x in pts); maxx=max(x for y,x in pts)
  sig=(maxx-minx+1,maxy-miny+1,tuple(sorted((y-miny,x-minx) for y,x in pts)))
  matches=[d for d,s in TEMPLATES.items() if s==sig]
  if len(matches)!=1: raise ChartParserError("OCR_AMBIGUOUS")
  digits.append(matches[0])
 if not digits: raise ChartParserError("OCR_EMPTY")
 n=0
 for d in digits: n=n*10+d
 return n

def _components(rows,color,xlo,xhi,ylo,yhi):
 h=len(rows); w=len(rows[0]); seen=set(); out=[]
 for y in range(max(0,ylo),min(h,yhi+1)):
  for x in range(max(0,xlo),min(w,xhi+1)):
   if rows[y][x]!=color or (y,x) in seen: continue
   q=[(y,x)]; seen.add((y,x)); pts=[]
   while q:
    yy,xx=q.pop(); pts.append((yy,xx))
    for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
     ny,nx=yy+dy,xx+dx
     if ylo<=ny<=yhi and xlo<=nx<=xhi and 0<=ny<h and 0<=nx<w and rows[ny][nx]==color and (ny,nx) not in seen:
      seen.add((ny,nx)); q.append((ny,nx))
   ys=[p[0] for p in pts]; xs=[p[1] for p in pts]
   out.append({"y0":min(ys),"y1":max(ys),"x0":min(xs),"x1":max(xs),"area":len(pts),"color":color})
 return out

def parse(rows,query):
 if not rows or len({len(r) for r in rows})!=1: raise ChartParserError("RASTER_SHAPE")
 h=len(rows); w=len(rows[0])
 counts=Counter("".join(rows)); bg=counts.most_common(1)[0][0]
 chars=[c for c in counts if c!=bg]
 if len(chars)<2: raise ChartParserError("INSUFFICIENT_COLORS")
 ink=max(chars,key=lambda c:_max_run(rows,c))

 col_counts=[sum(rows[y][x]==ink for y in range(h)) for x in range(w)]
 axis_x=max(range(w),key=lambda x:col_counts[x])
 row_counts=[sum(rows[y][x]==ink for x in range(w)) for y in range(h)]
 base_y=max(range(h),key=lambda y:row_counts[y])
 axis_ys=[y for y in range(h) if rows[y][axis_x]==ink]
 top_y=min(axis_ys)
 plot_right=axis_x
 while plot_right+1<w and rows[base_y][plot_right+1]==ink: plot_right+=1

 left_hi=max(0,axis_x-4)
 band_rows=[y for y in range(h) if any(rows[y][x]==ink for x in range(left_hi+1))]
 bands=_runs(band_rows)
 labels=[]
 for ya,yb in bands:
  try: val=_ocr_band(rows,ink,0,left_hi,ya,yb)
  except ChartParserError: continue
  labels.append(((ya+yb)/2,val))
 labels=sorted(labels)
 if len(labels)<2: raise ChartParserError("AXIS_LABELS_MISSING")
 top_value=labels[0][1]; bottom_value=labels[-1][1]

 colors=[c for c in chars if c!=ink]
 legend_swatches=[]
 for color in colors:
  for comp in _components(rows,color,plot_right+1,w-1,0,h-1):
   if comp["area"]>=4: legend_swatches.append(comp)

 legend_rows=[y for y in range(h) if any(rows[y][x]==ink for x in range(plot_right+1,w))]
 legend_labels=[]
 for ya,yb in _runs(legend_rows):
  try: val=_ocr_band(rows,ink,plot_right+1,w-1,ya,yb)
  except ChartParserError: continue
  legend_labels.append(((ya+yb)/2,val))
 if not legend_labels: raise ChartParserError("LEGEND_LABELS_MISSING")

 mapping={}
 for sw in legend_swatches:
  cy=(sw["y0"]+sw["y1"])/2
  nearest=min(legend_labels,key=lambda p:abs(p[0]-cy))
  mapping[nearest[1]]=sw["color"]

 bars=[]
 for color in colors:
  for comp in _components(rows,color,axis_x+1,plot_right,0,base_y-1):
   if comp["area"]>=4: bars.append(comp)
 bars.sort(key=lambda c:(c["x0"],c["y0"]))
 nseries=len(mapping)
 if nseries<1 or len(bars)%nseries!=0: raise ChartParserError("BAR_GROUPING_INVALID")
 groups=[bars[i:i+nseries] for i in range(0,len(bars),nseries)]
 category=int(query["category_index"])
 series_label=int(query["series_label"])
 if category<0 or category>=len(groups) or series_label not in mapping: raise ChartParserError("QUERY_OUT_OF_SCOPE")
 color=mapping[series_label]
 chosen=[b for b in groups[category] if b["color"]==color]
 if len(chosen)!=1: raise ChartParserError("SERIES_SELECTION_AMBIGUOUS")
 bar=chosen[0]
 height=base_y-bar["y0"]
 numerator=height*(top_value-bottom_value)
 denominator=base_y-top_y
 if denominator==0 or numerator%denominator!=0: raise ChartParserError("NONINTEGRAL_SCALE")
 return bottom_value+numerator//denominator

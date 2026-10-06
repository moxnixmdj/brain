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

def _draw_text(grid,x,y,text,ch):
 cx=x
 for c in str(text):
  rows=FONT[int(c)]
  for dy,row in enumerate(rows):
   for dx,b in enumerate(row):
    if b=="1": grid[y+dy][cx+dx]=ch
  cx+=6

def render(layout):
 w=layout["width"]; h=layout["height"]; bg=layout["bg"]; ink=layout["ink"]
 ax=layout["axis_x"]; ty=layout["top_y"]; by=layout["base_y"]; pr=layout["plot_right"]
 top=layout["top_value"]; colors=layout["colors"]; labels=layout["labels"]; values=layout["values"]
 g=[[bg]*w for _ in range(h)]
 for y in range(ty,by+1): g[y][ax]=ink
 for x in range(ax,pr+1): g[by][x]=ink
 for x in range(ax-3,ax+1): g[ty][x]=ink; g[by][x]=ink
 _draw_text(g,1,ty-3,str(top),ink)
 _draw_text(g,max(1,ax-12),by-3,"0",ink)
 lx=pr+6
 for j,(color,label) in enumerate(zip(colors,labels)):
  yy=3+j*10
  for y in range(yy,yy+3):
   for x in range(lx,lx+3): g[y][x]=color
  _draw_text(g,lx+6,yy-2,str(label),ink)
 start=ax+6; usable=pr-start-7; step=usable//2; gx=[start,start+step,start+2*step]
 scale=(by-ty)/top
 for ci,vals in enumerate(values):
  for si,val in enumerate(vals):
   hh=val*scale
   if abs(hh-round(hh))>1e-12: raise ValueError("NONINTEGRAL_HEIGHT")
   hh=int(round(hh)); x0=gx[ci]+si*4
   for y in range(by-hh,by):
    for x in range(x0,x0+3): g[y][x]=colors[si]
 return ["".join(r) for r in g]

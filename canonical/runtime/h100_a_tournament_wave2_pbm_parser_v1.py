from __future__ import annotations

class VisionParseError(ValueError):pass

def _pbm(s):
 t=s.split()
 if len(t)<3 or t[0]!="P1":raise VisionParseError("FORMAT")
 w,h=int(t[1]),int(t[2]);v=list(map(int,t[3:]))
 if len(v)!=w*h or any(x not in(0,1) for x in v):raise VisionParseError("PIXELS")
 return [v[i*w:(i+1)*w] for i in range(h)],w,h

def _rects(a,w,h):
 seen=[[0]*w for _ in range(h)];o=[]
 for y0 in range(h):
  for x0 in range(w):
   if a[y0][x0]!=1 or seen[y0][x0]:continue
   st=[(y0,x0)];seen[y0][x0]=1;p=[]
   while st:
    y,x=st.pop();p.append((y,x))
    for dy,dx in((1,0),(-1,0),(0,1),(0,-1)):
     Y,X=y+dy,x+dx
     if 0<=Y<h and 0<=X<w and a[Y][X]==1 and not seen[Y][X]:
      seen[Y][X]=1;st.append((Y,X))
   ys=[q[0] for q in p];xs=[q[1] for q in p];a0,b0,c0,d0=min(xs),max(xs),min(ys),max(ys)
   bw,bh=b0-a0+1,d0-c0+1
   if bw>=2 and bh>=2 and len(p)>=6 and len(p)==bw*bh:o.append((a0,b0,c0,d0,bw,bh))
 return o

def solve(pbm_text,question):
 a,w,h=_pbm(pbm_text);b=_rects(a,w,h)
 if not 3<=len(b)<=7:return{"status":"ABSTAIN_BAR_SET_INVALID","bar_count":len(b)}
 vs=(len({x[4] for x in b})-1)*100+max(x[3] for x in b)-min(x[3] for x in b)
 hs=(len({x[5] for x in b})-1)*100+max(x[0] for x in b)-min(x[0] for x in b)
 if vs==hs:return{"status":"ABSTAIN_ORIENTATION_AMBIGUOUS"}
 ori="VERTICAL" if vs<hs else "HORIZONTAL"
 b=sorted(b,key=lambda x:x[0] if ori=="VERTICAL" else x[2])
 L=[x[5] if ori=="VERTICAL" else x[4] for x in b];q=question["type"]
 if q=="COUNT_BARS":ans=len(L)
 elif q=="ARGMAX_INDEX":
  m=max(L)
  if L.count(m)>1:return{"status":"ABSTAIN_RENDERED_LENGTH_AMBIGUOUS","orientation":ori,"lengths":L}
  ans=L.index(m)
 elif q=="ARGMIN_INDEX":
  m=min(L)
  if L.count(m)>1:return{"status":"ABSTAIN_RENDERED_LENGTH_AMBIGUOUS","orientation":ori,"lengths":L}
  ans=L.index(m)
 elif q=="COMPARE_I_GT_J":
  i,j=int(question["i"]),int(question["j"])
  if not(0<=i<len(L) and 0<=j<len(L)):return{"status":"ABSTAIN_QUESTION_INVALID"}
  if L[i]==L[j]:return{"status":"ABSTAIN_RENDERED_LENGTH_AMBIGUOUS","orientation":ori,"lengths":L}
  ans=L[i]>L[j]
 else:return{"status":"ABSTAIN_QUESTION_UNSUPPORTED"}
 return{"status":"ANSWER","answer":ans,"orientation":ori,"lengths":L}

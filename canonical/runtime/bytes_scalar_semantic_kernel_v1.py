def st(q,o):
 a,b,d,p=q
 if not d:return q
 if o=="N":return(-a,-b,d,p)
 if o=="D":return(a,b-1,d,p)
 if o=="I":return(a,b+1,d,p)
 if o=="2":return(2*a,2*b,d,p)
 s=1 if a*d>0 else -1
 if o=="A":return(a,b,d,p) if s>0 else(-a,-b,d,p)
 if o=="P":return(a,b,d if s>0 else 0,p)
 if o=="M":return(a,b,d if s<0 else 0,p)
 y=(a*p+b)&1
 if o=="E":return(a,b,d if y==0 else 0,p)
 if o=="O":return(a,b,d if y==1 else 0,p)
def tail(w,d,p):
 q=(1,0,d,p)
 for o in w:q=st(q,o)
 return q[:3] if q[2] else None
def pt(w,x):
 for o in w:
  if o=="N":x=-x
  elif o=="A":x=abs(x)
  elif o=="D":x-=1
  elif o=="I":x+=1
  elif o=="2":x*=2
  elif o=="P":
   if x<=0:return
  elif o=="M":
   if x>=0:return
  elif o=="E":
   if x&1:return
  elif o=="O":
   if not x&1:return
 return x
def eq(a,b):
 return all(pt(a,x)==pt(b,x) for x in range(-3,3)) and all(tail(a,d,p)==tail(b,d,p) for d in(-1,1) for p in(0,1))
def dead(w):
 return all(pt(w,x) is None for x in range(-3,3)) and all(tail(w,d,p) is None for d in(-1,1) for p in(0,1))
def mono(w,s):
 if any(pt(w,x) is None for x in range(-4,4)):return False
 y=[pt(w,x) for x in range(-4,4)]
 if not all((y[i+1]-y[i])*s>0 for i in range(len(y)-1)):return False
 for d in(-1,1):
  q=tail(w,d,0)
  if q is None or q[0]*s<=0:return False
 return True
def inj(w):return mono(w,1) or mono(w,-1)
def nonneg(w):
 if any((z:=pt(w,x)) is None or z<0 for x in range(-3,3)):return False
 return all((q:=tail(w,d,p)) is not None and q[0]*d>0 for d in(-1,1) for p in(0,1))
def even(w):
 if any((z:=pt(w,x)) is None or z&1 for x in range(-3,3)):return False
 return all((q:=tail(w,d,p)) is not None and ((q[0]*p+q[1])&1)==0 for d in(-1,1) for p in(0,1))
def pred(o):
 a=[pt(o,x) is not None for x in (-1,0,1)]
 t=[[tail(o,d,p) is not None for p in(0,1)] for d in(-1,1)]
 return tuple(a),tuple(map(tuple,t))

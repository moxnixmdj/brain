from itertools import product
M="NADI2"
SCHEMA="PROJECT_BRAIN_BYTES_SCALAR_SMALL_MODEL_V1"
def ev(w,x):
 for o in w:
  if o=="N":x=-x
  elif o=="A":x=abs(x)
  elif o=="D":x-=1
  elif o=="I":x+=1
  elif o=="2":x*=2
 return x
def words(d):
 q=[()]
 for n in range(1,d+1):q+=list(product(M,repeat=n))
 return q
def order_shape(w):
 f=("aff",1,0)
 for o in w:
  if f[0]=="aff":
   _,a,b=f
   if o=="N":f=("aff",-a,-b)
   elif o=="D":f=("aff",a,b-1)
   elif o=="I":f=("aff",a,b+1)
   elif o=="2":f=("aff",2*a,2*b)
   elif o=="A":f=("abs",1,a,b,0)
  else:
   _,k,a,b,d=f
   if o=="N":f=("abs",-k,a,b,-d)
   elif o=="D":f=("abs",k,a,b,d-1)
   elif o=="I":f=("abs",k,a,b,d+1)
   elif o=="2":f=("abs",2*k,a,b,2*d)
   elif o=="A":
    if d: raise ValueError("NESTED_SHIFTED_ABS")
    f=("abs",abs(k),a,b,0)
 if f[0]=="aff":return ("inc" if f[1]>0 else "dec",None)
 from fractions import Fraction
 _,k,a,b,d=f;c=Fraction(-b,a)
 if c not in (-1,0,1):raise ValueError("CENTER_OUT_OF_BASIS")
 return ("abs" if k>0 else "rabs",int(c))
def reduced_cmp(w,x,y):
 k,c=order_shape(w)
 if k=="inc":d=x-y
 elif k=="dec":d=y-x
 else:
  d=(x-y)*(x+y-2*c)
  if k=="rabs":d=-d
 return (d>0)-(d<0)
def direct_cmp(w,x,y):
 a,b=ev(w,x),ev(w,y);return (a>b)-(a<b)
def catx(x):
 if x<-2:return 0
 if x==-2:return 1
 if x<-1:return 2
 if x==-1:return 3
 if x<0:return 4
 if x==0:return 5
 if x<1:return 6
 if x==1:return 7
 if x<2:return 8
 if x==2:return 9
 return 10
def cats(s):
 if s<-2:return 0
 if s==-2:return 1
 if s<0:return 2
 if s==0:return 3
 if s<2:return 4
 if s==2:return 5
 return 6
def relation_signature(t):
 q=[]
 for x in t:q += [catx(x),x&1]
 for i in range(len(t)):
  for j in range(i+1,len(t)):q += [(t[i]>t[j])-(t[i]<t[j]),cats(t[i]+t[j])]
 return tuple(q)
def compress_tuple(t):
 mags=sorted({abs(x) for x in t if abs(x)>=3});mp={}
 if mags:
  m=mags[0];n=m if m<=4 else (5 if m&1 else 6);mp[m]=n
  for a,b in zip(mags,mags[1:]):
   g=b-a;n+=g if g<=2 else (3 if g&1 else 4);mp[b]=n
 return tuple(x if abs(x)<=2 else (mp[abs(x)] if x>0 else -mp[abs(x)]) for x in t)
def verify():
 w=words(2)
 for p in w:
  for x in range(-20,21):
   for y in range(-20,21):assert reduced_cmp(p,x,y)==direct_cmp(p,x,y)
 checked=0
 for n in range(1,5):
  for t in product(range(-8,9),repeat=n):
   c=compress_tuple(t);assert max(map(abs,c),default=0)<=18;assert relation_signature(t)==relation_signature(c);checked+=1
 return {"schema":SCHEMA,"status":"PASS","prefixes":len(w),"pair_checks":len(w)*41*41,"tuple_checks":checked,"representative_abs_bound":18}

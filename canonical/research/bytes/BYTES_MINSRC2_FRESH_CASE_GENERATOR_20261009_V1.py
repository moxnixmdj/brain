import json, random, math
from fractions import Fraction
rnd=random.Random(20261009175531)
cases=[]
def add(op,**kw): cases.append({'id':len(cases)+1,'op':op,**kw})
for _ in range(120):
    add('rational_sum',a_num=rnd.randint(-10**12,10**12),a_den=rnd.randint(1,10**6),b_num=rnd.randint(-10**12,10**12),b_den=rnd.randint(1,10**6))
def pmul(a,b):
    out=[0]*(len(a)+len(b)-1)
    for i,x in enumerate(a):
      for j,y in enumerate(b):out[i+j]+=x*y
    return out
for _ in range(220):
    p=[rnd.choice([-12,-6,-3,-2,-1,1,2,3,6,12])]
    deg=rnd.randint(1,14)
    for _j in range(deg): p=pmul(p,[1,-rnd.randint(-25,25)])
    add('factor',coeffs=p)
for _ in range(110):
    p=[rnd.choice([-6,-3,-1,1,2,5])]
    for _q in range(rnd.randint(1,4)): p=pmul(p,[1,0,rnd.randint(1,15)])
    for _j in range(rnd.randint(0,5)): p=pmul(p,[1,-rnd.randint(-15,15)])
    add('factor',coeffs=p)
for n in range(2,21):
    add('factor',coeffs=[1]+[0]*(n-1)+[-1])
    add('factor',coeffs=[1]+[0]*(n-1)+[1])
for _ in range(300):
    deg=rnd.randint(0,35); coeffs=[rnd.randint(-5000,5000) for _ in range(deg+1)]
    if coeffs[0]==0:coeffs[0]=rnd.choice([-3,-1,1,2,5])
    add('coefficient',coeffs=coeffs,power=rnd.randint(0,deg+5))
for deg in range(1,5):
  for _ in range(75):
    roots=sorted(rnd.sample(range(-40,41),deg));p=[rnd.choice([1,2,3,5])]
    for r in roots:p=pmul(p,[1,-r])
    add('roots',coeffs=p)
q=0
while q<170:
    a=rnd.randint(1,12);b=rnd.randint(-30,30);c=rnd.randint(-25,25);D=b*b-4*a*c
    if D>0 and math.isqrt(D)**2!=D:
        add('roots',coeffs=[a,b,c]);q+=1
add('differentiate',kind='xpowx')
for n in range(1,81): add('differentiate',kind='power',n=n)
for a in list(range(-20,0))+list(range(1,21)):
    add('differentiate',kind='exp_linear',a=a); add('differentiate',kind='sin_linear',a=a)
for m in range(1,41):add('integrate_sin_even',m=m)
for n in range(1,7):
  for _ in range(16):
    add('determinant',matrix=[[rnd.randint(-12,12) for _ in range(n)] for __ in range(n)])
for n in range(1,8):add('hilbert_determinant',n=n)
for n in list(range(0,101))+[127,150,200,255,300]: add('binomial_square_sum',n=n)
for a in list(range(-50,0))+list(range(1,51)): add('limit_sin_linear_over_x',a=a)
for _ in range(180):
  while True:
    a,b,c,d=[rnd.randint(-50,50) for _ in range(4)]
    if a*d-b*c:break
  e,f=[rnd.randint(-100,100) for _ in range(2)]
  add('linear2',A=[[a,b],[c,d]],b=[e,f])
for _ in range(280):
    a=rnd.choice([z for z in range(-8,9) if z]); b=rnd.choice([z for z in range(-8,9) if z]); n=rnd.randint(1,30)
    add('series_exp_sin_coeff',a=a,b=b,n=n)
print(json.dumps({'seed':20261009175531,'cases':cases},separators=(',',':')))

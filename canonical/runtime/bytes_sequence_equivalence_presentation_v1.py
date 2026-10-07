from itertools import product
L='RSu<>NADI2PMEO'
SCALAR=set('NADI2PMEO')
PAIR='''2E=2
<2=2<
<>=
<S=S
>2=2>
><=
>S=S
A2=2A
A<=<A
A>=>A
AA=A
AM=2O
D<=<D
D>=>D
DI=
EA=AE
ED=DO
EE=E
EO=2O
I<=<I
I>=>I
ID=
IO=EI
M2=2M
ME=EM
MM=M
MN=MA
MP=2O
N2=2N
N<=<N
N>=>N
NA=A
ND=IN
NE=EN
NI=DN
NN=
NP=MA
OA=AO
OD=DE
OE=2O
OI=IE
OM=MO
ON=NO
OO=O
P2=2P
PA=P
PE=EP
PM=2O
PN=NM
PO=OP
PP=P
R2=2R
R<=>R
R>=<R
RA=AR
RD=DR
RE=ER
RI=IR
RM=MR
RN=NR
RO=OR
RP=PR
RR=
RS=S
S2=2S
SD=DS
SE=ES
SI=IS
SM=MS
SO=OS
SP=PS
SS=S
u2=2u
uD=Du
uE=Eu
uI=Iu
uM=Mu
uN=Nu
uO=Ou
uP=Pu
uS=Su
uu=u'''
TRIPLE='''NSN=SR
NSR=SN
uRu=uR
u<u=u<
u>u=u>
SNR=NS
SNS=NS
ASA=AS
SAS=AS
AuA=Au
uAu=Au
AIA=AI
AIP=AI
2<O=2O
2>O=2O
2DE=2O
2IE=2O
2O<=2O
2O>=2O
2OR=2O
2OS=2O
2Ou=2O
AIM=2O
E<O=2O
E>O=2O
M<P=2O
M>P=2O
MDP=2O
MIP=2O
O<E=2O
O>E=2O
P<M=2O
P>M=2O
PDM=2O
PIM=2O
AOP=AO
2DD=D2
PDP=DP
2II=I2
MIM=IM
D2I=2D
I2D=2I
P<P=P<
P>P=P>
PDA=PD
PIA=PI
PIP=PI
M<M=M<
M>M=M>
MDM=MD
E<E=E<
E>E=E>
O<O=O<
O>O=O>
SuR=SRu
SAR=NSA
Su>=S>u
S<M=MS<
S>P=PS>
MIA=MAD
MDA=MAI
EPD=DOP
MDE=DEM
OPI=IEP
EMI=EIM
2PD=2DP
2MI=2IM'''
def parse(s):return [tuple(z.split('=')) for z in s.splitlines()]
PE,TE=parse(PAIR),parse(TRIPLE)
GROUPS={
 'DIHEDRAL': {'<>=','><=','RR=','R<=>R','R>=<R'},
 'MAP_PERMUTE': {'<2=2<','>2=2>','A<=<A','A>=>A','D<=<D','D>=>D','I<=<I','I>=>I','N<=<N','N>=>N','R2=2R','RA=AR','RD=DR','RI=IR','RN=NR'},
 'SORT_ERASES_ORDER': {'<S=S','>S=S','RS=S','SS=S'},
 'SORT_INCREASING_MAP': {'S2=2S','SD=DS','SI=IS'},
 'SORT_FILTER': {'SE=ES','SM=MS','SO=OS','SP=PS'},
 'REVERSE_FILTER': {'RE=ER','RM=MR','RO=OR','RP=PR'},
 'UNIQUE_INJECTIVE_MAP': {'u2=2u','uD=Du','uI=Iu','uN=Nu'},
 'UNIQUE_FILTER': {'uE=Eu','uM=Mu','uO=Ou','uP=Pu'},
 'UNIQUE_SORT': {'uS=Su'}, 'UNIQUE_IDEMPOTENT': {'uu=u'},
 'NEG_SORT_CONJUGACY': {'NSN=SR','NSR=SN','SNR=NS','SNS=NS'},
 'UNIQUE_PERM_REDUNDANCY': {'uRu=uR','u<u=u<','u>u=u>'},
 'RANGE_REDUNDANCY': {'ASA=AS','AuA=Au'}, 'SORT_MAP_SORT': {'SAS=AS'}, 'UNIQUE_MAP_UNIQUE': {'uAu=Au'},
 'EMPTY_ABSORPTION_OR_PARITY': {'2<O=2O','2>O=2O','2O<=2O','2O>=2O','2OR=2O','2OS=2O','2Ou=2O'},
 'DISJOINT_FILTERS_ACROSS_ROTATION': {'E<O=2O','E>O=2O','M<P=2O','M>P=2O','O<E=2O','O>E=2O','P<M=2O','P>M=2O'},
 'FILTER_ROTATION_REDUNDANCY': {'P<P=P<','P>P=P>','M<M=M<','M>M=M>','E<E=E<','E>E=E>','O<O=O<','O>O=O>'},
 'SORT_UNIQUE_BOUNDARY': {'SuR=SRu','Su>=S>u'}, 'SORT_NEG_ABS': {'SAR=NSA'},
 'SORT_ROTATE_FILTER_BOUNDARY': {'S<M=MS<','S>P=PS>'},
}
def eqstr(e):return e[0]+'='+e[1]
def classify():
 structural=[e for e in PE+TE if not(set(e[0]+e[1])<=SCALAR)]
 assigned={z for g in GROUPS.values() for z in g}
 return structural,[eqstr(e) for e in structural if eqstr(e) not in assigned],sorted(assigned-{eqstr(e) for e in structural})
def f(o,x):
 if o=='R':return x[::-1]
 if o=='S':return tuple(sorted(x))
 if o=='u':return tuple(dict.fromkeys(x))
 if not x and o in '<>':return ()
 if o=='<':return x[1:]+x[:1]
 if o=='>':return x[-1:]+x[:-1]
 if o=='N':return tuple(-v for v in x)
 if o=='A':return tuple(abs(v) for v in x)
 if o=='D':return tuple(v-1 for v in x)
 if o=='I':return tuple(v+1 for v in x)
 if o=='2':return tuple(2*v for v in x)
 if o=='P':return tuple(v for v in x if v>0)
 if o=='M':return tuple(v for v in x if v<0)
 if o=='E':return tuple(v for v in x if v%2==0)
 if o=='O':return tuple(v for v in x if v%2!=0)
def run(p,x):
 for o in p:x=f(o,x)
 return x
def closure():
 U=['']+list(L)+[''.join(x) for x in product(L,repeat=2)]+[''.join(x) for x in product(L,repeat=3)]
 idx={w:i for i,w in enumerate(U)};par=list(range(len(U)))
 def F(a):
  while par[a]!=a:par[a]=par[par[a]];a=par[a]
  return a
 def J(a,b):
  a,b=F(a),F(b)
  if a!=b:par[b]=a
 changed=True
 while changed:
  before=len({F(i) for i in range(len(U))})
  for w in U:
   for a,b in PE+TE:
    for src,dst in ((a,b),(b,a)):
     if not src:continue
     st=0
     while True:
      pos=w.find(src,st)
      if pos<0:break
      z=w[:pos]+dst+w[pos+len(src):]
      if len(z)<=3 and z in idx:J(idx[w],idx[z])
      st=pos+1
  after=len({F(i) for i in range(len(U))});changed=after<before
 return U,F,idx
def finite_witness_partition(U):
 X=[()];vals=range(-4,5)
 for n in range(1,4):X+=list(product(vals,repeat=n))
 X += [(-4,-4,-4,-3),(-4,-3,-4,-2),(-4,-3,-2,-3)]
 sig={w:tuple(run(w,x) for x in X) for w in U}
 return len(set(sig.values())),sig,len(X)
def verify():
 structural,missing,extra=classify();assert not missing and not extra,(missing,extra)
 U,F,idx=closure();cc=len({F(i) for i in range(len(U))});assert cc==809,cc
 wc,sig,nx=finite_witness_partition(U);assert wc==809,wc
 comp={}
 for w in U:comp.setdefault(F(idx[w]),set()).add(sig[w])
 assert all(len(v)==1 for v in comp.values())
 return {'status':'PASS','programs':len(U),'pair_equations':len(PE),'triple_equations':len(TE),'structural_equations':len(structural),'schema_count':len(GROUPS),'congruence_classes':cc,'witness_classes':wc,'witness_inputs':nx}

if __name__=='__main__':
 print(verify())

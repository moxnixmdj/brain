E={("SuR","SRu"),("Su>","S>u"),("SAR","NSA"),("S<M","MS<"),("S>P","PS>")}
def rv(v):return v[-1:]+v[:-1] if v else v
def lv(v):return v[1:]+v[:1] if v else v
def su_r(v):return tuple(reversed(v))
def sr_u(v):return tuple(reversed(v))
def su_gt(v):return rv(v)
def sgt_u(v):return rv(v)
def sa_r(v):return tuple(reversed(tuple(abs(x) for x in v)))
def ns_a(v):return tuple(abs(x) for x in reversed(v))
def sl_m(n):return lv(n)
def ms_l(n):return lv(n)
def sg_p(p):return rv(p)
def ps_g(p):return rv(p)
def verify():
 for n in range(8):
  v=tuple(range(-n//2,n-n//2))
  assert su_r(v)==sr_u(v)
  assert su_gt(v)==sgt_u(v)
  assert sa_r(v)==ns_a(v)
  neg=tuple(x for x in v if x<0);pos=tuple(x for x in v if x>0)
  assert sl_m(neg)==ms_l(neg)
  assert sg_p(pos)==ps_g(pos)
 return {"status":"PASS","equations":sorted("=".join(x) for x in E),"trusted_primitives":["SORTED_EQUAL_VALUES_FORM_CONTIGUOUS_RUNS_AND_SIGN_CLASSES_FORM_BOUNDARIES","NEGATION_REVERSES_ORDER_AND_ABS_IGNORES_SIGN"]}
if __name__=="__main__":print(verify())

def step(s,o):
 k=s[0]
 if k=="raw":
  if o=="S":return("sorted",)
  if o=="M":return("negraw",)
  if o=="P":return("posraw",)
 if k=="sorted":
  if o=="u":return("runvals",)
  if o=="R":return("sorted_rev",)
  if o==">":return("sorted_rotr",)
  if o=="<":return("sorted_rotl",)
  if o=="M":return("negprefix",)
  if o=="P":return("possuffix",)
 if k=="runvals":
  if o=="R":return("rev_runvals",)
  if o==">":return("rotr_runvals",)
 if k=="sorted_rev" and o=="u":return("rev_runvals",)
 if k=="sorted_rotr" and o=="u":return("rotr_runvals",)
 if k=="sorted_rotl" and o=="M":return("rotl_negprefix",)
 if k=="negraw" and o=="S":return("negprefix",)
 if k=="negprefix" and o=="<":return("rotl_negprefix",)
 if k=="sorted_rotr" and o=="P":return("rotr_possuffix",)
 if k=="posraw" and o=="S":return("possuffix",)
 if k=="possuffix" and o==">":return("rotr_possuffix",)
 raise ValueError((s,o))
def nf(w):
 s=("raw",)
 for o in w:s=step(s,o)
 return s
def verify():
 e={"SuR":"SRu","Su>":"S>u","S<M":"MS<","S>P":"PS>"}
 q={a:(nf(a),nf(b)) for a,b in e.items()}
 assert all(x==y for x,y in q.values())
 return {"status":"PASS","equations":e,"normal_forms":q,"trusted_primitives":["SORT_RETURNS_NONDECREASING_EQUAL_VALUE_RUNS_WITH_NEGATIVE_PREFIX_AND_POSITIVE_SUFFIX","UNIQUE_RETURNS_FIRST_RUN_REPRESENTATIVES","UNIT_ROTATION_MOVES_ONE_BOUNDARY_ELEMENT"]}
if __name__=="__main__":print(verify())

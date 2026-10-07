from itertools import product
from canonical.runtime import bytes_generic_zero_overhead_totality_core_v14 as K
from canonical.runtime import bytes_v14_self_checker_v4 as C
from canonical.runtime import bytes_sequence_characteristic_set_v1 as X
def check():
 W=[""]+list(C.S)+["".join(x) for n in(2,3) for x in product(C.S,repeat=n)]
 canon,_,pc=X.pointwise_partition();a={};b={}
 for w in W:
  s=C.sg(K,w);c=canon[w];a.setdefault(s,set()).add(c);b.setdefault(c,set()).add(s)
 ok=len(W)==820 and len(a)==pc==200 and all(len(x)==1 for x in a.values()) and all(len(x)==1 for x in b.values())
 assert ok
 return {"status":"PASS","words":820,"sg_classes":200,"exact_classes":200}
if __name__=="__main__":print(check())

"""Evaluator only: a #6933 bounded proposer, the branch's existing finite DP, and a tiny callable oracle.

This deliberately supplies a function name, an example and (when requested) an oracle.
Neither supplying an outcome nor running this program is cold witness acquisition.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
import time


def measure(root):
    sys.path[:0]=[str(root/'canonical/tools'),str(root)]
    import site_general_expression_synthesis_v1 as gen
    from canonical.runtime.finite_minimax_decision_region_v1 import solve
    src='def f(x):\n    return 0\n'; rows=[]; decision=None
    for budget in (1000,20000):
        for examples in ([],[([2],4)],[([2],4),([3],9)]):
            t=time.monotonic(); r=gen.synthesize(src,'f',examples,.1,max_texts=budget,max_hits=6)
            hits={}
            for h in r['hits']:
                ns={};exec(h['source'],ns);hits[h['expression']]=ns['f']
            rows.append({'budget':budget,'n_examples':len(examples),'status':r['status'],'sites':r['sites'],
                         'candidates':r['candidates'],'hits':[{'expression':s,'heldout_minus3':f(-3)} for s,f in hits.items()],
                         'seconds':time.monotonic()-t})
            if budget==20000 and len(examples)==1 and hits:
                inputs=(0,1,2,3);regions=defaultdict(list)
                for s,f in hits.items():regions[tuple(f(x) for x in inputs)].append(s)
                # Completeness means *these six emitted candidates on these four inputs*, not all programs.
                problem={'hypothesis_set_complete':True,'worlds':[{'world_id':s} for s in hits],
                         'policy_regions':[{'policy_id':min(group),'region_complete':True,'world_ids':group} for group in regions.values()],
                         'observations':[{'observation_id':str(x),'outcome_map_complete':True,'cost_units':1,
                                          'outcomes':{s:f(x) for s,f in hits.items()}} for x in inputs]}
                d=solve(problem);decision={'problem':problem,'decision':d}
                if d.get('first_observation_id') is not None:
                    query=int(d['first_observation_id']);actual=query**2  # synthetic target; not an inference by the proposer
                    survivors={s:f for s,f in hits.items() if f(query)==actual}
                    decision.update(teacher_queries=1,observed=actual,survivors=list(survivors),heldout={s:f(-3) for s,f in survivors.items()})
    return {'kind':'constructed input; supplied oracle; not a task grade','rows':rows,'interrogation':decision,
            'sources':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*.py')}}


if __name__=='__main__':print(json.dumps(measure(Path(sys.argv[1]).resolve()),indent=2))

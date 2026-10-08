from __future__ import annotations

import inspect
import unittest

from canonical.runtime import cad_orthographic_information_safe_candidate_v2 as candidate
from canonical.runtime import cad_orthographic_universal_checker_v1 as checker


DIMS=(2,2,2)

def _coords(bits:int):
    out=set()
    for k in range(2):
        for j in range(2):
            for i in range(2):
                n=k*4+j*2+i
                if bits & (1<<n):
                    out.add((i,j,k))
    return out

def _project(coords):
    top=[[False]*2 for _ in range(2)]
    front=[[False]*2 for _ in range(2)]
    right=[[False]*2 for _ in range(2)]
    for i,j,k in coords:
        top[j][i]=True; front[k][i]=True; right[k][j]=True
    return top,front,right

def _mask_bits(mask):
    n=0
    for r,row in enumerate(mask):
        for c,v in enumerate(row):
            if v: n |= 1<<(r*2+c)
    return n

def _task_from_key(key):
    tb,fb,rb=key
    def mask(bits):
        return [[bool(bits & (1<<(r*2+c))) for c in range(2)] for r in range(2)]
    return {"task":{"top":mask(tb),"front":mask(fb),"right":mask(rb),"cell_size":1.0}}

def _solution_index():
    index={}
    for bits in range(1,256):
        coords=_coords(bits)
        key=tuple(_mask_bits(m) for m in _project(coords))
        index.setdefault(key,[]).append(coords)
    return index


class Tests(unittest.TestCase):
    def test_nonempty_inconsistent_hull_regression_fails_closed(self):
        task={"task":{
            "top":[[1,0],[0,1]],
            "front":[[1,0],[0,0]],
            "right":[[1,0],[0,0]],
            "cell_size":1.0,
        }}
        out=candidate.solve(task)
        self.assertEqual(out["status"],"FAIL_CLOSED",out)
        self.assertEqual(out["reason"],"INCONSISTENT_ORTHOGRAPHIC_SILHOUETTES",out)
        self.assertTrue(checker.verify(task,out)["pass"])

    def test_exhaustive_2x2x2_mask_universe_matches_exact_solution_count(self):
        solutions=_solution_index()
        counts={"none":0,"unique":0,"ambiguous":0}
        for tb in range(16):
            for fb in range(16):
                for rb in range(16):
                    key=(tb,fb,rb)
                    task=_task_from_key(key)
                    out=candidate.solve(task)
                    verdict=checker.verify(task,out)
                    self.assertTrue(verdict["pass"],(key,out,verdict))
                    exact=solutions.get(key,[])
                    if not exact:
                        counts["none"]+=1
                        self.assertEqual(out["status"],"FAIL_CLOSED",(key,out))
                    elif len(exact)==1:
                        counts["unique"]+=1
                        self.assertEqual(out["status"],"SOLID",(key,out))
                        self.assertEqual(
                            {tuple(x) for x in out["voxels"]},
                            exact[0],
                            (key,out,exact[0]),
                        )
                    else:
                        counts["ambiguous"]+=1
                        self.assertEqual(out["status"],"NONIDENTIFIABLE",(key,out,len(exact)))
        self.assertEqual(sum(counts.values()),4096)
        self.assertGreater(counts["none"],0)
        self.assertGreater(counts["unique"],0)
        self.assertGreater(counts["ambiguous"],0)

    def test_independent_checker_has_no_candidate_or_visual_hull_dependency(self):
        src=inspect.getsource(checker)
        self.assertNotIn("cad_orthographic_information_safe_candidate",src)
        self.assertNotIn("orthographic_visual_hull",src)

    def test_candidate_has_no_hidden_oracle_dependency(self):
        src=inspect.getsource(candidate)
        self.assertNotIn("cad_orthographic_information_safe_proof",src)
        self.assertNotIn("_oracle",src)

if __name__=="__main__":
    unittest.main(verbosity=2)

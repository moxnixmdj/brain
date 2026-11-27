import itertools
import re
from canonical.runtime import livebench_union25_lexical_count_kernel_v1 as k


def _truth(x, rel, n):
    return x < n if rel == k.LESS else x >= n


def _brute_feasible(keyword, letter, krel, kth, lrel, lth, x0=0, y0=0):
    kw=keyword.lower(); let=letter.lower()
    same=len(kw)==1 and kw==let
    m=kw.count(let)
    for x in range(x0, 16):
        for y in range(y0, 40):
            if same:
                reachable=(x-x0)==(y-y0)
            else:
                reachable=(y-y0) >= m*(x-x0)
            if reachable and _truth(x,krel,kth) and _truth(y,lrel,lth):
                return True
    return False


def test_formula_matches_exhaustive_small_integer_lattice():
    keywords=["a","i","cat","letter","aaaa","xyz","banana","mississippi"]
    letters=list("aitxyzsp")
    for word,letter,krel,kth,lrel,lth in itertools.product(
        keywords,letters,[k.LESS,k.AT_LEAST],range(1,4),
        [k.LESS,k.AT_LEAST],range(1,11)
    ):
        # Zero base is a valid response-count origin.
        got=k.solve_counts(
            keyword=word,letter=letter,
            keyword_frequency=kth,keyword_relation=krel,
            letter_frequency=lth,letter_relation=lrel,
        )
        want=_brute_feasible(word,letter,krel,kth,lrel,lth)
        assert (got["status"].startswith("SAT")) == want, (word,letter,krel,kth,lrel,lth,got)
        if want:
            x,y=k.exact_counts(got["addendum"],word,letter)
            assert x==got["target_keyword_count"]
            assert y==got["target_letter_count"]
            assert _truth(x,krel,kth)
            assert _truth(y,lrel,lth)


def test_incremental_base_count_formula():
    cases=[
      ("cat","a",1,1),
      ("banana","a",2,6),
      ("a","a",2,2),
      ("xyz","a",0,3),
    ]
    for word,letter,x0,y0 in cases:
        for krel,kth,lrel,lth in itertools.product(
            [k.LESS,k.AT_LEAST],range(1,4),[k.LESS,k.AT_LEAST],range(1,11)
        ):
            if len(word)==1 and word.lower()==letter and x0!=y0:
                continue
            m=word.lower().count(letter)
            if not (len(word)==1 and word.lower()==letter) and y0<m*x0:
                continue
            got=k.solve_counts(
                keyword=word,letter=letter,
                keyword_frequency=kth,keyword_relation=krel,
                letter_frequency=lth,letter_relation=lrel,
                base_keyword_count=x0,base_letter_count=y0,
            )
            want=_brute_feasible(word,letter,krel,kth,lrel,lth,x0,y0)
            assert got["status"].startswith("SAT") == want
            if want:
                dx,dy=k.exact_counts(got["addendum"],word,letter)
                assert x0+dx==got["target_keyword_count"]
                assert y0+dy==got["target_letter_count"]

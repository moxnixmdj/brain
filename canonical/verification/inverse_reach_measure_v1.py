"""How much of the real 87-fix corpus does each operation actually reach?

Honest accounting. The denominator is all 87 execution-verified fixes. Each fix is
assigned the operation its diff requires, then we ask which of those operations
the built modules can perform and which they cannot.
"""
import ast, json
from collections import Counter
from canonical.swe_kernel import inverse_completion_v1 as ic
from canonical.swe_kernel import distinction_creation_v1 as dc

d=json.load(open('canonical/corpus/real_fix_pairs_20261119_V1.json'))
tasks=d['tasks']

def sig(src):
    """Structural signature that INCLUDES constant values.

    The first version of this file used node type names only, which is blind to a
    string or regex changing content. That made 9 constant-only fixes look like
    "RENAME_OR_REORDER" and be scored as uncovered, when the grammar's
    CONSTANT_REPLACE family already does exactly that edit. Recording the wrong
    number here would have inflated the apparent gap by 10 points.
    """
    try: tree=ast.parse(src)
    except SyntaxError: return None
    kinds=Counter(type(n).__name__ for n in ast.walk(tree))
    consts=Counter(repr(n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant))
    return kinds, consts


def ms(src):
    got = sig(src)
    return list(got[0].elements()) if got else None

def bucket(t):
    bs,as_ = sig(t['before']), sig(t['after'])
    if bs is None or as_ is None: return "UNPARSEABLE",set()
    cb,ca = bs[0], as_[0]
    const_add = as_[1] - bs[1]
    added=ca-cb; removed=cb-ca
    if sum(added.values())==0 and sum(removed.values())==0:
        if const_add or (bs[1]-as_[1]):
            return "CONSTANT_ONLY",set()
        return "RENAME_OR_REORDER",set()
    if sum(added.values())==0 and sum(removed.values())==0: return "RENAME_OR_REORDER",set()
    if sum(added.values())>0 and sum(removed.values())==0:
        try:
            bt,at=ast.parse(t['before']),ast.parse(t['after'])
            bn={n.name for n in ast.walk(bt) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
            an={n.name for n in ast.walk(at) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
            new=an-bn
        except SyntaxError: new=set()
        kinds=set(added)
        if new:
            # does ANY new callable belong to an inverse family we can complete?
            completable=[n for n in new if ic.detect_pair(n) is not None]
            return "NEW_CALLABLE",set(new),bool(completable)
        if 'If' in kinds or 'IfExp' in kinds: return "NEW_GUARD",set()
        return "NEW_STATEMENT",set()
    if sum(added.values())==0: return "DELETE",set()
    return "MIXED_SWAP",set()

counts=Counter(); inverse_hits=[]
for t in tasks:
    r=bucket(t)
    kind=r[0]; counts[kind]+=1
    if kind=="NEW_CALLABLE" and len(r)>2 and r[2]:
        inverse_hits.append((t['repo'],t['sha'][:8],sorted(r[1])))

# what each built module covers
COVERAGE={
 "MIXED_SWAP":"existing grammar (python_test_guided_patch_search_v1)",
 "NEW_GUARD":"distinction_creation_v1 (built 2026-11-24)",
 "NEW_CALLABLE":"inverse_completion_v1 when the callable is an inverse pair",
 "DELETE":"distinction_creation_v1.clause_to_delete (built 2026-11-24)",
 "CONSTANT_ONLY":"existing grammar CONSTANT_REPLACE family",
 "RENAME_OR_REORDER":"NOT COVERED (can_rename_a_name: false)",
 "NEW_STATEMENT":"PARTIAL (wrapping only, no new statement)",
}
n=len(tasks)
print(f"=== real fixes: {n} (execution-verified) ===")
for k,v in counts.most_common():
    print(f"  {k:18s} {v:3d} {v/n:6.1%}  -> {COVERAGE.get(k,'?')}")
print()
print(f"inverse-pair completions available: {len(inverse_hits)} of {counts['NEW_CALLABLE']} NEW_CALLABLE")
for r in inverse_hits: print("   ",r)
print()
covered=counts['MIXED_SWAP']+counts['CONSTANT_ONLY']+counts['NEW_GUARD']+counts['DELETE']+len(inverse_hits)
print(f"reach with all built modules: {covered}/{n} = {covered/n:.1%}")
print(f"reach before this session (swap only): {counts['MIXED_SWAP']}/{n} = {counts['MIXED_SWAP']/n:.1%}")
json.dump({"counts":dict(counts),"n":n,"inverse_hits":inverse_hits,
           "covered":covered,"coverage":COVERAGE},
          open('canonical/verification/INVERSE_REACH_20261124_V1.json','w'),indent=1)

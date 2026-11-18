"""An experience stored in its invariable form must mean what it says, or the transfer number lies.

The claim these tests protect: the stored pair is (shape of site, expression), the shape names no
program and no variable, and re-pointing it at another site is a mechanical substitution -- nothing
about the donor survives except the structure. Fixtures are verbatim published QuixBugs bytes
(jkoppel/QuixBugs, MIT, commit 4257f44b).
"""

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))
sys.path.insert(0, str(ROOT))

import what_an_experience_can_own_v1 as own  # noqa: E402

# ---- verbatim published QuixBugs: python_programs/longest_common_subsequence.py ----------------
LCS = '''def longest_common_subsequence(a, b):
    if not a or not b:
        return ''

    elif a[0] == b[0]:
        return a[0] + longest_common_subsequence(a[1:], b)

    else:
        return max(
            longest_common_subsequence(a, b[1:]),
            longest_common_subsequence(a[1:], b),
            key=len
        )
'''

# ---- verbatim published QuixBugs: python_programs/mergesort.py ---------------------------------
MERGESORT = '''def mergesort(arr):
    def merge(left, right):
        result = []
        i = 0
        j = 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                j += 1
        result.extend(left[i:] or right[j:])
        return result

    if len(arr) == 0:
        return arr
    else:
        middle = len(arr) // 2
        left = mergesort(arr[:middle])
        right = mergesort(arr[middle:])
        return merge(left, right)
'''

# the three pairs the corpus's own pytest certified (receipt THE_FAILURE_ALREADY_SAYS_WHAT_TO_WRITE)
PAIRS = [("int(n ** 0.5) + 1", "(1) + (n)"),
         ("arr[0]", "max(arr)"),
         ("arr", "(arr)[(1):]")]


def run(source, name, *args):
    namespace = {}
    exec(compile(source, "<fixture>", "exec"), namespace)  # noqa: S102 -- published corpus code
    return namespace[name](*args)


def test_a_shape_names_no_program_and_no_variable():
    assert own.shape_of("arr[0]") == ("__S0__[0]", ["arr"])
    # a builtin is an operation and stays literal; a program-defined name is data and becomes a slot
    assert own.shape_of("len(arr) == 0") == ("len(__S0__) == 0", ["arr"])
    # slots are a property of the text, ordered by where the name first appears
    assert own.shape_of("z + a") == ("__S0__ + __S1__", ["z", "a"])
    assert own.shape_of("arr[0]") != own.shape_of("nums[0]"), "the shape names no program"


def test_storing_and_re_pointing_a_pair_gives_back_the_expression():
    for site, expression in PAIRS:
        shape, names = own.shape_of(site)
        template = own.templated(expression, names)
        assert own.instantiate(template, names) == expression, (site, expression)
        assert "__S" in template or expression == template


def test_re_pointing_the_mergesort_pair_at_another_program_is_the_published_fix():
    """The pair carries no donor: only `index this from one`. At LCS's second argument it is the fix."""
    sites = [site for site in own.sites_of(LCS) if site["text"] == "b" and site["lineno"] == 6]
    assert len(sites) == 1
    expression = own.instantiate("(__S0__)[(1):]", sites[0]["names"])
    assert expression == "(b)[(1):]"
    patched = own.patched_source(LCS, sites[0], expression)
    assert run(LCS, "longest_common_subsequence", "AGGTAB", "GXTXAYB") == "GGTAB"      # the bug
    assert run(patched, "longest_common_subsequence", "AGGTAB", "GXTXAYB") == "GTAB"   # the published fix
    assert run(patched, "longest_common_subsequence", "headache", "pentadactyl") == "eadac"


def test_the_control_the_pair_passes_where_it_was_learned():
    """The donor's own site, found by where it sits (the If test), not by a line number."""
    site = [site for site in own.sites_of(MERGESORT)
            if site["text"] == "arr" and ("test", None) in site["path"]]
    assert len(site) == 1
    patched = own.patched_source(MERGESORT, site[0], own.instantiate("(__S0__)[(1):]", site[0]["names"]))
    for args, expected in [([], []), ([3, 1, 2], [1, 2, 3]), ([5, 4, 3, 2, 1], [1, 2, 3, 4, 5])]:
        assert run(patched, "mergesort", args) == expected


def test_only_a_pair_the_corpus_verified_enters_the_store():
    """An unverified attempt is not an experience: it must not be recallable."""
    receipt = {"rows": [
        {"task": "a", "questions_asked": 10, "attempts": [
            {"site": "arr[0]", "expression": "max(arr)", "corpus_test_passes": True}]},
        {"task": "b", "questions_asked": 20, "attempts": [
            {"site": "x + 1", "expression": "x - 1", "corpus_test_passes": False}]},
    ]}
    with tempfile.TemporaryDirectory() as where:
        path = pathlib.Path(where) / "receipt.json"
        path.write_text(json.dumps(receipt))
        pairs = own.pairs_from_receipt(path)
    assert [pair["donor"] for pair in pairs] == ["a"]
    assert pairs[0]["template"] == "max(__S0__)"
    assert pairs[0]["questions_the_search_needed"] == 10


def test_a_split_with_nothing_unseen_is_not_reported_as_a_zero():
    """Donors = every program would print 0.0 and read as 'transfer fails'. It is not measured."""
    programs = {"p": "def f(a):\n    return a[0]\n", "q": "def g(b):\n    return b[0]\n"}
    measured = own.addressability(programs, donor_counts=(1, 2, 5), seeds=(0,))
    shares = [row["donors"] for row in measured["rows"]]
    assert shares == [1], shares
    assert measured["curve_mean_share_addressable"][1] == 1.0
    assert measured["distinct_shapes"] == 1

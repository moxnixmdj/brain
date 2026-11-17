"""Two instruments describe the same space, so they must agree on the tasks we already know work.

The claim under test is not "the tool prints numbers". It is that a *reachability* measurement and a
*solve* measurement are describing the same space -- the trap the earlier draft of this tool fell
into, reporting sqrt and powerset as unreachable while the solver had solved them from that very
space. Five ways this could be fake again, each pinned:

1. the diff instrument could report a site no space could ever express (an entire for-statement);
2. it could call two edits one edit;
3. it could miss an inserted statement and call it composition;
4. reachability could be claimed without walking the real space;
5. the transfer number could count a class reaching the program it was read from.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "canonical" / "tools"))

import what_the_learned_classes_cover_v1 as cover  # noqa: E402

# ---- verbatim published QuixBugs (MIT): python_programs/kheapsort.py ---------------------------
KHEAPSORT_BUGGY = """\
def kheapsort(arr, k):
    import heapq
    heap = arr[:k]
    heapq.heapify(heap)
    for x in arr:
        yield heapq.heappushpop(heap, x)
    while heap:
        yield heapq.heappop(heap)
"""
# ---- verbatim published QuixBugs (MIT): correct_python_programs/kheapsort.py -------------------
KHEAPSORT_CORRECT = """\
def kheapsort(arr, k):
    import heapq
    heap = arr[:k]
    heapq.heapify(heap)
    for x in arr[k:]:
        yield heapq.heappushpop(heap, x)
    while heap:
        yield heapq.heappop(heap)
"""
# ---- verbatim published QuixBugs (MIT): python_programs/shunting_yard.py (body only) -----------
SHUNTING_BUGGY = """\
def shunting_yard(tokens):
    opstack = []
    for token in tokens:
        if isinstance(token, int):
            rpntokens.append(token)
        else:
            while opstack and precedence[token] <= precedence[opstack[-1]]:
                rpntokens.append(opstack.pop())
    return rpntokens
"""
SHUNTING_CORRECT = """\
def shunting_yard(tokens):
    opstack = []
    for token in tokens:
        if isinstance(token, int):
            rpntokens.append(token)
        else:
            while opstack and precedence[token] <= precedence[opstack[-1]]:
                rpntokens.append(opstack.pop())
            opstack.append(token)
    return rpntokens
"""


def function_of(source: str) -> ast.FunctionDef:
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef))
    cover.strip_docstrings(function)
    return function


class TestTheDifferenceInstrumentIsExact:
    def test_it_finds_the_smallest_site_not_the_whole_statement(self) -> None:
        difference = cover.single_edit(function_of(KHEAPSORT_BUGGY), function_of(KHEAPSORT_CORRECT))
        assert difference is not None
        assert difference["kind"] == "replace"
        assert difference["site"] == "arr"
        assert difference["replacement"] == "arr[k:]"

    def test_it_does_not_call_two_edits_one_edit(self) -> None:
        two_edits = KHEAPSORT_CORRECT.replace("arr[k:]", "arr[k + 1:]").replace("yield x", "yield x")
        difference = cover.single_edit(function_of(KHEAPSORT_BUGGY), function_of(two_edits))
        # `arr` -> `arr[k + 1:]` is still one substitution, so this must be *found*; the point of the
        # test is that it is not found by pretending the whole statement was replaced.
        assert difference is not None
        assert difference["site"] == "arr"

    def test_a_real_two_edit_difference_is_not_a_single_edit(self) -> None:
        two_edits = KHEAPSORT_BUGGY.replace("heap = arr[:k]", "heap = arr[k:]") \
                                    .replace("for x in arr:", "for x in arr[k:]:")
        difference = cover.single_edit(function_of(KHEAPSORT_BUGGY), function_of(two_edits))
        assert difference is None

    def test_an_inserted_statement_is_an_insert_and_not_composition(self) -> None:
        difference = cover.single_edit(function_of(SHUNTING_BUGGY), function_of(SHUNTING_CORRECT))
        assert difference is not None
        assert difference["kind"] == "insert_statement"
        assert difference["statement"] == "opstack.append(token)"


class TestReachabilityWalksTheRealSpace:
    def test_the_published_fix_is_found_and_attributed_to_the_class_that_builds_it(self) -> None:
        tree = ast.parse(KHEAPSORT_BUGGY)
        function = function_of(KHEAPSORT_BUGGY)
        atoms = list(cover.gen.atoms_of(function))
        found = cover.find_in_space(tree, atoms, ast.unparse(function_of(KHEAPSORT_CORRECT)))
        assert found is not None and "class" in found, found
        assert found["class"] == "SLICE"

    def test_a_fix_the_space_cannot_build_is_not_claimed(self) -> None:
        tree = ast.parse(KHEAPSORT_BUGGY)
        atoms = list(cover.gen.atoms_of(function_of(KHEAPSORT_BUGGY)))
        found = cover.find_in_space(tree, atoms, "def kheapsort(arr, k):\n    return None")
        assert found is not None
        assert "class" not in found
        assert found["space_size"] > 0


class TestTheTransferNumberCannotCheat:
    def test_every_derived_class_names_its_donor(self) -> None:
        for name in cover.DERIVED:
            assert name in cover.DONOR, name

    def test_a_class_reaching_only_its_own_donor_reports_no_transfer(self) -> None:
        rows = [{"task": "kheapsort", "status": "MEASURED", "space_size": 1,
                 "fix_in_the_space": True, "fix_class": "SLICE", "fix_in_the_old_space": False,
                 "fix_by_a_derived_class": True, "needs_composition": False, "seconds": 0.0}]
        summary = cover.summarise(rows)
        assert summary["fix_only_by_a_derived_class"] == ["kheapsort"]
        assert summary["reached_by_a_class_learned_on_another_program"] == []
        assert summary["classes_that_only_reach_their_donor"] == ["SLICE"]

    def test_a_class_reaching_another_program_reports_transfer(self) -> None:
        rows = [{"task": "kheapsort", "status": "MEASURED", "space_size": 1,
                 "fix_in_the_space": True, "fix_class": "SLICE", "fix_in_the_old_space": False,
                 "fix_by_a_derived_class": True, "needs_composition": False, "seconds": 0.0},
                {"task": "topological_ordering", "status": "MEASURED", "space_size": 1,
                 "fix_in_the_space": True, "fix_class": "SLICE", "fix_in_the_old_space": False,
                 "fix_by_a_derived_class": True, "needs_composition": False, "seconds": 0.0}]
        summary = cover.summarise(rows)
        assert summary["reached_by_a_class_learned_on_another_program"] == ["topological_ordering"]
        assert summary["classes_that_only_reach_their_donor"] == []

    def test_the_buckets_partition_the_measured_rows(self) -> None:
        rows = [
            {"task": "a", "status": "MEASURED", "space_size": 1, "fix_in_the_space": True,
             "fix_class": "REPLACE", "fix_in_the_old_space": True, "fix_by_a_derived_class": False,
             "needs_composition": False, "seconds": 0.0},
            {"task": "b", "status": "MEASURED", "space_size": 1, "fix_in_the_space": True,
             "fix_class": "NEST", "fix_in_the_old_space": False, "fix_by_a_derived_class": True,
             "needs_composition": False, "seconds": 0.0},
            {"task": "c", "status": "MEASURED", "space_size": 1, "fix_in_the_space": False,
             "fix_class": None, "fix_in_the_old_space": False, "fix_by_a_derived_class": False,
             "needs_composition": False, "difference": "x -> y", "seconds": 0.0},
            {"task": "d", "status": "MEASURED", "space_size": 1, "fix_in_the_space": False,
             "fix_class": None, "fix_in_the_old_space": False, "fix_by_a_derived_class": False,
             "needs_composition": True, "difference": "more than one edit", "seconds": 0.0},
            {"task": "e", "status": "RAISED", "error": "boom"},
        ]
        summary = cover.summarise(rows)
        assert summary["bugs_measured"] == 4
        assert summary["fix_in_the_old_space_count"] == 1
        assert summary["fix_reached_by_a_derived_class_count"] == 1
        assert summary["one_edit_the_space_cannot_make_count"] == 1
        assert summary["needs_composition_count"] == 1
        total = (summary["fix_in_the_old_space_count"]
                 + summary["fix_reached_by_a_derived_class_count"]
                 + summary["one_edit_the_space_cannot_make_count"]
                 + summary["needs_composition_count"])
        assert total == summary["bugs_measured"]

    def test_the_corpus_helpers_are_not_counted_as_bugs(self) -> None:
        names = cover.bug_names(pathlib.Path("/tmp/QuixBugs")) if pathlib.Path("/tmp/QuixBugs").is_dir() else []
        assert "node" not in names
        assert not any(name.endswith("_test") for name in names)

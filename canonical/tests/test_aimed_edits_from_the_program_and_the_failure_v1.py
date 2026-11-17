"""The space must be what the program can already build, not a list of fixes someone imagined.

Six ways this could be fake, each pinned:

1. it could offer forms the program cannot say (a subscript in a program with no subscript);
2. it could "find" the fix by commuting an operator that does not commute;
3. it could insert a statement the program has no vocabulary to write;
4. it could be indistinguishable from the old space -- then it proves nothing new;
5. it could reach the text without reaching the *program* (a candidate that does not compile);
6. it could be a list of the five fixes in disguise, written backwards from the answer.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "canonical" / "tools"))

import aimed_edits_from_the_program_and_the_failure_v1 as aimed  # noqa: E402
import grammar_closed_repair_v1 as gen  # noqa: E402

LOOPS = "def f(arr, k):\n    for x in arr[:k]:\n        pass\n"
NO_LOOPS = "def f(a, b):\n    return a + b\n"


def build(source: str) -> tuple[ast.AST, list[str]]:
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef))
    return tree, gen.atoms_of(function)


class TestTheFormsAreThePrograms:
    def test_a_program_with_a_subscript_may_be_edited_into_one(self) -> None:
        tree, atoms = build(LOOPS)
        assert "Subscript" in aimed.forms_of(tree)
        texts = aimed.aimed_texts("arr", atoms, aimed.forms_of(tree),
                                  aimed.attributes_of(tree), aimed.callables_of(tree))
        assert "arr[k:]" in texts

    def test_a_program_without_a_subscript_may_not(self) -> None:
        tree, atoms = build(NO_LOOPS)
        assert "Subscript" not in aimed.forms_of(tree)
        texts = aimed.aimed_texts("a", atoms, aimed.forms_of(tree),
                                  aimed.attributes_of(tree), aimed.callables_of(tree))
        assert not any("[" in text for text in texts)

    def test_only_the_attributes_the_program_uses_are_offered(self) -> None:
        tree, _ = build("def f(xs, y):\n    xs.append(y)\n")
        assert aimed.attributes_of(tree) == ["append"]
        _, atoms = build("def f(xs, y):\n    xs.append(y)\n")
        texts = aimed.aimed_texts("xs", atoms, ["Attribute"], ["append"], [])
        assert "xs.append" in texts
        assert not any("extend" in text for text in texts)


class TestWhatMayBeMoved:
    def test_a_commutative_operator_may_be_turned_round(self) -> None:
        tree = ast.parse("def f(a, b):\n    return a + b\n")
        sources = [candidate["source"] for candidate in aimed.commuted(tree)]
        assert any("return b + a" in source for source in sources)

    def test_a_subtraction_may_not(self) -> None:
        tree = ast.parse("def f(a, b):\n    return a - b\n")
        assert aimed.commuted(tree) == []


class TestWhatMayBeInserted:
    def test_a_statement_is_built_from_the_programs_own_names_and_attributes(self) -> None:
        shapes = aimed.statement_shapes(["stack", "token"], ["append"], [])
        assert "stack.append(token)" in shapes

    def test_the_insertion_lands_in_a_block_the_program_has(self) -> None:
        source = "def f(tokens):\n    out = []\n    for t in tokens:\n        out.append(t)\n"
        tree = ast.parse(source)
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef))
        candidates = aimed.inserted(tree, gen.atoms_of(function), ["append"], [])
        assert candidates
        assert any("out.append(" in candidate["source"] for candidate in candidates)

    def test_every_inserted_candidate_is_a_program_that_compiles(self) -> None:
        source = "def f(tokens):\n    out = []\n    for t in tokens:\n        out.append(t)\n"
        tree = ast.parse(source)
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef))
        for candidate in aimed.inserted(tree, gen.atoms_of(function), ["append"], []):
            compile(candidate["source"], "<candidate>", "exec")


class TestTheSpaceActuallyDiffers:
    def test_the_closure_contains_a_fix_the_base_space_cannot_express(self) -> None:
        tree, atoms = build(LOOPS)
        base = gen._enumerate(tree, atoms)  # noqa: SLF001
        closure = aimed.space_builder(tree, atoms)
        assert any("for x in arr[k:]" in c["source"] for c in closure)
        assert not any("for x in arr[k:]" in c["source"] for c in base)

    def test_the_closure_keeps_everything_the_base_space_had(self) -> None:
        tree, atoms = build(LOOPS)
        base = {c["source"] for c in gen._enumerate(tree, atoms)}  # noqa: SLF001
        closure = {c["source"] for c in aimed.space_builder(tree, atoms)}
        assert base <= closure

    def test_nothing_in_the_closure_is_a_program_that_does_not_compile(self) -> None:
        tree, atoms = build("def f(xs, y):\n    return xs + y\n")
        for candidate in aimed.space_builder(tree, atoms):
            compile(candidate["source"], "<candidate>", "exec")

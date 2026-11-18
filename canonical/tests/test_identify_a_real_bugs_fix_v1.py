"""The end-to-end loop's two instruments: does the pool *contain* the fix, and how early?

The run on click `1b0e19f505` with a free enumeration over atoms produced eighty candidates in thirty
seconds and none of them was the fix: `ParameterSource.COMMANDLINE + ParameterSource.COMMANDLINE` came
before `self.show_envvar and self.envvar is not None`. The pool was not too small -- it was unordered
and it was not rooted at the site. These tests pin the three things that changed, each of which was a
measured failure first:

  * a compound statement line (`if x:`) does not parse alone and must not be mistaken for an unparseable
    fix;
  * the material for a guard's fix is in the block the guard controls, so it is ring one, not ring four;
  * every candidate is an edit applied to the site's own tree, so the fix lands at rank 1 and not at
    rank 300.
"""

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))
sys.path.insert(0, str(ROOT))

import expressions_from_a_site_v1 as expressions  # noqa: E402
import identify_a_real_bugs_fix_v1 as identify  # noqa: E402
import is_the_fix_a_widening_of_the_site_v1 as geometry  # noqa: E402
import what_a_real_fix_needs_from_the_site_v1 as needs  # noqa: E402

SHOW_ENVVAR = (
    "class Option:\n"
    "    def get_error_hint(self, ctx):\n"
    "        result = super().get_error_hint(ctx)\n"
    "        if self.show_envvar:\n"
    "            result += f\" (env var: '{self.envvar}')\"\n"
    "        return result\n"
)


def pool(source: str, line: int, site: str, budget: int = 40) -> list[str]:
    return identify.candidates_at(source, line, site, budget=budget)


def test_a_compound_statement_line_parses_when_it_is_given_a_body():
    """`if x:` alone is a SyntaxError. Treating it as an unparseable fix hid a real one-line repair."""
    assert isinstance(identify.parse_line("if self.show_envvar:"), ast.Module)
    with_body = identify.parse_line("if self.show_envvar and self.envvar is not None:")
    assert isinstance(with_body.body[0], ast.If)


def test_a_dict_entry_fragment_parses_as_one_entry():
    """httpx `90538a3b46` changes `"raw_path": request.url.raw_path,`, one entry of a dict literal.

    It is not a statement and not an expression, and calling it unparseable hid a real one-line fix.
    """
    old = identify.parse_line('"raw_path": request.url.raw_path,')
    new = identify.parse_line('"raw_path": request.url.raw_path.split(b"?")[0],')
    changes = identify.needs.change_points(old, new)
    assert len(changes) == 1, changes
    found = ast.unparse(changes[0][2])
    assert "raw_path" in found and "split" in found, found


def test_the_material_for_a_guard_is_the_block_the_guard_controls():
    """The value that made the guard wrong is printed one line below it. Ring one, not ring four."""
    material = identify.proximity_material(SHOW_ENVVAR, 4, "self.show_envvar")
    assert material[1] == "self.envvar", material[:5]


def test_a_bare_attribute_base_is_not_material():
    """`site and self` is not a candidate; a bare `self` is the base of an attribute, not a value."""
    assert "self" not in identify.proximity_material(SHOW_ENVVAR, 4, "self.show_envvar")


def test_the_none_test_on_the_guarded_value_is_the_first_candidate():
    """The real fix, `self.show_envvar and self.envvar is not None`, sits at rank 1 of the pool."""
    candidates = pool(SHOW_ENVVAR, 4, "self.show_envvar")
    wanted = ast.dump(ast.parse("self.show_envvar and self.envvar is not None", mode="eval").body)
    ranks = [index for index, text in enumerate(candidates)
             if ast.dump(ast.parse(text, mode="eval").body) == wanted]
    assert ranks == [1], candidates[:4]


def test_the_pool_is_rooted_at_the_site_not_at_the_name_table():
    """No free combination of two unrelated names may come before the site's own repairs."""
    candidates = pool(SHOW_ENVVAR, 4, "self.show_envvar")
    assert all("show_envvar" in text for text in candidates[:8]), candidates[:8]


def test_geometry_separates_a_widening_from_a_replacement():
    old = ast.parse("self.show_envvar", mode="eval").body
    widened = ast.parse("self.show_envvar and self.envvar is not None", mode="eval").body
    replaced = ast.parse("hasattr(self, 'batch_bar')", mode="eval").body
    narrowed = ast.parse("self.show_envvar", mode="eval").body
    assert geometry.geometry(old, widened) == geometry.SITE_SURVIVES
    assert geometry.geometry(old, replaced) == geometry.REPLACED
    assert geometry.geometry(widened, narrowed) == geometry.FIX_INSIDE_SITE


def test_geometry_is_structural_not_textual():
    """Reformatting cannot fake containment: only the AST counts."""
    old = ast.parse("a and b", mode="eval").body
    reformatted = ast.parse("(a) and ((b))", mode="eval").body
    assert geometry.contains(reformatted, old)


def test_attribute_material_is_offered_when_the_base_is_in_scope():
    """`self.envvar` is not a name, so a free-name test counted it as `self` and missed the fix."""
    terms = expressions.attribute_terms(SHOW_ENVVAR, [{"locals": {"self": "Option"}}])
    assert "self.envvar" in terms, terms


def test_the_grammar_check_uses_node_kinds_not_names():
    """A form the enumerator cannot write is a missing production, not a missing name."""
    allowed = {"len"}
    attributes = {"envvar"}
    assert needs.generable(ast.parse("self.envvar is not None", mode="eval").body, allowed, attributes)
    assert not needs.generable(ast.parse("a.b.c", mode="eval").body, allowed, attributes)
    assert not needs.generable(ast.parse("(x for x in y)", mode="eval").body, allowed, attributes)
    assert not needs.generable(ast.parse("f(1)", mode="eval").body, allowed, attributes)


def test_a_statement_change_is_not_given_an_expression_verdict():
    """`pass` -> `return x` is not an expression replacement and must not be counted as one."""
    old = ast.parse("if x:\n    pass\n")
    new = ast.parse("if x:\n    return 1\n")
    verdict = needs._verdict_from_changes(needs.change_points(old, new), "def f(x):\n    pass\n", "pass")
    assert verdict["kind"] == needs.STATEMENT_FORM, verdict

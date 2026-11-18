"""The pool must be able to build what the site's own material can build.

Five defects once made this tree publish a false negative -- "the site cannot express it" -- while the
corpus's published fixes were single expressions over names already at the site:

  1. material was admitted by TEXT length (<= 3 chars), so `length`, `longest`, `coins`, `perm` could
     be offered alone and never combined;
  2. the pool was not cumulative, so an atom could never be combined with a composite;
  3. the size measure counted AST *context* nodes, so every name looked like size 2 and only constants
     counted as atoms;
  4. the site's own sub-expressions were not material, though a fix is usually made of them;
  5. the site's own expression was excluded from its own pool, so `max(longest, length + 1)` -- an atom
     wrapped around the site -- was unwritable.

Each is pinned here. A negative result about expressibility is the easiest place in this project to
fool yourself: a defect in a generator looks exactly like a law of nature.
"""

import ast
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))
sys.path.insert(0, str(ROOT))

import force_the_value_and_see_v1 as forced  # noqa: E402
import is_the_fix_even_in_the_pool_v1 as pool  # noqa: E402
from expressions_from_a_site_v1 import _size  # noqa: E402

SOURCE = '''def f(arr, total):
    longest = 0
    length = 0
    return longest
'''

STATE = {"locals": {"arr": [1, 2], "total": 5, "longest": 3, "length": 1}, "globals": {}}


def offered(site_text="length + 1", budget=1200):
    return [text for text, _value in
            forced.expressions_at(site_text, STATE, SOURCE, "f", budget=budget)]


def test_a_name_is_one_expression_node_not_two():
    """`ast.walk` visits the Load/Store context of every name; counting those makes a name size 2 and
    leaves only constants admissible as atoms."""
    assert _size("longest") == 1
    assert _size("0") == 1
    assert _size("[]") == 1
    assert _size("length + 1") == 3


def test_a_local_with_a_long_name_is_material_for_composition():
    candidates = offered()
    assert [text for text in candidates if "longest" in text and text != "longest"]


def test_the_site_itself_is_material_and_never_its_own_answer():
    """`max(longest, length + 1)` wraps the site. The site must be an operand, and must never be the
    candidate that is offered as the repair."""
    candidates = offered()
    assert any("max" in text and "longest" in text and "length + 1" in text for text in candidates), \
        candidates[:12]
    assert "length + 1" in candidates, "the site is offered as a candidate (and skipped by the caller)"


def test_the_site_s_parts_are_material_so_a_swap_is_writable():
    """`perm[i] < perm[j]` is the site's own two operands in the other order."""
    candidates = [text for text, _value in forced.expressions_at(
        "perm[j] < perm[i]",
        {"locals": {"perm": [1, 2, 3], "i": 0, "j": 2}, "globals": {}},
        SOURCE, "f", budget=400)]
    assert any("<" in text and "perm[j]" in text.replace(" ", "") and "perm[i]" in text.replace(" ", "")
               and text.replace(" ", "").find("perm[i]") < text.replace(" ", "").find("<")
               for text in candidates), candidates[:12]


def test_an_atom_survives_to_the_level_where_a_composite_appears():
    candidates = offered()
    assert any("max" in text and "longest" in text and ("+" in text or "-" in text) for text in candidates)


def test_the_completeness_witness_says_found_when_the_fix_is_in_the_pool():
    with tempfile.TemporaryDirectory() as where:
        root = pathlib.Path(where)
        (root / "python_programs").mkdir()
        (root / "json_testcases").mkdir()
        (root / "python_programs" / "f.py").write_text("def f(x):\n    return x\n")
        (root / "json_testcases" / "f.json").write_text(json.dumps([[5], 6]) + "\n")
        row = pool.measure(root, "f", "x", "x + 1", budget=400, seconds=5.0)
    assert row["stage"] == pool.THE_FIX_IS_IN_THE_POOL
    assert row["rank_of_the_published_fix"] is not None


def test_the_witness_never_reports_impossible():
    assert pool.UNRESOLVED.endswith("__NOT_A_CLAIM_OF_IMPOSSIBILITY")

"""A removed import must be related to an edit actually made in the target.

The example may include unrelated import cleanup, including imports relied on for
side effects or re-exported by another module. A successful rewrite is not evidence
that those unrelated imports should be removed from every target.
"""
import ast

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as editor


BEFORE = "import cgi\nimport random\n\ndef f(x):\n    return cgi.escape(x)\n"
AFTER = "import html\n\ndef f(x):\n    return html.escape(x)\n"


def test_unrelated_import_removed_by_example_is_not_removed_from_target():
    rules = editor.learn(BEFORE, AFTER)
    result = editor.repeated(rules, BEFORE, "example")
    assert "import random\n" in result
    assert "import cgi\n" not in result
    assert "html.escape(x)" in result


def test_unrelated_import_is_kept_even_when_target_does_not_import_changed_name():
    before = "import random\n\ndef f(x):\n    return x + 1\n"
    after = "def f(x):\n    return x + 2\n"
    target = "import random\n\ndef f(x):\n    return x + 1\n"
    result = editor.repeated(editor.learn(before, after), target, "example")
    assert result == "import random\n\ndef f(x):\n    return x + 2\n"


def test_probe_that_forces_a_place_to_fail_cannot_authorize_removal():
    rules = editor.learn(BEFORE, AFTER)
    # Exercise the actual fail-at path used for checking whether a target place
    # matters, rather than treating the intentionally failing replacement as a lesson.
    text = editor.Text(BEFORE, "target")
    # Keep the test independent of the matching API: the first rule fits this node.
    node = next(n for n in ast.walk(text.tree)
                if isinstance(n, ast.Attribute) and ast.unparse(n) == "cgi.escape")
    bound = {}
    assert editor.fits(rules[0].pattern, node, bound)
    place = (text.span(node), node, rules[0], bound)
    result = editor.written_once(text, [place], fail_at=(text.span(node), node))
    assert "import cgi\n" in result
    assert "import random\n" in result
    assert "ChangedCodeFails" in result

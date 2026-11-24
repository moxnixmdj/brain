"""The oracle that cannot choose: what the receipt claims, held to what the tool does.

Why a test and not prose
------------------------
The claim of this round is embarrassing to the project's own plan -- the loop it has proposed
three times ("run the tests, keep what passes") is shown here to keep 34 of 80 arrangements on a
task whose answer is one of them, and not one of the other 33 passes the hidden test. A claim like
that must be checkable by somebody who does not trust the receipt, so this file holds:

  1. the TOOL's search never receives the hidden fail-to-pass list (leakage would invalidate
     everything), and the only thing it reads from the test patch is the module label;
  2. the generator is honest about the two expert changes: both are REACHED, and reached by a
     label that names the function the expert touched;
  3. the arithmetic in the receipt adds up and says what it means;
  4. the defects this round found in its own instrument are recorded, and two of them are pinned by
     a test that would fail if they came back.

Nothing here re-runs the measurement: re-running it costs ~5 minutes per task and the receipt
keeps the numbers. What is tested is that the instrument cannot quietly become a different one.
"""
from __future__ import annotations

import ast
import inspect
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.tools import can_the_visible_suite_select_v1 as tool   # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "THE_ORACLE_THAT_CANNOT_CHOOSE_20261124_V1.json"


def receipt() -> dict:
    return json.loads(RECEIPT.read_text())


# --------------------------------------------------------------------------- #
# 1. the search cannot see the hidden tests
# --------------------------------------------------------------------------- #
def test_the_search_function_never_receives_the_fail_to_pass_list() -> None:
    """`measure` is where the green set is decided. The hidden tests must not be an argument, and
    must not be reachable from one."""
    parameters = set(inspect.signature(tool.measure).parameters)
    assert "fail_to_pass" not in parameters
    assert "hidden" not in " ".join(parameters).lower()
    source = inspect.getsource(tool.measure)
    assert "fail_to_pass" not in source
    assert "pass_to_pass" not in source


def test_the_only_thing_taken_from_the_test_patch_is_the_module_label() -> None:
    """`labels_of` reads test module paths out of a diff. It must not return test names, whose
    assertions are the answer."""
    source = inspect.getsource(tool.labels_of)
    assert "def labels_of" in source
    patch = "diff --git a/tests/admin_views/test_x.py b/tests/admin_views/test_x.py\n+    def test_secret(self):\n+        self.assertEqual(1, 2)\n"
    labels = tool.labels_of(patch)
    assert labels == ["admin_views.test_x"]
    assert all("test_secret" not in label for label in labels)


def test_the_receipt_states_the_order_the_hidden_tests_are_used_in() -> None:
    text = receipt()["integrity_before_anything"]
    assert "PRISTINE" in text
    assert "afterwards" in text


# --------------------------------------------------------------------------- #
# 2. the generator reaches the two expert changes it claims to reach
# --------------------------------------------------------------------------- #
EXPERT = {
    # the expert change, written out here rather than fetched, so the test needs no network
    "django__django-16527": (
        "django/contrib/admin/templatetags/admin_modify.py",
        '"show_save_as_new": not is_popup\n            and has_change_permission\n',
        '"show_save_as_new": not is_popup\n            and has_add_permission\n',
    ),
}


def test_a_leaf_exchange_between_two_names_the_file_holds_is_generated() -> None:
    """The round's cheapest true statement: `has_change_permission` -> `has_add_permission` is one
    of the arrangements the tool produces from the file alone, and the tool labels it as such."""
    path, old, new = EXPERT["django__django-16527"]
    source = (
        "from django.utils.translation import gettext_lazy as _\n"
        "\n"
        "def submit_row(context):\n"
        '    is_popup = context["is_popup"]\n'
        "    has_add_permission = context.get(\"has_add_permission\", True)\n"
        "    has_change_permission = context.get(\"has_change_permission\", True)\n"
        "    change = context[\"change\"]\n"
        "    return {\n"
        "        \"show_save\": not is_popup and has_change_permission and change,\n"
        '        "show_save_as_new": not is_popup\n'
        "            and has_change_permission\n"
        "            and change,\n"
        "    }\n"
    )
    arrangements = tool.arrangements(source, 100000)
    labels = [what for what, _ in arrangements]
    assert any("has_change_permission->has_add_permission" in label for label in labels)
    written = dict(arrangements)["leaf:has_change_permission->has_add_permission"]
    assert "has_add_permission" in written


def test_a_binding_before_the_consumer_is_generated_and_is_not_inside_the_docstring() -> None:
    """`format_type = str(format_type)` before the line that consumes it. The first version of this
    family put the statement INSIDE the docstring; the guard is that the function's docstring is
    still the first statement and the binding is a statement of its own."""
    source = (
        "def get_format(format_type, lang=None):\n"
        '    """Return the format for a specific format type."""\n'
        "    if format_type == 'DATE_FORMAT':\n"
        "        return 1\n"
        "    cache_key = (format_type, lang)\n"
        "    return cache_key\n"
    )
    arrangements = dict(tool.arrangements(source, 100000))
    binds = {label: written for label, written in arrangements.items() if label.startswith("bind:get_format:format_type=str")}
    assert binds, "the BIND family produced nothing for a name it rebinds"
    for written in binds.values():
        tree = ast.parse(written)
        function = tree.body[0]
        assert isinstance(function.body[0], ast.Expr), "the docstring stopped being the first statement"
        assert isinstance(function.body[0].value, ast.Constant)
        assert any(
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "format_type"
            and isinstance(node.value, ast.Call) and getattr(node.value.func, "id", "") == "str"
            for node in function.body
        ), "no `format_type = str(format_type)` statement in the function"


def test_the_consumer_site_is_used_not_only_the_top() -> None:
    source = (
        "def f(x):\n"
        '    """doc"""\n'
        "    return g(x)\n"
    )
    labels = [what for what, _ in tool.arrangements(source, 100000) if what.startswith("bind:f:x=")]
    assert len(labels) >= 2, "both the top and the consumer site must be tried"


# --------------------------------------------------------------------------- #
# 3. every generated arrangement is a different program that compiles
# --------------------------------------------------------------------------- #
def test_every_arrangement_compiles_and_differs_from_the_file() -> None:
    source = "def f(a, b):\n    c = a + b\n    return c\n"
    seen = set()
    for what, written in tool.arrangements(source, 100000):
        assert written != source, what
        assert written not in seen, f"a duplicate arrangement was emitted: {what}"
        seen.add(written)
        compile(written, what, "exec", dont_inherit=True)


def test_a_candidate_is_not_a_cumulative_edit() -> None:
    """The defect that made every candidate name the target: a shared tree mutated in place. Two
    different labels must give two different programs, each differing from the source in ONE
    place."""
    source = "def f(a, b):\n    return a + b\n"
    first = dict(tool.arrangements(source, 100000))
    second = dict(tool.arrangements(source, 100000))
    assert first == second, "the generator is not deterministic"
    for label, written in list(first.items())[:25]:
        assert written.count("+") <= source.count("+") + 1, label


# --------------------------------------------------------------------------- #
# 4. the arithmetic of the claim
# --------------------------------------------------------------------------- #
def test_the_two_tasks_say_what_the_receipt_says_they_say() -> None:
    measured = receipt()["measured"]
    assert measured["django__django-16527"]["green_that_ALSO_pass_the_hidden_new_test"] == 0
    assert measured["django__django-15741"]["green_that_ALSO_pass_the_hidden_new_test"] == 0
    for task in measured.values():
        assert task["green_under_the_repository_s_own_tests"] <= task["scored"]
        assert task["scored"] <= task["space"]
        assert task["hidden_oracle_is_valid"] == {"with_the_expert_change": True, "unmodified": False}


def test_the_green_shares_are_what_the_counts_give() -> None:
    for task in receipt()["measured"].values():
        share = task["green_under_the_repository_s_own_tests"] / task["scored"]
        assert abs(share - task["share_green"]) < 0.006, (task["share_green"], share)


def test_the_claim_is_bounded_to_two_tasks_and_says_so() -> None:
    limits = receipt()["limits"]
    assert any(limit.startswith("TWO tasks") for limit in limits)
    assert receipt()["model_calls"] == 0 and receipt()["parameters"] == 0


def test_the_receipt_records_the_defects_found_in_its_own_instrument() -> None:
    defects = receipt()["defects_this_round_found_in_its_own_instrument"]
    assert len(defects) >= 6
    joined = " ".join(defects)
    assert "docstring" in joined
    assert "alphabetically" in joined
    assert "litter" in joined

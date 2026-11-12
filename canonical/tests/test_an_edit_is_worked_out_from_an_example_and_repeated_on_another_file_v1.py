"""An edit is worked out from one example and repeated on another file.

The example is two files, before and after.  ``canonical/swe_kernel/taught_actions/edit_by_example_v1``
finds what changed, turns it into rewrite rules, and makes the same change in a third file.  Nobody
writes the change down as a program.

Pinned here:

* the rule is about the smallest piece of code that holds a change, and a part of it becomes a blank
  only where two changed places of the example differ;
* code the example left alone vetoes a rule that would change it; then more surrounding code is
  taken into the rule, or the example is refused;
* a change that only works together with other changes (a rename) is refused, and so is new code
  that would read a name the edited file does not provide;
* the edit touches only the bytes of the places that fit, and adds brackets only where the new code
  needs them -- checked against an independent tree rewrite on generated code;
* the lesson is in the tracked bundle, and through the front door the sentence is done inside the
  sandbox, while every case the action declines is refused with the action's own reason.
"""
from __future__ import annotations

import ast
import pathlib
import random
import shutil

import pytest

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as compiler
from canonical.swe_kernel.taught_actions import edit_by_example_v1 as by_example
from canonical.tools import teach_actions_v1 as teach

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRATCH = ROOT / "canonical/astra_runtime/tmp/zq_w7_k2"
needs_sandbox = pytest.mark.skipif(
    compiler._sandbox_for_taught_programs() is None, reason="this machine cannot start the namespace sandbox")

ASSERTS = ("class T:\n"
           "    def test_a(self):\n"
           "        self.assertEquals(add(1, 2), 3)\n"
           "        self.assertTrue(ok)\n"
           "    def test_b(self):\n"
           "        self.assertEquals(name, 'x')\n")
NONE_BEFORE = "def f(total, rate):\n    if total == None:\n        return 0\n    return rate.x == None\n"
NONE_AFTER = "def f(total, rate):\n    if total is None:\n        return 0\n    return rate.x is None\n"
# The third line of each shows the result called: a use that was not shown is refused, and the generated code below calls it.
HAS_KEY = ("a = d.has_key(k)\nb = e.f.has_key('x')\nc = g.has_key(m)(1)\n", "a = k in d\nb = 'x' in e.f\nc = (m in g)(1)\n")
POWER = ("a = pow(x, 2)\nb = pow(y.z, 2)\nc = pow(w, 2)(1)\n", "a = x ** 2\nb = y.z ** 2\nc = (w ** 2)(1)\n")
FIRST = ("a = first(x)\nb = first(y[0])\nc = first(w)(1)\n", "a = x[0]\nb = y[0][0]\nc = w[0](1)\n")
JOIN = ("import os\nx = os.path.join(a, b)\ny = os.path.join(c.d, 'e')\n",
        "import os\nfrom pathlib import Path\nx = Path(a) / b\ny = Path(c.d) / 'e'\n")


def rules(before: str, after: str) -> list[str]:
    return [str(rule) for rule in by_example.learn(before, after)]


# ----------------------------------------------------------------------------- what a rule is


@pytest.mark.parametrize("before,after,expected", [
    # one changed place: the smallest piece that holds the change, exactly as written
    ("x = compute(a, b)\ny = other(c)\n", "x = compute(a, b, strict=True)\ny = other(c)\n",
     ["compute(a, b) -> compute(a, b, strict=True)"]),
    # two places that differ only in what the call is given: the method is the rule, the arguments are not in it
    (ASSERTS, ASSERTS.replace("assertEquals", "assertEqual"), ["self.assertEquals -> self.assertEqual"]),
    # two places that differ in one operand: that operand is a blank
    (NONE_BEFORE, NONE_AFTER, ["?1 == None -> ?1 is None"]),
    # blanks may move and repeat
    (HAS_KEY[0], HAS_KEY[1], ["?1.has_key(?2) -> ?2 in ?1"]),
    ("p = a * 2\ndef f(b):\n    return b * 2\n", "p = a + a\ndef f(b):\n    return b + b\n", ["?1 * 2 -> ?1 + ?1"]),
    # the same blank in two positions means the same code in both
    ("x = x + 1\ny = y + 1\n", "x += 1\ny += 1\n", ["?1 = ?1 + 1 -> ?1 += 1"]),
    # a keyword argument is a piece of its own
    ("f = open(p, encoding='utf8')\ng = open(q, 'r', encoding='utf8')\n",
     "f = open(p, encoding='utf-8')\ng = open(q, 'r', encoding='utf-8')\n", ["encoding='utf8' -> encoding='utf-8'"]),
    # two kinds of change in one example are two rules
    ("a = s.assertEquals(1, 1)\nb = s.assertNotEquals(1, 2)\n", "a = s.assertEqual(1, 1)\nb = s.assertNotEqual(1, 2)\n",
     ["s.assertEquals -> s.assertEqual", "s.assertNotEquals -> s.assertNotEqual"]),
    # an import line changed in place is a one-line statement like any other
    ("from django.utils.translation import ugettext_lazy as _\nlabel = _('x')\n",
     "from django.utils.translation import gettext_lazy as _\nlabel = _('x')\n",
     ["from django.utils.translation import ugettext_lazy as _ -> from django.utils.translation import gettext_lazy as _"]),
    # an import line that was added is not a place; the rule is what uses it
    (JOIN[0], JOIN[1], ["os.path.join(?1, ?2) -> Path(?1) / ?2"]),
])
def test_the_rule_is_the_smallest_changed_piece_with_blanks_only_where_places_differ(before, after, expected) -> None:
    assert rules(before, after) == expected


def test_two_changes_that_only_look_alike_are_not_merged_into_a_rule_of_blanks() -> None:
    # Both calls gained an argument.  "any call gains an argument" would fit both -- and any other call.
    assert rules("a = foo(x)\nb = bar(y)\n", "a = foo(x, 1)\nb = bar(y, 1)\n") == [
        "foo(x) -> foo(x, 1)", "bar(y) -> bar(y, 1)"]


def test_code_the_example_left_alone_makes_the_rule_take_in_more_of_its_surroundings() -> None:
    # compute(a, b) was changed on one line and left alone on another: the call alone is not the rule.
    before = "x = compute(a, b)\nprint(compute(a, b))\n"
    after = "x = compute(a, b, strict=True)\nprint(compute(a, b))\n"
    assert rules(before, after) == ["x = compute(a, b) -> x = compute(a, b, strict=True)"]
    edited = by_example.edit_by_example("def g(a, b):\n    x = compute(a, b)\n    return compute(a, b)\n", before, after)
    assert edited == "def g(a, b):\n    x = compute(a, b, strict=True)\n    return compute(a, b)\n"


def test_the_rules_reproduce_the_example_they_came_from() -> None:
    for before, after in [(ASSERTS, ASSERTS.replace("assertEquals", "assertEqual")), (NONE_BEFORE, NONE_AFTER),
                          HAS_KEY, POWER, FIRST]:
        replayed, count = by_example.rewrite(by_example.learn(before, after), before)
        assert count >= 2 and ast.dump(ast.parse(replayed)) == ast.dump(ast.parse(after))


# ----------------------------------------------------------------------------- repeating the change


def test_only_the_places_that_fit_are_changed_and_everything_else_keeps_its_bytes() -> None:
    target = ("class U:\r\n"
              "    def test_c(self):\r\n"
              "        self.assertEquals( len(rows),4 )  # keep  this\r\n"
              "        value = self.assertEquals(a, b, msg='why')\r\n"
              "        other.assertEquals(a, b)\r\n"
              "        note = 'self.assertEquals(1, 1)'   # caf\u00e9\r\n")
    shown = ASSERTS + "        self.assertEquals(name, 'y', msg='named')\n"      # the keyword is used below, so it is shown
    edited = by_example.edit_by_example(target, shown, shown.replace("assertEquals", "assertEqual"))
    assert edited == (target.replace("self.assertEquals( len", "self.assertEqual( len")
                      .replace("value = self.assertEquals", "value = self.assertEqual"))


def test_a_blank_keeps_the_code_that_stood_there_with_brackets_only_where_needed() -> None:
    target = ("ok = not cache.has_key(a + b) and m.has_key(n)\n"
              "n = cache.has_key(a or b) + 1\n"
              "q = [x.has_key(y) for y in z if w.has_key(y) == True]\n"
              "p = -c.has_key(1) ** 2\n")
    assert by_example.edit_by_example(target, *HAS_KEY) == (
        "ok = not a + b in cache and n in m\n"
        "n = ((a or b) in cache) + 1\n"
        "q = [y in x for y in z if (y in w) == True]\n"
        "p = -(1 in c) ** 2\n")
    assert by_example.edit_by_example("c = pow(-m, 2)\nd = -pow(m, 2)\ne = pow(m + 1, 2) ** 3\nf = 2 ** pow(m, 2)\n", *POWER) == (
        "c = (-m) ** 2\nd = -m ** 2\ne = ((m + 1) ** 2) ** 3\nf = 2 ** m ** 2\n")
    assert by_example.edit_by_example("c = first(p if q else r)\nd = first(lambda: 1)\ne = first((1, 2))\nf = first(u.v)\n", *FIRST) == (
        "c = (p if q else r)[0]\nd = (lambda: 1)[0]\ne = (1, 2)[0]\nf = u.v[0]\n")
    assert by_example.edit_by_example("s = (c - d) * 2\nr = y * 2 * z\n", "p = a * 2\ndef f(b):\n    return b * 2\n",
                                      "p = a + a\ndef f(b):\n    return b + b\n") == "s = c - d + (c - d)\nr = (y + y) * z\n"


def test_text_that_parses_to_something_else_is_not_accepted() -> None:
    before, after = "a = pair(x, y)\nb = pair(u.v, 1)\n", "a = x, y\nb = u.v, 1\n"
    assert rules(before, after) == ["pair(?1, ?2) -> ?1, ?2"]
    # Written without brackets, ``f(p, q)`` parses -- as a call with two arguments.  That is not the edit.
    assert by_example.edit_by_example("r = f(pair(p, q))\n", before, after) == "r = f((p, q))\n"


def test_rules_that_do_not_reproduce_their_example_are_not_used(monkeypatch) -> None:
    monkeypatch.setattr(by_example, "rewrite", lambda found, text, *rest, **more: (text, 0))   # an edit that edits nothing
    with pytest.raises(by_example.Refused, match="do not reproduce the example"):
        by_example.learn(NONE_BEFORE, NONE_AFTER)


def test_the_same_blank_twice_needs_the_same_code_twice() -> None:
    edited = by_example.edit_by_example("k = k + 1\nm = n + 1\nself.n = self.n + 1\n", "x = x + 1\ny = y + 1\n", "x += 1\ny += 1\n")
    assert edited == "k += 1\nm = n + 1\nself.n += 1\n"


def test_a_rule_learned_where_code_is_read_does_not_change_where_it_is_assigned() -> None:
    before = "def f(o):\n    a = o.size\n    return o.size + a\n"
    after = "def f(o):\n    a = o.length\n    return o.length + a\n"
    assert by_example.edit_by_example("o.size = 3\nprint(o.size)\n", before, after) == "o.size = 3\nprint(o.length)\n"


class _HasKey(ast.NodeTransformer):
    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "has_key" and len(node.args) == 1:
            return ast.Compare(left=node.args[0], ops=[ast.In()], comparators=[node.func.value])
        return node


class _Power(ast.NodeTransformer):
    def visit_Call(self, node):
        self.generic_visit(node)
        if (isinstance(node.func, ast.Name) and node.func.id == "pow" and len(node.args) == 2
                and isinstance(node.args[1], ast.Constant) and node.args[1].value == 2):
            return ast.BinOp(left=node.args[0], op=ast.Pow(), right=ast.Constant(value=2))
        return node


class _First(ast.NodeTransformer):
    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id == "first" and len(node.args) == 1:
            return ast.Subscript(value=node.args[0], slice=ast.Constant(value=0), ctx=ast.Load())
        return node


def _expression(rng: random.Random, depth: int) -> str:
    if depth == 0 or rng.random() < 0.2:
        return rng.choice(["a", "b.c", "d[0]", "g(h)", "1", "'s'", "-e"])
    one, two, three = (_expression(rng, depth - 1) for _ in range(3))
    return rng.choice([
        "(%s) + (%s)" % (one, two), "(%s) * (%s)" % (one, two), "(%s) or (%s)" % (one, two),
        "(%s) and (%s)" % (one, two), "not (%s)" % one, "(%s) if (%s) else (%s)" % (one, two, three),
        "(%s) ** (%s)" % (one, two), "((%s), (%s))" % (one, two), "(lambda: (%s))" % one,
        "(%s) == (%s)" % (one, two), "(%s) - (%s)" % (one, two), "[(%s)]" % one, "(%s) | (%s)" % (one, two),
        "(%s) < (%s)" % (one, two), "~(%s)" % one, "(%s).real" % one, "(%s)[1]" % one])


@pytest.mark.parametrize("example,call,oracle", [
    (HAS_KEY, "(%s).has_key(%s)", _HasKey), (POWER, "pow(%s, 2)", _Power), (FIRST, "first(%s)", _First),
], ids=["has_key", "pow", "first"])
def test_generated_code_comes_out_as_an_independent_tree_rewrite_says(example, call, oracle) -> None:
    rng = random.Random(20261112)
    frames = ["x = %s", "x = not %s", "x = -%s", "x = %s + 1", "x = 1 - %s", "x = %s ** 2", "x = 2 ** %s",
              "x = %s.real", "x = %s[0]", "x = %s(1)", "x = [%s for i in j if %s]", "x = %s if %s else 0",
              "x = f(%s, k=%s)", "x = %s and %s", "x = %s == %s", "x = lambda: %s", "x = (%s, %s)", "x = %s * 3 // 4"]
    checked = 0
    for _ in range(240):
        frame = rng.choice(frames)
        calls = []
        for _slot in range(frame.count("%s")):
            blanks = tuple(_expression(rng, rng.randrange(3)) for _ in range(call.count("%s")))
            written = call % blanks
            calls.append("(%s)" % written if rng.random() < 0.3 else written)
        target = "# kept\n" + frame % tuple(calls) + "  # also kept\n"
        expected = ast.dump(ast.fix_missing_locations(oracle().visit(ast.parse(target))))
        try:
            edited = by_example.edit_by_example(target, *example)
        except by_example.Refused as why:
            assert "its own variable" in str(why) or "does not define" in str(why), (target, str(why))
            continue
        assert ast.dump(ast.parse(edited)) == expected, (target, edited)
        assert edited.startswith("# kept\n") and edited.endswith("  # also kept\n")
        checked += 1
    assert checked >= 200


# ----------------------------------------------------------------------------- what is refused


@pytest.mark.parametrize("why,target,before,after,reason", [
    ("the example renames a variable: each changed line works only with the others",
     "def g(tmp):\n    return tmp + 1\n",
     "def f(a, b):\n    tmp = a * b\n    return tmp + 1\n", "def f(a, b):\n    product = a * b\n    return product + 1\n",
     "changes which names are assigned"),
    ("the new code reads a variable that exists only inside the example's function",
     "def g(a):\n    return scale(a)\n",
     "def f(a):\n    k = 2\n    return scale(a)\n", "def f(a):\n    k = 2\n    return scale(a) * k\n",
     "makes the code read 'k'"),
    ("the same code was changed in one place and left alone in another",
     "x = f(1)\n", "x = f(1)\ny = 2\nx = f(1)\n", "x = f(2)\ny = 2\nx = f(1)\n", "left alone, or changed another way"),
    ("the example adds a statement", "x = 1\n", "x = 1\n", "x = 1\ny = 2\n", "adds, removes or reshapes whole statements"),
    ("the example renames a function", "def g():\n    pass\n", "def f():\n    pass\n", "def h():\n    pass\n",
     "adds, removes or reshapes whole statements"),
    ("the two example files hold the same code", "x = 1\n", "x = 1  # a\n", "x  =  1\n", "hold the same code"),
    ("nothing in the file has the changed form", "x = 1\n", NONE_BEFORE, NONE_AFTER,
     "nothing in the file has the form the example changed (?1 == None -> ?1 is None)"),
    ("a comment inside a changed place would be lost", "c = d.has_key(  # why\n    z)\n", HAS_KEY[0], HAS_KEY[1],
     "a comment inside the code at line 1"),
    ("the new code needs an import that cannot be found here", "import os\nz = os.path.join(root, name)\n",
     JOIN[0], JOIN[1].replace("from pathlib import Path", "from zq_paths_q7 import Path""").replace("pathlib", "zq_paths_q7"),
     "nothing named 'zq_paths_q7' can be found"),
    ("the new code brings its own variable and the copied code already uses that name",
     "d = map(lambda v: v + x, cells)\n", "a = map(str, xs)\nb = map(int, rows[0])\n",
     "a = [str(x) for x in xs]\nb = [int(x) for x in rows[0]]\n", "its own variable 'x'"),
    ("an import was renamed but a function binds the old name for itself and reads it",
     "from m import old_name\nx = old_name(1)\n\n\ndef f(old_name):\n    return [old_name]\n",
     "from m import old_name\nx = old_name(1)\nz = old_name(2, 3)\n", "from m import new_name\nx = new_name(1)\nz = new_name(2, 3)\n",
     "takes the name 'old_name' away"),
    ("two places to change overlap", "x = first(first(y))\n", FIRST[0], FIRST[1], "overlap"),
    ("the file to edit is not Python", "x = = 1\n", NONE_BEFORE, NONE_AFTER, "is not Python"),
])
def test_what_cannot_be_repeated_one_place_at_a_time_is_refused(why, target, before, after, reason) -> None:
    with pytest.raises(by_example.Refused) as refusal:
        by_example.edit_by_example(target, before, after)
    assert reason in str(refusal.value), why


def test_new_code_may_read_what_the_file_provides() -> None:
    assert by_example.edit_by_example("import os\nfrom pathlib import Path\nz = os.path.join(root, name)\n", *JOIN) == (
        "import os\nfrom pathlib import Path\nz = Path(root) / name\n")
    gains_self = ("class A:\n    def f(self, x):\n        return helper(x)\n    def g(self, y):\n        return [helper(y + 1)]\n",
                  "class A:\n    def f(self, x):\n        return self.helper(x)\n    def g(self, y):\n        return [self.helper(y + 1)]\n")
    assert by_example.edit_by_example("class B:\n    def h(self, q):\n        return helper(q)\n", *gains_self) == (
        "class B:\n    def h(self, q):\n        return self.helper(q)\n")
    with pytest.raises(by_example.Refused, match="the change uses 'self'"):
        by_example.edit_by_example("def free(q):\n    return helper(q)\n", *gains_self)


def test_an_import_changed_together_with_its_uses_is_repeated_when_every_use_is_covered() -> None:
    before = "from m import old_name\nx = old_name(1)\nz = old_name(k)\n"
    after = "from m import new_name\nx = new_name(1)\nz = new_name(k)\n"
    assert rules(before, after) == ["old_name(?1) -> new_name(?1)", "from m import old_name -> from m import new_name"]
    assert by_example.edit_by_example("from m import old_name\nq = old_name(7)\n", before, after) == (
        "from m import new_name\nq = new_name(7)\n")
    # ... and when the file lists the name among others on its import line, the one alias follows
    # the renamed uses right where it stands, exactly as the example renamed its own
    assert by_example.edit_by_example("from m import other, old_name\nq = old_name(7)\n", before, after) == (
        "from m import other, new_name\nq = new_name(7)\n")


def test_the_program_refuses_without_writing(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    for name, text in (("t.py", "x = 1\n"), ("a.py", NONE_BEFORE), ("b.py", NONE_AFTER)):
        (tmp_path / name).write_text(text, encoding="utf-8")
    assert by_example.main(("edit", ("t.py", "a.py", "b.py"))) == 3
    assert capsys.readouterr().out.startswith("REFUSED: nothing in the file has the form")
    assert (tmp_path / "t.py").read_text(encoding="utf-8") == "x = 1\n"
    assert by_example.main(("edit", ("../t.py", "a.py", "b.py"))) == 3
    assert "must be a path inside the project" in capsys.readouterr().out
    (tmp_path / "t.py").write_text("if v == None:\n    pass\n", encoding="utf-8")
    assert by_example.main(("edit", ("t.py", "a.py", "b.py"))) == 0
    assert capsys.readouterr().out == "edited t.py the way a.py was changed into b.py\n"
    assert (tmp_path / "t.py").read_text(encoding="utf-8") == "if v is None:\n    pass\n"


# ----------------------------------------------------------------------------- the lesson and the front door


def test_the_lesson_is_in_the_tracked_bundle() -> None:
    import json
    skeletons = {skill["goal_skeleton"] for skill in json.loads(teach.BUNDLE.read_text(encoding="utf-8"))["skills"]}
    assert {"edit ?path0 the way ?path1 was changed into ?path2",
            "make the same change in ?path0 that turned ?path1 into ?path2"} <= skeletons


@pytest.fixture
def taught_door(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAIN_COMPILED_WORKFLOW_DB", str(tmp_path / "skills.sqlite"))
    compiler.import_workflow_bundle(teach.BUNDLE, db_path=tmp_path / "skills.sqlite")
    shutil.rmtree(SCRATCH, ignore_errors=True)
    SCRATCH.mkdir(parents=True)
    count = [0]

    def ask(sentence: str, files: dict[str, str]):
        count[0] += 1
        for name, text in files.items():
            (SCRATCH / name).write_text(text, encoding="utf-8")
        result = door.solve({"task_id": "BY_EXAMPLE_%d" % count[0],
                             "goal": sentence.replace("DIR", SCRATCH.relative_to(ROOT).as_posix())})
        return result, (SCRATCH / "tgt.py").read_text(encoding="utf-8")

    yield ask
    shutil.rmtree(SCRATCH, ignore_errors=True)


CLOCK_BEFORE = "import time\n\n\ndef run(job):\n    started = time.clock()\n    job()\n    return time.clock() - started\n"
CLOCK_AFTER = CLOCK_BEFORE.replace("time.clock", "time.perf_counter")
CLOCK_TARGET = ("import time\n\n\nclass Meter:\n    def lap(self):\n        now = time.clock()  # since start\n"
                "        return now - self.zero\n\n    def reset(self):\n        self.zero = time.clock()\n        return clock()\n")


@needs_sandbox
@pytest.mark.parametrize("sentence", [
    "edit DIR/tgt.py the way DIR/old.py was changed into DIR/new.py",
    "make the same change in DIR/tgt.py that turned DIR/old.py into DIR/new.py",
    "Edit DIR/tgt.py the way DIR/old.py was changed into DIR/new.py.",
])
def test_the_door_repeats_an_edit_it_is_shown(taught_door, sentence) -> None:
    result, after = taught_door(sentence, {"tgt.py": CLOCK_TARGET, "old.py": CLOCK_BEFORE, "new.py": CLOCK_AFTER})
    assert result.get("pass") is True, result.get("status")
    assert result["status"] == "PASS__COMPILED_WORKFLOW_SKILL"
    assert [receipt["confined"] for receipt in result["step_receipts"]] == [True]
    assert after == CLOCK_TARGET.replace("time.clock()", "time.perf_counter()")


@needs_sandbox
@pytest.mark.parametrize("files,reason", [
    ({"tgt.py": "def g(tmp):\n    return tmp + 1\n", "old.py": "def f(a, b):\n    tmp = a * b\n    return tmp + 1\n",
      "new.py": "def f(a, b):\n    product = a * b\n    return product + 1\n"}, "changes which names are assigned"),
    ({"tgt.py": "x = 1\n", "old.py": CLOCK_BEFORE, "new.py": CLOCK_AFTER}, "nothing in the file has the form"),
    ({"tgt.py": CLOCK_TARGET, "old.py": CLOCK_BEFORE, "new.py": CLOCK_BEFORE}, "hold the same code"),
])
def test_what_the_action_declines_is_refused_at_the_door_with_its_reason(taught_door, files, reason) -> None:
    result, after = taught_door("edit DIR/tgt.py the way DIR/old.py was changed into DIR/new.py", files)
    assert result.get("pass") is not True
    assert after == files["tgt.py"]
    assert reason in str(result.get("taught_action_declined")), result.get("taught_action_declined")


@needs_sandbox
@pytest.mark.parametrize("sentence", [
    "edit DIR/tgt.py like DIR/old.py was changed into DIR/new.py",
    "edit DIR/tgt.py the way DIR/old.py was changed",
    "edit everything the way DIR/old.py was changed into DIR/new.py",
])
def test_a_sentence_that_is_not_the_taught_one_is_refused(taught_door, sentence) -> None:
    result, after = taught_door(sentence, {"tgt.py": CLOCK_TARGET, "old.py": CLOCK_BEFORE, "new.py": CLOCK_AFTER})
    assert result.get("pass") is not True
    assert after == CLOCK_TARGET


def test_without_the_lesson_the_door_refuses_the_sentence(taught_door, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("BRAIN_COMPILED_WORKFLOW_DB", str(tmp_path / "empty.sqlite"))
    monkeypatch.setattr(compiler, "default_workflow_bundle_path", lambda: tmp_path / "no_bundle.json")
    result, after = taught_door("edit DIR/tgt.py the way DIR/old.py was changed into DIR/new.py",
                                {"tgt.py": CLOCK_TARGET, "old.py": CLOCK_BEFORE, "new.py": CLOCK_AFTER})
    assert result.get("pass") is not True
    assert after == CLOCK_TARGET

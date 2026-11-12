"""Two refactorings the front door did not have are taught, once each, and checked on a second example.

The actions: rename a local variable; inline a local variable that is set once and read once,
straight away.  Each is a self-contained program in ``canonical/swe_kernel/taught_actions``.
``canonical/tools/teach_actions_v1.py`` runs a program on a first example, then hands it to the
existing demonstration-to-skill compiler with a second example; what qualifies is exported to the
tracked bundle, and the front door recalls from it when its usual path has refused a sentence.

Pinned here:

* each program does what it says and nothing else, and refuses whenever it cannot keep behaviour
  the same -- on written cases and on generated functions run before and after;
* a taught value occurs once in its program, inside a string literal, so a request can only ever
  arrive there as data;
* the tracked bundle is exactly what teaching produces, and each skill in it is its program;
* through the front door a taught sentence is done on a new file inside the sandbox, a case the
  action declines is refused with the action's own reason, and the usual traps stay refused;
* a skill database that already exists receives skills that are added to the bundle later.
"""
from __future__ import annotations

import json
import pathlib
import random
import re
import shutil

import pytest

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as compiler
from canonical.swe_kernel.taught_actions import inline_variable_v1 as inline
from canonical.swe_kernel.taught_actions import rename_local_variable_v1 as rename
from canonical.tools import teach_actions_v1 as teach

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRATCH = ROOT / "canonical/astra_runtime/tmp/test_taught_refactorings"
needs_sandbox = pytest.mark.skipif(
    compiler._sandbox_for_taught_programs() is None, reason="this machine cannot start the namespace sandbox")

MODULE = '''import math


def double(x):
    return 2 * x


def compute(a, b, verbose=False):
    tmp = a * b
    scaled = tmp / 3600
    if verbose:
        print("scaled", scaled)
    total = scaled + double(a)
    return total
'''


def _call(source: str, expression: str):
    scope: dict = {}
    exec(compile(source, "<module>", "exec"), scope)  # noqa: S102 - the module under test
    try:
        return "returned", eval(expression, scope)  # noqa: S307
    except Exception as error:  # noqa: BLE001 - the kind of failure is part of the behaviour
        return "raised", type(error).__name__


# ----------------------------------------------------------------------------- rename a local variable


def test_a_rename_changes_the_variable_and_only_the_variable() -> None:
    source = (
        "def compute(a, b):\n"
        "    tmp = a * b  # tmp is a product\n"
        "    pick = lambda k: tmp + k\n"
        "    rows = [tmp * i for i in range(3)]\n"
        "    text = f\"{tmp!r} and {'tmp'}\"\n"
        "    box.tmp = tmp\n"
        "    note(tmp=tmp)\n"
        "    return pick(1), rows, text\n"
    )
    assert rename.rename_local_variable(source, "compute", "tmp", "product") == (
        "def compute(a, b):\n"
        "    product = a * b  # tmp is a product\n"
        "    pick = lambda k: product + k\n"
        "    rows = [product * i for i in range(3)]\n"
        "    text = f\"{product!r} and {'tmp'}\"\n"
        "    box.tmp = product\n"
        "    note(tmp=product)\n"
        "    return pick(1), rows, text\n"
    )


def test_a_rename_reaches_a_method_and_leaves_its_namesakes_alone() -> None:
    source = (
        "r = 10\n\n\n"
        "class Disc:\n"
        "    def area(self):\n"
        "        r = self.r\n"
        "        return 3 * r * r\n\n"
        "    def rim(self):\n"
        "        r = self.r\n"
        "        return 6 * r\n"
    )
    result = rename.rename_local_variable(source, "Disc.area", "r", "radius")
    assert "        radius = self.r\n        return 3 * radius * radius\n" in result
    assert result.startswith("r = 10\n") and "        r = self.r\n        return 6 * r\n" in result


@pytest.mark.parametrize("why,source,function,old,new", [
    ("a parameter", "def f(a):\n    return a\n", "f", "a", "b"),
    ("not a variable assigned", "def f():\n    return limit\n", "f", "limit", "cap"),
    ("already used", "def f():\n    x = 1\n    y = 2\n    return x + y\n", "f", "x", "y"),
    ("already used", "def f():\n    x = 1\n    return x + cap\n", "f", "x", "cap"),
    ("already used", "def f(cap):\n    x = 1\n    return x\n", "f", "x", "cap"),
    ("nested scope", "def f():\n    x = 1\n    g = lambda x: x\n    return g(x)\n", "f", "x", "y"),
    ("nested scope", "def f():\n    x = 1\n    return [x for x in range(3)]\n", "f", "x", "y"),
    ("nested scope", "def f():\n    x = 1\n    def g():\n        x = 2\n        return x\n    return g() + x\n", "f", "x", "y"),
    ("an except clause", "def f():\n    try:\n        pass\n    except KeyError as x:\n        x = 1\n", "f", "x", "y"),
    ("an import", "def f():\n    import os as x\n    x = 1\n", "f", "x", "y"),
    ("a nested def or class", "def f():\n    def x():\n        return 1\n    x = 2\n", "f", "x", "y"),
    ("a global or nonlocal", "def f():\n    global x\n    x = 1\n", "f", "x", "y"),
    ("a global or nonlocal", "def f():\n    x = 1\n    def g():\n        nonlocal x\n        x = 2\n    return x\n", "f", "x", "y"),
    ("can see variable names", "def f():\n    x = 1\n    return locals()\n", "f", "x", "y"),
    ("can see variable names", "def f(s):\n    x = 1\n    return eval(s)\n", "f", "x", "y"),
    ("not a name", "def f():\n    x = 1\n    return x\n", "f", "x", "class"),
    ("not a name", "def f():\n    x = 1\n    return x\n", "f", "x", "a b"),
    ("not a name", "def f():\n    x = 1\n    return x\n", "f", "x", "__import__('os')"),
    ("the same", "def f():\n    x = 1\n    return x\n", "f", "x", "x"),
    ("no function", "def f():\n    x = 1\n    return x\n", "g", "x", "y"),
    ("a class, not a function", "class C:\n    x = 1\n", "C", "x", "y"),
    ("2 definitions", "def f():\n    x = 1\n\ndef f():\n    x = 2\n", "f", "x", "y"),
])
def test_a_rename_that_could_change_behaviour_is_refused(why, source, function, old, new) -> None:
    with pytest.raises(rename.Refused, match=why):
        rename.rename_local_variable(source, function, old, new)


# ----------------------------------------------------------------------------- inline a variable


@pytest.mark.parametrize("source,name,expected", [
    ("def f(a, b):\n    tmp = a * b\n    return tmp + 1\n", "tmp", "def f(a, b):\n    return (a * b) + 1\n"),
    ("def f(a):\n    x = a - 1\n    return round(x, 2)\n", "x", "def f(a):\n    return round(a - 1, 2)\n"),
    ("def f(a):\n    n = 5\n    return n.real\n", "n", "def f(a):\n    return (5).real\n"),
    ("def f(a):\n    t = a, 2\n    return len(t)\n", "t", "def f(a):\n    return len((a, 2))\n"),
    ("def f(a):\n    s = a + 1\n    return s ** 2\n", "s", "def f(a):\n    return (a + 1) ** 2\n"),
    ("def f(a):\n    d = load(a)\n    if d:\n        return 1\n    return 0\n", "d",
     "def f(a):\n    if load(a):\n        return 1\n    return 0\n"),
    ("def f(xs):\n    k = lambda v: -v\n    return sorted(xs, key=k)\n", "k",
     "def f(xs):\n    return sorted(xs, key=(lambda v: -v))\n"),
    ("def f(a):\n    big = [\n        a,\n        a + 1,\n    ]\n    return sum(big)\n", "big",
     "def f(a):\n    return sum(([\n        a,\n        a + 1,\n    ]))\n"),
    ("def f(a):\n    if a:\n        y = a * 2\n        a += y\n    return a\n", "y",
     "def f(a):\n    if a:\n        a += a * 2\n    return a\n"),
    ("def f(xs):\n    out = []\n    for x in xs:\n        y = x * 2\n        # doubled\n        out += [y]\n    return out\n", "y",
     "def f(xs):\n    out = []\n    for x in xs:\n        # doubled\n        out += [x * 2]\n    return out\n"),
])
def test_an_inline_puts_the_expression_where_the_variable_was_read(source, name, expected) -> None:
    assert inline.inline_variable(source, "f", name) == expected


def test_an_inline_keeps_every_operation_in_the_order_it_ran() -> None:
    source = (
        "def f(log):\n"
        "    first = log.append('one') or 1\n"
        "    return first + (log.append('two') or 2)\n"
    )
    result = inline.inline_variable(source, "f", "first")
    assert result == "def f(log):\n    return (log.append('one') or 1) + (log.append('two') or 2)\n"
    before, after = [], []
    scope_before, scope_after = {}, {}
    exec(source, scope_before), exec(result, scope_after)  # noqa: S102
    assert scope_before["f"](before) == scope_after["f"](after) == 3
    assert before == after == ["one", "two"]


@pytest.mark.parametrize("why,source,name", [
    ("read 2 times", "def f(a):\n    x = a + 1\n    return x * x\n", "x"),
    ("never read", "def f(a):\n    x = a + 1\n    return a\n", "x"),
    ("set 2 times", "def f(a):\n    x = a\n    x = x + 1\n    return x\n", "x"),
    ("set 2 times", "def f(a):\n    x = a\n    x += 1\n    return x\n", "x"),
    ("a parameter", "def f(a):\n    return a\n", "a"),
    ("not a variable assigned", "def f(a):\n    return limit\n", "limit"),
    ("not set by a plain", "def f(a):\n    x: int = a\n    return x\n", "x"),
    ("not set by a plain", "def f(a):\n    x, y = a\n    return x\n", "x"),
    ("not set by a plain", "def f(a):\n    x = y = a\n    return x\n", "x"),
    ("not set by a plain", "def f(a):\n    for x in a:\n        pass\n    return x\n", "x"),
    # the read is not in the statement that directly follows
    ("not the first thing", "def f(a):\n    x = a + 1\n    a = 0\n    return x\n", "x"),
    ("not the first thing", "def f(a):\n    if a:\n        x = 1\n    return x\n", "x"),
    ("not the first thing", "def f(a):\n    x = a + 1\n    while x:\n        pass\n", "x"),
    # something is computed before the read, so the order of operations would change
    ("not the first thing", "def f(a):\n    x = a + 1\n    return g(a) + x\n", "x"),
    ("not the first thing", "def f(a, box):\n    x = a + 1\n    return box.put(x)\n", "x"),
    ("not the first thing", "def f(a):\n    x = a + 1\n    return f'{a}{x}'\n", "x"),
    # the read may be skipped or repeated
    ("not the first thing", "def f(a):\n    x = a + 1\n    return a and x\n", "x"),
    ("not the first thing", "def f(a):\n    x = a + 1\n    return 0 if a else x\n", "x"),
    ("not the first thing", "def f(a):\n    x = a + 1\n    return [x for _ in a]\n", "x"),
    ("not the first thing", "def f(a):\n    x = a + 1\n    return lambda: x\n", "x"),
    ("not the first thing", "def f(a):\n    x = a + 1\n    return g(*a, x)\n", "x"),
    # a name read before the variable could be replaced while the expression runs
    ("assigns it more than once", "helper = len\nhelper = str\n\ndef f(a):\n    x = g(a)\n    return helper(x)\n", "x"),
    ("assigns it more than once", "def swap():\n    global helper\n    helper = str\n\ndef f(a):\n    x = g(a)\n    return helper(x)\n", "x"),
    ("declared global or nonlocal", "def f(a):\n    h = len\n    def swap():\n        nonlocal h\n        h = str\n    x = swap()\n    return h(x)\n", "x"),
    ("yield, await", "def f(a):\n    x = yield a\n    return x\n", "x"),
    ("yield, await", "def f(a):\n    x = (y := a)\n    return x\n", "x"),
    ("shares its lines", "def f(a):\n    x = a + 1; return x\n", "x"),
    ("shares its lines", "def f(a):\n    x = a + 1  # keep\n    return x\n", "x"),
    ("carries a comment", "def f(a):\n    x = [\n        a,  # first\n    ]\n    return x\n", "x"),
    ("can see variable names", "def f(a):\n    x = a + 1\n    return vars()\n", "x"),
    ("not set by a plain", "def f(a):\n    g = [x := a]\n    return x\n", "x"),
    ("nested scope", "def f(a):\n    return [x for x in a]\n", "x"),
    ("nested function or lambda", "def f(a):\n    x = a\n    return (lambda x: x)(1)\n", "x"),
])
def test_an_inline_that_could_change_behaviour_is_refused(why, source, name) -> None:
    with pytest.raises(inline.Refused, match=why):
        inline.inline_variable(source, "f", name)


def test_a_name_read_first_is_fine_when_the_file_binds_it_once() -> None:
    source = "def helper(v):\n    return v + 1\n\ndef f(a):\n    x = g(a)\n    return helper(x)\n"
    assert inline.inline_variable(source, "f", "x").endswith("def f(a):\n    return helper(g(a))\n")


def test_generated_functions_behave_the_same_after_either_action() -> None:
    rng = random.Random(20261112)
    operators = ["+", "-", "*", "//", "%", "<", "==", "and", "or"]

    def expression(names: list[str], depth: int = 0) -> str:
        if depth > 2 or rng.random() < 0.3:
            return rng.choice(names + [str(rng.randint(1, 9))])
        return "(%s %s %s)" % (expression(names, depth + 1), rng.choice(operators), expression(names, depth + 1))

    inlined = renamed = 0
    for _ in range(250):
        names, lines = ["a", "b", "c"], ["def f(a, b, c):"]
        for index in range(rng.randint(2, 6)):
            lines.append("    v%d = %s" % (index, expression(names)))
            names.append("v%d" % index)
        lines.append("    return %s" % expression(names))
        source = "\n".join(lines) + "\n"
        calls = ["f(%d, %d, %d)" % tuple(rng.randint(-5, 5) for _ in range(3)) for _ in range(5)]
        for variable in names[3:]:
            results = [rename.rename_local_variable(source, "f", variable, "renamed_" + variable)]
            renamed += 1
            try:
                results.append(inline.inline_variable(source, "f", variable))
                inlined += 1
            except inline.Refused:
                pass
            for result in results:
                for call in calls:
                    assert _call(result, call) == _call(source, call), (source, result, call)
    assert renamed > 800 and inlined > 50, (renamed, inlined)


# ----------------------------------------------------------------------------- the lessons and the bundle


@pytest.mark.parametrize("lesson", teach.LESSONS, ids=lambda lesson: lesson["action"])
def test_a_taught_value_occurs_once_in_its_program_and_only_as_data(lesson) -> None:
    program, request = teach.program_and_request(lesson)
    assert list(request) == list(lesson["parameters"])
    for value in request.values():
        assert program.count(value) == 1


def test_a_program_that_mentions_a_taught_value_twice_is_not_taught(monkeypatch, tmp_path) -> None:
    lesson = dict(teach.LESSONS[0])
    text = (teach.PROGRAMS / (lesson["action"] + ".py")).read_text(encoding="utf-8")
    (tmp_path / (lesson["action"] + ".py")).write_text(text + "\n# settle_q7 again\n", encoding="utf-8")
    monkeypatch.setattr(teach, "PROGRAMS", tmp_path)
    with pytest.raises(teach.LessonError, match="occurs 2 times"):
        teach.program_and_request(lesson)
    for not_a_string in ("settle_q7", "7"):
        (tmp_path / (lesson["action"] + ".py")).write_text(
            text.replace('"settle_q7"', not_a_string), encoding="utf-8")
        with pytest.raises(teach.LessonError, match="tuple of 4 string literals"):
            teach.program_and_request(lesson)


def test_every_skill_in_the_tracked_bundle_is_one_of_the_programs() -> None:
    bundle = json.loads(teach.BUNDLE.read_text(encoding="utf-8"))
    expected = {}
    for lesson in teach.LESSONS:
        program, request = teach.program_and_request(lesson)
        for sentence in lesson["said_as"]:
            generalized = compiler.anti_unify_workflow(
                sentence.format(**request), [{"layer": "confined_python_exec", "code": program}],
                {"kind": "stdout_equals", "expected": lesson["answers"].format(**request)})
            expected[generalized["goal_skeleton"]] = generalized["abstract_steps"]
    assert {skill["goal_skeleton"]: skill["abstract_steps"] for skill in bundle["skills"]} == expected
    assert bundle["skill_count"] == len(expected) == 4
    for skill in bundle["skills"]:
        (step,) = skill["abstract_steps"]
        assert step["layer"] == "confined_python_exec"
        request_line = next(line for line in step["code"].splitlines() if line.startswith("REQUEST = "))
        values = request_line.split("(", 1)[1].split(")", 1)[0].split(", ")
        # every value of the request is a hole inside a string literal ...
        assert sorted(value.strip('"') for value in values) == sorted(skill["param_order"])
        assert all(value.startswith('"') and value.endswith('"') for value in values)
        # ... and there is no hole anywhere else in the program
        assert not re.search(r"\?(?:str|path|num|url)\d", step["code"].replace(request_line, ""))


def test_the_tracked_bundle_imports_whole(tmp_path) -> None:
    report = compiler.import_workflow_bundle(teach.BUNDLE, db_path=tmp_path / "skills.sqlite")
    assert (report["accepted"], report["refused"]) == (4, 0), report


@needs_sandbox
def test_teaching_again_produces_the_tracked_bundle(tmp_path) -> None:
    report = teach.teach(tmp_path / "bundle.json")
    assert report["skill_count"] == 4
    assert (tmp_path / "bundle.json").read_bytes() == teach.BUNDLE.read_bytes(), \
        "the tracked bundle is not what the lessons teach: run canonical/tools/teach_actions_v1.py"


def test_a_skill_database_that_already_exists_receives_what_is_taught_later(monkeypatch, tmp_path) -> None:
    database, bundle = tmp_path / "skills.sqlite", tmp_path / "bundle.json"
    whole = json.loads(teach.BUNDLE.read_text(encoding="utf-8"))
    earlier = dict(whole, skills=whole["skills"][:1], skill_count=1)
    bundle.write_text(json.dumps(earlier), encoding="utf-8")
    monkeypatch.delenv("BRAIN_COMPILED_WORKFLOW_DB", raising=False)
    monkeypatch.setattr(compiler, "_default_workflow_db", lambda: database)
    monkeypatch.setattr(compiler, "default_workflow_bundle_path", lambda: bundle)

    def held() -> set[str]:
        monkeypatch.setattr(compiler, "_AUTO_SEEDED_DBS", set())      # a new process
        _, connection = compiler._connect_db()
        try:
            return {row[0] for row in connection.execute("SELECT skill_id FROM compiled_workflow_skills")}
        finally:
            connection.close()

    assert held() == {whole["skills"][0]["skill_id"]}
    bundle.write_text(json.dumps(whole), encoding="utf-8")            # more is taught
    assert held() == {skill["skill_id"] for skill in whole["skills"]}


# ----------------------------------------------------------------------------- through the front door


@pytest.fixture
def taught_door(monkeypatch, tmp_path):
    """The front door with a skill database seeded from the tracked bundle, and one file to work on."""
    database = tmp_path / "skills.sqlite"
    monkeypatch.setenv("BRAIN_COMPILED_WORKFLOW_DB", str(database))
    compiler.import_workflow_bundle(teach.BUNDLE, db_path=database)
    shutil.rmtree(SCRATCH, ignore_errors=True)
    SCRATCH.mkdir(parents=True)
    target = SCRATCH / "calc.py"
    target.write_text(MODULE, encoding="utf-8")
    count = [0]

    def ask(sentence: str, **extra):
        count[0] += 1
        return door.solve({"task_id": "TAUGHT_%d" % count[0],
                           "goal": sentence.replace("FILE", target.relative_to(ROOT).as_posix()), **extra})

    yield ask, target
    shutil.rmtree(SCRATCH, ignore_errors=True)


@needs_sandbox
def test_the_door_renames_a_variable_it_was_taught_to_rename(taught_door) -> None:
    ask, target = taught_door
    result = ask("rename the variable 'tmp' to 'product' in the function 'compute' in FILE")
    assert result.get("pass") is True, result.get("status")
    assert result["status"] == "PASS__COMPILED_WORKFLOW_SKILL"
    assert [receipt["confined"] for receipt in result["step_receipts"]] == [True]
    text = target.read_text(encoding="utf-8")
    assert text == MODULE.replace("tmp", "product")
    assert _call(text, "compute(3, 4)") == _call(MODULE, "compute(3, 4)")
    assert result["answer"].startswith("renamed the variable 'tmp' to 'product' in the function 'compute' in ")


@needs_sandbox
def test_the_door_inlines_a_variable_it_was_taught_to_inline(taught_door) -> None:
    ask, target = taught_door
    result = ask("inline the local variable 'total' in the function 'compute' in FILE")
    assert result.get("pass") is True, result.get("status")
    text = target.read_text(encoding="utf-8")
    assert text == MODULE.replace("    total = scaled + double(a)\n    return total\n", "    return scaled + double(a)\n")
    assert _call(text, "compute(3, 4)") == _call(MODULE, "compute(3, 4)")


@needs_sandbox
@pytest.mark.parametrize("sentence,reason", [
    ("rename the variable 'a' to 'left' in the function 'compute' in FILE", "a is a parameter of compute"),
    ("rename the variable 'tmp' to 'scaled' in the function 'compute' in FILE", "scaled is already used in compute"),
    ("rename the variable 'tmp' to 'x y' in the function 'compute' in FILE", "is not a name a variable can have"),
    ("inline the variable 'scaled' in the function 'compute' in FILE", "scaled is read 2 times"),
    ("inline the variable 'tmp' in the function 'missing' in FILE", "there is no function missing"),
])
def test_a_case_the_taught_action_declines_is_refused_with_its_reason(taught_door, sentence, reason) -> None:
    ask, target = taught_door
    result = ask(sentence)
    assert result.get("pass") is not True, result.get("status")
    assert target.read_text(encoding="utf-8") == MODULE
    declined = result.get("taught_action_declined") or []
    assert declined and reason in declined[0]["reason"], declined


@needs_sandbox
@pytest.mark.parametrize("sentence,extra", [
    ("do not rename the variable 'tmp' to 'product' in the function 'compute' in FILE", {}),
    ("rename the variable 'tmp' to 'product' in the function 'compute' in FILE and then delete FILE", {}),
    ("rename the variable 'tmp' to 'product' in the function 'compute' in FILE", {"route_memory_mode": "exclude"}),
    ("rename the variable 'tmp' to 'pro\"+__import__(\"os\").getcwd()+\"' in the function 'compute' in FILE", {}),
    ("rename the variable 'tmp' to 'product' in the function 'compute' in ../../outside.py", {}),
])
def test_what_was_not_taught_is_still_refused(taught_door, sentence, extra) -> None:
    ask, target = taught_door
    result = ask(sentence, **extra)
    assert result.get("pass") is not True, result.get("status")
    assert target.read_text(encoding="utf-8") == MODULE


@needs_sandbox
def test_without_the_lesson_the_same_sentence_is_refused(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("BRAIN_COMPILED_WORKFLOW_DB", str(tmp_path / "empty.sqlite"))
    shutil.rmtree(SCRATCH, ignore_errors=True)
    SCRATCH.mkdir(parents=True)
    target = SCRATCH / "calc.py"
    target.write_text(MODULE, encoding="utf-8")
    try:
        for index, sentence in enumerate((
            "rename the variable 'tmp' to 'product' in the function 'compute' in %s",
            "inline the variable 'tmp' in the function 'compute' in %s",
        )):
            result = door.solve({"task_id": "UNTAUGHT_%d" % index, "goal": sentence % target.relative_to(ROOT).as_posix()})
            assert result.get("pass") is not True, result.get("status")
            assert target.read_text(encoding="utf-8") == MODULE
    finally:
        shutil.rmtree(SCRATCH, ignore_errors=True)


@needs_sandbox
def test_recall_reports_why_a_matching_skill_did_not_complete(tmp_path) -> None:
    database = tmp_path / "skills.sqlite"
    compiler.import_workflow_bundle(teach.BUNDLE, db_path=database)
    world = tmp_path / "world"
    world.mkdir()
    (world / "calc.py").write_text(MODULE, encoding="utf-8")
    declined: list = []
    assert compiler.recall_and_execute_workflow(
        "inline the variable 'scaled' in the function 'compute' in calc.py",
        cwd=world, db_path=database, refusals=declined) is None
    assert len(declined) == 1 and "scaled is read 2 times" in declined[0]["reason"]
    nothing: list = []
    assert compiler.recall_and_execute_workflow("paint the fence", cwd=world, db_path=database, refusals=nothing) is None
    assert nothing == []
    assert (world / "calc.py").read_text(encoding="utf-8") == MODULE

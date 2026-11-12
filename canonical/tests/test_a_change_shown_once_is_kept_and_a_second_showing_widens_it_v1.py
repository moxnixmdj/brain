"""A change shown once is kept in a file, a second showing widens it, and it is repeated only where it was shown.

``canonical/swe_kernel/taught_actions/edit_by_example_v1`` works a change out from examples.  Until now the
example had to be handed over again with every request, one example was all it could read, and a rule was
applied to every piece of code of its form.  Measured on commits of projects the program was not developed on,
that last point wrote calls the new function does not accept (``yaml.safe_load(stream, Loader=...)``).

Pinned here:

* several examples are read as one: one changed place gives a rule about exactly that code, a second and
  different place gives the blank, and code any example left alone speaks against a rule that fits it;
* a rule is applied only to code that is about the same things (the same imports) and is used a way an
  example showed; a use that was not shown is refused with the line, and nothing is written;
* a lesson file holds the examples whole and says what they teach; what it says is checked against the
  examples at every use; nothing in it is ever run; a file that is not a lesson is never written over;
* a use that was not shown is left as it is only when the request says to leave the rest alone;
* one program serves four taught actions, and through the front door a change is remembered, widened and
  repeated inside the sandbox, with the action's own reason on every refusal.
"""
from __future__ import annotations

import ast
import json
import pathlib
import shutil

import pytest

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as compiler
from canonical.swe_kernel.taught_actions import edit_by_example_v1 as by_example
from canonical.tools import teach_actions_v1 as teach

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRATCH = ROOT / "canonical/astra_runtime/tmp/zq_k4_m8"
needs_sandbox = pytest.mark.skipif(
    compiler._sandbox_for_taught_programs() is None, reason="this machine cannot start the namespace sandbox")


def became(text: str, old: str, new: str) -> tuple[str, str]:
    assert old in text
    return text, text.replace(old, new)


ONE_PLACE = became("def unpaid(product):\n    return product == None\n", "== None", "is None")
OTHER_PLACE = became("def open_orders(order):\n    return [order.total == None, order.total == 0]\n", "== None", "is None")
WARN_A = became("import logging\nlogger = logging.getLogger(__name__)\n\n\ndef load(path):\n    logger.warn('no file %s', path)\n",
                ".warn(", ".warning(")
WARN_B = became("import logging\nlog = logging.getLogger('jobs')\n\n\ndef run(job):\n    log.warn('late %s', job)\n",
                ".warn(", ".warning(")
YAML_PLAIN = became("import yaml\n\n\ndef read(stream):\n    return yaml.load(stream)\n\n\ndef read_text(text):\n    return yaml.load(text)\n",
                    "yaml.load(", "yaml.safe_load(")
YAML_FULL_LEFT_ALONE = (
    "import yaml\n\n\ndef plain(a):\n    return yaml.load(a)\n\n\ndef trusted(c):\n    return yaml.load(c, Loader=yaml.FullLoader)\n",
    "import yaml\n\n\ndef plain(a):\n    return yaml.safe_load(a)\n\n\ndef trusted(c):\n    return yaml.load(c, Loader=yaml.FullLoader)\n")
YAML_TARGET = ("import yaml\n\n\ndef settings(handle):\n    return yaml.load(handle)  # ours\n\n\n"
               "def theirs(handle):\n    return yaml.load(handle, Loader=yaml.FullLoader)\n")
# `assertEquals` -> `assertEqual` is a name the standard library kept, and a kept name is no longer
# refused for another call shape: the callee is the same function, so `kept_under_an_old_name_v1`
# says there is nothing to be unsure about. The principle below is about a change between two
# *different* names, so the vehicle has to be one of those, and `self.thread.isAlive` ->
# `self.thread.is_alive` is one: a different method, not an alias of the old one.
EQUALS_TWO = became("import threading\n\n\nclass T:\n    def alive(self):\n"
                    "        return self.thread.isAlive()\n", "self.thread.isAlive", "self.thread.is_alive")
EQUALS_THREE = became("import threading\n\n\nclass U:\n    def wait(self, timeout):\n"
                      "        return self.thread.isAlive(timeout)\n", "self.thread.isAlive", "self.thread.is_alive")
EQUALS_NAMED = became("import threading\n\n\nclass V:\n    def state(self, extra):\n"
                      "        return self.thread.isAlive(extra='now')\n", "self.thread.isAlive", "self.thread.is_alive")
CLOCK = became("import time\n\n\ndef run(job):\n    started = time.clock()\n    job()\n    return time.clock() - started\n",
               "time.clock", "time.perf_counter")
JOIN = ("import os\n\n\ndef cache(root, name):\n    return os.path.join(root, name)\n\n\ndef log(base):\n    return os.path.join(base, 'run.log')\n",
        "import os\nfrom pathlib import Path\n\n\ndef cache(root, name):\n    return Path(root) / name\n\n\ndef log(base):\n    return Path(base) / 'run.log'\n")


KEPT_AS_IT_WAS = became("def unpaid(product, fee):\n    total = fee + 1\n    return product == None\n", "fee + 1", "fee + 2")


def rules(*examples: tuple[str, str]) -> list[str]:
    return [str(rule) for rule in by_example.learn_all(list(examples))]


def repeated(target: str, *examples: tuple[str, str]) -> str:
    return by_example.repeated(by_example.learn_all(list(examples)), target, "the examples")


# ----------------------------------------------------------------------------- several examples are read as one


def test_one_changed_place_is_a_rule_about_exactly_that_code_and_a_second_place_makes_it_general() -> None:
    assert rules(ONE_PLACE) == ["product == None -> product is None"]
    assert rules(ONE_PLACE, OTHER_PLACE) == ["?1 == None -> ?1 is None"]
    target = "def late(invoice, fee):\n    return invoice.paid == None or fee == 0\n"
    with pytest.raises(by_example.Refused, match="nothing in the file has the form"):
        repeated(target, ONE_PLACE)
    assert repeated(target, ONE_PLACE, OTHER_PLACE) == target.replace("== None", "is None")


def test_one_example_read_alone_gives_what_it_gave_before() -> None:
    for before, after in (ONE_PLACE, OTHER_PLACE, WARN_A, YAML_PLAIN, CLOCK, JOIN):
        assert [str(rule) for rule in by_example.learn(before, after)] == rules((before, after))
    assert rules(JOIN) == ["os.path.join(?1, ?2) -> Path(?1) / ?2"]


def test_what_one_example_left_alone_speaks_against_a_rule_from_another() -> None:
    assert rules(YAML_PLAIN) == ["yaml.load -> yaml.safe_load"]
    # The second example changes a plain call and leaves the call with a Loader as it was.  The rule about the
    # function alone would change that call too, so the rule takes in the whole call.
    assert rules(YAML_PLAIN, YAML_FULL_LEFT_ALONE) == ["yaml.load(?1) -> yaml.safe_load(?1)"]
    assert repeated(YAML_TARGET, YAML_PLAIN, YAML_FULL_LEFT_ALONE) == YAML_TARGET.replace(
        "yaml.load(handle)  # ours", "yaml.safe_load(handle)  # ours")


def test_examples_that_change_and_keep_the_very_same_code_are_refused_and_the_refusal_names_the_example() -> None:
    # Left alone inside a longer statement, the code only makes the rule take in its whole statement ...
    longer = became("def unpaid(product, fee):\n    return product == None or fee == 1\n", "fee == 1", "fee == 2")
    assert rules(ONE_PLACE, longer) == ["return product == None -> return product is None", "fee == 1 -> fee == 2"]
    # ... left alone as the very same statement, it contradicts the other example.
    with pytest.raises(by_example.Refused, match="line 2 of example 1 was changed, but the same code was left alone"):
        by_example.learn_all([ONE_PLACE, KEPT_AS_IT_WAS])
    whole = ("def f(a):\n    return a\n", "def f(a):\n    b = a\n    return b\n")
    with pytest.raises(by_example.Refused, match="of example 2 adds, removes or reshapes whole statements"):
        by_example.learn_all([ONE_PLACE, whole])
    with pytest.raises(by_example.Refused, match="of the example adds, removes or reshapes whole statements"):
        by_example.learn_all([whole])
    with pytest.raises(by_example.Refused, match="the two files of example 2 hold the same code"):
        by_example.learn_all([ONE_PLACE, (ONE_PLACE[0], ONE_PLACE[0])])


def test_the_rules_must_reproduce_every_example_not_only_the_first(monkeypatch) -> None:
    real, calls = by_example.rewrite, []

    def second_file_unchanged(found, text, *rest, **more):
        calls.append(text)
        return (text, 0) if text == OTHER_PLACE[0] else real(found, text, *rest, **more)

    monkeypatch.setattr(by_example, "rewrite", second_file_unchanged)
    with pytest.raises(by_example.Refused, match="do not reproduce example 2"):
        by_example.learn_all([ONE_PLACE, OTHER_PLACE])
    assert calls == [ONE_PLACE[0], OTHER_PLACE[0]]


# ----------------------------------------------------------------------------- where a rule is applied


@pytest.mark.parametrize("line,used", [
    ("x = yaml.load(stream, Loader=yaml.Loader)", "called with 1 argument and the keyword Loader"),
    ("x = yaml.load(stream, yaml.Loader)", "called with 2 arguments"),
    ("x = yaml.load()", "called with 0 arguments"),
    ("x = yaml.load(*parts)", "called with 0 arguments and unpacked arguments"),
    ("x = yaml.load(stream, **options)", "called with 1 argument and unpacked keywords"),
    ("reader = yaml.load", "not called"),
])
def test_a_use_no_example_showed_is_refused_with_its_line_and_nothing_is_changed(line, used) -> None:
    target = "import yaml\ny = yaml.load(first)\n%s\n" % line
    with pytest.raises(by_example.Refused) as refusal:
        repeated(target, YAML_PLAIN)
    said = str(refusal.value)
    assert said.startswith("line 3 of the file has yaml.load %s; the examples showed it called with 1 argument." % used), said
    assert "nothing was changed" in said and "show that use too, changed or left alone" in said


def test_a_refusal_names_every_use_that_was_not_shown() -> None:
    target = ("import yaml\ny = yaml.load(q)\nx = yaml.load(s, Loader=yaml.Loader)\ncb = yaml.load\n"
              "z = yaml.load(a, b)\nw = yaml.load(a, b, c)\nv = yaml.load(c, Loader=1)\n")
    with pytest.raises(by_example.Refused) as refusal:
        repeated(target, YAML_PLAIN)
    assert str(refusal.value).startswith(
        "line 3 of the file has yaml.load called with 1 argument and the keyword Loader "
        "(also line 4, not called; line 5, called with 2 arguments; and 1 more); "
        "the examples showed it called with 1 argument.")
    assert "show those uses too, changed or left alone" in str(refusal.value)


def test_asked_to_leave_the_rest_alone_the_uses_that_were_shown_are_changed_and_no_other() -> None:
    found = by_example.learn_all([YAML_PLAIN])
    target = "import yaml\na = yaml.load(one)\nb = yaml.load(two, Loader=yaml.Loader)\nc = yaml.load\nd = yaml.load(three)\n"
    with pytest.raises(by_example.Refused, match="line 3 of the file has yaml.load"):
        by_example.rewrite(found, target)
    assert by_example.rewrite(found, target, leave_unshown=True) == (
        "import yaml\na = yaml.safe_load(one)\nb = yaml.load(two, Loader=yaml.Loader)\nc = yaml.load\nd = yaml.safe_load(three)\n", 2)
    # A name the new code needs is no longer refused when the examples added its import: it is brought.
    assert by_example.rewrite(by_example.learn_all([JOIN]), "import os\nx = os.path.join(a, b)\n",
                              leave_unshown=True) == ("import os\nfrom pathlib import Path\nx = Path(a) / b\n", 1)
    only_unshown = "import yaml\nb = yaml.load(two, Loader=yaml.Loader)\n"
    assert by_example.rewrite(found, only_unshown, leave_unshown=True) == (only_unshown, 0)
    with pytest.raises(by_example.Refused, match="nothing in the file has the form"):
        by_example.repeated(found, only_unshown, "the lesson", leave_unshown=True)


def test_this_is_the_call_the_new_function_does_not_take() -> None:
    """The measured case.  Before this guard the edit was written, and ``yaml.safe_load`` has no ``Loader``."""
    import inspect
    yaml = pytest.importorskip("yaml")
    assert "Loader" not in inspect.signature(yaml.safe_load).parameters
    with pytest.raises(by_example.Refused, match="the keyword Loader"):
        repeated("import yaml\n\ndef load(stream):\n    return yaml.load(stream, Loader=yaml.Loader)\n", YAML_PLAIN)


def test_a_use_is_shown_when_any_example_showed_it() -> None:
    assert rules(EQUALS_TWO, EQUALS_THREE, EQUALS_NAMED) == ["self.thread.isAlive -> self.thread.is_alive"]
    target = ("import threading\n\n\nclass W:\n    def a(self):\n        return self.thread.isAlive()\n\n\n"
              "    def b(self, timeout):\n        return self.thread.isAlive(timeout)\n\n\n"
              "    def c(self, extra):\n        return self.thread.isAlive(extra='now')\n")
    with pytest.raises(by_example.Refused, match="line 10 of the file has self.thread.isAlive called with 1 argument"):
        repeated(target, EQUALS_TWO)
    with pytest.raises(by_example.Refused, match="line 14 of the file .* the keyword extra; the examples showed it "
                                                 "called with 0 arguments, called with 1 argument"):
        repeated(target, EQUALS_TWO, EQUALS_THREE)
    assert repeated(target, EQUALS_TWO, EQUALS_THREE, EQUALS_NAMED) == target.replace("isAlive", "is_alive")
    # Shown with no and with one argument is not shown with two ...
    with pytest.raises(by_example.Refused, match="called with 2 arguments"):
        repeated("import threading\n\n\nclass X:\n    def d(self):\n        return self.thread.isAlive(a, b)\n",
                 EQUALS_TWO, EQUALS_THREE)
    # ... and shown with two and with four is not shown with three: nothing between two showings is assumed.
    apart = became("import shapes\n\nflat = shapes.area(w, h)\nsolid = shapes.area(w, h, d, unit)\n", "shapes.area", "shapes.size")
    assert rules(apart) == ["shapes.area -> shapes.size"]
    with pytest.raises(by_example.Refused, match="called with 3 arguments; the examples showed it called with 2 arguments, "
                                                 "called with 4 arguments"):
        repeated("import shapes\n\nroom = shapes.area(x, y, z)\n", apart)


def test_a_rule_about_a_whole_call_does_not_ask_how_its_result_is_used() -> None:
    target = "import os\nfrom pathlib import Path\nhere = os.path.join(a, b)\nsize = len(os.path.join(c, d).parts)\n"
    assert repeated(target, JOIN) == "import os\nfrom pathlib import Path\nhere = Path(a) / b\nsize = len((Path(c) / d).parts)\n"
    keyword = became("import subprocess\nout = subprocess.run(cmd, universal_newlines=True)\nerr = subprocess.check_output(cmd, universal_newlines=True)\n",
                     "universal_newlines=True", "text=True")
    assert rules(keyword) == ["universal_newlines=True -> text=True"]
    assert repeated("p = Popen(a, b, c, universal_newlines=True, cwd=d)\n", keyword) == "p = Popen(a, b, c, text=True, cwd=d)\n"


@pytest.mark.parametrize("target", [
    "from schedule import time\n\n\ndef tick():\n    return time.clock()\n",                 # another module under that name
    "import time\n\n\ndef tick(time):\n    return time.clock()\n",                           # a parameter of that name
    "import time\n\n\ndef tick():\n    time = Meter()\n    return time.clock()\n",           # a variable of that name
    "class Meter:\n    def tick(self):\n        return self.time.clock()\n",                 # not that name at all
])
def test_code_that_reads_another_thing_by_the_same_name_is_not_what_the_rule_is_about(target) -> None:
    assert rules(CLOCK) == ["time.clock -> time.perf_counter"]
    with pytest.raises(by_example.Refused, match="nothing in the file has the form"):
        repeated(target, CLOCK)
    mixed = "import time\n\n\ndef a():\n    return time.clock()\n\n\ndef b(time):\n    return time.clock()\n"
    assert repeated(mixed, CLOCK) == mixed.replace("def a():\n    return time.clock()", "def a():\n    return time.perf_counter()")


def test_a_blank_that_stood_for_variables_does_not_stand_for_an_imported_module() -> None:
    assert rules(WARN_A) == ["logger.warn -> logger.warning"]
    assert rules(WARN_A, WARN_B) == ["?1.warn -> ?1.warning"]
    target = ("import logging\nimport warnings\nLOG = logging.getLogger()\n\n\ndef check(self, value):\n"
              "    warnings.warn('old %s', value)\n    LOG.warn('bad %s', value)\n    self.log.warn('odd %s', value)\n")
    assert repeated(target, WARN_A, WARN_B) == target.replace("LOG.warn(", "LOG.warning(").replace("self.log.warn(", "self.log.warning(")
    # ``warnings.warning`` does not exist; the first rule of blanks would have written it.
    import warnings
    assert hasattr(warnings, "warn") and not hasattr(warnings, "warning")
    # Shown on an imported object, the same blank does stand for one.
    shared = became("from app.log import logger\n\n\ndef load(path):\n    logger.warn('no file %s', path)\n", ".warn(", ".warning(")
    assert rules(shared, WARN_B) == ["?1.warn -> ?1.warning"]
    theirs = "from their.log import audit\n\n\ndef note(a):\n    audit.warn('seen %s', a)\n"
    assert repeated(theirs, shared, WARN_B) == theirs.replace(".warn(", ".warning(")
    with pytest.raises(by_example.Refused, match="nothing in the file has the form"):
        repeated(theirs, WARN_A, WARN_B)


@pytest.mark.parametrize("head,reason", [
    ("import os\nclass Path:\n    pass\n", "the change uses 'Path', which the examples get by `from pathlib import Path`"),
    ("import os\nfrom shapes import Path\n", "the change uses 'Path', which the examples get by `from pathlib import Path`"),
])
def test_a_name_the_new_code_brings_must_be_the_import_the_examples_used(head, reason) -> None:
    body = "\n\ndef report(out, day):\n    return os.path.join(out, day)\n"
    with pytest.raises(by_example.Refused, match=reason):
        repeated(head + body, JOIN)
    # A file that does not bind 'Path' at all gets the import the examples added, where it can be found.
    assert repeated("import os\n" + body, JOIN) == (
        "import os\nfrom pathlib import Path\n" + body.replace("os.path.join(out, day)", "Path(out) / day"))
    with pytest.raises(by_example.Refused, match="at line 5 of the file that name is something else"):
        repeated("import os\nfrom pathlib import Path\n\ndef report(out, day, Path):\n    return os.path.join(out, day)\n", JOIN)
    good = "import os\nfrom pathlib import Path\n" + body
    assert repeated(good, JOIN) == good.replace("os.path.join(out, day)", "Path(out) / day")


# ----------------------------------------------------------------------------- a lesson kept in a file


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def write(files: dict[str, str]) -> None:
        for name, text in files.items():
            (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / name).write_bytes(text.encode("utf-8"))

    return write


def run(capsys, *request) -> tuple[int, str]:
    code = by_example.main(request)
    return code, capsys.readouterr().out


def test_a_change_is_remembered_in_a_file_and_repeated_from_it(project, capsys) -> None:
    project({"shown/was.py": JOIN[0], "shown/is.py": JOIN[1],
             "report.py": "import os\nfrom pathlib import Path\n\ndef report(out, day):\n    return os.path.join(out, day + '.csv')\n"})
    assert run(capsys, "remember", ("kept/paths.lesson", "shown/was.py", "shown/is.py")) == (
        0, "remembered in kept/paths.lesson the way shown/was.py was changed into shown/is.py\n")
    held = json.loads(pathlib.Path("kept/paths.lesson").read_text(encoding="utf-8"))
    assert held["format"] == by_example.LESSON_FORMAT
    assert held["teaches"] == [{"change": "os.path.join(?1, ?2) -> Path(?1) / ?2",
                                "imports": {"Path": ["from pathlib import Path"], "os": ["import os"]}}]
    assert [(example["shown by"], "".join(example["before"]), "".join(example["after"])) for example in held["examples"]] == [
        ("shown/was.py -> shown/is.py", JOIN[0], JOIN[1])]
    # The example files are no longer needed.
    shutil.rmtree("shown")
    assert run(capsys, "repeat", ("report.py", "kept/paths.lesson")) == (0, "edited report.py the way kept/paths.lesson remembers\n")
    assert pathlib.Path("report.py").read_text(encoding="utf-8") == (
        "import os\nfrom pathlib import Path\n\ndef report(out, day):\n    return Path(out) / (day + '.csv')\n")
    code, said = run(capsys, "repeat", ("report.py", "kept/paths.lesson"))
    assert code == 3 and said.startswith("REFUSED: nothing in the file has the form the lesson changed")


def test_a_second_showing_is_added_and_the_lesson_then_says_more(project, capsys) -> None:
    project({"a/was.py": YAML_PLAIN[0], "a/is.py": YAML_PLAIN[1], "b/was.py": YAML_FULL_LEFT_ALONE[0],
             "b/is.py": YAML_FULL_LEFT_ALONE[1], "config.py": YAML_TARGET})
    assert run(capsys, "remember", ("yaml.lesson", "a/was.py", "a/is.py"))[0] == 0
    first = json.loads(pathlib.Path("yaml.lesson").read_text(encoding="utf-8"))
    assert first["teaches"] == [{"change": "yaml.load -> yaml.safe_load", "shown": ["called with 1 argument"],
                                 "imports": {"yaml": ["import yaml"]}}]
    code, said = run(capsys, "repeat", ("config.py", "yaml.lesson"))
    assert code == 3 and "line 9 of the file has yaml.load called with 1 argument and the keyword Loader" in said
    assert pathlib.Path("config.py").read_text(encoding="utf-8") == YAML_TARGET
    assert run(capsys, "remember", ("yaml.lesson", "b/was.py", "b/is.py"))[0] == 0
    second = json.loads(pathlib.Path("yaml.lesson").read_text(encoding="utf-8"))
    assert second["teaches"] == [{"change": "yaml.load(?1) -> yaml.safe_load(?1)", "imports": {"yaml": ["import yaml"]}}]
    assert [example["shown by"] for example in second["examples"]] == ["a/was.py -> a/is.py", "b/was.py -> b/is.py"]
    assert second["examples"][0] == first["examples"][0]
    assert run(capsys, "repeat", ("config.py", "yaml.lesson"))[0] == 0
    assert pathlib.Path("config.py").read_text(encoding="utf-8") == YAML_TARGET.replace(
        "yaml.load(handle)  # ours", "yaml.safe_load(handle)  # ours")


def test_the_rest_is_left_alone_only_when_the_request_says_so(project, capsys) -> None:
    project({"was.py": YAML_PLAIN[0], "is.py": YAML_PLAIN[1], "config.py": YAML_TARGET})
    assert run(capsys, "remember", ("yaml.lesson", "was.py", "is.py"))[0] == 0
    code, said = run(capsys, "repeat", ("config.py", "yaml.lesson"))
    assert code == 3 and "the keyword Loader" in said and pathlib.Path("config.py").read_text(encoding="utf-8") == YAML_TARGET
    assert run(capsys, "repeat_shown", ("config.py", "yaml.lesson")) == (
        0, "edited config.py the way yaml.lesson remembers and left the rest alone\n")
    assert pathlib.Path("config.py").read_text(encoding="utf-8") == YAML_TARGET.replace(
        "yaml.load(handle)  # ours", "yaml.safe_load(handle)  # ours")
    code, said = run(capsys, "repeat_shown", ("config.py", "yaml.lesson"))        # only the use that was not shown is left
    assert code == 3 and "nothing in the file has the form the lesson changed" in said


def test_an_example_is_kept_byte_for_byte(project, capsys) -> None:
    before = "# caf\u00e9\r\nimport time\r\nstart = time.clock()\r\nend = time.clock()  # \u2028 odd\r\nx = 1"     # no last newline
    project({"was.py": before, "is.py": before.replace("time.clock", "time.perf_counter")})
    assert run(capsys, "remember", ("odd.lesson", "was.py", "is.py"))[0] == 0
    raw = pathlib.Path("odd.lesson").read_bytes()
    assert raw.endswith(b"\n") and "caf\u00e9".encode("utf-8") in raw
    (example,) = json.loads(raw.decode("utf-8"))["examples"]
    assert "".join(example["before"]) == before and len(example["before"]) >= 5
    assert "".join(example["after"]) == before.replace("time.clock", "time.perf_counter")


@pytest.mark.parametrize("change,reason", [
    (lambda held: held["teaches"].__setitem__(0, {"change": "os.path.join(?1, ?2) -> Path(?1) / ?2"}), "says it teaches something other"),
    (lambda held: held["teaches"].clear(), "says it teaches something other"),
    (lambda held: held["examples"][0]["after"].__setitem__(5, "    return Path(root).joinpath(name)\n"), "says it teaches something other"),
    (lambda held: held["examples"][0]["after"].__setitem__(5, "    return Path(root) /\n"), "no longer give rules"),
    (lambda held: held["examples"][0].__setitem__("after", held["examples"][0]["before"]), "no longer give rules"),
    (lambda held: held.__setitem__("format", "ANOTHER"), "exists and is not a lesson file"),
    (lambda held: held["examples"].clear(), "exists and is not a lesson file"),
    (lambda held: held["examples"][0].__setitem__("before", "import os\n"), "exists and is not a lesson file"),
    (lambda held: held.pop("examples"), "exists and is not a lesson file"),
])
def test_a_lesson_that_says_one_thing_and_shows_another_is_not_used(project, capsys, change, reason) -> None:
    target = "import os\nfrom pathlib import Path\nhere = os.path.join(a, b)\n"
    project({"was.py": JOIN[0], "is.py": JOIN[1], "t.py": target, "more_was.py": CLOCK[0], "more_is.py": CLOCK[1]})
    assert run(capsys, "remember", ("p.lesson", "was.py", "is.py"))[0] == 0
    held = json.loads(pathlib.Path("p.lesson").read_text(encoding="utf-8"))
    change(held)
    tampered = json.dumps(held, indent=1).encode("utf-8")
    pathlib.Path("p.lesson").write_bytes(tampered)
    for request in (("repeat", ("t.py", "p.lesson")), ("remember", ("p.lesson", "more_was.py", "more_is.py"))):
        code, said = run(capsys, *request)
        assert code == 3 and reason in said, said
    assert pathlib.Path("t.py").read_text(encoding="utf-8") == target
    assert pathlib.Path("p.lesson").read_bytes() == tampered


@pytest.mark.parametrize("name,content,reason", [
    ("notes.txt", "keep me\n", "a lesson file's name ends in .lesson"),
    ("module.py", "x = 1\n", "a lesson file's name ends in .lesson"),
    ("kept.json", "{}\n", "a lesson file's name ends in .lesson"),
    ("words.lesson", "not json at all\n", "exists and is not a lesson file"),
    ("list.lesson", "[1, 2]\n", "exists and is not a lesson file"),
    ("../outside.lesson", None, "must be a path inside the project"),
    ("/tmp/zq_k4_m8_absolute.lesson", None, "must be a path inside the project"),
])
def test_a_file_that_is_not_a_lesson_is_never_written_over(project, capsys, name, content, reason) -> None:
    project({"was.py": CLOCK[0], "is.py": CLOCK[1], "t.py": "import time\nx = time.clock()\n"})
    if content is not None:
        project({name: content})
    for request in (("remember", (name, "was.py", "is.py")), ("repeat", ("t.py", name))):
        code, said = run(capsys, *request)
        assert code == 3 and reason in said, said
    if content is not None:
        assert pathlib.Path(name).read_text(encoding="utf-8") == content
    assert not pathlib.Path("/tmp/zq_k4_m8_absolute.lesson").exists()
    assert pathlib.Path("t.py").read_text(encoding="utf-8") == "import time\nx = time.clock()\n"


def test_what_a_lesson_refuses_leaves_it_as_it_was(project, capsys) -> None:
    project({"was.py": ONE_PLACE[0], "is.py": ONE_PLACE[1], "same.py": ONE_PLACE[0],
             "kept_was.py": KEPT_AS_IT_WAS[0], "kept_is.py": KEPT_AS_IT_WAS[1],
             "broken.py": "def f(:\n"})
    assert run(capsys, "remember", ("n.lesson", "was.py", "is.py"))[0] == 0
    kept = pathlib.Path("n.lesson").read_bytes()
    for before, after, reason in (("was.py", "is.py", "already holds this example"),
                                  ("kept_was.py", "kept_is.py", "the same code was left alone"),
                                  ("was.py", "same.py", "hold the same code"),
                                  ("was.py", "missing.py", "the example's second file does not exist"),
                                  ("broken.py", "is.py", "is not Python")):
        code, said = run(capsys, "remember", ("n.lesson", before, after))
        assert code == 3 and reason in said, said
        assert pathlib.Path("n.lesson").read_bytes() == kept
    code, said = run(capsys, "repeat", ("missing.py", "n.lesson"))
    assert code == 3 and "the file to edit does not exist" in said
    code, said = run(capsys, "repeat", ("was.py", "none.lesson"))
    assert code == 3 and "the lesson file does not exist" in said and not pathlib.Path("none.lesson").exists()
    code, said = run(capsys, "forget", ("n.lesson",))
    assert code == 3 and "does not know the action" in said


def test_nothing_in_a_lesson_is_ever_run(project, capsys) -> None:
    trap = "import pathlib\npathlib.Path('ran.txt').write_text('ran')\n"
    before = trap + "import time\nstart = time.clock()\nend = time.clock()\n"
    project({"was.py": before, "is.py": before.replace("time.clock", "time.perf_counter"),
             "t.py": trap + "import time\nlap = time.clock()\n"})
    assert run(capsys, "remember", ("t.lesson", "was.py", "is.py"))[0] == 0
    assert run(capsys, "repeat", ("t.py", "t.lesson"))[0] == 0
    assert not pathlib.Path("ran.txt").exists()
    assert pathlib.Path("t.py").read_text(encoding="utf-8") == trap + "import time\nlap = time.perf_counter()\n"


# ----------------------------------------------------------------------------- the lessons and the front door


def test_one_program_serves_five_taught_actions() -> None:
    mine = [lesson for lesson in teach.LESSONS if lesson.get("program", lesson["action"]) == "edit_by_example_v1"]
    assert sorted(lesson["does"] for lesson in mine) == ["edit", "remember", "repeat", "repeat_shown", "repeat_tried"]
    own_line = next(line for line in (teach.PROGRAMS / "edit_by_example_v1.py").read_text(encoding="utf-8").splitlines()
                    if line.startswith("REQUEST = "))
    for lesson in mine:
        program, request = teach.program_and_request(lesson)
        (line,) = [line for line in program.splitlines() if line.startswith("REQUEST = ")]
        assert ast.literal_eval(line.split("=", 1)[1].strip()) == (lesson["does"], tuple(lesson["first_request"].values()))
        assert request == lesson["first_request"] and tuple(request) == tuple(lesson["parameters"])
        assert program.replace(line, own_line) == (teach.PROGRAMS / "edit_by_example_v1.py").read_text(encoding="utf-8")
    skeletons = {skill["goal_skeleton"] for skill in json.loads(teach.BUNDLE.read_text(encoding="utf-8"))["skills"]}
    assert {"remember in ?path0 the way ?path1 was changed into ?path2",
            "remember in ?path0 also the way ?path1 was changed into ?path2",
            "edit ?path0 the way ?path1 remembers",
            "edit ?path0 the way ?path1 remembers and leave the rest alone",
            "edit ?path0 the way ?path1 remembers and try the rest with ?path2"} <= skeletons


def test_the_teaching_tool_compares_a_lesson_file_by_what_it_holds(tmp_path) -> None:
    (tmp_path / "kept.lesson").write_text('{\n "b": [1, 2],\n  "a": "x"}', encoding="utf-8")
    assert teach._differences(tmp_path, {"after_json": {"kept.lesson": {"a": "x", "b": [1, 2]}}}) == []
    assert teach._differences(tmp_path, {"after_json": {"kept.lesson": {"a": "x", "b": [1, 3]}}}) == ["kept.lesson"]
    assert teach._differences(tmp_path, {"after_json": {"none.lesson": {}}}) == ["none.lesson"]
    (tmp_path / "broken.lesson").write_text("{", encoding="utf-8")
    assert teach._differences(tmp_path, {"after_json": {"broken.lesson": {}}, "after": {"kept.lesson": "other"}}) == [
        "kept.lesson", "broken.lesson"]


@pytest.mark.parametrize("damage", [
    lambda lesson: lesson.__setitem__("first_request", dict(reversed(list(lesson["first_request"].items())))),
    lambda lesson: lesson["first_request"].pop(next(iter(lesson["first_request"]))),
    lambda lesson: lesson["first_request"].__setitem__(next(iter(lesson["first_request"])), 3),
    lambda lesson: lesson["first_request"].__setitem__(next(iter(lesson["first_request"])), "REQUEST"),
])
def test_a_lesson_whose_first_values_do_not_fit_its_program_is_not_taught(damage) -> None:
    import copy
    lesson = copy.deepcopy(next(lesson for lesson in teach.LESSONS if lesson.get("does") == "remember"))
    damage(lesson)
    with pytest.raises(teach.LessonError):
        teach.program_and_request(lesson)


@pytest.fixture
def taught_door(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAIN_COMPILED_WORKFLOW_DB", str(tmp_path / "skills.sqlite"))
    compiler.import_workflow_bundle(teach.BUNDLE, db_path=tmp_path / "skills.sqlite")
    shutil.rmtree(SCRATCH, ignore_errors=True)
    SCRATCH.mkdir(parents=True)
    count = [0]

    def ask(sentence: str, files: dict[str, str] | None = None):
        count[0] += 1
        for name, text in (files or {}).items():
            (SCRATCH / name).write_bytes(text.encode("utf-8"))
        return door.solve({"task_id": "KEPT_CHANGE_%d" % count[0],
                           "goal": sentence.replace("DIR", SCRATCH.relative_to(ROOT).as_posix())})

    yield ask
    shutil.rmtree(SCRATCH, ignore_errors=True)


def held(name: str) -> str:
    return (SCRATCH / name).read_text(encoding="utf-8")


@needs_sandbox
def test_through_the_door_a_change_is_remembered_refused_where_it_was_not_shown_widened_and_repeated(taught_door) -> None:
    files = {"was.py": YAML_PLAIN[0], "is.py": YAML_PLAIN[1], "more_was.py": YAML_FULL_LEFT_ALONE[0],
             "more_is.py": YAML_FULL_LEFT_ALONE[1], "tgt.py": YAML_TARGET}
    missing = taught_door("edit DIR/tgt.py the way DIR/kept.lesson remembers", files)
    assert missing.get("pass") is not True and "the lesson file does not exist" in str(missing.get("taught_action_declined"))

    remembered = taught_door("remember in DIR/kept.lesson the way DIR/was.py was changed into DIR/is.py")
    assert remembered.get("pass") is True and remembered["status"] == "PASS__COMPILED_WORKFLOW_SKILL", remembered.get("status")
    assert [receipt["confined"] for receipt in remembered["step_receipts"]] == [True]
    assert json.loads(held("kept.lesson"))["teaches"][0]["change"] == "yaml.load -> yaml.safe_load"

    refused = taught_door("edit DIR/tgt.py the way DIR/kept.lesson remembers")
    assert refused.get("pass") is not True and held("tgt.py") == YAML_TARGET
    assert "the keyword Loader" in str(refused.get("taught_action_declined")), refused.get("taught_action_declined")

    again = taught_door("remember in DIR/kept.lesson the way DIR/was.py was changed into DIR/is.py")
    assert again.get("pass") is not True and "already holds this example" in str(again.get("taught_action_declined"))

    widened = taught_door("remember in DIR/kept.lesson also the way DIR/more_was.py was changed into DIR/more_is.py")
    assert widened.get("pass") is True, widened.get("status")
    assert json.loads(held("kept.lesson"))["teaches"][0]["change"] == "yaml.load(?1) -> yaml.safe_load(?1)"

    for name in ("was.py", "is.py", "more_was.py", "more_is.py"):          # the lesson is all that is left of them
        (SCRATCH / name).unlink()
    done = taught_door("edit DIR/tgt.py the way DIR/kept.lesson remembers")
    assert done.get("pass") is True and done["status"] == "PASS__COMPILED_WORKFLOW_SKILL", done.get("status")
    assert [receipt["confined"] for receipt in done["step_receipts"]] == [True]
    assert held("tgt.py") == YAML_TARGET.replace("yaml.load(handle)  # ours", "yaml.safe_load(handle)  # ours")


@needs_sandbox
def test_through_the_door_the_rest_is_left_alone_when_the_sentence_says_so(taught_door) -> None:
    lesson = by_example.lesson_text([YAML_PLAIN], ["was.py -> is.py"]).decode("utf-8")
    refused = taught_door("edit DIR/tgt.py the way DIR/kept.lesson remembers", {"kept.lesson": lesson, "tgt.py": YAML_TARGET})
    assert refused.get("pass") is not True and held("tgt.py") == YAML_TARGET
    assert "line 9 of the file has yaml.load called with 1 argument and the keyword Loader" in str(refused.get("taught_action_declined"))
    done = taught_door("edit DIR/tgt.py the way DIR/kept.lesson remembers and leave the rest alone")
    assert done.get("pass") is True and done["status"] == "PASS__COMPILED_WORKFLOW_SKILL", done.get("status")
    assert [receipt["confined"] for receipt in done["step_receipts"]] == [True]
    assert held("tgt.py") == YAML_TARGET.replace("yaml.load(handle)  # ours", "yaml.safe_load(handle)  # ours")
    assert held("kept.lesson") == lesson


@needs_sandbox
@pytest.mark.parametrize("sentence", [
    "remember in DIR/kept.txt the way DIR/was.py was changed into DIR/is.py",
    "remember in DIR/tgt.py the way DIR/was.py was changed into DIR/is.py",
    "remember DIR/kept.lesson the way DIR/was.py was changed into DIR/is.py",
    "remember in DIR/kept.lesson how DIR/was.py became DIR/is.py",
    "edit DIR/tgt.py the way DIR/full.lesson teaches",
    "edit DIR/tgt.py the way DIR/full.json remembers",
    "edit DIR/tgt.py the way DIR/full.lesson remembers and leave the rest",
    "edit DIR/tgt.py the way DIR/full.lesson remembers but leave the rest alone",
    "edit everything the way DIR/full.lesson remembers",
])
def test_another_wording_or_another_kind_of_file_changes_nothing(taught_door, sentence) -> None:
    files = {"was.py": CLOCK[0], "is.py": CLOCK[1], "tgt.py": "import time\nlap = time.clock()\n", "kept.txt": "mine\n"}
    lesson = by_example.lesson_text([CLOCK], ["was.py -> is.py"]).decode("utf-8")
    files.update({"full.lesson": lesson, "full.json": lesson})
    result = taught_door(sentence, files)
    assert result.get("pass") is not True, result.get("status")
    assert {name: held(name) for name in files} == files
    assert sorted(path.name for path in SCRATCH.iterdir()) == sorted(files)


def test_without_the_lessons_the_door_refuses_the_sentences(taught_door, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("BRAIN_COMPILED_WORKFLOW_DB", str(tmp_path / "empty.sqlite"))
    monkeypatch.setattr(compiler, "default_workflow_bundle_path", lambda: tmp_path / "no_bundle.json")
    files = {"was.py": CLOCK[0], "is.py": CLOCK[1], "tgt.py": "import time\nlap = time.clock()\n",
             "full.lesson": by_example.lesson_text([CLOCK], ["was.py -> is.py"]).decode("utf-8")}
    for sentence in ("remember in DIR/kept.lesson the way DIR/was.py was changed into DIR/is.py",
                     "edit DIR/tgt.py the way DIR/full.lesson remembers"):
        result = taught_door(sentence, files)
        assert result.get("pass") is not True
    assert {name: held(name) for name in files} == files and not (SCRATCH / "kept.lesson").exists()

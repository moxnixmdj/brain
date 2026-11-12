"""A parameter is added with the default the sentence states, or it is not added.

Measured 2026-11-12 through the front door on main: "add a parameter 'unit' with the default 1 to the
function 'compute' in <file>" answered PASS and wrote ``unit=None``.  Eleven of fourteen wordings that
give a value did the same.  The binder read three spellings of a default and turned every other one
into ``None``, still labelled as stated.

Pinned here:

* a literal default is read in the usual wordings and written as stated;
* a sentence that gives no value keeps the adapter's own default, as before;
* a value this rule cannot read binds nothing, so the request is refused and the file is unchanged;
* the sibling row, whose default is ``None`` by its own law, does not answer a sentence that gives a value;
* a default other than ``None`` is refused when the body reads an attribute of the same name, because
  no edit keeps what existing calls compute.
"""
from __future__ import annotations

import pathlib
import shutil

import pytest

from canonical.runtime import declared_input_derivation_v1 as derivation
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime.bound_capabilities import python_source_add_parameter as adapter

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRATCH = ROOT / "canonical/astra_runtime/tmp/zq_w8_k3"
MODULE = '''import math


def compute(a, b, scale=2):
    tmp = a * b
    total = tmp + scale
    return math.floor(total)


def report(a, b):
    return "%d" % compute(a, b)
'''
LINE_TOTAL = '''def line_total(item):
    return item.price * item.qty
'''


@pytest.mark.parametrize("words,expected", [
    ("with the default 1 to the function f in a/b.py", ("stated", "1")),
    ("defaulting to 1 to the function f in a/b.py", ("stated", "1")),
    ("which defaults to True in a/b.py", ("stated", "True")),
    ("with default value 'kg' to the function f in a/b.py", ("stated", "'kg'")),
    ('with a default of "kg" to the function f in a/b.py', ("stated", '"kg"')),
    ("whose default is None to the function f in a/b.py", ("stated", "None")),
    ("with the default none to the function f in a/b.py", ("stated", "None")),
    ("(default: 0.5) to the function f in a/b.py", ("stated", "0.5")),
    (", default -1e-3, to f in a/b.py", ("stated", "-1e-3")),
    ("with 'kg' as the default to the function f in a/b.py", ("stated", "'kg'")),
    (", False by default, to the function f in a/b.py", ("stated", "False")),
    ("with the default 1. Then stop", ("stated", "1")),
    ("to the function f in a/b.py", ("none", None)),
    ("with a default value to the function f in a/b.py", ("none", None)),
    ("with a default in a/b.py", ("none", None)),
    ("with a sensible default to the function f in a/b.py", ("none", None)),
    ("with the default one to the function f in a/b.py", ("unread", "one to the function")),
    ("with the default DEFAULT_RATE to the function f in a/b.py", ("unread", "DEFAULT_RATE to the function")),
    ("with a default of [] to the function f in a/b.py", ("unread", "of [] to the")),
    ("with the default 1.5.2 to f in a/b.py", ("unread", "1.5.2 to f in")),
    (", off by default, to the function f in a/b.py", ("unread", "by default")),
])
def test_what_a_sentence_says_about_the_default(words, expected) -> None:
    assert derivation.stated_parameter_default("add a parameter unit " + words) == expected


def test_a_default_written_on_the_name_is_read() -> None:
    assert derivation.stated_parameter_default("add a parameter unit=1 to the function f in a/b.py") == ("stated", "1")
    assert derivation.stated_parameter_default("add a parameter 'unit' = true, to f in a/b.py") == ("stated", "True")


@pytest.fixture
def ask():
    shutil.rmtree(SCRATCH, ignore_errors=True)
    SCRATCH.mkdir(parents=True)
    target = SCRATCH / "calc.py"
    count = [0]

    def send(sentence: str, module: str = MODULE):
        count[0] += 1
        target.write_text(module, encoding="utf-8")
        result = door.solve({"task_id": "DEFAULT_%d" % count[0],
                             "goal": sentence.replace("FILE", target.relative_to(ROOT).as_posix())})
        return result, target.read_text(encoding="utf-8")

    yield send
    shutil.rmtree(SCRATCH, ignore_errors=True)


@pytest.mark.parametrize("sentence,signature", [
    ("add a parameter 'unit' with the default 1 to the function 'compute' in FILE", "def compute(a, b, scale=2, unit=1):"),
    ("add a parameter unit with the default 1 to the function compute in FILE", "def compute(a, b, scale=2, unit=1):"),
    ("add a parameter 'unit' defaulting to 1 to the function 'compute' in FILE", "def compute(a, b, scale=2, unit=1):"),
    ("add a parameter 'unit' with default value 'kg' to the function 'compute' in FILE", "def compute(a, b, scale=2, unit='kg'):"),
    ("add a parameter unit=1 to the function compute in FILE", "def compute(a, b, scale=2, unit=1):"),
    ("add a parameter 'verbose', False by default, to the function 'compute' in FILE", "def compute(a, b, scale=2, verbose=False):"),
    ("add a parameter 'unit' with a default of -0.5 to the function 'compute' in FILE", "def compute(a, b, scale=2, unit=-0.5):"),
    ("add a parameter 'unit' to the function 'compute' in FILE", "def compute(a, b, scale=2, unit=None):"),
    ("add a parameter 'unit' with a default value to the function 'compute' in FILE", "def compute(a, b, scale=2, unit=None):"),
])
def test_the_door_writes_the_default_the_sentence_states(ask, sentence, signature) -> None:
    result, after = ask(sentence)
    assert result.get("pass") is True, result.get("status")
    assert result.get("compiled_capability_id") == "python.source.add_parameter.v1"
    assert signature in after
    assert after == MODULE.replace("def compute(a, b, scale=2):", signature)


@pytest.mark.parametrize("sentence", [
    "add a parameter 'unit' with the default one to the function 'compute' in FILE",
    "add a parameter 'unit' with the default DEFAULT_RATE to the function 'compute' in FILE",
    "add a parameter 'verbose', off by default, to the function 'compute' in FILE",
    "add a parameter 'unit' with a default of [] to the function 'compute' in FILE",
])
def test_a_default_the_binder_cannot_read_is_refused_and_nothing_is_written(ask, sentence) -> None:
    result, after = ask(sentence)
    assert result.get("pass") is not True
    assert str(result.get("status")).startswith("FAIL")
    assert after == MODULE


def test_the_row_that_reads_an_attribute_still_answers_when_no_value_is_given(ask) -> None:
    result, after = ask("Add a parameter qty with a default value to the function line_total in FILE", LINE_TOTAL)
    assert result.get("pass") is True, result.get("status")
    assert after == ("def line_total(item, qty=None):\n"
                     "    return item.price * (qty if qty is not None else item.qty)\n")


@pytest.mark.parametrize("sentence", [
    "Add a parameter qty with the default 3 to the function line_total in FILE",
    "Add a parameter qty with a default of 3 to the function line_total in FILE",
])
def test_a_value_that_would_replace_an_attribute_the_body_reads_is_refused(ask, sentence) -> None:
    result, after = ask(sentence, LINE_TOTAL)
    assert result.get("pass") is not True
    assert after == LINE_TOTAL


def test_the_adapter_names_the_attribute_it_will_not_replace(tmp_path) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "calc.py").write_text(LINE_TOTAL, encoding="utf-8")
    request = {"source_root": "pkg/calc.py", "qualname": "line_total", "param_name": "qty", "output_path": "out.json"}
    with pytest.raises(RuntimeError, match="DEFAULT_OTHER_THAN_NONE_WOULD_CHANGE_EXISTING_CALLS:item.qty"):
        adapter.run({**request, "default_expr": "3"}, tmp_path)
    assert (tmp_path / "pkg" / "calc.py").read_text(encoding="utf-8") == LINE_TOTAL

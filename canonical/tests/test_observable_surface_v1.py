"""What the widened observer promises, and the ways it must be allowed to say no.

Each test states a claim that was measured on real pairs first, then pins it so it cannot regress.
The interesting tests here are the refusals: an observer that can only say "I saw something" is not
an observer, it is a mirror.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import observable_surface_v1 as surfaces   # noqa: E402


BEFORE = '''\
from typing import List, Optional


class Job:
    region = "us-east-1"

    def __init__(self, name):
        self.name = name
        self.count = 0

    def bump(self):
        self.count += 1
        return self.count

    def label(self) -> Optional[str]:
        return None


def helper(x: List[int]) -> Optional[int]:
    if not x:
        return None
    return 0
'''


def test_a_class_body_is_observable_where_a_single_function_is_not():
    """The reach claim, in the smallest form that can hold it.

    A file with no top-level function at all is unreachable to a reader that needs one. It is not
    unreachable to this one: the constructor is built from plain values, the state is read, and every
    zero-argument method is driven.
    """
    source = '''\
class Counter:
    def __init__(self):
        self.value = 0

    def bump(self):
        self.value += 1
        return self.value
'''
    assert not any(isinstance(node, __import__("ast").FunctionDef)
                   for node in __import__("ast").parse(source).body), "no top-level function here"

    observed = surfaces.observe(source)
    assert observed["surface_count"] >= 2
    assert "STATE:Counter" in observed["observed"]
    assert "METHOD:Counter.bump" in observed["observed"]
    # The state is a signature of the object, not an address.
    assert observed["observed"]["STATE:Counter"] == "{value=0}"


def test_an_annotation_change_is_invisible_to_execution_and_visible_to_the_declaration_surface():
    """The finding this instrument exists for.

    Python never evaluates a function's annotations when the function is called, so
    `Optional[str] -> str | None` cannot move any behaviour. It is still a real change, and it is
    most of what the corpus's edits are. The two verdicts must be reported separately.
    """
    after = BEFORE.replace("Optional[str]", "str | None").replace("List[int]", "list[int]")

    # Execution cannot tell them apart: the same calls take the same paths.
    from canonical.swe_kernel.observable_surface_v1 import path_of
    import types
    one, two = {}, {}
    exec(compile(BEFORE, "<a>", "exec"), one)          # noqa: S102
    exec(compile(after, "<b>", "exec"), two)           # noqa: S102
    assert isinstance(one["helper"], types.FunctionType)
    assert path_of(one["helper"], []) == path_of(two["helper"], [])

    comparison = surfaces.comparable(surfaces.observe(BEFORE), surfaces.observe(after))
    assert comparison["behaviour_differences"] == 0
    assert comparison["declaration_differences"] >= 2
    keys = {difference["key"] for difference in comparison["differing"]}
    assert "SIGNATURE:helper" in keys
    assert all(difference["surface"] == "declaration"
               for difference in comparison["differing"])


def test_it_can_say_there_is_no_difference():
    """A source compared with itself must produce nothing. An observer that always finds something
    is useless for deciding whether a lesson was copied faithfully."""
    comparison = surfaces.comparable(surfaces.observe(BEFORE), surfaces.observe(BEFORE))
    assert comparison["differing"] == []
    assert comparison["behaviour_differences"] == 0
    assert comparison["declaration_differences"] == 0


def test_a_changed_body_is_a_behaviour_difference_not_a_declaration_one():
    """The other direction, so the labelling cannot pass by only ever saying 'declaration'."""
    after = BEFORE.replace("    if not x:\n        return None\n    return 0",
                           "    total = len(x)\n    if not total:\n        return None\n    return 0")
    assert after != BEFORE, "the fixture must actually change"
    comparison = surfaces.comparable(surfaces.observe(BEFORE), surfaces.observe(after))
    assert comparison["behaviour_differences"] >= 1
    assert any(difference["surface"] == "behaviour" for difference in comparison["differing"])


def test_a_body_edit_that_keeps_the_same_lines_in_the_same_order_can_be_missed():
    """The honest limitation of observing a path instead of a value.

    `if not x:` and `if x is None or not x:` take the same branch on every plain input, so the
    executed line offsets are identical and the observation does not move. Measured on the corpus:
    this is why not one of the 44 real edits showed up as a behaviour-only difference. It is stated
    here rather than hidden, because a reader who assumes "behaviour was compared, therefore the
    behaviour is equal" would be wrong.
    """
    after = BEFORE.replace("if not x:", "if x is None or not x:")
    assert after != BEFORE
    comparison = surfaces.comparable(surfaces.observe(BEFORE), surfaces.observe(after))
    assert comparison["behaviour_differences"] == 0, (
        "if this ever starts reporting a difference, the observation got richer -- update the "
        "record rather than the test")
    assert comparison["declaration_differences"] == 0


def test_a_class_that_cannot_be_built_is_unreachable_and_never_agreement():
    """Two ways a class refuses to be driven, both reported as reasons, never as a match.

    A constructor that rejects every plain-value argument set cannot be instantiated; a base from an
    import carries behaviour the extracted module does not have. Both must appear in `unreachable`
    with a cause, because "no difference found" on an unbuilt object would be a fabrication.
    """
    rejects = '''\
class NeedsNetwork:
    def __init__(self, url):
        if not isinstance(url, str) or "." not in str(url):
            raise ValueError("a real url is required")
        self.url = url
'''
    observed = surfaces.observe(rejects)
    assert "STATE:NeedsNetwork" not in observed["observed"]
    assert any(entry["name"] == "NeedsNetwork" for entry in observed["unreachable"]), (
        observed["unreachable"])

    # An ABC with no abstract members really is constructible, so its state IS observable -- that is
    # not a flaw to hide. The honest refusal is a class that cannot be constructed at all.
    abstract = '''\
from abc import ABC, abstractmethod


class Shape(ABC):
    @abstractmethod
    def area(self):
        ...
'''
    observed = surfaces.observe(abstract)
    assert "STATE:Shape" not in observed["observed"]
    assert any(entry["name"] == "Shape" for entry in observed["unreachable"]), observed["unreachable"]


def test_a_module_that_will_not_import_is_reported_not_silently_observed():
    """A module that will not import is reported as such, and no executed surface is claimed.

    The already-committed reader (`oracle_active_on_new_pull_requests_20261114_v1._load`) compiles one
    top-level function's OWN source in isolation, so it never executes the module's imports and it
    never claimed to. The distinction matters anyway, because it decides what a difference means: a
    function read out of a module that will not import can show that its TEXT differs, and cannot show
    that the code behaves differently in the project. Strict mode says so; lenient mode says what it
    did instead of hiding it.
    """
    source = "import certainly_not_a_real_module_xyz\n\n\ndef f(x):\n    return x\n"
    strict = surfaces.observe(source)
    lenient = surfaces.observe(source, strict=False)

    # The declaration surface is read from the text, so it is honest about the shape either way.
    assert "SIGNATURE:f" in strict["observed"]
    # Strict mode claims no executed surface at all for a module that did not import.
    assert strict["ran"] == 0
    assert "WILL_NOT_EXECUTE" in strict["detail"]
    # Lenient mode does execute the definition, and says that is what it did -- the difference it
    # reports is about text, not behaviour, because the module itself never imported.
    assert lenient["ran"] >= 1
    assert lenient["strict"] is False
    assert strict["strict"] is True


def test_a_declaration_walk_reaches_module_fields_class_fields_and_local_declarations():
    """Three places a declaration can hide. All three were missed by the first version measured."""
    source = '''\
from typing import List


exclude_patterns: List[str] = []


class Command:
    options: List[str] = []

    def run(self, x: List[int]) -> None:
        local: List[str] = []
'''
    after = source.replace("List[", "list[")
    comparison = surfaces.comparable(surfaces.observe(source), surfaces.observe(after))
    keys = {difference["key"] for difference in comparison["differing"]}
    assert "DECLARED_FIELD:exclude_patterns" in keys
    assert "DECLARED_FIELD:Command.options" in keys
    assert "DECLARED_FIELD:Command.run.local" in keys
    assert "SIGNATURE:Command.run" in keys


def test_one_spelling_kept_one_spelling_changed_so_a_faithful_copy_is_not_reported_wrong():
    """`typing.Optional` and `Optional` are the same spelling of the same thing; the import prefix is
    normalised. `Optional[X]` and `X | None` are different spellings and must stay different."""
    plain = "from typing import Optional\n\n\ndef f(x: Optional[int]) -> None:\n    return None\n"
    prefixed = plain.replace("x: Optional[int]", "x: typing.Optional[int]")
    spelled = plain.replace("x: Optional[int]", "x: int | None")

    same = surfaces.comparable(surfaces.observe(plain), surfaces.observe(prefixed))
    assert same["declaration_differences"] == 0

    different = surfaces.comparable(surfaces.observe(plain), surfaces.observe(spelled))
    assert different["declaration_differences"] >= 1

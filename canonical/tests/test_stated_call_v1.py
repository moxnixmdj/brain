"""One mechanism, five items: a construction call whose every part is DECLARED.

The claim under test is not "these five items pass". It is that the body can be written from
statements alone:

  * the return annotation declares the constructor        (PinJoint)
  * the prose states the argument paths verbatim          (parent.frame.x, -child.frame.x)
  * the type's own dir() declares the keyword members     (parent_point, child_point)

and that the pairing rule is the SHARED STEM, not a table. The negative test below is the
one that matters: if the mechanism only fires on `_point`, it is a lookup table wearing a
function's clothes.
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import shape_and_synonym_v1 as SS

STUB = ("from sympy.physics.mechanics import Body, PinJoint\n"
        "import sympy.physics.mechanics\n\n"
        "def custom_pinJoint(parent: sympy.physics.mechanics.Body, "
        "child: sympy.physics.mechanics.Body) -> sympy.physics.mechanics.PinJoint:\n"
        "    return ")

PROBLEM = ("Create a pin joint connecting two bodies. A PinJoint in the parent to be "
           "positioned at parent.frame.x with respect to the mass center, and in the child "
           "at -child.frame.x.")

MEMBERS = ["parent", "child", "parent_point", "child_point", "parent_axis", "child_axis",
           "joint_axis", "name", "coordinates", "speeds"]


def test_constructs_the_reference_body_from_statements_alone():
    out = SS.stated_call(STUB, PROBLEM, MEMBERS)
    assert out, "mechanism did not fire"
    assert out[0] == ("PinJoint('pin', parent, child, "
                      "parent_point=parent.frame.x, child_point=-child.frame.x)")


def test_pairs_on_the_shared_stem_not_on_a_member_table():
    """A DIFFERENT label over the same shape must work without any new code."""
    members = ["parent", "child", "parent_axis", "child_axis"]
    problem = "the joint should use parent.q.x and -child.q.x as its axis points"
    out = SS.stated_call(STUB, problem, members, label_suffix="_axis")
    assert out and "parent_axis=parent.q.x" in out[0]
    assert "child_axis=-child.q.x" in out[0]


def test_does_not_fire_when_the_paths_are_not_parameters():
    problem = "position it at some.frame.x and -other.frame.x"
    assert SS.stated_call(STUB, problem, MEMBERS) == []


def test_does_not_fire_without_a_declared_constructor():
    stub = STUB.replace("-> sympy.physics.mechanics.PinJoint", "-> list")
    assert SS.stated_call(stub, PROBLEM, MEMBERS) == []


def test_does_not_invent_a_member_when_the_type_has_none():
    assert SS.stated_call(STUB, PROBLEM, ["parent", "child"]) == []

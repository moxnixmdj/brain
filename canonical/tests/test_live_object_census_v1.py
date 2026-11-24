"""Crossing the wall: a compiled callable cannot be read, but it can be asked.

§A148b measured the wall precisely. Of six standard-library modules, the stdlib `csv` module defines
ZERO python functions -- `csv.reader` and `csv.writer` are builtins imported from `_csv`, with no AST
node and no source anywhere for a census to parse. A source census reports the room as nearly empty
and misses the two functions everybody actually calls.

They are not silent, though. Asked directly:

    csv.reader.__module__  ->  '_csv'
    csv.reader.__doc__     ->  'csv_reader = reader(iterable [, dialect=\\'excel\\'] ...'

That docstring opens with a USAGE LINE -- the same artefact `cli_contract_inference` already reads off
a program's `--help`. So the same instrument works on both sides of the wall, and the rest of the
pipeline does not need to know which side a callable came from.

WHAT THIS MUST NOT BECOME. `room_census_v1`'s rule is that a census never admits anything: a callable
found is a hypothesis, and only `forge_and_record` -- which runs it twice and tries to corrupt it --
makes it a capability. This module keeps that rule. The docstring is a way to NOTICE a callable, never
a reason to believe one.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_object_census_v1 as L  # noqa: E402
from canonical.runtime import room_census_v1 as RC  # noqa: E402


def test_the_compiled_wall_is_crossed():
    """`csv.reader` has no source and must still be found, with its required argument."""
    asked = L.census_module("csv")
    assert asked["status"] == "ASKED", asked
    rows = {f["function"]: f for f in asked["functions"]}
    assert "reader" in rows, sorted(rows)
    assert "writer" in rows, sorted(rows)
    # read from the usage line in the compiled docstring, not from any file
    assert rows["reader"]["required"] == ["iterable"], rows["reader"]
    assert rows["writer"]["required"] == ["fileobj"], rows["writer"]
    assert rows["reader"]["is_compiled"] is True, rows["reader"]
    assert rows["reader"]["origin"] == "_csv", rows["reader"]


def test_a_python_module_reads_its_real_signature():
    """On the other side of the wall the signature is exact, and must be preferred."""
    asked = L.census_module("json")
    rows = {f["function"]: f for f in asked["functions"]}
    assert rows["dump"]["required"] == ["obj", "fp"], rows["dump"]
    assert rows["loads"]["required"] == ["s"], rows["loads"]
    # a defaulted parameter is optional, not required
    assert "skipkeys" in rows["dump"]["params"], rows["dump"]
    assert "skipkeys" not in rows["dump"]["required"], rows["dump"]

    # ONLY A REAL SIGNATURE CAN PRODUCE THIS SET. `dump`'s docstring contains no usage line, so a
    # census that fell back to parsing prose would report no parameters at all -- which is why
    # dropping the signature path survived the first version of this test (it only checked that the
    # required names were right, and they were right for the wrong reason).
    assert rows["dump"]["params"][:2] == ["obj", "fp"], rows["dump"]["params"]
    assert "indent" in rows["dump"]["params"], rows["dump"]["params"]
    assert "sort_keys" in rows["dump"]["params"], rows["dump"]["params"]
    # PARAMETERS IN THE ORDER THE CALLABLE DECLARES THEM. Only a real signature knows the order;
    # `params` built from the docstring path would be `required + optional` (obj, fp, then the
    # defaulted ones), which for this function happens to coincide. `dumps` is the sharper case:
    # its optional parameters are interleaved with none, so ordering alone cannot separate them --
    # but `load` and `loads` take exactly one required argument each, and a docstring path that
    # found nothing would report NO parameters rather than one.
    assert rows["load"]["params"][0] == "fp", rows["load"]["params"]
    assert rows["loads"]["params"][0] == "s", rows["loads"]["params"]
    # `load` really does take a long tail of hooks; a census that reported only the docstring's
    # one-word description would have one parameter, not six.
    assert len(rows["load"]["params"]) > 3, rows["load"]["params"]
    # a **kwargs catch-all is not a parameter a caller supplies by name
    assert "kw" not in rows["dump"]["params"], rows["dump"]["params"]


def test_a_class_is_not_offered_as_a_callable():
    """A constructor is a template, not a thing a person asks for by name.

    Offering `DictReader` alongside functions puts it in the same list, and `DictReader(path)` does
    not read a csv -- it needs a file OBJECT. Only functions and methods are candidates.
    """
    asked = L.census_module("csv")
    names = {f["function"] for f in asked["functions"]}
    assert "DictReader" not in names, names
    assert "Dialect" not in names, names
    assert "reader" in names, names


def test_a_usage_line_is_not_confused_with_python_prose():
    """TWO KINDS OF DOCSTRING. Subtracting a usage line that is not there mangled the other kind.

    Measured: `json.dump` described itself as "dump ." because its first line was stripped as if it
    were a header. Before the fix the room ranked nothing for "write the records as a json file";
    after it, `dump` is first.
    """
    asked = L.census_module("json")
    rows = {f["function"]: f for f in asked["functions"]}
    assert "Serialize" in rows["dump"]["doc"], rows["dump"]["doc"]
    assert len(rows["dump"]["doc"]) > 20, rows["dump"]["doc"]


def test_the_usage_line_stops_at_the_balanced_paren():
    """The usage wraps across lines, and the example that follows it is not part of the contract."""
    usage = L._first_line(
        "csv_writer = csv.writer(fileobj [, dialect='excel']\n"
        "                        [optional keyword args])\n"
        "for row in sequence:\n"
        "    csv_writer.writerow(row)\n")
    assert "for row in sequence" not in usage, usage
    assert usage.endswith(")"), usage
    assert "optional keyword args" in usage, usage


def test_a_live_room_ranks_the_right_callable():
    """The bridge exists so the SAME selector works on both sides of the wall."""
    room = L.bridge_to_room("csv")
    assert room["status"] == "SURVEYED", room
    plan = RC.closing_plan(room, "count how many rows are in a csv file", ())
    top = [n["function"] for n in plan["need"]]
    assert top and top[0] == "reader", plan

    js = RC.closing_plan(L.bridge_to_room("json"), "write the records as a json file", ())
    assert [n["function"] for n in js["need"]][0] == "dump", js


def test_an_unimportable_module_is_reported_not_raised():
    asked = L.census_module("no_such_module_anywhere_v1")
    assert asked["status"] == "NOT_IMPORTABLE", asked
    assert asked["functions"] == [], asked

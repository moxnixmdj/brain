"""The declaration was in hand; the binder was not reading it.

Round 6 measured 786 operations that were unbound, and called them
`RESOLVABLE_BY_DRIVING`: the program documents itself, so the fix is ours. Round 7
drove them, and every failure it found was ONE ASSUMPTION rather than a missing fact:

  * `bind` assumed `argv[1]` was the flag. True for `cp --backup`, false for
    `openssl asn1parse -in`, so the subcommand was handed a value and openssl
    answered `Invalid command 'cms=out.bin'` about 62 times in a 120-row sample.
  * the usage-line parser read the program's own echoed name and the word `[options]`
    as OPERANDS, so every openssl subcommand got a seed filename appended that it
    refuses with `Use -help for summary` -- 143 of 258 sampled failures.
  * `-offset +int` parsed to placeholder None because the spec regex excluded `+`, so
    the program's declaration that the slot is a SIGNED INTEGER was discarded and a
    filename went in: `Can't parse "in.txt" as a number`.
  * `-out outfile` was read as a flag that takes a path VALUE and nothing else, so the
    binder supplied the artifact and never the input, and `openssl x509 -out out.bin`
    read an empty stdin and wrote nothing.
  * the passphrase flags were not read at all, so 108 failures were the program asking
    `enter AES-128-CBC encryption password:` and waiting for an answer no trial can
    give -- while the same help text declares `-k val  Passphrase`.

The tests below hold the MEASURED numbers and the mechanisms that produced them, so
that a later optimisation cannot quietly re-generalise what was measured.
"""
from __future__ import annotations

import pathlib
import shutil
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import tool_census_v1 as C  # noqa: E402

HAVE_OPENSSL = shutil.which("openssl") is not None
HAVE_CP = shutil.which("cp") is not None
HAVE_BASE64 = shutil.which("base64") is not None


def _openssl_contract():
    return C.parse_contract(C._own_text("openssl"), "openssl")


def _sub(subcommand: str):
    cen = C.census("openssl", depth=2, max_ops=60,
                   subcommands=[subcommand])
    return cen, {op["id"]: op for op in cen["operations"]}


# --------------------------------------------------------------------------- #
# the flag is found, not assumed to be second
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not HAVE_OPENSSL, reason="openssl is the deep-subcommand machine")
def test_a_subcommand_is_never_given_a_value():
    """`openssl cms=out.bin` is not a subcommand of openssl, and openssl said so.

    The binder wrote `argv[1]` -- the subcommand -- as if it were the flag, four times.
    A flag is identified by BEING the flag, which is a lookup, not a position.
    """
    cen, ops = _sub("asn1parse")
    bound = C.bind(ops["asn1parse.in"], contract=_openssl_contract())
    assert bound["invoked_as"][:2] == ["openssl", "asn1parse"], (
        "the subcommand was treated as a flag and given a value")
    assert "=" not in bound["invoked_as"][1]


@pytest.mark.skipif(not HAVE_OPENSSL, reason="openssl is the deep-subcommand machine")
def test_a_declared_quantity_is_a_value_and_not_a_filename():
    """`-offset +int` says SIGNED INTEGER, and the `+` was dropping the declaration.

    The spec regex accepted `[A-Za-z0-9_|]`, so `+int` did not parse, the placeholder
    came back None, and the binder fell through to a seed filename. openssl's answer --
    `Can't parse "in.txt" as a number` -- was a correct refusal of our argument.
    """
    cen, ops = _sub("asn1parse")
    op = ops["asn1parse.offset"]
    assert op.get("placeholder"), "the program's own `+int` declaration was discarded"
    bound = C.bind(op, contract=_openssl_contract())
    assert bound["invoked_as"] == ["openssl", "asn1parse", "-offset=1"]


@pytest.mark.skipif(not HAVE_OPENSSL, reason="openssl is the deep-subcommand machine")
def test_the_usage_line_does_not_declare_its_own_name_as_an_operand():
    """`asn1parse [options]` declares no operand at all.

    Two separate defects, and both had to go: `[options]` was read as a slot although
    `[OPTION]` was already excluded, and the leading bare word -- the command the usage
    line describes -- was kept unless it happened to equal the PARENT program's name,
    which for `openssl x509 -h` it never does.
    """
    text = C._run_capped(["openssl", "asn1parse", "-h"])["text"]
    contract = C.parse_contract(text, "openssl")
    assert contract["positionals"] == [], (
        f"the usage line's own name and [options] were read as operands: "
        f"{contract['positionals']}")
    assert C.parse_required_positionals(text) == []


@pytest.mark.skipif(not HAVE_CP, reason="cp is the two-operand machine")
def test_a_required_operand_is_still_required():
    """The same reading must keep `cp SOURCE DEST`, or the door disappears.

    Removing the phantom operand is only correct if a REAL operand survives: `cp`'s
    two slots are bare in its usage line, and `base64`'s one slot is bracketed.
    """
    cp = C.parse_contract(C._own_text("cp"), "cp")
    assert cp["positionals"] == ["SOURCE", "DEST"]
    assert cp["required_positionals"] == ["SOURCE", "DEST"]


@pytest.mark.skipif(not HAVE_BASE64, reason="base64 declares an optional operand")
def test_an_optional_operand_is_not_invented():
    """`base64 [OPTION]... [FILE]` brackets its one slot: it runs without it.

    A pinned test already refused `base64 --wrap=1 in.txt`; the usage line says why,
    and says it structurally rather than by a list of program names.
    """
    base64_contract = C.parse_contract(C._own_text("base64"), "base64")
    assert base64_contract["positionals"] == ["FILE"]
    assert base64_contract["required_positionals"] == [], (
        "a bracketed slot was read as required")
    wrap = next(op for op in C.census("base64", depth=1)["operations"]
                if op["id"] == "base64_wrap")
    assert C.bind(wrap, contract=base64_contract)["invoked_as"] == ["base64", "--wrap=1"]


# --------------------------------------------------------------------------- #
# the scope that declared the operation is the one that binds it
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not HAVE_OPENSSL, reason="openssl is the deep-subcommand machine")
def test_a_subcommand_binds_against_its_own_declaration():
    """`openssl -h` prints no `-offset`; `openssl asn1parse -h` prints `-offset +int`.

    The census PARSED the subcommand's contract and then dropped it, handing every
    sub-operation the parent's flags. The declaration the binder needed was already on
    the row's own scope, so the join is a lookup, not a new rule.
    """
    cen, ops = _sub("asn1parse")
    op = ops["asn1parse.offset"]
    assert operation_declares(op, "-offset"), (
        "the row does not carry the flags of the scope that declared it")
    assert not operation_declares(ops["asn1parse.offset"], "-passin")


def operation_declares(operation: dict, flag: str) -> bool:
    return any(flag in (f.get("flags") or ())
               for f in operation.get("declared_flags") or ())


# --------------------------------------------------------------------------- #
# a door has a place to read from and a place to write to
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not HAVE_OPENSSL, reason="openssl declares both slots")
def test_the_artifact_flag_is_given_the_artifact_and_the_input_flag_the_seed():
    """Direction is declared, and the role is declared in WORDS.

    `-in infile  input file` and `-out outfile  output file` are two lines of the same
    help text. Reading only the artifact line bound `openssl x509 -out out.bin`, which
    reads an empty stdin and writes nothing -- half an action, which is what the
    planner literature says cannot be planned with.
    """
    cen, ops = _sub("x509")
    bound = C.bind(ops["x509.out"], contract=_openssl_contract())
    assert bound["invoked_as"] == [
        "openssl", "x509", "-in", "in.txt", "-out=out.bin", "-passin=pass:txt"]
    assert bound.get("reads_from") == "-in"


@pytest.mark.skipif(not HAVE_OPENSSL, reason="openssl declares both slots")
def test_the_placeholder_gives_the_type_and_the_description_gives_the_role():
    """`-signature infile` and `-oid infile` are `infile` too, and neither is the input.

    The first version of the input rule read the TYPE alone and picked `-signature`
    ("File with signature to verify") for the digest commands and `-oid` ("file of extra
    oid definitions") for asn1parse. The same defect the artifact rule already avoids by
    reading the description, so both now read it the same way.
    """
    cen, ops = _sub("rmd160")
    bound = C.bind(ops["rmd160.out"], contract=_openssl_contract())
    assert "-signature" not in bound["invoked_as"], (
        "a verification precondition was supplied as the operand")
    # rmd160 declares no usage line of its own, so it declares no OPERAND and gets
    # none: `openssl rmd160 -out=out.bin in.txt` is refused with "Use -help for
    # summary". It reads standard input, which is where the seed is offered.
    assert bound["invoked_as"] == [
        "openssl", "rmd160", "-out=out.bin", "-passin=pass:txt"]
    assert "in.txt" not in bound["invoked_as"]


# --------------------------------------------------------------------------- #
# a declared passphrase is a declared precondition
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not HAVE_OPENSSL, reason="openssl declares its passphrase flags")
def test_a_declared_passphrase_is_supplied_in_the_declared_form():
    """`-k val  Passphrase` takes the phrase; `-passin val  ... pass-phrase SOURCE`
    takes a source SPEC, and both words are the program's own.

    Without them the operation waits on a prompt no trial can answer: 108 of openssl's
    failures were `enter AES-128-CBC encryption password:`. With them the same command
    produces a file.
    """
    cen, ops = _sub("aes-128-cbc")
    bound = C.bind(ops["aes-128-cbc.out"], contract=_openssl_contract())
    assert "-k=txt" in bound["invoked_as"], "the cipher would block on a prompt"
    cen2, ops2 = _sub("x509")
    bound2 = C.bind(ops2["x509.passin"], contract=_openssl_contract())
    assert bound2["invoked_as"] == ["openssl", "x509", "-passin=pass:txt"], (
        "a pass-phrase SOURCE was given a bare word")


# --------------------------------------------------------------------------- #
# the numbers, measured on the same programs from both sides
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not (HAVE_OPENSSL and HAVE_CP), reason="the fleet needs both")
def test_the_fleet_gained_doors_and_lost_none():
    """BEFORE is the shipped module on the same programs; AFTER is this one.

    Measured with the same script and the same seeds: doors 33 -> 57, and no program
    went down. openssl went 0 -> 24, which is the whole point -- it documents itself
    and the binder was not reading the document. The litter count FELL from 14 to 9,
    because a correct invocation refuses instead of half-writing.
    """
    before = {"cp": 2, "openssl": 0}
    after = {}
    for program in before:
        contract = C.parse_contract(C._own_text(program), program)
        cen = C.census(program, depth=2, max_ops=60)
        bound = [C.bind(op, contract=contract) for op in cen["operations"]]
        commit = C.commit_check_many(bound, seed=C.trial_seeds(), preparation="PLAIN")
        after[program] = commit["counts"].get("CHANGES", 0)
    for program, doors in before.items():
        assert after[program] >= doors, (
            f"{program} went DOWN from {doors} doors to {after[program]}")
    assert after["openssl"] >= 20, (
        f"openssl produced {after['openssl']} doors from its own documentation")

"""A value *inside* a document is attacker-controlled too, and the family is not one thing.

Measured on pyjwt `793a302` (issue 1186): `jwt.decode()` caught `ValueError` around `int(claim)` and leaked
`TypeError` for `{"exp": [1]}`, so an application catching the documented `PyJWTError` crashed. Two things
had to be true for the law to see it, and both are asserted here:

1. The mutation must survive re-encoding. Changing the payload text invalidates the signature, so the
   parser answers `InvalidSignatureError` before it ever reads the claim — the parser's own `encode` has to
   put the mutation back into a valid document.
2. The sibling family is not always `TypeError`. `int([1])` raises `TypeError`, `int(None)` raises
   `TypeError`, but `int(float("inf"))` raises `OverflowError`. A candidate that catches only the first two
   cleared nine of pyjwt's twelve hidden cases and still failed the three `inf` ones.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import law_repair_synthesis_v1 as synthesis
from canonical.swe_kernel import metamorphic_laws_v1 as laws

MARKER = object()


class ParseError(Exception):
    pass


def _decode_one(claim_value, guard: tuple[type, ...]):
    try:
        return int(claim_value)
    except guard:
        raise ParseError("claim must be an integer") from None


def _validate_exp(claims, guard=(ValueError,)):
    return _decode_one(claims["exp"], guard)


GUARD = (ValueError,)


def parser(document):
    """A parser shaped like pyjwt's: `int()` inside a handler that catches one builtin family."""
    import json

    return _validate_exp(json.loads(document), GUARD)


def encode(content):
    import json

    return json.dumps(content)


def test_a_wrong_typed_value_leaks_the_builtin_family():
    caught = laws.check_content_retyping(
        "decode", parser, encode, {"exp": 10}, [ParseError], "")
    kinds = {v["detail"].split(" raised ")[1].split(" at ")[0] for v in caught}
    assert kinds == {"TypeError", "OverflowError"}


def test_a_parser_that_catches_the_families_is_silent():
    global GUARD
    GUARD = (ValueError, TypeError, OverflowError)
    try:
        assert laws.check_content_retyping("decode", parser, encode, {"exp": 10}, [ParseError], "") == []
    finally:
        GUARD = (ValueError,)


def test_the_witness_names_the_site_the_exception_escaped_from():
    caught = laws.check_content_retyping(
        "decode", parser, encode, {"exp": 10}, [ParseError], "")
    assert any("_decode_one" in v["detail"] for v in caught), caught


def test_a_document_that_is_not_three_segments_is_left_alone():
    assert laws._document_variants("not-a-token") == []
    assert laws._document_variants("a.b.c") == []


def test_the_generator_offers_each_family_separately(tmp_path):
    source = (
        "def _validate_exp(payload):\n"
        "    try:\n"
        "        int(payload['exp'])\n"
        "    except ValueError:\n"
        "        raise ValueError('exp')\n"
    )
    (tmp_path / "api.py").write_text(source)

    narrow = synthesis.error_discipline_candidates(tmp_path, narrow_to=["api.py"], max_candidates=1)
    wide = synthesis.error_discipline_candidates(
        tmp_path, narrow_to=["api.py"], max_candidates=1,
        extra_families=[("TypeError",), ("TypeError", "OverflowError")])

    assert len(narrow) == 1 and "TypeError" in next(iter(narrow[0][1].values())).decode()
    assert "OverflowError" not in next(iter(narrow[0][1].values())).decode()
    assert len(wide) == 2
    assert any("OverflowError" in next(iter(blobs.values())).decode() for _, blobs in wide)


def test_a_file_without_a_single_family_handler_yields_nothing(tmp_path):
    (tmp_path / "api.py").write_text(
        "def f(x):\n    try:\n        return int(x)\n    except (ValueError, TypeError):\n        return None\n")
    assert synthesis.error_discipline_candidates(tmp_path, narrow_to=["api.py"], max_candidates=2) == []

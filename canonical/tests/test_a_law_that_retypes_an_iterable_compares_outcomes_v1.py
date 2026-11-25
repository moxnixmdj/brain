"""The iterable-retyping law, and the four ways it was wrong before it was right.

Each assertion here is a failure that was measured on more-itertools (`cca32949f1`, "fix last() when
__reversed__ is None"), not a shape invented for the test:

1. `hasattr(o, "__reversed__")` is true for an object whose protocol is present and set to `None`.
   `last()` took that branch, `reversed()` raised, and the function returned its default instead of the
   element. A list subclass never shows this (the `Sequence` path short-circuits), which is why the
   first probe found nothing.
2. Comparing "did it raise" is not a law: `last([])` is *supposed* to raise `ValueError`, so every
   retyped variant raised and the law fired on the healthy tree. It has to compare against the baseline.
3. A live iterator cannot be replayed even after copying: `all_unique(prepend(3, count()))` is answered
   at the duplicate, and the copy then holds the unbounded remainder. That run was OOM-killed.
4. A string is not a container of characters to retype, and a receiver is not data.
"""

from __future__ import annotations

import itertools
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import law_repair_synthesis_v1 as synthesis
from canonical.swe_kernel import metamorphic_laws_v1 as laws

MARKER = object()


def _last(iterable, default, present):
    """`more_itertools.last`, parameterised by how it reads the optional `__reversed__` protocol."""
    from collections import deque

    try:
        # The `Sequence` path comes first in the real code, and that is exactly why a list subclass
        # never reaches the `__reversed__` guard: the trigger is invisible to a list-shaped probe.
        if isinstance(iterable, (list, tuple, range)):
            return iterable[-1]
        if present(iterable):
            return next(reversed(iterable))
        return deque(iterable, maxlen=1)[-1]
    except (IndexError, TypeError, StopIteration):
        if default is MARKER:
            raise ValueError("last() was called on an empty iterable")
        return default


def buggy_last(iterable, default=MARKER):
    """`more_itertools.last` before the fix: `hasattr` is true for a protocol set to `None`."""
    return _last(iterable, default, lambda x: hasattr(x, "__reversed__"))


def fixed_last(iterable, default=MARKER):
    """After the fix: the protocol must be *callable*, not merely present."""
    return _last(iterable, default, lambda x: getattr(x, "__reversed__", None))


def test_a_none_valued_protocol_is_where_the_law_fires():
    caught = laws.check_iterable_retyping("last", buggy_last, ([1, 2, 3],))

    assert [v["law"] for v in caught] == ["iterable_retyping"]
    assert "none_reversed" in caught[0]["detail"]


def test_the_fixed_reading_of_the_same_protocol_is_silent():
    assert laws.check_iterable_retyping("last", fixed_last, ([1, 2, 3],)) == []


def test_an_input_that_is_supposed_to_raise_is_not_a_violation():
    """`last([])` raises `ValueError` on purpose; every variant raises too, and that is agreement."""
    assert laws.check_iterable_retyping("last", buggy_last, ([],)) == []


def test_a_lazy_result_is_the_same_answer_as_a_lazy_result():
    """`distinct_permutations` returns a live generator; its repr differs every call."""
    assert laws.check_iterable_retyping(
        "permutations", lambda x: itertools.permutations(x), ([1, 2, 3],)) == []


def test_a_string_is_not_retyped_into_an_iterator_of_its_characters():
    assert laws._iterable_variants("abc") == []
    assert laws._iterable_variants(b"abc") == []


def test_an_unbounded_iterable_is_not_materialised():
    """An infinite argument is left alone rather than guessed at (this run was once OOM-killed)."""
    assert laws._iterable_variants(itertools.count()) == []
    assert laws._iterable_variants(range(10**9)) == []


def test_a_live_iterator_is_never_replayed():
    """The copy would hold the *remainder* of the stream, which is not the argument that was observed."""
    from canonical.swe_kernel import metamorphic_plugin_v1 as plugin

    assert plugin._replay((itertools.count(),)) is None
    assert plugin._replay((itertools.chain([3], itertools.count()),)) is None
    copied = plugin._replay(([1, 2, 3],))
    assert copied == ([1, 2, 3],) and copied[0] is not None


def test_the_generator_turns_the_witness_into_the_guard(tmp_path):
    source = (
        "def last(iterable):\n"
        "    if hasattr(iterable, '__reversed__'):\n"
        "        return next(reversed(iterable))\n"
        "    return None\n"
    )
    (tmp_path / "mod.py").write_text(source)

    candidates = synthesis.protocol_presence_candidates(tmp_path, "last")

    assert len(candidates) == 1
    tag, blobs = candidates[0]
    assert "hasattr" in tag
    patched = next(iter(blobs.values())).decode()
    assert "getattr(iterable, '__reversed__', None)" in patched
    assert "hasattr" not in patched


def test_a_function_without_such_a_guard_yields_nothing(tmp_path):
    (tmp_path / "mod.py").write_text("def last(iterable):\n    return iterable[-1]\n")
    assert synthesis.protocol_presence_candidates(tmp_path, "last") == []

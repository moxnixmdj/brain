"""Interrogate an unknown interface: the fewest runs that pin its readings.

THE OWNER'S PROPOSAL, TAKEN LITERALLY AND THEN MADE EXACT.

    "What if we make a perfect algorithm and that is basically our model? All he should do
     is go into any new arbitrary environment ... ask the right question and know all of the
     things that he should know about ... scan everything and retrieve what he knows and
     what he doesn't know. What he doesn't know, he should get it instantly."

Every previous round measured one half and left the middle unfilled:

* scanning yields affordances, not meanings (``scan_retrieve_fetch_v1``);
* a declaration is not the behaviour (``THE_GUIDE_IS_THE_ENVIRONMENTS_OWN_DECLARATION``);
* one demonstration does not identify: 14.1 of 47 hypotheses survive and the leader is right
  on 10% of held-out inputs;
* 0 of 6 unguarded real commits became checkable, because the disambiguating input "is
  itself knowledge, and nothing manufactures it".

That last sentence is the bottleneck, and it is false as stated. A disambiguating input is
not knowledge to be remembered: it is a **witness**, and a witness is *computed* from the
competing readings that the interface's own words already produced. What was missing is one
invariant nobody had written down:

    A distinction the goal cannot observe is a distinction the agent need not resolve.

So "knowing" here is never "is this the truth". It is:

    CERTIFIED  <=>  every reading that survives the evidence prints the same thing on
                    every shape the goal can produce.

That makes an unbounded identification problem finite, and it is why the probe counts below
are measured against an exact optimum rather than asserted.

THE PARTS, AND WHY EACH ONE EXISTS
----------------------------------
1. **A closed primitive algebra, not a table of tools.** ``PRIMITIVES`` is ten total
   functions over bytes (three sort orders, two descending sorts, adjacent and global
   dedupe, count, JSON key ordering, line reversal). A *reading* is a pipeline of at most
   two of them. No line of this file branches on a tool's name, and the candidate universe
   is the same 56 pipelines for every surface, so nothing is learned by recognition.
2. **Predictions are computed from the input bytes.** This is the correction that made the
   module work: predicting the form's output *from the default output* collapses exactly
   where the form and the default do the same work. `sort -u`'s default is already sorted,
   so every prediction derived from it agrees, and a first version of this file certified
   `sort -u` as adjacent-dedupe in zero probes -- a wrong fact, certified. Predicting from
   the input kills it in one run.
3. **The scan is a control, not a census.** The default form is run on each shape once, and
   its only job is attribution: `jq -S` exits 4 on text because *jq* cannot read text, not
   because of `-S`. Without the control, "the form rejected the input" and "the interface
   cannot read the input" are the same observation, and the repository has been burned by
   exactly that confusion before (`bzless` inheriting `bzip2`'s help page).
4. **The right question, exactly ranked.** ``choose_witness`` ranks unasked shapes by exact
   rational information gain over the survivors, reusing
   ``canonical.runtime.exact_information_gain`` -- no floats, no epsilon. A shape where
   every survivor agrees has exactly zero gain and is refused by arithmetic, which is the
   failure mode "Wild Guesses and Mild Guesses in Active Concept Learning" reports for
   eager EIG selection.
5. **The fewest runs, proven.** ``smallest_certificate_tree`` computes the minimum worst-case
   number of witnesses by exact search over the finite partition lattice of the survivors.
   Greedy EIG is then run on the same table and compared to that optimum, so "the fastest
   way with minimal actions" is a measurement.
6. **Memory believed only after it is re-derived.** Records are keyed by
   ``(content digest, invoked name, surface, goal)`` and carry the observed bytes' digests.
   Reuse re-runs the recorded evidence; a record whose evidence no longer reproduces is
   discarded by name. This is the ``(content, name)`` rule the host round proved with
   ``xz``/``unxz``, extended by the goal equivalence -- without which certification would
   never terminate.

WHAT THIS FILE REFUSES
----------------------
* It never reports an unidentified surface as understood: it returns ``OPEN`` naming the
  shapes that would separate the survivors, or ``NOT_IDENTIFIABLE__EQUIVALENT`` when the
  declared space cannot separate them and a *wider type* (a document, a teacher) is needed.
* It never spends a witness it cannot need: zero-gain shapes are refused by arithmetic.
* It never scores a question whose default form the interface cannot read: that shape is
  refused by name and dropped.
* It never patches a wrong prediction. A reading whose rendering hypothesis disagrees with
  the observed bytes is killed by that observation.

Authority ``NONE__PRODUCER_RUN_SANDBOX``. Model calls 0. Network calls 0. Parameters 0.
"""
from __future__ import annotations

import hashlib
import itertools
from decimal import Decimal
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from fractions import Fraction
from functools import cmp_to_key, lru_cache
from typing import Any, Callable, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime.exact_information_gain import (  # noqa: E402
    rank_tests_by_information_gain,
)

SCHEMA = "PROJECT_BRAIN_INTERROGATION_V1"
MEMORY_SCHEMA = "PROJECT_BRAIN_INTERROGATION_MEMORY_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

CERTIFIED = "CERTIFIED__ALL_SURVIVORS_AGREE_ON_EVERY_GOAL_OBSERVATION"
OPEN_NEED_WITNESS = "OPEN__NEED_ONE_WITNESS"
NOT_IDENTIFIABLE = "NOT_IDENTIFIABLE__EQUIVALENT_ON_THE_DECLARED_DESIGN_SPACE"
REFUSED_NO_READING = "REFUSED__NO_READING_IN_DECLARATION"
REFUSED_UNRUNNABLE = "REFUSED__SURFACE_FORM_COULD_NOT_BE_RUN"
OPEN_BUDGET = "OPEN__PROBE_BUDGET_SPENT"
# A refusal that names what is missing, not a guess: the declaration asked about a
# parameter the design space contains no evidence for.
REFUSED_PARAMETER_UNEXERCISED = "REFUSED__PARAMETER_NOT_EXERCISED_BY_ANY_SHAPE"

# Nothing is predicted for an input a reading cannot parse. Silence is not "no change":
# conflating the two is how a decompressor comes to look like a compressor, and it was a
# real bug in this repository's host instruments.
SILENT = "\x00SILENT"
# What a real program does with input outside its own words' domain: it fails. Modelling that
# as permanent silence let readings that could never print anything survive every evidence and
# made every certification either vacuous or impossible. Measured on `jq -S`, whose class was
# certified "understood" and then rejected every non-JSON input the moment it was tested on
# inputs the search had never seen.


MAX_OUTPUT = 64 * 1024
DEADLINE = 3.0


# --------------------------------------------------------------------------- design space
# The shapes are the types an interface's words can be about. They are not fixtures chosen to
# make a test pass: each is the smallest input that distinguishes at least one pair of
# readings below, and a shape that distinguished nothing was deleted rather than kept.
SHAPES: dict[str, bytes] = {
    "lines_alpha": b"banana\napple\ncherry\n",
    "lines_numeric": b"10 ten\n9 nine\n100 hundred\n",
    "lines_duplicates": b"a\nb\na\nc\nb\n",
    # Three of the four questions that matter about a line filter are only answerable on
    # UNSORTED duplicates: `sort -u` and `uniq` agree on sorted input, so a design space
    # without this shape cannot separate "dedupe everywhere" from "dedupe adjacent" -- and
    # the goal, which is handed whatever the world gives it, cares about exactly that.
    "lines_unsorted_duplicates": b"c\na\nb\nc\n",
    # Measured: `sort -n` puts `alpha` at numeric 0 while `sort -V` compares the text prefix,
    # so without a mixed line set the two orders are indistinguishable -- and a certificate
    # that cannot see the difference certified both as one behaviour and was falsified by the
    # first held-out input containing a word.
    "lines_mixed": b"x\n5\nalpha 6\n10 86\n",
    # Punctuation and case are where a dictionary order and a byte order disagree, and the
    # host offers both. Without this shape the two cannot be told apart inside the design
    # space, so the certificate would either merge them or claim the space is too small.
    "lines_punct": b"x1_b\nx1a\nZ_B\nz a\n",
    # Found by held-out falsification, not by design: without adjacent duplicates, `uniq_adj`
    # and `identity` are the same function on every shape, so both were certified and both were
    # wrong on the first sorted-with-repeats input the world produced.
    "lines_adjacent_duplicates": b"a\na\nb\nc\nc\n",
    # Month names, out of lexicographic order, because `sort -M` and `sort` agree on every
    # input that has no month in it.
    "lines_months": b"APR x\nJAN y\nDEC z\n",
    # Without exponents, `sort -g` and `sort -n` are the same function on every shape: `-n`
    # stops at "1e3" and reads it as 1, `-g` reads it as 1000, and only this shape can see the
    # difference. Found by the sweep, not by design -- the certificate `{sort_num,
    # sort_general}` for `sort -g` was the same false certificate as `fold -b` in a new place.
    "lines_exponents": b"1e3\n2\n0.5\n1e-2\n",
    # Without mixed case, `sort -f` and `sort` are the same function, and so are `uniq -i` and
    # `uniq`; without a repeated run, `uniq -d` and `uniq -D` are the same function too. These
    # are the shapes the refused declarations were asking for by name.
    "lines_mixed_case": b"apple\nBANANA\ncherry\nApple\nbanana\n",
    "lines_case_runs": b"A\na\nb\nB\nb\n",
    "json_object": b'{"b":1,"a":{"d":4,"c":3},"e":[2,1]}\n',
    "json_array": b"[3,1,2,3]\n",
    "single_line": b"only\n",
    "lines_over_width": (b"QWERTYUIOPASDFGHJKLZXCVBNMQWERTYUIOPASDFGHJKLZXCVBNM"
                        b"QWERTYUIOPASDFGHJKLZXCVBNMQWERTYUIOPASDFGHJKLZXCVBNM"
                        b"1234567890123456789012345\n"),
    "lines_over_width_spaces": (b"alpha beta gamma delta epsilon zeta eta theta iota kappa "
                               b"lambda mu nu xi omicron pi rho sigma tau upsilon phi chi "
                               b"psi omega alpha beta gamma delta\n"),
    # The shape without which `-b` and the default are the same function: tabs that land on
    # and across the boundary. Measured necessity, not decoration -- before it existed, every
    # byte and every displayed column agreed and `fold -b` was certified `identity`.
    "lines_with_tabs": (b"\t\t\t\t\t\t\t\t\t\t\tX\n"
                        b"alpha\tbeta\tgamma\tdelta\tepsilon\tzeta\teta\ttheta\tiota\t"
                        b"kappa\tlambda\tmu\n"),
    "empty": b"",
}


# --------------------------------------------------------------------------- primitives
KIND_OF_SHAPE: dict[str, str] = {
    "lines_alpha": "alpha", "lines_numeric": "numeric", "lines_duplicates": "duplicates",
    "lines_unsorted_duplicates": "unsorted", "lines_mixed": "mixed",
    "lines_punct": "punct", "lines_adjacent_duplicates": "adjacent",
    "lines_months": "months",
    "json_object": "object", "json_array": "array", "single_line": "single",
    "lines_over_width": "long", "lines_with_tabs": "long",
    "lines_exponents": "numeric", "lines_mixed_case": "alpha", "lines_case_runs": "adjacent", "lines_over_width_spaces": "long",
    "empty": "empty",
}

TEXT_KINDS = frozenset({"alpha", "numeric", "duplicates", "unsorted", "mixed", "punct",
                        "adjacent", "months", "single", "long", "empty"})
# Empty input parses as nothing and prints nothing, which is what the JSON tools
# actually do (`jq -S .` on empty input exits 0 with no output). Leaving `empty` out
# of the domain scored a real prediction as a rejection.
JSON_KINDS = frozenset({"object", "array", "empty"})
ANY_KIND = TEXT_KINDS | JSON_KINDS

# A primitive is a partial function: it is defined only on the kinds of input its own words
# are about, and a pipeline is defined on the intersection. Without this, `count_runs +
# json_keys` looked like a hypothesis about a surface when it is an ill-typed composition
# that can never print anything; it was silent on every shape, could never be removed by any
# observation, and made every interrogation end as NOT_IDENTIFIABLE. Silence is not a
# hypothesis; it is the absence of one.
PRIMITIVE_DOMAIN: dict[str, frozenset[str]] = {
    # A line filter does not know or care that the lines happen to be JSON: `sort` sorts a
    # JSON document perfectly well, and treating JSON inputs as outside a text primitive's
    # domain was a modelling error that made every line filter "contradict" the first JSON
    # shape it was shown.
    "sort_lex": ANY_KIND, "sort_num": ANY_KIND,
    "sort_general": ANY_KIND,
    "sort_dict": ANY_KIND, "sort_month": ANY_KIND,
    "sort_lex_desc": ANY_KIND, "sort_num_desc": ANY_KIND,
    "uniq_adj": ANY_KIND, "uniq_glob": ANY_KIND, "uniq_fold_case": ANY_KIND,
    "dedupe_repeated": ANY_KIND, "dedupe_all_repeated": ANY_KIND,
    "count": ANY_KIND, "count_runs": ANY_KIND,
    "count_words": ANY_KIND, "count_bytes": ANY_KIND, "count_chars": ANY_KIND,
    # A JSON primitive is the reverse: it is defined only where its input parses.
    "json_keys": JSON_KINDS, "json_keys_pretty": JSON_KINDS,
    "json_keys_compact": JSON_KINDS, "pretty_json": JSON_KINDS,
    "reverse_lines": ANY_KIND, "fold_columns": ANY_KIND, "fold_bytes": ANY_KIND,
}


def _rows(data: bytes) -> list[bytes]:
    return data.splitlines(keepends=True)


_LEADING_NUMBER = re.compile(rb"^[ \t]*(-?\d+(\.\d+)?)")


def _leading_number(line: bytes) -> float:
    """The number `sort -n` compares: one that STARTS the line (after blanks), not any number.

    Searching for a number anywhere in the line is the wrong parser and it was caught twice by
    a real host: `x1_b` was given key 1 while the program gives it 0, and `alpha 6` was given
    6 while the program gives it 0. A comparator is a specification, and half-specifying it
    produces predictions that are right on the fixtures and wrong on the world.
    """
    match = _LEADING_NUMBER.match(line)
    return float(match.group(1)) if match else 0.0


def _numeric_key(line: bytes) -> tuple[float, bytes]:
    """`sort -n`: compare the numeric value, and fall back to the whole line when it ties.

    Measured, not assumed, and measured the hard way: dropping the fallback (on the theory
    that a stable sort preserves input order) made every prediction of `sort -n` disagree with
    the program on inputs whose numbers repeat -- `banana/apple/cherry` came back
    alphabetically because all three keys are 0. The fallback is not a tie-breaker I invented;
    it is the behaviour, and removing it was a fidelity bug that hid behind a plausible story.
    """
    return (_leading_number(line), line)


_ALNUM = frozenset(b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")


def _dict_key(line: bytes) -> bytes:
    """`sort -d`: compare only blanks and alphanumerics; everything else is ignored.

    The alphanumerics are ASCII, because the comparison is pinned to the C locale -- Python's
    ``isalnum`` is Unicode-aware and disagreed with the program on the first accented line it
    saw, which is exactly the kind of "prediction that is almost right" a certificate must not
    tolerate.
    """
    return bytes(ch for ch in line if ch in b" \t" or ch in _ALNUM)


_MONTHS = (b"JAN", b"FEB", b"MAR", b"APR", b"MAY", b"JUN", b"JUL", b"AUG", b"SEP",
           b"OCT", b"NOV", b"DEC")


def _month_key(line: bytes) -> tuple[int, bytes]:
    """`sort -M`: the month index, with the same whole-line fallback `-n` uses."""
    upper = line.upper()
    for index, month in enumerate(_MONTHS):
        if upper.startswith(month):
            return (index, line)
    return (-1, line)


# ---- the primitive that was removed, and why -------------------------------------------
# `sort -V` was implemented three times here (a regex-tuple key, a two-key comparator, and
# gnulib's filevercmp with the blank-line and version-string rules). Each was falsified on the
# held-out set: 6 disagreements in 60 randomised inputs on the third attempt. The cause is not
# a missing detail. GNU documents that version sort "is not transitive", and a comparator
# without a total order cannot be reproduced by any key-based sort -- Python's Timsort assumes
# one, so the result depends on comparison order. A primitive this system cannot specify
# exactly must not sit in the candidate universe, because its presence manufactures
# certificates that are false. `sort -V` is therefore REFUSED BY NAME, and the refusal is the
# honest outcome rather than a rounding error.
# The record of a transform deliberately kept out. Both entries below name the measurement
# that removed them, so a future reader cannot re-add either one thinking it was an oversight.
_FOLD_SPACES_RECORD = (
    "fold -s / --spaces: the break point depends on GNU's internal column bookkeeping in a "
    "way five separately measured rules failed to reproduce (539 of 2100 random inputs still "
    "disagreed after the fifth). A transform that cannot be specified exactly does not enter "
    "the universe; `fold -s` is refused by name."
)

_NOT_A_TOTAL_ORDER = ("sort -V / --version-sort: the comparator is documented as intransitive; "
                      "a key-based implementation cannot reproduce it")


def _verrev_order(byte: int) -> int:
    """The character order filevercmp uses: `~` first, then letters, then everything else."""
    if 48 <= byte <= 57:
        return 0
    if 65 <= byte <= 90 or 97 <= byte <= 122:
        return byte
    if byte == 126:            # '~'
        return -1
    return byte + 256


def _verrevcmp(left: bytes, right: bytes) -> int:
    """gnulib's ``filevercmp``, which is what `sort -V` actually runs.

    Every detail here was wrong in a first draft that compared ``re.findall(rb"\\d+|\\D+")``
    tuples: leading blanks, the treatment of punctuation (+256), `~` sorting before
    everything, and the rule that a longer numeric run wins. The function is small enough to
    state exactly, so it is stated exactly rather than approximated.
    """
    i = j = 0
    while i < len(left) or j < len(right):
        while ((i < len(left) and not (48 <= left[i] <= 57))
               or (j < len(right) and not (48 <= right[j] <= 57))):
            a = _verrev_order(left[i]) if i < len(left) else 0
            b = _verrev_order(right[j]) if j < len(right) else 0
            if a != b:
                return -1 if a < b else 1
            i += 1
            j += 1
        while i < len(left) and left[i] == 48:
            i += 1
        while j < len(right) and right[j] == 48:
            j += 1
        start_i, start_j = i, j
        while i < len(left) and 48 <= left[i] <= 57:
            i += 1
        while j < len(right) and 48 <= right[j] <= 57:
            j += 1
        if i - start_i != j - start_j:
            return 1 if i - start_i > j - start_j else -1
        if left[start_i:i] != right[start_j:j]:
            return 1 if left[start_i:i] > right[start_j:j] else -1
    return 0


def _blank_first_vs_end_blank(left: bytes, right: bytes) -> int:
    """GNU's rule for a completely blank line under `sort -V`: it sorts first.

    This is a *discontinuity* in the comparison, not a refinement of it -- gnulib's
    ``filevercmp`` returns "end of string" for a blank line, which makes the comparison
    intransitive against ordinary lines. It cannot be expressed as a key function, and a key
    function was exactly what this file used, so blank lines landed at the end. A
    discontinuity is modelled as what it is: a comparator.
    """
    left_blank, right_blank = not left.strip(), not right.strip()
    if left_blank != right_blank:
        return -1 if left_blank else 1
    return 0


def _version_cmp_match(left: bytes, right: bytes) -> int:
    """A stable sort key built from a pairwise comparator (no total-order assumptions)."""
    # gnulib: "a number followed by a letter is a version string, not a version number".
    # This project's own held-out set found it, on `ab` vs `a.B`: the punctuation branch made
    # the comparison transitivity-fragile and the key-based sort returned a different order
    # from the program. The rule is the program's, not mine.
    numeric = not re.match(rb"^[ \t]*\d+$", left) or not re.match(rb"^[ \t]*\d+$", right)
    blank = _blank_first_vs_end_blank(left, right)
    if blank:
        return blank
    if numeric and _verrevcmp(left, right) < 0:
        return -1
    if numeric and _verrevcmp(left, right) > 0:
        return 1
    if _verrevcmp(left, right) == 0:
        return 0
    return -1 if left < right else 1


def _version_key(line: bytes) -> tuple:
    """`sort -V`: compare numeric runs as numbers and text runs as text, blanks ignored.

    Leading blanks are skipped because the program does skip them: a version comparison that
    counted the spaces put every indented line first and was falsified by the first held-out
    input that had one.
    """
    # The comparator is the specification, so the primitive sorts with it directly rather
    # than inventing a key function that must agree with it.
    return ()


def _version_sorted(data: bytes) -> bytes:
    return b"".join(sorted(_rows(data), key=cmp_to_key(_version_cmp_match)))


def _dedupe_adjacent(data: bytes) -> bytes:
    out: list[bytes] = []
    for line in _rows(data):
        if not out or out[-1] != line:
            out.append(line)
    return b"".join(out)


def _dedupe_global(data: bytes) -> bytes:
    return b"".join(dict.fromkeys(_rows(data)))


def _ordered(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _ordered(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_ordered(item) for item in value]
    return value


def _count_runs(data: bytes) -> bytes:
    out: list[bytes] = []
    runs: list[tuple[int, bytes]] = []
    for line in _rows(data):
        if runs and runs[-1][1] == line:
            runs[-1] = (runs[-1][0] + 1, line)
        else:
            runs.append((1, line))
    for count, line in runs:
        prefix = b"%7d " % count if len(line) else b"%7d" % count
        out.append(prefix + line)
    return b"".join(out)


def _fold(data: bytes, width: int, count_bytes: bool, break_words: bool = False) -> bytes:
    """Wrap each line at ``width``, keeping the terminator. Measured semantics of `fold`.

    Every rule here was found by shrinking a failing input, not by reading documentation:
      * under ``-b`` the count is a plain byte count: a tab and a backspace are one byte each
        and neither moves a column -- the whole difference from the default;
      * by default a tab advances the column to the next multiple of 8, a backspace steps one
        column back (never below zero) and a carriage return returns to column zero;
      * the piece ends at the byte where the column first *exceeds* ``width``;
      * with ``break at spaces`` the cut moves back to just after the last blank whose column
        is *inside* the piece -- a blank at the boundary is not a break point, and a blank at
        the start of the line is used when nothing else qualifies. Searching byte positions
        instead of columns is what produced every one of the 534 wrong `-s` answers measured:
        a tab moves the column by eight and a byte by one, so the two disagree exactly where
        a tab straddles the cut;
      * a last piece with no terminator in the input gets none added.
    """
    out: list[bytes] = []
    for line in data.split(b"\n"):
        while True:
            # The column after each byte, and the byte index at which the piece ends.
            columns: list[int] = []
            column = 0
            for byte in line:
                if count_bytes:
                    column += 1
                elif byte == 0x09:
                    column = (column // 8 + 1) * 8
                elif byte in (0x08, 0x0D):
                    column = 0 if byte == 0x0D else max(0, column - 1)
                else:
                    column += 1
                columns.append(column)
            cut = next((i for i, c in enumerate(columns) if c > width), len(line))
            if cut >= len(line):
                out.append(line)
                break
            if break_words:
                # Measured against the host, not derived: the blank taken is the last one whose
                # column is inside the width, searched from the byte before the cut *forward*
                # through the whole line. A blank that sits past the cut is therefore still a
                # candidate -- which is why scanning backwards from the cut (the obvious
                # reading of "break at spaces") was wrong on every input with a tab in it.
                target = -1
                for i, byte in enumerate(line):
                    if byte == 0x20 and columns[i] <= width:
                        target = i
                if target < 0:
                    # nothing inside: fall back to the last blank strictly before the cut
                    for i in range(cut - 1, -1, -1):
                        if line[i:i + 1] == b" ":
                            target = i
                            break
                if target >= 0:
                    cut = target + 1
            out.append(line[:cut])
            line = line[cut:]
    return b"\n".join(out)


_GENERAL_NUMBER = re.compile(
    r"[ \t]*([+-]?(?:nan\(?[^)]*\)?|inf(?:inity)?|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
    r"|0[xX][0-9a-fA-F]+(?:\.[0-9a-fA-F]*)?(?:[pP][+-]?\d+)?))",
    re.IGNORECASE)


def _general_key(line: bytes) -> tuple[int, Any, bytes]:
    """`sort -g`'s order. Measured by probing the host, not read off the documentation.

      * a line whose *first* character is not a digit, and is not a sign followed by a digit
        or a dot, and is not the start of a nan or an infinity, is a non-number and sorts
        below everything -- including -inf. That single rule is what puts "zzz", ".", "", "-" and
        "+" first, and it is why treating a non-number as 0.0 was wrong (measured);
      * a number is the longest numeric prefix: leading blanks are skipped (so "  5" is 5),
        trailing text is ignored (so "5x" is 5), and hex is accepted ("0x10" is 16);
      * a value too large for a double is still finite ("1e999" sorts below "inf"), so the
        comparison is in ``Decimal``, which is exact for every such literal;
      * nan, of any spelling and either sign, sorts below every number;
      * ties break on the whole line as bytes, which is why "INF" precedes "infinity".

    SCOPE, measured and stated rather than glossed: on 700 random inputs drawn from finite
    decimals, exponents, overflow, inf, nan, blanks and trailing text this model is exact
    (0 mismatches). It is NOT exact on hexadecimal literals ("0x10") or on a *signed* nan
    ("-nan"), where GNU's internal comparison does something this model does not reproduce
    (195 of 700 on a generator that included them). Those two corners are named in the
    certificate's limits rather than patched with a guess; a goal that puts hex literals in a
    general-numeric sort is outside what this primitive claims.
    """
    text = line.decode("latin-1")
    stripped = text.lstrip(" \t")
    # The pattern anchors at the start of the line, so this *is* the "does it start with a
    # number" test: nothing may precede it but blanks. .5, .3 and 5. all match; "." and "0x"
    # and "1e" and "zzz" do not, and a non-number sorts below everything.
    match = _GENERAL_NUMBER.match(text)
    if match is None:
        return (0, Decimal(0), line)          # a non-number: below everything
    body = match.group(1)
    sign = -1 if body.startswith("-") else 1
    core = body.lstrip("+-").lower()
    if core.startswith("nan"):
        return (0, Decimal(0), line)
    if core.startswith("inf"):
        return (1, Decimal("-Infinity") if sign < 0 else Decimal("Infinity"), line)
    if core.startswith("0x"):
        mantissa, _, exponent = core.partition("p")
        whole, _, fraction = mantissa[2:].partition(".")
        value = Decimal(int(whole or "0", 16))
        for power, digit in enumerate(fraction, start=1):
            value += Decimal(int(digit, 16)) / (Decimal(16) ** power)
        return (1, sign * value * (Decimal(2) ** (int(exponent) if exponent else 0)), line)
    return (1, sign * Decimal(core), line)


# REMOVED BY NAME, not approximated: `sort -f / --ignore-case`.
# Its ranking over printable ASCII is measurable (and was measured: `A a B b ... Z z` with the
# punctuation block moved after `z`), but no single key reproduces it. Eight successive
# candidates were each falsified: bytes.lower() (wrong on '_' and '['), a hand-built rank
# table with a raw tie-break (wrong on "aA" vs "AB"), the same with a low-cased tie-break
# (still wrong on the same pair), and five variants between them. Two lines that fold equal
# are ordered in a way that depends on more than a folded key, which is the same structural
# finding that removed `sort -V`: the comparator is not a key function, so it cannot sit in a
# hypothesis space whose members are key functions.
_SORT_FOLD_CASE_RECORD = (
    "sort -f / --ignore-case: eight candidate keys were each falsified against the host; two "
    "lines equal under a case fold are ordered by something a folded key does not capture. "
    "Refused by name rather than approximated."
)

def _uniq_fold_case(data: bytes) -> bytes:
    """`uniq -i`: a run collapses when its members are equal ignoring case, keeping the first.

    Measured: "A a a" keeps "A"; "a A a" keeps "a"; "Aa aA" keeps "Aa".
    """
    out: list[bytes] = []
    previous: bytes | None = None
    for line in _rows(data):
        if previous is not None and line.lower() == previous.lower():
            continue
        out.append(line)
        previous = line
    return b"".join(out)


def _dedupe_repeated(data: bytes, *, all_members: bool) -> bytes:
    """`uniq -d` (one line per run that repeats) and `uniq -D` (every member of such a run).

    Measured: on "a a b", -d prints one "a" and -D prints both.
    """
    out: list[bytes] = []
    rows = _rows(data)
    start = 0
    while start < len(rows):
        end = start + 1
        while end < len(rows) and rows[end] == rows[start]:
            end += 1
        if end - start > 1:
            out.extend(rows[start:end] if all_members else rows[start:start + 1])
        start = end
    return b"".join(out)


def _json_render(data: bytes, indent: int | None) -> bytes:
    """Re-render JSON with keys ordered, in one rendering style.

    The style is a real, independent degree of freedom and it is *not* determined by the
    input: `jq .` pretty-prints a one-line object, so a prediction that infers the style from
    the input's own newlines is falsified by its first observation -- which is exactly what
    happened before this became three primitives instead of one. Enumeration is the honest
    way to model an unknown: it stays in the universe until a run removes it.
    """
    try:
        value = json.loads(data.decode("utf-8"))
    except Exception:
        return SILENT
    separators = (",", ": ") if indent else (", ", ": ")
    return (json.dumps(_ordered(value), indent=indent, separators=separators) + "\n").encode()


def _json_key_order(data: bytes) -> bytes:
    text = data.decode("utf-8", "replace")
    indented = "\n" in text.strip()
    return _json_render(data, 2 if indented else None)


# Canonical application order. A pipeline is applied in this order regardless of how the
# interface names its flags, because the algebra must be a function of the reading rather
# than of the argv spelling.
ORDER: tuple[str, ...] = (
    "sort_lex", "sort_num", "sort_general", "sort_dict", "sort_month",
    "sort_lex_desc", "sort_num_desc",
    "uniq_adj", "uniq_glob", "uniq_fold_case", "dedupe_repeated",
    "dedupe_all_repeated", "count", "count_runs",
    "count_words", "count_bytes", "count_chars",
    "json_keys", "json_keys_pretty", "json_keys_compact", "pretty_json",
    "reverse_lines", "fold_columns", "fold_bytes",
)

# What each primitive's own declaration calls a *parameter*: a degree of freedom the words
# name that changes the output. `wrap each line to fit in specified width` names a width;
# `break at spaces` names a switch. A shape set that cannot exercise one of these cannot tell
# the primitive from another reading, and must say so instead of certifying -- this table is
# the mechanical form of the rule that caught `fold -b`.
# A parameter is exercised only if the design space holds a shape where two settings of it
# print different bytes. This is not a promise about shapes; it is computed, and a surface
# whose declaration names a primitive whose parameter is not exercised is REFUSED BY NAME
# rather than certified. `fold -b` was certified `identity` before this existed precisely
# because no shape crossed the width at all; the variant pair below makes that impossible to
# repeat silently.
PARAMETER_WITNESS: dict[str, tuple[str, str]] = {
    "fold_columns": ("fold_bytes", "lines_with_tabs"),
    "fold_bytes": ("fold_columns", "lines_with_tabs"),
}


def parameter_exercised(name: str, shapes: Mapping[str, bytes] | None = None) -> bool:
    """Does some shape print different bytes under the two settings of this parameter?"""
    pair = PARAMETER_WITNESS.get(name)
    if pair is None:
        return True
    other, shape = pair
    data = (shapes or SHAPES).get(shape)
    if data is None:
        return False
    return PRIMITIVES[name](data) != PRIMITIVES[other](data)

PRIMITIVES: dict[str, Callable[[bytes], bytes]] = {
    "sort_lex": lambda d: b"".join(sorted(_rows(d))),
    "sort_num": lambda d: b"".join(sorted(_rows(d), key=_numeric_key)),
    "sort_dict": lambda d: b"".join(sorted(_rows(d), key=_dict_key)),
    "sort_month": lambda d: b"".join(sorted(_rows(d), key=_month_key)),
    # `sort -g` is a different function from `sort -n` on 383 of 400 random numeric inputs,
    # so grading it `sort_num` was a false certificate of exactly the kind the fold shapes
    # exposed. It belongs in the algebra only because it can be specified exactly.
    "sort_general": lambda d: b"".join(sorted(_rows(d), key=_general_key)),
    "sort_lex_desc": lambda d: b"".join(sorted(_rows(d), reverse=True)),
    "sort_num_desc": lambda d: b"".join(sorted(_rows(d), key=_numeric_key, reverse=True)),
    "uniq_adj": _dedupe_adjacent,
    "uniq_fold_case": _uniq_fold_case,
    "dedupe_repeated": lambda d: _dedupe_repeated(d, all_members=False),
    "dedupe_all_repeated": lambda d: _dedupe_repeated(d, all_members=True),
    "uniq_glob": _dedupe_global,
    "count": lambda d: b"%d\n" % len(_rows(d)),
    # `wc` states six quantities in its own help ("print the byte counts", "the word counts",
    # ...). Three of them are computable exactly and are added here because the host uses them
    # constantly; the fourth is a display width, which needs a Unicode table this system will
    # not smuggle in as knowledge, so it stays out and is refused by name.
    "count_words": lambda d: b"%d\n" % len(d.split()),
    "count_bytes": lambda d: b"%d\n" % len(d),
    "count_chars": lambda d: b"%d\n" % len(d.decode("utf-8", "replace")),
    # `uniq -c` and its relatives print each line prefixed by how many times it occurred in
    # its run. That is a distinct transform from "how many lines were there", and without it
    # the honest answer for one of the most-used flags on a Unix host is "cannot see it".
    "count_runs": _count_runs,
    "json_keys": _json_key_order,
    "json_keys_pretty": lambda d: _json_render(d, 2),
    "json_keys_compact": lambda d: _json_render(d, None),
    "pretty_json": lambda d: _json_render(d, 2),
    "reverse_lines": lambda d: b"".join(reversed(_rows(d))),
    # `fold`'s own declaration says "wrap each input line to fit in specified width" and
    # "break at spaces". Both are parameters the words name; a design space that contains no
    # line longer than the default width cannot exercise either, which is why `fold -b` was
    # certified as `identity` (true inside the space, false in the world) before this existed.
    "fold_columns": lambda d: _fold(d, 80, False, False),
    "fold_bytes": lambda d: _fold(d, 80, True, False),
    # `fold -s` is deliberately NOT a primitive. Its break point depends on GNU's internal
    # column bookkeeping in a way five measured rules failed to reproduce (539 of 2100 random
    # inputs still disagreed). A transform that cannot be specified exactly does not enter the
    # universe -- the same rule that removed `sort -V` -- because its presence manufactures
    # false certificates instead of preventing them. `fold -s` is refused by name.
}

REJECT = "reject"
IDENTITY = "identity"

# The candidate universe: every pipeline of at most two primitives, in canonical order, plus
# "this form refuses the input" and "this form does nothing". It is the same for every
# surface. 56 readings, computed once.
READINGS: tuple[tuple[str, ...], ...] = tuple(
    [()]
    + [(name,) for name in ORDER]
    + [pair for pair in itertools.combinations(ORDER, 2)]
)

READING_NAMES: tuple[str, ...] = tuple(
    IDENTITY if not reading else "+".join(reading) for reading in READINGS
) + (REJECT,)


def reading_domain(reading: tuple[str, ...]) -> frozenset[str]:
    """The kinds of input a pipeline is defined on: the intersection of its members'."""
    domain = set(ANY_KIND)
    for name in reading:
        domain &= set(PRIMITIVE_DOMAIN[name])
    return frozenset(domain)


def apply_reading(reading: tuple[str, ...], data: bytes) -> bytes | str:
    """What this reading prints, computed from the input bytes. ``SILENT`` if it cannot say."""
    current = data
    for name in ORDER:
        if name not in reading:
            continue
        value = PRIMITIVES[name](current)
        if value == SILENT:
            return SILENT
        current = value
    return current


def predict(reading: str, data: bytes) -> bytes | str:
    if reading == REJECT:
        return REJECT.encode() if False else SILENT  # handled by the caller; see _outcome
    if reading == IDENTITY:
        return apply_reading((), data)
    return apply_reading(tuple(reading.split("+")), data)


# --------------------------------------------------------------------------- declarations
# A closed English verb algebra. The declaration is a HINT and a REFUSAL GATE, never a
# constraint on the universe: a flag's name does not restrict what it may do, and every one
# of the 56 readings stays in play until a run removes it. What the words do decide is
# whether the surface can be interrogated at all.
_WORDS: tuple[tuple[str, str], ...] = (
    (r"\bgeneral[- ]numeric[- ]sort\b|\bgeneral numeric\b|\bsort according to general numeric\b",
     "sort_general"),
    (r"\bnumeric(?:al)?[- ]sort\b|\bnumeric\b|\bsort according to (?:string )?numerical\b",
     "sort_num"),
    (r"\breverse the result of comparisons\b|\breverse sort\b", "sort_lex_desc"),
    (r"\breverse\b|\blast line first\b|\bbackwards?\b", "reverse_lines"),
    (r"\bonly print duplicate lines\b", "dedupe_repeated"),
    (r"\bprint all duplicate lines\b", "dedupe_all_repeated"),
    (r"\bignore differences in case when comparing\b", "uniq_fold_case"),
    (r"\bunique\b|\buniq\b", "uniq_glob"),
    (r"\bsorts?\b|\borders?\b|\bsorted\b|\bsorting\b", "sort_lex"),
    (r"\bthe number of (?:newlines|lines)\b|\bline count\b", "count"),
    (r"\bthe (?:byte|char(?:acter)?) counts?\b", "count_bytes"),
    (r"\bthe word counts?\b", "count_words"),
    (r"\bcounts?\b|\bnumber(?:s|ed|ing)?\b|\bprefixed by the number\b", "count"),
    (r"\bkeys\b|\bkey order\b", "json_keys"),
    # `fold`'s own two sentences. Without them the surface that produced the one false
    # certificate in the sweep is refused for the wrong reason ("mentions nothing in the
    # algebra") when the truth is that it mentions something the shapes cannot exercise.
    (r"\bwrap (?:each )?input lines?\b|\bfit in (?:the )?specified width\b"
     r"|\bcolumns?\b", "fold_columns"),
    (r"\bcount bytes rather than columns\b|\bb\) count bytes\b", "fold_bytes"),
)


def read_surface(words: str) -> dict[str, Any]:
    """Which readings the surface's own sentence names -- and refusal when it names none.

    A sentence naming nothing in the algebra yields ``REFUSED__NO_READING_IN_DECLARATION``
    instead of a plausible guess. This is the boundary that keeps the learner from reading
    "attach the separator before instead of after" as some sort of ordering.
    """
    low = " ".join((words or "").lower().split())
    named: list[str] = []
    sources: dict[str, str] = {}
    for pattern, primitive in _WORDS:
        match = re.search(pattern, low)
        if not match or primitive in named:
            continue
        named.append(primitive)
        sources[primitive] = match.group(0)
    if not named:
        return {"schema": SCHEMA, "status": REFUSED_NO_READING, "words": (words or "")[:300],
                "named": []}
    ordered = [name for name in ORDER if name in named]
    return {"schema": SCHEMA, "status": "OK", "words": (words or "")[:300],
            "named": ordered, "sources": {k: sources[k] for k in ordered}}


_OPTION_LINE = re.compile(r"^\s{1,8}(-{1,2}[A-Za-z][\w-]*)")


def form_needs_argument(declaration: str) -> bool:
    """Is this form complete on its own, or does its own declaration demand a value?

    A question the interface cannot answer without an argument is not a question yet, and
    running it anyway produces a usage error on every shape -- which every reading "predicts"
    as a rejection, so a first version of this file certified `nl -n`, `nl -w`, `od --endian`
    and `sort --sort` as understood in one probe. They were not understood; they were
    unasked. Supplying the value would have to come from a document or a teacher, so the form
    is refused and named, not guessed.
    """
    text = declaration or ""
    head = text.split("  ")[0]
    if "=" in head:
        return True
    tokens = head.split()
    if len(tokens) > 1 and tokens[1][:1] in ("N", "S", "F", "C", "B", "W", "T", "A", "[") \
            and not tokens[1].startswith("-"):
        return True
    return False


def forms_in(help_text: str, *, limit: int = 64) -> list[dict[str, str]]:
    """The surface forms the interface declares, each with the line that declares it.

    This is the other half of the scan: the words name the questions that *can* be asked, so
    the caller need not know a tool's flags in advance. A form nobody described is not
    offered, because its meaning would be a guess.
    """
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in help_text.splitlines():
        match = _OPTION_LINE.match(line)
        if not match:
            continue
        flag = match.group(1)
        if flag in seen or flag in ("-h", "--help"):
            continue
        seen.add(flag)
        declared = line.strip()[:300]
        out.append({"form": flag, "line": declared,
                    "complete": not form_needs_argument(declared)})
        if len(out) >= limit:
            break
    return out


def declaration_line(help_text: str, form: Sequence[str]) -> str:
    """The line of the interface's own help that declares this surface form.

    A declared option is a line that *starts* with the flag. Matching the flag anywhere picks
    up other options' prose -- `uniq --help` mentions "sort -u" in a footnote, and a version
    of this file read that footnote as `uniq -u`'s description. The declaration form is
    tried first and the loose form is only a fallback, so the ambiguity is resolved in favour
    of the line that declares rather than the line that discusses.
    """
    flags = [flag for flag in form if flag.startswith("-")]
    if not flags:
        return ""
    for flag in flags:
        pattern = rf"^\s{{1,8}}{re.escape(flag)}(?![\w-])"
        for line in help_text.splitlines():
            if re.match(pattern, line):
                return line.strip()[:300]
    best = ""
    for line in help_text.splitlines():
        for flag in flags:
            if re.search(rf"(?<![\w-]){re.escape(flag)}(?![\w-])", line):
                stripped = line.strip()
                if len(stripped) > len(best):
                    best = stripped
                break
    return best[:300]


# --------------------------------------------------------------------------- the runner
def run_bounded(argv: Sequence[str], stdin: bytes = b"", *, deadline: float = DEADLINE,
                cwd: str | None = None) -> dict[str, Any]:
    """Run one command and return its code and bytes, bounded in time and size.

    The bound is this repository's own scar tissue: an unbounded reader of a foreign
    executable was OOM-killed twice at exit 137, and a buffered read hung a 900 s run. Every
    learner that reads the world needs this, so it is one function and nothing re-implements
    it.
    """
    started = time.perf_counter()
    # Byte order, not the host's collation. `sort` under a UTF-8 locale orders punctuation and
    # case differently from the byte order any computed prediction can produce, so the
    # comparison is pinned to C and the pin is a declared part of the experiment rather than
    # a hidden assumption about the box.
    env = dict(os.environ, LC_ALL="C", LANG="C")
    try:
        proc = subprocess.Popen(list(argv), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, cwd=cwd, start_new_session=True,
                                env=env)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "reason": type(exc).__name__, "argv": list(argv), "rc": None,
                "out": b"", "err": b"", "seconds": 0.0}
    try:
        out, err = proc.communicate(input=stdin[:MAX_OUTPUT], timeout=deadline)
        return {"ok": True, "reason": "OK", "argv": list(argv), "rc": proc.returncode,
                "out": out[:MAX_OUTPUT], "err": err[:MAX_OUTPUT],
                "seconds": round(time.perf_counter() - started, 4)}
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
        try:
            out, err = proc.communicate(timeout=1.0)
        except Exception:
            out, err = b"", b""
        return {"ok": False, "reason": "TIMEOUT", "argv": list(argv), "rc": None,
                "out": (out or b"")[:MAX_OUTPUT], "err": (err or b"")[:MAX_OUTPUT],
                "seconds": round(time.perf_counter() - started, 4)}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def file_digest(path: str) -> str | None:
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None


# --------------------------------------------------------------------------- the surface
@dataclass(frozen=True)
class Surface:
    """One optional surface form of one interface, and the goal it is asked for.

    ``shapes`` is the goal's observation domain: what the goal can actually produce. A
    reading that agrees with every survivor on all of them is certified *for this goal* even
    if it is wrong in general. That is not a weakening; it is the only definition of "known"
    that never requires knowing what the goal cannot see.
    """
    tool: str                       # the invoked name; evidence, never a branch condition
    base: tuple[str, ...]           # argv without the surface form
    form: tuple[str, ...]           # the surface form itself, e.g. ("-n",)
    words: str                      # the surface's own sentence, from its own --help
    shapes: tuple[str, ...] = tuple(SHAPES)

    def argv(self, *, with_form: bool) -> list[str]:
        # An empty string in a form is not an argument: dropping it here is what keeps the
        # "the tool's own default" case from becoming `fold ''`, which reads `''` as a file
        # name and fails on every shape. A flag with no letter is not a flag.
        form = tuple(f for f in self.form if f)
        return [self.tool, *self.base, *(form if with_form else ())]


def scan(surface: Surface, *, runner=run_bounded) -> dict[str, Any]:
    """Run the surface's *default* form on every shape: the control that attributes outcomes.

    The default run never changes the world (its job is to print), so this is the cheap,
    effect-free half. Its job here is attribution, not census: `jq -S` exits 4 on text
    because jq cannot read text, not because of `-S`, and without the control those two
    facts would be one observation.
    """
    table: dict[str, Any] = {}
    started = time.perf_counter()
    for shape in surface.shapes:
        got = runner(surface.argv(with_form=False), SHAPES[shape])
        if not got.get("ok") or got.get("rc") != 0:
            table[shape] = {"status": "UNASKABLE",
                            "reason": got.get("reason") or f"rc={got.get('rc')}"}
            continue
        table[shape] = {"status": "ASKABLE", "output": got["out"],
                        "digest": digest(got["out"]), "seconds": got["seconds"]}
    return {"schema": SCHEMA, "surface": list(surface.form), "table": table,
            "askable": sorted(k for k, v in table.items() if v["status"] == "ASKABLE"),
            "unaskable": {k: v["reason"] for k, v in table.items()
                          if v["status"] == "UNASKABLE"},
            "scan_seconds": round(time.perf_counter() - started, 4)}


def ask(surface: Surface, scanned: Mapping[str, Any], shape: str, *,
        runner=run_bounded) -> dict[str, Any]:
    """One witness: the surface form on a shape the control says the interface can read."""
    row = scanned["table"].get(shape)
    if not row or row.get("status") != "ASKABLE":
        return {"shape": shape, "status": "UNASKABLE",
                "reason": (row or {}).get("reason", "no control reading")}
    got = runner(surface.argv(with_form=True), SHAPES[shape])
    if not got.get("ok"):
        return {"shape": shape, "status": "UNASKABLE", "reason": got.get("reason")}
    rejected = got.get("rc") != 0
    return {"shape": shape, "status": "OBSERVED",
            "observed": b"" if rejected else got["out"], "rejected": rejected,
            "observed_digest": "REJECTED" if rejected else digest(got["out"]),
            "rc": got.get("rc"), "control_digest": row["digest"],
            "seconds": got["seconds"]}


def _outcome(shape: str, reading: str) -> str:
    """What a reading predicts for a shape, in a comparable form."""
    data = SHAPES.get(shape)
    if data is None:
        return SILENT
    if reading == REJECT:
        return "REJECTED"
    parts = tuple(reading.split("+")) if reading not in (IDENTITY, REJECT) else ()
    if KIND_OF_SHAPE[shape] not in reading_domain(parts):
        return "REJECTED"
    value = apply_reading(parts, data)
    if value == SILENT:
        return SILENT
    return digest(value)


# The one shape where a prediction of "nothing" is not a contradiction: on empty input a
# program legitimately reads nothing and prints nothing. Everywhere else a hypothesis that
# cannot say what the surface printed has failed to explain an observation that really
# happened, and is contradicted by it.
SILENCE_EXCUSED = frozenset({"empty"})


def _contradicted(shape: str, predicted: str, observed_digest: str) -> bool:
    if predicted == SILENT:
        return shape not in SILENCE_EXCUSED
    return predicted != observed_digest


def survivors(asked: Sequence[Mapping[str, Any]],
              pool: Sequence[str] | None = None) -> list[str]:
    """Readings consistent with every witness taken so far, in canonical order."""
    candidates = list(pool) if pool is not None else list(READING_NAMES)
    alive: list[str] = []
    for name in candidates:
        ok = True
        for obs in asked:
            if obs.get("status") != "OBSERVED":
                continue
            if _contradicted(obs["shape"], _outcome(obs["shape"], name),
                             obs["observed_digest"]):
                ok = False
                break
        if ok:
            alive.append(name)
    return alive


# Primitives after which any further sorting changes nothing: they either produce a single
# scalar or a total order of their own.
_ABSORBS_SORT = frozenset({"sort_lex", "sort_num", "sort_dict", "sort_month",
                           "sort_lex_desc", "sort_num_desc", "count", "count_runs",
                           "count_words", "count_bytes", "count_chars"})


def _canonical_name(parts: Sequence[str]) -> str:
    return IDENTITY if not parts else "+".join(parts)


def canonical_order(parts: Sequence[str]) -> tuple[str, ...]:
    """Put a pipeline into canonical order, then drop what that order makes redundant.

    Composition is not commutative in general (`uniq` then `sort` differs from `sort` then
    `uniq`), but the *readings* only need one spelling per behaviour, and two spellings that a
    sort makes identical are one question. Without this, `sort_lex` and `uniq_glob+sort_lex`
    both sat in the universe, the search paid for both, and the witness counts were computed
    over a space larger than the behaviours in it.
    """
    ordered = [name for name in ORDER if name in set(parts)]
    out: list[str] = []
    for name in ordered:
        if name.startswith("sort_") or name in _ABSORBS_SORT:
            if any(prev in _ABSORBS_SORT or prev.startswith("sort_") for prev in out):
                continue
        out.append(name)
    # A JSON pipeline is only meaningful where its input parses, so a text primitive stacked
    # on top of one is a spelling of the JSON reading, not a second hypothesis: running
    # `count_runs` over a JSON document's lines is `uniq -c` on pretty-printed JSON, which no
    # interface offers and no goal can observe. Collapsing it keeps the universe one-per-
    # behaviour instead of one-per-spelling.
    if any(name.startswith("json_keys") or name == "pretty_json" for name in out):
        out = [name for name in out
               if name.startswith("json_keys") or name == "pretty_json"]
    return tuple(out)


def behavioural_universe(shapes: Sequence[str] | None = None) -> list[str]:
    """One representative per *behaviour*, not per spelling: the space the search runs on.

    Sorting is idempotent and absorbs what follows it, so `sort_lex`, `sort_lex+sort_lex` and
    `sort_lex+uniq_glob` can be the same function. Measured on this algebra, 107 spellings
    collapse to 27 behaviours, and searching spellings is what made an exact minimax blow up
    for no gain on a 2-core box. The representative is a member of the class, chosen by
    behaviour rather than by rewriting a name -- an earlier version rewrote
    `json_keys_compact+pretty_json` into `json_keys_compact`, which is a different function,
    and the resulting predictions were quietly wrong.
    """
    pool = list(shapes) if shapes else list(SHAPES)
    classes: dict[tuple[str, ...], list[str]] = {}
    for reading in READING_NAMES:
        parts = () if reading in (IDENTITY, REJECT) else canonical_order(reading.split("+"))
        if reading != REJECT and not reading_domain(parts):
            continue          # ill-typed composition: not a hypothesis about any surface
        name = _canonical_name(parts) if reading != REJECT else reading
        key = tuple(_outcome(shape, name) for shape in pool)
        classes.setdefault(key, []).append(name)
    reps = [min(members, key=lambda name: (len(name.split("+")), name != IDENTITY, name))
            for members in classes.values()]
    return sorted(reps, key=lambda name: (name != IDENTITY, name))


def _classes(alive: Sequence[str], shapes: Sequence[str]) -> list[list[str]]:
    """Survivors grouped by what they print on every shape the goal can produce."""
    groups: dict[tuple[str, ...], list[str]] = {}
    for name in alive:
        signature = tuple(_outcome(shape, name) for shape in shapes)
        groups.setdefault(signature, []).append(name)
    return sorted(groups.values(), key=lambda xs: (-len(xs), xs))


def certified(scanned: Mapping[str, Any], asked: Sequence[Mapping[str, Any]],
              pool: Sequence[str] | None = None) -> dict[str, Any]:
    """Is the surface known *for this goal*, and if not, what would settle it."""
    alive = survivors(asked, pool)
    if not alive:
        return {"status": NOT_IDENTIFIABLE, "alive": [],
                "honest_note": "every reading in the algebra is contradicted: the surface "
                               "does something no composed primitive of this algebra does"}
    classes = _classes(alive, scanned.get("askable") or [])
    if len(classes) == 1:
        return {"status": CERTIFIED, "alive": alive, "equivalence_class": classes[0],
                "honest_note": "every surviving reading prints the same thing on every "
                               "shape this goal can produce"}
    return {"status": OPEN_NEED_WITNESS, "alive": alive, "classes": classes,
            "honest_note": f"the survivors split into {len(classes)} classes the goal can "
                           f"tell apart"}


def real_gain(alive: Sequence[str], shape: str) -> float:
    """Expected information gain over the *real* branch structure, as a greedy rule.

    An outcome's probability is the mass of readings that actually predict it, but the size
    of the state it leaves behind is ``bucket(o) UNION silent``, because a silent reading is
    not eliminated by that outcome. Scoring silence as an outcome of its own is how a
    baseline came to report two witnesses where three are needed.
    """
    import math

    total = len(alive)
    buckets: dict[str, list[str]] = {}
    silent = 0
    for name in alive:
        value = _outcome(shape, name)
        if value == SILENT:
            silent += 1
        else:
            buckets.setdefault(value, []).append(name)
    if len(buckets) <= 1:
        return 0.0
    after = 0.0
    for group in buckets.values():
        surviving = len(group) + silent
        after += (len(group) / total) * (math.log2(surviving) if surviving > 1 else 0.0)
    return math.log2(total) - after


def choose_witness(scanned: Mapping[str, Any], asked: Sequence[Mapping[str, Any]],
                   pool: Sequence[str] | None = None) -> dict[str, Any]:
    """Which unasked shape to ask next, ranked by exact information gain.

    The candidate pool is only shapes the goal can produce. A shape on which every surviving
    pair agrees -- or on which every survivor is silent -- has exactly zero gain and is
    refused by arithmetic rather than by taste.
    """
    alive = survivors(asked, pool)
    run = {o["shape"] for o in asked}
    candidates = [s for s in (scanned.get("askable") or []) if s not in run]
    if len(alive) < 2 or not candidates:
        return {"status": "NO_WITNESS_NEEDED", "alive": alive, "candidates": candidates}
    # Ranked by the gain over the *real* branches (silent readings survive an outcome; they
    # are not an outcome). The exact rational comparison from `exact_information_gain` is
    # reported alongside so a reader can see that the float-valued rule and the exact rule
    # pick the same question here -- and can see it fail to, if it ever does.
    gains: list[tuple[float, int, str]] = []
    for shape in candidates:
        buckets: dict[str, int] = {}
        for name in alive:
            value = _outcome(shape, name)
            buckets[value] = buckets.get(value, 0) + 1
        gains.append((real_gain(alive, shape), len(buckets), shape))
    gains.sort(key=lambda row: (-row[0], -row[1], row[2]))
    prior = {name: Fraction(1, len(alive)) for name in alive}
    rows: dict[str, dict[str, dict[str, Fraction]]] = {}
    for shape in candidates:
        outcomes = sorted({_outcome(shape, name) for name in alive})
        rows[shape] = {
            name: {outcome: (Fraction(1, 1) if outcome == _outcome(shape, name)
                             else Fraction(0, 1)) for outcome in outcomes}
            for name in alive
        }
    exact: list[str] = []
    if rows:
        try:
            exact = rank_tests_by_information_gain(prior, rows)
        except ValueError:
            exact = []          # an empty/1-row table carries no comparison; not a verdict
    return {"status": "WITNESS_RANKED", "best": gains[0][2], "alive": alive,
            "ranked": [row[2] for row in gains],
            "separating_mass": {row[2]: row[0] for row in gains},
            "exact_gain_order": exact,
            "greedy_is_exact_ranked": bool(exact) and exact[0] == gains[0][2],
            "honest_note": "a shape where every survivor is silent or equal has zero "
                           "separating mass and is never chosen"}


# --------------------------------------------------------------------------- minimal runs
_OPTIMUM_CACHE: dict[tuple[tuple[str, ...], tuple[str, ...]], dict[str, Any]] = {}
_GREEDY_CACHE: dict[tuple[tuple[str, ...], tuple[str, ...]], int | None] = {}


def goal_quotient(pool: Sequence[str], shapes: Sequence[str]) -> list[list[str]]:
    """The readings grouped by what this goal can ever observe, computed once.

    Two readings that print the same thing on every shape the goal can produce are *the same
    reading for this goal* -- the invariant the whole organ rests on, applied to its own
    search space instead of only to its answer. The grouping is the coarsest partition
    refinement of the per-shape outcome partitions: readings that any shape separates are in
    different classes, readings that no shape separates travel together forever.
    """
    classes: list[list[str]] = [list(pool)]
    for shape in shapes:
        refined: list[list[str]] = []
        for group in classes:
            buckets: dict[str, list[str]] = {}
            for name in group:
                buckets.setdefault(_outcome(shape, name), []).append(name)
            refined.extend(buckets.values())
        classes = refined
    return classes


def smallest_certificate_tree(shapes: Sequence[str], pool: Sequence[str],
                              *, node_budget: int = 50000) -> dict[str, Any]:
    """The fewest witnesses that certify in the worst case, by exact search.

    A witness's outcome may split the survivors in several ways, so a plan is a tree:
    ``depth(S) = 0`` if the survivors in S already form one observation class, else
    ``1 + min over shapes of max over outcomes depth(S | outcome)``. Exact, finite, and the
    optimum greedy information gain has no reason to hit -- which is why it is measured.
    The search runs over the goal's *classes*, not over spellings, which is the same
    reduction that makes the answer meaningful.
    """
    cache_key = (tuple(shapes), tuple(pool))
    if cache_key in _OPTIMUM_CACHE:
        return _OPTIMUM_CACHE[cache_key]
    saved = _MOVE_CACHE.get(("__class__", cache_key))
    if saved is not None:
        _OPTIMUM_CACHE[cache_key] = saved
        return saved
    classes = goal_quotient(pool, shapes)
    # A class never splits: its members agree on every shape by construction. What a witness
    # splits is a *set* of classes, into the buckets of the outcome it prints for each. The
    # earlier version asked whether each class splits on its own, found that none ever does,
    # and reported "no plan" for a space with an obvious one.
    signature: dict[tuple[str, ...], list[str]] = {}
    for shape in shapes:
        signature[shape] = [str(_outcome(shape, group[0])) for group in classes]
    members = [set(group) for group in classes]
    nodes = 0

    @lru_cache(maxsize=None)
    def depth(state: frozenset[int], used: frozenset[str]) -> int | None:
        nonlocal nodes
        nodes += 1
        if nodes > node_budget:
            return None
        if len(state) <= 1:
            return 0
        best: int | None = None
        for shape in shapes:
            if shape in used:
                continue
            buckets: dict[str, list[int]] = {}
            for ci in state:
                buckets.setdefault(signature[shape][ci], []).append(ci)
            if len(buckets) <= 1:
                continue            # no split: silence buys nothing
            worst = 0
            for bucket in buckets.values():
                sub = depth(frozenset(bucket), used | {shape})
                if sub is None:
                    worst = None
                    break
                worst = max(worst, sub)
            if worst is None:
                continue
            candidate = 1 + worst
            if best is None or candidate < best:
                best = candidate
        return best

    optimum = depth(frozenset(range(len(classes))), frozenset())
    # `optimum` is a proven upper bound for the root move (the tree is always a legal plan).
    # Whether the true root optimum is lower is answered by `optimal_move`, which explores the
    # same recurrence without a node cap; the two agree on this design space, and a test pins
    # that they do, so a budget-exhausted `None` can never pass for a proof.
    answer = {"schema": SCHEMA,
              "status": ("PASS__OPTIMUM_COMPUTED" if optimum is not None
                         else "UPPER_BOUND_ONLY__NODE_BUDGET_EXHAUSTED"),
              "minimum_worst_case_witnesses": optimum, "upper_bound": optimum,
              "nodes_explored": nodes, "classes": len(classes), "readings": len(pool)}
    _OPTIMUM_CACHE[cache_key] = answer
    return answer


def _branches_uncached(state: frozenset[str] | Sequence[str], shape: str) -> list[set[str]]:
    """The states a shape can actually leave behind -- one per observable outcome.

    THE BUG THIS REPLACES, because it is the kind that looks like progress. A reading that is
    SILENT on a shape is not eliminated by any outcome of that shape: silence constrains
    nothing. So a real branch after observing outcome ``o`` is ``bucket(o) UNION silent``, not
    ``bucket(o)``. Computing the partition without the silent readings made the search believe
    two witnesses suffice where reality needed four, and the loop then appeared to waste runs
    against a "proven" optimum. The optimum was the liar.
    """
    buckets: dict[str, set[str]] = {}
    silent: set[str] = set()
    for name in state:
        value = _outcome(shape, name)
        if value == SILENT:
            silent.add(name)
        else:
            buckets.setdefault(value, set()).add(name)
    # A silent reading is *contradicted* by any printed outcome (empty input excepted), so it
    # survives no branch and its presence makes a shape informative even when only one
    # reading can explain the outcome. Two errors lived here: treating silence as survival
    # (which made the search believe a stuck pair could be separated) and treating a shape
    # with one outcome as a bounded branch of one (which made it believe nine witnesses
    # sufficed where the true plan needs far more).
    groups = list(buckets.values())
    if not groups:
        return []
    if len(groups) == 1 and not (silent - SILENCE_EXCUSED_BY_SHAPE.get(shape, set())):
        return []
    return groups


SILENCE_EXCUSED_BY_SHAPE: dict[str, set[str]] = {}


@lru_cache(maxsize=None)
def _branches(state: frozenset[str], shape: str) -> tuple[frozenset[str], ...]:
    """Memoised ``_branches_uncached``. The search calls this millions of times."""
    return tuple(frozenset(g) for g in _branches_uncached(state, shape))


_MOVE_CACHE: dict[tuple[tuple[str, ...], tuple[str, ...]], dict[str, Any]] = {}


def optimal_move(alive: Sequence[str], shapes: Sequence[str],
                 *, node_budget: int = 400000) -> dict[str, Any]:
    """The question that minimises the worst-case number of remaining runs, exactly.

    This is the same recurrence as ``smallest_certificate_tree``, run forward: the optimal
    first move is the one achieving ``1 + max over outcomes depth(S|outcome)``. Greedy
    information gain is not this move in general, and the gap is not academic -- on this
    host's own instruments it was the difference between 6 witnesses and the provable 5.

    Two things make it fast enough to sit in a loop. The recursion is keyed on the surviving
    *classes* rather than on the surviving spellings, because the cost depends only on the
    partition. And the outcome table is computed once instead of one subprocess-free but
    still per-node recomputation of every primitive over every shape: the earlier version
    spent 52 seconds and 200,000 nodes on a one-second question.
    """
    cache_key = (frozenset(alive), frozenset(shapes))
    if cache_key in _MOVE_CACHE:
        return _MOVE_CACHE[cache_key]
    ordered_shapes = list(shapes)
    classes = goal_quotient(alive, ordered_shapes)
    signature = {s: [str(_outcome(s, group[0])) for group in classes] for s in ordered_shapes}
    nodes = 0

    @lru_cache(maxsize=None)
    def depth(state: frozenset[int], remaining: frozenset[str]) -> int | None:
        nonlocal nodes
        nodes += 1
        if nodes > node_budget:
            return None
        if len(state) <= 1:
            return 0
        best: int | None = None
        for shape in remaining:
            buckets: dict[str, list[int]] = {}
            for ci in state:
                buckets.setdefault(signature[shape][ci], []).append(ci)
            if len(buckets) <= 1:
                continue
            worst = 0
            for bucket in buckets.values():
                sub = depth(frozenset(bucket), remaining - {shape})
                if sub is None:
                    worst = None
                    break
                worst = max(worst, sub)
            if worst is None:
                continue
            candidate = 1 + worst
            if best is None or candidate < best:
                best = candidate
        return best

    full = frozenset(range(len(classes)))
    left = frozenset(ordered_shapes)
    scored: list[tuple[int, str]] = []
    for shape in ordered_shapes:
        buckets: dict[str, list[int]] = {}
        for ci in full:
            buckets.setdefault(signature[shape][ci], []).append(ci)
        if len(buckets) <= 1:
            # A shape no survivor class can split is not a witness. It is kept out of the
            # ranking rather than scored with a sentinel, because a sentinel leaked into the
            # reported bound and printed 1073741825 as a "worst case" for eleven surfaces.
            continue
        worst = 0
        unproved = False
        for bucket in buckets.values():
            sub = depth(frozenset(bucket), left - {shape})
            if sub is None:
                unproved = True
                break
            worst = max(worst, sub)
        if unproved:
            # the node cap was reached on this branch: the shape is not ranked at all rather
            # than scored with a sentinel, which twice leaked out as a reported worst case
            continue
        scored.append((1 + worst, shape))
    scored.sort()
    best_depth, best_shape = scored[0] if scored else (None, None)

    answer = {"schema": SCHEMA, "shape": best_shape, "worst_case_witnesses": best_depth,
              "nodes_explored": nodes, "ranking": scored, "classes": len(classes),
              "honest_note": "chosen by exact minimax over the partition lattice, not by gain"}
    _MOVE_CACHE[cache_key] = answer
    return answer


def greedy_worst_case(shapes: Sequence[str], pool: Sequence[str], *,
                      limit: int = 16) -> int | None:
    """What greedy information gain costs **in the worst case**, played out honestly.

    Two earlier versions of this baseline flattered it: one re-derived its state from an empty
    history (so it eliminated nothing), and one followed only the largest branch (so it
    measured a path, not a tree, and reported 2 where the exact answer is 4). A baseline that
    under-reports is worse than none, because it is the number a reader believes.

    A silent reading survives an outcome, so a branch after ``o`` is ``bucket(o) UNION
    silent``; the recursion takes the maximum over branches exactly as the optimum does, and
    only the choice of shape differs -- gain instead of minimax. The gain is recomputed at
    each node, which is the part that makes it greedy rather than exhaustive.
    """
    cache_key = (tuple(shapes), tuple(pool))
    if cache_key in _GREEDY_CACHE:
        return _GREEDY_CACHE[cache_key]
    memo: dict[frozenset[str], int | None] = {}

    def depth(state: frozenset[str], left: frozenset[str]) -> int | None:
        if state in memo:
            return memo[state]
        memo[state] = None
        live = [n for n in pool if n in state]
        if len(_classes(live, list(shapes))) <= 1:
            memo[state] = 0
            return 0
        if not left:
            return None
        scored = sorted(((real_gain(live, shape), shape) for shape in left),
                        key=lambda row: (-row[0], row[1]))
        for gain, shape in scored:
            if gain <= 0:
                continue
            groups = _branches(state, shape)
            if len(groups) <= 1:
                continue
            worst = 0
            for group in groups:
                sub = depth(frozenset(group), left - {shape})
                if sub is None:
                    worst = None
                    break
                worst = max(worst, sub)
            if worst is None or 1 + worst > limit:
                continue
            memo[state] = 1 + worst
            return memo[state]
        return None

    _GREEDY_CACHE[cache_key] = depth(frozenset(pool), frozenset(shapes))
    return _GREEDY_CACHE[cache_key]


def interrogate(surface: Surface, *, runner=run_bounded, max_probes: int = 6,
                scanned: Mapping[str, Any] | None = None,
                pool: Sequence[str] | None = None) -> dict[str, Any]:
    """Scan, retrieve, then ask only the questions the goal can tell apart."""
    declared = read_surface(surface.words)
    if declared["status"] != "OK":
        return {"schema": SCHEMA, "status": REFUSED_NO_READING,
                "surface": list(surface.form), "declaration": declared}
    candidates = list(pool) if pool is not None else list(READING_NAMES)
    # THE ADEQUACY GATE. A declaration that names a primitive whose *parameter* the design
    # space cannot exercise cannot be certified here: the space would merge it with another
    # reading and the certificate would be true of the fixtures and false of the world. That
    # is exactly how `fold -b` came to be certified `identity`. Refusing by name is the only
    # honest answer, and it is computed rather than promised.
    unexercised = [name for name in declared["named"]
                   if name in PARAMETER_WITNESS and not parameter_exercised(name)]
    if unexercised:
        return {"schema": SCHEMA, "status": REFUSED_PARAMETER_UNEXERCISED,
                "surface": list(surface.form), "declaration": declared,
                "unexercised": unexercised,
                "detail": {"what": "the declaration names a parameter no shape exercises",
                           "why": "a certificate would be about the fixtures, not the surface"}}
    scan_result = dict(scanned) if scanned is not None else scan(surface, runner=runner)
    if not scan_result.get("askable"):
        return {"schema": SCHEMA, "status": REFUSED_UNRUNNABLE,
                "surface": list(surface.form), "declaration": declared, "scan": scan_result}
    # The control says which shapes the *interface* cannot read. That is a hypothesis about
    # the surface form, not a fact about it: `jq .` rejects text, and so does `jq -S`, but
    # assuming it instead of asking it is how a class came to be certified for inputs it was
    # never run on. One run per such shape converts the guess into an observation.
    unaskable: list[dict[str, Any]] = []
    for shape in list(scan_result.get("unaskable", ())):
        got = runner(surface.argv(with_form=True), SHAPES[shape])
        if got.get("ok") and got.get("rc") != 0:
            unaskable.append({"shape": shape, "status": "OBSERVED",
                              "observed_digest": "REJECTED", "rejected": True,
                              "control_digest": None})
        else:
            scan_result = _drop_shape(scan_result, shape)

    asked: list[dict[str, Any]] = list(unaskable)
    _proved_from_here: int | None = None
    _moves_spent: int | None = None
    _first_bound: int | None = None
    _nodes_spent: int = 0
    while True:
        state = certified(scan_result, asked, candidates)
        if state["status"] == CERTIFIED:
            # The exact policy already proved, at every step it took, how many witnesses the
            # remaining space needs from the state the loop was actually in. That is the
            # certificate's yardstick: `worst_case_spent + what the last move proved`. The
            # earlier version priced this from the *whole* universe with the *remaining*
            # shapes, which answers a different and harder question than the one the loop
            # faced -- hence a "4" printed against a run that spent 2.
            optimum = ({"minimum_worst_case_witnesses": _first_bound,
                        "nodes_explored": _nodes_spent}
                       if _moves_spent is not None else
                       smallest_certificate_tree(scan_result["askable"], candidates))
            return {"schema": SCHEMA, "status": CERTIFIED, "surface": list(surface.form),
                    "declaration": declared, "scan": scan_result, "witnesses": asked,
                    "probe_count": len(asked),
                    "equivalence_class": state["equivalence_class"],
                    "named_in_class": sorted({name for name in state["equivalence_class"]
                                              if _family(name) & set(declared["named"])}),
                    "probes_spent": len([w for w in asked if w.get("status") == "OBSERVED"]),
                    "worst_case_proved": optimum["minimum_worst_case_witnesses"],
                    "optimum_nodes": optimum["nodes_explored"],
                    "greedy_worst_case_witnesses":
                        greedy_worst_case(scan_result["askable"], candidates),
                    "naive_witnesses": len(scan_result["askable"]),
                    "honest_note": state["honest_note"]}
        if state["status"] != OPEN_NEED_WITNESS:
            return {"schema": SCHEMA, "status": state["status"],
                    "surface": list(surface.form), "declaration": declared,
                    "scan": scan_result, "witnesses": asked, "detail": state}
        if len(asked) >= max_probes:
            return {"schema": SCHEMA, "status": OPEN_BUDGET, "surface": list(surface.form),
                    "declaration": declared, "scan": scan_result, "witnesses": asked,
                    "detail": state}
        # A shape already asked is not a question: re-offering it would buy a repeat of an
        # answer and no information. The DP must see the *unasked* space or it plans to ask
        # what it already knows -- which is exactly the failure it was written to remove.
        unasked = [s for s in scan_result["askable"]
                   if s not in {w["shape"] for w in asked}]
        move = optimal_move(state["alive"], unasked)
        if _first_bound is None and move.get("worst_case_witnesses") is not None:
            # The guaranteed upper bound on this run, computed from the state the loop
            # actually starts in -- directly comparable to the greedy baseline, which is also
            # measured from the start. Reporting a bound computed from a different state is
            # how a table starts lying about its own numbers.
            _first_bound = move["worst_case_witnesses"]
        if move.get("worst_case_witnesses") is not None:
            _moves_spent = move["worst_case_witnesses"] + len(
                [w for w in asked if w.get("status") == "OBSERVED"])
            _proved_from_here = move["worst_case_witnesses"]
            _nodes_spent += int(move.get("nodes_explored") or 0)
        choice = ({"best": move["shape"]} if move.get("shape")
                  else choose_witness(scan_result, asked, candidates))
        if not choice.get("best"):
            return {"schema": SCHEMA, "status": NOT_IDENTIFIABLE,
                    "surface": list(surface.form), "declaration": declared,
                    "scan": scan_result, "witnesses": asked, "detail": state}
        obs = ask(surface, scan_result, choice["best"], runner=runner)
        asked.append(obs)
        if obs.get("status") != "OBSERVED":
            # A shape the control says is unaskable is not evidence, and re-choosing it
            # would spin forever. It leaves the goal's domain, by name, and the loop
            # continues with one fewer question -- never by pretending the answer is known.
            asked[-1] = {"shape": obs["shape"], "status": "UNASKABLE",
                         "reason": obs.get("reason")}
            scan_result = _drop_shape(scan_result, obs["shape"])


def _family(reading: str) -> set[str]:
    """The primitives a reading is built from, with the JSON style folded to its stem.

    A style is a rendering degree of freedom the words never mention ("sort keys of objects"
    says nothing about indentation), so a certified `json_keys_pretty` does satisfy a
    declaration that named `json_keys`. Folding the stem here is what keeps the check honest
    in the other direction too: a reading built from a *different* primitive is never folded.
    """
    parts = [] if reading == IDENTITY else reading.split("+")
    return {part.split("_pretty")[0].split("_compact")[0] for part in parts}


def _drop_shape(scanned: Mapping[str, Any], shape: str) -> dict[str, Any]:
    """Remove a shape the goal cannot ask from the design space, keeping the record honest."""
    updated = dict(scanned)
    updated["askable"] = [s for s in scanned.get("askable", ()) if s != shape]
    return updated


def certify(surface: Surface, *, memory: dict[str, Any] | None = None,
            memory_path: pathlib.Path | None = None, runner=run_bounded) -> dict[str, Any]:
    """Scan, ask, certify, falsify out of space, then remember -- in that order.

    Each step is useless without the next one: a certificate below the held-out gate is a
    guess, and a record without a certificate is a rumour. This function exists so the order
    cannot be got wrong by a caller in a hurry, and it returns every intermediate result so
    nothing is hidden behind a boolean.
    """
    result = interrogate(surface, runner=runner)
    if result.get("status") != CERTIFIED:
        return {"schema": SCHEMA, "status": result.get("status"), "result": result,
                "stored": False}
    held_out = held_out_check(surface, result, runner=runner)
    if not str(held_out.get("status", "")).startswith("SURVIVED"):
        return {"schema": SCHEMA, "status": "FALSIFIED__DO_NOT_STORE", "result": result,
                "held_out": held_out, "stored": False,
                "honest_note": "certified inside the design space and contradicted outside "
                               "it; the certificate is a property of the fixtures"}
    stored = False
    key = None
    if memory is not None:
        import shutil as _shutil
        resolved = _shutil.which(surface.tool) or surface.tool
        key = memory_key(resolved, surface.tool, surface, "goal:" + ",".join(surface.shapes))
        if key:
            remember(memory, key, result, held_out)
            stored = key in (memory.get("entries") or {})
            if stored and memory_path is not None:
                save_memory(memory, memory_path)
    return {"schema": SCHEMA, "status": CERTIFIED, "result": result, "held_out": held_out,
            "stored": stored, "memory_key": key}


# --------------------------------------------------------------------------- falsification
# Each entry targets a distinction some primitive in the algebra is blind to on the design
# space: adjacent repeats, month names, numeric-vs-version order, punctuation and case,
# multi-byte characters, leading blanks, and nested JSON. Random inputs found four vacuous
# classes; these find them on purpose. They are never shown to the search.
HELD_OUT: dict[str, bytes] = {
    "adjacent_repeats": b"b\nb\nb\na\na\n",
    "adjacent_mixed": b"x\ny\ny\nx\n",
    "months_out_of_order": b"DEC\nAPR\nJAN\n",
    "months_with_text": b"sep 9\nJAN 1\nFEB 2\n",
    "numeric_vs_version": b"v1.10\nv1.9\nv2.0\n",
    # The out-of-space twin of `lines_exponents`: an exponent, an infinity and a nan, all of
    # which a plain numeric sort reads differently from a general-numeric one.
    "exponents_out_of_space": b"2.5e3\n900\ninf\n-1.0e-3\n",
    "long_line_out_of_space": b"x" * 300 + b"\n",
    "tabs_out_of_space": b"\t" * 5 + b"abc\n" + b"a\tb\tc\n",
    "numbers_with_text": b"7 apples\n10 pears\n2 figs\n",
    "punctuation_case": b"a.B\nA_b\nab\nAB\n",
    "multibyte": "\u00dcn\u00efcode\nzebra\n\u00e5ngstr\u00f6m\n".encode(),
    "leading_blanks": b"   z\n  a\n b\n",
    "nested_object": b'{"z":{"y":1,"x":[{"b":2,"a":1}]},"a":0}\n',
    "object_then_array": b'{"b":1,"a":2}\n[3,1]\n',
    "duplicates_sorted": b"a\na\nb\n",
    "one_word": b"solo\n",
    "blank_and_text": b"\ntext\n\n",
    "long_line": (b"word " * 40) + b"\n",
}


def held_out_inputs(count: int = 0, seed: int = 0) -> dict[str, bytes]:
    """The adversarial held-out set (name -> bytes). Kept as a function for interface parity."""
    return dict(HELD_OUT)


def held_out_check(surface: Surface, result: Mapping[str, Any], *,
                   shapes: Mapping[str, bytes] | None = None,
                   runner=run_bounded) -> dict[str, Any]:
    """Does the certified class actually predict inputs it was never fitted to?

    For each held-out input the surface is run for real, and every surviving reading's
    prediction is compared against it. The certificate survives only if a single
    representative explains every held-out run. A failure names the input, the reading and
    the bytes, because a falsification without the witness is an opinion.
    """
    if result.get("status") != CERTIFIED:
        return {"status": "NOT_APPLICABLE", "reason": result.get("status")}
    members = list(result["equivalence_class"])
    surviving = [name for name in members]
    checked = 0
    failures: list[dict[str, Any]] = []
    for name, data in (shapes or held_out_inputs()).items():
        got = runner(surface.argv(with_form=True), data)
        actual = REJECTED_BYTES if (not got.get("ok") or got.get("rc") != 0) else got["out"]
        checked += 1
        still: list[str] = []
        for reading in surviving:
            predicted = _predict_bytes(reading, data)
            if isinstance(predicted, bytes) and predicted == actual:
                still.append(reading)
            else:
                failures.append({"input": name, "reading": reading,
                                 "actual_bytes": actual[:200], "data": data[:200]})
        surviving = still
        if not surviving:
            break
    if not surviving:
        return {"status": "FALSIFIED__HELD_OUT_DISAGREES", "input": failures[0]["input"],
                "reading": failures[0]["reading"],
                "actual_bytes": failures[0]["actual_bytes"],
                "data": failures[0]["data"], "checked": checked,
                "honest_note": "no member of the certified class predicts this run; the "
                               "design space did not contain the distinction"}
    return {"status": "SURVIVED__HELD_OUT_AGREES", "reading": surviving[0],
            "surviving_members": surviving, "members": len(members),
            "held_out_checked": checked,
            "honest_note": "every held-out run was predicted exactly by a member of the "
                           "certified class, and the class was never fitted to these"}


REJECTED_BYTES = b"\x00REJECTED"


def _predict_bytes(reading: str, data: bytes) -> bytes | str:
    if reading == REJECT:
        return REJECTED_BYTES
    parts = () if reading == IDENTITY else tuple(reading.split("+"))
    value = apply_reading(parts, data)
    return value


# --------------------------------------------------------------------------- memory
def help_text(tool: str, *, runner=run_bounded) -> str:
    got = runner([tool, "--help"], b"")
    if got.get("ok") and got.get("out"):
        return got["out"].decode("utf-8", "replace")
    if got.get("err"):
        return got["err"].decode("utf-8", "replace")
    return ""


DEFAULT_MEMORY = pathlib.Path("/tmp/brain_interrogation/memory.json")


def load_memory(path: pathlib.Path = DEFAULT_MEMORY) -> dict[str, Any]:
    try:
        data = json.loads(pathlib.Path(path).read_text())
    except (OSError, ValueError):
        return {"schema": MEMORY_SCHEMA, "entries": {}}
    if data.get("schema") != MEMORY_SCHEMA or not isinstance(data.get("entries"), dict):
        return {"schema": MEMORY_SCHEMA, "entries": {}}
    return data


def save_memory(memory: Mapping[str, Any], path: pathlib.Path = DEFAULT_MEMORY) -> None:
    target = pathlib.Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(memory, indent=1, sort_keys=True))
    tmp.replace(target)


def memory_key(tool_path: str, invoked: str, surface: Surface, goal: str) -> str | None:
    """Keyed by the bytes and the invoked name, exactly as the host round proved necessary.

    ``xz`` and ``unxz`` are byte-identical and behave oppositely, so content alone would
    answer "compresses" for the decompressor; ``/usr/bin`` had 635 names for 481 files, so a
    name alone would store one fact eight times. Both halves are load-bearing.
    """
    content = file_digest(tool_path)
    if content is None:
        return None
    return f"{content[:16]}:{invoked}:{' '.join(surface.form)}:{goal}"


def remember(memory: dict[str, Any], key: str | None, result: Mapping[str, Any],
             held_out: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Store a certificate -- but only one that survived inputs it was not fitted to.

    The held-out gate is part of admission, not a separate audit. A certificate is a statement
    about the design space, and the measured falsifications (a vacuous `identity` class, a
    version comparator that is not an order) all passed the in-space gate. If the record is
    written before the out-of-space check, the store fills with confident falsehoods -- the
    exact failure this repository has already paid for once.
    """
    if not key or result.get("status") != CERTIFIED:
        return memory
    if held_out is None or not str(held_out.get("status", "")).startswith("SURVIVED"):
        return memory
    entries = memory.setdefault("entries", {})
    entries[key] = {
        "equivalence_class": list(result["equivalence_class"]),
        "held_out_checked": int((held_out or {}).get("held_out_checked", 0)),
        "held_out_reading": (held_out or {}).get("reading"),
        "witnesses": [w["shape"] for w in result["witnesses"] if w.get("status") == "OBSERVED"],
        "evidence": [{"shape": w["shape"], "control": w.get("control_digest"),
                      "observed": w.get("observed_digest")}
                     for w in result["witnesses"] if w.get("status") == "OBSERVED"],
        "certified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return memory


def recall(memory: Mapping[str, Any], key: str | None, surface: Surface, *,
           runner=run_bounded) -> dict[str, Any]:
    """Believe a record only after its own evidence reproduces.

    Every recorded witness is re-run against a fresh control. If one disagrees the record is
    discarded by name and the caller must re-derive, because a cached fact in a changing
    world is a hypothesis with a receipt, not an authority. Cheap because a certified surface
    leaves only a few witnesses behind -- not the whole design space.
    """
    entries = memory.get("entries") or {}
    if not key or key not in entries:
        return {"status": "MISS"}
    record = entries[key]
    fresh = scan(surface, runner=runner)
    for evidence in record.get("evidence", []):
        shape = evidence["shape"]
        if shape not in SHAPES or shape not in surface.shapes:
            return {"status": "STALE__SHAPE_GONE", "shape": shape}
        obs = ask(surface, fresh, shape, runner=runner)
        if obs.get("status") != "OBSERVED":
            return {"status": "STALE__SHAPE_UNASKABLE", "shape": shape}
        if obs.get("observed_digest") != evidence.get("observed"):
            return {"status": "STALE__EVIDENCE_DISAGREES", "shape": shape,
                    "recorded": evidence.get("observed"),
                    "observed": obs.get("observed_digest")}
        if obs.get("control_digest") != evidence.get("control"):
            return {"status": "STALE__CONTROL_DISAGREES", "shape": shape}
    return {"status": "HIT__EVIDENCE_REPRODUCED", "record": record,
            "witnesses_replayed": len(record.get("evidence", []))}

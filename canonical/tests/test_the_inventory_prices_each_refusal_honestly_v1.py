"""The inventory must price each refusal by who is actually wrong.

The document has two sections that answer the same question -- §3 lists every refusal with the
cheapest correct fix, and §6 ranks the work using how many of those refusals are fixture defects,
selection misses, or real capability gaps. If they disagree, the ranking is built from a number the
evidence does not support. That failure happened twice while this section was being written, and
both times it was **silent**:

1. The split read ``refusal.split(":")[0]``, which is ``CAPABILITY_REFUSED`` for every row -- so it
   reported *0 of 7 are fixture defects* while §3 was documenting four.
2. ``defect_owner`` was handed the bare class (``NO_FLAKY_TEST_DETECTED``) instead of the door's
   full status key (``FAIL_CLOSED__CAPABILITY_REFUSED_NO_FLAKY_TEST_DETECTED``). An unresolved key
   falls through to ``capability``, so again it reported *0 fixture, 7 capability* -- and 7
   capability gaps is a completely different, much more expensive, plan.

Both bugs produce a plausible-looking plan. Nothing failed; the document simply argued for the
wrong work. These tests make the two sections check each other, and they pin the direction the
error must fall: an unknown refusal is **capability**, never excused, because excusing work that
has not been done is the worse mistake.
"""
from __future__ import annotations

import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))

import compose_hardcore_swe_problem_inventory_v1 as compose  # noqa: E402

DOC = ROOT / "HARDCORE_SWE_ALL_PROBLEMS_20261031_V1.md"

OWNERS = {"fixture", "selection", "capability"}


def _remedy_keys() -> list[str]:
    return [k for k in compose.FIX if k.startswith("FAIL")]


def test_every_remedy_resolves_to_one_of_three_owners() -> None:
    """No remedy may fall through to an owner that means something else."""
    for key in _remedy_keys():
        assert compose.defect_owner(key) in OWNERS, key
        # The bare class is what a caller naturally has, and it must agree with the full key.
        bare = compose.refusal_class({"status": key})
        assert compose.defect_owner(bare) == compose.defect_owner(key), (key, bare)


def test_a_bare_class_resolves_exactly_when_it_is_unambiguous() -> None:
    """The suffix lookup must resolve the real classes and refuse to guess on a collision."""
    resolved = {}
    for key in _remedy_keys():
        bare = compose.refusal_class({"status": key})
        if len([k for k in compose.FIX if k.endswith("_" + bare)]) == 1:
            resolved[bare] = compose.defect_owner(bare)
        else:
            # Ambiguous suffixes must not silently pick one of several remedies.
            assert compose.defect_owner(bare) == "capability", bare
    # These are the refusals the census actually returned; all are unambiguous.
    for bare in ("NO_FLAKY_TEST_DETECTED", "STATED_ANSWER_NOT_PROVIDED",
                 "NO_REPRODUCIBLE_BUG_SPECIFIED_OR_OBSERVED",
                 "NO_MODIFIED_PYTHON_FUNCTIONS_BETWEEN_REVISIONS",
                 "TARGET_SYMBOL_COLLISION", "TARGET_NOT_IN_STANDALONE_GIT_REPOSITORY"):
        assert resolved.get(bare) in OWNERS, bare


@pytest.mark.parametrize("unresolvable", ["", "add", "NOT_A_REAL_CLASS", "REFUSED_"])
def test_an_unknown_refusal_is_never_excused(unresolvable: str) -> None:
    """Failing toward 'capability' is the safe direction: it never excuses unfinished work."""
    assert compose.defect_owner(unresolvable) == "capability"


@pytest.mark.parametrize("real_gap", [
    "FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED",
    "FAIL_CLOSED__CAPABILITY_REFUSED_CPP_NO_APPLICABLE_TRANSFORM",
    "FAIL_CLOSED__CAPABILITY_REFUSED_SQL_UNSUPPORTED_DDL_EDIT",
    "FAIL_CLOSED__CAPABILITY_REFUSED_NO_TESTS_DISCOVERED",
])
def test_a_real_capability_gap_is_never_excused(real_gap: str) -> None:
    """These are missing capabilities, so no wording in their remedy may re-price them."""
    assert compose.defect_owner(real_gap) == "capability"


def test_the_word_none_is_not_what_marks_a_fixture_defect() -> None:
    """The trap: 'the gate is working, the fix is to build the capability' is a *real gap*.

    Its remedy begins with 'none' exactly like a fixture defect's does, so an owner decided by that
    word would excuse four genuine gaps. The discriminator is what the remedy says is missing.
    """
    gate_working = compose.FIX["FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED"]
    fixture = compose.FIX["FAIL_CLOSED__CAPABILITY_REFUSED_NO_FLAKY_TEST_DETECTED"]
    assert gate_working.lower().startswith("none") and fixture.lower().startswith("none")
    assert compose.defect_owner("FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED") == "capability"
    assert compose.defect_owner("FAIL_CLOSED__CAPABILITY_REFUSED_NO_FLAKY_TEST_DETECTED") == "fixture"


def _doc() -> str:
    assert DOC.exists(), f"the composed document is missing: {DOC}"
    return DOC.read_text()


def test_the_published_sections_agree_on_who_is_wrong() -> None:
    """§3's owner column and §6's counts must be the same claim, in the same document."""
    text = _doc()
    section3 = text.split("## §3 ", 1)[1].split("### 3.0", 1)[0]
    owners = re.findall(r"^\| `(FAIL[A-Z_0-9]+)` \| (\d+) \| \*\*(\w+)\*\* \|", section3, re.M)
    assert owners, "§3 no longer carries an owner column"

    priced = {"fixture": 0, "selection": 0, "capability": 0}
    for key, count, owner in owners:
        assert owner in OWNERS, (key, owner)
        assert compose.defect_owner(key) == owner, (key, owner)
        priced[owner] += int(count)

    section6 = text.split("## §6 ", 1)[1].split("## §7", 1)[0]
    stated = re.search(
        r"\*\*(\d+) are fixture defects\*\*.*?\*\*(\d+) are selection\*\*.*?\*\*(\d+) are capability\*\*",
        section6, re.S)
    assert stated, "§6 no longer states the three counts"
    got = dict(zip(("fixture", "selection", "capability"), (int(g) for g in stated.groups())))
    assert got == priced, f"§6 prices {got} but §3 documents {priced}"

    refused = re.search(r"Of the (\d+)\s*\nthat remain", text)
    assert refused, "§6 no longer states how many sentences remain"
    assert int(refused.group(1)) == sum(priced.values()), "the split does not sum to the refusals"


def test_the_ranking_does_not_spend_capability_work_on_fixtures() -> None:
    """A fixture defect ranked as capability is the expensive version of the same mistake."""
    text = _doc()
    section6 = text.split("## §6 ", 1)[1].split("## §7", 1)[0]
    fixture = int(re.search(r"\*\*(\d+) are fixture defects\*\*", section6).group(1))
    capability = int(re.search(r"\*\*(\d+) are capability\*\*", section6).group(1))
    row3 = re.search(r"^\| 3 \| \*\*capability\*\* for the (\d+) remaining", section6, re.M)
    row7 = re.search(r"^\| 7 \| fix the (\d+) fixture defect", section6, re.M)
    assert row3 and row7, "the ranked table changed shape"
    assert int(row3.group(1)) == capability
    assert int(row7.group(1)) == fixture
    # The fixture row must not sit above the capability row: it cannot buy capability.
    assert int(capability) == 0 or section6.index(row3.group(0)) < section6.index(row7.group(0))

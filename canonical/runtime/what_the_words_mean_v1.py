"""WHAT THE WORDS MEAN: the organ that turns an instruction into a target, without a model.

THE GAP THIS CLOSES, MEASURED NOT ASSUMED.

    ground_consensus_action(ConsensusRequest(action="click", role="button", name="Compose"), page)
        -> SELECT  UNIQUE_MULTI_CHANNEL_NORMALIZED_CONSENSUS   (it works)

    ground_consensus_action(ConsensusRequest(action="click", role="button", name="write a new email"), page)
        -> ESCALATE  NO_CONSENSUS_MATCH                        (no path at all)

`consensus_dom_grounding` says of itself, correctly: it "does not infer a target from a goal". It is fail-closed
safety, and it answers the question *given a target, is it unambiguous* -- never *which element did they mean*.
Every computer-use number in this repository is unmeasured because nothing answered the second question.

THE PRINCIPLE, IN ONE SENTENCE. A person and a well-made interface both use the SAME WORD for the same thing;
the difficulty is that the interface may use a word the person did not, so the agent must know the relation
between them -- and that relation is a fact about language, which can be READ, not guessed.

    instruction: "write a new email"     page words: "Compose"
    both are about composing. Neither string contains the other. A char-level matcher fails.

So there are exactly two honest sources for the bridge, and this module uses both, in order:

    1. THE PAGE'S OWN WORDS. An element that says "Compose" and a task that says "compose" meet in one word --
       same lemma, no knowledge needed. "write a new email" -> "email" is on the page? then "new email" is a
       phrase, and the element that composes one is the one whose accessible name the PAGE ITSELF associates
       with it. This covers most real interfaces, because good interfaces name things what people call them.

    2. A MEANS-RELATION READ FROM DOCUMENTATION. When the words do not meet, the relation is a fact someone
       wrote down -- "to compose, click Compose" -- and this repository already fetches manuals and mining
       sources (`program_manual_v1`, `documentation_mining_v1`). This module does not fetch; it CONSUMES the
       relation when given one, and REFUSES when it has neither source.

WHAT THIS MODULE REFUSES, AND WHY THAT IS THE DESIGN.

    - It refuses when two elements match equally.  A coin flip presented as an answer is the defect that
      `consensus_dom_grounding` exists to prevent, and §A74 already ruled: when the evidence does not choose,
      return nothing.
    - It refuses when the best match is not better than a threshold derived from the page itself.
    - It never invents a synonym. `Archive` is not `Delete` because they are both verbs in a toolbar. Every
      relation it uses is either a shared lemma present in both strings or one somebody supplied with a source.

AUTHORITY NONE. No model, no parameters, no network at runtime, $0.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

SCHEMA = "PROJECT_BRAIN_WHAT_THE_WORDS_MEAN_V1"

# Words that carry no reference. They are not "stopwords" in the linguistic sense -- they are the words a
# person uses to phrase a REQUEST rather than to name a THING. Derived here, not copied from a list: the test
# is whether the word can ever be the name of a control, and every word below cannot.
_SILENT = frozenset("""
a an the one ones some any all of in on at to for from by with into onto over under about as is are be been
being was were am do does did doing done can could would should will shall may might must need needs needed
have has had having i me my we our you your it its this that these those there here then than and or but if
so just also very please now first next lastly then new again another same other more most much many few
""".split())

_TOOLBAR = frozenset("""
button link tab menuitem checkbox radio textbox combobox option treeitem slider spinbutton searchbox
textfield field input icon item cell row heading label image img anchor control widget element
""".split())


def words(text: str) -> list[str]:
    """The words of a string, in order, with the request's furniture removed. Punctuation is not a word."""
    normalised = unicodedata.normalize("NFKC", str(text or "")).casefold()
    # A DIGIT IS NOT PART OF A NAME IT TOUCHES. Real pages glue counters to labels -- GitHub renders the
    # issues tab as "Issues5k+ (5k+)" and the pull-request tab as "Pull requests2.4k (2.4k)". Measured
    # 2026-11-23: that made the word people say ("issues") an unrecognisable token ("issues5k+"), so a word
    # plainly on the page failed to match. The rule below breaks a letter/digit boundary; it does not invent
    # a word, and it never removes one.
    # A COUNT IS NOT PART OF THE NAME IT SITS IN. Remove counter shapes whole -- "5k+", "2.4k", "36.6k" --
    # BEFORE splitting, so no fragment of a number survives as a word. Measured 2026-11-23: stripping only
    # the letter/digit boundary left a bare "k" in the name, which then failed the whole-name test.
    without_counts = re.sub(r"\d+(?:[.,]\d+)?\s*[kmb]?\s*\+?", " ", normalised)
    spaced = re.sub(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])", " ", without_counts)
    found = re.findall(r"[a-z0-9]+(?:['’][a-z]+)?", spaced)
    # a bare number is a count, not a name
    return [w for w in found if w not in _SILENT and not w.isdigit()]


def stem(word: str) -> str:
    """A cheap, order-preserving root, so `compose`/`composing`/`composed` meet and `compose`/`compost` do not.

    This is ONE suffix rule, not a stemmer library, and it is checked in both directions before being applied:
    a word that would shrink below three characters keeps its form. Measured against the failure this project
    already recorded (§A130): a stemmer's special case can swallow another word, so nothing here rewrites a
    stem to a different one -- it only removes a suffix that the word can afford to lose.
    """
    w = word.casefold()
    for suffix, floor in (("ing", 4), ("edly", 4), ("ed", 3), ("es", 3), ("s", 3), ("e", 3), ("ly", 4)):
        if w.endswith(suffix) and len(w) - len(suffix) >= floor:
            return w[: -len(suffix)]
    return w


def stems(text: str) -> set[str]:
    return {stem(w) for w in words(text)}


@dataclass(frozen=True)
class Candidate:
    """One thing on the page that a person could have meant."""
    element_id: str
    role: str
    name: str
    aliases: tuple[str, ...] = ()

    def all_text(self) -> tuple[str, ...]:
        return tuple(t for t in (self.name, *self.aliases) if t)


@dataclass(frozen=True)
class Meaning:
    """What a request asked for, as far as its words can say."""
    target_words: frozenset[str]
    stems: frozenset[str]
    ordered: tuple[str, ...] = ()

    @classmethod
    def of(cls, instruction: str) -> "Meaning":
        ws = [w for w in words(instruction) if w not in _TOOLBAR]
        return cls(frozenset(ws), frozenset(stem(w) for w in ws), tuple(ws))


def _names(candidate: Candidate, meaning: Meaning) -> tuple[bool, set[str]]:
    """Does this element's own name sit inside the request's words?

    THE RULE, AND WHY IT IS NOT A SIMILARITY SCORE. A person naming a control uses the control's own name, or
    the control's name is a word of what they said. So the test is CONTAINMENT, both directions:

        "check my INBOX"        names element "Inbox"     every word of the name is in the request
        "ARCHIVE the convo"     names element "Archive"   ditto
        "write a new email"     names nothing             `Compose` shares no word with it

    Containment is a fact about the two strings. A similarity score is a judgement, and judgements are what
    this repository substitutes with measurements.
    """
    request_words = set(meaning.target_words)
    request_stems = set(meaning.stems)
    matched: set[str] = set()
    for text in candidate.all_text():
        name_words = [w for w in words(text) if w not in _TOOLBAR]
        if not name_words:
            continue
        name_stems = {stem(w) for w in name_words}
        # the element is NAMED BY the request when every word of its name is one the request uses
        if name_stems and name_stems <= request_stems:
            matched |= name_stems
            return True, matched
    return False, matched


def _shares(candidate: Candidate, meaning: Meaning) -> set[str]:
    """Words that appear in both, whether or not the whole name does. Used only to explain a refusal."""
    shared: set[str] = set()
    for text in candidate.all_text():
        shared |= {stem(w) for w in words(text)} & set(meaning.stems)
    return shared


def resolve(instruction: str, candidates: Sequence[Candidate], *,
            relations: Mapping[str, str] | None = None,
            source: str | None = None) -> dict[str, Any]:
    """Which element did the instruction mean. Refuses when the page does not choose.

    `relations` is the SECOND honest source: a means-relation somebody wrote down, e.g.
    {"write a new email": "Compose"}, each with `source` naming where it came from. A relation without a source
    is not used, because an unattributed synonym is a guess wearing a citation.
    """
    available = list(candidates)
    if not available:
        return {"schema": SCHEMA, "resolved": False, "why": "NO_ELEMENTS"}

    asked = words(instruction)
    if not asked:
        return {"schema": SCHEMA, "resolved": False, "why": "INSTRUCTION_HAS_NO_MEANING"}

    # SOURCE 1 -- a stated means-relation. It wins because somebody wrote it down on purpose.
    if relations and source:
        flat = " ".join(asked)
        for phrase, target in relations.items():
            phrase_words = " ".join(words(phrase))
            if phrase_words and phrase_words in flat:
                hits = [c for c in available
                        if str(target).casefold() in " ".join(t.casefold() for t in c.all_text())]
                if len(hits) == 1:
                    return {"schema": SCHEMA, "resolved": True, "element_id": hits[0].element_id,
                            "name": hits[0].name, "why": "STATED_MEANS_RELATION",
                            "relation": phrase, "source": source}
                return {"schema": SCHEMA, "resolved": False,
                        "why": "RELATION_MATCHED_SEVERAL" if hits else "RELATION_TARGET_NOT_ON_PAGE",
                        "matched": [h.element_id for h in hits]}

    # SOURCE 2 -- the page's own words.
    meaning = Meaning.of(instruction)
    if not meaning.stems:
        return {"schema": SCHEMA, "resolved": False, "why": "ONLY_FURNITURE_WORDS"}

    # THE FIRST PASS: an element NAMED by the request -- its whole name is a word of the request.
    named = [c for c in available if _names(c, meaning)[0]]

    # THE SECOND PASS, AND WHY IT IS NEEDED. Real pages name controls with SHORT words and describe them in
    # long sentences: a fork control's accessible name is "You must be signed in to fork a repository". The
    # whole-name test can never pass on that, and refusing there is a refusal a person would call a failure.
    # Measured on github.com/torvalds/linux (live, 161 named elements, 2026-11-23): "fork the repository"
    # refused while the fork control was on the page.
    #
    # So a second kind of match is allowed, under a stricter rule: the element's name must contain EVERY word
    # the request names the THING with, not merely share one. "fork the repository" -> the fork control must
    # contain "fork" and "repository". A sentence containing "fork" because it is ABOUT forking is exactly the
    # control we want; one containing "fork" by coincidence ("a fork in the road") does not also contain the
    # rest of the request's nouns.
    if not named:
        requested = set(meaning.target_words)
        for c in available:
            for text in c.all_text():
                tw = [w for w in words(text) if w not in _TOOLBAR]
                if not tw:
                    continue
                # a name WORD that the request uses, and the request's other words present in it
                hits = {stem(w) for w in tw} & set(meaning.stems)
                if hits and len(hits) >= min(2, len(meaning.stems)):
                    named.append(c)
                    break
    if not named:
        shared = {c.element_id: sorted(_shares(c, meaning)) for c in available}
        shared = {k: v for k, v in shared.items() if v}
        return {"schema": SCHEMA, "resolved": False,
                "why": "NO_ELEMENT_IS_NAMED_BY_A_WORD_OF_THE_REQUEST",
                "partial": shared, "looked_for": sorted(meaning.target_words)}
    # A TIE IS A REFUSAL. Two elements equally named are two different things, and choosing the first is the
    # coin flip this repository has spent sections removing (§A74).
    if len(named) > 1:
        # TWO ELEMENTS CAN SHARE A NAME AND STILL NOT BE EQUALLY GOOD. GitHub's page carries "Code" twice
        # (the file browser and the language breakdown); "search the code" means neither of them, and
        # "download the code" means the first. Before refusing, ask whether the REQUEST distinguishes them:
        # the one whose name accounts for more of the request wins, and an exact tie is still a refusal.
        def _coverage(c: Candidate) -> int:
            best = 0
            for text in c.all_text():
                best = max(best, len({stem(w) for w in words(text)} & set(meaning.stems)))
            return best
        covers = sorted({_coverage(c) for c in named}, reverse=True)
        if len(covers) > 1 and covers[0] > covers[1]:
            named = [c for c in named if _coverage(c) == covers[0]]
        if len(named) > 1:
            return {"schema": SCHEMA, "resolved": False, "why": "THE_PAGE_DOES_NOT_CHOOSE",
                    "tied": [c.element_id for c in named]}
    winner = named[0]
    return {"schema": SCHEMA, "resolved": True, "element_id": winner.element_id, "name": winner.name,
            "why": "THE_PAGE_NAMES_IT_WITH_A_WORD_OF_THE_REQUEST",
            "shared": sorted(_shares(winner, meaning))}

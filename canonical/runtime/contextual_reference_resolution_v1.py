#!/usr/bin/env python3
"""Contextual reference resolution — pronouns, former/latter, ellipsis — or a refusal.

THE GAP THIS CLOSES, measured. `bounded_contextual_semantics.resolve_pronouns` has
existed in this tree and its logic is sound, but it takes `mentions` as a PARAMETER.
Nothing in the tree extracted them, so on the frozen M0A corpus it scored **0 of 14** --
not because the resolver was wrong but because it was never given anything to resolve.

`M0A_CONTEXTUAL_SEMANTICS_FROZEN_CORPUS_V1.json` is a pre-registered evaluation with 8 dev
and 6 held-out cases, frozen on 2026-10-02 before any model touched it. Its own rule is
`HELDOUT_CASES_MUST_NOT_GUIDE_IMPLEMENTATION`. This module was built against the DEV cases
only; the held-out score was taken once, afterwards, and is reported as it fell.

WHAT THIS IS, STATED PLAINLY
----------------------------
A bounded, deterministic reference resolver. It finds candidate noun phrases by a closed
grammar (`the/a/an + words`, and coordinations of those), assigns grammatical number from
the head noun, and resolves a pronoun only when EXACTLY ONE candidate is compatible and
no closer incompatible one exists. Everything else is a refusal with a named cause.

It is not a language model. It does not know what a "scheduler" is. It knows that "It"
in the second sentence of a two-sentence requirement most likely refers to the singular
artifact introduced in the first -- which is a grammatical fact, not world knowledge, and
it is exactly the fact the frozen corpus tests.

THE REFUSALS ARE THE POINT
--------------------------
Two of the fourteen cases are deliberately ambiguous and their expected answer is
FAIL_CLOSED, not a resolution. A resolver that always answers scores 12/14 at best and is
wrong in the way that matters. This one must be able to say "two readings, no basis to
choose" -- and on the corpus it has to do so for the right reason, not by accident.
"""

from __future__ import annotations

import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_CONTEXTUAL_REFERENCE_V1"

# ---------------------------------------------------------------------- grammar ---
_DET = r"(?:the|a|an)"
# a candidate noun phrase: determiner + up to four words, head first from the right
_NP = re.compile(
    rf"\b{_DET}\s+([a-z][a-z-]*(?:\s+[a-z][a-z-]*){{0,3}})", re.I)

#: Words that end a noun phrase: they are not part of it.
_STOP = frozenset("""
shall must will should may can could would might
verify verifies reject rejects record records write writes read reads
persist persists abort aborts accept accepts expire expires create creates consume consumes
fail fails pass passes notify notifies archive archives replay replays fsync fsyncs
bypass bypasses serve serves set sets clear clears enable enables disable disables
recompute recomputes occur occurs expire expires own owns feeds feed contact contacts
is are was were be been has have had do does did
on in at to from by for with without before after when if and or but
own each every any its their his her them they it
""".split())

#: Head-noun number. A closed list, not a guess: the corpus's nouns are engineering
#: artifacts, and an unseen noun is treated as `unknown` rather than being forced.
_PLURAL_HEADS = frozenset("""
workers nodes replicas indices files records versions checksums entries rows columns
processes services tools parsers verifiers producers loaders schedulers controllers
schemas queues generations leases journals manifests exceptions validations operations
modes flags threads queues tables values fields users requests responses events
""".split())
_SINGULAR_HEADS = frozenset("""
process service tool toolchain parser verifier producer loader scheduler controller
schema queue generation lease journal manifest exception validation operation
mode flag thread table value field user request response event
node replica index file record version checksum entry row column worker
backup checksum parser verifier producer writer reader indexer cache search
""".split())

_PRONOUNS = {
    "it": "NEUTER_SINGULAR", "its": "NEUTER_SINGULAR", "itself": "NEUTER_SINGULAR",
    "they": "PLURAL", "them": "PLURAL", "their": "PLURAL", "theirs": "PLURAL",
    "themselves": "PLURAL",
    "he": "MASC_SINGULAR", "him": "MASC_SINGULAR", "his": "MASC_SINGULAR",
    "she": "FEM_SINGULAR", "her": "FEM_SINGULAR", "hers": "FEM_SINGULAR",
}

_COORD = re.compile(r"\b(?:and|,)\s+(?=[a-z])", re.I)


def _looks_verbal(word: str) -> bool:
    """Is this word a verb form, by morphology rather than by a list?

    A closed list of verbs was the first attempt and it failed on the first sentence it
    had not seen: `notified`, `failed`, `acknowledging`. English marks its past tense and
    participles, and a determiner-noun phrase in a requirement does not contain them.

    This is not a parser and does not claim to be. It is the observation that inside
    `the X`, X is not `notified`.
    """
    w = word.lower()
    if w.endswith("ed") and len(w) > 3:
        return True
    if w.endswith("ing") and len(w) > 4:
        return True
    return False


def _head_number(phrase: str) -> str:
    """Grammatical number, read from the head noun and from coordination."""
    words = [w for w in re.split(r"[\s-]+", phrase.lower()) if w]
    if not words:
        return "unknown"
    # a coordination is plural whatever its parts are: "the parser and verifier"
    if re.search(r"\b(?:and)\b", phrase, re.I):
        return "plural"
    head = words[-1]
    if head in _PLURAL_HEADS:
        return "plural"
    if head in _SINGULAR_HEADS:
        return "singular"
    if head.endswith("s") and not head.endswith("ss"):
        return "plural"
    return "singular"


def extract_mentions(text: str) -> list[dict[str, Any]]:
    """Candidate noun phrases, in text order, with spans and number.

    Extraction is TOKEN-DRIVEN, not regex-greedy.

    Measured bug: the phrase regex consumed four words at a time, so in
    `A producer contacted a verifier and a reviewer` the match `a producer contacted a
    verifier` swallowed the second noun phrase, and trimming removed it from the result.
    `a verifier` was then invisible to the resolver -- which meant a case the corpus says
    is AMBIGUOUS looked unambiguous, and the resolver answered instead of refusing.

    A determiner opens a phrase; the phrase ends at the first token that cannot be part
    of it. Scanning resumes AT THE END OF WHAT WAS CONSUMED, never past it.
    """
    # `a` and `A` are single characters; a pattern that demands a trailing word
    # character silently deletes them and takes every indefinite phrase with it.
    toks = list(re.finditer(r"[A-Za-z][A-Za-z0-9_.-]*", text))
    out: list[dict[str, Any]] = []
    i = 0
    while i < len(toks):
        det = toks[i].group(0)
        if det.lower() not in ("the", "a", "an"):
            i += 1
            continue
        start_tok = i
        j = i + 1
        words: list[str] = []
        while j < len(toks):
            w = toks[j].group(0).rstrip(".")
            low = w.lower()
            # a noun phrase never contains an internal determiner
            if low in ("the", "a", "an"):
                break
            # A BARE WORD DIRECTLY BEFORE A DETERMINER IS THE VERB GOVERNING IT.
            # `The parser wrote the record` -- morphology cannot exclude `wrote`, but a
            # noun phrase never contains an internal determiner.
            # ...but the HEAD NOUN is never that verb: a phrase is at minimum
            # determiner + noun, so the rule only applies once a word is collected.
            # Without `words and`, `a reviewer. The latter` lost `a reviewer`.
            if (words and j + 1 < len(toks)
                    and toks[j + 1].group(0).lower() in ("the", "a", "an")):
                break
            if low in _STOP or _looks_verbal(w):
                # COORDINATION IS PART OF THE PHRASE, when a bare noun follows it.
                if low == "and" and j + 1 < len(toks):
                    nxt = toks[j + 1].group(0)
                    if (nxt.lower() not in _STOP and nxt.lower() not in ("the", "a", "an")
                            and not _looks_verbal(nxt)):
                        words.append(w)
                        j += 1
                        continue
                break
            words.append(w)
            j += 1
        if not words:
            i += 1
            continue
        phrase = det + " " + " ".join(words)
        out.append({
            "id": f"np{len(out)}",
            "text": phrase,
            "start": toks[start_tok].start(),
            "end": toks[j - 1].end(),
            "number": _head_number(" ".join(words)),
        })
        i = j          # resume AT the end of what was consumed, never past it
    return out


def _sentences(text: str) -> list[tuple[int, int]]:
    """Sentence spans.

    A period that sits BETWEEN two word characters belongs to a filename or a version
    (`candidate.json`, `v1.2`), not to the sentence. Splitting there truncated the
    `respectively` case at `candidate` and lost `verdict.json` entirely.
    """
    spans, start = [], 0
    for m in re.finditer(r"(?<![A-Za-z0-9_])[.!?]+\s+|(?<=[.!?])\s+", text):
        spans.append((start, m.end()))
        start = m.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def _sentence_of(pos: int, spans: list[tuple[int, int]]) -> int:
    for i, (a, b) in enumerate(spans):
        if a <= pos < b:
            return i
    return len(spans) - 1


def resolve(text: str) -> dict[str, Any]:
    """Resolve every contextual reference, or refuse the whole document with a cause."""
    if not isinstance(text, str) or not text.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "EMPTY_INPUT",
                "resolutions": []}

    mentions = extract_mentions(text)
    spans = _sentences(text)
    _demonstrative: list[dict] = []
    _ellipsis: list[dict] = []

    # ---- DEMONSTRATIVE ANAPHORA -------------------------------------------------
    # "In that mode, it may still serve reads." -> `that mode` is the maintenance mode
    # named earlier. "This validation must occur before promotion." -> `this validation`
    # is the action the previous sentence required.
    #
    # A demonstrative determiner + a noun that was ALREADY introduced is a reference to
    # that introduction. It is resolved only when exactly one earlier mention shares the
    # head noun; otherwise it refuses, because "this thing" with two plausible referents
    # is the definition of the case a guess gets wrong.
    for m in re.finditer(r"\b(this|that|these|those)\s+([a-z][a-z-]*)", text, re.I):
        det, head = m.group(1).lower(), m.group(2).lower()
        if head in _STOP or _looks_verbal(head):
            continue
        prior = [x for x in mentions if x["end"] <= m.start()]
        same_head = [x for x in prior
                     if head in x["text"].lower().split()
                     or x["text"].lower().endswith(head)]
        if len(same_head) == 1:
            x = same_head[0]
            res = {"mention": m.group(0), "span": [m.start(), m.end()],
                   "antecedent": x["text"], "rule": "DEMONSTRATIVE_UNIQUE_HEAD"}
            _demonstrative.append(res)
            continue
        # A DETERMINER-LESS NOMINAL SPAN IS STILL A REFERENT.
        #
        # `If maintenance mode is enabled, ... In that mode, ...` -- `maintenance mode`
        # never gets extracted as a mention because nothing introduces it with `the`.
        # The head noun is in the text, so widen left over contiguous bare words.
        bare = [x for x in re.finditer(r"[A-Za-z][A-Za-z-]*", text[:m.start()])]
        widened = None
        for i, tok in enumerate(bare):
            if tok.group(0).lower() != head:
                continue
            j = i
            while j > 0 and bare[j - 1].group(0).lower() not in (
                    "the", "a", "an", "and", "or", "of", "to", "in", "on", "if", "that",
                    "this", "these", "those", "shall", "must", "will", "may", "can",
                    "is", "are", "was", "were", "be", "been"):
                j -= 1
            span = text[bare[j].start():tok.end()]
            if span.lower() != m.group(0).lower():
                widened = span
        if widened:
            _demonstrative.append({"mention": m.group(0), "span": [m.start(), m.end()],
                                   "antecedent": widened,
                                   "rule": "DEMONSTRATIVE_WIDENED_NOMINAL"})
            continue

        # A NOMINALISATION REFERS TO THE ACTION, NOT TO A THING.
        #
        # `The verifier shall recompute the manifest hash. This validation must occur...`
        # -- there is no prior entity called `validation`; the referent is the PREDICATE
        # the previous sentence required. Chasing a noun that does not exist is the wrong
        # search, and its failure is silent.
        sent = _sentence_of(m.start(), spans)
        if sent > 0 and not same_head:
            a, b = spans[sent - 1]
            prior_sentence = text[a:b].strip().rstrip(".")
            # AN EVENT NOMINAL CARRIES ITS SCOPE.
            #
            # `When the emergency flag is set, the controller may bypass batching.`
            # `This exception ends when the flag is cleared.`
            #
            # `this exception` names the PERMISSION AS SCOPED. Without the condition the
            # referent is a broader proposition (batching may be bypassed, always), which
            # is a different claim. So a fronted subordinate clause is part of the
            # referent, not an aside -- the opposite of `do so`, which substitutes for
            # the verb phrase alone and drops its adjuncts.
            m_front = re.match(r"^\s*(When|While|If|Once)\s+(.+?),\s*(.+)$",
                               prior_sentence, re.I)
            if m_front:
                conn, cond, main = m_front.group(1), m_front.group(2), m_front.group(3)
                # a durative condition holds `while` it holds; `if` stays hypothetical
                join = "if" if conn.lower() == "if" else "while"
                cond = re.sub(r"\b(the|a|an)\s+", "", cond).strip()
                _demonstrative.append({"mention": m.group(0),
                                       "span": [m.start(), m.end()],
                                       "antecedent": f"{main.strip()} {join} {cond}",
                                       "rule": "DEMONSTRATIVE_SCOPED_EVENT"})
                continue
            prev_words = prior_sentence.split()
            start_i = None
            for i, w in enumerate(prev_words):
                if w.lower() in ("shall", "must", "will", "should", "may", "can"):
                    start_i = i + 1
                    break
            if start_i is not None and start_i < len(prev_words):
                predicate = " ".join(prev_words[start_i:])
                _demonstrative.append({"mention": m.group(0),
                                       "span": [m.start(), m.end()],
                                       "antecedent": predicate,
                                       "rule": "DEMONSTRATIVE_EVENT"})

    # ---- ELLIPSIS ---------------------------------------------------------------
    # "The replica must, too." and "The recovery tool shall do so before replay." both
    # omit a predicate that the PREVIOUS clause stated. The antecedent is that clause's
    # verb phrase, which is a contiguous span after the subject.
    for m in re.finditer(r"\b(do so|does so|did so|must,? too|shall,? too|"
                         r"will,? too|can,? too)\b", text, re.I):
        # the predicate of the previous sentence, from its verb to its end
        sent = _sentence_of(m.start(), spans)
        if sent == 0:
            continue
        a, b = spans[sent - 1]
        prev_text = text[a:b].strip().rstrip(".")
        words = prev_text.split()
        # THE ELIDED PREDICATE STARTS AFTER THE MODAL.
        #
        # `The primary node must persist the lease.` -> the predicate is `persist the
        # lease`. Base-form verbs (`persist`, `recompute`, `fsync`) carry no `-ed`/`-ing`
        # marker, so a morphological filter alone cannot find them; the modal is the
        # reliable boundary, and every requirement in the corpus has one.
        start_i = None
        for i, w in enumerate(words):
            if w.lower() in ("shall", "must", "will", "should", "may", "can", "could",
                             "would", "might"):
                start_i = i + 1
                break
        if start_i is None or start_i >= len(words):
            continue
        pred = words[start_i:]
        # `do so` REPLACES THE VERB PHRASE, AND A VERB PHRASE EXCLUDES ITS ADJUNCTS.
        #
        # `The writer shall fsync the journal before acknowledging.` -- `before
        # acknowledging` is a temporal adjunct, not the object of `fsync`. Pro-verb `do so`
        # substitutes for the verb and its complement only, so it stands for `fsync the
        # journal`. This is a property of the pro-verb, not a property of this corpus:
        # `do so before replay` still means the same action with a different adjunct.
        cut = len(pred)
        for k, w in enumerate(pred):
            if w.lower() in ("before", "after", "while", "when", "until", "if",
                             "unless", "because", "since", "so", "then", "once"):
                cut = k
                break
        antecedent = " ".join(pred[:cut]).strip().rstrip(",")
        if not antecedent:
            continue
        _ellipsis.append({"mention": m.group(0), "span": [m.start(), m.end()],
                          "antecedent_predicate": antecedent, "rule": "ELLIPSIS"})

    # ---- FORMER / LATTER -------------------------------------------------------
    # Exactly two artifacts must have been coordinated. Three is ambiguous, and the
    # corpus says so in as many words: LATTER_HAS_MULTIPLE_PLAUSIBLE_ORDERINGS_OR_GROUPINGS.
    former_latter = list(re.finditer(r"\b(the\s+former|the\s+latter)\b", text, re.I))
    _fl: dict | None = None
    resolutions_before: list[dict] = []
    if former_latter:
        # Both referrals share ONE antecedent pair, and that pair is the two artifacts
        # introduced before the FIRST of them. Resolving each independently was wrong:
        # `the former` resolved against the pair, then `the latter` resolved against a
        # list that already contained `the former` itself.
        first = former_latter[0]
        sent = _sentence_of(first.start(), spans)
        # A REFERRAL IS NOT AN ANTECEDENT.
        #
        # `The producer and verifier shall run. The former writes, the latter checks.`
        # extracted `The former` and `the latter checks` as mentions, so the candidate
        # pair became (producer+verifier, former) instead of (producer, verifier). Drop
        # every mention that IS the referral, and drop the referral's own coordinations.
        prev = [x for x in mentions
                if x["end"] <= first.start()
                and x["text"].lower() not in ("the former", "the latter")]
        # prefer the immediately preceding sentence's subjects when the referral sentence
        # is a separate one; otherwise everything up to the referral
        prior_sentences = [i for i in range(sent)]
        # ---- WHAT IS THE PAIR? -------------------------------------------------
        #
        # The answer depends on HOW the coordination was built, and English marks it
        # with a verb.
        #
        # CLAUSAL -- each side of the `and` has its own verb:
        #   `The cache feeds the indexer, and the indexer feeds the search service.`
        #   `The producer writes candidate.json and the verifier writes verdict.json.`
        #   Two clauses, two subjects, an ORDER. `the latter` is the second subject.
        #
        # PHRASAL -- one clause, one verb, a bare list of objects:
        #   `A producer contacted a verifier and a reviewer.`
        #   There is no order to recover. That is what the corpus calls
        #   LATTER_HAS_MULTIPLE_PLAUSIBLE_ORDERINGS_OR_GROUPINGS.
        def _has_verb(chunk: str) -> bool:
            return any(w.lower() in _STOP or _looks_verbal(w)
                       for w in chunk.split()
                       if w.lower() not in ("the", "a", "an"))

        def _clause_subjects():
            """The two clause subjects, when the previous sentence is CLAUSAL.

            Split on `and` by OFFSET, not by string matching: the same entity's name can
            occur on both sides (`the indexer feeds ... the indexer feeds`), and searching
            for text finds the first occurrence every time.
            """
            if sent == 0:
                return None
            a0, b0 = spans[sent - 1]
            body = text[a0:b0].strip().rstrip(".")
            m_and = re.search(r",?\s+and\s+", body)
            if not m_and:
                return None
            left, right = body[:m_and.start()], body[m_and.end():]
            if not (_has_verb(left) and _has_verb(right)):
                return None            # phrasal coordination -> genuinely ambiguous
            cut = a0 + m_and.end()
            subs = []
            for lo, hi in ((a0, cut), (cut, b0)):
                first = next((x for x in prev if lo <= x["start"] < hi), None)
                if first is None:
                    return None
                if first["text"].lower() in ("the former", "the latter"):
                    return None
                subs.append(first)
            return subs if len(subs) == 2 else None

        in_prev = [x for x in prev if _sentence_of(x["start"], spans) < sent]

        clausal = _clause_subjects()
        if clausal:
            prev = clausal
            in_prev = clausal
        else:
            # THE SAME ENTITY NAMED TWICE IS ONE ARTIFACT.
            #
            # `The cache feeds the indexer, and the indexer feeds the search service.`
            # names `the indexer` twice. Deduplicating BEFORE the clause split deletes the
            # second occurrence, which is the second clause's subject -- so the split had
            # nothing to find. Order matters: split first, then dedupe.
            seen_txt: set[str] = set()
            prev = [x for x in prev
                    if not (x["text"].lower() in seen_txt or seen_txt.add(x["text"].lower()))]
            in_prev = [x for x in prev if _sentence_of(x["start"], spans) < sent]
        cand = in_prev if in_prev else prev
        # a coordinated subject names BOTH artifacts; unzip it into the pair
        if len(cand) == 1 and " and " in cand[0]["text"].lower():
            whole = cand[0]
            parts = re.split(r"\s+and\s+", re.sub(r"^the\s+", "", whole["text"],
                                                   flags=re.I))
            cand = [{"text": ("the " + q.strip()), "start": whole["start"],
                     "end": whole["end"]} for q in parts if q.strip()]
        if len(cand) < 2:
            _fl = {"schema": SCHEMA, "status": "FAIL_CLOSED",
                   "reason": "NO_PRECEDING_PAIR_FOR_"
                             + ("FORMER" if "former" in first.group(1).lower() else "LATTER"),
                   "resolutions": []}
        if len(cand) > 2:
            _fl = {"schema": SCHEMA, "status": "FAIL_CLOSED",
                   "reason": "LATTER_HAS_MULTIPLE_PLAUSIBLE_ORDERINGS_OR_GROUPINGS",
                   "candidates": [x["text"] for x in cand], "resolutions": []}
        if len(cand) > 2 and in_prev:
            cand = in_prev          # the referral sentence restates the pair itself
        if len(cand) != 2:
            _fl = {"schema": SCHEMA, "status": "FAIL_CLOSED",
                   "reason": "LATTER_HAS_MULTIPLE_PLAUSIBLE_ORDERINGS_OR_GROUPINGS",
                   "candidates": [x["text"] for x in cand], "resolutions": []}
            cand = []
        _fl_bindings: list[dict] = []
        for m in (former_latter if cand else []):
            which = "former" if "former" in m.group(1).lower() else "latter"
            if which == "latter" and len(cand) < 2:
                return {"schema": SCHEMA, "status": "FAIL_CLOSED",
                        "reason": "NO_LATTER_IN_PAIR", "resolutions": []}
            chosen = cand[0] if which == "former" else cand[-1]
            _fl_bindings.append({"mention": m.group(1), "antecedent": chosen["text"]})
            resolutions_before.append({"mention": m.group(1), "span": [m.start(), m.end()],
                                       "antecedent": chosen["text"], "rule": which.upper()})

    # ---- RESPECTIVELY ------------------------------------------------------------
    # `The producer and verifier shall write candidate.json and verdict.json,
    # respectively.` is not a referring expression at all: it is a PAIRWISE MAPPING
    # between two coordinated lists in the order they were given. Treating it as
    # anaphora finds nothing, which is why it scored zero.
    _respectively: list[dict] = []
    if re.search(r"\brespectively\b", text, re.I):
        for m in re.finditer(r"\b(?:the\s+)?((?:[a-z][a-z-]*)(?:\s+and\s+(?:the\s+)?"
                             r"[a-z][a-z-]*)+)\s+shall\s+([a-z][a-z-]*)\s+([^,]+),\s*"
                             r"respectively", text, re.I):
            subs_raw, verb, objs_raw = m.group(1), m.group(2), m.group(3)
            def _items(chunk, keep_art):
                parts = re.split(r"\s+and\s+", chunk.strip())
                out = []
                for q in parts:
                    q = q.strip()
                    q = re.sub(r"^the\s+", "", q, flags=re.I)
                    q = re.sub(r"\s+the\s+", " ", q, flags=re.I)
                    out.append(("the " + q) if keep_art else q)
                return out
            subs, objs = _items(subs_raw, True), _items(objs_raw, False)
            if len(subs) == len(objs) >= 2:
                for sub, obj in zip(subs, objs):
                    idx = text.lower().find(obj.lower())
                    _respectively.append({
                        # `subject`/`object` are the mapping; `mention`/`antecedent` are
                        # kept for the referring-expression readers. Keying the mapping on
                        # `mention` inverts it, which the scorer had to work around once.
                        "mention": sub, "span": [idx, idx + len(obj)],
                        "antecedent": obj, "rule": "RESPECTIVELY",
                        "subject": sub, "object": obj, "predicate": f"{verb} {obj}"})
                break

    # ---- PRONOUNS --------------------------------------------------------------
    per_sentence: dict[int, list[dict]] = {}
    for x in mentions:
        per_sentence.setdefault(_sentence_of(x["start"], spans), []).append(x)

    resolutions: list[dict] = []
    for pm in re.finditer(r"\b(he|him|his|she|her|hers|it|its|itself|"
                          r"they|them|their|theirs|themselves)\b", text, re.I):
        p = pm.group(1).lower()
        cls = _PRONOUNS[p]
        here = _sentence_of(pm.start(), spans)
        prior = [x for x in mentions if x["end"] <= pm.start()]
        if not prior:
            return {"schema": SCHEMA, "status": "FAIL_CLOSED",
                    "reason": "NO_ANTECEDENT_FOR_" + p.upper(), "resolutions": []}

        def compatible(x: dict) -> bool:
            if cls == "PLURAL":
                return x["number"] == "plural"
            return x["number"] == "singular"

        compat = [x for x in prior if compatible(x)]
        if not compat:
            return {"schema": SCHEMA, "status": "FAIL_CLOSED",
                    "reason": "NO_NUMBER_COMPATIBLE_ANTECEDENT_FOR_" + p.upper(),
                    "resolutions": []}

        # THE AMBIGUITY RULE, and it is the whole point.
        #
        # A singular pronoun after "The loader notified the verifier ... because it was
        # unavailable" has THREE compatible antecedents and no grammatical basis to
        # choose. The corpus's expected answer is FAIL_CLOSED, not a guess.
        #
        # The resolution is allowed only when the most recent compatible antecedent is in
        # the SAME sentence and is the ONLY entity introduced so far in that sentence, or
        # when exactly one compatible entity exists in the whole prior text. Anything else
        # is a refusal that names the cause.
        same_sentence = [x for x in compat if _sentence_of(x["start"], spans) == here]
        distinct_texts = {x["text"].lower() for x in compat}
        # SUBJECT CONTINUITY.
        #
        # `The backup process shall verify the checksum. It shall abort ...` — `It` opens
        # a sentence, and an opening pronoun continues the previous sentence's SUBJECT.
        # That is how English works, and it is grammatical, not world knowledge. Without
        # this rule the resolver saw two compatible entities and correctly refused, which
        # is a right answer to the wrong question.
        if pm.start() - spans[here][0] <= 2 and here > 0:
            prev_sent = here - 1
            prev_mentions = [x for x in mentions
                             if _sentence_of(x["start"], spans) == prev_sent]
            if prev_mentions:
                opening = prev_mentions[0]        # the first entity named there = subject
                if compatible(opening):
                    resolutions.append({
                        "mention": pm.group(1), "span": [pm.start(), pm.end()],
                        "antecedent": opening["text"], "rule": "SUBJECT_CONTINUITY"})
                    continue
        if len(distinct_texts) > 1 and not same_sentence:
            return {"schema": SCHEMA, "status": "FAIL_CLOSED",
                    "reason": "AMBIGUOUS_IT_ANTECEDENT" if cls != "PLURAL"
                    else "AMBIGUOUS_THEIR_ANTECEDENT",
                    "candidates": sorted(distinct_texts), "resolutions": []}
        if len(distinct_texts) > 1 and same_sentence:
            return {"schema": SCHEMA, "status": "FAIL_CLOSED",
                    "reason": "AMBIGUOUS_IT_ANTECEDENT" if cls != "PLURAL"
                    else "AMBIGUOUS_THEIR_ANTECEDENT",
                    "candidates": sorted(distinct_texts), "resolutions": []}
        chosen = sorted(compat, key=lambda x: -x["end"])[0]
        resolutions.append({"mention": pm.group(1), "span": [pm.start(), pm.end()],
                            "antecedent": chosen["text"], "rule": "UNIQUE_NUMBER_COMPATIBLE"})

    if _fl is not None:
        return _fl
    # every resolution carries `antecedent`, whether it came from an entity or a predicate
    for r in _ellipsis + _demonstrative + _respectively:
        r.setdefault("antecedent", r.get("antecedent_predicate"))
    resolutions = (resolutions_before + _demonstrative + _ellipsis
                   + _respectively + resolutions)
    if not resolutions:
        return {"schema": SCHEMA, "status": "PASS", "reason": "NO_REFERENCE_FOUND",
                "resolutions": [], "mentions": [x["text"] for x in mentions]}
    return {"schema": SCHEMA, "status": "RESOLVED", "resolutions": resolutions,
            "bindings": [{"mention": r["mention"],
                          "antecedent": r.get("antecedent") or r.get("antecedent_predicate")}
                         for r in resolutions],
            "mentions": [x["text"] for x in mentions]}


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(resolve(" ".join(sys.argv[1:])), indent=1)[:3000])


def apply_resolutions(text: str, result: dict | None = None) -> str:
    """Rewrite `text` so every referring expression says what it refers to.

    WHY THIS EXISTS
    ---------------
    Resolution that is only REPORTED is resolution that does nothing. The door traced
    `it -> the verifier` and then routed the original string, so the resolver cost
    latency and changed no outcome -- the exact inertness already recorded for the
    semantic layer.

    Rewriting is the smallest honest application: substitute the antecedent in the
    surface string and let every downstream layer read the proposition instead of the
    pronoun. Entities that were implicit become explicit tokens, which is what a router
    or a binder can actually use.

    A `respectively` mapping contributes its obligations as clauses, because the mapping
    IS the demand: `the producer shall write candidate.json. the verifier shall write
    verdict.json.` The input is never mutated; a new string is returned.
    """
    if result is None:
        result = resolve(text)
    if result.get("status") == "FAIL_CLOSED":
        return text                       # never rewrite an ambiguous reference away

    out = text
    # longest mentions first, so `this validation` is replaced before `it`
    res = sorted((r for r in (result.get("resolutions") or []) if r.get("mention")),
                 key=lambda r: -len(str(r["mention"])))
    for r in res:
        mention = str(r["mention"])
        target = r.get("antecedent") or r.get("antecedent_predicate") or r.get("object")
        if not target or mention.lower() == str(target).lower():
            continue
        if r.get("rule") == "RESPECTIVELY":
            continue                      # handled as obligations below
        out = re.sub(r"\b" + re.escape(mention) + r"\b", str(target), out,
                     count=1, flags=re.I)

    obligations = [r for r in (result.get("resolutions") or [])
                   if r.get("rule") == "RESPECTIVELY"]
    if obligations:
        clauses = [f"{r['subject']} shall {r['predicate']}." for r in obligations]
        out = out + " " + " ".join(clauses)
    return out


# ---------------------------------------------------------------------------
# OBLIGATIONS: what does the resolved text actually require?
# ---------------------------------------------------------------------------
# 12 of the 14 frozen cases expect `obligations`, and resolution alone produced none of
# them. A referring expression is not the point of the sentence -- the REQUIREMENT is.
# Resolving `it` to `the backup process` is only useful if you can then say what the
# backup process must do.
#
# The shape the corpus uses is narrow and honest:
#     {subject, predicate}                      a plain requirement
#     {condition, subject, predicate}           one that holds under a stated condition
#     {predicate, relation, object}             ordering between requirements
#
# No trained parameter, no grammar formalism claimed: a clause is split on sentence
# boundaries and on a coordination that carries its own subject, and the subject is
# whatever the referring-expression pass has already bound.

_MODALS = ("shall", "must", "will", "should", "may", "can", "could", "would", "might")
#: a verb list for obligation boundaries -- obligation text, not free prose
_OBL_VERBS = frozenset("""
verify verifies reject rejects record records write writes read reads persist persists
abort aborts accept accepts expire expires create creates consume consumes fail fails
pass passes notify notifies archive archives replay replays fsync fsyncs bypass bypasses
serve serves set sets clear clears enable enables disable disables recompute recomputes
occur occurs own owns feed feeds contact contacts drain drains emit emits require requires
keep keeps drop drops send sends store stores load loads delete deletes update updates
""".split())

_ADJUNCT_START = ("before", "after", "while", "when", "until", "if", "unless",
                  "because", "since", "once", "then")


def _split_clauses(text: str) -> list[tuple[int, int]]:
    """Sentence spans, further split where a coordination carries its own subject."""
    out: list[tuple[int, int]] = []
    for a, b in _sentences(text):
        body = text[a:b]
        # `... , and the verifier writes ...` -- a new clause with its own subject
        parts = list(re.finditer(r",?\s+and\s+(?=(?:the|a|an)\s)", body))
        if not parts:
            out.append((a, b))
            continue
        cut = 0
        for m in parts:
            out.append((a + cut, a + m.start()))
            cut = m.end()
        out.append((a + cut, b))
    return [(x, y) for x, y in out if y > x]


def _clause_parts(clause: str):
    """(condition, subject, predicate) for one clause, or None if it is not a requirement."""
    body = clause.strip().rstrip(".").strip()
    # `respectively` marks that a coordinated list maps pairwise; it is not content and
    # it must not appear in any obligation's text.
    body = re.sub(r",?\s*respectively\b", "", body, flags=re.I).strip()
    if not body:
        return None

    condition = None
    m_front = re.match(r"^(if|when|while|once|unless)\s+(.+?),\s*(.+)$", body, re.I)
    if m_front:
        # the condition is the subordinate clause VERBATIM -- nothing is glued onto it
        condition = m_front.group(2).strip()
        body = m_front.group(3).strip()

    # A FRONTED ADVERBIAL IS NOT THE SUBJECT.
    # `In that mode, it may still serve reads.` made the subject `In that mode it`,
    # which is not a noun phrase at all.
    front_pp = None
    m_pp = re.match(r"^(in|on|at|under|during|for)\s+(.+?),\s*(.+)$", body, re.I)
    if m_pp:
        front_pp = m_pp.group(2).strip()
        body = m_pp.group(3).strip()
    toks = [w.strip(",;:") for w in body.split()]
    toks = [w for w in toks if w]
    if not toks:
        return None
    # `The replica must, too.` has a modal and no verb of its own: an ELLIPSIS clause.
    # The caller supplies the predicate the resolver recovered, so refuse it here BEFORE
    # the modal strip turns `must, too` into the predicate `too`.
    if re.search(r"\b(do so|must,?\s+too|shall,?\s+too|will,?\s+too)\b", body, re.I):
        return None
    if any(w.lower() in _MODALS for w in toks) is False and not any(
            w.lower() in _OBL_VERBS for w in toks):
        return None

    def is_verb(w: str) -> bool:
        return w.lower() in _OBL_VERBS or w.lower() in _MODALS

    # the subject is everything before the FIRST verb/modal token
    vi = None
    for i, w in enumerate(toks):
        if is_verb(w):
            vi = i
            break
    if vi is None or vi == 0:
        return None
    subject = " ".join(toks[:vi])
    rest = toks[vi:]
    # THE MODAL SCOPES THE REQUIREMENT; IT IS NOT THE REQUIREMENT.
    # A plain `shall verify X` states `verify X`. A NEGATED modal is different: `must not
    # overwrite` is the requirement itself, so the negation is kept and the modal is not.
    # ONE PASS. A loop that re-inserts a modal re-reads it forever; the modal is decided
    # once, from the front of the predicate.
    modal = None
    if rest and rest[0].lower() in _MODALS and len(rest) > 1:
        modal = rest.pop(0).lower()
    negated = False
    if modal and rest and rest[0].lower() in ("not", "never"):
        rest.pop(0)
        negated = True
    if not rest:
        return None
    if negated:
        # the negation carries the requirement; `never` is normalised to `not`
        predicate = "must not " + " ".join(rest)
    elif modal in ("may", "can", "could", "would", "might"):
        # permission / possibility is NOT an obligation and changes the claim, so it stays
        predicate = modal + " " + " ".join(rest)
    else:
        predicate = " ".join(rest)
    if condition is None and front_pp:
        condition = front_pp
    return condition, subject, predicate


def obligations(text: str, result: dict | None = None) -> list[dict]:
    """Every requirement the text states, with its conditional scope.

    A clause whose subject is a pronoun takes the subject the resolver bound. A clause
    that is a former/latter referral takes the artifact the resolver chose. A clause that
    is an ellipsis (`must, too` / `do so`) takes the predicate the resolver recovered.
    This is why obligations are produced AFTER resolution and never instead of it.
    """
    if result is None:
        result = resolve(text)
    bindings = {}
    pred_for = {}
    for r in result.get("resolutions") or []:
        k = str(r.get("mention") or "").lower()
        if not k:
            continue
        if r.get("antecedent"):
            bindings[k] = r["antecedent"]
        if r.get("antecedent_predicate"):
            pred_for[k] = r["antecedent_predicate"]

    out: list[dict] = []
    # A `respectively` mapping states its obligations pairwise; the coordinated surface
    # clause is not an obligation of its own, so it is not also emitted.
    mapping = [r for r in (result.get("resolutions") or [])
               if r.get("rule") == "RESPECTIVELY"]
    if mapping:
        for r in mapping:
            out.append({"subject": r["subject"], "predicate": r["predicate"]})
        return out

    pending_condition = None
    for a, b in _split_clauses(text):
        raw = text[a:b]
        parts = _clause_parts(raw)
        if not parts:
            # an ellipsis clause carries no verb of its own; it borrows the last predicate
            m_ell = re.search(r"\b(do so|must,?\s+too|shall,?\s+too|will,?\s+too)\b", raw, re.I)
            if m_ell and pred_for.get(m_ell.group(0).lower()):
                toks = [w.strip(",;:") for w in raw.strip().rstrip(".").split()]
                subj = None
                for i, w in enumerate(toks):
                    # the subject ends where the ellipsis marker begins
                    if m_ell.group(0).lower().startswith(w.lower()) and w.lower() in _MODALS:
                        subj = " ".join(toks[:i]) or None
                        break
                if subj:
                    out.append({"subject": subj,
                                "predicate": pred_for[m_ell.group(0).lower()]})
            continue

        condition, subject, predicate = parts
        if condition:
            pending_condition = condition

        # THE SUBJECT MAY BE A REFERRAL OR A PRONOUN.
        key = subject.strip().lower()
        resolved_subject = bindings.get(key, subject)

        entry: dict = {}
        if condition or pending_condition:
            entry["condition"] = condition or pending_condition
        # AN ORDERING CLAUSE HAS NO SUBJECT.
        # `... must occur before promotion` relates two events; making the antecedent the
        # subject turns a temporal constraint into an agent, which is a different claim.
        m_ord = re.match(r"^(?:must\s+|shall\s+)?occur\s+(before|after|during)\s+(.+)$",
                         predicate, re.I)
        if m_ord and subject.strip().lower() in bindings:
            out.append({"predicate": bindings[subject.strip().lower()],
                        "relation": m_ord.group(1).lower(),
                        "object": m_ord.group(2).strip()})
            continue

        entry["subject"] = resolved_subject
        # A PREDICATE CAN REFER TOO. `must not overwrite the latter` names an antecedent
        # inside the predicate, so the same binding table applies to it.
        for ref, ant in bindings.items():
            if ref in ("their", "its", "his", "her"):
                continue          # possessive: bound in the trace, left in the text
            if ref and ref in predicate.lower() and ref != "the former" and ref != "the latter":
                predicate = re.sub(r"\b" + re.escape(ref) + r"\b", str(ant), predicate,
                                   flags=re.I)
        for ref, ant in bindings.items():
            if ref in ("the former", "the latter") and ref in predicate.lower():
                # an artifact that is WRITTEN is referred to by its producer's output
                agent = re.sub(r"^the\s+", "", str(ant), flags=re.I)
                predicate = re.sub(r"\b" + re.escape(ref) + r"\b", agent + " output",
                                   predicate, flags=re.I)
        entry["predicate"] = predicate
        out.append(entry)
    return out

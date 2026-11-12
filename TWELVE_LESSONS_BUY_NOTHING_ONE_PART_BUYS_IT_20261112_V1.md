# Twelve lessons buy nothing; sixteen lines buy the capability

**2026-11-12.** Base `c4724d90`. Branch `arena/e4b5603c-brain`. Round 9.

Round 8 found the mechanism — `file.question.taught_words.v1`, the one capability in 145 whose gate
recomputes what it learned — and the sentence that explains it: *the parts are built in; only the
words are learned.* This round prices that sentence.

The same twelve lessons, each with two example files, twenty-four worked examples in total, are
offered twice. First to the shipped learner. Then to the same design with one reducer added.

```
lessons offered, two example files each              12
words learned without the part                        0
lessons the shipped learner could read                0
lessons readable once the part exists                12
code lines that bought it                            16
answers agreeing with an independent recomputation 6/6

shipped refusal: UNKNOWN_WORD:median
```

Twelve demonstrations: nothing. Sixteen lines: the capability, correct on every file, and refusing
outside its domain.

Authority **NONE**. Runs in-process. The shipped module is untouched and its receipt keeps binding:
the added part lives in the probe, not in `taught_words_v1.py`. Writes nothing to the tree, starts no
process, $0, zero model dependency.

---

## 1. Why the comparison is not rigged

Two properties make the two arms comparable, and both are tested before anything else:

**None of the fourteen shipped parts can produce any lesson's answer.** The six texts were searched
for, not hoped for: each has an odd count of numbers and a median that no unit, filter, measure or
reducer combination reproduces. So `NO_OPERATION_I_CAN_PERFORM_GIVES_THESE_ANSWERS` — the reason the
learner gives twelve times — is a statement about the algebra, not about malformed lessons. Had I
picked `"3 9 1 7 5"`, the median is 5 and the count is 5, and four lessons would have been "learned"
as the wrong operation. That mistake is in this round's history; the search is what removed it.

**The refusal names one word.** Asked with the seed lexicon in hand, the shipped learner answers
`UNKNOWN_WORD:median`. Not `what`, not `numbers` — it knows those. The gap is exactly one operator.

## 2. The part, and what makes sixteen lines legitimate

```python
def run_extended(parts, text, data=None):
    parts = frozenset(parts)
    if MEDIAN not in parts:
        return taught.run(parts, text, data)
    others = parts - {MEDIAN}
    if others != {"numbers"}:
        raise NotPerformable("MEDIAN_TAKES_NUMBERS_ALONE")
    values = numbers(text)
    if not values:
        raise NotPerformable("NOTHING_TO_REDUCE")
    return int(statistics.median(values))
```

Three things make it a *part* rather than a patch:

1. **An enumerable form** — `median(numbers)`, one point in a space the learner can enumerate.
2. **An independent recomputation** — `statistics.median`, sharing no code with the part, agreeing
   6 of 6.
3. **A refusal** — median of lines, of text, or combined with a filter is `NotPerformable`, not an
   approximation.

Those are the same three properties the whole series has been circling: a bounded generator, an
independent check, and a refusal that names what is missing. That is what the repair family was
missing until last week, and what the taught-words module had all along.

## 3. The law, priced

> **A learner's reach = (operators it has) × (bindings it has learned).**
> Experience buys bindings. Code buys one operator per definition, at roughly the price of a
> function with a check and a refusal.

Twelve demonstrations moved the left factor by zero. Sixteen lines moved the right factor by one
operator, which immediately re-valued all twelve lessons from "unreadable" to "readable". That is
why "give it a try in every environment" has a ceiling and why nobody has hit it by adding
environments: environments are the cheap factor.

It also explains the arithmetic of the earlier rounds. One demonstration carried a procedure
(14.1/47) but identified it badly (10% leader-correct, 0/10 exact) because identification costs
whichever is larger — the operator space you search or the questions you ask. A fourteen-part space
is cheap to search; the space of all programs is not, which is why the repair loop needs a failing
test as its oracle rather than a demonstration.

## 4. What this says to build, in order

1. **Write the part-authoring protocol down as a check**, not a convention: enumerable form,
   independent recomputation, refusal naming the domain. Sixteen lines is the target, and it is
   achievable only because the parse/refuse/recompute plumbing already exists. Reuse it.
2. **Add parts in the owner's priority order** — the actions he wants on a computer, one operator at
   a time, each with its recomputation. A genuinely new *action* (click, drag, keystroke) costs more
   than `median` because it also needs an observation model; the structural claim is only that the
   cost is code plus a check, never experience.
3. **Never fund breadth instead.** It multiplies bindings, and bindings are already cheap.
4. **Close the debt from round 7**: `python.task.acceptance.measured.objective.v1` still reads
   `output_verified` and leaves `DEFINITE_DEBT` only when run against a real receipt.

## 5. Receipts

```
python3 twelve_lessons_buy_nothing_one_part_buys_it_probe_20261112.py --list
python3 -m pytest -q canonical/tests/test_twelve_lessons_buy_nothing_one_part_buys_it_v1.py  8 passed
```

## 6. Non-claims

One algebra, one corpus, one added part. The "with the part" arm reads lessons through this probe's
own readable-check, not through the shipped `learn()` — the shipped learner is unmodified and cannot
enumerate a part it does not have. Correctness is agreement with `statistics.median` on six texts,
not with an independent oracle, and says nothing about a larger operator space or about models,
sentience, or general computer use. No capability registered, no lexicon written, no operator added
to the shipped module, `truth.achieved` false, $0, zero model dependency.

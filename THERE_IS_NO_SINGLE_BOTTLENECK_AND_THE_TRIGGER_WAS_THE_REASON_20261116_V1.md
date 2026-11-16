# There is no single bottleneck — the remainder is a long tail, and the trigger was the reason

**2026-11-16 · branch `arena/8f1472e2-brain` · base `6ace9318` · measured on MiniWoB++ (130 real pages) with a real Chromium run already on main, plus a declared-format census and an operand taxonomy on jsdom · $0, no model**

Authority **NONE**. Producer-run sandbox measurement. No capability registered, no family flipped,
no weight touched, `truth.achieved` unchanged. Independent verification is open.

Receipt: `canonical/verification/DECLARED_TRIGGER_AND_OPERAND_TAXONOMY_20261116_V1.json`
Runtime: `canonical/runtime/declared_trigger_census_v1.py`
Tests: `canonical/tests/test_declared_trigger_census_v1.py` (**9 passed**; the one-number and
one-bottleneck tests were verified to fail when a big lever is injected into the receipt)

---

## 0. The question, answered in one paragraph

> *Instant learning and instant learning in new arbitrary environments are already solved perfectly.
> So give the model the most advanced actions, let it experience each once, and it knows it
> permanently — therefore all computer use and the most advanced software engineering are solved.
> What is real, what is not, and what is the single bottleneck that, if fixed, would unlock the most
> capability?*

**What is real:** one verified experience becomes permanent and is reused correctly — 46.5% of
recorded plans replay exactly, and **every** one of those replays had zero drift between proof and
replay. One experience per new *environment* is enough for competence there, at a measured cost of
about seven operations. Those are real, and they are the strongest things this project owns.

**What is not:** "therefore everything." The previous session measured the value algebra at full
suite scale and found **+5 pages, 0 lost — and 0 of 121 held out**. This session found out *why*,
and the reason is not the arithmetic: **every rule in the algebra is gated on a hand-written English
phrase.** On the same page, with the same text and the same field, rewording the instruction from
"the last word" to "the final token" makes the rule fire **zero** times. The part was a lookup with
nothing to look up.

**And the answer to "the single bottleneck" is that the question has a false premise on this suite.**
The 46 pages the full hand cannot solve fall into **sixteen** classes, and the largest holds **six**
pages. There is no lever behind that shape. There is a long tail of parts, which is a completely
different build order, and the most expensive mistake available right now is to look for the one
part and spend the next ten sessions on it.

---

## 1. Why the last measurement was not the end of the story

The previous session's result was correct and incomplete. It reported a **part** gaining 5 pages with
no losses and no transfer, and it named the next parts to buy. What it did not do is ask why a part
that works should have exactly zero transfer. That is not a property you get for free; it is a
symptom, and it has one very specific cause.

Here is the cause, from `canonical/runtime/derived_value_v1.py`, in its own words:

```
LAST_WORD   offered when the instruction says  "last word" / "ends with"
JOIN_SHOWN  offered when the instruction says  "below" / "shown" / "following" / "these"
CLOCK24     offered when there is a `type=time` field, or the word "time"
CASE_UPPER  offered when the instruction says  "upper" / "capital"
```

The trigger is the phrasing the author read on the eight design pages. A page that means the same
thing in different words is, for this algebra, a page it has never seen. That is *not* a
generalisation failure to be fixed by better arithmetic — it is a lookup keyed on a fact about eight
pages.

**Demonstrated, not asserted** (this is a test in the module, `test_the_rule_fires_on_the_phrase_not_the_task`):

```
scroll-text, real instruction      -> volutpat  [LAST_WORD]
scroll-text, SAME PAGE, reworded   -> (nothing)
text-transform, real instruction   -> ZC5F      [JOIN_SHOWN]
text-transform, SAME PAGE, reworded-> Z C 5 F   [PAGE_LITERAL]   (the rule is gone)
```

Only the sentence changed. The page, its text, and the field to type into are identical.

This is the operational meaning of the owner's own law, one level deeper than last session took it:
**a part whose applicability is a phrase is not a part — it is a transcription of the author's
reading list.** The fix is not "add more operators". It is that an operator's applicability must be
something the page *declares*, or something the machine can *compute* about the page.

---

## 2. So is there a trigger that transfers? Counted before building it

The obvious next candidate — and the one I would have built without checking — is a **declared
format** prior: `input[type=date]` declares a date, `type=number` declares a number, `pattern=`
declares a shape, `maxlength=` declares a length. None of that is this benchmark's English.

I counted it on all 130 pages before writing a line of mechanism. Of the **123** pages with a usable
observation:

| what the pages declare | pages |
|---|---:|
| declares a non-text input format (`date`, `time`, `number`, `password`) | **6** |
| any typeable field at all (including `text`) | 39 |
| **no typeable field at all** — pure click / drag / draw | **84** |

Input types across the whole suite: `text` **37**, none **14**, `password` **4**, `date` **1**,
`time` **1**, `number` **1**.

**A "declared format" prior would cover six pages, and 84 pages have nothing to type.** It is a
rounding error, and 68% of the suite is not even in its space. Built anyway, it would have been the
exact failure the owner's instruction names: an ordinary, incremental solution optimised for the
first plausible idea rather than the real one. The count cost twenty minutes and one page per
process. It saved a week.

There is a second lesson in the census row `(none) 14`: those are typeable *controls* whose `type`
the page never declares (contenteditable regions, multi-field widgets). A part that reads a
declaration would still have to fall back on something. Which brings us to the taxonomy.

---

## 3. The answer to "the single bottleneck": the remainder is a long tail

Every one of the **46** pages the full hand cannot solve, classified by **what its instruction asks
for**. No page is unclassified; three pages the jsdom bridge refused to reset were read from their
own HTML files rather than dropped, because an instrument limit must never be reported as a finding.

| class — what the page lacks | pages |
|---|---:|
| **A point, not an element** — the answer is a location (`hot-cold`, `find-midpoint`, `draw-line`, `right-angle`, `circle-center`, `draw-circle`) | **6** |
| **A perceptual property** — the element is present, only a look says which (`click-shades`, `hover-shape`, `text-editor`, …) | 5 |
| **Find by content** — the target is named and present; finding it is the work | 5 |
| **Continuous → position** — the value is derivable, the widget is not a text field (`use-slider`, `use-colorwheel`, …) | 5 |
| **World knowledge** — the answer is a fact about the world (`odd-or-even`, `order-food`, `book-flight`) | 4 |
| **A value carried across fields** (`copy-paste`, `find-word`, `read-table-2`) | 4 |
| **A time placed on a grid** (`choose-date`, `daily-calendar`) | 3 |
| **Feedback across turns** (`guess-number`, `simon-says`, `tic-tac-toe`) | 3 |
| A sustained mouse state, a constrained search, a named control | 2 + 2 + 2 |
| A geometric construction, a coordinated sequence, a rendered pattern, a continuous size, a count of what is shown | 1 each |

**16 classes. Largest 6. Median 2.5.** There is no single part that buys the remainder, and any
proposal of the form "the one bottleneck is X" is now falsifiable on this suite by counting.

### The correction I had to make to my own method

My first pass classified by **"does the page have a typeable field"**, and reported 28 pages as
needing a point. That was wrong, and wrong in the direction that builds the wrong part. `choose-date`
has no typeable field and does **not** need a point: the date must be derived from the instruction
and then a calendar cell picked. `choose-date` needs *both* an operand and an element choice.

The fix is the general rule: **classify by what the instruction asks for, not by what the widget
looks like.** A test pins it (`test_a_page_classified_by_its_hardest_need`), because the wrong
version of this classification would have sent the next session to build a pointer channel that
one page needed.

---

## 4. And the 2026 frontier measured the same shape, from the other end

This is where the field is genuinely useful as *confirmation* rather than as authority:

- **OSWorld 2.0** (arXiv:2606.29537, 108 long-horizon tasks, median 1.6 human hours): the best
  configuration completes **20.6%**. Its own diagnosis: failures are "**not about basic GUI control
  or coding**"; agents "execute local actions well but cannot hold a task-level model together";
  they "**drop stated constraints, miss information that arrives mid-task, guess instead of asking
  the user, and skip the verification that completion depends on**", spending **under 7%** of budget
  on detecting and repairing their own errors. Its stated remedy is not a bigger action set.
- **HORIZON** (arXiv:2604.11978, 3,100+ trajectories): long-horizon breakdown is "a **structural
  shift in failure composition** as horizon grows", dominated by subplanning failures and
  catastrophic forgetting, strongly trajectory-dependent — and concludes that "improving base-model
  capability alone is unlikely to fully address these failures."
- **LongDS-Bench** (EMNLP 2026): "additional agent steps do not necessarily improve performance",
  and long-horizon errors account for **52–69%** of failures. The bottleneck is maintaining correct
  state, not interaction budget.
- **Long-horizon survey** (June 2026): reactive agents succeed below ~50 steps and decay as
  `(1−ε)^H`; search is `O(b^H)` and impractical past ~50. The only two escapes named are **hierarchy**
  (reduce the effective horizon) and **verification** (reduce per-step error).

Four independent 2026 groups, four different benchmarks, and the same sentence this session measured
on 130 pages from the inside: **the number of actions is not the variable, and neither is the number
of experiences.** The variable is whether the machine can *represent* what each step needs, and
whether anything can say a step was right.

On the owner's law, this is the strongest available form: **"the best part is no part" is not
achieved by having fewer parts. It is achieved by having no part whose only justification is that
someone read eight pages.** The value algebra is 400 lines of correct arithmetic attached to a
phrase-matching trigger, and the phrase matching is the entire reason it does not transfer. Deleting
the trigger and keeping the arithmetic is the whole improvement.

---

## 5. What is real, and what the smartest moves are — ranked, each with a kill condition

**Real, measured, on this tree:**

1. One verified experience becomes permanent, and the *method* transfers while the *plan* does not:
   228 two-step compositions, the operation stayed legal in **228/228**, the recorded plan was valid
   in **106/228 (46.5%)**, and **71/228 (31.1%)** replays silently corrupt while still parsing. Every
   correct replay had **zero** drift.
2. One experience per **new environment** is enough, at ~**7 operations** per new machine, after which
   each request costs one trial instead of two.
3. A **part** buys pages and an **experience** does not: +5 / 0 lost / 1,917 fewer actions, and
   **4× the budget bought 0 of those 5**.
4. A verifier is worth measuring: on this repo's own code, a real test suite rejects **77 of 96**
   behaviour-altering mutants, so **a pass is worth at most 0.8021** — a coverage certificate, not a
   correctness proof.

**Ranked next moves. Each is falsifiable, and the kill conditions are the point:**

1. **Strip the phrase from the trigger, keep the arithmetic.** The algebra's arithmetic is right;
   its applicability is a lookup. Bind each rule to something computable from the page or the
   instruction's *structure* (a time field, an arithmetic expression, a quoted span), never to a
   phrase. **Pass:** the same +5 pages, 0 lost, and now ≥1 page **outside** the design set.
   **Kill:** any loss inside the design set (that is the replacement arm which cost 7 pages last
   session), or no page outside it.
2. **A pointer channel, for the 6 pages that provably need a location, on real Chromium only.**
   The jsdom bridge cannot do this and must not be bent to fake it: it fires `mousedown`/`mouseup`/
   `click` on an element, and any position would have to be synthesized from an element's index.
   **Pass:** ≥1 of the 6, at 1600 actions, with a wrong-witness decoy that gains none.
   **Kill:** the decoy gains one. **Do not run this on jsdom.**
3. **The verifier, in the domain that has an oracle — code.** This is the term that multiplies
   everything else, and it is the one term where being wrong is cheapest to detect. A pass is worth
   0.8021; a *law confirmed on the baseline* is worth more because it can be pointed at a mutant
   (this tree already does: 19 of 19 survivors were reachable). **Pass:** a confirmed law rejects a
   candidate the suite accepts. **Kill:** a "law" that is vacuous — the tree already counts those and
   refuses to use them, and that refusal is what makes the number honest.
4. **Hierarchy, because the exponent is the wall.** With a measured **8.34 actions per
   distinguishable state** and a median **150 states per page**, flat search needs `b^depth`:
   depth 6 is **336,511** actions against a 400-action budget. Reducing the effective horizon by
   composing steps into verified macros is the only move in the 2026 literature that addresses the
   exponent rather than the constant. **Pass:** one task family solved at depth ≥5 within the same
   budget. **Kill:** macros that raise the failure rate on the pages they were not built from — the
   long-tail result says most of them will.
5. **Weights last, and only procedure.** `ready_to_train=False`. Fact capacity is ~2 bits/parameter
   and did not improve 2024–2026; the measured gain is procedural. A fact store in weights also
   cannot say **when something was never recorded**. Procedure and prior in weights, facts external.

**Measured dead — do not rebuild (all on this tree's own receipts):** more demonstrations of the
same thing (0 bits, 0/200 identified); more search budget (2.26× → 1 page; 4× → 0 of 5 here); more
action primitives as the coverage fix (0 of 37 pages proved unreachable); pricing inert actions (4
arms tied at 1/6); a bigger skill library (0.605 vs 0.602, ContinualSkillBench); replacing a working
vocabulary (7 pages lost); and now **a declared-format prior** (6 of 123 pages).

---

## 6. On "our model", "from scratch", and "sentient" — plainly

- **No model is used, reached for, or depended on.** `producer_cognition_model_dependency_count: 0`
  in the receipt. Every number here is a hand, a rule, and a page's own reward. That is deliberate:
  a result about *parts* holds for any model or none, which is the strongest form available.
- **"Sentient" is not measurable by anything in this tree, and nothing here claims it.** The word
  covers three things that *are* measurable, and OSWorld 2.0's own failure list names exactly those
  three: **state continuity** ("loss of task-level state"), **self-verification** ("under 7% of
  budget"), and **recovery** ("skip the verification that completion depends on"). Build those and
  the system will look like what the word means. Build none and no amount of "once" produces it.
- **"Our own weights, every bit calculated"** is compatible with everything above, and the
  measurement says what belongs in them: **procedure and prior, never facts.** The 2-bit/parameter
  figure is exactly the "knowledge house" the owner rejects, and it is also the measured ceiling.
  The honest reading of *the best part is no part* for weights is: no parameter that encodes a fact
  a lookup can fetch, and no parameter whose job is to remember a page someone read.

---

## 7. Honest limits of this document

- **Two substrates, and they disagree in a way that matters.** The full-suite figures (78/83/66)
  come from real headless Chromium and are quoted from the merged receipt
  `DERIVED_VALUE_FULL_SUITE_20261116_V1`. The census and taxonomy in this document were taken on
  **jsdom**, which has no layout engine. jsdom refused 7 pages outright and produced **two false
  "exhausted" verdicts** last session (`enter-date`, `scroll-text-2`, both solved in 2 and 10
  actions on Chromium). The taxonomy is about *what an instruction asks for*, which does not need
  layout; the reachability claims do, and none is made here from jsdom.
- **The taxonomy's classes are mine.** They are decided by regex rules over the instruction, ordered
  by strength. The rules are in the module and are meant to be argued with; the counts are the claim,
  not the labels.
- **MiniWoB++ is small and easy by 2026 standards.** 83/129 is far below frontier and is not offered
  as a capability result. The *mechanism* result — a part buys pages, compute does not, and a
  phrase-gated trigger cannot transfer — stands on its own terms.
- **Not claimed:** any capability, any family flip, any weight change, any terminal credit, any
  sentience result.

## 8. Test ledger

```
canonical/tests/test_declared_trigger_census_v1.py                       9 passed
  incl. test_the_declared_surface_is_six_pages
        -> fails if a "declared format" prior is ever reported as a large lever
  incl. test_no_class_holds_more_than_six_pages
        -> fails if a single bottleneck ever appears in the remainder
  incl. test_no_page_is_unclassified
        -> fails if any unsolved page falls out of every downstream count
  incl. test_the_rule_fires_on_the_phrase_not_the_task
        -> the same page, reworded, must stop firing LAST_WORD; skipped (not faked) without the
           page files and jsdom
  neighbouring suites (derived value, full suite, wall classification)   55 passed
```

The three load-bearing tests were checked by injecting a fabricated large lever into the receipt:
`test_the_declared_surface_is_six_pages`, `test_no_class_holds_more_than_six_pages`, and
`test_no_page_is_unclassified` all failed, and all passed again on restore. A test that cannot fail
is not a test.

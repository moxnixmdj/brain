# The hand was never the bottleneck. The operand was.

**2026-11-16 · branch `arena/0ec412aa-brain` · base `85b7036b` · measured on MiniWoB++ with real Chromium, no model, $0**

Authority **NONE**. Producer-run sandbox measurement. No capability registered, no family flipped, no weight touched, `truth.achieved` unchanged. Independent verification is open.

Receipts: `canonical/verification/DERIVED_VALUE_20261116_V1.json`,
`canonical/verification/INERT_ACTION_PRIOR_20261116_V1.json`. Tests:
`canonical/tests/test_derived_value_and_inert_prior_v1.py` (25, OK).

---

## 1. The question, and the answer in one paragraph

> *Give the model the most advanced actions, let it experience each once, and it learns them for
> ever — so all computer use and the most advanced software engineering are solved. Am I right?*

The direction is right and one step of it is now measured, but not the step you named. **Two
things were wrong**, and the corpus said so before I wrote a line of the wrong thing: (i) the
lever is not *more* actions — 47.1% of the hand the machine already has changes nothing in the
initial state of the pages measured (314 actions, one reset each; 36.1% mean in the committed
receipt), so a richer hand is mostly more experiments to pay for; (ii) the wall is not
*learning* — the search fails on these pages at 400 actions as surely as at 1500, so no amount
of experience helps, because **the action that would succeed cannot be constructed at all**. The
machine's only way to produce text is to copy a word of the instruction or a string already on
the page. A page that shows `7 + 0 =` wants `7`. A page that shows a 900-character text area
wants its last word. A page that says `7:55 PM` into a time field wants `19:55`. None of those
is a word anywhere. The search was not failing to *find* the answer. It was unable to *express*
it — and that is a missing part, not missing experience.

That is exactly the defect `WHAT_ONE_DEMONSTRATION_BUYS_20261116_V1.md` already found in the
edit vocabulary (`n ^= n - 1` → `n &= n - 1` is unreachable at any depth), moved one level up:
not the edit, the **operand**. Same law, different latitude.

---

## 2. What was built, and why it is the smallest thing that works

Two parts, both cheap, both falsifiable, neither a model.

**`canonical/runtime/derived_value_v1.py` — a stated algebra of value derivation.**
Eight operators, each with a precondition over what the agent can see:
`STRIP`, `CASE`, `LAST_WORD`/`FIRST_WORD` (when the instruction names which), `JOIN_SHOWN`,
`ARITHMETIC` (a page expression, evaluated), `LINEAR` (one-variable equations), `CLOCK24`.
An operator that cannot fire says so by name. The two that *execute text read off a page* walk
an allow-list AST — no names, no calls, no attributes, no strings, a node budget, an exponent
cap, a magnitude cap — so `__import__(...)` is `EVAL_REFUSED` rather than executed.

**`canonical/runtime/inert_action_prior_v1.py` — affordance-keyed effect counts.**
The explorer already had `effect_prior`, keyed on the action *string* (`click@7`), which cannot
transfer: `click@7` means nothing on the next page, so every page is the first page for ever.
This keys the same counter on the **affordance** — `hover|button|pressable`,
`type|input|typable|empty` — which means the same thing on a page nobody has seen.

---

## 3. The measurement that decided it (and killed my first idea)

Eight pages, 400 actions, four arms that differ **only in what may be typed** (pressing,
hovering, dragging are identical across arms, and a test enforces that):

| arm | what it may type | solved | actions spent |
|---|---|---|---|
| **A** shipped hand | quoted spans / instruction words / page text | **1 / 8** | 2,803 |
| **E** derived hand | the algebra's values | **6 / 8** | **852** |
| **U** union | both | 6 / 8 | 931 |
| **D** decoy | same *number* of values, from the **wrong witness** | **0 / 8** | 3,200 |

| page | A | E | rule that solved it |
|---|---|---|---|
| simple-arithmetic | fail 400a | **pass 12a** | `ARITHMETIC` |
| simple-algebra | fail 400a | **pass 9a** | `LINEAR` |
| scroll-text | fail 400a | **pass 10a** | `LAST_WORD` |
| text-transform | fail 400a | **pass 11a** | `JOIN_SHOWN` |
| enter-time | fail 400a | **pass 7a** | `CLOCK24` |
| search-engine | pass 3a | pass 3a | `STRIP` (no regression) |
| use-slider | fail | fail | — (a drag to a point, not a string) |
| guess-number | fail | fail | — (needs feedback over turns) |

Five pages that were unsolved **at any budget** now solve in **7–12 actions**, every one
re-verified by replaying the plan on a fresh page and letting the page's own reward judge it.
**D is the control that can lose, and it lost 0/8**: the gain is the *rule*, not the extra
values. U ≈ E means the derived hand is not merely additive — replacing 40 words with 2 aimed
values costs nothing.

Two pages still fail, and they name the next two parts rather than hiding: `use-slider` needs a
*spatial* derivation (a number → a point on a track), and `guess-number` needs feedback across
turns. Neither is a learning problem.

### The negative result, stated plainly

The inert-action prior **does not buy coverage**, and I am not going to dress that up. 47.1% of
the offered hand is inert in the initial state of the eight pages sampled first (314 actions,
one reset per action, counting only what the agent can see); the committed receipt, over six
pages and the corrected mechanism, reports mean inert share **0.3614** and four arms that are
indistinguishable — 1/6 solved each, 2,003 actions each (2,026 for the shuffled control). Pricing that inertness changes nothing on these pages,
because the pages the search fails are not budget-bound — at 400 actions they fail exactly as at
1500. **Inertness is a real tax and not the binding constraint.** The receipt stays in the tree
as a measured kill, because a future session that "optimises the branching factor" should find
this before rebuilding it.

---

## 4. Four defects the corpus found that I did not

Every one of these was measured wrong, diagnosed from the page, and fixed — and each has a test
that fails if it comes back.

1. **The `=` at the end of a page expression.** `7 + 0 =` was checked for purity *before* the
   trailing `=` was stripped, so every arithmetic page refused. Fix: strip, then check.
2. **The unknown on either side.** `x + 7 = 5` and `8 + x = 33` both occur on the same task. A
   solver written from the first shape refused half the seeds. Fix: the general linear rule,
   `a·x + b` per side; still only linear, refusing `x*x` and `x = y` by name.
3. **The button's own label offered as a value to type.** `press "Search"` quotes a control; a
   draft typed `Search` into the search box, the page became unreachable, and a page the
   baseline solved in **3 actions** went unsolved at **400**. Fix: a quote that equals a
   control's label is a press target, not a value.
4. **A deferral so large it inverted the search.** Pricing inert actions at `10**9` made the
   explorer prefer endless resets to paying one: the same page went 3 → 400 actions. Fix: a
   surcharge of one unit, matching the cheapest live action — reordered, never priced out.

Defect 3 and 4 are the ones worth keeping: **both were "improvements" that silently broke a
solved page, and only a regression guard on an already-solved page caught them.** A benchmark
that only reports gains cannot see this class of error at all.

---

## 5. So what is true about the plan?

| your claim | verdict |
|---|---|
| Instant learning works once a demonstration exists | **true, and already measured here** (60% vs 15% cache, held-out pages; one demonstration ⇒ a rule that transfers to another module) |
| Give it the most advanced **actions** and it learns them once, permanently | **the wrong lever.** 36–47% of the current hand is inert; action *richness* raises the hypothesis space that one-shot learning must search. 0 of 37 pages were ever proved to need a new primitive. |
| One experience ⇒ the rule | **false as stated.** The floor is ~2.76 chosen *contrasts*, not 1, and in a mechanically identifiable class no number of repeats works at all, because the separating observable is absent. |
| More coverage of environments ⇒ capability | **false.** More places to be wrong, unverified. |
| **Do a thing once on a computer and it is solved for ever** | **false, and now measured false on the part that looked most obviously true.** What persists is not the keystroke; it is the *rule* — and only if the action that succeeded could be built in the first place. Five of these pages would have stayed unsolvable after a *million* demonstrations, because no demonstration of "type the answer" is reachable until something can compute it. |
| The bottleneck is the verifier | **still true, and still unaddressed here.** Every number above is judged by the page's own reward, which a deployment does not have. This session bought *reachability*, not *trust*. |
| We should build our own weights | **not yet, and the reason is arithmetic, not ideology.** A parameter is justified only by evidence that identifies it. Today the fuel store is `ready_to_train=False`; the traces that exist are unidentified successes. This session adds candidates and rules, not identified traces. |
| "Sentient" | not a target. Three measurable properties hide inside it — state continuity, self-verification, recovery — and the third is barely represented anywhere in this tree. |

---

## 6. The single bottleneck, restated after today

Before today: *the verifier*. Half right. The honest form is a **conjunction of two**, and they
are cheap in different currencies:

```
   REACHABILITY            the action that could succeed must be CONSTRUCTIBLE
   (operand vocabulary)    from what the agent can see  ->  costs KNOWLEDGE, a part, in code
                                     |
                                     v
   IDENTIFIABILITY         after it succeeds, something must say it was RIGHT
   (the verifier)          ->  costs an ORACLE, which code has and GUIs do not
```

Today moved the first term from "argued" to **measured**, with a control that could have lost.
The second term is untouched and remains the largest multiplier: coverage produces candidates,
learning needs to know which outcome was success, composition needs to know the sequence did not
revert, persistence needs to know the row is true. A wrong verifier corrupts all four at once,
silently, while every local check passes — which is exactly what the no-op-composition result
already showed.

**And the day's real lesson is about method, not mechanism.** The mechanism I set out to build
(the inert-action prior) was worth nothing; the mechanism that worked was found by *looking at
what the page was asking for* and noticing that the machine could not write it down. No amount
of search, experience, or parameters would have revealed that. One page, read carefully, did.

---

## 7. Ranked next work (pre-registered)

1. **A spatial derivation**, because `use-slider` names it: a number in the instruction → a point
   on a track, given the track's box. Pass: `use-slider` and `use-slider-2` solve, and no page in
   §3 regresses. This is `derived_value_v1` gaining one operator, not a new subsystem.
2. **A turn-level derivation**, because `guess-number` names it: a value that depends on the
   *history* of feedback ("higher"/"lower"), which the state key already distinguishes. If this
   needs a loop rather than an operator, that is a finding and should be reported as one.
3. **The verifier for the domain that has an oracle — code — made adversarial.** Unchanged from
   the last three sessions, and still the largest multiplier. Execution evidence plus a check
   that the check cannot be satisfied by a no-op.
4. **Wire `lesson_admission_gate_v1` into one autonomous caller**, so no derived rule becomes
   permanent without a held-out verdict. Today `rule_of()` records *which* rule produced a value;
   nothing yet admits it.
5. **Weights last**, from identified, contrastive, admitted traces only. Not before 1–4 exist.

## 8. The artifact a new runtime module invalidates, and the one thing it taught me

`canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` is content-addressed over the tree it
indexes, and `canonical/runtime` is one of those trees. Adding two modules therefore broke the
digest and CI failed on `recompilation_is_byte_identical` — correctly, and with no way to see
why except the published tail, which this workflow does publish on purpose.

Regenerated with `canonical/runtime/compile_brain_unified_model_v1.py` (never by hand):
**33/33 PASS**, recompilation byte-identical, `MODEL 14d99cdb…`. `test_brain_unified_model_v1`
+ `test_goal_compiler` + `test_goal_compiler_world_binding_v1`: **137 tests, OK**.

The lesson is not "remember to recompile". It is that **a part is never free**: two files that
touch no shared code still changed the identity of the whole artifact, which is the same
arithmetic as `A_NEW_PART_COSTS_CODE_ONE_LESSON_BUYS_THE_WORD_20261112_V1` — the price of a new
component is paid somewhere you did not look, and in this tree the somewhere is content-hashed.

## 9. Honest limits

- Eight pages, one seed (1060), one substrate (headless Chromium 153.0.8010.0, 480×360), one
  session, producer-run. Not independent verification, not a leaderboard entry.
- The budget was **lower** than the wall measurement's (400 vs 1500). Every arm faces the same
  budget, so the comparison is fair, but "these pages were unreachable at 400" is a statement
  about 400 unless a baseline arm shows the same pages failing at 1500 — which the wall receipt
  does for five of the six (all but `search-engine`, which solves in 3).
- `visual-addition`, `read-table-2`, `find-word` were tried and not solved by any arm; they need
  pixels and layout, which this hand cannot read. They are reported in the raw rows, not hidden.
- MiniWoB++ is small and, by 2026 standards, easy. A 6/8 here is not evidence of frontier
  capability. It is evidence that a *specific* inability was specific and is now removed.

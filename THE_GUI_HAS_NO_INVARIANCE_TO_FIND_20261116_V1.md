# The GUI side has no invariance to find — and that is the answer, not a gap

**Date:** 2026-11-16 · **Branch:** `arena/3bce4e81-brain` · **Base:** `989cac08`
**Authority:** `NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT`. Producer-run, seed 1060, jsdom. No third party ran this. What follows is a measurement of our own instruments, and it is offered as a falsification, not as a capability claim.

---

## 1. The thing that was about to be assumed

The code side has a *measured* invariance that multiplies the reach of a single demonstration. `THE_INVARIANCE_IS_THE_REACH_20261116_V1.md` records it: bind names are α-renameable, so folding one verified repair over renamings took it from **0 survivors to 4**, and from **0 repaired bugs to 5 bugs the demonstration had never seen** — at 0.2 s each, 129× cheaper than hand-written repair families. Rung 2 (a consistently renamed program) scored identically to rung 1, so the invariance cost nothing at home.

The law written there is:

> the demonstration is the content; the invariance is the reach;
> the invariance cannot be learned from the demonstration.

The GUI side has never had one. A `grep` over the whole tree for `invariance` returns **no GUI or miniwob document** — the code side has one, the GUI side has phrase-gated lookups in `derived_value_v1.derivations()` and nothing else. So the natural next move, and the one this session set out to make, was: *find the GUI invariance, and one demonstration will reach many pages.*

**It is not there. This document is the falsification, and it is worth more than the census that produced it, because it says where not to spend.**

---

## 2. What an invariance has to be, to be worth anything

An invariance is a claim of the form *these two things are the same task*. Two distinct things must be called the same. That is the whole content of the idea — in the code case, `def f(x)` and `def f(y)` are different programs and the same bug.

On the GUI side there are exactly two places such a claim could live, and they are different in kind:

| where | claim | who can settle it |
|---|---|---|
| **identity** | the rules do not move when `index` / `name` / `id` change | the rules can be read; this is exact and static |
| **judge** | the page calls two different answers equally correct | only the page; it must be played |

The first is free to test. The second is the only one that could ever buy reach, because reach means *the same answer accepted in more places*.

---

## 3. The first instrument was wrong, and how

Pass one compared the derivable values before and after perturbing an observation, and called any difference a defect. `text-transform` failed arm I4 (elements reordered): `JOIN_SHOWN` returned `F5CZ` instead of `ZC5F`. On its face that is a mechanism keyed on a detail that does not matter — the α bug, in GUI clothing.

It is not. The page renders the answer across four sibling `<span>`s, one character each, and judges `typed === q`. **DOM order is the answer.** Played against the page's own judge:

```
ZC5F   -> reward  1
F5CZ   -> reward -1
```

So a reversed page genuinely wants `F5CZ`, and reading DOM order is *correct*. A "fix" here would have broken a working page — the same failure mode the tree already recorded once, when the replacement arm cost 7 pages.

Two different things produce a difference between before and after, and only one is a defect:

- the rule keys on something that does not matter → **DEFECT** (the α bug)
- the perturbation changed the answer → **TRUTH**

Pass one's third arm could not tell them apart, because it perturbed the **observation** and then asked whether the page still wanted the baseline answer. The page never changed, so the answer never moved, so the arm could never fire. That is a structural defect in the instrument — the kind that produces a confident wrong verdict forever. It is recorded in the module docstring and held down by a test rather than quietly repaired.

---

## 4. Identity invariance is real, and vacuous

Fifteen arms over five pages, rules compared exactly:

```
identity_arms: 15
  INVARIANT                                       13
  UNDECIDED (page not perturbed, nothing to compare) 2
```

And the reason 13 are invariant is the finding, not the number. The rules never read identity as a **computed term**. `index` appears exactly once in the whole value algebra:

```python
derived_value_v1.py:397
fields = [int(e["index"]) for e in observation.get("elements") or [] if e.get("can_type")]
```

That is an **address** — where to type — not a term in a computation. `name` and `id` are not read at all. So I1 and I2 hold *by construction*, and an invariance that holds by construction cannot buy reach: there was never a second task for it to reach into. It quotients out nothing because nothing was ever in the way.

**This is the contrast with the code side, stated precisely.** α-renaming is not vacuous there because a program's bound names are *arbitrary choices an author made*, and a bug-fix template that mentions one will not match the next program. On the GUI side the author's arbitrary choices are `id`/`name`/`class` — and our rules never mention them. The code side needed a lever because it was keying on something arbitrary. The GUI side was never keying on it.

---

## 5. The judge has no quotient — measured

This is the decisive measurement. If anywhere, reach lives here: the page accepting a *different* answer it considers the same. For each page, the answer its judge accepts, run through distinct spellings only (`"11".upper()` is `"11"` — that is not a variant, and counting it was pass two's mistake):

| page | answer | accepted variants | semantic quotient |
|---|---|---|---|
| `simple-arithmetic` | `11` | as-is | **0** |
| `simple-algebra` | `25` | as-is | **0** |
| `enter-time` | `13:13` | as-is | **0** |
| `text-transform` | `ZC5F` | as-is | **0** |
| `scroll-text` | `volutpat` | as-is, `volutpat.`, ` volutpat`, `volutpat `, `  volutpat  ` | 1, see below |

Four of five have **quotient size zero**. The fifth is not a task equivalence either: `scroll-text.html` line 34 does

```js
adjustedAnswer = ans.replace(/[^a-zA-Z0-9]/g, '');
```

The page tokenizes its own answer. The trailing dot is accepted because the *page* strips it — a fact about that page's string handling, not a class of equivalent answers the task recognizes.

And `enter-time` shows how total the equality is. Its field is `<input type="time">`. It rejects the utterance's own string:

```
'13:13'     ->  1
'1:13 PM'   -> -1
'1:13PM'    -> -1
'01:13 PM'  -> -1
'13:13:00'  -> -1
'0113PM'    -> -1
```

**There is no pair of distinct answers the judge calls the same.** The GUI value task is a total equality checked by string comparison. An invariance needs two things to be the same; here the judge refuses. That is not an implementation gap — it is what the environment is.

---

## 6. Which means the phrase gate is not the bug it looked like

Last session measured that every rule is gated on an English phrase, and that rewording the instruction on an unchanged page empties the gate (`scroll-text`: `"last word"` fires, `"final word"` does not). The recorded conclusion was *vocabulary insufficiency*. Half of that survives; the *diagnosis of the gate* does not.

If the judge has no quotient, then the only way to find a page's accepted answer is to **submit candidates and let the page answer**. So the gate cannot be a reach device — it can only be a **ranking** device. Those are different claims and only one is a defect. That is testable, so it was tested.

**A phrase-blind basis**, reading no English at all: each short page string; its first and last token; its case variants; any linear or arithmetic solution its characters contain; the concatenation of single characters in both orders. Then submit, cheapest first, until the page accepts (budget 400 actions, seed 1060).

### On the 5 pages the union gained

| page | gate on neutral text | blind basis | answer found at submit |
|---|---|---|---|
| `scroll-text` | **0** | 5 | **#1** |
| `simple-arithmetic` | 2 | 7 | #4 |
| `simple-algebra` | 3 | 10 | #4 |
| `text-transform` | 4 | 12 | #11 |
| `enter-time` | 0 | 3 | **not found** |

With the English *deleted* (`utterance = "Do the thing."`), the phrase-blind basis still contains the answer on **4 of 5** — including `scroll-text`, where the gate returns `[]`. Cost: 126 actions versus the gate's 23. So the gate buys **order**, and order is recoverable by submitting.

`enter-time` is the honest failure and it is the exception that names the rule. The utterance says `1:13 PM`; the judge wants `13:13`. That string is **nowhere on the page and nowhere in the instruction** — it is constructed by a notational rewrite (12-hour + meridiem → 24-hour) that lives in the *world*, not in the page. No basis built from page content can contain it. That is a genuine vocabulary requirement, and it is the only one of the five.

### On the full surface

All 123 jsdom-loadable pages, both arms, same seed:

```
gated_solved  =  9     blind_solved =  5
gated_actions = 566    blind_actions = 2611
BLIND_ONLY = []        GATED_ONLY = ['enter-text','enter-text-2','enter-text-dynamic','enter-time']
neither = 114
```

**The blind arm adds zero pages and costs 4.6× the actions.** Seven pages could not load at all (`ascending-numbers`, `hover-shape` — jsdom reply timeout; `bisect-angle`, `click-pie`, `click-pie-nodelay`, `drag-cube`, `moving-items` — jsdom has no `getBBox` / `createSVGMatrix`). Those are instrument limits, excluded, and never counted as findings.

---

## 7. What this settles — and the question it answers

The user's question was whether instant learning in new environments, plus the most advanced actions demonstrated once, solves all computer use. This session's contribution is to kill the most attractive shortcut to that answer.

**The code-side lever does not transfer, and the reason is structural.**

| | code | GUI |
|---|---|---|
| what is arbitrary | bound names (author's choice) | `id`/`name` (author's choice) |
| do our rules key on it? | **yes** — A names the target's variable | **no** — never read as a term |
| so is there a quotient? | **yes** — α-equivalence | **no** — judge is total equality |
| what invariance buys | reach: 0→4 survivors, 0→5 bugs | **nothing**: 13/15 arms vacuous, 4/5 judges have quotient 0 |
| what actually limits reach | the template's context | **the operand vocabulary** |

So there were two candidate diagnoses on the GUI side and this session falsifies the first:

- ~~*the GUI side is missing an invariance*~~ — **falsified.** There is nothing to quotient. The identity arms are vacuous by construction, and the judge refuses every distinct answer. Building an invariance machinery for GUI value tasks would be building a part with no job — exactly what "the best part is no part" forbids.
- *the GUI side is missing operand vocabulary* — **survives, and is now the only one standing.** `enter-time` is the existence proof: one notational rewrite in the world (12h→24h), unavailable from page content, and no basis built from the page can contain it.

This explains, rather than re-derives, the numbers already on `main`: why the +5 union gain does not transfer (0 of 121) — the gate is a ranking device tuned to the design pages' phrasing, and ranking does not travel; why the 16-class operand taxonomy is where the remaining 46 pages actually live; and why "give the model the most advanced actions" does not by itself transfer — an action's *reach* is set by the invariances its context admits, and on the GUI side the environment grants none.

**The one thing this does not say** is that the GUI is hopeless. It says the *lever* is not here. The blind basis found four answers with no English at all, which means the environment is more self-describing than the gate assumed. The honest next question is not "what invariance does GUI have" but **"which operands must a vocabulary supply that no page can show"** — and `enter-time` is the first measured member of that set: a rewrite in the world, not on the page.

---

## 8. Non-claims

- jsdom, not Chromium. 123 of 130 pages load; 7 are excluded for missing SVG/layout, listed above, and none of the exclusions flatter an arm.
- Seed 1060 only. The arms are deterministic, but one seed is one draw.
- The blind arm is a **strawman-strong** baseline, not a proposal: 2,611 actions for 5 pages is not a system. It exists to price the gate, not to replace it.
- Producer-run, authority `NONE`. No third party ran this, and a pass on our instrument is not evidence about the world until someone else runs it.
- §6's `enter-time` result is a *negative* control that passed: it fails for a stated reason, and that reason is the finding.

---

## 9. Reproduce

```bash
python3 canonical/tools/gui_invariance_census_v1.py canonical/verification/inv.json
/tmp/v4/bin/python -m pytest canonical/tests/test_gui_invariance_census_v1.py -q   # 13 passed

# one page per process: a bridge that lives across pages dies at the 20 s reply timeout
bash /tmp/arm_all.sh /tmp/arm_rows
```

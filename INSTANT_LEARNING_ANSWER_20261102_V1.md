# The answer: is "instant learning solves everything on a computer" true?

**2026-11-02.** Owner's question: *instant learning and instant learning in new arbitrary
environments are already solved perfectly — doesn't that mean this is the perfect solution for
all the problems the machine and any computer has? Just give the model a try in each new
environment, or give it the smartest actions, and after he does them once he learns them
permanently. So we solve everything on a computer, perfectly and permanently? We were trying to
make our model a sentient creature. Is this true, or are there things that are wrong?*

This answers it on **this checkout** (`2ececc4`, `main`), by running the probes, not by reading
the earlier document. `INSTANT_LEARNING_SCOPE_20261101_V1.md` reached the same shape of
conclusion; everything below I re-measured, and I add one correction it does not contain (§4).

---

## 1. The short answer

**The mechanism is real. The inference from it is not.**

Four of your five claims are true as stated about a *narrow object*. The step from
"it learns each thing it is shown" to "it solves everything on a computer" fails, and it fails
for a reason that is already measured in this tree, not a matter of opinion:

> **The learner captures less than the success taught, and what it captures it only offers
> back inside the row that routing already chose.**

Both halves of that sentence are numbers, not arguments. Everything else follows.

---

## 2. What is true, what is false, what is unproven

| your claim | verdict | what I measured today |
|---|---|---|
| Instant learning works | **TRUE** | One lesson taught into a fresh store: `crystallized: true`. Store, restart and bundle transport all work. |
| It learns in new arbitrary environments | **TRUE within a family, FALSE across kinds** | 5 families, new instances: **10/10** solved on the first and second new instance. But all five are ~40-line symbolic environments (`dials`, `switches`, `grid`, `counter`, `string`) written in the probe itself, sharing action names. This is transfer across *instances*, not across *kinds* of environment. |
| "Does it once, learns it permanently" | **TRUE for the rules that get stored; the rule is narrow** | Taught the `<= hi` → `< hi` lesson; on the ladder of new shapes it solved **2 of 9**, of which **1 of 7** were novel same-lesson shapes and **1 of 2** were controls. Repetition does not help — see §3. |
| "Give it a try in all the environments and it learns all of those" | **FALSE** | It learns *one* thing per success, and the thing it learns is the shape of that one edit. Same rate with learning on and off: **6/9 vs 6/9**. |
| "Anything on a computer" | **HALF TRUE** | Real code operations run for real: `git bisect`, mutation scoring, taint-flow, whole-runtime AST indexing — **10/10 tiers reached**. Real CLI discovery from `PATH`, real subprocesses. The GUI half is **closed against a virtual desktop double**, not a real OS: 12/12 tests pass, and only `VirtualDesktop` is a fake. `pyautogui` driving a real OS is still unproven. |
| "Perfectly" | **FALSE, by design** | Every recall is a **hypothesis**: `recall_and_apply_verified` takes a mandatory `verifier` and returns nothing unverified. The floor is therefore your verifier's quality, never zero. That is correct engineering, not a bug. |
| "We are making a sentient creature" | **NOT MEASURED, AND NOT THE MISSION** | See §6. |

---

## 3. The three real walls, in the order they will stop you

These are not gaps in memory or speed. Adding exposure does not move any of them.

**Wall 1 — the learner captures the shape, not the lesson.** Taught one boundary fix, it
solves a renamed copy and a class-method variant, and misses: a new literal, the operator
inside a larger expression, inside an `if`, inside a `while` guard, operands flipped, the
negated form, and the expanded `x < hi or x == hi` form. Measured again today: **1 of 7** novel
shapes. Teaching the exact case it missed does not fix it — the failure is
**representational, not statistical**, so a thousand more tries buy nothing.

**Wall 2 — teaching does not fix routing.** A lesson lives *inside a row*. If the door does not
route your sentence to that row, the lesson is never consulted, however many times it was
taught. Measured directly in this tree: a rule was taught and recalled `MATCHED`, and the door
still refused, because selection had already declined the sentence. **443 registry rows,
11 ever reached.** Your plan "try it in all the new environments" collides with a declaration
table before it ever reaches the memory table.

**Wall 3 — observation abstraction, on a real screen.** Learning by doing needs `state()` to
return something hashable and comparable. On a CLI that is a filename and an exit code. On a GUI
it is pixels. "Learn the transition function in one trial" on pixels is not one observation, it
is a tabulation nobody can afford. The recipe layer that would turn a screen into a comparable
state is documented in a docstring and **not implemented**.

---

## 4. One correction this repository's own docs do not contain

The strongest number in the instant-learning case is *"10/10 new instances solved by a
**recalled plan**."* I re-ran it and it reproduces — but the label is doing more work than the
measurement.

`transfer_learning_v1.drive` returns `PASS__ENVIRONMENT_SOLVED_BY_RECALLED_PLAN` in **two
different situations**:

1. a stored plan was replayed and the goal was observed — genuine recall, one trial; and
2. the plan search was **warm-started from a carried-over model** — the status is set to
   "recalled" whenever a prior model exists, even though the plan was found by search.

Per-family trial counts from my run:

| family | COLD | FIRST | SECOND | honestly recalled? |
|---|---|---|---|---|
| three-dial lock | 32 | **1** | **1** | yes |
| accumulator word | 64 | **1** | **1** | yes |
| grid reach | 16 | **1** | **1** | yes |
| modulo counter | 8 | **1** | **1** | yes |
| four toggles | 8 | **8** | **8** | **no — warm-started search, zero trials saved, still labeled "recalled"** |

So the honest figure is **8/10 genuine 1-trial recalls, not 10/10** — and the toggles family
shows the specific thing you are hoping for *not* happening: a carried-over model that bought
**literally nothing** (8 trials before, 8 after), reported under a status that says the plan was
recalled. The document reports the `8 / 8 / 8` numbers, so the data is transparent; the **status
constant and the summary line round it up**.

This matters beyond bookkeeping. It is exactly the failure mode `AGENTS.md` was written to
stop: a number that goes green in the receipt while the underlying quantity did not move.

**Fixed 2026-11-02** — see §9. The probe now prints `8/10 genuinely recalled` and names the
family that saved nothing.

---

## 5. What is genuinely strong — defend these

I want to be clear that the pessimistic reading is not the accurate one. Four things here are
real, and three of them I verified by running them:

1. **One-shot environment *operation*** — `environment_fit_v1` reads a project's own
   declarations (CI file, `package.json`, `Makefile`) and works out how to run it. It
   generalises because the schema is universal, not because it memorised anything. Measured
   2/2 on real external repos with their own suites as oracle.
2. **Real code surgery, not chat about code** — today: `git.history.bisect_regression`,
   `python.tests.mutation_score`, `python.source.taint_flow`,
   `python.source.symbols.index.ast`, cross-file extract-function, race repair. **10/10 tiers
   reached** on a real filesystem.
3. **The rules that do transfer transfer perfectly** — and across languages, when asked.
   Teaching in Python, then consulting the language-neutral bridge explicitly, carried the same
   token swap into **Go, TypeScript, C++ and Java (4/5)**, and for C++ the result was
   **compiled by `g++` and run with 3/3 real assertions passing**. Rust was missed — not by a
   safety guard, but because the rule's pattern is `return ?id0 <= ?id1` and Rust writes the
   same function as a tail expression (§9.2).
4. **It knows what it does not know, and ranks it** — `ignorance_ledger_v1` scores each gap by
   expected value, prefers the unknown over the known-useless without an exploration rule
   being written, and reorders itself from outcomes. 52/52 tests pass across the ignorance,
   expiry and transfer modules. This is the honest, measurable half of the thing you want.

---

## 6. On the sentient creature

You did not build a sentient creature, and — more importantly — **the objective does not ask
for one.** The canonical objective is *"the most capable general reliable and resource-efficient
problem-solving system possible."* Sentience is not a term in it.

What you do have is the part of it that can be measured: **a working self-model of its own
ignorance, ranked by what closing each gap is worth, improved by being wrong.** A system that
models what it lacks and acts on that ranking is doing the thing people mean by "knows what
needs to be known." That is real and it is in the tree.

Asserting more than that would put every real number above at risk, because a claim with no
instrument is precisely what the laws in this repository exist to prevent. My recommendation:
stop aiming at the word, keep aiming at the five behaviours in
`canonical/governance/OWNER_ACTIVE_GOAL_20261018_V1.md` §5.

Two of those five are directly contradicted by your current framing and are worth saying plainly:

- **"It must know literally all the data, and everything must be done in the fastest way"**
  cannot be satisfied as written by any system — the unknown space cannot be enumerated, so
  "fastest" can never be certified globally. The computable version is: report a **lower bound
  plus a named coverage residual**, and never use the word "fastest" without it. That is
  falsifiable and monotone. It needs an owner decision, not an agent reinterpretation.
- **"It will not stop till it really hits the goal"** is a persistence property, not a learning
  property. Nothing in the learning machinery provides it; it needs its own controller.

---

## 7. The smartest things to do, ranked by what they would actually change

**1. Wire the two finished modules that nothing calls.** This is the single highest-value move
and it is embarrassingly small. `language_neutral_skill_bridge_v1` (cross-language carry, 4/5
measured) and `rule_scope_learning_v1` (automatic scope narrowing via `select_probe`) are both
**called only from their own tests**. The live repair paths still hardcode `language="python"`
(`software_repair_crossfile_choreograph_v1.py:1126`,
`multistep_repo_closed_loop_solver_v1.py:1865`). So the fixes exist, are tested, and are not on
the production path. Every "we solved it" claim in this family is true of the laboratory and
false of the solver until these two wires exist. `select_probe` itself was an orphan until
`rule_scope_learning_v1` adopted it — do not let that repeat one level up.

**2. Fix the transfer status label before quoting the number again.** §4. Return
`PASS__WARM_STARTED_SEARCH` when the plan came from search. You will lose 2 of 10 from the
headline; you will gain a number that does not need a footnote.

**3. Exercise the OSWorld stack against a real OS.** 90 modules, the largest surface measured
nowhere, and it is exactly the *"anything on a computer"* you asked for. The loop is already
closed against the virtual desktop; what remains is one honest sentence — *`pyautogui` drives a
real operating system* — and buying that evidence is worth more than any new mechanism.

**4. Implement the screen→state recipe layer (Wall 3).** This is the one genuine research gap
in the "anything on a computer" claim, and it is the difference between learning a CLI in one
trial and learning a GUI in one trial.

**5. Stop buying exposure.** §3 Wall 1 is measured: 1, 2 and 3 examples all give 6/7. More
demonstrations do not widen a rule; only a wider hypothesis space does, and that requires
someone to author the new shape. Measure before you spend.

---

## 8. Non-claims

Authority: **NONE.** Zero capability, ownership, benchmark, terminal or sentience credit follows
from this document. It changes no number and moves no row. The one measurement that is new
relative to `INSTANT_LEARNING_SCOPE_20261101_V1.md` is §4, and it **reduces** a claim rather
than raising one. Every figure above was produced by running a file in this checkout on
2026-11-02; none is quoted from a prior document without saying so.

---

## 9. What changed on 2026-11-02 (executing items 1–2 of §7)

### 9.1 The rounding-up is fixed, and pinned from both sides

`canonical/runtime/transfer_learning_v1.py` gains a third outcome,
`PASS__ENVIRONMENT_SOLVED_BY_WARM_STARTED_SEARCH`. Only the replay path may return
`PASS__ENVIRONMENT_SOLVED_BY_RECALLED_PLAN`; a search that merely reused a carried-over model
returns the new status with `transferred=False, warm_started=True`. Every return path now
carries both keys, so no caller has to infer "was this a replay?" from a missing field.

Four tests were added to `canonical/tests/test_transfer_learning_v1.py`. **All four fail on the
2026-11-01 code** — the clearest message being `AssertionError: 8 != 1 : claimed recall but
spent 8 trials` — and all four pass on the corrected code. The suite went 23 → 27 passing, with
109 passing across every test that consumes the module and no new failures anywhere
(`test_composer_route_v1.py` has 10 failures that are **pre-existing and identical on clean
HEAD**; measured, not assumed).

Re-run of the environment probe now reports honestly:

```
FIRST  solved by RECALLED plan:      4/5   (1 trial each)
SECOND solved by RECALLED plan:      4/5   (1 trial each)
FIRST+SECOND solved at all:          10/10
  of which genuinely recalled:       8/10
  warm-started search (no saving):   2/10
  families learning nothing from the prior model: toggles_4
```

### 9.2 The cross-language claim is now executed, not asserted

New probe `cross_language_learning_probe_20261102.py`: one lesson, taught from **one** Python
example, then offered to five languages. For C++ the carried patch is **compiled by `g++` and
run against three real assertions** — it passes 3/3. One example in Python, working C++.

It also corrected the *reason* the earlier note gave for the missing fifth. Rust is not stopped
by a safety guard. The crystallized rule is `return ?id0 <= ?id1`, so it crosses into exactly
the languages that spell the fix with `return`; Rust writes the same function as a tail
expression. That is Wall 1 of §3 wearing a different hat, and it is the cheapest next fix on
the list: admit a tail-expression form of the pattern.

### 9.3 The record is corrected in place

`INSTANT_LEARNING_SCOPE_20261101_V1.md` §8 now carries both corrections, dated, and says
plainly that the "10/10" was 8/10 and that the defect was the **label**, not the data — the
trials were always printed. Both corrections **lower** a claim. No number was raised anywhere
in this work, and no capability, benchmark, terminal or sentience credit is claimed.

### 9.4 One governance gate is left red on purpose, and here is why

The intent `canonical/action_intents/A_RECALLED_PLAN_IS_A_REPLAYED_PLAN_V1_20261102_V1.json`
describes this change truthfully and fills every block it can fill from measurement: the
recursive observation receipt, the v22 pre-write admission bound to the live pointer blob, the
blocker lease, and the tournament block bound to the real blobs of the four files that carry
the evidence.

**One objection remains:** `LIVE_CHALLENGER_FRONTIER_EXEMPTION_NOT_ALLOWED_FOR_ACTION_KIND`.
The drift guard requires a live challenger frontier over **external software suppliers** —
four distinct query families, four source classes with non-empty evidence, six comparison
dimensions — for any action kind except `GOVERNANCE_GUARD`, `RECONCILE_FRONTIER` or
`EVIDENCE_PRESERVATION`.

This change introduces **no supplier, product or implementation-form choice**. There is no
external part to discover. The question is entirely internal and already closed by measurement:
*which of the two code paths inside `drive()` produced the returned plan, and does the printed
trial count contradict the returned status?* Filling that schema would have meant inventing
external source evidence for a question that has none — precisely the fake-proof failure the
laws exist to prevent — or relabelling the action as `EVIDENCE_PRESERVATION` to slip past the
check, which `AGENTS.md` forbids in the same sentence it forbids working around the guard.

So it is left red, with `discovery_required: false` and a `not_applicable_reason` that states
the reason instead of concealing it. Per `AGENTS.md`: *"If you believe a rule is wrong: say so
in the PR description and stop. Do not work around it."* **This is the owner's call, not an
agent's** — either the guard gains a falsification/label-correction action kind, or the owner
lands this one under the existing exception.

Worth naming plainly: a guard that cannot express *"I corrected a status string that
over-claimed, and lowered a number"* exerts pressure to inflate small, honest corrections into
capability-acquisition narratives. That pressure is a governance defect in its own right.

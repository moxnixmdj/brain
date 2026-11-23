# Hold a constraint: the postcondition is clauses, not a string

**Date:** 2026-11-23 · **Branch:** `arena/eac85348-brain` · **Base:** `68bf0400`
**Authority:** NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT · **Model calls:** 0 · **Weights:** unchanged
**Organ:** `canonical/runtime/hold_a_constraint_v1.py`
**Tests:** `canonical/tests/test_hold_a_constraint_v1.py` (13 passed)
**Receipt:** `intake/RECEIPT_HOLD_A_CONSTRAINT_20261123_V1.json`

---

## 0. The requirements this answers, and the §2 boundary

Own weights, **zero model calls at runtime**, **zero knowledge house**, every parameter
calculated, knowledge external and removable without retraining, instant learning from a single
experience, Elon's law, insanely fast, and nothing claimed that was not run.

**§2 resolved, unchanged by this round's evidence:** forbidden is *parameters acting as a lookup
of memorised world facts*, and any runtime dependency on another model. Allowed is an external,
inspectable store the system computes with. Nothing built here adds a weight, and the only thing
saved is a clause matrix and a *refusal* — both JSON, both editable, neither retrained. The test
the constraint sets holds: knowledge lives outside the weights, and the weights hold only
computed mechanisms.

---

## 1. The four ideas in the message, taken literally, and what each one costs

The message proposed **(a)** a perfect algorithm that enters any unknown environment and pulls
what it needs from instant knowledge, **(b)** goal-directed vs learn-everything, **(c)** scan →
retrieve → fetch the unknowns, **(d)** memory that saves generalised learning rather than raw
experience.

(b) and (d) were answered with measurement in earlier rounds of this project and the answers
stand: goal-directed is **5.9×** cheaper than learning a family (2.30 s against 13.49 s), and a
per-app name cache measured **exactly zero** gain (cold 2.15 s, warm 2.17 s) because every app
re-declares its own names in 1.24 s. So the durable thing is the *shape*, not the names.

(c) is real but the unknowns are **declared, not inferred**: an interface publishes what it
needs, and the composed accessibility tree is 253 bytes where a screenshot is 9,601.

**(a) is where this round lives**, and the previous round left it honestly open. Its own closing
sentence named the bottleneck:

> *every number assumed someone supplied the goal as strings the checker understood, and the real
> task arrives in natural language.*

That was half of it. The other half is harder and is the subject of this document.

---

## 2. The bottleneck, found before building

OSWorld 2.1 is the hardest open computer-use benchmark: 108 long-horizon workflows, beyond 250
agent steps. It names the failure modes itself — **constraint tracking, multi-item state
tracking, conflict disambiguation, mid-task change detection, verification** — and not one of
them is about the first action.

The two-action organ from the previous round was measured against exactly that, on a real app,
before any code was written:

> **Task:** *mark beta complete but leave alpha and gamma uncompleted*
>
> every candidate scored `2.0`; the top-ranked action was **"Toggle All Input"**, which would
> complete all three items and violate the constraint while satisfying the named one.

That is the whole failure in one line: **a goal that is a list of strings cannot express "and not
the others."** The organ did not mis-execute; it could not represent the task.

This is the same absence the coding search has been stuck on for five rounds. In
`FIVE_THOUSAND_DOCUMENTS_CHANGE_NOTHING…` the project wrote:

> *"There is no per-gate objective. The search cannot say 'this candidate is one gate closer', so
> it cannot prefer a candidate… The single bottleneck: the search has no measure of distance to
> the part it is trying to reach."*

Two organs, one disease. The GUI case is the tractable one, because the environment **verifies**
in 123 ms — so the objective can be exact rather than approximated.

---

## 3. The idea: a postcondition is a clause matrix

Not a string. A set of clauses, each with a polarity and a scope:

| clause | kind |
|---|---|
| `beta` shows as complete | **POSITIVE** — must become true |
| `alpha` does not | **NEGATIVE** — must stay false |
| `gamma` keeps the state it has now | **INVARIANT** — must not move |

An action is then scored by **how many clauses it changes**, a change to a clause you must
preserve **disqualifies** it, and a clause that *already holds* scores negative because acting on
it can only break it. That is the per-gate objective, and here it is not an approximation: the
interface re-declares its own state after every action, so the value of every clause is read back
exactly.

**Why it generalises instead of memorising.** Nothing in the module knows what a todo is.

- A **row** is a container that declares a text and holds a control.
- A **control with no name** is addressed by the text of the row it sits in — which is where a
  person's eye goes too, and the relation is in the DOM rather than in my memory.
- Every word comes from the app: the item names from the task, the roles from the accessibility
  tree, the relation from the composed tree.

---

## 4. Measured

Eleven self-contained implementations of a published interface specification, in eleven
frameworks, **none written by me**.

| task | result | actions | time |
|---|---|---|---|
| **T1** mark beta complete, leave alpha and gamma uncompleted | **11/11 SATISFIED** | 11 total | 120.6 s |
| **T2** mark alpha and beta complete, leave gamma and delta uncompleted | **11/11 SATISFIED** | 22 total | 164.8 s |
| **T3** complete two, then the user completes a third; detect the drift | **11/11 RECOVERED_AFTER_CHANGE** | 33 total | 166.7 s |

T1–T3 each take **one action per positive clause** and never touch a protected row. T3 is the
mid-task change detector: after the user's edit the loop re-reads the clauses, finds the negative
violated, and reports the drift with the item's name instead of declaring success.

Visual proof, Svelte, the exact action the planner chose:
**beta checked, alpha and gamma untouched, "2 items left".**

### The control that gives the number meaning

A result with no control is a story. The control is deliberately the *strongest cheap action a
constraint-blind loop would take* — the global toggle, which is one click and is exactly what the
two-action organ ranked first:

| | result |
|---|---|
| constraint organ | **11/11** satisfy the task |
| constraint-blind global toggle | **0/11** |

On 6 apps the blind toggle completed the two protected rows; on 5 it completed nothing at all.
Either way the task is not done. **The clause matrix is the difference between 0/11 and 11/11**,
and that is the only reason to keep the organ.

---

## 5. Six bugs, all found by running

Each was invisible in the offline reading and each is pinned by a test.

1. **Polarity by adjacency.** `"leave alpha and gamma uncompleted"` puts the word `uncompleted`
   after gamma only, so alpha was classified as a weak **invariant**. The loop checked alpha
   **twelve times in a row** and never reached the positive clause. *A leave/keep scope runs to the
   end of its list, and a negative is strictly stronger than an invariant.*
2. **The scope ran past a conjunction.** `"leave alpha alone but mark beta complete"` made beta
   negative too — inverting the task's own instruction. *The scope ends at but/however/then/instead.*
3. **A satisfied clause scored like an open one.** Every named row scored 6.0, so acting on the
   protected row looked as good as acting on the open one. *A clause that already holds scores
   negative.*
4. **Row membership paired two traversals by index.** `row_text` was `None` on every control, so
   the two shadow-DOM apps had no row-addressed action at all. *Stamp the row on the element
   before the element list is read, and carry the row text, not a sequence number.*
5. **Clause items matched by equality against the whole row text.** One implementation reports the
   row as `"Toggle Todo beta"` where the item is `beta`; nothing matched, every row scored 0.0, and
   the planner fell through to a global checkbox. *Match the item as a word inside what the row
   publishes — on the reader and the scorer alike.*
6. **The row container was assumed to be a listitem.** A 10-second timeout on one implementation.
   *Try listitem, then row, then plain tags, then refuse by name.*

The pattern is the one this project keeps rediscovering: **a string assumed to mean one thing is
how an instrument lies** — the same class as the `sort -V` certificate, the placeholder mistaken
for an accessible name, and the goal word `buy` matching inside `Enter a new todo.`

---

## 6. Honest limits

- **Eleven apps of one specification.** Depth within a family, not generalisation across families.
  A desktop application or a browser-based IDE declares a different surface and none was tested.
- **Three to six actions, not 250.** Task chains create → mutate → verify, but nothing here
  approaches OSWorld's horizon, and **no OSWorld task was run**.
- **The clause reader is a closed word class** (`complete/incomplete/leave/keep/but`). A task
  phrased outside it yields no clause or the wrong polarity. It parses a small grammar; it does
  not understand the instruction.
- **The postcondition is the app's own declaration**, so an app that declares the wrong state
  would be believed. The effect is only as trustworthy as the declaration.
- **One control procedure.** A blind loop that happened to click the right row would have passed,
  and nothing here rules that out.
- **The SWE-bench generation gap is untouched** — 1.4% search ceiling against 78.80% top agent.
  This round made the *GUI* objective exact; it did not make the coding search have a gradient.

---

## 7. What this does and does not say about §3

**Real:** that a postcondition can be read as clauses and verified by the environment itself; that
a constraint held across steps beats a constraint-blind loop 11/11 to 0/11 on real apps; that a
control with no name is addressable by the row that declares one.

**Not real:** that this is instant learning. Nothing here was learned from a single experience and
reused — the clause matrix is derived fresh from the task at run time, and the only durable
artefact is a refusal. Calling that "learning" would be the flattery the honesty rules forbid.

**Still missing, and named:** the coding search needs the *same* thing the GUI now has — an
objective it can evaluate per candidate. The GUI case got it cheaply because the environment
verifies in 123 ms. The coding case has a verifier too, but only at the granularity of a whole
test, and that is a first-class test failure, richer than a bit and cheaper than a model. That is
the next blocker and it is where the loop goes next.

---

## Reproduce

```sh
sh canonical/runtime/browser_launch_v1.sh                 # real Chromium, DevTools on :9222
python3 -m http.server 8800 --bind 0.0.0.0 &            # in examples/ of a TodoMVC checkout
python -m pytest canonical/tests/test_hold_a_constraint_v1.py -q
```

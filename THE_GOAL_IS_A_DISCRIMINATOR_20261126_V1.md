# THE GOAL IS A DISCRIMINATOR

**The user never states the goal. The user gives judgments. What the agent must recover is the
smallest relation that separates them — and what it must do when two are still possible is either act
on both or ask again, never guess.**

Date: 2026-11-26 · Authority: `NONE__PRODUCER_RUN_SANDBOX` · Branch `arena/0a4f2cd7-brain`
Receipt: `canonical/verification/THE_GOAL_IS_A_DISCRIMINATOR_20261126_V1.json`
Tool: `canonical/tools/the_goal_is_a_discriminator_v1.py` · 5 tests · 0 parameters · 0 model calls

---

## 1. Where the previous two rounds left the question

Round one showed that an action experienced once is knowledge only if the vocabulary can *name* what
it did: a fixed list of effects calls `mv` and `sort` inert, and an effect the agent cannot see is a
goal it cannot state. Round two replaced the list with relations over the machine's own reader and
admitted only the relations a goal needs.

**Both rounds handed the goal in.** That is the last place where a human was still doing the agent's
work: someone had to say *which* relation the request is about. This round removes that.

## 2. What is built

The user gives **judgments** — "this state is what I wanted", "this one is not". The agent must
recover the **discriminator**: the smallest conjunction of terms over the machine's own reader that is
true of every accepted state and false of every rejected one. Terms are not written per goal; they are
instantiated from the literals the machine itself produced (`card==n`, `count[c]==k`, `multiset==M`,
`first==c`, `order_is_sorted`, `contents_distinct`, `ident_order==I`, `has[i]=c`).

Three consequences are measured, not asserted:

1. **Identification is a count.** After one judgment the answer is a *set* of minimal discriminators,
   and the tool reports the exact size. That number is what "a single trace is consistent with many
   hypotheses" means on real machines.
2. **The agent chooses which judgment to ask for.** The next state asked about is the one whose answer
   splits the surviving discriminators most evenly — the version-space question with the highest
   information — compared against asking in the pool's own order.
3. **Acting under ambiguity is refraining.** While more than one discriminator survives, the agent may
   only aim at states **every** survivor accepts. If no action reaches one, it asks instead of
   guessing. A guess that lands on a state the user rejects is a **false accept** — the accusation
   class, and the one error that must be zero.

Real machines throughout: FILESYSTEM, TARBALL, SQLITE, GIT, each with its own reader and opaque atoms
(`FS_A3`, `SRT_A1`, …). Judgments are produced by running real tools and reading the machine.

## 3. The result

| | |
|---|---|
| goals | 5, across 4 real machines |
| survivors after **one** judgment | 12, 11, 16, 11, 12 → **median 12** |
| judgments to a unique answer (active, chosen) | 4, 2, 5, 2, 5 |
| judgments in the pool's own order | 4, 2, 6, 2, 6 |
| strictly fewer questions by choosing | **2 of 5** (SQLITE 5 vs 6, GIT 5 vs 6); never worse on any |
| goals acted on, from the inferred discriminator alone | **5 of 5**, every one a state the user accepts, verified by the reader |
| **false accepts** | **0** |
| false accepts on held-out states (never judged) | **0** of 6 |

**Declared before the run:** A1 held-out soundness; A2 syntactic uniqueness (≥3 goals); A3 asking well
never worse and strictly better somewhere; A4 ≥3 goals acted on with zero false accepts; A5 median
ambiguity after one judgment > 1; A6 zero model calls and zero parameters.

**Met: A1, A3, A4, A5, A6. Not met: A2** — 2 of 5 goals reached a *syntactically* unique
discriminator, not 3. That failure is the most interesting number in the round.

## 4. Why A2 failed, and the law that replaces it

The survivors that remain are not noise. On TARBALL, five one-term discriminators survive — `card==3`,
`count[probe_new_content]==1`, `has[probe_member]=probe_new_content`, … On SQLITE, two survive —
`first==probe_new_content` and `has[1]=probe_new_content`. Asking more questions does not help,
because **every one of them gives the same answer on every state the machine can reach**.

The tool checks that this is not an artifact of a shallow search. It rebuilds the reachable set three
actions deep — GIT grows from 6 states to **31**, SQLITE to 10, TARBALL to 4 — and the number of
behavioural classes of the surviving discriminators stays at **1 on every machine**.

> **The law.** Identification is bounded by the **reachable contrast set**, not by the number of
> questions. A question can only separate hypotheses that differ on a *reachable* state; where they do
> not differ, no question exists. And none needs to: two discriminators that agree on every reachable
> state are the same goal in the only sense that can license an action.

That is a two-sided result and both sides matter. **As a limit:** you cannot always know which goal the
user meant — the machine itself may be unable to show you the difference. **As a licence:** you do not
need to, because everything you could do satisfies both. The agent's rule is therefore not "identify,
then act" but **"act on the intersection; ask only where the intersection is empty."**

This is also why A4 can be perfect while A2 fails: five of five actions satisfied every survivor, and
a false accept requires a state that *some* survivor rejects — which, by the measurement above, is a
state this machine cannot reach.

## 5. The composite goal, and an honest collapse

One goal was declared as a conjunction on purpose — *"the new content appears exactly once **and** the
seed content survives"* — to see whether the mechanism can find a two-term goal rather than a lookup.

On TARBALL it **collapsed to a one-term discriminator**, because the machine cannot dissociate the two
conjuncts: under every reachable sequence the two properties move together. The result is not "the
search failed". It is the same law, seen from the other side: *the machine could not show the
difference, so the agent could not be wrong about it.* Reported, not hidden.

## 6. What the frontier is doing in November 2026

The same problem has a name in the 2026 literature, and everyone attacks it with a model:

* **TeleTune** (arXiv 2610.05437) names **Goal Underspecification** as challenge (1) for learning
  skills from UI telemetry and solves it with a **"Goal-Inference Prompt"** to an LLM.
* **Semantic under-specification in host-acting agents** (J. Networking and Network Applications,
  May 2026) shows goal-only instructions force the agent to complete missing execution semantics, and
  that the completion — not the action — is where the risk lives.
* On the coding side the same structure is measured: SWE-bench Pro's own verifier runs at **8.5% false
  accept / 24.0% false reject** (Datacurve, May 2026), and *Accepted but Wrong* (arXiv 2611.08269)
  shows the fix is not more tests but **which** input is asked.

Here, nothing is prompted. The discriminator is a finite search over terms the machine produced, the
question is chosen by information, and the answer is verified by the reader. **0 parameters.**

## 7. What is real, what is false

**Real.**
* A user's taste can be *recovered* as a relation when it is consistent — 5 of 5 goals, from judgments
  alone, with the machine's reader as the only judge.
* The agent can choose its own next question, and choosing beats the pool's order on 2 of 5 goals and
  is never worse on the rest.
* Ambiguity is a number: **median 12** minimal discriminators after a single judgment, on real tools.
* Acting on the intersection of all survivors is *safe*: 0 false accepts, 0 held-out false accepts.

**False.**
1. **"Give it the action once and it has the capability."** The action was never the unit. The unit is
   the relation the goal is about; `mv` and `sort` are invisible to a multiset vocabulary, so an agent
   can watch them forever and still not take the request.
2. **"One demonstration identifies."** One judgment leaves a median of 12 candidate goals. What kills
   them is not more watching — it is a *question chosen* to separate them.
3. **"More experience fixes ambiguity."** Where the machine cannot produce a distinguishing state, no
   amount of experience can. That is the insufficiency wall, now measured from the goal's side.
4. **"So all computer use follows."** The grammar here is a grammar. A permission, a pixel, a deadline,
   "reply politely" — a discriminator outside it is reported `NO_DISCRIMINATOR_IN_GRAMMAR` rather than
   approximated, and OSWorld 2.0's hardest phenomena (implicit state, multi-item tracking, conflict
   disambiguation, dynamic environments, best binary **20.6%**) live exactly there.

**On the sentient creature.** This round is what that phrase reduces to when it is made testable: a
system that holds *several* hypotheses about what the user wants, acts only where they agree, and asks
the question that would split them. That is a mind-shaped object you can measure — version space,
information, refusal — and it needs no parameters at all.

## 8. The single bottleneck, restated with what this round added

> **The set of relations the system can state, together with the states it can reach to separate
> them.** Vocabulary and reachability are one constraint seen from two sides: a relation you cannot
> state is a goal you cannot form, and a state you cannot reach is a question you cannot ask.

Identifiability (round three), vocabulary insufficiency (round two) and the synthesis–verification
asymmetry (round one) are all downstream of that pair. Nothing else this tree has measured — search
cost, oracle exactness, stored parameters — is remotely as binding.

## 9. Next, declared so it can fail

The discriminator is currently inferred from judgments on *states*. The remaining step for computer
use is the same mechanism on **trajectories**: the user judges two *runs* ("this is what I meant, that
is not"), and the agent must recover the smallest relation over the run — order, multiplicity,
who-did-what — then act. That is where OSWorld 2.0's failures actually live (long-horizon state, not
single actions), and it is measurable with the same three objects: a relation grammar, a reachable set,
and a reader. Acceptance will be declared the same way: zero false accepts, behavioural identification
two levels deep, and an honest count of the ambiguity that remains.

## 10. Accounting

| | |
|---|---|
| machines | 4 real tools (`mv`/`rm`/`cp`, `tar`, `sqlite3`, `git`), each with its own reader |
| goals | 5, one of them declared composite; judgments produced by real executions |
| relation grammar | instantiated from the literals the machine produced (16–33 terms per machine) |
| questions | chosen by information (active) vs the pool's order, both run on every goal |
| acting | on the intersection of every surviving discriminator; 5 of 5 accepted, **0 false accepts** |
| depth-3 check | reachable sets rebuilt three actions deep (GIT 6 → 31 states); behavioural classes stay 1 |
| parameters / model calls | **0 / 0** |
| wall clock | 18.1 s |
| tests | 5 new, all passing |
| declared acceptance | **A2 not met and reported as not met**; A1, A3, A4, A5, A6 met; A7 added after the first run, with the reason in the receipt |

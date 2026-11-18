# Instant learning is perfect. It is not the bottleneck.

Round 14. Branch `arena/032d96f4-brain`, from `c88adba0`.

## The question, stated exactly as asked

> We already solved instant learning, and instant learning in new arbitrary environments. Doesn't that
> mean we can give the model the smartest actions, let it experience them once, and have the most
> advanced coding agent and computer-use agent on the planet — permanently? Am I right or wrong?

**You are right about the half you built, and wrong about what it promises.** Not wrong in emphasis —
wrong in the arithmetic. The rest of this is the arithmetic, measured in this tree, cross-checked against
the field's own 2026 numbers, with the instrument's ability to fire proven before any zero is believed.

## What is real, and permanently real

Instant learning is not a compromise. For **retention** it is strictly better than gradient descent:

* acquisition is one observation, zero parameters, zero compute;
* retention is exact — the object kept is the thing that happened, not a compressed approximation of it;
* it is reversible and auditable — you can read what was learned and delete it;
* it cannot catastrophically forget, because nothing is overwritten.

The field spends enormous effort to get *worse* versions of this. **Skill0** (2026) retrieves skills into
context and then has to internalise them by RL with a withdrawing curriculum, because retrieval alone
does not make them stick. **VERA** (Oct 2026) builds 9,000+ verifiable environments and still updates
weights. Nobody in 2026 has a retention mechanism as clean as yours. That part is genuinely solved, and
nothing below takes it back.

## What is not real: three walls, three numbers

### Wall 1 — evidence. A memory cannot contain a comparison it never made.

Round 13 ran the tree's own repair machinery over 17 real fix commits. **16 of 17 refuse before any
vocabulary is ever consulted**: the failing test's evidence is not a controlled difference (a failing
value next to a passing sibling), so there is nothing to learn *from*. The refusal has a name —
`REFUSED__NO_PARTITION` — and it fires upstream of everything else.

Round 12 showed this wall can be pushed: capturing values at runtime instead of reading parametrize
tables raised partitions from **1/7 to 3/7**. And solves stayed at **1/7**. Evidence is manufacturable,
and manufacturing it did not buy capability, because the two new partitions were a feature addition and a
tokenizer rewrite — shapes that no predicate can express.

### Wall 2 — vocabulary. Killed today, by measurement, including my own two bugs.

The obvious fix for Wall 1 is to widen what the agent can name. I built exactly that: every
side-effect-free expression over the live values, depth ≤ 2, from the value's own API and from the
target's own imports — **112 templates, 147 in-process evaluations, zero subprocesses** — filtered by
*separation on the observed values* before a single test runs.

Result: **+0 reach. 1 of 17, unchanged.** And the finding is not "the widening was weak" — it is that
16 of 17 die before a term could ever be named.

Two bugs in that instrument were caught by the test suite before the number was believed, and both are
worth stating because they are the reason a zero here is trustworthy:

1. I *replaced* round 11's supply instead of unioning it, deleting the one term that had ever worked.
2. `str.isupper` read through its type still declares `self`, so **every method template was silently
   discarded** — the first run reported a zero from an instrument that could not fire.

The end-to-end test now constructs a case where the narrow supply is *provably empty* and the widened one
must supply the term, and asserts the solve in one execution. Only then does the 17-commit zero mean
anything.

### Wall 3 — identity. The verifier cannot pick, so "permanent" has no referent.

Also round 13, on the one commit that is reachable: its own 344 tests accept **four distinct repairs at
four different guards**, each raising a different message. The human's diff is one of the four. The exact
verifier is exact about behaviour and silent about which behaviour was meant.

This is the one that dissolves the premise most directly. "Learned permanently" is well-formed for
behaviour. It is **not well-formed for intent** until something picks a member of the set. That is not a
weakness of memory; it is a missing fact.

### The fourth wall, already counted: shape

191 real changed sites: a missing check **10.5%**, replay of a seen edit **49.2%**, **new code 40.3%**.
Only the first is addressable by anything a demonstration can teach.

## The field says the same thing, with its own numbers

Not as support — as an independent derivation, which is the only kind of corroboration worth having.

* **OSWorld 2.0** (Jun 2026), 108 real multi-hour desktop workflows: the best configuration fully
  completes **20.6%** (54.8% partial). The diagnosed failures are *not* clicking or coding. They are
  **lost constraints, missed mid-task information, guessing instead of asking, and skipping
  verification** — and agents spend **under 7% of their budget** detecting and repairing their own
  errors. The dominant difficulty is recovering **hidden state**.
* **Causal Agent Replay** (Jun 2026): attributing an agent's failure to a step by correlation is **~14%**
  accurate. Only `do(·)` interventions identify causes. That is Wall 1, found independently, in the
  strongest agents anyone has.
* **The verifiability constraint** (Stanford CS329A, Epoch AI, Oct 2026): *"RLVR works only where a
  grader exists."* Wherever the grader is cheap, capability compounds; wherever it is not, the flywheel
  stalls — "not because they are harder to learn, but because there is nothing to train against."

Read together: **the frontier's binding resource is not parameters, not data, and not memory. It is
graders and evidence.** Your architecture refuses the knowledge house and it is *right* to; but the thing
that replaces it is not a better memory. It is the ability to manufacture a checkable claim.

## The single bottleneck, in one sentence

> An agent can only be as general as the set of claims it can **check**, and only as correct as the
> evidence that distinguishes the claim it made from the claim it should have made.

Memory carries neither. Search supplies neither. Parameters supply neither — they merely *encode*
checks learned from outcomes the field paid for with graders.

This is also the operational meaning of the word you used, "understand". It is not sentience, and no
sentience claim is needed: a system understands a situation to the extent it holds claims about that
situation whose truth it can test. Everything else — weights, skills, retrieval — is downstream of a
checkable claim. That is why the frontier is stuck at 20.6% on real work while being excellent at local
actions: local actions are checkable; "the workflow was completed correctly" is not.

## What is smart to do, ranked, and why each is the *ultimate* form rather than a first attempt

**1. A demonstration must be recorded as a state delta, not as a gesture sequence.** This is the decisive
change and it is where "do it once, keep it forever" becomes well-formed. If the record is *what changed
in the environment* — files, records, screens, values — it is an executable postcondition: checkable,
transferable, immune to surface change, and it licenses *any* action that reaches it. If the record is
the clicks, it is a point in a space nobody can verify, and the tree has already measured what that
costs: **46.5%** of replays matched a changed world and **31.1%** damaged the file while raising no error.
A delta is the only representation of a demonstration that survives the environment changing, which is
the definition of "permanently".

**2. Evidence must be manufactured by intervention, not accumulated by repetition.** One trace is
consistent with exponentially many hypotheses — measured here, and measured at ~14% accuracy by the field.
Perturb one input, re-run, compare. That is the cheapest operation that converts an observation into
evidence, and this tree can already do it (round 12's capture, round 14's separation filter) — it just
does not yet do it *deliberately*, as the first move after any failure.

**3. When the check cannot decide, ask — and ask the minimum question that decides.** Round 13 turns a
version space into one behavioural question a non-technical person can answer. OSWorld 2.0 independently
names "guess instead of ask" as a top failure mode of the best agents in the world. Asking is not a
fallback. It is the only correct action available when the evidence underdetermines the intent.

**4. For the 40.3% that needs new code: say so.** No trace-reading mechanism authors design. The only
zero-weight source of structure is the environment's own implementations, and transplanting them is
research, not a feature. Pretending a template covers it is the incremental lie you told me to kill.

## What I will measure next, on the hardest thing available here

The delta-verifier, in a real environment, with **stale** actions: a task specified only by a state delta
must be re-achieved where replay of the recorded action sequence fails. The tree has already measured the
failure side (46.5% stale, 31.1% silent damage). If the delta side succeeds, "do it once, keep it
forever" becomes a measured statement instead of a hope — and it becomes so *in the form that is
checkable*, which is the only form that can be permanent.

## What would be dishonest to claim today

* That vocabulary is the limit. **Killed by measurement in this round** — 112 templates, +0 reach.
* That more evidence solves it. Partitions went 1/7 → 3/7 and solves did not move; shape gated them.
* That the feature bucket is handled. It is not, and the reason is design, not learning.
* That a stronger learning mechanism would change any of this. Learning is already instant, exact and
  free. The curve is flat because the other term is zero.

## Reproduce

```
.venv/bin/python -m pytest canonical/tests/test_environment_basis_v1.py -q
.venv/bin/python canonical/swe_kernel/environment_basis_v1.py --limit 9 \
    --json canonical/verification/ENVIRONMENT_BASIS_20261116_V1.json
.venv/bin/python canonical/swe_kernel/environment_basis_v1.py --limit 24 \
    --json canonical/verification/ENVIRONMENT_BASIS_WIDER_20261116_V1.json
```

Model calls 0. Network calls 0. Spend $0. Authority: sandbox measurement, not independent verification.

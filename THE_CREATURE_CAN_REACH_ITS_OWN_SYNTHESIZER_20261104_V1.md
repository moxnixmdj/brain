# THE CREATURE CAN REACH ITS OWN SYNTHESIZER

2026-11-04, V1. Result note for `PREREG_THE_CREATURE_CANNOT_REACH_ITS_OWN_SYNTHESIZER_20261104_V1.md`.
Base `9c4bdb0f`. Authority: `NONE`. `truth.achieved`: false. $0. No external models, no neural
weights, no dynamic code execution in result-bearing modules.

Predictions P1, P2, P3, P5, P6: **PASS**. P4: **PASS AS WRITTEN, FAILED AS INTENDED** — see §3a.
The prediction was satisfied by a cache, which is the honest verdict: the route recalls, it does not
generalise across shapes. Two further defects were found that the pre-registration did not anticipate
(both reported below as failures of the tree, not of the predictions).

---

## 1. The defect, restated in one line

The path that actually executes work — `sovereign_perform` — routed on **four hardcoded id prefixes**
(`chase:`, `gap:`, `inspector:`, `repair:`) and answered everything else with
`{"blocked": "UNSUPPORTED_WORK_KIND"}`. Three rounds of synthesis sat behind that list. A problem whose
name the creature did not recognise was refused **before any reasoning happened**.

That is not a temperature setting or a threshold. It is a frozen enumeration of the kinds of problem
the creature is permitted to try to understand — and it is the same defect as a frozen table of
functions, one level up.

## 2. What changed

**A door that does not ask the problem's name.**

```
sovereign_perform:
    ... four known routes, unchanged ...
    else, if the work carries examples + an oracle:
        learned = organ_graph.synthesize_or_disambiguate_skill(
            examples, task_signature=<shape of the evidence>, oracle=oracle)
        settle through core.belief.settle_and_compute_surprise   # same as every other route
    else:
        UNSUPPORTED_WORK_KIND     # unchanged; an empty room is not furnished
```

Four properties, each chosen against a specific way this could have been a fake:

- **No vocabulary.** The new arm does not branch on the id at all beyond "not one of the four kinds
  above". There is no fifth prefix and no list of synonyms. If a future problem needs a new spelling
  to be attempted, the design has failed again.
- **Fails closed.** No examples → `NO_EXAMPLES_TO_LEARN_FROM`. No oracle → `NO_ORACLE_TO_CHECK_AGAINST`.
  The route never invents evidence in order to have something to do, and the original
  `UNSUPPORTED_WORK_KIND` still fires for a work item that carries nothing to learn from.
- **Signature from evidence, not from names.** `_evidence_shape_signature` hashes *arity and input
  types only*. Two differently-spelled problems of the same shape share what was learned; two
  identically-spelled problems with different evidence do not.
- **The answer is checked on the target, not assumed.** After synthesis the organ is evaluated on
  every target input; if any evaluation fails, the whole result is `ok: False`.

## 3. Measured, through the live executor

Each row is a real `Creature`, booted, given a `Work` whose id the router has never seen, and driven
through `sovereign_perform`. Nothing below calls the synthesizer directly.

| | id given to the executor | status | questions | answers vs. truth |
|---|---|---|---|---|
| period-3 block `[5,-2,7]` | `mystery:the-thing-nobody-named` | INDUCED_OPERATOR_CRYSTALLIZED | 14 | `[7, 7, -2]` = `[7, 7, -2]` |
| affine `3x-4` | `mystery:affine` | DISAMBIGUATED_AND_CRYSTALLIZED | — | `[26, 56, -19]` exact |
| same function, 2nd sighting | `mystery:second-sighting` | **RECALLED_TIER0_ORGAN** | **1** | exact |
| same function, 3rd sighting, 5 examples | `zzz:third` | RECALLED_TIER0_ORGAN | 1 | exact |
| same shape, **different** function `[9,1,-4]` | `mystery:looks-the-same` | INDUCED_OPERATOR_CRYSTALLIZED | 14 | `[-4, -4, 1]` exact — stale memory not reused |
| no examples | `mystery:no-evidence` | refused | — | `NO_EXAMPLES_TO_LEARN_FROM` |
| no oracle | `mystery:no-oracle` | refused | — | `NO_ORACLE_TO_CHECK_AGAINST` |
| nothing registered | `mystery:totally-unknown` | refused | — | `UNSUPPORTED_WORK_KIND` (unchanged) |

**Durability:** learn in one process, restart, present the same shape under a new id → `RECALLED`,
`1` question, correct answers. Experience that lives only in the process is a cache, not experience;
the organ is in `P_t` on disk and the recall passes the oracle-refutation check rather than trusting
itself.

### 3a. What 14 → 1 actually is, and what it is not — a correction to this note

I first wrote that 14 → 1 is "the difference between a library and something that has been through an
experience." I then ran the measurement that claim needs, and it failed:

| period-5, measured cold and warm | questions |
|---|---|
| period-5 alone, in a fresh creature | **24** |
| period-5 **after** meeting period-3 and period-7 (24 and 34 questions) | **24** |

**Flat.** So meeting two other periodic structures taught this creature nothing that made a third one
cheaper. What 14 → 1 measures is **recall of the identical shape**, which is a cache hit, not
learning. A cache hit is worth having — it is durable, oracle-checked, and it is what makes a repeated
world cheap — but it is not the same thing, and the pre-registration for this round did not
distinguish them. P4 said "a second work item of the same shape must be cheaper", which a cache
satisfies while generalisation does nothing. A prediction that can be satisfied by a cache is not a
test of learning.

The reason the cost does not transfer is structural, not incidental: the questions pay for *evidence*,
and round 20 already established that a period-P structure costs roughly `4P` observations. Two other
periods do not reduce the evidence a third period requires. **You cannot make a period-5 problem
cheaper by having seen period-3 and period-7.** So "gets smarter" cannot mean "cheaper per problem" in
this class at all.

Where the slack actually is, and what this round therefore does *not* fix: the creature collects those
`4P` points with a **blind linear sweep** (`step = 1`) under a **constant budget**
(`growth_evidence_budget: int = 24`, escalating to at most `2 * 24`). It does not choose a question
because the question would discriminate between its surviving hypotheses. That is observing, not
experimenting — and a probe *policy* is exactly the part that could improve with experience and
currently does not exist. Recorded as the next frontier, not claimed here.

## 4. What this round found that the pre-registration did not predict

Both were found by **driving** the router rather than reading it, which is the whole point of the
round.

**(a) The reported cost of a recall was a lie.** With the route live, the second sighting was still
reported as `oracle_queries_used: 0` — while the tier-0 path had just spent one oracle query testing
whether the incumbent organ was still right. The number was hardcoded. A creature that reports *0
questions* after asking one has a broken account of its own evidence, and every downstream
value-of-information calculation inherits the error. Fixed at the source in
`meta_circular_organ_graph_v1`: the recall path counts from the first query, returns
`oracle_queries_used: 1`, and additionally reports `recall_verified_by_oracle: true` so a caller can
tell "recalled and checked" from "recalled on faith". The fall-through into fresh synthesis now starts
its count from `recall_queries_used` instead of `0`.

**(b) A route in the router could never run.** The `repair:` branch read a module constant named
`_REPO_ROOT` that **did not exist anywhere in the file**, so the branch raised `NameError` on every
call. Under `sovereign_perform` that exception escaped the function entirely, *after* the belief
ticket had been opened — the creature would act and then never learn what it had predicted. This is
the round's own thesis one door over: a capability reported in the tree and unreachable in fact.
Fixed by binding `_REPO_ROOT`, and by making the sandbox call settle-and-report
(`REPAIR_ROUTE_RAISED:<exc>`) instead of propagating. A route that cannot finish must say why, like
every other route.

There is now a test that parses the module and asserts every global name the executor *reads* is
actually bound. Reintroducing the bug fails it (verified by reintroducing the bug).

**(c) My own first signature was wrong in the way this round is about.** It included the evidence
*count*. Two sightings of the identical function at 3 and at 5 samples therefore produced two different
keys and the second was synthesized from scratch — experience silently failed to accumulate, with no
error anywhere. Caught only because P4 asked for a *cheaper* second sighting rather than merely a
correct one. A prediction that merely asked "is the second answer right?" would have passed while the
feature did nothing.

## 5. Honest limits

- **Reaching the synthesizer is not general capability.** The reachable structures are still the ones
  the synthesizer can diagnose: periodicity and affineness over the reachable probe space. A problem
  outside that space still refuses — correctly, and with a named reason.
- **The evidence still has to be supplied.** Someone must hand the work item examples and a way to
  check an answer. This round removed the *naming* gate; it did not give the creature perception or
  the ability to generate its own target questions. That is the next real frontier, and it is not
  claimed here.
- **Recall costs a question, not zero.** The tier-0 path tests its incumbent before trusting it. It is
  cheap, not free, and it now says so.
- **A period table of size P still costs ~4P observations** (round 20). Experience buys
  *expressibility*, never reduced evidence.
- `INDUCED_OPERATOR_CRYSTALLIZED` means *induced from this run's evidence and verified on inputs never
  shown* — not truth. `truth.achieved` false, `authority: NONE`, $0, no sentience claim.

## 6. Receipts

```
canonical/tests/test_the_creature_can_reach_its_own_synthesizer_v1.py   20 passed
regression set (11 suites, incl. rounds 17-20)                         152 passed, 5 subtests
execution_guard/repo_integrity_guard_v1.py                             violations=0 -> PASS
canonical/runtime/enforce_goal_hierarchy.py --base 9c4bdb0f            DRIFT_GUARD_PASS
```

Every claim above is produced by `sovereign_perform` on a real booted `Creature`, not by calling the
synthesizer directly. That distinction is the entire content of this round.

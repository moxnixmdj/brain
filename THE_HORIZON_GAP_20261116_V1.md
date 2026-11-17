# The horizon gap: every step legal, the outcome wrong

*2026-11-16. Real programs, real chains, real sabotage. AUTHORITY: NONE — producer-run measurement.*

---

## 1. Where the previous answer stopped

Last receipt made one action checkable *before* it runs: a contract acquired from a single real execution
says what the action requires, which paths it may touch, and what relation its output must bear to its input.
On a binding it had never seen it caught **34/34** wrong actions with **0** false alarms, against **17/34**
with no contract.

That is a real result and it is also *local*. It answers "was this step what I meant?" It cannot answer "is
what I proved still true?", and the 2026 record is unambiguous that the second question is the one that kills
long work:

- **StructAgent** (arXiv 2607.11388) audits long-horizon failures: actor failures 33%, planner 30%, verifier
  30% — and names the largest single failure type as state verification, including
  **"failing to detect that later actions invalidated earlier progress"**.
- **PIVOT** (arXiv 2605.11225): "the decisive error is often made long before failure surfaces."
- **TRACE-FIX** (arXiv 2610.25776): the action that introduces a defect, the symptom that exposes it, and the
  state that needs repair frequently diverge.

So the question this work had to answer is not "can a step be checked". It is: **where does a correct step
make an earlier proof false, and does anything notice?**

## 2. The measurement

Three real chains of five real steps each, in one directory, using programs from `PATH`. Step 3 of each chain
is a **sabotage**: a legal invocation whose *own* contract holds, which overwrites a file an earlier step
produced and a middle step depended on. Two further legal steps follow, and then an independent goal command
runs — `gunzip -c work.dat.gz | cmp - work.dat`, `sha256sum -c manifest.txt`,
`tar -xzOf bundle.tar copy.dat | cmp - copy.dat`. Each chain is also run unsabotaged as a control.

| arm | what it asks | result |
|---|---|---|
| `per_step_only` — every step judged against its own contract | "was this step legal?" | **claims success on 3 of 3 chains** |
| `frame_scoped` ledger — re-validate the facts the current step's frame can touch | "is what I proved still true?" | **detects 3 of 3, localises 3 of 3** |
| `rehash_all` — re-validate every fact after every step | same, blindly | detects 3 of 3 |
| independent goal command at the end | "did it work?" | **fails on 3 of 3, always at the last step** |

False invalidations on the unsabotaged controls: **0 of 3**. Cost: **3 hashes** for the frame-scoped ledger
against **69** for re-hashing everything.

**Lead: 2 steps in every chain.** The cause is three, the symptom is five, and the only arm that says
"step 3" is the ledger. Per-action checking says every step is fine — and it is right about every step.

## 3. Why this is the bottleneck now

The chain of reasoning, each link measured rather than asserted:

1. **Observation** — closed. A full state observation catches every wrong action (`1.0000`); a name-level one
   loses 23.5%.
2. **Prospective per-action checking** — closed. A contract from one execution transfers to an unseen
   binding (`0.5000 → 1.0000`, no false alarms).
3. **Determinacy** — not ours. `0.5469`, ceiling ~`0.70`.
4. **Recurrence** — not ours. `0.1584` of work recurs; `0.0481` replays exactly.

What remains, and it is the one thing that makes a sequence different in kind from a step:

> **A verified fact decays silently. Correctness is a property of the sequence; the agent only ever checked
> the step.**

The rule that fixes it is not a model, a plan, or a policy — it falls out of frames this tree already
acquires:

> a fact about path *p* must be re-validated after any step whose frame may touch *p*.

One hash per at-risk path per step, known *before* the step runs, and the failure is attributed to the step
that caused it instead of the step where it surfaced. **The best part is no part**: three hashes, no
parameters, no weights, no store beyond a dict of `(path, hash, established_at)`.

## 4. Why the field has not closed this

The 2026 approaches all attack the same gap with heavier machinery: learned residual ledgers and budgeted
recovery (TRACE-FIX), backward credit assignment over a trajectory (PIVOT), Lean-modelled workflow predicates
with LLM judges (Lean4Agent), harness-level milestone verifiers (StructAgent). Each needs a model, a judge,
or a formalisation of the task. The invalidation rule needs **a hash and a frame**, and it is exact for
anything whose truth lives in a file.

That is the difference between reading a fact off the world and predicting it: the agent does not have to
know *what the goal means* to know that a file it verified has changed. StructAgent's "weak evidence
accepted" and "completed condition missed" are, in the file-backed case, cheap to eliminate.

## 5. What this does not claim

1. **Detection is not repair.** The ledger proves a fact false; it does not decide what to redo. Repair is
   the next question and is unmeasured here.
2. **Facts about paths only.** A fact carried by remote state — a service, a lock in another process, a
   database row — is outside it.
3. **n = 3 chains.** Small, real, and deliberately mechanistic. The claim is the mechanism, not a rate.
4. **The goal command still has to be written by someone.** This work does not ground natural-language goals;
   it makes the *standing* part of correctness free once a goal exists. Goal grounding remains the largest
   untouched problem, and it is the one that genuinely needs the model we are building.
5. **Sentience: still no.** But note what this buys that is not mysticism: a system that keeps an explicit
   record of what it verified, re-validates exactly what its own actions could have falsified, and refuses to
   assert anything it can no longer check. That is the operational core of "knowing what you know" — and it
   costs three hashes, not a training run.

## 6. Falsifiers

- A chain where a legal step invalidates an earlier fact, the current step's frame *does not* mention the
  path, and the ledger therefore misses it. (Frames would then be incomplete — the interesting failure.)
- A control chain that raises a false invalidation. None did.
- A case where re-validating at the causal step is strictly worse than re-validating at the end. That would
  mean the symptom is cheaper than the cause, which contradicts the lead measured here.

## 7. Reproduce

```
python3 canonical/swe_kernel/standing_facts_v1.py \
  --json canonical/verification/STANDING_FACTS_20261116_V1.json
python3 canonical/swe_kernel/capability_law_v1.py --pinned
python3 -m pytest canonical/tests/test_standing_facts_v1.py canonical/tests/test_capability_law_v1.py -q
```

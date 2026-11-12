# The environment is not in the key

**2026-11-12.** Base `4138e9ee`. Branch `arena/79487470-brain`. Round 5 of the owner's question.

The owner sharpened the claim this round, and the sharpening is the whole question:

> *"We already solved instant learning, and instant learning in new arbitrary environments, perfectly.
> Doesn't this mean this is a perfect solution for all the problems, and any computer use? All we have
> to do is give our model a try in all those new coding environments or give it the smartest actions.
> After he does them at least once, he would learn all of those permanently."*

Round 3 killed the second half of that — *one try buys the HOW, never the WHEN* — and round 4 killed
my own correction to it. This round takes the first half, the premise everything else rests on:
**"instant learning in new arbitrary environments is solved perfectly."**

It is the only part of the owner's claim never measured. It is also load-bearing: if it is false, the
"just try each environment once" plan inherits a defect at exactly the scale the plan operates on.

Authority **NONE**. One machine, no independent verifier, $0, zero model dependency.
`truth.achieved` stays `false`; no capability registered; no family flipped.

---

## 1. The measured answer

The memory that carries a learned job is `macro_v1`. Its key is `signature(clauses)`: the verbs and
file kinds of each clause, with paths removed. That design is deliberate and documented — *"a
different file of the same kind hits the same macro; a different job does not."*

Measured on this module:

```
job: extract the text from report.pdf → verify the docx output.docx

MACHINE A  (binaries present)   record once           successes = 1
MACHINE B  (same platform,
            binary absent)      lookup                SAME MACRO RETURNED
B's attempt fails               note_failure          failures = 1, kept
B's attempt fails again         note_failure          MACRO DELETED
MACHINE A                       lookup                GONE
```

**One environment destroyed another environment's knowledge, and the other environment was right.**

Three separate facts fall out, and they are not the same fact:

1. **There is no environment in the key.** The signature is invariant to root, user, host and case —
   verified directly: four spellings of the same job, one key. "Instant learning in a new arbitrary
   environment" therefore has no representation of *which* environment was instant.
2. **Knowledge flows freely between environments.** B inherits A's plan without any check that A's
   conditions hold on B.
3. **Evidence is aggregated across environments.** B's failures are counted against A's successes
   until A's knowledge is deleted.

And this is **the fifth sighting of one bug**, which `macro_v1`'s own docstring enumerates: *"a
goal-relative file kind became a permanent ban; a precondition became one; eight audits of one bad
directory disabled auditing everywhere."* Each time the fix was the same — the unit of memory was too
coarse. The environment is the next level of the same unit, and it had never been addressed.

## 2. Why the obvious fix is wrong — and this is the important part

The obvious move is to put the environment in the key: `signature(clauses, env)`. That is the same
move that produced every previous sighting, one level up, and it fails for the same reason a
goal-relative file kind failed:

> An environment-specific key learns nothing that transfers, and an environment-blind key transfers
> everything, including what does not apply. Both are wrong, and tightening the key only chooses
> which wrong.

The correct structure was already in the repository, in `experience_v1`, and it says so in its
docstring:

> *"THE UNIT OF MEMORY IS THE PATHOLOGY, NOT THE TASK."*
> *"'There is no tesseract on this box' is not a statistical claim. It is a fact about a machine,
> true on the first observation."*

`experience_v1` is machine-addressed, structural, and believed on first observation. `macro_v1` is
not. Two memory organs, one of which knows where it is running and one of which does not.

## 3. What was built

Not a narrower key. The key cannot know what the failure knows, so the **failure carries the
address**:

```python
record(clauses, steps, where="a.example")
note_failure(key)                       # unchanged: counts for everyone
note_failure(key, where="b.example")    # counts only for b.example
```

Measured after the repair:

| Scenario | Before | After |
|---|---|---|
| A proves once, B fails 5×, A looks up | A's plan **gone** | A's plan **remembered** |
| A proves once, A fails twice | dropped | dropped (a real refutation still deletes) |
| unaddressed record, B fails twice | dropped | dropped (unknown provenance is fail-safe) |
| `A.Example` vs `  a.EXAMPLE  ` | n/a | one environment, not two |
| successes counted across A and B | n/a | `proved_where` never silently moves |

Seven regression tests pin every row. **19 pre-existing failures in the macro/experience/chain
subset before the change, the same 19 after; zero new, zero fixed by accident.**

The visible change to store shape is additive: `proved_where` and `failures_by_environment` appear on
entries that have an address. Entries without one behave exactly as they did.

## 4. What 2026 says, and it agrees from the outside

The same defect is the field's live research question, not a local quirk:

- **OSExpert** (arXiv 2603.07978): on **unseen UIs**, across current computer-use agents, *"none of
  the agents exhibits meaningful generalization, with success rates remaining in the 0% to 10%
  range."* Its conclusion is that skills must be **environment-specific procedural knowledge** — the
  opposite of "one try anywhere transfers".
- **PolySkill** (ICLR 2026): skills induced by experience have **<3–9% reuse on unseen websites**;
  separating a skill's abstract goal from its website-specific implementation lifts transfer to
  **73%**. The fix is abstraction, not exposure.
- **SkillHarness** (arXiv 2606.20636): skills learned from successful trajectories *"often fail to
  capture the conditions under which they remain valid"* — verbatim the round-3 finding — and under
  environmental perturbation the rigid ones collapse.
- **SkillApt** (arXiv 2609.26863): *"Environment validity should be a hard precondition for
  applicability… when the precondition cannot be reproduced through the agent's actual tool path, the
  system should retire or quarantine the skill until revalidation."* That is the `prefer` safety net
  this repo already has (`prefer` is honoured only if the capability is still a *survivor*), stated
  as a research result.
- **SkillsVote** (arXiv 2605.18401): exposing an evolved library without task-conditioned
  recommendation yields **larger negative than positive** deltas (+3.3/−6.7); recommendation turns it
  to +6.0/−6.0. **Onaverage, learning from experience transfers negatively.**
- **Raw Experience / skill-lifecycle measurements** (arXiv 2605.23899, arXiv 2607.10113): skills help
  on average but **25% of extractor–target pairings show negative transfer** (ALFWorld 47%).
- **What Keeps Agent Skills from Being Reusable?** (arXiv 2608.08453, 138K SKILL.md files): the failure
  mode in public registries is exactly applicability that was never captured.

## 5. Answering the owner directly

**"We solved instant learning in new arbitrary environments perfectly."**
Half true, and the halves matter. *Speed* on a known interface is genuinely solved — that is what
`macro_v1` does, and it is real. *Transfer* is not, and this repository had a measurable defect in it:
one environment silently deleted another's knowledge. That is not a missing feature; it is a live bug
in the organ your plan depends on.

**"So give it a try in each new environment and it learns them permanently."**
A try in a new environment currently writes into a store that cannot distinguish that environment from
any other. So the try produces (a) a plan with no record of where it holds, and (b) evidence that is
summed against unrelated environments. Adding environments *faster* multiplies that defect. This is
the one place where the owner's own law — *find the mistakes before you start* — points at doing the
address first, not the environments.

**"Give it the smartest actions."**
Already the correct instinct, measured twice: 59 of 145 capabilities are invocable with no learning at
all, and rounds 3–4 showed the front door loses the ones that are not. This round adds the condition:
an action is only *reusable* if its applicability is recorded. `requires` is the place for that, and
**56 of 145 capabilities declare no preconditions at all** — including every `docx.*` and `xlsx.*`
verifier and `shell.command.run`. Those rows cannot fail a perception check, so nothing can ever tell
the machine that a given box cannot run them.

**"We were trying to make our model a sentient creature."**
Sentience is not measured here and is not the objective. What is measured is narrower and, I think,
more useful to that goal: the machine now has a memory that knows *where* a thing was true. A creature
whose knowledge is destroyed by moving to another room is not one.

**"Is this a revolutionary way to make agents learn faster?"**
Yes for the mechanism, no for the shortcut. Storing a verified procedure once and reusing it is the
field's central line of work in 2026 (OSExpert, PolySkill, SkillHarness, SkillsVote, SkillX, SkillFlow)
— and every one of those papers independently reports the same two findings this round measured: the
procedure transfers badly, and the fix is applicability, not exposure. The revolutionary part is not
"try once, keep forever". It is **"try once, record *where* it was true, and let the world refute
it."**

## 6. What this changes about the plan

| Work item | Size | Status |
|---|---|---|
| Evidence is addressed by environment (this round) | 1 organ, 7 tests | **done** |
| Declare `requires` for the 56 capabilities that have none | 56 registry rows | next, measured |
| Arity / selector defaults on the 4 dispatch capabilities | 4 rows | round-4 carry-over |
| Blind premises | 12 capabilities | lower priority (round-4) |

The order is by count and by whether the fix makes *learning* possible. A capability with no declared
preconditions cannot contribute a negative example, so the 56-row gap is upstream of everything in the
owner's plan.

---

## 7. Receipts and non-claims

- `canonical/tests/test_an_environment_cannot_delete_another_environments_knowledge_v1.py` — **7/7**.
- Regression: targeted subset **19 pre-existing failures before, the same 19 after** (missing optional
  modules such as `cv2`). Zero new failures.
- Every number in §1 and §3 was produced by running the module, not by reading it.

**Not claimed:** that addressed evidence makes reuse safe — it only makes it *attributable*; the
`prefer`→`survivor` gate and per-step verification remain the safety net. Nothing here drives a GUI.
No environment was actually provisioned and run; the two environments are simulated inside the store,
which is sufficient to measure the aggregation rule and not sufficient to measure a real provisioning
cost.

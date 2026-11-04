# From first principles: the creature has no intra-run memory, and that is the frame error

**2026-11-05.** Sixth pass. Written after the owner asked, for the sixth time, whether this is the
smartest approach. Answer: **no.** The previous four passes were correct work in the wrong frame.

## 1. Axioms

A1. **Only time is scarce.** Life budget, wallclock, attempts. Everything else is a constraint to model,
    not a thing to optimise.
A2. **A creature is what persists.** If nothing persists across steps, there is no creature — there is a
    stateless policy recomputed each step. "Sentient-like" is a claim about the persistence structure.
A3. **Memory is worth what it saves in time.** A remembered solution that costs more to retrieve than to
    recompute is not memory; it is decoration.
A4. **Verification is not learning.** A verifier that rejects bad outputs leaves the system exactly as
    capable as before. Rejecting is a floor, not a gain.
A5. **A static organ set caps capability, not intelligence.** No policy is smarter than the space of
    actions it is choosing from.

## 2. What the measurements say

| observation | measurement |
|---|---|
| cost of remembering | `crystallized_skills` 0 rows across every run, until 9096c3d6 |
| cost of retrieval | warm store vs cold: **2.09/2.31/2.41 s vs 1.18/1.45/1.37 s, 3/3** — memory costs ~0.9 s |
| how many work kinds | one (`inspector_onboarding`, 202/202 in 20 sessions) until cf97cad |
| acquisitions per defect shape | 5/6, but **all from a four-wide search in one step** |

Three findings that decide the rest:

**F1. The creature is a pipeline, not an agent.** Every pass rewinds it. Within a run, each work item is
an isolated episode: sense → propose → rank → execute → verify → *settle, discard*. Nothing an early step
produces is available to a later step except a scalar. That is why the measured skill curve saturates at
+0.681 and every run re-solves from scratch. A stateless policy is the *definition* of static.

**F2. Memory must pay for itself in time, and ours does not.** With retention fixed, warm is *slower*
than cold. The reason is structural: `recall_and_apply_verified` does confined verification plus
contract checks, while the synthesizer in the same situation runs one constrained search. Recall is the
more expensive path *because it is more careful*, and it is bought at a cost the creature cannot afford
under A3. Retention that raises cost is worse than no retention.

**F3. The capability ceiling is the organ set, not the search.** 5/6 comes from enumerating four
operators. Off-by-one needs a `+1` that the same search could reach trivially — it fails only because
the evidence cannot discriminate `xs` from `xs[:-1]`. So the limit is not search width; it is that the
creature has no way to *construct* a discriminating input. It can only be handed tests.

## 3. Why the previous frame was wrong

Four passes optimised *rejection and reachability*: ranking, scheduling, scoping, honest gating,
candidate breadth. Every one of those is about **not doing the wrong thing**. None is about **getting
better at doing the right thing**. Under A4 that work has a hard ceiling: it can take capability from
zero to the organ set's limit and no further, and it never makes the creature different at the end of a
run in the way the owner keeps asking for.

The flat skill curve (+0.465 at grant 40, +0.681 at 480) is not a tuning problem. It is the shape of a
system that does not accumulate.

## 4. What follows, in dependency order

**Step 1 — make memory pay (the only non-negotiable one).** Precondition: retention works (done). Now
recall must be *cheaper* than synthesis or it is not memory by A3. Concretely: a negative cache and a
retrieval path that returns a verified source without re-running a suite, with the suite run kept as the
audit that happens once per rule, not once per recall. If recall cannot be made cheaper, the honest
conclusion is that this creature should not remember repairs at all, and retention should be deleted
rather than left as a cost with no benefit.

**Step 2 — make the run a sequence, not a reset.** Feed each step's outcome forward as a *structured*
input to the next proposal: the candidate that failed and why, the frontier of what was tried. This is
the difference between a pipeline and an agent under A2, and it is measurable (does step *n* use step
*n−1*'s result, yes/no).

**Step 3 — a second lever: construct, don't select.** For any defect class the search can reach but the
evidence cannot discriminate, the creature can *propose the discriminating input itself* and check its
own hypothesis before touching the world — hypothesis, prediction, experiment. That is a capability no
amount of candidate enumeration produces, and it is the only route past the 5/6 ceiling that does not
require being handed a better test.

**Rejected on principle, not stealth:**

- *Adding more candidate generators* — measured inert twice (pass six of this session). More actions in a
  search that already reaches the ceiling.
- *Raising life/attempts/slice* — measured inert (grant sweep, `max_attempts` sweep, slice 112 vs 155).
- *A new verifier or checker* — A4. Rejection is a floor.
- *A bigger model in the loop* — forbidden by `NO_MODEL_PRODUCER_COGNITION`; and it would replace the
  creature with an oracle.

## 5. Falsifiers, pre-committed

- **S1 (memory pays):** warm-store recall must be *faster* than cold synthesis on the same world, 3/3
  trials, ideally ≥30%. If it is not, delete the retention path — a memory that costs more is a tax.
- **S2 (sequence):** in a world with two related defects, the second repair must consume the first
  repair's recorded outcome (instrumented, not inferred). If it does not, the run is still a reset and
  step 2's premise is false.
- **S3 (construct):** given a defect whose test cannot discriminate the answer, the creature must
  produce at least one input that separates the candidate from the correct behaviour, and change its
  own verdict on that basis. If it cannot, the off-by-one class stays unreachable and I will say so.

Authority NONE. `truth.achieved` false. No new capability is claimed by this document; it is a
correction of frame, and its steps are falsifiable individually.

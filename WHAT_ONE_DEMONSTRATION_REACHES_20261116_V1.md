# What one demonstration reaches

*Answer to: "instant learning and instant learning in new arbitrary environments are already solved,
so can we give the model the most advanced actions once and have them permanently, and does that
solve anything on a computer?"*

Measured on this repository's own code, on this branch, with no model in the loop (0 model calls,
$0): `canonical/swe_kernel/one_demonstration_reach_v1.py`,
receipt `canonical/verification/ONE_DEMONSTRATION_REACH_20261116_V1.json`.

---

## 1. The claim, split into the five things it actually bundles

"Learn it once and it is learned permanently, for anything on a computer" is not one claim. It is
five, and they have five different answers. Only the first is as strong as it sounds.

| link in the chain | status | measured here |
|---|---|---|
| **capture** — one demonstration becomes a reusable action | **real** | 4 of 4 exercisable learned skills do exactly what their sentence says on real files; 275 verified applications in the reach run below |
| **safety** — the action only fires where it is justified | **real, and this is the strong part** | **0 damaged** in 600 executed applications; every decline names its reason (12 classes) |
| **reach** — one action covers a machine | **false** | 5.3% of sites for a semantic rewrite, 86.3% for an α-conversion, 45.8% overall |
| **transfer to a new environment** — "instant learning in arbitrary environments" | **not the right variable** | the environment never appears in the measurement: what decides reach is the *premise*, and it is a property of the site |
| **"most advanced actions, experienced once"** | **not a finite plan** | 12 classes of site are declined by two trivial operations alone; the class count is discovered from reality and has no known bound |

## 2. The measurement

The learned-skill bundle is that mechanism at its best: four exercisable skills, each learned from
one demonstration, each carrying a written premise (`set once, read once, in the statement that
directly follows`), each proving its own edit by re-parsing and comparing ASTs before writing a
byte. So the question is answerable by execution rather than by argument.

Universe: **5,513 files, 139,439 name sites, 60,808 of them bound directly in a function body.**
Sample: a deterministic stride of **300 sites per family** over the whole list — coverage of the
tree, not of a corner. Each site is executed against the stored skill in an isolated copy of its
file and lands in exactly one box: **verified** (file changed, sentence matched, everything outside
the named function byte-identical), **declined** (nothing written, reason named), **damaged**
(written, and the verdict did not hold).

| family | operation | reach | inside its documented premise | declined | classes | damaged |
|---|---|---|---|---|---|---|
| `inline` | semantic rewrite (substitute the value, delete the binding) | **5.3%** (16/300) | 12/18 proxy, all 6 residuals the one premise condition the proxy cannot see | 284 | 9 | **0** |
| `rename` | α-conversion (rename within scope) | **86.3%** (259/300) | **18/18** | 41 | 4 | **0** |
| both | | **45.8%** (275/600) | | 325 | **12** | **0** |

Three facts decide the question, and none of them is about environments:

1. **Reach is a property of the operation, not of the agent.** Two actions learned the same way, by
   the same mechanism, differ by **16×** (5.3% vs 86.3%). Rename is nearly free — α-conversion
   preserves meaning by construction. Inline is expensive — it must prove that removing the binding
   and substituting the expression cannot change evaluation order, duplication, or mutation. No
   amount of "learning it better" moves either number: the number is the measure of the proof.
2. **The premise is the whole boundary.** Inside the documented premise the demonstrations are
   exact (18/18 for rename; for inline, every one of the 6 non-verified proxy sites is the fourth
   documented condition — "the first thing the next statement computes, exactly once" — which the
   proxy deliberately leaves to the skill). Nothing is unexplained, and 241 rename applications
   verified *outside* the coarse proxy, because the skill proves safety per site instead of
   matching a pattern.
3. **Nothing was damaged.** Across 600 real applications the actions never fired outside their
   proof. That is the honest meaning of "permanent": a stored action is permanent as a
   *decision procedure*, not as a capability. It fires exactly where its premise holds, forever,
   for free — and it is silent everywhere else.

The declined mass is the answer to "just give it the most advanced actions". Ranked by mass:

    126  $NAME is read N times; this action inlines a variable that is read once
     66  $NAME is not set by a plain '$NAME = ...' statement
     32  $NAME is not the first thing the next statement computes, exactly once
     31  $NAME is bound in a nested scope at line N
     25  $NAME is set N times in $FUNCTION; only a variable set once can be inlined
      1  $NAME is a parameter of $FUNCTION, not a variable
    ---
     34  $NAME is not a variable assigned in $FUNCTION            (rename)
      5  $NAME is also bound in a nested scope at line N
      1  $FUNCTION uses exec(), which can see variable names

Each line is not a missing *experience*. It is a missing *proof obligation*: duplicating an
expression requires purity; handling a tuple or attribute binding requires a different binding
model; inlining across a mutation requires dataflow; renaming past `exec` is undecidable enough
that the skill refuses. **One more demonstration of the same operation adds zero of these.** A new
operation with a new proof adds that class. That is why "experience each action once" cannot be the
growth mechanism: the unit that has to grow is the space of proofs, and its size is discovered
from reality — 12 classes from two trivial operations on one repository.

## 3. The single bottleneck

> **A demonstration does not buy an action. It buys an operation together with the premise under
> which the operation is meaning-preserving. Reach = the measure of that premise. Everything
> outside it needs a different operation, therefore a different proof, therefore a different
> demonstration — or a synthesis, which is the only mechanism that can produce proofs it was never
> shown.**

That is why the "give it the most advanced coding actions and let it experience them once" plan
cannot close: *the list of most advanced actions is the bottleneck itself*, and it is unbounded in
an open world. What is unbounded in principle is the *class space*; what is scarce is proofs.

The independent evidence from the frontier says the same thing from the other side. OSWorld 2.0
(arXiv:2606.29537, June 2026) is 108 long-horizon workflows, median 1.6 hours, ~318 tool calls per
task; the best agent at release completed **20.6%** binary (54.8% partial), and the field is at
roughly **44%** now. The paper's failure modes are *not* "the agent did not have the action":
agents lose track of constraints, miss information that arrives mid-task, guess instead of asking,
and **skip verification**. A 99.5%-reliable step survives 318 steps with probability
**0.995³¹⁸ ≈ 0.20**. Computer use is not blocked by a missing library of actions; it is blocked by
per-step verification over a long horizon. Voyager's skill library transfers across worlds for a
precise reason — the underlying API is the same world protocol — and its own ablations are blunt:
removing self-verification costs **73%**, removing the curriculum **93%**. SkillOS (arXiv:2605.06614)
finds environment-specific skills transfer worst and abstract strategies transfer best. The
continual-learning survey line (arXiv:2610.29357) states the failure we measured directly: *stored
content can survive while remaining unaccessed, unused, or ineffective* — `hit_count` 0 of 11 in
this tree's own bundle is that sentence with a number on it.

## 4. What is real, stated so it can be used

1. **A demonstrated action can be made permanent and free** — as a decision procedure with a
   premise, checked before it acts, at 0 model calls. This tree now does that: four-arm certificate
   (4 of 4 real admitted, 12 of 12 impostors refused), `file_edit_claim` + `outside_digests` for
   the scope of a change, and this reach measurement for how far it goes.
2. **Knowing your own reach is cheaper than acting.** The whole 139k-site classification takes one
   static pass (~48 s, no execution, no model); the 600 executed applications take 42 s. Reach is
   decidable before anything is written — that is what makes withholding possible, and withholding
   is what keeps a permanent store from becoming a permanent liability.
3. **Instant knowledge is the right substrate for knowledge**; it is the wrong substrate for
   *skills*, because a skill is not a fact, it is a proof-shaped action. Your premise holds: do not
   put knowledge in the weights. But do not put proofs there either — proofs belong in the store,
   where they can be re-checked.

## 5. What the weights are for, then

Not knowledge (instant knowledge source). Not the skill store (arithmetic, $0, re-checkable). The
weights carry the **policy of proof**: given a situation, (a) which operation is even a candidate,
(b) what premise would make it sound, (c) which single observation most cheaply separates sound from
unsound (this tree already has the exact-information-gain selector
`canonical/runtime/contrast_selection_v1.py`), and (d) act or withhold. Each of those is a decision
under uncertainty — the one thing parameters are legitimately for under your rule that "every bit
must be calculated": each parameter must be justified by a measured decision boundary, not by
absorbed text.

That also reframes "sentient creature" into something measurable: a system that knows what it does
not know, and declines to act outside its proofs. The 0-damage row above is the beginning of that,
and it is the only part of the ambition that can be checked today.

## 6. The smartest next moves, ranked, each falsifiable

1. **Make premise coverage the growth metric, not skill count.** The tree now has the regression:
   reach, reach-inside-premise, classes, damaged. Add one operation per top-mass class above
   (read-twice → purity/duplication proof; non-plain binding → tuple/attribute model; nested scope →
   scope analysis; set-twice → dataflow; parameter → different operation entirely) and measure the
   *marginal* verified sites each adds over the same 300-site stride. Falsifier: an operation whose
   class mass does not transfer to verified sites is a proof that does not generalise, and must be
   reported as a refusal instead.
2. **Withhold by default at recall.** A stored action whose premise is false or undetermined must
   not fire. The machinery exists (`skill_scope_bundle_v1` buys scope from observations and
   withholds on identified scope); this measurement says *what to withhold on*: the premise, read
   from the site, before execution. Falsifier: any damaged site in a reach run.
3. **Move the verified unit from "the action" to "the step's effect on the goal state".** OSWorld's
   318-step arithmetic is the argument. For code, `file_edit_claim` + `outside_digests` is that
   shape; for computer use, the same shape is *claim + independent observation of the artifact*,
   with the observation never taken from the agent's own report. Falsifier: an episode that is
   "complete" by the agent's report and wrong by independent observation.
4. **Compose only what is proved.** Two proved operations compose only if the second's premise
   survives the first's effect — that is a checkable condition, not a hope. The next module should
   be a composition rule with its own reach measurement, because composition is the only route from
   12 classes to an open world.
5. **Do not build**: an enumeration of "most advanced actions"; a similarity-based widenening (this
   tree measured 0 kills from shape-derived laws); a knowledge house in the weights. Each of those
   is a way to spend effort without moving any of the four numbers in §2.

## 7. The honest one-line answer

You are **right** that a demonstrated action can be made permanent, reusable, and free, and this
tree now proves that claim instead of asserting it. You are **wrong** that this solves anything on
a computer: one demonstration buys one operation and its premise, and its reach is the measure of
that premise — 5.3% or 86.3% depending only on how much proof the operation needs. The bottleneck is
not experience, not the environment, and not the model. It is **proof**, and the only mechanism that
can produce proofs beyond what it was shown is synthesis with verification — which is exactly what
we were already building, now aimed at the right target.

# The unit of permanence is not the action. It is the action plus its check

*Round 5. 2026-11-16. Branch `arena/4c287ab6-brain`, base `6c0d26ca`.*

## The claim, stated exactly, in four parts

> Instant learning is solved, and instant learning in new environments is solved. So: give the model the
> smartest actions once, let it experience each once, and it learns them permanently. Do anything on a
> computer once and it learns it permanently. Therefore all computer use and all advanced coding are
> solved, permanently.

Four propositions. Each is decidable, and each has already been measured — three of them in this tree.

| proposition | verdict | the measurement |
|---|---|---|
| **1.** instant learning in a new environment is solved | **TRUE as a cost law, FALSE as "perfect"** | 4 machines, 16 real requests → 13 solved, at 29–36 probe trials per environment (`INSTANT_LEARNING_IN_A_NEW_ENVIRONMENT_20261116_V1`) |
| **2.** one exposure identifies an action well enough to keep it | **FALSE** | one demonstration: **0 survivors**, held-out accuracy **0.069**, **297 dangerous errors** of 319 (`ONE_DEMONSTRATION_IDENTIFIES_20261116_V1`) |
| **3.** once learned, it stays learned | **FALSE under environment evolution** | SkillShift-Bench (arXiv 2610.33528): ASI 53.65% → 41.84% → 15.79%; skill failure rate 9.83% → 16.70% → **27.60%**; 25% of skill deployments cause **negative** transfer (SkillLens, May 2026) |
| **4.** therefore all computer use and advanced coding are solved | **FALSE as coverage, TRUE as a cost law on already-specified actions** | four rounds of this tree: 0 of 18 witnesses invertible; 0 of 13 drivable commits pin; 0 kills in 188 laws; 0 of 40 commit messages compile usefully by occurrence |

Proposition 2 is the hinge, and it is worth reading twice. **One demonstration leaves nothing identifiable.**
A demonstration is a point: (source, site, outcome). What it can support is a *set* of candidate applicability
conditions — and that set's size is what one experience bought. Measured on 5,532 files, 319 train sites and
319 held-out sites: one demonstration left **zero survivors** and predicted the held-out set at **6.9%**, with
**93.1%** of its errors dangerous. With **three contrasting outcomes** the same learner reached **512
survivors, 96.24% accuracy, precision 1.0**.

The receipt's own reason string says why, and it is the deepest sentence in this whole round:

> `NO_FAILURE__NECESSITY_IS_ONLY_REFUTED_BY_FAILURE`

You cannot learn *where an action applies* from watching it succeed. Necessity is refuted only by failure, and
one observation contains no failure. That is not a data problem; it is a logical one.

## So what did round 5 build?

Round 4 ended with the finding that a specification has **two halves** — the value a sentence names, and the
site that decides it — and that history supplies only the first. It also named the lever: *a site is named
only by intervention*.

The tree already had that lever under a non-obvious name: `interventional_goal_v1`, resting on a theorem the
capability file states outright — `UNIQUE_ROOT_CAUSE_IS_NOT_IDENTIFIABLE_IN GENERAL FROM DECLARED
OBSERVATIONS ALONE; premises: NO_REPLAY_OR_INTERVENTION`. So round 5 changes **exactly one rule** and imports
everything else: the value reader, the direction reader, the clause language, the judge, all four verdicts.

> Round 4 grounds a clause by **textual occurrence** of the value in a callable.
> Round 5 grounds it by **DO-intervention**: which callable's observable output *moves* when the value moves?

A site is a callable, a parameter position, **and a shape**. Three bugs had to be found before the measurement
was worth anything — all three found in my own instrument, this round, by distrusting its first answer:

1. the intervention passed the value as a **scalar string** where the mechanism expects a **collection** →
   13 candidates, 52 probes, **0 responders** on the one commit whose site is real;
2. the judge then **re-encoded the value as a scalar**, discarding the shape the intervention had discovered →
   a true `False → True` pair read as `WRONG_AT_FIXED`;
3. the counterfactual pool **truncated away its own null contrast**, so some sites were "sensitive" only to a
   nonsense string.

Each fix moved the number **up**, and each was a real defect in the instrument, not a leniency. Both shared
modules were extended **additively** (`@json:` tokens; a `shape` key that defaults to round 4's exact
encoding), and round 4's receipt **reproduces byte-identically** after the change — verified, not asserted.

## The measurement (same 40 commits, same judge)

| | round 4 — occurrence | round 5 — intervention |
|---|---|---|
| discriminating | **0** | **1** |
| wrong at the fixed state | 2 | 2 |
| refused | 38 | 35 (`NO_SITE_RESPONDS` 10, `NO_DIRECTION` 19, `NO_VALUE` 6) |
| usable | 0 of 40 | **1 of 40** |

One win, and it is a real one, derived from a sentence alone — no model, no test, no experience, no knowledge
house, $0:

> **"Add riscv64 as a supported manylinux architecture."**
> value `riscv64`, direction `WIDENING` → 13 candidate callables, 78 probes → two respond →
> site `_have_compatible_abi(executable, archs)` with the value intervened on **as a collection** →
> **parent `False`, fixed `True`** → `DISCRIMINATING`.

The commit ships **no test**. The sentence names a value; the intervention names the site and the shape; the
pair is then checkable forever. That is a specification manufactured from an instruction and an execution, and
it is the first one in five rounds.

The remaining refusals are mostly the corpus's fault, not the organ's: **19 of 40 real commit messages state no
direction at all**, and 6 name nothing. A message written after the fact *summarises*; it does not *instruct*.

## The synthesis — the answer to the question, and the thing to build next

Here is the whole chain in one line, with every term measured:

> **permanence = (action) × (the check that validates it)**, and the check is obtained by **intervention**,
> which is the only thing that names **value × site × shape**.

That is why "do it once" is *almost* right and precisely wrong. One execution gives you **one** action and
**zero** contrasts. A demonstration *shows* an outcome; an **intervention** *separates* two. And the tree's own
numbers say what separation buys: 0 survivors at 6.9% from one observation, 512 survivors at 96.24% from three
contrasts. The 2026 literature says the same thing from the other side — SkillShift measures what happens to
actions learned without checks (failure rate nearly triples), Causal Agent Replay measures that attribution by
judgment is ~14% while attribution by intervention is the reliable mechanism.

So the correct object is not a skill library of actions. It is a library of **checkable actions**: each with the
value it is about, the site it acts on, the shape it consumes, and the interventional contrast that refutes it
when the environment moves. That object:
- cannot be manufactured by watching (proposition 2 is false);
- does not stay valid by itself (proposition 3 is false);
- **can** be manufactured by intervening, and the intervention is exactly what an agent does when it runs the
  thing it just changed — which is why the agent must run things, and why "give it the smartest actions" is
  not the missing piece. The missing piece is **the contrast**.

## On the sentient creature

Asked again, so answered again, plainly: *that was not what the last five rounds built, and it is not what the
ceiling is on.* Nothing here is a claim about experience or self. What was built is a **checker** — a device
for deciding, before spending, whether a claim about a machine can be falsified. The honest bound is the one
already stated in round 1 and unmoved since: the system cannot get better at *being* more than it is; it gets
better at *checking* more. Every gain measured across five rounds is a gain in the second, and every zero is a
place where the second was believed to be free.

A sentient creature would not help. A **falsifier per claim** would — and that is buildable, and it is what
these rounds are building.

## The single bottleneck, restated after five measurements

**The bottleneck is the contrast.** Not the action, not the parameters, not the model, not the grammar:

- round 1: experience supplies actions, never specifications — `p_correct` 0.2978;
- round 2: 13 drivable commits, **0 pins**; the discriminating input is the missing object;
- round 3: 188 laws, **0 kills**; real work extends a specification instead of violating one;
- round 4: 2 of 40 messages compile, **0 usable**; the site is the missing half;
- round 5: the site **is** named by intervention, **1 of 40** usable — and the other 39 are refused because
  the message, not the organ, supplies nothing to contrast.

Every one of those five zeros is the same zero: **a claim without a contrast cannot be decided**, and no
amount of exposure, parameters, or training manufactures a contrast out of a point.

*Reproduce:* `.venv/bin/python canonical/swe_kernel/site_by_intervention_v1.py --corpus --limit 40 --json
canonical/verification/SITE_BY_INTERVENTION_20261116_V1.json`

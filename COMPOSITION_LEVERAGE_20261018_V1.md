# THE FASTEST PATH: COMPOSE, DON'T HAND-WRITE — measured 2026-10-18

Authority: NONE. Credit: 0. Spend: $0. Model dependency: 0.

---

## 0. Correction first — I was wrong about the machine's body

In `LIMITING_FACTORS_TO_ACTIVE_GOAL_20261018_V1.md` I listed **network egress** as blocker #1 and
wrote that the machine "has almost no hands and almost no eyes on the outside world."

**That is false, and it was the same mistake for the ninth time: I described my sandbox and
called it the machine.**

- The machine runs on `runs-on: ubuntu-latest` GitHub-hosted runners — **general internet
  egress, apt, everything**.
- `FRONTIER_LIMITING_FACTORS_20261017_V1.md` already recorded: **67/67 runnable on the public
  runner.**
- The two network-dependent families are listed as blocked **"in this sandbox"** — my dev
  environment, not the machine's runtime.
- `web.browser.rendered.capture.chromedriver` is one of the 67 and works there (the frontier doc:
  *"67/67 after a one-line apt fix"*).

**The machine already has hands, eyes, and the internet.** The correct statement of the limiting
factors is therefore much narrower than what I wrote. This file supersedes §1–§2 of that
document on the egress point.

---

## 1. The mechanism was already in the brain

`canonical/runtime/capability_planner.py`:

> *"Zero-dependency capability-graph planner... plans over externally declared capabilities
> (preconditions/effects/cost/action contracts). It does not interpret arbitrary natural language
> and it does not call a model. Unknown effects fail closed so the acquisition layer can search
> for a missing capability instead of guessing."*

It provides `reachable_effects()` (the closure) and `_resolve_effect_bindings()` (bind one
capability's output to another's input).

**That is automated service composition** — the exact technique the research literature has
studied for two decades (HTN planning / SHOP2 / OWLS-Xplan, PDDL encodings, non-deterministic
planning with strong-cyclic and contingency plans). It was never missing. It was never wired to
the bound registry.

And the registry already declares precisely the contract the planner consumes:
`provides` (effects), `requires` (preconditions), `cost`.

---

## 2. The real bottleneck, measured

Feeding all 67 bound capabilities into the planner:

```
capabilities                              : 67
distinct effects they provide             : 90
facts nothing produces (come from world)  : 30
capabilities that are DEAD                : 0
```

Then the number that matters:

```
outputs produced but consumed by NOTHING  : 82 of 90
capabilities whose input comes from
  another capability's output             :  9 of 67
```

**82 of the machine's 90 outputs are dead ends.** The tools work; almost nothing flows from one
into the next. The reason is visible in the vocabularies themselves:

- produced: `yaml.to_json`, `pdf.extract.text`, `json.query.transform`, `docx.document.create`
- required: `json.file.available`, `pdf.file.available`, `artifact.file.available`

These are the same things under different names. `yaml.to_json` produces a JSON file; the
consumer asks for `json.file.available`; the two strings never unify, so the edge does not exist.

**This is not a capability problem. It is a type-vocabulary problem.** The research literature
reached the same conclusion and solved it with semantic service annotation (OWL-S, SAWSDL,
semantic types) — the surveys note the blocker is precisely that *"different organizations use
different concept models... there does not exist a unique language to define and evaluate the Web
services."*

---

## 3. The leverage, measured

I wrote a ~30-line `SATISFIES` table mapping each produced effect to the consumer facts it
actually satisfies (prototype, hand-read off the two vocabularies). Results:

| | before | after | change |
|---|---|---|---|
| capabilities that chain into another | 9 / 67 | **44 / 67** | **4.9x** |
| two-step compositions available | 10 | **95** | **9.5x** |
| capabilities reachable in ≤2 steps | 77 | **162** | **2.1x** |

**67 hand-written tools become 162 reachable capabilities, from ~30 lines of data.**

No model. No retraining. No new mechanism. No hand-written families. It is a data change on top
of a planner that already exists, and it runs in milliseconds.

For scale: hand-writing families for the 38 unexercised capabilities was going to take ~19 PRs at
the governance cap of two per PR. This is one PR.

---

## 4. Where the genuinely new primitives come from

Composition only recombines what exists. For capabilities that cannot be composed, the
model-free answer from the literature is **synthesis from execution traces**, which beats LLM
approaches on exactly this task:

- **LogLoom** (OOPSLA'26): synthesises automation scripts from event logs — *"identical to
  reference solutions for 60 out of 72 benchmarks, compared to 14 for an existing symbolic
  approach and 39 for an LLM."* And critically: *"unlike LLMs, LogLoom will never generate
  invalid solutions."*
- **Syren** (CMU): synthesises scripts from **partial** traces, recovering the "hidden logic" the
  operator performs in their head, via correctness-preserving program rewrites plus SyGuS.
- Programming-by-Demonstration / Programming-by-Example (Gulwani et al.) — the established
  model-free lineage.

These are Brain-legal (`NO_MODEL_PRODUCER_COGNITION`) because the producer cognition is symbolic
search over a program space with a verifier — not a model. They fit the route order's terminal
step, `SYNTHESIZE_NEW_PRIMITIVE`.

So the full architecture is:

```
compose what exists   -> capability_planner + type unification   (built, needs wiring)
synthesize what's new -> trace-to-script synthesis (LogLoom/Syren pattern)   (not built)
verify independently  -> existing oracle discipline               (built)
learn instantly       -> flywheel_v1                              (built, proven)
never stop short      -> goal_chase_v1 / target_chase_driver_v1   (built, proven)
never call it fastest -> completeness gate                        (rule in canon, wiring unverified)
```

Five of six already exist. The missing one is being measured, not invented.

---

## 5. Caveats — what this measurement is and is not

- The `SATISFIES` table is a **prototype I hand-authored by reading the two vocabularies**. It
  demonstrates leverage; it is not verified truth. Each mapping must be individually proven
  (does `yaml.to_json` really emit a file satisfying `json.file.available`?) before it carries
  credit.
- Reachable-closure counts are **graph reachability**, not verified capability. A composition is
  only a real capability once it is executed and independently verified on held-out instances.
  Reaching it is necessary, not sufficient.
- 67 → 162 understates the ceiling: the table is deliberately conservative and covers ~32 of the
  90 produced effects. Untyped domain-specific outputs (chart raster, python repair internals)
  are left unmapped.
- `capability_planner.py` is "deliberately small" and classical. It does not handle
  non-determinism, sensing actions, or replanning on failure — the literature's answers for that
  (strong-cyclic plans, contingency strategies, FF-Replan style determinization) are not
  implemented here.

---

## 6. Next actions, in order

1. **Prove each `SATISFIES` mapping** rather than asserting it — turn the prototype into a
   verified artifact, one mapping at a time, with the independent-oracle discipline.
2. **Wire the planner to the registry** so composition is a runtime operation, not a measurement
   script.
3. **Verify the completeness gate** on the chase (owner requirement #5) — does the machine obey
   the "global minimality needs completeness" rule that is already in the canon?
4. **Only then** consider trace-based synthesis of genuinely new primitives.

Everything above is agent-actionable, model-free, and $0.

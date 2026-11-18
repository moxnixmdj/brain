# The run already contains the intervention

*2026-11-19 · measurement: `canonical/verification/THE_SAME_GUARD_TWICE_IS_THE_DISCRIMINATOR_20261119_V1.json`
· tool: `canonical/tools/the_same_guard_twice_is_the_discriminator_v1.py`
· intent: `canonical/action_intents/THE_RUN_ALREADY_CONTAINS_THE_INTERVENTION_20261119_V1.json`*

---

## 1. The claim, and the two functions inside it

> "Instant learning and instant learning in new environments are solved. So all we do is give the model a
> try in each new environment, hand it the smartest actions once, and it owns them permanently. Isn't
> coding and computer use therefore solved?"

Two functions hide in that sentence, and only one of them is solved.

**Retention** — keeping competence across environments — is solved, and it was already measured here:
`O(machines × adaptation) + O(requests)`, crossover at the second or third request. That part of the
sentence is correct and this round does not contest it.

**Identification** — deciding *which* action was right, from what the environment did — is not solved, and
repetition does not buy it. One try produces one trace, and one trace is consistent with exponentially
many hypotheses: every hypothesis that agrees on this input produces this output. The version-space bound
is not a metaphor; it is why a single demonstration is the maximum-variance estimator.
`INSUFFICIENCY_CERTIFICATE_20261113_V1` states the sharper case: when the causal observable is absent from
the representation, no number of repetitions separates the hypotheses, because they are *the same
observation*.

So the question is not whether one try teaches an action. It is whether the trace of one try contains
what a second observation would have given — a **contrast**. This round built the cheapest possible
contrast and then measured, on commits nobody had looked at, how far it actually gets. The answer is
below and it is not flattering: the contrast is real, it is free, and on its own it is **not enough**.

## 2. The weights question, answered by a parameter count

The instruction was explicit: our own parameters, every bit *calculated*, never a knowledge house, and the
best part is no part.

The operator this round adds has **zero parameters**. Not few — zero, and the receipt carries the count
next to the measurement instead of asserting it:

```
"parameters_stored": 0
"bits_from_the_oracle": 409        # 15 fresh commits x the flips they needed
```

Each bit is one execution of the project's own test command with one firing of one guard flipped, and each
bit is the exit status it returned. The table is discarded when the row is written: nothing measured on
one commit is available to the next. The only thing that crosses tasks is code, and the code contains no
fitted quantity.

That is what "the best part is no part" means operationally, and it is the answer to "should we train our
own weights on our own traces": a weight is a compressed summary of many observations used *in place of
one*. Here the observation is exact, free, and re-derivable in about 50 microseconds, so a summary would be
a lossy copy of something we can recompute. The right number of parameters for identification is zero, and
any future round that spends compute learning what it can re-measure is buying the worse artifact.

The one thing that *is* stored is instant knowledge in the form the tree already has — the store, lookup
measured at 40.6 µs against a 7.69 ms question. This round adds nothing to it and removes the reason to
believe the store needs parameters to be useful.

## 3. The operator: the second firing is a free counterfactual

The previous round indexed candidates by the failing run's values and walked one chain: the message quotes
a value → the value has a producer → the guard above it let it through. It derived the human's fix for
`click@1b0e19f505` at rank 0, and returned `NO_BLAME` for 14 of 29 real commits, because an exit code, an
exception type and a wrong list are not values that appear in a message.

This round stops reading the message. It reads control flow and asks a question the message cannot answer:

> This guard let the wrong path through. **Which firing of it was the wrong one?**

No second environment, no second trace: a guard that fires twice inside the failing run has already been
evaluated under two different states. The run *is* the contrastive pair, and the intervention is one
boolean, injected into a copy of the module — same lines, same numbers, semantics identical unless a flip
is asked for:

```python
if __brain_switch__(sid, guard_test, operands):     # counts firings; flips firing k on request
```

Flipping firing *k* of site *s* costs one bit, and the project's own pytest returns the verdict. Then the
refinement is **not searched for**: the same hook logs what was in scope at every firing, and the predicate
that must hold at one firing and not the others is selected by **exact fit** against those logged values —
no scoring function, no threshold, no ordering by learned frequency.

On `click@1b0e19f505` (in-sample: the case this tool was built on) the log says

| firing | `self.show_envvar` | `self.envvar` |
|---|---|---|
| 2 | `True` | `'bar'` |
| 3 | `True` | `None` |

`self.envvar is not None` is the only candidate that is `False` at the wrong firing and `True` at the right
one, so the refined guard is `(self.show_envvar) and (self.envvar is not None)` — the human's fix in the
human's form, with no failure text, no diff, no function name, no problem statement. It is verified by
patching the **uninstrumented** source and running all 144 tests in the file: green. Cost: 90 flips, 53.7 s.
That is the whole mechanism, and it works exactly as advertised *on a guard bug*.

Three properties make it a mechanism rather than a demo:

* **The flip must be a single firing.** The same guard is correct at firing 2 and wrong at firing 3; any
  edit that changes the guard for both breaks a test that was passing. This is also why "flip the whole
  predicate" — the classic predicate-switching formulation — cannot reach this case.
* **A flip that breaks other tests is not a repair.** The suite has to stay green, not just the one test —
  and on the fresh corpus every one of the seven flips that passed the one test failed this check.
* **A fit with no other firing is refused.** If a guard fired once there is nothing to separate, and the
  tool would happily emit `guard and (x == <the value it had>)` — a lookup table in a predicate's clothes.
  Vacuous refinements are the standing failure mode of every "learn from one trace" method; the refusal is
  the feature.

### Why this is not the field's counterfactual

The 2026 literature runs the same idea, approximated. AgenTracer (ICLR 2026) *defines* the decisive step by
counterfactual replay and then has DeepSeek-R1 guess which step to replay; CausalFlow (arXiv 2605.25338)
computes causal responsibility by step-level intervention, where the intervention is a model's rewrite of a
step; the public review of "Who Broke the System?" (arXiv 2607.07989) says it plainly: *"the Judge does not
execute R and only approximates this criterion by reasoning over the logged trajectory."*

Here the counterfactual is **executed**, once per firing, at about half a second per verdict, with no model
anywhere in the loop. The literature needs a frontier model because it intervenes on natural-language
steps, where an intervention must be *written*. A guard is already an expression in a language with an
interpreter, so the intervention is a boolean and the engine that applies it is the engine that produced the
failure. **Where the artifact is executable, counterfactual attribution is not a reasoning problem.** That
is the part of the user's intuition that is exactly right, and it is worth its zero parameters.

## 4. The measurement, on commits nobody had looked at

The prior round's population was four libraries' histories chosen by hand and partly studied while the tool
was built — the "bugs we already know work" problem the user named. This round changes the population
first and looks at nothing twice: a mechanical rule, run before either arm was measured.

**Corpus.** `git log --no-merges` over the newest 600 commits of click, httpx, jinja2 and attrs; keep a
commit only if it touches at least one `tests/*.py` **and** at least one non-test `.py`; primary test file
and primary source file are the ones with the most changed lines. Sample every 7th candidate (every 3rd in
a second pass). A candidate is admitted only if the oracle exists: at the **parent** commit, with the
**post-fix** test file written in, the file runs and at least one test genuinely fails. Two pre-registered
quality rules, both applied before any arm was measured: failing share < 10% of the file, and — after a
defect found mid-round — a skip is not a failure.

**15 commits** survived: click 6, jinja2 5, attrs 4. (httpx contributed none: at every sampled commit its
test files died in collection. attrs `f53fc5440d` and `c44b8b0052` were dropped when the "failing" tests
turned out to be tests that had skipped themselves.) Both arms ran on the same 15 commits, same oracles,
same sandbox.

| | arm A: the failure text | arm B: the flipped firing |
|---|---|---|
| rows | 15 | 15 |
| seconds | 56.8 | 251.1 |
| cost | ≤ 5 candidates per site | 409 flips = 409 bits, 421 guard sites, 18,598 logged firings |
| proposed a site at the human's changed line | **1** | **2** (and 1 more within 2 lines) |
| produced the human's expression | **0** | **0** |
| refusals | `NO_BLAME` 6, `NO_GUARD` 4 | `NO_SWITCH` 10 |
| flips that turned the failing test green | — | **7, on 5 of the 15 rows** |
| of those, suite still green | — | **0** |
| of those, exact-fit refinement available | — | **0** |
| would have been claimed as repairs by a version without the gates | — | **7** |

The last line is the one that matters for integrity. Seven single-firing flips, spread over five of the
fifteen commits, made the failing test pass. Every one of them had `file_green: false` next to it in the
receipt (1 to 8 other tests broke), and none admitted a refinement that fit the logged values. A version of
this round without those two gates would have reported "the flip repairs a third of fresh commits" and
would have been wrong seven times out of seven.

And the in-sample case that does work — `click@1b0e19f505` — is **in-sample**. This round produced exactly
one verified repair, on the case the tool was built on. That is the honest count, and it is the same
self-congratulation trap the user described, caught in the act.

## 5. What the misses are, precisely

Post-hoc (disclosed as post-hoc), each row is bucketed by whether the human's edit touched an existing
expression, and by the distance from what each arm proposed to the line the human actually changed:

| commit | class of the human's fix | arm A | arm B |
|---|---|---|---|
| click `9f0bcdf0d8` | adds `Parameter.spec` (new behaviour) | far | none |
| click `f25f697a43` | new argument behaviour | far | none |
| click `271effb3d9` | adds `get_help_spec` (new behaviour) | no blame | none |
| click `a1d87858ab` | termui behaviour | no blame | same line, suite broke |
| click `1f9cd54f68` | termui behaviour | no guard | none |
| click `047adef258` | command behaviour | no blame | far, suite broke |
| jinja `227edfd372` | message construction (`repr`, plural) | no guard | none |
| jinja `d655030770` | regex `\s` → `[\s/>=]` | **same line**, wrong expression | none |
| jinja `065334d1ee` | `attr` filter routes through `env.getattr` | no blame | same line, suite broke |
| jinja `d05bd3858c` | adds an argument (`context`) | no blame | none |
| jinja `91a972f580` | new sandbox logic (`format` indirection) | no blame | within 2 lines, suite broke |
| attrs `0f758fe54a` | `ca.converter` → `ca._converter` | far | none |
| attrs `cbaef3f8f5` | `optional` validator argument | far | far, suite broke |
| attrs `af9c510912` | validator behaviour | no guard | none |
| attrs `5bab46deb9` | validator behaviour | no guard | none |

Read the third column: not one of the fifteen human fixes is a refinement of a guard. Twelve change a
*value or an expression* — an attribute name, a regex, an argument, a call's routing — and three add
behaviour that did not exist. The mechanism that worked so well on `click@1b0e19f505` works there because
that commit *is* a guard bug, and guard bugs are the class the tree has been studying. This is what the
user's objection looks like when it is measured instead of argued.

Two worked examples, both single-expression edits, both reachable in principle:

* **attrs `0f758fe54a`** — the fix is `ca.converter` → `ca._converter`, one attribute in a call argument.
  Arm A blamed `decl` (unrelated). Arm B flipped 90 firings in `_make.py` and found nothing: no guard's
  truth value was involved. The wrong value is a *name*, and the observation never compares it.
* **jinja `d655030770`** — the fix replaces the whitespace regex with `[\s/>=]`. Arm A *did* land on the
  changed line and blamed `key` = `'class\tonclick=alert(1)'` — the right place, the wrong quantity — then
  had nothing to write. Arm B never executed that region's guard during the failing test.

The negative result is not "the tools are bad". Both arms are cheap and both are exact when they fire; the
`click@1b0e19f505` verify is real. The finding is that **the observable identifies a place and a
discrepancy, and never the expression that computes the right value.**

## 6. The single bottleneck

The question was: what one thing, if fixed, unlocks the most capability?

Not the parameters — there are none, and this round adds none.
Not the observation device — the intervention is free and now measured: 409 bits, 254 seconds, 15 commits.
Not the index, which the previous round named — it is cheap and, on three of these fifteen, it reaches the
human's line.
Not the search width — the prior rounds already measured that a bigger pool does not help (median rank 22
once the site is writable).

**The bottleneck is the replacement expression: the content of the fix.** The run can say *where* the wrong
value was produced and *which* firing let it through; it cannot say what the right value is, because the
right value is not in the artifact at all — it is the thing that has to be invented. 12 of these 15 fixes
are a value the failing run never produced (a different attribute, a different regex, an extra argument),
and 3 are behaviour that did not exist (which
`INSUFFICIENCY_CERTIFICATE_20261113_V1` already proves is unreachable from any trace).

This is the sharpest form of the answer, and it moves the frontier by one step: last round's bottleneck was
"which site", and that turned out to be *soluble* — this round solved it for 1 bit per candidate — which
means the capability that is actually missing is **synthesis with an exact verifier and a space derived
from the artifact itself**, not attribution.

The one thing this measurement does *not* license is the conclusion everyone reaches at this point: get a
model to write the expression. That is exactly the "use a model and call it ours" move the rules forbid,
and it also loses the only property that makes the result worth having — that every bit is calculated,
verifiable, and inspectable. The alternative is the tree's own route: force the value at the firing the
flip fingerprinted, and synthesize the expression from the artifact's vocabulary
(`force_the_value_and_see_v1` + `expressions_from_a_site_v1` do both halves at function scale). What this
round contributes to that composition is the **address** — site plus firing, at one bit each, with a
refusal when the address is not discriminating. The falsifier for that round is stated below.

## 7. What this means for "give it the smartest actions once"

The actions are not the knowledge. A smart action, given once, transfers as a *policy* only where the
environment is the same; where it differs, what transfers is the *contrast* that made the action right.
This round shows that the contrast can be manufactured for free from a single failing run — and that it
still leaves the interesting half of the problem untouched.

For computer use the mapping is direct and worth stating because it is the 84–95% bucket in OSWorld 2.0:
the failing final-state check is a *comparison*, exactly like a guard's test. The same instrument applies —
instrument the check, log the values it compared, flip the firing whose comparison was wrong, and fit the
refinement by exact fit. What it will not do is invent the missing capability (an absent menu item, a
stale coordinate); that is the synthesis half again, and it is why "everything on a computer is solved"
is false in 2026 no matter how good the action library is.

## 8. Falsifier

**This round's claim dies if** a mechanism that forces the *value* at a flip-identified firing, and
synthesizes the replacement expression from the artifact's own vocabulary, does not beat **0/15** on a
fresh mechanical corpus of the same construction — or if it beats it only by reading the commit's diff.

**The user's claim dies if** any of the fifteen rows above is repaired by supplying the right action once
and repeating it. None is.

## 9. Limits, stated plainly

* 15 commits, three libraries, one sandbox, producer-run. Not a benchmark; a causal probe with a stated
  population rule.
* Localization is *given* to both arms (the changed source file). A system that must find the file is
  strictly worse than these numbers.
* The log vocabulary is the enclosing function's locals plus the enclosing class's `__dict__` attributes,
  nearest-first. It is calculated from the AST, but it is bounded, and the exact-fit gate fails closed when
  the discriminator is outside it. That is why 5 flips produced no refinement, and the receipt does not
  distinguish "spurious flip" from "discriminator outside the vocabulary" — a stated limitation, not a
  result.
* Reading `self.__dict__` avoids firing properties, so the measurement cannot perturb the object it
  observes, at the cost of not seeing class-level defaults.
* The in-sample `click@1b0e19f505` result is in-sample. One verified repair, on the case the tool was
  built on.

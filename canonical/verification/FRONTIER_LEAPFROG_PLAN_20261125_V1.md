# The leapfrog plan — 25 November 2026

Not "how do we catch up". Catching up is arithmetically impossible on their axis
(99.4 % SWE-bench Pro V2 is a rate over 642 tasks produced by a rented model with
a 1M-token window). The plan is to win a *different* axis that the frontier has
publicly admitted it cannot hold, and to make that axis measurable.

## 1. What the research says is unsolved, right now

Three problems, all in areas where our assets are already unusual:

1. **Test-time continual learning.** NeurIPS 2026 chartered a workshop on it, with
   the premise stated plainly: frontier models are frozen at deployment and any
   apparent adaptation "comes from prompting, retrieval, memory, or external
   tools rather than genuine internal learning"; agents "do not improve from
   repeated mistakes, and erase prior skills when updated naively". aTTT buys
   retention, not learning (1.9× cost). JitRL shows training-free memory can beat
   fine-tuning — the first serious crack in the "you need gradients" wall.
   SkillEvolBench concludes the bottleneck is **selective procedural
   abstraction**, not storage: agents "adapt locally but rarely form robust
   reusable skills".
2. **Long-horizon state.** OSWorld 2.0 strict binary tops out at 20.6 % and
   collapses to ~0 % past 163 minutes. GUI world models look plausible and are
   unusable: GUI-CC finds best offline task progress 16.7/100 and asks, in its
   own conclusion, for *explicit state representations or memory modules*.
   CUWM's most valuable output is not a screenshot — it is a textual description
   of what changed.
3. **Verification-first synthesis.** LeetProof beats single-mode synthesis at the
   same budget by validating specifications with property-based testing *before*
   generating code. Verified synthesis is a budget win, not just a safety
   property.

And one **measurement failure** the whole field is living inside: Mem0
self-reports 93.4 % on LongMemEval; an independent run of its open-source edition
scores 32.4 %, and GPT-4o-mini with *no memory layer at all* scores 57.6 %.
Whoever measures honestly owns the category.

## 2. The wedge, in one sentence

**We are the only system whose state is explicit, whose claims are receipts, and
whose context cannot rot — and the frontier's three open problems are all
symptoms of not having those three things.**

Everything below is a way to spend that advantage where it is worth points, not
where it is flattering.

## 3. Six plays

Each play states the frontier's failure, our unusual move, the first measurable
step, and the kill criterion. A play that cannot be killed in a week is not a
play, it is a slogan.

### Play 1 — The world model that is a contract, not a renderer

*Frontier:* CUWM predicts the next screen (text, then pixels). GUI-CC measures
what that buys: 16.7/100 progress, "usable-looking screens while losing
task-relevant state".

*Our move:* predict the **state delta as a typed effect contract** and check it
against the real environment after the action. No pixels, no generator, no
rendering. The prediction is falsifiable at the next observable, which is exactly
what a world model is for and exactly what a screenshot model cannot do. We
already own the pieces: effect contracts, provenance maps, observable traces,
refusal on unobservable effects.

*First step:* over one scripted desktop workflow (10 steps, 3 branch points),
record predicted deltas and compare with observed accessibility-tree deltas.
Report: prediction accuracy, action loops prevented, state-loss events caught.
*Kill:* if delta prediction accuracy on the observable fields is under 0.6, or
catching state loss does not reduce loop count, the play is dead and the honest
report says so.

### Play 2 — Consolidation without gradients ("sleep" that is a proof compressor)

*Frontier:* aTTT trains adapters during the episode and keeps competence at 1.9×
cost. Lightweight latent memories still need a few gradient steps. JitRL proves a
non-parametric memory can substitute for RL — with logits we do not have.

*Our move:* a nightly pass that **compresses receipts into laws**: merge
duplicate laws, demote laws whose refutations exceed their confirmations, promote
laws that fire across independent repos. Output is a smaller store with the same
refutation power — measured, not asserted. This is the discrete analogue of a
closed-form policy update: no gradient, no loss, an auditable rule with a bound.

*First step:* run it over the 45-commit corpus. Report compression ratio at equal
refutation power (laws before/after, false-refutations before/after), and whether
a held-out commit set loses any coverage.
*Kill:* if compression below 5 % at equal refutation power, or coverage drops on
held-out commits.

### Play 3 — Induction with an abstain option (selective procedural abstraction)

*Frontier:* SkillEvolBench's headline is that agents adapt but do not form
reusable skills; the failure is *selection*, and NSI shows state-aware branching
is what separates a skill from a compressed trace.

*Our move:* a skill is admitted only if it **refuses on every stored negative**.
We already measure isolation at 50 % precision / 100 % recall and law recurrence
at 6/6 across repos. The unusual part is the admission rule: abstention is the
gate, not a fallback. That is the opposite of how agents usually acquire skills
(store everything, retrieve by similarity), and it is precisely what the
self-evolving-agent paper found breaks stability.

*First step:* build a 40-episode induction set from commits we already hold:
teach on one, test on three variants, require the induced law to refuse the
negatives. Report precision/recall and cross-family transfer (the 0/36 result is
the number to beat).
*Kill:* if cross-family transfer stays 0 and precision does not exceed 0.5 with
abstention, the gate is decorative.

### Play 4 — The context that cannot rot (a benchmark we can win outright)

*Frontier:* Anthropic's own numbers: compaction +29 %, with a memory tool +39 %,
84 % fewer tokens; "as tokens in the window increase, accurate recall decreases".
Multi-agent runs cost 15× chat tokens. Everyone is engineering around a window.

*Our move:* we have no window, and the curve already exists in this tree
(`o1_bucket_law_store_scaling_ablation_20261124_v1.json`, 0 model calls):

| laws in store | median match | p95 match |
| ---: | ---: | ---: |
| 1 | 0.2723 ms | 0.3996 ms |
| 10 | 0.2581 ms | 0.3355 ms |
| 100 | 0.2514 ms | 0.3102 ms |
| 500 | 0.2687 ms | 0.3156 ms |

500/10 latency ratio **1.04×**, and the removal control — delete the matching
law, hits drop 1 → 0 — shows the lookup is real rather than a constant. The
honest limit is stated with it: exact-match retrieval over indexed laws, not
open-ended reasoning.

*First step:* one page that puts that table beside the token cost a window-based
harness pays to hold the same store (Anthropic's own figures: 150K-token
compaction trigger, 84 % token reduction from editing, 15× chat tokens for
multi-agent). Add the 1,000-law point, which is the only gap in the curve.
*Kill:* if latency grows superlinearly at 1,000 laws, the claim dies.

### Play 5 — Publish the refusal rate (a category nobody is in)

*Frontier:* no board scores abstention. The models that self-report 96 % also
produce confident wrong patches with no published refusal rate.

*Our move:* an **abstention benchmark**: for N tasks, does the system say "I
cannot, because X" — with X checkable? We already do this in anger: 43 of 51
tasks refused with `FAIL_CLOSED`, `store: STORE_FILE_ABSENT`; a receipt edited
after the fact is refused; an observer that changes the program is refused.
Publishing a refusal *rate with reasons* is a first, and it is cheap for us.

*First step:* 100 tasks, each labelled solved / refused-with-reason / wrong.
Report the three numbers and the reason histogram. *Kill:* if refusals are under
20 % or the reasons are not checkable in 90 % of cases.

### Play 6 — Adversarial verification of our own instruments, sold as a service

*Frontier:* verifier-in-the-loop papers exist; no published test-of-the-test with
surviving mutants named.

*Our move:* mutation testing on every capability we claim — 10 supervisor, 7 DOCX,
11 scheduler mutants today, with false negatives published. Turn it into the
admission gate for the harvested surface: a capability that cannot be mutated
into a failure is not a capability.

*First step:* apply one mutation per newly admitted capability; publish survivors.
*Kill:* if survivors exceed 20 %, the gate is theatre.

## 4. The lift, and why it is now a pipeline rather than a hope

The instruction that hidden capabilities must be at the unified runtime is not a
side quest; it is the engine of plays 2, 3 and 6. The loop is now proven end to
end, this week:

```
census (626 discovered)  ->  execute through the lane (producer receipt)
        ->  CI re-runs as a different identity with GitHub OIDC claims
        ->  load_verified_registry admits   (447 -> 449, two surfaces)
```

Two surfaces crossed it — `binding_pin_is_current_v1`, `capability_selection_retrieval_v1`
— verified by `github-actions:moxnixmdj/brain`, not by us. The remaining 622 are
blocked on **inputs**, not authority.

**The lift target, stated numerically:** 10 admitted from the discovered set in
seven days, 40 in thirty. The mechanism is per-surface input synthesis from the
module's own documented contract (41 of the 622 are contracts whose inputs are
written in their own docstrings), one receipt each, then the CI gate. Nothing is
declared; everything is re-run by someone else.

Second lift, same rule, different layer: the 82 diverged branches hold 1,776
files that are not on `main` (146 runtime, 82 tools, 53 swe-kernel, 30 bound
adapters). Pick the ones that are *plays*: `cdfc4713` (closed-loop slider 2/5),
`4f36ef34` (decision loop), `086851e2` (chart extractor), `98e3c624`
(lesson-as-substitution), `e705f1be` (BugsInPy blind runner), `b81b2217`
(differential state tomography, instant skill stores, the comparison document).
Land one per day, with its receipts, or record why it dies.

## 5. Sequence

**Seven days.** Play 1 first step (delta contracts on one workflow); Play 2 first
run (compression at equal refutation power); 10 admissions through the OIDC gate;
Play 4 page published. Success = four measured numbers and no new prose.

**Thirty days.** Plays 3 and 5 to first results; OSWorld-style harness on the
delta contracts if Docker/KVM arrives, otherwise the scripted desktop workflow
with real consequences; 40 admissions; the union of branch-only plays landed or
killed with a receipt each.

**Ninety days.** One public, reproducible artifact per play: a benchmark, a
dataset, or a store. Not a paper — a thing someone else can run. The frontier
cannot copy the refusal rate without giving up the confident wrong patch, and
cannot copy "flat recall" without giving up the window. That is the moat.

## 6. What we will not do

* **Not** chase the SWE resolve rate with a better scaffold. The gap is ~99 points
  and the frontier spends 15× our tokens to hold it.
* **Not** train weights. aTTT and the latent-memory work both show the gains are
  retention, not learning, and we would lose the only property nobody can copy.
* **Not** build a memory "system" with a vector store. The independent numbers
  say a file-based store and no memory layer at all beat the marketed ones.
* **Not** claim a number we did not run, on a set we cannot name. Three vendors,
  three numbers, one benchmark name — that is the failure mode this repo exists
  to avoid.

## 7. Non-claims

Every frontier figure in this plan is quoted from a dated board or paper, none
was produced here. Our own numbers are the ones already receipted in this tree:
0/51 claimable on SWE-bench Pro V2, 2/89 and 5/30 blind repair, 0.2581 ms law
match at 10 laws vs 0.2687 ms at 500, 6/6 law recurrence, 3.7 % edit recurrence,
50 % selection precision, 2000/2000 SACCR, two CI-verified admissions. Sandbox
measurement only; authority NONE.

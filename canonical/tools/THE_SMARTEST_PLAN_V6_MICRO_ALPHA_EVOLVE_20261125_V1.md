# The smartest plan v6: we already run a zero-LLM micro-AlphaEvolve inside the planner

**Date:** 2026-11-25. **Authority:** NONE (producer-run sandbox).
Supersedes v5. This round's searches (web + repo, both under unfamiliar names) converge on one
finding: the frontier's most-celebrated architecture — AlphaEvolve — is *my plan v5 loop,
implemented with an LLM in the candidate-generator seat*. Under Elon's law the LLM is the part to
delete, and deleting it was already executed last round (`7c91733f`). Every number below verified
today or marked.

---

## §0 What the web said this round (and why it lands on us)

- **AlphaEvolve** (DeepMind): "Because every candidate program is graded by an automatic evaluator
  rather than trusted on the LLM's word, the system can run autonomously for long stretches."
  FunSearch line in the same doc: **"small LLMs used; no benefit from larger."** Millions of LLM
  samples for FunSearch, thousands for AlphaEvolve — all of them to *propose candidates* that a
  verifier then judges.
- **OpenEvolve / CodeEvolve** (open-source reimplementations): the four core modules are LLM
  sampler, cascade evaluator, MAP-Elites archive, evolution controller. Ablation (jjakimoto
  #1483): **"No evolution → worst performance; proves evolution is the core driving mechanism."**
- **EvoX** (arXiv 2602.23413): *meta*-evolution — "jointly evolves candidate solutions and the
  search strategies used to generate them" — beats AlphaEvolve/OpenEvolve/GEPA on ~200 tasks
  within 100 iterations. The lesson: adapting the SEARCH beats scaling the GENERATOR.
- Small-model agent results (Works With Agents, May 2026): SmolLM3 3B beats Claude Sonnet 4 and
  GPT-5 on agentic coding — **"size isn't the bottleneck — execution logic is"**; benchmarks now
  weight efficiency 30%.

## §1 The repo-side finding: the map is already drawn, under these names

| AlphaEvolve/OpenEvolve module | ours | measured today |
|---|---|---|
| LLM candidate sampler | **OE enumeration + stochastic search union** (`stochastic_synthesizer_v1`, the planner's H2 affordance) | 1.69–191 ms, 0 LLM samples, 0 tokens |
| cascade evaluator | examples-verification at generation (verify-at-generation) → `unittest discover` in-loop → post-edit verify affordance | three-stage, all automatic |
| MAP-Elites archive | **`CompoundingConceptLibrary`** — sleep-abstraction of verified programs into concepts that widen the grammar | G_0: 138 ms miss → G_1: 65 ms hit |
| evolution controller (search adapts) | planner MCTS with **online-learned** pass probabilities/effects (`EpistemicSelfBeliefEngine`, `CausalWorldGraph` settle on actual outcomes) | EvoX's lever, zero-LLM |
| whole-file diff evolution | H1 AST single-op patcher + H2 function-body rewrite (in-source replace) | 861 ms end-to-end DONE |

The FunSearch ablation ("no evolution = worst") has its exact mirror in OUR measured result: the
observational synthesizer WITHOUT archived concepts **misses at every budget 4–8** (10/10 configs);
WITH 2 archived concepts it hits in 65 ms. That is the headline AlphaEvolve finding, reproduced in
130 lines of test.

**Plan v5 moves, closed:**
- **Move 2 — DONE** (wired; end-to-end proof `test_plan_v5_ensemble_affordance_v1.py`, 3 passed).
- **Move 1 — FALSIFIED BY EXISTENCE.** `creature_runtime_v1.py:1077` already binds
  `model_v1.bind(SOVEREIGN_ZERO_LLM_MODEL_SPEC)` — the explicit bind at the loop, exactly where it
  belongs. `model_v1.bind` *refuses* to fall back to a default by design ("a binding that silently
  fails is indistinguishable from one that worked and returned nothing"). A default binding at the
  socket is the part the design rejects; the plan was wrong and nothing was changed. **Best part is
  no part — this part was already deliberately absent.**
- Related honest finding: affordance 7 (`unified_model_solve`) cannot run in the confined carrier —
  its rendered program inserts the repo root into sys.path, but inside the CoW sandbox (`/work/
  program.py`) the root doesn't exist (observed `ModuleNotFoundError: canonical`, live trace).
  This is the repo's own documented confinement blocker manifesting inside the loop, not a wiring
  bug to paper over. Flagged, NOT worked around.

## §2 The unusual ideas (this round, all cheap)

1. **Say the sentence and make it true: "micro-AlphaEvolve, zero LLM samples, 861 ms per
   patched-and-verified task."** Every piece exists (table §1). The only new work is an
   instrumented benchmark: run the loop over a family of H2-shaped repair tasks and report
   (solved, ms, tokens=0) next to OpenEvolve-style cost (LLM samples). No new part; a measuring
   part. This is what "ahead of the frontier" would look like as a *number*: equal verifier-
   grounded search, ~100–1000× less cost per step, on the task family where the grammars reach.
2. **Archive pressure = the next lever, and it is a deletion.** EvoX adapts search from progress.
   Our concept library only grows; AlphaEvolve's archive *resurfaces promising* programs, but the
   frontier pays storage/eval for breadth we don't need. Cheapest EvoX-flavored move: after N
   misses at budget w, *retry at w+1 only for shapes whose held-out verify is cheap*; after
   concepts stop earning hits, expire them (`rule_expiry_v1` already exists for exactly this —
   hidden under a memory-governance name). Both are ~10-line planner-adjacent edits, gate:
   never slower than today's fixed w=4 on the hit path.
3. **Do the benchmark WITHOUT external data.** Plan v2/v3 blocked on HuggingFace corpora. The
   task family generator is already in-repo: `extract_io_examples_from_test_source` consumes
   test sources we can *synthesize ourselves* (random small programs → render tests → break the
   impl → solve → verify). Self-generated corpora dodge the download wall entirely — 0 parts
   added, and honest only if we report it as constructed-stream scoring (AgentCL's "dependent
   stream" language fits exactly).

## §3 Falsifiers

1. If the self-generated repair family saturates at ~100% for the loop AND for a
   "always-return-first-candidate" baseline, the benchmark measures nothing; raise task depth
   until the baseline breaks, else drop idea 1.
2. If budget-escalation (idea 2) slows the hit path by >2× (gate inherited from v5 §4#3), revert.
3. If concept expiry evicts a concept that later streams needed, negative transfer reappears —
   require the expiry decision to be evidence-scored (crystallizer already tracks hits).
4. If affordance 7's confinement failure turns out to block the loop from ever *using*
   unified-model capabilities outside tests, record the loop as synthesis-driven only (no
   over-claim), and leave the confinement seam to its owner docs (`CONFINEMENT_FRONT_DOOR_*`).

## §4 Rejected

Default model binding at the socket (v5 move 1 — design refuses it, confirmed by reading bind());
promoting the angelic monolith (v4 stands); anything LLM-in-the-generator when enumeration+verify
is 300–1000× cheaper; external-corpus download paths (blocked before, unnecessary now — §2.3).

## §5 Bottom line

The frontier's answer to "how do we get reliable code" (AlphaEvolve: generate cheap, verify
everything, archive what wins, let the search adapt) has been reinvented here in reverse-cost
order: we verify everything, enumerate the candidates exhaustively, compound concepts as the
archive, and use no LLM at all — measured 65–861 ms per verified patch. Plan v5's move 1 died
honestly (it already existed); the wire is bound. The remaining smart-unusual move is a
**self-generated benchmark that prices our loop against OpenEvolve-style LLM sampling in ms,
tokens, and solved-count** — no new parts, one measuring stick. §3 not met until that number
exists.

## §6 Smoke benchmark executed (same day) — the number exists

10 self-generated 1-var repair tasks (random `rng=65`; tests rendered from the program, impl
broken to `return 0`), full live loop (`model_v1.bind` → `solve_v1.solve`, steps=6, learn=False),
independently re-verified by a fresh-process `unittest discover`:

**solved 4/10 · mean 954 ms/task · 0 LLM samples · 0 tokens.**

Readings:
- Falsifier #1 does NOT fire: the family is not saturated (4/10), so it measures reach.
- The 4 hits include all three conditional shapes the union fallback exists for — the merge from
  v5 §7 is load-bearing at loop level, not just unit level.
- Misses cluster on (a) nested conditionals `(x±b)*a` (outside OE-grammar weight at the fixed
  budget), (b) `abs(x)*a - b`, (c) ONE variance: the same expression `x*3+3` hit at task 2 and
  missed at task 8 — different sampled points, so the knob is example-underdetermination or the
  steps=6 budget, not the grammar. Not yet chased; recorded.
- Cost line vs the frontier frame: OpenEvolve-style pipelines need thousands of LLM samples per
  discovery run; this full search-patch-verify loop costs 0 samples and ~1 s wall per task.

Next knobs (each with a falsifier of its own before adoption): steps 6→10 escalation on miss;
max_weight 4→5 only when H2+union both miss (v6 §2.2 archive-pressure idea); more example points
from the test generator. Until then, 4/10 @ 954 ms / 0 tokens is the measured reach of the
micro-AlphaEvolve loop on its home family.

## §7 The three knobs, executed and adjudicated (`go` round)

Bench lives at `canonical/tools/micro_evolve_bench_v1.py` (fixed seed 65, fresh-process
independent re-verification, JSON out). Baseline reproduces: 4/10 @ 916 ms.

| knob | hypothesis | result | verdict |
|---|---|---|---|
| steps 6→10 | misses are horizon misses | 4/10 @ 890 ms — no change | **FALSIFIED.** The misses are reach, not patience |
| points 6→8 | example-underdetermination | 5/10 | **rejected as adoption** — more visible tests makes the TASK easier (benchmark difficulty tuning, not a production knob); recorded as a finding |
| max_weight 4→6 escalation | deeper OBS grammar covers the class | None at w=4,5,6 for all miss-shapes | **FALSIFIED**, and it redirected to the true root cause |

### Root cause found (the interesting part)
Same-expression hit/miss variance was a red herring: BOTH point sets uniquely determine `x*3+3`
— yet OE returns **0 candidates for it at any point set**: the promoted OE enumeration composes
binary ops only at Level 2 (Level 3 is ITE-only), so `((x*3)+3)` was reachable by NEITHER engine.
Debug trail kept: first escalation attempt (more random tries, seed+1) is luck and still missed
(~1/30k sampled hit rate); replaced by **deterministic class completion**: `_level2c_exhaustive`
enumerates `((x|neg x|abs x) ∘ c) ∘ c`, signature-deduped OE-style — 12 ms for the whole class.
Two wrapper bugs found and fixed en route (escalation keyed on EMPTY UNION instead of NO
SHIPPABLE CANDIDATE; `lang=lang` NameError swallowed by its own except — proof that
broad excepts deserve witnesses). Constants pool widened to include env values (4 was sliced out).
`*` added to the stochastic binary ops (one tuple; OE-evaluable, emit-safe).

### Result
**4/10 → 7/10 solved, same family, same steps=6, same 6 points, mean 946 ms unchanged
(miss-path-only work), 0 LLM samples, 0 tokens.** All 9 synthesizer/planner tests pass.

Remaining 3/10 are all the ITE-with-deep-branches class (`(x±b)*a if…else…`): needs 2c-sized
bodies UNDER both ITE branches — touches the promoted OE module's Level-3 composition. NOT
done this round (scope discipline); recorded as the next known lever with its own gate.

## §8 The last class closed — ITE over the 2c pool (next "go" round)

Web + repo converged on the same pattern under three names: Alur's TACAS'17
"divide and conquer" (terms grammar × conditionals grammar combined by ITE),
the EUSolver pattern already INSIDE the promoted OE module at its Level 3 —
and the reason the class was missed: Level 3 composes only OE's DEPTH-2 pool.
The fix stayed inside `stochastic_synthesizer_v1` (the OE module untouched):
the 2c enumeration now also fills a signature-deduped pool, and the same
coverage+separating-guard composition runs on the DEEPER pool. ~40 lines.

Measured, same fixed family (seed 65, steps=6, points=6): **7/10 → 10/10 @ 927 ms,
0 LLM samples, 0 tokens**; nested-conditional unit examples recover the exact
program and generalize over ±16 points. Saturated families are worthless as
evidence (own falsifier #1 inverted), so the verdict number is on THREE untuned
seeds (99, 7, 2026): **29/30 (96.7%) @ ~890 ms mean.**

The single residual miss (`x if x > 3 else 4` — a shape solved on other seeds) is
a branch-pairing cap (parts[:6] in the composition), not a grammar gap; recorded,
not chased. Two knobs of the class remain in principle (pool cap, guard
max_results) — each needs its own falsifier before adoption, per house law.

Web corroboration this round (direct, fresh): "Can LLMs Perform Synthesis?"
(arXiv 2603.20264, 2026) compares LLM toolchains against Cataclyst-style
enumerative CEGIS and finds enumerative engines NEVER repeat a candidate while
LLM toolchains "often repeat the same incorrect proposal many times" — the
sampling tax the frontier pays is measured, not asserted. Our position inherits
it: OE enumeration + stochastic fill-in + exhaustive 2c completion is one
gradient-free, zero-token ladder over the same space.

**Frontier-relative claim, bounded:** on this home family the loop fixes ~97% of
broken functions at ~0.9 s and zero LLM calls per verified patch. The family is
1-var conditional/arithmetic programs, self-generated, verifier = visible tests;
this is NOT SWE-bench, NOT GUI, NOT long-horizon. Reach on certified HARD-51:
still 0 — unchanged by everything above; the axis improved is candidate reach
per millisecond, which is what the loop actually gates on.

## §9 The residual miss was a verifier LIE — pyc staleness (next "go" round)

Seed-99's `x if x > 3 else 4` did not resist synthesis: every layer solved it
(OBS body, `return 4` fallback, both assert orders). The loop kept FAILING a
correct file because **CPython's pyc invalidation keys on (mtime-seconds, size)
— `return 4` over `return 0` is the same 19 bytes in the same second**, so the
test ran the PREVIOUS bytecode and reported `0 != 4` about code no longer on
disk. `unittest` re-run on the correct file failed the same way; the kernel
output was a lie about kernel truth. Same-size patches are the MOST COMMON
mutation class (every operator swap), so this poisoned exactly the fast in-place
write+verify rhythm the loop is built on.

The repo already knew: FIVE bound_capabilities runners set
`PYTHONDONTWRITEBYTECODE=1`; the probe even measures the venv-python mount bug
around the launcher. What nobody had done was apply it to the LOOP:
- `solve_v1.act()` host-fallback: env added.
- All three planner renderers (H1 AST patch, H2 synth patch, verify_
  postconditions): clear stale `__pycache__/*.pyc` once at program start (covers
  pyc predating any fix, e.g. written by the probe step) and run unittest with
  writes disabled — inside the RENDERED programs, so it holds under BOTH carriers
  (the confined launcher takes no env, and confine_v1 is a security module not
  to be touched for this).

Verdict after fix, four seeds x 10 tasks, bench re-verify hardened identically:
**40/40 (seeds 65/99/7/2026), mean ~920 ms, 0 LLM samples, 0 tokens.** The
parts[:6] cap was NOT the culprit and stays as-is (falsifier #2-style honesty:
the recorded "next lever" was wrong; the trace said so).

Tests: 9/9 synth+e2e, 9/9 loop suites, planner suite = identical 3 pre-existing
failures (stash-verified baseline), 59 passed + 927 subtests.

Lesson, repo-wide: any harness that runs code it just wrote must treat bytecode
cache as adversarial state. A verifier's word is only as good as its freshest
read; "insanely fast" loops that re-read through a stale cache are not fast,
they are wrong at high speed.

## §10 A yardstick that bites again: the 2-var family (this round)

A saturated family measures nothing, so `micro_evolve_bench_v1.py` gained
`--two-var` (same generator discipline: fixed seeds, fresh-process re-verify):
cross-variable programs — `x*y+a`, `(x+c)*(y+c')`, `abs(x-y)*a`, compound
conditionals. First blood: **7/10**, the loop's honest failure profile.

Root causes found and fixed same round, all in `stochastic_synthesizer_v1`
(the OE module still untouched):
1. The 2c base atoms were single-var; added PAIRED cross atoms (x±y, x*y,
   neg/abs over them) → `abs(x-y)*4`-class recovered.
2. `(x+4)*(y-3)` needs TERM x TERM. Measured the feared blowup: after
   signature-dedup the full product was 72 atoms -> 5184 pairs -> **19 ms**.
   Added the product behind a |inner|<=256 cap: exceeding it forfeits the
   extra class, never correctness (soundness by construction — every
   candidate is still verified on all examples).

Family verdict after fixes: **2-var 26/30 (9/9/8 on seeds 65/99/2026),
mean ~1030 ms, 0 LLM samples, 0 tokens**; 1-var still 10/10 (no regression);
9/9 unit+e2e tests pass.

The frontier is now named, not guessed: the residual misses are (a) compound
conditionals needing product-sized atoms UNDER both ITE branches and (b) the
same 2c class at |inner|>256 (2-var consts widen the pool past the cap).
Candidate levers, each behind its own gate, measured NOT yet adopted: coverage-
ordered branch pairing over the product-augmented pool; MUL-only product with
cap 1024 (measured cost estimate 2-5 s on the miss path — over the loop's
~1 s budget, so the gate is: only if a solved-task counts >=2 improvement at
<=2.5 s mean miss-path cost).

External context this round (the axis we are on, corroborated):
- The stale-world-model literature names our pyc bug's genus: agents decide on
  outdated state, failures "quiet, irreversible, compounding"; "no framework
  solves it automatically" (tianpan.co, 2026-04). Our fix is one concrete
  freshness guarantee in the verifier path.
- SlopCodeBench (arXiv 2603.24755): no agent solves iterative tasks end-to-end
  across 11 models; pass-rate benchmarks miss structural decay; prompt fixes
  shift intercept, not slope. Read as: verification-coupled loops (ours) over
  bigger generators (theirs) on horizons where the generator degrades.
- Compounding math (85%/step -> 20% at 10 steps) is the argument for the only
  remaining big axis: per-step reliability of the JUDGE, not the generator —
  our judge is a unittest run, which cannot drift. The pyc incident was the
  judge being wrong for a mechanical reason; now fixed at all three carriers.
- Edinburgh synthesis work: LLM outputs mined as heuristics for enumerative
  search hit 80.1% on SyGuS — recorded as REJECTED-shape for this repo (it
  re-introduces the sampling tax); our deterministic pool completions are the
  zero-sample version of "search the neighborhood".

Reach on certified HARD-51: still 0 (unchanged all session; different problem
class, honestly tracked).

## §11 The two §10 levers, adjudicated (this "go")

> RESIDUAL-LEVER STATUS (updated in §13): the "one more inverse-composition
> pass" recorded below is DONE — branch-restricted, 2-var family now saturated.

Both levers were one mechanism. A naive term x term scan at real loop sizes
measured 429 atoms / 5.3 s — OVER the 2.5 s miss-path gate, so the cap-1024
plan was rejected in favor of the algebra: for `*`, `+`, `-` the second
operand's value vector is DETERMINED pointwise by target and first operand, so
composition is O(atoms x points) dict lookups — ~30 ms at the same 429-atom
size, no cap compromise. Composite atoms join the pool, so the existing
coverage+guard ITE stage gets product/sum BRANCHES for free (lever 2 folded
into lever 1 rather than built twice). Zero-divisor slots skipped: rare, and
sound — nothing is ever emitted unverified against every example.

Gate (from §10): ">=2 solved-task improvement at <=2.5 s mean miss-path
cost." Result: 2-var family **26/30 -> 28/30** (10/9/9 on seeds 65/99/2026),
mean ~1030 ms. **Gate met; adopted.** 1-var family 10/10 (no regression);
9/9 unit+e2e tests pass.

Honesty notes: (1) seed-65's compound-conditional now passes on a program that
fits the 6 visible points but is NOT the generating function — correct
behavior for a spec-verifier (the test is the ground truth of the loop),
flagged because "solved" here means *spec-consistent*, not *target-identical*.
(2) The two residual misses are the same compound shape at other point sets;
next lever is one more inverse-composition pass over (atom, guard-pair)
branches; recorded, gated like all the others.

Cumulative loop ledger on self-generated families: 1-var 40/40 @ ~920 ms;
2-var 28/30 @ ~1030 ms; 0 LLM samples, 0 tokens, whole session. Certified
HARD-51 reach: 0 — unchanged, different problem class, still the binding
number for anything claiming SWE-frontier parity.

## §12 "At the unified model", made literal (this round)

The registry already HAD the door: `engine:REPAIR_SYNTHESIS` routes, via the
cognitive fabric's front `run()`, to `live_brain_runtime_v1.
synthesize_failure_repair`. What it did not have was our loop behind it — the
function only spoke R3-fingerprint. Move: an additive examples-fallback —
when a request carries `arg_names` + `(args, expected)` examples and no
fingerprint, answer from the verified ensemble (`synthesize_body_from_examples`).
Fingerprint-shaped requests keep the old path byte-for-byte.

Measured through the front door, not the function:
`fabric.run({"mode":"REPAIR_SYNTHESIS","payload":{...6 points...}})` ->
`inner_pass: true`, body `return ((x * 3) if (x >= 0) else ((x + 1) * 3))`,
**334 ms, 0 LLM samples**, with the honesty fields in the payload itself
(`authority: NONE`, `non_claim: "spec-consistent, not target-identical"`).

Carrier files are content-addressed, so the registry was RECOMPILED through
the repo's own compiler (`compile_brain_unified_model_v1.py`) rather than
hand-edited. Side result: the three long-standing "stale artifact" failures
(partition exactness, compile determinism, fixed point) — failing since the
sandbox checkout was made — **now pass: 62/62 + 927 subtests**, because the
committed artifact finally matches the compiled one. Source index grew
2237 -> 2239 modules (this session's new files), routing tokens 1729 -> 2373.

Frontier context this round (fresh): Cognition's **SWE-2.1 released 2026-11-24**
roughly DOUBLED its benchmarks (Terminal-Bench 4.1 24.2->50.0) via pure RL on
Kimi K3 — the frontier is spending gradient compute on exactly the reliability
axis our zero-token loop addresses at the spec-verified seam; Opus 5.5 holds
SWE-bench Pro 89.9 / TB 2.1 87.6. We do not chase those numbers; the ledger
stays: engines reachable FROM the unified model's own front door, priced in ms
and tokens, HARD-51 reach still 0 and stated as the gap.

## §13 Branch-restricted composition: the class closes, and the yardstick hits its ceiling (this "go")

§11/§12 left one shape unsolved: a compound conditional whose ELSE branch is
only required to be right on the points where it RUNS. A global inversion
(look up `target - a` over ALL example points) can never find `-(x*3)-y`,
because that branch is irrelevantly wrong on the then-side. That is not a
reach limit, it is a scope error in my own indexing.

Mechanism, in one splice inside the ITE stage of `_level2c_exhaustive`: project
the target and every atom's value vector onto the REMAINDER index set (the
points the then-branch does not cover), index atoms by that projected tuple,
and solve the three slot equations there (`b = t-a`, `b = a-t`, `b = t/a` with
an exact-divisibility guard). Value-vector construction was hoisted into
`_atom_vals()` so both passes share one build — the restricted pass costs extra
hash lookups, not extra evaluation. Soundness is untouched: the composed ITE
still has to match EVERY example in the final `_sig` check, so a branch that is
wrong outside its own region is harmless and a candidate is never emitted
unverified.

Gate (same shape as §11: improve the family, stay under ~2.5 s mean miss-path
cost). Result: **2-var 28/30 -> 30/30** (10/10/10 on seeds 65/99/2026) at
1065 / 1098 / 1010 ms. The six previously-missing rows now resolve in 180-949
ms each, e.g. seed 99 `(x*3+y) if (x+y)>=1 else -(x*3)-y` ->
`(9 - abs(y)) if ((x < -1) or (x > 1)) else ((abs(y) * -2) + ((x + y) * 3))`,
and seed 2026 `(x*2+y) if (x+y)>=1 else -(x*2)-y` -> `(y + 6) - (abs(y) * 2)`
(the latter is x-free — all its sampled points sit on a line where x is
determined by y, which is the §13 ceiling showing up before the grid does).
Anti-overfit check on two seeds never used for tuning (7, 1234): **10/10 and
10/10** at 915 / 879 ms — 50/50 across five seeds, so this is class coverage,
not seed luck. 1-var family 10/10 @ 916 ms (no regression); 10/10 synthesizer +
OE + ensemble tests; 9/9 loop suites (`solve` ends-what-a-project-test-started,
transfer probe). **Gate met; adopted.** The mechanism ships with a red/green
falsifier, not just a number:
`test_branch_restricted_composition_closes_compound_conditional` pins the two
recorded specs, FAILS (`found nothing`) against the pre-§13 module and PASSES
with it — `git stash` proved both directions in one run.

The number is the less interesting result. Measuring what the loop SHIPS
against a 231-point grid (`x in [-5,5], y in [-11,11]`) instead of its own 6
visible points: **6/10 generalize on seeds 65/99/2026, 4/10 on seed 7.** For
every non-generalizing row, the ENTIRE verified candidate set for that spec
contains no target-equivalent program — e.g. for `x if x > y+4 else y*2` all
six sampled points land in the else branch, so `y + y` is a perfectly correct
answer to the question that was actually asked. So this is NOT a selection bug
(shortest-first is not discarding a better candidate) and NOT a reach bug (the
class is now saturated); it is the information content of the spec.
`points=6` over a 49-point domain cannot pin a two-variable guarded program.
Raising `points` would move the generalization number by making the benchmark
easier to pin, which is difficulty tuning, not capability — refused, same rule
that killed move 1 and the `parts[:6]` hypothesis. The lever that would genuinely
buy something is a stronger SPEC, and the loop has no oracle beyond the tests
it is given: candidate-distinguishing queries (CEGIS-style) need a teacher.

Practical reading for the repo: on this axis the remaining error budget is owned
by whoever writes the test file, not by the search. In the real setting the spec
is a whole test module, so the ceiling here is an artifact of the micro-family.

Ritual, paid for immediately: `stochastic_synthesizer_v1` is a COMPILED runtime
module, so editing it without re-emitting `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json`
turns `test_compilation_is_deterministic` and `test_the_compile_is_a_fixed_point`
red. That is the §12 carrier test doing exactly what a tripwire is for; the fix
is one command (`python canonical/runtime/compile_brain_unified_model_v1.py`,
62/62 + 927 subtests green afterwards), never a hand-edit of the artifact.

Ledger after §13 — 1-var 40/40 @ ~920 ms; 2-var 50/50 @ ~1000 ms; 0 LLM samples
and 0 tokens for the entire session; certified HARD-51 reach still 0/51, and
still the binding number for any frontier claim. "Solved" in this section means
*spec-consistent*, which is exactly what a verifier-gated loop can promise.

External corroboration this round: eUSolver (Alur et al., TACAS'17) prescribes exactly
this separation — enumerate value terms, enumerate predicates, combine by ITE —
and warns enumerative solvers degrade "drastically with the size of the smallest
solution"; the fix there is decomposition, here it was scoping the inversion to
the branch. SlopCodeBench (2603.24755) reports pass-rate benchmarks hiding
structural decay; the 6/10-vs-30/30 split above is the same trap one level down,
which is why the generalization grid is now part of how this family is read.

## §14 The loop learns to read its own learned grammar (this "go")

HARD-51 first, because it keeps being quoted as the gap and it is not what it
looks like: `canonical/tools/pro_hard51_preflight_v1.py` says `Read-only ...
NEVER runs tasks`, and its own docstring pins an upstream checksum manifest. So
`0/51` is a **certification and data wall, not a search result** — no splice in
this repo changes it, and I stopped treating it as a capability number
(external: the Hard split spans 52.9-98.0% across frontier systems, Opus 5
(xhigh) failing 4 tasks; SWE-2 Flash 89.9%, and Flint 89.7% on full v2 with
~2.5B active parameters. None of that is reachable from a zero-token loop that
is not authorized to run the tasks.)

The round therefore went after the thing the session keeps finding: an organ
that already exists, wired to the wrong doors. `K3` here is
`canonical/swe_kernel/concept_library_v1.py` — a 122 KB **CompoundingConceptLibrary**:
anti-unification over solved programs, admission only if the concept compresses
executable description length AND evaluates deterministically on probes AND
kills a syntactic mutant, Levin/Laplace log-priors, per-concept contribution
stats (`uses`, `verified_hits`, `disconfirmations`, `retired`), persistence
gated by `memory_policy_v1`. Its docstring states its purpose: close "the
frozen-hypothesis-space limitation (`G_0 = const`)". The SWE-side observational
synthesizer already consults it; **the ensemble fallback this session has been
tuned for six rounds did not** — it re-derived a hand-written atom grammar and
ignored everything the repo had learned.

Move, entirely read-side: `numeric_concept_templates(library)` (first-order,
live, numeric entries only) feeding a new `concepts=` argument through
`synthesize_body_from_examples` into `_level2c_exhaustive`, where each concept
is instantiated as a TEMPLATE — hole filled with a variable or with any atom the
enumerator already produced, plus literal-lifted variants and the min/max dual.
Wired at the unified model's own affordance call site, so it is the *loop* that
reads the library, not just the function.

Measured (synthesizer level, 6-point specs, ±16 grid for generalization):

| arm | clamp family spec-pass | clamp generalizes | cost/call |
|---|---|---|---|
| hand-written grammar only | 4/10 | 1/10 | 294 ms |
| + learned templates | **7/10** | **2/10** | 303 ms |
| 1-var family (regression) | 10/10 both | 6/10 both | 258 → 254 ms |
| 2-var family (regression) | 10/10 both | 6/10 both | 492 → 511 ms |

`min`/`max` are not atoms in the micro grammar at ANY depth, so the 3 rows this
recovered are not "found faster" — they are **unreachable before, reachable
now**. The falsifier is the cleanest kind: on the clamp row at seed 65 the
fallback returns `None` without the wiring and `return min(max(2 * (x), 0), 100)`
— the generating function itself — with it, verified on all 33 grid points.
`test_learned_grammar_read_path_v1.py` pins exactly that pair against a stub
library, so it cannot drift with the real one's contents.

Two findings that cut against me, recorded rather than smoothed over:

1. **The end-to-end number did not move: clamp family 7/10 before, 7/10 after**
   (847-927 ms). The primary path already consults the library — it emits
   `def concept_f1f3674d(_v0): return min(max(2 * _v0, 0), 100)` and calls it —
   so on this family the fallback rarely gets control. Verdict: the §14 gate
   ("extend end-to-end reach") is **NOT met**; the splice is kept because it
   costs 0 ms where it is not needed and turns a hard `None` into a correct
   program where it is, but no end-to-end claim is being made. Arm C — consult
   the deep pass even when a candidate already verified, to displace overfits —
   was implemented, measured at +150-330 ms and worse results, and **refused**.
2. **Dreaming on the repo's own source does not pay for this grammar.** Running
   the organ over 116 runtime modules (970 KB) took 84.5 s and admitted 4 real
   concepts (`len(_v0) != len(set(_v0))` from 9 sites; a whitespace normalizer
   from 6). Handing that library to the observational synthesizer on 9
   string-shaped specs changed nothing: 6/9 and 3/9 in both arms. Its concept
   instantiation is numeric-shaped, so a string template is admitted, persisted,
   and then never applied. The write path also refuses to fire at micro sizes:
   `sleep_abstract` admitted 0 of 3-5 solved loop programs even at `min_nodes=2`
   — which is what LILO reports as *correct* early-learning behavior ("the
   actual library size can be smaller than iterations ... avoids introducing
   abstractions that have no utility"), not a bug to chase.

What the round actually taught me about my own code: **the tiebreak was throwing
away the win.** `_scan` selects the shortest verified candidate, and a concept
instance is longer than the ad-hoc ITE that overfits the visible points, so
ranking by length silently discarded the learned abstraction — generalization
1/10. Candidates now carry a grammar-aware `rank` (naming a library concept
costs a node, not its body) and the tiebreak uses it; that is the difference
between paying for a learned grammar and using it. Related trap, also measured:
truncating the instantiated candidates to `max_results` lost solves (7/10 ->
5/10) by starving the good ones — the verifier selects, the enumerator should not.

Hygiene, found by accident and worth more than the feature: after one 10-task
family run, `git status` showed the **committed** learning-state file modified —
`"uses": 0 -> 2`. The loop persists learning state while benchmarking, and
`solve(learn=False)` does not cover it (the synthesizer credits concept use on
the ambient memory policy). A yardstick that mutates the system it measures is
not a yardstick; the bench now runs inside the already-existing
`memory_policy_scope(READ_ONLY)` and the file stays pristine through a full run.
The module itself documents the same genus one level up: `record_concept_outcome`
notes the synthesizer "was previously mislabelling" use as a verified hit, so a
concept used only inside WRONG bodies raised its own prior. Self-crediting
learning is the same failure as a stale-bytecode verifier, wearing a different
name — which is why the external literature's fix (Library Drift, Zhang 2026:
contribution logs, outcome-based retirement, active-library cap) is already
sitting in this file's dataclass.

Frontier context for the axis, from this round's search: CODESKILL (2605.25430)
trains an RL policy for skill extraction/bank maintenance and reports +11.03
points over a no-skill baseline while keeping the bank compact; SAGE (ACL 2026)
gets +8.9% scenario completion with 26% fewer steps and 59% fewer tokens by
accumulating skills across a task chain; Anthropic's "dreaming" and Letta's
sleep-time compute are the productized form of the same offline pass (~5x less
test-time compute reported). SkillLearnBench and ContinualSkillBench are the
counterweight: skill gains are inconsistent across tasks and models, and
unconditional accumulation can degrade performance — a positive average often
hides a narrow set of gains. Our version of that lesson is already structural:
admission requires compression plus mutant-killing, and retirement is an entry
field, so the loop cannot inflate its own grammar with junk. What we do NOT have
is the RL half — and per the standing rule, we do not buy it with samples.

Ledger after §14: 1-var 40/40 @ ~920 ms; 2-var 50/50 @ ~1000 ms; clamp family
7/10 loop-level (fallback 4/10 -> 7/10 at unit level); 27 unit/e2e tests green,
planner suite 62/62 + 927 subtests, carrier recompiled through the repo's own
compiler; integrity guard clean; 0 LLM samples and 0 tokens for the entire
session; certified HARD-51 reach 0/51, now explicitly labelled a policy wall
rather than a capability claim.

---

## §15 — Merging main: what the repo's own gates actually require (2026-11-26)

The merge itself was one conflict. `git merge-tree` said so before I touched
anything: `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` only, because
main carries 1,566 commits on that generated carrier since the base. A conflict
in compiled output is not hand-merged — it is regenerated with
`canonical/runtime/compile_brain_unified_model_v1.py`, and
`test_brain_unified_model_v1.py::test_compilation_is_a_fixed_point` is the
check that proves nobody faked it.

The expensive part was not git. Four CI gates (`guard`, `verify` x3, `verify-r3`,
`Load-bearing primary admission`) went red on the merged head, and PR #7119 had
zero failing checks, so red meant *mine* until proven otherwise. Two lessons,
both cheaper to write down than to re-learn:

1. **Any branch that touches a compiled module owes an action intent.**
   `enforce_load_bearing_primary_pr.py` demands *exactly one*
   `canonical/action_intents/*.json` added by the PR diff, and
   `enforce_goal_hierarchy.py` demands the full 18-key `recursive_obs` receipt
   (canonical 8-step deletion order, per-layer required keys,
   `expected_parent_level_state_change` byte-equal to
   `expected_parent_frontier_change`) plus the v22 preflight/tournament block.
   Don't hand-write it blind: `canonical/tools/rebind_intent_and_verify_gates_v1.py`
   runs rebind -> recompile -> all four gates in the one order that works, and
   `intent_added_by_this_branch` explains why rebinding an already-merged intent
   fails both referees at once (`MULTIPLE_ACTION_INTENTS_IN_ONE_PR`).
2. **The base is `origin/main`'s tip, not the merge base.** The drift guard
   compares `recursive_obs.canonical_base_commit` against
   `github.event.pull_request.base.sha`. On a repo moving 23,992 commits per
   merge window, a local rebind to `git merge-base` passes at home and fails in
   CI every single time.

Honest accounting of the four reds after the fixes: `admission`, `integrity` and
`unified_model` (38/38) pass locally, and `guard` passes once the receipt is
complete. The remaining red — the R1 architecture-closure `verify` job and the
two fabric modules in `verify-r3` — is **main's, not this branch's**, proven by
re-running the identical commands in a clean `git worktree` of `origin/main`
(`git worktree add /tmp/mainwt2 origin/main`): same 5 `*_BLOB_DRIFT` codes,
same 3 failures. Fabric pins drift because governance and runtime move at
different speeds; this branch touches neither fabric nor its pins, so it does
not fix them and does not claim to.

No capability claim in this section: it is plumbing that made the shipped §7-§14
work mergeable, and the loop's numbers are unchanged by it.

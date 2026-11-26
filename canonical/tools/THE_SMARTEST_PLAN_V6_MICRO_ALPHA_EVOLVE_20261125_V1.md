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

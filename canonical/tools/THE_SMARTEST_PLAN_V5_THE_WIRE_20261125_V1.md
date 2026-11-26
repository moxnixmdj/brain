# The smartest plan v5: the parts exist, the socket exists — bind the wire

**Date:** 2026-11-25. **Authority:** NONE (producer-run sandbox).
Supersedes v4. Elon's law applies to plans too: v1-v4 *built* parts; the measurements below say the
winning move **adds no part at all**. Every number verified today or marked otherwise.

---

## §0 The finding that rewrites the plan

I went looking for hidden capabilities to wire up and found the repo's real spine under
non-obvious names — and it is **already wired**:

| hidden under the name | what it actually is | wiring status |
|---|---|---|
| `solve_v1.py` (618 L) | "The whole system, reduced to what cannot be removed": observe → model → act → diff. Zero domain knowledge. Speed as design constraint ("the world is diffed rather than rebuilt") | the loop |
| `model_v1.py` (158 L) | "The socket the brain plugs into": `model(goal, seeing) -> program | None`, bound by env `BRAIN_MODEL` | the socket |
| `SovereignZeroLLMPlanner` (in `brain_unified_model_v1`) | Active inference + MCTS + epistemic self-belief + **concept compounding**; its docstring says "Zero-LLM agent **for `solve_v1`**" | the model |
| `swe_observational_program_synthesizer_v1` (1,857 L) | enumerate-and-verify function-body synthesis | **26 importers** |
| `concept_library_v1.CompoundingConceptLibrary` (2,702 L) | sleep-time abstraction: verified programs → reusable concepts (G_0 → G_1) that widen synthesis | **28 importers** |
| `model_v1` | the socket | **80 importers** |

The claim "we have tremendous hidden capabilities under non-obvious names" is **true, and better
than claimed**: they are not scattered — they form one chain (loop ← socket ← planner ←
synthesizer ← concept memory) that is already connected end-to-end. `test_sentient_cognitive_core_v1`
proves the whole chain today: bind → conformance ok → `solve("write 42 to answer.txt")` → **DONE**,
20 tests passing in this sandbox.

## §1 Measured today: compounding is instant learning, and it is fast

Same task (clamped percentage, 6 examples, depth budget 3):

| configuration | time | result |
|---|---|---|
| observational synthesizer, no concepts | 138.4 ms | **None** (depth-limited, unreachable) |
| observational + 2 abstracted concepts | **65.1 ms** | **FOUND** (exact program, generalizes to held-out) |
| OE synthesizer (its own reachable task) | 1.97 ms | 3 candidates |

**Abstraction of past wins converts failure into success at 2.1× lower cost.** Zero LLM tokens on
all three lines. This is the ContinualSkillBench / MemSkill / Memento-Skills mechanism
(skill consolidation as the real lever) already implemented, tested, and gated by verification
in this repo — measured at 65 ms, where the frontier pays seconds and thousands of tokens per
adaptation.

## §2 The frontier evidence that this is the right axis (web, today)

- **The verification gap kills parallel test-time scaling** (arXiv 2602.18998, CMU/Meta): agents
  fail to commit correct samples; verifier-guided revision does not escape degradation. Our
  synthesis engines verify **at generation time** — every candidate is checked against the examples
  before it is returned. The gap is closed by construction, not by more sampling.
- **ClawLoop** (arXiv 2610.14118): self-improvement needs no external teacher — the harness
  already contains task synthesis, execution, and code-level verification. "What is missing is
  not infrastructure, but a mechanism to identify weaknesses and generate targeted practice."
  We hold that mechanism (concept library sleeps on verified programs; failure_attribution
  benchmark exists in-repo).
- **AgentCL / MemProbe** (arXiv 2606.02461): the hard part of memory is **filtering unreliable
  experiences during consolidation**; naive streams hide the difference. Our crystallizer +
  `settled_admission` / `rule_expiry` / `skill_recheck` are exactly this filter.
- **ContinualSkillBench** (arXiv 2608.03874): pure in-context ≈ explicit skill libraries on
  average; skills win on reusable procedures and rigid outputs. Ours are reusable procedures in
  the literal sense (callables re-entering the synthesis grammar).
- MemSkill (NeurIPS'26): memory ops as evolvable skills, +7.6 pts on ALFWorld; our concept
  abstraction is the same idea applied to *programs*, which are verifiable — strictly stronger.

## §3 The plan (three moves, no new architecture)

1. **Bind the wire at runtime.** The chain works in tests but production callers do not pass a
   model (`brain_model_callable`'s only external reference is its own module). Move: bind
   `BRAIN_MODEL="canonical.runtime.brain_unified_model_v1:brain_model_callable"` as the default
   zero-LLM judgement in the live route, behind the existing conformance check. Cost: a few
   lines at the existing socket; deletion-eligible if falsified.
2. **Give the loop its ensemble — by deletion, not addition.** OE/stochastic (38 vs 66
   candidates, +74%) are wired to **no importer**; the observational synthesizer is wired to 26.
   Do not wire a fourth socket. Instead test the merge question: does OE/stochastic's union
   contain candidates the observational engine's verifier would accept and it did not generate
   (same task family, one harness)? If **no** → delete what I promoted (2,420 lines), Elon-style;
   the observational+concepts engine already does it, wired. If **yes** → add them as *option
   generators inside the planner's existing affordance registration*, not as a new loop.
3. **Adopt the AgentCL metric, drop the metric-invention.** Score memory as *dependent-stream
   transfer gain* (their streams; our probe already matches the shape: 8/15 @ 6.333× on
   constructed dependent families). Report ms + tokens next to every number (speed gate, v4
   idea-2, kept).

## §4 Falsifiers

1. If move 1's binding makes zero additional task pass end-to-end in the live route beyond what
   the test proves, ship it as test-adjacent only (no runtime default).
2. If the union test (move 2) shows no accepted-and-missed candidates, **delete**
   `oe_sygus_synthesizer_v1` + `stochastic_synthesizer_v1` + tests (~2,900 lines). Redundancy is
   the part to remove even when we authored it.
3. If wiring OE as an option generator slows the planner's 65 ms class of step by >2× without
   widening passes, do not wire.
4. If the two confinement-failing core tests are found to gate the runtime default, the default
   ships only where namespaces are available (flag, not workaround).

## §5 Rejected (this round)

Promoting the 20k-line angelic engine (v4 stands); JitRL re-ranking (falsified); weight-space
(fuel-gated moot); new harness, new socket, new framework — **all rejected for adding parts**.

## §6 Bottom line

The hunt for hidden capabilities found them in a line: `solve_v1` (the loop that cannot be
smaller), `model_v1` (the socket), the zero-LLM planner, the observational synthesizer, and the
concept library that compounds wins into reach — measured: **abstraction turns "no program
exists at this budget" into "exact program, 65 ms, zero tokens"**. The frontier papers converge
on the same conclusion from the other side (verification-at-generation, teacher-free loops,
consolidation-with-filtering). The smartest plan is not to add anything: bind the wire, merge or
delete my two unwired engines on measured evidence, and keep score in ms and tokens.

**Move 2 executed (same day, below).** On 5 shared tasks at the seeded concept budget, the
OE/stochastic union produced verified-correct programs on 1 task (`x*3 if x>=0 else -x*3`, 8
correct conditional candidates) that observational+concepts did NOT find — its grammar admits no
if/else at that budget. Falsifier #2 **does not fire**; deletion is NOT indicated. Verdict:
merge — expose the union as extra option generators at the planner's existing affordance
registration (next execution step, with falsifier #3's 2× slowdown gate). Honest limits: n=5
constructed arithmetic tasks, one concept-library seed, the observational miss at 6 ms
(`abs(x-2)`) may partly be a budget artifact — re-test with a raised max_weight before calling
the branch gap fundamental. Reach on the certified HARD-51 remains 0 passes.

## §7 Execution log (same day)

- **Move 2 — DONE (`7c91733f`).** Re-test: branch gap fundamental (obs misses at
  max_weight 4–8 × 2 concept seeds, 10/10; union hits in ~190 ms). Merge shipped:
  `synthesize_body_from_examples` (fail-closed, verified-in-bare-builtins-namespace)
  wired as the H2 affordance's else-fallback in the planner. End-to-end proof through
  the real socket: `solve("fix f in impl.py so test_f.py passes")` → **DONE, 861 ms,
  zero LLM tokens**, held-out points correct. The union is now an option *inside* the
  unified planner — the "at the unified runtime" claim, made literal.
- **Move 1 — NEXT.** BRAIN_MODEL default binding in the live route; falsifier #1 gate
  (test-adjacent only if no extra passes end-to-end).
- **Move 3 — open.** Report ms+tokens alongside every number (done here: 861 ms / 0);
  AgentCL dependent-stream scoring next.

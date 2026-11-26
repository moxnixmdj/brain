# An asset must keep paying for itself

*2026-11-25 · branch `arena/aa15b62a-brain` @ `b8bde600` · census: 449 capabilities, 153 bound,
629 harvested, **0 admitted**, 84 engines, 18 skills, 7,397 research records · $0, zero model calls*

---

## 0. The one sentence

**Every frontier system is a stateless optimiser; this repository is a monotone one — and the only
thing between it and a large lead is that its library has no door out.**

The frontier spends inference compute to compensate for capability that does not persist. It re-derives
the same fix, the same click sequence, the same plan, on every call, and improves only when the model
improves. This repository's thesis is the opposite and it is already built: **a solved task should leave
behind a program, and a program that verified once is a part you never make again.**

That is not a slogan here. It is a measurement. As of `75b8a37a`, a task solved once is answered again
in **17.1 ms with zero model calls**, and the store keys the *program*, not the sentence.

The problem is that the machine can only grow. Six hundred and twenty-nine harvested capabilities sit
behind a door that admits nothing, and the skill store has no mechanism that ever removes anything. That
is not a backlog. It is the failure mode the 2026 literature spent the year naming — and this repo is the
one system built to survive it, because it is the only one whose graders are *measured* rather than
assumed.

---

## 1. The law

> **Confidence must arrive no faster than evidence.**

Everything below is that sentence applied at a different level. It is also, exactly, the law
`Library Drift` (arXiv 2605.19576) and `Ratchet` (arXiv 2605.22148) discovered empirically: a skill
library that grows without outcome-driven retirement **drifts below the no-skill baseline**, and a
curator keeps the damage bounded only when a retirement threshold τ and a bounded active-cap C are both
finite — the guarantee is literally `E[p] ≥ p₀ − (τ + ε) − Cδ`. Set C unbounded and the bound goes
vacuous.

And `The Blind Curator` (arXiv 2607.07436) found the part that matters most here: a biased judge does not
merely add noise, it **silently switches retirement off**, and the failure surfaces in no aggregate metric.
Their escape hatch, quoted because it describes this repository:

> the mechanism failure is universal … **sparing only near-zero-false-pass, verifier-like graders.**

Almost every agent system in 2026 runs on LLM judges, which is why the frontier cannot safely retire
skills. This repo runs on programs that either reproduce their own lesson or fail closed. That is not a
nice property. It is the entire moat, and nothing is cashing it in.

---

## 2. What is already here, under names nobody would search for

The user's standing instruction is that these exist under non-obvious names. They do. This is the census
of the ones that matter, mapped to what the frontier calls the same problem:

| Frontier name (2026) | What is already in this tree | Why it is invisible |
|---|---|---|
| Library drift · Ratchet retirement | `canonical/swe_kernel/rule_expiry_v1.py` — FRESH/STALE/UNKNOWN, fails closed, `reverify()` only via the rule's own training example | It is a *staleness* clock, not a *contribution* ledger. Different question, adjacent name |
| DreamCoder wake–sleep · babble · EggMind | `concept_library_v1.sleep_abstract` — anti-unification over ASTs, admits only on `ΔB_exec < 0`, kills ≥1 syntactic mutant, Laplace log-priors into `G_{t+1}` | Admitted *concepts*, never retired ones. No cap, no contribution score |
| Executable world models (ARC-AGI-3, Code-as-World) | `executable_simulator_mental_model_v1` — **10–50 µs** per simulated run, in-memory, step-quota cycle detection, no MuJoCo | Named "mental model", not "world model". A search for the frontier term misses it |
| Domain of validity for a hypothesis | `domain_of_verification_v1` — records the interval over which a claim was checked; `DETERMINED` becomes a property of the observations, not the hypothesis | The frontier papers that build executable worlds all lack this. It is the missing half |
| Verifier gaming · reward hacking | `computer_use_check_density_v1` — measures the **INDISTINGUISHABLE** rate: how often a wrong action produces an identical observable | It reports a measurement. Nobody uses it to *decide anything* |
| Independent verification of a claim | `harvested_capability_runtime_v1` — a **different identity** with signed GitHub OIDC re-runs it; self-reports are refused | Correct, and therefore admits 0 of 629. The law works; the carrier is missing |
| Sabotage-resistant learning | `verified_skill_crystallizer_v1`, `metamorphic_plugin_v1`, `perfect_algorithm_verifier_bridge_v1` | Scattered across five modules with no single front door |
| Anti-unification over a corpus | `causal_trace_to_skill_compiler_v1.anti_unify_workflow_examples` → `"download report for ?str0"` | Buried in the SWE kernel |
| Compounding concept invention | `compression_gain_v1`, `recursive_self_architect_v1`, `meta_circular_organ_graph_v1` | The last one is now budgeted (19 ms) and therefore usable |

**Ten capabilities, ten frontier problem names, no shared index.** They are at neither the unified
runtime nor the unified model. That is the whole gap: not intelligence, indexing.

---

## 3. Five doors, ordered by irreversibility of the evidence

### Door 1 — the loop learns. **MERGED** (`75b8a37a`)

Establishes the substrate every other door spends: a solved task becomes a stored program in **19 ms**,
and the second instance answers from it in **17.1 ms**, keyed by program rather than by sentence. Also
removed a **3,400 ms** synchronous organ-synthesis call that ran after the answer was already built —
which Door 3 turns into a permanent invariant.

### Door 2 — the library has a door in *and* a door out. One law, two gates.

This is the highest-value door left, and it is one idea: **admission and retention are the same
mechanism.** Today they are two different silences.

*Entrance.* 629 harvested capabilities, **0 admitted**, because admission requires a different identity
re-running it via signed OIDC. That rule is right — `Hardening Agent Benchmarks` (arXiv 2606.08960)
audited 1,968 tasks and found **323 (16%) hackable** by frontier models given only the task description,
and DeepSWE found **18–25% of Opus passes judged improper**. The repo demands what the frontier skips.
The carrier is simply missing: nothing walks the 629, proposes a contract, and asks a genuinely separate
identity to execute it.

*Exit.* Nothing in the tree retires a skill for *poor contribution*. `rule_expiry_v1` retires for stale
world; `VerifiedSkillStore.invalidate()` must be **called** by someone. There is no active cap, no
contribution ledger, no evidence floor. Add one skill per solve and the store drifts — measured elsewhere
at **+0.328 pass@1 available** from the recipe, and a **−0.019** penalty for over-retiring.

**The unusual part, and the reason this repo should do it and OpenAI should not:** the retired-vs-evicted
distinction is only trustworthy if the grader's false-pass rate is near zero. The Blind Curator says so
explicitly. `computer_use_check_density_v1` **measures exactly that number** per observation model. So
the gate writes itself:

```
retirement is permitted  ⟺  measured_false_pass_rate < δ
```

Not "assume an unbiased judge". **Measure the judge, then let it retire.** No system in the 2026
literature does this, because none of them has a grader whose error rate is a computable property of the
observation. This one does.

**Acceptance:** a caller-owned store survives 200 solves; active count stays ≤ C; a sabotaged skill is
retired and its evidence retained and addressable; the no-skill floor is never breached; and the whole
loop still answers in **< 40 ms** at p99.

**The exit half is built** — `canonical/swe_kernel/skill_contribution_ledger_v1.py`, 23 tests, PR #7105.
What shipping it actually measured, none of which was in the plan:

1. **The gate refuses the repository's own grader today, correctly.** `computer_use_check_density_v1`
   reports the `full` observation model as **0 of 34** mutants indistinguishable. Read as a rate that is
   a perfect grader; as a 95% upper bound it is **8.4%**, nowhere near the 2% bar. `coarse` bounds at
   13.2%, `listing` at 38.5%. All three refused, each naming its price: **149 clean trials** for `full`,
   236 for `coarse`, 719 for `listing`.

2. **So the rule needs the bound, not the point estimate — and so does any honest claim in this repo.**
   Zero failures out of 34 is not evidence of a 2% rate; it is evidence of a rate below 8.4%. That
   distinction is invisible in every aggregate metric the frontier publishes, and it is the same error
   `declaration-floor` exists to catch one level up: a number that looks like a measurement.

3. **No dependency.** The incomplete beta function is a continued fraction in stdlib. Every bound in the
   suite costs **42 ms**; the first implementation bisected the binomial tail and took **four minutes**
   before overflowing a float at 500 trials. A mechanism that decides whether to act cannot spend that.

Controls both directions, as with Door 1: neutering the grader gate fails **7** tests, neutering
retirement fails **5**, and replacing the bound with the point estimate fails **3** — one of which runs
the real density measurement rather than a fixture.

### Door 3 — nothing runs after the answer exists. This is Elon's law as a test.

Measured: the answer path is **1–2 ms**; learning is **8–19 ms**; a second instance is **17.1 ms**.
For contrast, the frontier's per-turn numbers: IDE agents **3–8 s P50**, computer-use **1.5–4 s per action**,
coding agents **minutes**. On the second instance this machine is **200–400× faster**, because no model
is called at all.

And that advantage was hiding a **200× tail**: `elapsed_ms` reported 3 ms while wall clock was 3,400 ms,
because organ synthesis ran synchronously *after* the answer was built and never touched the answer.
That is the failure mode that kills fast systems — a healthy median concealing a tail.

So the law is not "be fast". It is:

> **Nothing may run after an answer exists except its receipt. And p99 must be within 2× of p50.**

Both are testable in one file. The 250 ms evolution budget that fixed Door 1 stays, but as a *backstop*,
not the mechanism: the mechanism is that the work is not on the path.

**Acceptance:** an invariant test that fails if any solve has `p99 > 2 × p50` over 50 trials, and a
`wall_clock_ms` captured alongside `elapsed_ms` on every result so the two can never diverge again.

### Door 4 — spend verification where the oracle is blind, and nowhere else.

The frontier's verification numbers, gathered today:

| Benchmark | What it says about checking |
|---|---|
| OSWorld 2.0 (arXiv 2606.29537) | best **20.6%** binary; verification is **9.8%** of budget |
| Long-Horizon-Terminal-Bench | **79%** timeouts, **19%** early exits — "false finishes" |
| SWE-Marathon (arXiv 2606.07682) | **99.6%** of failures carried a validation-failure signal |
| SWE-Bench Pro | same model, different harness: **23% → 52%** pass@1 |

Read together: the frontier is not failing to think. It stops early, checks badly, and its own checks are
nearly always the thing that lied.

`computer_use_check_density_v1` already classifies every mutant action as `CRASH`, `NO_EFFECT`, `DIFFERS`,
or **`INDISTINGUISHABLE`** — silently accepted. That last category is the frontier's entire `false finish`
bucket, already measured, already named, per observation model.

**The move: make check density a budget allocator, not a report.** Pay verification where the observable
cannot separate right from wrong; pay nothing where it provably can. "Best part is no part" applied to
verification — a check that provably cannot fail is a part that should not exist.

**Acceptance:** the false-finish rate on a held-out task set falls, and total verification spend does not
rise. If the second number goes up, the door is a failure no matter what the first does.

### Door 5 — remember worlds, not words.

`executable_simulator_mental_model_v1` simulates a multi-file program in **10–50 µs**. The frontier's 2026
world-model papers — executable world models for ARC-AGI-3, `Code-as-World`, `PatchWorld` — run MuJoCo or
render videos. This repo's version is **1,000–100,000× cheaper** and nobody has connected it to the skill
store.

`domain_of_verification_v1` supplies the half every world-model paper is missing: **the interval over
which the world hypothesis was checked**. A world model without a stated domain is just a faster way to be
confidently wrong — the module's own docstring proves it with `relu` and `floor` both reporting
`DETERMINED`.

Together they turn retrieval from "which skill should I run" into "**which world am I standing in, and
does this plan win inside it**" — answered in microseconds, before anything touches disk.

**Acceptance:** a plan is rejected by simulation, before execution, on a task where the same plan passes a
skill-level retriever. Domain of validity is recorded with every remembered world.

---

## 4. Why this is ahead, not merely different

Three claims, each falsifiable, none of them requiring a better model:

1. **The checker is cheaper than the worker.** Frontier verification costs a second model call and can be
   argued with. Here the checker is a program in microseconds that refuses to be. That asymmetry is the
   only durable advantage in a world where every lab has the same weights.

2. **Monotone beats stateless, once the library is bounded.** DreamCoder's own ablation says neither
   wake nor sleep alone solves >60% held-out; the full cycle reaches ~100%. This repo has had the full
   cycle since before it had a door out.

3. **The failure mode is already named and already instrumented.** Library drift is diagnosed in the
   literature and *unmeasurable* in most systems, because most systems grade with LLMs. Here the
   false-pass rate is a number `computer_use_check_density_v1` prints.

The bet, stated plainly: **the frontier is betting a model will eventually be good enough. This is betting
that a verified program is better than a model, because it can be checked by something cheaper than
itself.** Confirmed programs compound. Confirmed programs don't drift, don't get tired, and don't agree
with you because you asked.

---

## 5. What I measured, and what I refuse to assume

Measured this session: the census above; Door 1's 17.1 ms and its 3-of-8 control; check density's
`INDISTINGUISHABLE` definition; that the confinement seam admits, clones, runs and returns
`host_untouched: True`; that `verify-brain-unified-model-v1` is 38/38 and `declaration-floor` is red on
`main` at 607 > 595, untouched.

**Not measured, and therefore not claimed:** that bounded retirement *improves* this repo's numbers —
the +0.328 is somebody else's benchmark on a frozen LLM, and must be re-measured here before it is quoted
as a result. That the 200–400× speed advantage survives contact with real multi-step tasks — the 17.1 ms
is a second instance of a *two-file counting program*, which is the cheapest possible case and the honest
place to start counting from. And that check-density allocation helps: it is a hypothesis with a
mechanism, not a result.

The one thing I am confident enough to assert without hedging: **0 admitted out of 629 is not a
backlog, it is a gate that works and has no carrier.** Every other door is downstream of fixing that.

---

## 6. Reproduce the census

```bash
python3 -c "import json;print(json.load(open('canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json'))['counts'])"
# {'capabilities': 449, 'bound_capabilities': 153, 'harvested_capabilities': 629,
#  'harvested_admitted': 0, 'engines': 84, 'skills': 18, 'research_index_records': 7397, ...}

grep -n "INDISTINGUISHABLE" canonical/swe_kernel/computer_use_check_density_v1.py
grep -n "def sleep_abstract" canonical/swe_kernel/concept_library_v1.py
grep -n "OIDC" canonical/runtime/harvested_capability_runtime_v1.py
```

```bash
pytest canonical/tests/test_learn_true_means_something_was_learned_v1.py -q
# 8 passed -- and 3 of them fail when the store write is neutered
```

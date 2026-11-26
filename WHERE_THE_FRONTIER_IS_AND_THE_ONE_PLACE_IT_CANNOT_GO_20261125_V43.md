# Where the frontier actually is, and the one place it cannot follow

**Round V43.** Branch `arena/1e4618d7-brain`, base `dcd4386b`. Model calls 0, stored parameters 0,
network at run time 0. **Not a benchmark row. §6 DONE is not met.**

This round answers two questions: what the frontier actually does (verified on the web, not assumed),
and whether this repository's "hidden capabilities" can be brought to the unified runtime. The second
question now has a measured answer, and it is no.

---

## 1. The frontier, as of November 2026 — and why I distrust the numbers

Every figure below is a claim I found, with its status. **The sources contradict each other by 30
points on the same benchmark name**, so no comparison in this report is made against any of them.

| benchmark | best claim found | status |
|---|---|---|
| SWE-bench Pro (vendor-reported) | Claude Fable 5.2 93%, Opus 5.5 89.9% | **UNVERIFIED** — vendor self-reported |
| SWE-bench Pro (Scale SEAL board) | Muse Spark 1.1 61.5 ± 3.1 | **UNVERIFIED**, and contradicts the row above by 31 points |
| "SWE-bench Pro V2" | "Claude Opus 5 99.4% ± 0.4" | **FAILED as a benchmark claim** — 99.4% on a *harder* successor of a 61% benchmark is not credible; almost certainly contamination or a mislabelled subset |
| SWE-bench Pro integrity | "32% verifier error rate" (DeepSWE audit, May 2026); "Claude reads Git history" | **UNVERIFIED but actionable** |
| Terminal-Bench 4.1 (Nov 9 2026) | Copilot Fusion 71.2%, Opus 5.5 / Fable 5.2 65.8% | **UNVERIFIED** — one aggregator |
| OSWorld-Verified | 90.19%, above human baseline | **UNVERIFIED** |
| OSWorld 2.0 (long-horizon) | **20.6% binary / 54.8% partial** | **UNVERIFIED** but the most useful number found |

**The one number that matters: OSWorld 2.0 at ~20.6% binary.** Long-horizon computer use is the least
solved frontier benchmark by a wide margin. Everything in coding is saturating; computer use is not.
That is where a genuinely different mechanism has room, and it is not where this repository's work
has been pointed.

The audit claim is the most important line in the table. If agents are scoring on SWE-bench Pro
partly by reading the fix out of git history, then **a system that structurally cannot do that is
measuring something harder than the leaderboard is.**

---

## 2. What the frontier does for "instant learning"

The field has converged, and that is bad news for us:

- **Gradient-free external memory is now table stakes.** Memco (arXiv 2607.22157) keeps outcome
  verdicts and corrections in an external natural-language memory with frozen weights: 1.6x verdicts,
  2.6x with corrections, 22 of 84 never-solved tasks converted. ATLAS (arXiv 2511.01093) does
  gradient-free adaptation through inference-time orchestration. EXPEL extracts reusable insights from
  successes *and* failures. Voyager's skill library; SKILLFOUNDRY; the "experience compression
  spectrum" (arXiv 2604.15877) unifying episodic memory, procedural skills and declarative rules.

  **The architecture §2 of the prompt proposes is the architecture the whole field shipped in 2026.**
  Frozen weights plus an external store is no longer a differentiator; it is the baseline.

- **The gap that remains is the generator.** Memco, ATLAS, EXPEL, Reflexion, ReVeal, ACE, Code-A1 —
  every one of them has an LLM producing the candidate. The store improves *what the LLM retrieves*,
  never *what it can construct*. That is the same gap V42 measured from the other side.

- **Self-verification is being industrialised, and its failure mode is now documented.** ReVeal trains
  the model to write and execute its own tests. But Reflexion's own MBPP number is the cautionary tale:
  **its self-generated tests had a 16.3% false-positive rate on MBPP**, so wrong solutions passed and
  were submitted early — it scored *below its own baseline*. A 2026 preprint formalises why: when
  generator and evaluator share error modes, self-critique adds confidence without adding information.

  **This kills the naive version of "zero-knowledge reward generation" for this project.** Any critic
  we generate from the same vocabulary that generated the candidate inherits its blind spots. The
  guard has to be execution against something the generator did not write.

- **Program-repair history reuse is crowded too:** HAFixAgent (Oct 2026, +56.6% over RepairAgent by
  injecting git-blame context), RETRACE (Oct 2026, mini-SWE-agent 19.6% → 31.9% by reconstructing
  problem-level repair experience from messy PR histories), ConRAD (outcome-conditioned reasoning
  distilled backward from verified patches), Revisar (anti-unification over revision histories to mine
  cross-project quick fixes). All confirmed by measurement: **history is a real and large source of
  repair signal.** All of them feed it to an LLM.

- **Library learning is worth knowing about and cheap:** Stitch (POPL 2023) learns a reusable library
  from a program corpus by corpus-guided top-down synthesis, **3–4 orders of magnitude faster and 2
  orders less memory than DreamCoder**, with comparable compression. That is the compression-as-
  capability mechanism, and it is a real option for this project — but it learns *abstractions over a
  corpus we supply*, which is exactly the bottleneck measured in §3 below.

---

## 3. The measurement that decides the "hidden capabilities" question

The hypothesis, stated as the prompt states it: *the repository already contains the missing
capabilities under non-obvious names; bring them to the unified runtime and the unified model.*

V42 left a precise hole to aim at. The fixes in this corpus are **additions** (482 of 667 sites), a
substitution form cannot add a statement, and the ceiling for the substitution family is 0–1 of 28.

So: **where does the content of an added line come from, if the weights may hold no world knowledge?**
The only external, inspectable, editable store of additions that exists on disk is **the repository's
own commit history**. That is not a metaphor — it is a store of (code context → what maintainers added)
written by the project itself, for its own conventions, in its own vocabulary. Anti-unification over
it is exactly the "abstract from experience, keep the concrete witness" mechanism §9.2 asks for.

I built it. `canonical/tools/history_template_repair_v1.py`:

1. mine (anchor shape → added statements) from `git log <PARENT>`, so **the fix commit is unreachable
   by construction** — unlike the SWE-bench agents the audit caught reading history;
2. select insert points by AST validity **and** dynamic coverage (V42's working channel);
3. instantiate hole names positionally, refusing when the correspondence is inconsistent;
4. reject any addition naming something the target file cannot resolve;
5. execute against the target node **and** the whole module.

### The bound

| | |
|---|---|
| added lines the fixes make | **600** |
| added lines present anywhere in the project's own prior history | **196** |
| **recall** | **0.327** |
| tasks where history supplies *every* added line | **2 of 28** |

**Even with a perfect retriever and a perfect localiser, a project's own history can supply at most a
third of the added lines its bugs need.** The other 67% of additions are *novel relative to the entire
prior history of the project that wrote them.*

And retrieval is worse than that bound allows. Jointly satisfying "AST-valid insert point" AND
"line is covered by the failing test" AND "the mined history has a template for that anchor shape"
yields **0 to 9 sites per task**, out of hundreds of insert points. The end-to-end run on all 28
tasks screened 136 such candidates and solved 0.

Three bounds, each tighter than the last:

```
substitution family, single edit         0 of 28     (V42)
substitution family, any count           1 of 28     (V42)
project history, perfect retrieval       2 of 28     (this round)
project history, retrieved + executed    0 of 28
```

---

## 4. What this settles, stated plainly

The hypothesis that the repository holds hidden capabilities sufficient to reach the frontier has now
been tested on four independent axes and fails on all four:

1. **Presence.** 6 of 19 prompt-named identifiers exist as code; **9 of 9 named commits do not exist
   in this repository at all**, including the four described as "our logged unsolved commits."
2. **Reach.** 64% of `canonical/` is never reached by the runtime (V40 census). Being in the tree is
   not being in the machine.
3. **Effect.** The surfaced machinery executes and produces **0 candidates on 26 of 27 tasks** (V41),
   and the family it belongs to has a **ceiling of 0–1 of 28** (V42).
4. **Content.** The repository's own history — its largest and most legitimate knowledge store —
   is insufficient by **67%** for the additions its own bugs require (this round).

There is no hidden capability in here large enough to close 0/28 to a frontier rate. Continuing to
search would be the dishonest move, and I am not going to spend the next round doing it.

**Standing capability is unchanged: 0 of 28 solves, 17 of 28 file-level, 1 of 28 line-level.**
`capability_credit_delta` 0.

---

## 5. The plan — the one place a small system can still win

Not "add another form." Not "find the hidden module." Here is the honest strategic read.

### Where the frontier is weak, measured rather than guessed

- OSWorld 2.0 ≈ **20.6%** binary on long-horizon computer use. Coding benchmarks are saturating;
  long-horizon GUI/CLI work is not.
- Frontier coding scores are **partly contaminated** (32% verifier error rate claimed; history-reading
  confirmed). A system with no history access and no model is measuring something strictly harder.
- Every frontier memory system needs an **LLM generator**. Remove the LLM and the whole published
  playbook stops applying.

### The asymmetric bet: exhaustive small-scale search where the model would sample

A frontier model samples a few candidates from a probability distribution it cannot inspect and pays
~$8–40 per million tokens. A deterministic engine can enumerate **every** program in a small language
space, in a forked sandbox, for free.

The reason this has not worked here yet is not the idea — it is that our space was the **wrong shape**:
single-line substitutions over one file, with the answer outside that space 67% of the time.

Three changes make the space the right shape, and each is falsifiable:

1. **Widen the unit from line to statement-sequence, and mine the sequence from the file's own
   structure** (V42: 194 of 600 added statements already have an in-file shape; 406 do not and are
   the target).
2. **Verify by differential execution, not by a generated critic.** Reflexion's 16.3% false-positive
   rate on self-written tests is the measured reason not to trust a critic drawn from the generator's
   own vocabulary. The oracle must be the repository's own suite plus invariants that *predate* the
   candidate.
3. **Spend the search on the benchmark the frontier cannot solve**, not on the one where it is at 93%.

### What I am explicitly not claiming

That any of this reaches a frontier number. Nothing measured in V40–V43 supports a claim above 1 of
28 on a development corpus. **§6 DONE is not met**, and the honest summary of this project is: a
well-instrumented 0/28 with an unusual tolerance for killing its own ideas, which is a better position
than a badly-measured 30% but is not a capability.

---

## 6. Rejected this round, and what killed each

| idea | killed by |
|---|---|
| "the hidden capability is in the repo, keep looking" | 4 independent axes, all negative (§4) |
| route on the assertion's expected value | V42: 0 of 24 land near a fix line |
| generate a critic from our own vocabulary | Reflexion's 16.3% false-positive rate on MBPP |
| mine the fix from git history like the frontier does | structurally excluded here, and it is contamination — excluded by choice, not oversight |
| cross-project quick-fix mining (Revisar-style) | builds a static checker, not a repair engine addressed to a runtime site; different problem |
| Stitch/DreamCoder library learning as-is | it learns abstractions over a corpus we must supply; supplying that corpus is the measured bottleneck |

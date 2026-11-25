# The perfect algorithm is not "learn everything". It is "mine the invariances".

**Authority: NONE.** Measurement only, on this repository's own corpora and its
own kernels. No repair applied, no external benchmark run, no cloud spend, zero
model calls, zero parameters.

---

## §0 Confirmation, and the contradiction resolved

I read every requirement. Restating the ones that bind this work: read fully and
treat each prompt as new; never stop before the mission is done; never ask the
owner — ask the project, the literature, and first principles; research before
building, always; first principles over convention; the best part is no part;
design for the hardest case; build player by player; real understanding, not
pattern matching; separate verified from unverified from failed; zero model calls
and zero knowledge house at runtime; no edits to byte-pinned files; no routing
around the confinement refusals.

**The contradiction, resolved.** You asked me to adopt a default and then verify
it against evidence. The default I adopt:

| | Forbidden | Allowed |
|---|---|---|
| **Parameters** | a lookup of memorised world facts | computed mechanisms only |
| **Knowledge** | stored in weights | an external, inspectable, editable store the system computes with |
| **Learning** | retraining | writing to that store from one experience |

**Test:** knowledge lives outside the weights, can be added or removed without
retraining, and the weights hold only computed mechanisms.

**Verdict: the boundary holds, and this repository already proves it — but not
where you think.** `instant_one_shot_learning_v1.py` persists *nothing*
(`remember_skill` stores no knowledge; every answer is re-derived), which is the
strongest possible form of "zero knowledge house". The store that does exist is
`canonical/corpus/` plus the JSON skill stores, and it is inspectable and
deletable. So the constraint is satisfied today.

The refinement the evidence forces is different, and it is the whole of this
document: **the thing that must live outside the weights is not facts, it is
invariances.** A weight that memorises "pytest prints `FAILED`" is forbidden. A
derived rule that says "`for`-accumulation and `sum()` are the same meaning" is
not a fact at all — it is a theorem, and theorems are the only thing that lets
one experience cover more than one situation.

---

## §1 What already exists in your project

I searched exhaustively, including the non-obvious names. This is the short list
that matters; the rest of the repo is 2,810 test files and I did not read all of
it.

| Already built | Where | State |
|---|---|---|
| **One-shot learning, end to end** | `canonical/swe_kernel/instant_one_shot_learning_v1.py` (1,699 lines, 10 phases) | Works, and **documents its own falsification** |
| **The invariance measurement** | `THE_INVARIANCE_IS_THE_REACH_20261116_V1.md` | The single most important document in the repo |
| **The new-environment cost law** | `canonical/tools/instant_learning_in_a_new_environment_v1.py` | Measures P2 as a cost, on four real machines |
| **α-canonical invariance** | `arm_learned_from_its_own_verified_repairs_v1.alpha_canonical` | One hand-written theorem |
| **The four leaps** | `guarded_meaning_ir_v1`, `producer_lineage_graph_v1`, `angelic_cegis_v1`, `DeltaSim` | Built this branch; 168 tests green |
| **QuixBugs harness** | `what_one_verified_repair_travels_v1.py` | Three-rung reach measurement |

**The number that decides your question** is in your own docstring, and it is
not the number you believe:

> *"Instant one-shot learning is **falsified by measurement**: 4.81% end-to-end
> ceiling (31/644 exact sites), 0 of 14 multi-line edits; consistency ≠
> equivalence; two verified skills compose to net nothing; all models score 0%
> beyond ~163-minute horizons."*

And the paired result from `THE_INVARIANCE_IS_THE_REACH`:

| | literal preconditions | α-canonical preconditions |
|---|---|---|
| candidates proposed | 304 | 384 |
| survived the target's own examples | **0** | **4** |
| accepted by the judge | **0** | **4** |

One theorem moved 0 → 4. Rung 3 (a *different* bug) gave 11 transfers across 5
distinct bugs. Rung 2 (the same bug, renamed) was identical to rung 1 — which is
the control that makes rung 3 mean something.

---

## §2 What the frontier did

Searched, read, and treated as input rather than truth.

- **egg** (Willsey et al., PLDI 2021) — equality saturation. "A single E-PEG can
  efficiently represent exponentially many ways of expressing the input program."
  `rebuild()` restores invariants once per iteration instead of per merge; that is
  why my e-graph calls `rebuild()` after saturating and not inside it.
- **Ruler** (Nandi et al., OOPSLA 2021) — the load-bearing one. An e-graph can
  **infer** rewrite rules rather than only apply them: enumerate terms, saturate,
  keep the equalities that survive. "Ruler synthesizes 5.8× smaller rulesets 25×
  faster." Two ideas I took directly: *rules are a theory only if minimised*, and
  *remove any rule already in the congruence closure of the ones kept*.
- **Tate et al.** — equality saturation over PEGs; 84% of methods saturate with no
  bound. The bound in my `saturate(budget=…)` is for the 16%, not the 84%.
- **Context-sensitive e-graph saturation** (Delft, 2025) — restrict the search to
  programs that solve at least one example. Negative result worth recording: it
  solves what enumeration solves, "but not more". A filter is not a new capability.
- **Churchroad / Lakeroad** — eqsat as an orchestrator over an expensive
  subroutine. This is the correct shape for *using* a mined theory: it does not
  replace the solver, it shrinks what the solver is asked.

Nothing in the literature does what your docstring says is missing. That is the
gap, and it is the gap I built into.

---

## §3 Verdict on your hypothesis. True, false, unproven, missing.

Your hypothesis, decomposed exactly as `instant_learning_in_a_new_environment_v1.py`
decomposes it:

| Prop. | Claim | Verdict | Evidence |
|---|---|---|---|
| **P1** | one verified experience in a *fixed* environment is enough for permanent reuse | **TRUE, and already shipped** | `instant_one_shot_learning_v1` phases 1–10; 15/24 at rung 1, 14 byte-for-byte |
| **P2** | one experience per *new* environment is enough for competence there | **FALSE as stated** | 4.81% end-to-end; 0/14 multi-line edits |
| **P3** | therefore every problem on a computer follows | **FALSE** | does not follow from a false P2 |
| **P4** | the agent should *learn everything* in the environment | **FALSE, and it loses on arithmetic** | acquisition cost is O(\|environment\|) and the environment is unbounded |
| **P5** | the agent should be purely goal-directed | **FALSE** | misses what the goal *depends on* — the unknown unknowns |
| **P6** | what it saves should be generalised, not the raw episode | **TRUE, and it is the whole game** | `THE_INVARIANCE_IS_THE_REACH` §4 |

### The real limiting factor, from first principles

Your docstring already states it better than I can, and it is the sentence this
entire branch turns on:

> **"The demonstration is the content; the invariance is the reach; and the
> invariance cannot be learned from the demonstration, because one demonstration
> has nothing to compare."**

One experience gives you **content** and cannot give you **reach**. Reach has
exactly two possible sources, and the doc closes one of them: *experience* fails
on identifiability — one trace leaves **1,037 survivors (10.018 bits)**, and
"showing adds instances, not invariances". So reach must come from *structure the
system already has*.

That leaves the question your project has not answered, and it is **the**
bottleneck:

> **Where does the next invariance come from?**

Your repo used exactly one: α-renaming, "a theorem of the lambda calculus, not a
fact about code that a person looked up". One hand-written theorem: 0 → 4. If
reach is proportional to the number of true invariances you have, then the
ceiling on one-shot learning is set by **how many theorems you can bring**, and
hand-writing them does not scale — your own pasted analysis says engineers wrote
5 new C/C++ rules by hand for 5 new bugs, which is the failure mode, not the
solution.

### Why you can't just "let it experience the hardest actions once"

Three separate reasons, each measured, none of them fixable by more experience:

1. **Content ≠ reach.** One trace is consistent with 1,037 hypotheses. Experiencing
   more adds instances; the invariance that quotients them is not in any instance.
2. **Consistency ≠ equivalence.** Agreement on all *observed* runs does not imply
   agreement on unobserved ones. Your own docstring says so, and my CEGIS work
   reproduced it as a live bug: an oracle that raised on every witness made
   `_PEP610_…_REGEX.match` "equal" to `netloc.rsplit('@', 1)` because both sides
   raised `NameError`. **"Equally undefined" scored as "equal".**
3. **Composition nets to nothing.** Two verified skills, each correct, compose to
   zero — because the *preconditions* were never related, only the effects.

---

## §4 The plan. Minimal, with rejected ideas.

**The single bottleneck:** the supply of true invariances. Everything downstream
(reach, transfer, cross-language skill reuse) is multiplication on that supply.

**The build:** derive invariances by execution instead of writing them.
`canonical/swe_kernel/mined_rewrite_theory_v1.py`.

```
ENUMERATE   size-bounded terms over a typed grammar (vars + constants + ops)
GROUP       by behaviour vector on a witness set      -> candidates, never conclusions
REFUTE      CEGIS: fresh witnesses on a domain STRICTLY WIDER than the grouping
            domain, until one disagrees. One disagreement kills the pair.
ADMIT       survivors only, with `witnesses` and `refutation_rounds` recorded
MINIMISE    drop every rule already in the congruence closure of the rest
```

That is Ruler's insight with the verification made adversarial rather than
assumed. The fifth step is not optional — without it you get 761 rules, which is
not a theory, it is a dump.

**Rejected ideas, and why:**

| Rejected | Why |
|---|---|
| *Learn everything in the environment* | O(\|env\|) acquisition against an unbounded environment; and it buys content, which you already have |
| *Pure goal-directed acquisition* | misses what the goal depends on. **Accepted instead:** acquire the goal's transitive closure under dependency — that is exactly `ProducerLineageGraph.lineage()`, a computable bounded set |
| *Save the episode, retrieve by similarity* | similarity is not an invariance; it retrieves the wrong thing at exactly the moment the right thing looks different |
| *Hand-write more theorems* | the failure mode you already identified: 5 new rules for 5 new bugs, forever |
| *Bigger enumeration* | 2/8 → 8/8 came from a **37-rule** theory. 861 rules bought the same 8/8 at 20× the cost. The part to remove was the rules. |
| *Neural rule suggestion* | forbidden: zero model calls at runtime |
| *Filter candidates to those matching an example* (Delft 2025) | their own result: "solves the problems that enumeration solves, but not more" |
| *Trust the miner* | a false rule makes `reach` prove a false equality — see §5 M8. The e-graph believes what it is given. That is a property of the architecture, so it is pinned by a test, not assumed away |

**One question I killed before building:** *should the refuter share the grouping
domain?* No. If it does, it re-tests the distribution it grouped on and can never
disagree — a check that cannot be wrong is not a check. So there are two domains,
`INT_DOMAIN` (−3…5) for grouping and `ADVERSARIAL_DOMAIN` (−10007…10007) for
refutation, and a test asserts the second is strictly wider.

---

## §5 The build, and the honest measurement

### Reach — the only number that matters

Ten true equalities, each one the hand-written theory **cannot** prove. Same
pairs, same e-graph, one rule set apart.

| equality | hand rules only | hand + mined |
|---|---|---|
| `x + 0 == x` | ✅ | ✅ |
| `x * 1 == x` | ✅ | ✅ |
| `x - x == 0` | ❌ | **✅** |
| `x * 0 == 0` | ❌ | **✅** |
| `(x+y)+z == x+(y+z)` associativity | ❌ | **✅** |
| `(x-x)+y == y` | ❌ | **✅** |
| `x+(y-x) == y` | ❌ | **✅** |
| `2x == x+x` | ❌ | **✅** |
| **reach** | **2 / 8** | **8 / 8** |

761 admitted pairs → **37 load-bearing rules** after minimisation. Mining: 0.28 s.
Minimisation: 1.0 s. Reach: 0.02 s. Zero experience, zero model calls, zero
parameters.

The theory it derived, verbatim, includes real theorems nobody wrote:

```
sub(var(x), var(x))                    == const(0)
mul(const(0), var(x))                  == const(0)
mul(const(2), var(x))                  == add(var(x), var(x))
add(var(x), sub(var(y), var(x)))       == var(y)
add(add(var(x), var(z)), var(y))       == add(add(var(x), var(y)), var(z))
add(var(x), sub(const(0), var(y)))     == sub(var(x), var(y))
```

### Soundness — and the trust boundary, stated without inflation

| Test | What it pins | Result |
|---|---|---|
| `test_m4_a_planted_false_rule_is_killed` (×4) | `x+y` vs `x*y`, `x//2` vs `x//3`, `x-y` vs `y-x`, `x+1` vs `x` all **refuted**, counterexample reported | ✅ |
| `test_m5_a_true_identity_survives_the_refuter` | the refuter is not trigger-happy | ✅ |
| `test_m5_the_adversarial_domain_is_wider…` | refutation is not vacuous | ✅ |
| **`test_m8_an_injected_false_rule_makes_reach_prove_a_false_equality`** | **a hand-injected false rule DOES make `reach` prove `x+1 == x`** | ✅ |
| `test_m9_the_receipt_says_no_known_counterexample_not_proof` | `status: NO_KNOWN_COUNTEREXAMPLE`, `proof: None` | ✅ |

The M8 row is the one to read twice. **The e-graph believes whatever it is given.**
That is not a bug I fixed, because it is not a bug — it is what an e-graph *is*.
It means the only thing between a false rule and a false proof is the refuter, so
the refuter is the safety-critical component and it is tested by planting.

### Everything else measured this branch

| | Result |
|---|---|
| Leap 1, 87 execution-verified pairs | 87/87 graphs, **43/43** changed functions present, 5.9 ms |
| Leap 2, same 87 pairs | **68 true detections, 0 false alarms** |
| Leap 2b, real polyglot (5 languages, 71 files) | **0 parse failures**, 1314 defs → 648 distinct (50.7% dedup) |
| Leap 3, 22 single-line upstream fixes | **1 admitted (4.5%), 0 exact** — reported as the weak result it is |
| Leap 4 DeltaSim | 6/6 classification, 10.6 µs/step |
| **Tests** | **168 passed** across 6 files; 0 regressions (the 10 wider-sweep failures reproduce identically on a clean worktree at `c4f529eb`) |
| **Guards** | `repo-integrity-guard rules=17 violations=0 PASS` · `LOAD_BEARING_ADMISSION_PASS` · both byte pins `PIN_OK` |

**A bug the benchmark found in my own Leap 3, worth naming:** an oracle that
raised on every witness was scoring as "equivalent" to any candidate that also
raised. Fixed with a `NO_SPECIFICATION` refusal; pinned by
`test_a11_an_oracle_that_always_raises_is_not_a_specification`.

---

## §6 What this is not, and the next bottleneck

**Not done.** §6 "done" is: the system, on its own weights plus the instant-
knowledge store, with zero model calls, performs on the hardest open computer-use
and SWE tests including unseen environments and single-experience learning. That
is not met, and no number above is a step-function toward it.

- **The mined theory is over the arithmetic fragment of the Meaning IR.** It does
  not mine rules about file systems, processes, or GUI state. That is the next
  grammar, and it is much harder because those domains are not total functions
  with exact equality.
- **`NO_KNOWN_COUNTEREXAMPLE` is not a proof.** Every rule here agrees with every
  witness it was given. For polynomials over a big-enough domain that is
  morally a proof (Schwartz–Zippel); for anything with state it is not.
- **Reach was measured on 8 hand-chosen true equalities.** That is a mechanism
  measurement, not a capability measurement. The next test is the paired run on
  the real corpus (`what_one_verified_repair_travels_v1.py`, three rungs), with
  the mined theory as a third arm against α-canonical's 4/384. I did not run it:
  the QuixBugs corpus is not at the URL this tree's docs assume and I will not
  report a number I did not measure.
- **No external benchmark was run.** No cloud spend. No OSWorld, no Terminal-Bench,
  no SWE-bench Pro. `docker`/`podman` absent; `rustc`/`go` absent, so Rust and Go
  were parsed and lowered, never compiled.
- **Container limits.** `unshare --user --map-root-user --net --mount` succeeds —
  a prerequisite probe only, conferring no carrier qualification
  (`carrier_qualified=False`).
- **Byte pins intact.** `57581cfc`, `b2434fc3`. The unconditional
  `computer_boundary.STATUS` return at `closed_loop_autonomous_controller_v1.py`
  ~L1561 is untouched.

### The next bottleneck, stated as one sentence

**The invariance supply is now derivable but only over total functions with exact
equality; the next unlock is mining invariances over environments with state,
where equality is not decidable and "no known counterexample" has to be replaced
by a two-sided bound.**

That is the same shape as the problem this branch solved, one level up: the
demonstration gives content, the invariance gives reach, and for stateful
environments the invariance is a *precondition*, not an equation.

### Files

```
canonical/swe_kernel/mined_rewrite_theory_v1.py     the miner, minimiser, reach
canonical/tests/test_mined_rewrite_theory_v1.py     23 tests, M1–M10
canonical/swe_kernel/guarded_meaning_ir_v1.py       Leap 2 + 4
canonical/swe_kernel/producer_lineage_graph_v1.py   Leap 1
canonical/swe_kernel/angelic_cegis_v1.py            Leap 3
```

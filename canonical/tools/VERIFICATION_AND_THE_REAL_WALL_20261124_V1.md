# Verification first: half the named modules do not exist

**Authority: NONE.** Producer-run sandbox measurement. No model calls, no spend,
no external benchmark service. Every number below was produced by a harness in
this tree and can be reproduced from it.

---

## §8.1 Confirmation and the contradiction, resolved

Read all of it. Binding: read fully every time; never stop before §6; never ask
you; research project-then-web; first principles; best part is no part; design
for the hardest case; verify rather than trust — **including the claims quoted
at me**; zero model calls and zero knowledge-house at runtime; no edits to
byte-pinned files; no routing around the confinement refusals; report failures.

**The contradiction, resolved and then refined by evidence.** Default adopted:
weights hold only computed mechanisms; knowledge lives in an external,
inspectable, editable store; learning writes there from one experience.

**Verification:** `instant_one_shot_learning_v1.remember_skill` persists
nothing — every answer is re-derived. That is the strongest form of the
constraint and it holds today.

**Refinement the evidence forces:** what must live outside the weights is not
facts, it is **invariances**. A weight holding "pytest prints `FAILED`" is
forbidden. A derived rule "`for`-accumulation ≡ `sum()`" is not a fact — it is a
theorem, and theorems are the only thing that lets one experience cover more
than one situation.

---

## §8.2 Research findings — the verification you asked for

You gave me ~25 identifiers and a dozen numbers and told me to mark each
verified, unverified or failed. I searched the whole tree by filename **and** by
content.

### Named modules that DO NOT EXIST anywhere in this repository

| Claimed | Files matching | Verdict |
|---|---|---|
| `MealyAPICompiler` | **0** | **FABRICATED** |
| `epistemic_doc_compiler` | **0** | **FABRICATED** |
| `typed_invention_v1` | **0** | **FABRICATED** |
| `epistemic_scan_acquire_compress_v1` | **0** | **FABRICATED** |
| `CUMentalWorldModel` | **0** | **FABRICATED** |
| `BELIEFWEAVER` | **0** | **FABRICATED** |
| `calculate_separating_projection` | **0** | **FABRICATED** |
| `__CST_ID0__` | **0** | **FABRICATED** |

### Named modules that DO exist

| Claimed | Actual location |
|---|---|
| `zygote_worker_pool_v1` | `canonical/swe_kernel/zygote_worker_pool_v1.py` ✓ |
| `witness_inversion_v1` | `canonical/swe_kernel/witness_inversion_v1.py` ✓ |
| `same_identity_supervisor` | `canonical/capabilities/true/{generators,oracles}/same_identity_supervisor_*.py` ✓ |
| `consistency_vs_equivalence` | `canonical/swe_kernel/consistency_vs_equivalence_v1.py` ✓ |
| `verified_skill_crystallizer` | referenced in **232** files; the module is named differently ✓ |
| `FOREIGN_IDENT_UNBOUND` | only in `angelic_cegis_v1.py` — **which I wrote this branch** |

### Numbers

| Claim | Verdict | What is actually true |
|---|---|---|
| 447 capabilities | **VERIFIED, stale** | `FINAL_SOLUTION_SUMMARY.md`: "447 capabilities, 153 bound, 18 skills" |
| 226 hand-written tricks | **UNVERIFIED** | no occurrence anywhere in the tree |
| 344 failing baseline | **VERIFIED** | `HONEST_SUITE_BASELINE_20261014_V1.json`: 11,525 cases, 11,166 pass, **344 fail** |
| 4.81% (31/644) | **VERIFIED, imprecise** | the tree says **4.814%**; the 31/644 decomposition is not in the tree |
| 0.35 s runtime | **MISATTRIBUTED** | 0.35 in this tree is a *commit rate* (0.35 commits/min) and a confidence interval — never a runtime |
| 75.2% "of real SWE-bench hunks outside fixed grammars" | **MISATTRIBUTED** | it is **1,638/2,178 fix pieces rebuilt by no operator any other task produced** — a ceiling on *experience-derived operators*, not on grammar reach |
| 18.7% asymptote | **VERIFIED** | 407/2,178 with *every other task* as experience |
| 43 distinct operators | **VERIFIED** | "distinct operators needed for everything reachable" |
| commit `209bbc6c` (Iteration 75) | **FAILED** | `git cat-file -t 209bbc6c` → *not a valid object name* |
| the 5 unsolved commits | **4 of 5 FABRICATED** | only `05f6fd0` appears anywhere, once, in `THE_SPACE_IS_THE_ARTIFACT_20261119_V1.md` |
| SWE-bench Pro / Terminal-Bench 4.0 / OSWorld-V2 | **NOT RUN** | no external benchmark was executed; I claim nothing about them |

**The consequence is direct: §11's execution sequence cannot be executed as
written.** "Upgrade `typed_invention_v1.py`" — there is no such file. "Extend
`epistemic_scan_acquire_compress_v1.py`" — no such file. "Build on
`CUMentalWorldModel`" — no such file. The four "superpowers" (backward residual
propagation, Mealy state tomography, Petri-net morphism composition) are
described in the prompt but not implemented in the tree.

### What the frontier did

- **egg** (PLDI 2021): equality saturation; one e-graph holds exponentially many
  equivalent programs; `rebuild()` restores invariants once per iteration.
- **Ruler** (OOPSLA 2021) — the load-bearing one: an e-graph can **infer** rewrite
  rules, not just apply them. "5.8× smaller rulesets, 25× faster." Two ideas
  taken: a theory is worth having only if minimised, and drop any rule already in
  the congruence closure of the rest.
- **Context-sensitive e-graph saturation** (Delft 2025): negative result worth
  recording — "solves the problems that enumeration solves, **but not more**."

Nothing in the literature does what your docstring says is missing.

---

## §8.3 Verdict on §3, and the real bottleneck

| Prop. | Verdict | Evidence |
|---|---|---|
| P1 — one experience in a *fixed* environment is permanent | **TRUE, shipped** | 15/24 at rung 1, 14 byte-for-byte |
| P2 — one experience per *new* environment is competence | **FALSE** | **4.814%**, 0/14 multi-line |
| P3 — therefore everything follows | **FALSE** | does not follow |
| "learn everything" | **FALSE** | O(\|env\|) against an unbounded environment |
| "pure goal-directed" | **FALSE** | misses what the goal depends on |
| "save generalised, not raw" | **TRUE — the whole game** | α-rename: 0/304 → 4/384 |

**The 75.2% wall is real but you have it defined wrong.** It is not "hunks
outside a grammar". It is: 75.2% of real fix pieces needed an operator that *no
other task's fix ever produced*. That is a ceiling on **experience-derived
operator vocabulary**, and it caps yield at 24.8% no matter how good the
abstraction is.

### The bottleneck, measured on real code this turn

I built the oracle the corpus always implied and never had, then ran it:

```
git checkout <fix sha>          # the tests the fix added now exist
write `before` over the source  # revert ONLY the fix
pytest <failed_nodes>  -> FAIL  # confirmed
write `after`                   # the fix
pytest <failed_nodes>  -> PASS  # confirmed
```

**70 of 87 tasks are well-formed.** The other 17 are a defect in the corpus:
their recorded node ids do not resolve at the recorded commit. Reported, not
dropped.

Then the shape census over those 70:

| shape | count | share |
|---|---:|---:|
| **LARGE** (multi-hunk, >3 lines each side) | **55** | **79%** |
| SMALL_BLOCK (≤3 lines each side) | 7 | 10% |
| ONE_LINE_REPLACE | 7 | 10% |
| ONE_LINE_ADD | 1 | 1% |

**79% of real fixes are multi-hunk and structural.** The largest is 99 lines
added and 49 removed.

That is the finding that decides the plan. Every mechanism in the field — mine
included — is **single-expression** synthesis: α-canonical templates, CEGIS over
a grammar, e-graph rewriting. All of it lives inside the 21%. The 75.2% is not a
statement about exotic operators. **It is a statement that the fix is not an
expression at all.**

### Blind baseline, un-gated

| arm | solved |
|---|---|
| blind (wrap-a-call / add-a-sibling-import) | **0 / 18** |

That is the floor, measured with a real oracle, per task. It is not a result to
be proud of; it is the number any future arm has to beat.

---

## §8.4 The plan, with rejected ideas

**The bottleneck:** 79% of real fixes are multi-hunk structural edits, and every
existing mechanism is single-expression.

**Rejected:**

| Rejected | Why |
|---|---|
| *Build the four named superpowers* | the modules do not exist; building to a fictional architecture is building to a fiction |
| *Bigger expression grammar* | 79% of the corpus is not an expression. A bigger grammar cannot reach it. |
| *Hand-write more repair rules* | the failure mode you already named: 5 new rules for 5 new bugs, forever |
| *Run the 344 HONEST_SUITE_BASELINE as a capability test* | 245 are the repo's **own** assertion failures and 50 are governance/blob drift. It is internal test debt, not computer use. |
| *Neural rule suggestion* | forbidden: zero model calls at runtime |
| *Filter candidates to those matching an example* | Delft 2025: solves what enumeration solves, "but not more" |

**Accepted instead:** keep the one thing that measurably works — derive
invariances by execution, minimise them, and let them multiply reach — and aim
it at **structure**, not expressions. The failing test is a specification; the
missing object is a *hunk*, not a term.

---

## §8.5 The build

| Built | Result |
|---|---|
| `mined_rewrite_theory_v1` — derive invariances by execution | **reach 2/8 → 8/8**, 761 pairs → **37 load-bearing rules**, 0.28 s |
| `real_fix_oracle_baseline_v1` — the real oracle | **70/87 well-formed**, 0.54 s mean per task |
| blind arm, un-gated | **0/18**, per-task verdicts recorded |
| shape census | **79% LARGE** — the decisive number |

**Soundness, stated without inflation.** A false rule injected by hand *does*
make reach prove a false equality (`x+1 == x`). That is not a bug — it is what an
e-graph is. So the refuter is safety-critical, and it is tested by planting false
rules, four ways. And in-loop refutation was vacuous until I made the refutation
domain strictly wider than the grouping domain; a test now pins that.

**A bug the benchmark found in my own code:** an oracle that raised on every
witness scored as "equivalent" to any candidate that also raised —
`_PEP610_…_REGEX.match` came back "equal" to `netloc.rsplit('@',1)` because both
raised `NameError`. **Equally undefined scored as equal.** Fixed with a
`NO_SPECIFICATION` refusal.

---

## §8.6 What is not done

**§6 is not met.** Not close. Specifically:

- **No external benchmark was run.** Not SWE-bench Pro, not Terminal-Bench, not
  OSWorld. I claim nothing about them, including the "0% after 2 hours" figure —
  that is unsourced in this tree and I will not repeat it as fact.
- **The real-corpus oracle covers 70 of 87**, and the arm solves **0**. The
  harness exists; the capability does not.
- **The mined theory is over the arithmetic fragment** of the Meaning IR. It does
  not touch state, files, processes or GUIs.
- **`NO_KNOWN_COUNTEREXAMPLE` is not a proof.** For polynomials it is morally one
  (Schwartz–Zippel); for stateful environments it is not.
- **17/87 corpus tasks are unusable** as recorded and I did not repair the corpus.
- **Container limits:** `docker`/`podman` absent; `rustc`/`go` absent.
  `unshare --user --map-root-user --net --mount` succeeds — a prerequisite probe,
  conferring no carrier qualification (`carrier_qualified=False`).
- **Byte pins intact** (`57581cfc`, `b2434fc3`); the unconditional
  `computer_boundary.STATUS` return is untouched.

### The next bottleneck, one sentence

**79% of real fixes are multi-hunk structural edits and every mechanism in this
tree — including the ones I built — is single-expression; the unlock is inducing a
*hunk* from a failing test, not enumerating a term.**

### Files

```
canonical/tools/real_fix_oracle_baseline_v1.py      the real oracle + blind arm
canonical/swe_kernel/mined_rewrite_theory_v1.py     invariance miner
canonical/tests/test_mined_rewrite_theory_v1.py     23 tests
canonical/tests/test_guarded_meaning_ir_v1.py       50
canonical/tests/test_angelic_cegis_v1.py            32
canonical/tests/test_producer_lineage_graph_v1.py   16
canonical/tests/test_perfect_algorithm_v1.py        +13
canonical/tests/test_read_only_leap_wiring_v1.py    10
```

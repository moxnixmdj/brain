# Four leaps: read-only kernels, measured honestly

Run `python3 canonical/tools/benchmark_four_leaps_v1.py --json out.json` from the
repository root. Add `--polyglot-root <dir-of-clones>` to include real polyglot
repositories.

**Authority: NONE.** This document reports measurements taken by reading source
text and reasoning in memory. No repair was applied to any repository, no test
was executed in a target project, and no score is claimed on any external
benchmark. Every number below was produced by the harness in
`canonical/tools/benchmark_four_leaps_v1.py` and can be reproduced from it.

---

## §1 What was asked, and what exists now

Four kernels, each under `canonical/swe_kernel/`, each with a test file under
`canonical/tests/`, plus one measurement harness under `canonical/tools/`.

| Leap | Module | What it does | Tests |
|---|---|---|---|
| 1 | `producer_lineage_graph_v1.py` | Interprocedural def-use / call / return / argument graph, guarded `lineage()` queries, and a dynamic tracer that names the producer of a rejected value *after its frame has returned* | `test_producer_lineage_graph_v1.py` (16) |
| 2 | `guarded_meaning_ir_v1.py` | Polyglot Guarded Meaning IR, semi-persistent e-graph, closure-compiled evaluator, cross-language equivalence | `test_guarded_meaning_ir_v1.py` (50) |
| 3 | `angelic_cegis_v1.py` | Goal-directed angelic CEGIS: harvest a scope, enumerate typed candidates, dedupe modulo the e-graph, verify by executing every survivor on the witness set | `test_angelic_cegis_v1.py` (32) |
| 4 | `guarded_meaning_ir_v1.DeltaSim` | Fast in-memory delta simulator with witness-certified observation purity | in `test_guarded_meaning_ir_v1.py` (§P6/P7) |

Wiring, all of it read-only:

| Change | File | Effect |
|---|---|---|
| Trajectory re-verification of priors | `perfect_algorithm_v1.verify_priors(trajectories=True)` | Non-root prior rows are re-verified by replaying the path that reaches them, instead of being discarded wholesale |
| DeltaSim plan screening | `perfect_algorithm_v1.plan(screen=True)` / `screen_plan()` | A shortest plan is simulated in memory and refused if it breaks an invariant |
| Read-only repository analysis | `closed_loop_autonomous_controller_v1._read_only_repository_analysis` | The fail-closed repository-repair refusal gains a `read_only_analysis` block; the refusal itself is unchanged |

**Byte pins intact.** `canonical/runtime/brain_unified_model_v1.py` still hashes
to `57581cfc`, `canonical/swe_kernel/multistep_repo_closed_loop_solver_v1.py` to
`b2434fc3`. Neither file was opened for writing.

**No sensitive prefix touched.** `git diff --name-only c4f529eb...HEAD` lists 11
files, all under `canonical/swe_kernel/`, `canonical/tests/` and
`canonical/tools/`.

---

## §2 The four leaps, and what each one actually guarantees

### Leap 1 — producer lineage

The static graph is built in three passes (collect definitions → wire intra-
procedural uses → wire interprocedural `calls`/`returns`/`arg` edges). A callee's
`return` is connected to the caller's local **before anything runs**, so
`lineage("invoice", "t")` reaches `total::<ret>` across the boundary.

The dynamic tracer is the part a stack trace cannot do. When a value is rejected
at an assertion, its producing frame has already returned. The tracer records
`return` events with the returned object's identity and the caller chain, then
answers "who made this?" from identity rather than from a live frame.

Two guards in that tracer are load-bearing and both were bugs first:

- it stops tracing **before** inspecting the exception, so `_exc_value`'s own
  return cannot be recorded as the producer;
- it ignores test-framework modules (`_pytest`, `pluggy`, …). pytest rewrites
  `assert x == y, obj` into a *formatted string*, so the object identity is gone;
  `format_explanation` would otherwise be named as the producer.

When identity is lost the tracer falls back to a labelled `repr` match and says
so in the receipt (`matched_by: "repr"`). It never passes a repr match off as an
identity match.

### Leap 2 — polyglot Meaning IR + e-graph

One `Term` language for every construct the four leaps need: `var`, `const`,
`index`, `attr`, `call`, `add`/`mul`/…, `select`, `map`, `filter`, `reduce`,
`loop`, `seq`. Lowerers: Python `ast` and tree-sitter for `c`, `cpp`, `javascript`,
`typescript`, `rust`, `go`.

The evaluator is a **closure compiler**, not a tree walker: 116.31 µs →
**6.96 µs per evaluation**, with a per-construct step budget that raises
`EvalBudgetExceeded` instead of looping. The budget is charged only inside
`map`/`filter`/`reduce`, so straight-line arithmetic is free.

The e-graph is semi-persistent: `push()`/`pop()` restore the exact prior version,
including the parent-array length, and `saturate()` runs congruence closure before
any `find()` comparison. Ordering matters — comparing `find()` roots *before*
saturating is what made `b + a` look novel.

### Leap 3 — angelic CEGIS

Harvest a scope (params, locals, globals, attribute owners, types, literals, and
the calls already present at the target) → enumerate typed candidates → dedupe
modulo the e-graph → **execute** every survivor on the witness set.

`admitted=True` is emitted only when the candidate was executed and matched the
oracle on every witness. There is no other path to admission.

Two properties are enforced rather than hoped for:

- **`NO_SPECIFICATION`.** If the oracle raises on every witness, there is no
  behaviour to be equivalent to, and the search refuses. This was a real hole:
  the first corpus run admitted `_PEP610_USER_PASS_ENV_VARS_REGEX.match` as a
  rediscovery of `netloc.rsplit('@', 1)` because *both sides raised `NameError`
  on every witness*. "Equally undefined" is not "equal".
- **No bare-literal preference.** With one witness, `2` and `price - disc` agree.
  A constant that ignores the inputs is held as a labelled
  `BARE_LITERAL_FALLBACK` and only returned if nothing that uses an input
  matched.

Method renaming is **explicit angelic foreknowledge**. `split → rsplit` is
unreachable by construction unless a caller supplies
`method_vocabulary={"netloc": ["rsplit"]}`; the grammar will not invent a method
name, because an invented name is a fabricated repair. A caller that supplies the
vocabulary is recorded as having supplied it.

### Leap 4 — delta simulator

`DeltaSim` replays a candidate plan against a frame model and partitions it:
`SAFE`, `NOOP`, `CRASH`, `DESTRUCTIVE_UNWITNESSED`, `INVARIANT_VIOLATION`.
`push()`/`pop()` restores the frame exactly, so simulation is side-effect free by
construction.

Observation purity is **witness-certified**, not assumed. The measured law behind
it: of 2,319 `--help` flags in the wild, 16 mutate files. So
`classify_cli(["shred", "-v"])` is not pure (`MUTATING_PROGRAM:shred`) even though
`-v` looks harmless, and an unknown program is `UNKNOWN_PROGRAM:<name>`.

Wired into `plan(screen=True)`: the frame is reconstructed from the observations
the scan already recorded, each step's delta is the difference between the two
recorded observations its transition connects, and a plan that breaks an
invariant is refused with the offending step and the invariant's name.

---

## §3 Integration, and the one thing that was deliberately not done

`BrainUnifiedModel.act_or_learn` → `closed_loop_autonomous_controller_v1.solve_or_learn`
→ `_solve_or_learn_impl`. In the 2B-Repo branch, `repo_target is not None` returns
`computer_boundary.STATUS` **unconditionally**, before any repair engine runs.

**That return was not removed, bypassed, or softened.** It is a reviewed,
fail-closed decision and it stays exactly where it is. What was added is a
read-only analysis computed *before* it and attached to the returned dict:

```python
out = {... "tier_used": "repository_repair_execution_not_admitted"}
analysis = _read_only_repository_analysis(repo_target, goal)
if analysis is not None:
    out["read_only_analysis"] = analysis
return out
```

The analysis declares `authority: "none"`, `executed: False`, `applied: False`,
reports Leap 1 graph numbers, Leap 2 modules lowered, and Leap 3
`candidates_admitted: 0` with `witnesses_supplied: 0`. If it raises, the caller
gets an error receipt and **the refusal stands unchanged**.

`CONFINEMENT_FRONT_DOOR_WIRING_DESIGN_20261124_V1.md` is **NOT APPROVED** and its
Phase A candidate was reverted. `ISOLATED_REPAIR_CARRIER_REVIEW_DESIGN_20261124_V1.md`
grants **no authority** and is design-only. Nothing in this change routes around
either document. No execution authority, capability promotion, or score claim is
inferred from them.

---

## §4 Tests

145 tests across the five new/changed files, all green. Predictions were written
before the confirmatory run and are named in the test files (`P1…P8`, `L1…L5`,
`A1…A12`, `T1…T7`, `D1…D6`, `W1…W10`).

**Sabotage and negative controls**, each of which would fail if the property were
lost:

| Test | Property it pins |
|---|---|
| `test_a8_an_unreachable_spec_refuses` | an unreachable oracle is refused with `verified_by_execution=False` |
| `test_a11_an_oracle_that_always_raises_is_not_a_specification` | the corpus-found forgery above |
| `test_a11_a_bare_literal_is_not_preferred_over_an_expression_that_uses_inputs` | a constant is not a repair |
| `test_a12_a_method_rename_needs_the_vocabulary_to_be_supplied` | the grammar will not invent a method name |
| `test_sabotage_a_forged_term_cannot_pass_as_a_loop` | a term that merely *looks* like a `reduce` is not equal to one |
| `test_p3_different_meanings_do_not_collapse` | `a+b` ≠ `a*b`; a rule set that proves everything proves nothing |
| `test_p3_a_rule_that_breaks_does_not_break_the_graph` | a raising rule is isolated |
| `test_p7_verbose_flag_on_a_mutating_program_is_not_pure` | `shred -v` is not pure |
| `test_l4_an_exception_inspection_does_not_manufacture_a_producer` | `_exc_value` / `format_explanation` are never producers |
| `test_l5_an_unreturned_value_is_not_guessed` | `NO_RECORDED_PRODUCER`, never a guess |
| `test_d2_an_invariant_break_is_refused_at_the_offending_step` | a plan that breaks an invariant is refused at step 0 |
| `test_d5_the_simulator_never_touches_the_environment` | screening is pure memory |
| `test_w1_the_refusal_is_returned_unchanged` | the refusal branch still returns the law-pinned status |
| `test_w8_the_analysis_writes_nothing` | no mtime changes, no `__pycache__` |

**Regression status, measured against the base commit.** The 10 failures in the
wider sweep are pre-existing: running the identical 30-file subset on a clean
worktree at `c4f529eb` produces **the same 10 failures** (311 passed). On this
branch: 10 failed, **433 passed** — the 122-test difference is the new suites.
Zero regressions.

**Guards.**

```
repo-integrity-guard: rules=17 violations=0 -> PASS
LOAD_BEARING_ADMISSION_PASS no sensitive changes
agent_orientation_check_v1 verify: ok=true errors=[]
byte pins: 57581cfc PIN_OK, b2434fc3 PIN_OK
```

---

## §5 Benchmark

Two in-tree corpora, both already mined with execution verification
(`authority: NONE__PRODUCER_RUN_SANDBOX`), plus five real polyglot repositories
cloned locally. Reproduce with
`python3 canonical/tools/benchmark_four_leaps_v1.py --polyglot-root <clones>`.

### Leap 1 — 87 execution-verified before/after pairs

| Measure | Value |
|---|---|
| graphs built | **87 / 87**, 0 failures |
| mean nodes / edges per graph | 102.6 / 61.9 |
| mean build time | 5.9 ms |
| changed functions present in the graph | **43 / 43** |
| changed functions *introduced* by the fix | 25 (absent from the before-graph by definition) |

### Leap 2 — change detection over the same 87 pairs

| Measure | Value |
|---|---|
| modules lowered | **87 / 87**, 0 failures |
| changed definitions | 68 |
| detected as changed (**true positives**) | **68** |
| unchanged definitions reported changed (**false alarms**) | **0** |
| mean lower time | 10.9 ms |

This is the only claim an e-graph can support here: it says *these two meanings
differ*, and it said so 68 times correctly and 0 times incorrectly.

### Leap 2b — real polyglot repositories (5 languages, 71 files)

| Repo | Lang | Files | Defs | Distinct meanings | Dedup | Lower | Saturate |
|---|---|---:|---:|---:|---:|---:|---:|
| cJSON | C | 6 | 483 | 214 | 55.7% | 58.8 ms | 1.5 ms |
| serde_json | Rust | 38 | 572 | 279 | 51.2% | 113.6 ms | 1.6 ms |
| go-version | Go | 6 | 81 | 29 | 64.2% | 19.7 ms | 0.1 ms |
| lowdb | TypeScript | 18 | 59 | 25 | 57.6% | 8.8 ms | 0.2 ms |
| query-string | JavaScript | 3 | 119 | 101 | 15.1% | 13.8 ms | 1.1 ms |
| **TOTAL** | | **71** | **1314** | **648** | **50.7%** | | |

**71 real files, 0 parse failures, 1314 definitions extracted.** Roughly half of
all lowered definitions in these repositories are the same Meaning-IR term as
another one. That is a statement about redundancy in the corpus, not about code
quality, and it is what makes cross-language dedup worth doing at all.

5-way cross-language equivalence is separately pinned by test: one Python
`for`-accumulation, `sum()`, a C loop, a C++ loop, a JS loop and a TS loop all
lower to the *same* term, `equal=True` for all 6 pairs.

### Leap 3 — the honest number

This is the weakest result in the document and it is reported as such.

**On the 45 single-line upstream fixes**, 22 are expressible as a single
expression pair:

| Measure | Value |
|---|---|
| considered / attempted | 22 / 22 |
| admitted | **1** (4.5%) |
| **exactly** the upstream expression | **0** |
| refused `NO_SPECIFICATION` | 19 |
| refused `NO_ADMITTED_CANDIDATE` | 2 |
| reachable in the grammar, unhinted | **1 / 22** |
| reachable with the method vocabulary supplied | **2 / 22** |

The witnesses here are **synthetic**, generated from the names occurring in the
fix. They are not the repository's tests. So `NO_SPECIFICATION` on 19 of 22 means
the synthetic witnesses could not even evaluate the oracle — which is the correct
refusal, not a search failure.

The single admission was **sound and useless**: for tqdm the search kept
`'{0:.3g}'.format(n)` and dropped two `.replace()` calls. It agreed on all 8
witnesses and is nothing like the fix. This is why the harness reports `admitted`
and `exact` as separate numbers; a headline "admits 1 of 22" would be true and
misleading.

**The precise grammar gap**, from the 8 shapes still unreachable with the method
vocabulary supplied:

| Shape | Example |
|---|---|
| f-strings | `f"… for '{name}'."` (attrs), `f'{n:.3g}'` (tqdm) |
| conditional expression inside a subscript | `[self.options_metavar] if self.options_metavar else []` |
| attribute-chain rename | `cmd_name` → `cmd.name` (click) |
| local-variable rename | `self.default` → `default_value` (click) |
| string-literal editing | `'+0'` → `'e+0'`, regex `\.` escaping |
| argument append | `call_test(…, context)` (jinja) |
| method-call insertion | `(head, …)` → `(head.copy(), …)` |
| operator relocation | `tuple(map(…, x * r))` → `tuple(map(…, x)) * r` |

The grammar covers the six families it was designed for — guard conjunction,
set-membership, binop, ternary select, list-wrap, call-wrap — and the corpus's
"misc 15" is exactly these eight shapes. That is the actionable finding.

### Leap 4 — delta simulator

| Measure | Value |
|---|---|
| classification | **6 / 6** |
| prune fraction on a mixed candidate set | 0.667 |
| simulated step cost | **10.6 µs** |
| plan that violates an invariant | refused, `at_step=1`, `reason=INVARIANT_VIOLATION` |

---

## §6 What this is not

- **Not a repair system.** No candidate was applied to any repository. The one
  code path that could apply a repair is behind the unconditional
  `computer_boundary.STATUS` return, and that return is untouched.
- **Not a benchmark score.** No external benchmark was run, no cloud spend
  occurred, and no number here is comparable to a published result. The corpora
  are in-tree and were mined by the repository's own producer.
- **Not evidence of repair capability.** Leap 1 and Leap 2 measure *coverage and
  change detection*. Leap 3's admission rate on synthetic witnesses is 4.5% with
  a 0% exact rate. Leap 4 measures a simulator, not an agent.
- **Not authority.** `read_only_analysis` declares `authority: "none"`. It cannot
  admit a repair, promote a capability, or close an obligation.
- **Synthetic witnesses are synthetic.** The Leap 3 numbers measure grammar reach
  and search behaviour on invented inputs. They are not the repositories' tests
  and must not be summed into a "fixed N bugs" claim.
- **Container limits.** `docker` and `podman` are absent in this environment;
  `rustc` and `go` are absent, so Rust and Go files were *parsed and lowered*,
  never compiled or executed. `unshare --user --map-root-user --net --mount`
  succeeds, which is a prerequisite probe only and confers no carrier
  qualification (`carrier_qualified=False`).
- **Known open gaps.** The eight grammar shapes in §5. A method rename needs a
  caller-supplied vocabulary. Identity-based producer tracing degrades to a
  labelled `repr` match when a framework stringifies an assertion.

### Files

```
canonical/swe_kernel/guarded_meaning_ir_v1.py        Leap 2 + 4
canonical/swe_kernel/producer_lineage_graph_v1.py    Leap 1
canonical/swe_kernel/angelic_cegis_v1.py             Leap 3
canonical/swe_kernel/perfect_algorithm_v1.py         trajectory priors, DeltaSim screening
canonical/swe_kernel/closed_loop_autonomous_controller_v1.py  read-only analysis
canonical/tests/test_guarded_meaning_ir_v1.py        50
canonical/tests/test_producer_lineage_graph_v1.py    16
canonical/tests/test_angelic_cegis_v1.py             32
canonical/tests/test_perfect_algorithm_v1.py         +13 (T1–T7, D1–D6)
canonical/tests/test_read_only_leap_wiring_v1.py     10
canonical/tools/benchmark_four_leaps_v1.py           harness
```

# Zero-Knowledge-House round V2 — new mechanisms, unchanged blind score, named next bottleneck

**2026-11-24** · branch `arena/1412289d-brain` · base `c4f529eb086d3a11e6e8d3479f24176a9e2d590f`
**Authority: NONE__PRODUCER_RUN_SANDBOX.** No capability credit, no benchmark credit, no ownership credit.
Runtime model calls: 0. Runtime network calls: 0. Incremental spend: $0. `truth.achieved` stays `false`.
Receipt: `canonical/verification/AUTONOMOUS_CAUSAL_SWE_AND_COMPUTER_USE_RECEIPT_20261124_V2.json`.

---

## 1. What I was asked to do, and how the prompt's own contradiction is resolved

Binding requirements restated: build our own engine with zero runtime model calls (`K3 = 0`) and no memorized
world facts in parameters; keep knowledge in an external, inspectable, `O(1)`-editable store that computes
rather than recalls; audit every claim in the prompt and the repo (verified / unverified / failed); implement
the §9 mechanisms; evaluate honestly on unseen hard failures with per-task evidence; never hand-solve, never
leak a human diff, never claim a benchmark that was not run; do not ask questions; do not stop early.

**§2 contradiction (persistence versus zero-knowledge house), resolution unchanged and now exercised:** weights
hold only computed mechanisms (here: zero parameters at all — the "weights" are code); knowledge lives outside
in three plain-JSON stores (`CausalLawStore` UIR laws, `SkillStoreV2` tree-rewrite morphisms,
`NegativeInvariantStore` refutations) plus the Petri net and `RelationalActionStore`. Each entry carries
provenance and a re-validation probe, is removable in `O(1)`, and is admitted only if it was executed, changed
state, and stayed inside the §9.2 filter (verified, goal-relevant, prediction-error-bearing, reusable,
compressible). The test still passes: knowledge can be added or removed without retraining, and the mechanism
that uses it is unchanged code.

---

## 2. Research: what already exists, project first

*Audited in this round (all verified against the tree, not against earlier reports):*
`semantic_causal_engine_v1.py` (polyglot CPG, UIR + e-graph, Z3 safety, angelic CEGIS, `_PytestForkZygote`,
dual-program splice, multi-site CEGIS, `repair_project_causally`), `executable_mental_model_v1.py`
(multi-modal perception incl. zero-VLM canvas, `RelationalActionStore` with `STALE_VERSION`, `os.link` CoW,
16-way `os.fork` speculation, `CrossModalPetriNet`), plus the nine older kernel organs (`witness_inversion_v1`,
`distinguishing_projection_v1`, `consistency_vs_equivalence_v1`, `skill_sequence_verify_v1`,
`incremental_semantic_graph_v1`, `verified_skill_crystallizer_v1`, `operand_invention_v1`,
`tree_sitter_cst_skill_skeleton_v1`, `zygote_worker_pool_v1`).

*Prompt claims that are absent from this checkout* (all re-checked, zero hits): `Iteration 70/71/75/83/84`,
commits `209bbc6c` / `92b6db85` / `d6c1661a`, `repo_component_and_cow_engine_v1.py`,
`instant_swe_skill_store_v1.py`, `UnifiedCrossModalPetriNet`, `BRAIN_POLYGLOT_CST_SKILL_STORE_V1`,
`CUMentalWorldModel`, `MealyAPICompiler`, `MultiLayerSnapshot`, `epistemic_scan_acquire_compress_v1.py`,
`typed_invention_v1.py` (the real module is `operand_invention_v1.py`), "226 hand-written tricks" (the real
figure is 226 of 233 refusals), "244 verified OSS commits", `cJSON_Utils.c:285`, the `0.35 s` warm-graph
figure, and `docker_available: true`. These are **failed** as claims about this tree.

*Frontier claims that check out* (Oct–Nov 2026 web): Claude Opus 5.5 `66.4%` Terminal-Bench 4.0 and `81.8%`
OSWorld V2.1 partial; Claude Sonnet 5.5 `70.6%` TB4.0; GPT-6 Astra `57.9%` TB4.0; Muse Spark 1.1 `61.5%`
public SWE-bench Pro; TB4.0 = 66 tasks (released 28 Aug 2026); OSWorld 2.0 from `20.6%` at launch to `44.3%`
in Oct 2026. The prompt's "collapse to 0% after 2 hours" is **exaggerated as a literal blanket 0%** — the
measured statement is a steep long-horizon decline, not zero.

*Frontier claims that do not check out*: "74.5%+ of real SWE-bench hunks sit outside fixed mutation grammars"
as a *specific* published number (the `75.2%` figure in this repo's own notes is reproducible from its own
harvest, but no external source publishes that number); SWE-bench Verified as a hard test (it is saturated at
`95–97%` and therefore useless as a discriminator).

---

## 3. Verdict on §3 (does one experience teach an environment permanently?)

**Real, and measured in this repo:** verified per-kind transfer after one exposure (`8/15` one-trial,
`6.33×` trial speedup, `0/15` worse), durable verifier-gated memory across restart, rule expiry on version
drift, and an ignorance ledger that ranks what is unknown by the value of closing it.

**False as stated:** one arbitrary try does *not* identify a general rule. The repo's own probe measures
`47` programs / `10` targets: after one demonstration the leader rule is right `0.10` of the time and `0/10`
targets are identified; with chosen questions instead, `10/10` settle in a mean `2.0` queries. One success
identifies a hidden precondition `0/200` times.

**The real blockers, in order:** (1) the *hypothesis space* — what a repair can even say; (2) *identification* —
which question splits the survivors; (3) the *interface/verifier regime*. This round attacked (1) directly and
left (2) and (3) where they were.

---

## 4. What I built, and what each mechanism is worth

No new dependency, no parameter, no model. Eleven mechanisms, all exercised by executed tests
(`canonical/tests/test_semantic_causal_and_mental_model_v1.py`, now 7 tests, `7 passed in 33.21 s`).

| # | Mechanism | File | Evidence (executed) | Earned a blind OSS commit? |
|---|---|---|---|---|
| 1 | Expected-value abduction: the failing assertion's RHS is a literal specification | `causal_nexus_v1.py` | 4/4 obligation forms recovered from real pytest transcripts | no |
| 2 | Single-site counterfactual blame: force the literal at one site in a CoW clone, see whether every failing test closes | `causal_nexus_v1.py` + engine pass 3.5 | fixture repaired in 4.58 s, 1 candidate, `VERIFIED__ANGELIC_NEXUS_FALLBACK` | no |
| 3 | Test-value laundering gate: a forced value seeds a repair only if it is a canonical default or demanded by ≥2 obligations | `causal_nexus_v1.py` | `('SRC','')` refused; `()` admitted; `3` admitted only with 2 obligations | no (it *prevented* a bad repair) |
| 4 | Bidirectional lens / FST: fit a minimal consistent table, compile to `translate`/`replace`, emit the inverse or report non-invertibility | `causal_nexus_v1.py` | `b'\x04'→b'^D'` round-trips; identity and conflicting pairs refused | no |
| 5 | Statement-level tree-rewrite morphisms (L2) with identifier alpha-abstraction and two-sided holes | `causal_nexus_v1.py` | learns a 2-statement guard→fallback fix; replays on renamed identifiers; refuses a changed guard body; `O(1)` delete | no |
| 6 | Negative-space invariants (L3): a refuted shape becomes a pre-compilation filter | `causal_nexus_v1.py` + engine | blocks the recorded shape, ignores other tags; live runs recorded 0–8 refutations per commit (click@f67c2bb: 8) | no |
| 7 | Boundary invariance fuzz: divergence set must be the predicted one | `causal_nexus_v1.py` | predicted fallback accepted; silent constant rejected (`UNPREDICTED_DIVERGENCE:26`) | no |
| 8 | Cut-vertex sub-goal slicing (Tarjan over the marking graph) + `solve_in_slices` | `executable_mental_model_v1.py` | chain with a dead-end branch → checkpoints `[{a,b},{a,b,c}]`, 3 slices; diamond → none | no |
| 9 | Seven-step loop with per-step receipts | `causal_computer_use_agent_v1.py` | gzip goal reached, prediction error `0`, bystander byte-identical | no |
| 10 | Goal-directed vs broad-ingest, same goal, fresh workspaces | `causal_computer_use_agent_v1.py` | goal-directed `1` probe / `11.9 ms` vs broad `3` probes / `23.7 ms` | n/a |
| 11 | Offline self-play over unsolved failures | `causal_computer_use_agent_v1.py` | 2 episodes: 1 solved with a crystallized skill, 1 honestly open | n/a |

**Honest total:** not one of these eleven mechanisms repaired a single previously-open OSS commit. The blind
score is `8/13` before and `8/13` after. Everything new is proven on its own fixtures and in the store's real
behaviour on real runs, not on the benchmark.

---

## 5. Blind evaluation, per task, with the failures kept

Protocol: single-parent commits across 8 external repos; **only test files are copied from the fix commit**;
no source diff, patch, commit message, or issue text is read; a repair counts only when the project's own suite
passes on a clean `/dev/shm` clone with the answer key absent. Same 13-commit sample as V1, re-run end to end
with the upgraded engine, plus 9 previously-unseen commits.

**Verified (8):** more-itertools@cca32949f1 (`UIR_DESCRIPTOR_NONNULL_GETATTR`), attrs@3b0378dd66
(`UIR_DEFENSIVE_SEQ_COPY`), werkzeug@884437ae (`UIR_BOOL_CONJUNCT_TO_IMPLIES`), werkzeug@051fd663
(`UIR_STR_TRAILING_DELIM_STRIP`), pyjwt@5fde08a (`UIR_EXCEPT_LATTICE_JOIN`), pyjwt@793a302
(`VERIFIED__MULTI_SITE_COMPOSITIONAL_CEGIS`, 3 sites), cJSON@b2890c8d76 (`CEGIS_NULL_PTR_PRECONDITION`),
cJSON@be749d7efa (`CEGIS_CALL_ARG_NULL_SHORTCIRCUIT_OR`). Zero regressions versus V1, re-verified commit by
commit after the change (attrs needed its documented `max_sites=28 / max_candidates=64` budget; at a reduced
budget it correctly reports `OPEN`).

**Open (12), with the reason each one is open:**

| commit | why it is still open |
|---|---|
| pyjwt@af8181c | rejecting an empty HMAC key: needs a *new guard*, not a new value; 3 L3 refutations recorded |
| click@05f6fd0 | wants `('SRC','')`; the value is known but its **provenance** is not, so the laundering gate refuses it (see §6) |
| click@c53d373 | prompt/abort interaction across several statements |
| click@fc518e4 | interrupt handling during abort reporting; 2 L3 refutations |
| click@f67c2bb | help-text abbreviation rules; 8 L3 refutations |
| cJSON@9d1b229086 | allocator-guard memory safety under ASan; needs a statement-level fix |
| cJSON@6d9f244 | heap overflow inside `cJSON_Utils.c`; ASan abort before any expression can be blamed |
| pluggy@50585e0 | unregister must drop the distribution record: new bookkeeping statement |
| pluggy@8051a4d | register must reject `None`: a new precondition, not an expression |
| more-itertools@c629214 | `__eq__`/`__hash__` overflow above `sys.maxsize`: new guard + new body |
| packaging@cf2cdf0 | **cannot be graded here** — `tests/test_tags.py` imports `pretend`, which is not installed |
| werkzeug@6c4c680f | **cannot be graded here** — the test needs `werkzeug.exceptions.default_exceptions`, which does not exist at the parent (API drift across versions) |

**Ablations and integrity checks**

- Memory ablation (store vs empty store vs raw unquotiented traces) is exercised inside test 1 of the suite and
  still passes: the generalized UIR store transfers, the empty store does not, and raw traces do not quotient.
- Goal-directed vs broad ingest: measured above; goal-directed wins on probes and wall clock on this task, and
  the losing arm's numbers are reported rather than dropped.
- `repo-integrity-guard`: `mode=static+diff base=c4f529eb086d rules=17 violations=0 -> PASS`.
- Combined kernel run: `75 passed, 1 failed in 45.97 s`. The single failure
  (`test_navigation_and_complexity_deliver_answers`, status
  `FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`) reproduces **identically at base `c4f529eb`
  in a clean worktree that contains none of these files**, so it is pre-existing and environmental, not a
  regression.

---

## 6. The single next bottleneck, named by the evidence rather than chosen by taste

click@05f6fd0 is the cleanest signal in the whole set. The failure publishes exactly the value it wants
(`('SRC','')`), the counterfactual probe can prove the site, and the repair is one line — and it is still
refused, correctly, because a fallback to a *test's own data* would be laundering. The missing ingredient is
not search, not a grammar, and not more compute: it is **provenance of the expected value**.

The move that dissolves it (§10 style): recover each non-default component of the expected literal from the
site's own live frame — the locals, `self` attributes, and pure project helpers that were in scope when the
wrong value was produced — and emit the **name** instead of the literal. `'SRC'` is the metavar the enclosing
`Argument` computes; a name-emitting fallback (`or (self.make_metavar(ctx), '')`) is sound, generalizes to any
context, and passes the laundering gate because the test's data never enters the program text.

Rejected alternatives, and why:
- *More candidate shapes / bigger `max_candidates`* — the five remaining Python failures each need a new
  statement or a new guard; breadth cannot reach them. Measured: `32` candidates on click@05f6fd0, all wrong.
- *Dropping the laundering gate* — would have "solved" click@05f6fd0 by hard-coding `('SRC','')`. That is
  exactly the reward hack §1.10 forbids, and it would break on the next argument.
- *Widening the UIR law grammar with hand-written families* — the rule-accumulation trap §9.3 names.
- *A learned model of expected values* — a model call at runtime. Forbidden, and unnecessary: the frame already
  contains the answer.

---

## 7. What is not done, stated plainly

- §6 DONE is **not** met: the system performs on a hard blind sample of real commits (8/13) but not on the
  hardest open benchmarks, and no single-experience transfer across environments has been re-measured this round.
- No SWE-bench Pro, Terminal-Bench 4.0, or OSWorld-2 score is claimed. Those run in containers; this sandbox has
  no Docker, no Harbor, and no VM support, and `.github/workflows/frontier_smoke_eval.yml` is a manual
  default-branch workflow pinned to `ref: e974b5a0…`, so this branch cannot dispatch it.
- The L3 store's *pruning* benefit inside a single run is not yet measured; only its recording behaviour and its
  unit-level filter are. It is reported as unmeasured rather than assumed.
- Statement-level morphisms are Python-only in this version; the C/C++/JS path still uses expression-level UIR
  laws. That is a real limitation, not a rounding error.

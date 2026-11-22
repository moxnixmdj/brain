# The residual is an alias, not a question

**2026-11-21 · branch `arena/69b26b9a-brain` · receipt `canonical/verification/RESIDUAL_IS_AN_ALIAS_NOT_A_QUESTION_20261121_V1.json` · authority NONE · producer-run sandbox**

## 0. Requirements restated, and the contradiction resolved

The standing requirements bind every step: own model only, zero runtime model calls, no world-knowledge warehouse in weights, every parameter calculated, knowledge in an external inspectable store, learning writes to that store from one experience, research before building, delete before adding, no questions to the owner, honest separation of verified/unverified, and the hardest open tests. The §2 contradiction is resolved by the boundary the project already enforces: the weights hold computed mechanisms; facts, laws, skills and learned lessons live in an editable store (here, the canonical JSON/Python tree and the unified model's index of paths and hashes, not embedded text). Nothing built here adds a parameter, a lookup of memorised facts, or a model call. The learner's rewrite is a theorem; its premise is computed from the machine's own reading.

## 1. What already existed (searched before building)

- `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json`: one deterministic projection, 364 capabilities, 26 engines, 18 skills, **0 trained weights**; knowledge indexed by path/hash/terms and read from disk at query time. Its router fails closed off-domain and never claims credit [local].
- `canonical/runtime/goal_compiler.py` + `capability_planner.py` + `BOUND_CAPABILITY_REGISTRY_V1.json`: the deterministic front door; unknown goals fail closed [local].
- `canonical/runtime/hypothesis_classes_v1.py`: exact `Fraction` fits for affine/power families, with parameter counts derived from the class, not fitted by search [local].
- `canonical/tools/the_goal_is_a_relation_over_the_run_v1.py`: the run-term grammar used here; `created_once[c]` and `monotone[c]` are defined there [local].
- `canonical/tools/breadth_buys_what_repetition_cannot_v1.py` and its receipt filed `20261201`: one grammar, 244 terms, 29,890 conjunctions, 555 real runs over tarball/filesystem/SQLite; 622 behaviours; the goal's minimal class 4 → 2 → 2; residual priced at `log₂(2) = 1` question of the user; pre-registered a language intake as the next capability [local].
- `canonical/tools/the_goal_is_a_discriminator_v1.py`, `the_goal_is_a_quotient_of_the_trace_v1.py`, `the_repertoire_is_a_query_v1.py`: version-space questioning, trace-level goals, and the finding that a list of options is not a repertoire on a machine [local].
- Frontier checks: enumeration-based LTLf active learning keeps a version space, measures distinguishing queries, and explicitly discards rivals that agree on all feasible traces rather than spending a query on them [1](https://arxiv.org/html/2611.17866); ICLR 2026 decision-tree active learning uses *stagnation* of the version space as evidence rather than asking forever [2](https://proceedings.iclr.cc/paper_files/paper/2026/file/0e441913d4fa486c3eec967d79750b13-Paper-Conference.pdf); ACL 2026 finds unfiltered memory addition worse than a fixed baseline while strict admission wins [3](https://aclanthology.org/2026.acl-long.27/); EMNLP 2026 MemGuard shows the verifier signal must persist through the memory lifecycle, not just filter once [4](https://aclanthology.org/2026.emnlp-main.423/). The hardest current tests: SWE-bench Pro public leader 61.5 % and OSWorld 2.0 binary ~20.6 % as of Oct 2026 [5](https://decodethefuture.org/en/ai-agent-benchmarks-2026/); these are instruments, not the objective [local law].

Nothing in the project or the literature needed a new dialogue system for *this* residual. The project's own pre-registration was falsified before it was built.

## 2. Verdict on the core hypothesis

- **Real (measured):** retention from one experience is real in the bounded sense the project already documented — exact recall and compiled skill reuse work; the unified model is a single fail-closed front door with zero trained weights; run-level relations can separate runs with identical final states [local].
- **Not real as stated:** "give it the most advanced actions once and everything is solved." The 2026-11-22 census found that 17 of 30 real fixes are outside a one-expression/one-site hypothesis language, and 8 need two change regions [local]. Instant learning cannot change a grammar.
- **Partly false, now corrected:** the claim that the last residual costs one question of the user. The two sentences are the same telescoping fact under the machines' counting semantics; charging the user for a syntactic alias is a measurement error. This round removes it by calculation.
- **Missing:** an intake for *genuine* residual classes, if any remain after all computable identities are removed, plus the action synthesis the project still lacks. Nothing here touches GUIs, browsers, or a real benchmark.

## 3. Single bottleneck and the plan, with rejected ideas

**Bottleneck:** the grammar is enumerated and compared by sampled masks, so syntactic aliases wear the clothes of user intentions. Fix the *meaning* before pricing ambiguity.

**Ultimate minimal solution:** one calculated quotient with explicit premises, applied to every statement in the hypothesis space; refusal when a premise fails; repricing on the same 555 runs; a fourth machine that starts with one copy to try to break the identity.

**Rejected and why:**

| Idea | Why killed |
|---|---|
| Build the pre-registered language intake and ask one question | Fixes a counting artifact with a human; adds a component that the theorem deletes. |
| Add a fourth machine and let breadth split the pair | Would test the premise but leave the false price in place; used here only as a falsifier. |
| Increase depth to 6 and run more samples | The identity is exact; more samples cannot distinguish synonymous statements. |
| Full theorem prover / SMT over all 244 terms | One identity family accounts for the observed alias; the rest would be bureaucracy, not capability. |
| Train embeddings to see the sentences are similar | A model call, a parameter warehouse, and a probabilistic answer to an exact identity. |

Kill test before building: if a machine starts with one copy of `c`, `created_once[c]` and `monotone[c] ∧ final:count[c]==1` must separate on a real run; if the reducer merged them there, the design would be wrong. It does not merge them.

## 4. Build

- `canonical/runtime/computed_equivalence_quotient_v1.py` — derived identity `U(c) ⇔ M(c) ∧ F(c,k+1)`, with three computed premises: known common initial count, integer entry count, **unit increments**. A unit test found that a step from 0 to 2 violates the third premise; the tool now refuses the rewrite for any content with a non-unit jump. Zero parameters, no I/O, no imports of a model client.
- `canonical/tools/residual_is_an_alias_not_a_question_v1.py` — reuses the December round's executed pools and `Analysis`, applies the quotient to all 29,890 statements, reprices the goal, and builds a fourth machine (`PRELOADED`) that starts with one copy of `probe_new_content` and a content that starts absent.
- `canonical/tests/test_computed_equivalence_quotient_v1.py`, `canonical/tests/test_residual_is_an_alias_not_a_question_v1.py` — theorem over 542 short integer runs with unit increments, non-unit counterexample, premise handling, receipt pins. No conftest, no pinning of external files, no weakened assertions.

## 5. Measured result (all five criteria declared before the receipt run)

| Criterion | Result |
|---|---|
| C1 goal's minimal class falls without a question | **2 → 1**, representative `created_once[probe_new_content]`, price 0 |
| C2 every alias identical on all runs | **3/3** aliases, 3 distinct contents, observed identical on 555 runs |
| C3 off-distribution premise | fourth machine initial count 1: `created_once` mask `0`, `monotone ∧ final==1` mask `16777215`; **not merged**; initially absent content **merged** and observed identical on all 24 runs |
| C4 no behaviour changes | 622 behaviours before and after; unique statements 354 → 355; mean class 2.09 → 2.08 |
| C5 zero | 0 model calls, 0 stored parameters, 0 network calls at run time |

Wall time 172 s, standard library plus the project's existing machine drivers. Tests: **12 passed**. The old receipt and its test are untouched: they still report what that round measured; this round retracts the conclusion, not the evidence.

## 6. Honest limits and the next bottleneck

- **Not done** under §6. No hardest open benchmark was run; no GUI, browser, OSWorld 2.0 or SWE-bench Pro task was attempted; no independent verifier signed this. Authority remains NONE.
- **265 of 622 behaviours still have more than one minimal statement** after the quotient; the largest class remains 38. **175 of those 265 carry concatenated reader literals** such as `probe_seed_contentprobe_new_contentprobe_new_content…`, produced by the tarball reader when a member name is repeated — grammar artifacts, not user language. **90 have clean literals**: one sampled class holds `created_once[probe_seed_content]`, `final:count[probe_seed_content]==2`, `monotone[…] ∧ two_copies[…]` and precedence terms. Those agree on all 555 runs but no calculated identity here proves them equal, so they are the genuine residual. This split is the next bottleneck: audit the reader's literals, derive any remaining identities, and only then price language for what is left.
- The identity is derived for integer counts, unit increments and a known common initial reading. A machine with a different reader can violate a premise; the mask check refuses the merge, but the proof's premises must always be stated.
- The fourth machine is a new initial condition on a known tool family, not a new operating system. It tests the premise, not general computer use.

**Next loop:** classify the 265 residual behaviours into reader artifacts, further calculated identities, and genuine language-dependent classes. Only the third kind may price a user question.

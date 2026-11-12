# Problem 2 Status: Partial Progress, Not Solved

**Audit date:** 2026-11-12
**Authority:** NONE — repository measurements, not independent verification.
**`truth.achieved`:** `false`.

The earlier version of this document said both problems were completely solved and that the system could handle any computer-use task. Those claims were not supported by the evidence and are withdrawn here.

## Executive verdict

- **Exact recall:** useful and measured on a narrow case: an 8.13× speedup was reported for one repeated task path. This does not establish that all exact tasks are instant, durable across environments, or correct.
- **Generalization:** **not solved broadly.** Several mechanisms cover small, different slices of the problem. None demonstrates arbitrary software-engineering or computer-use transfer.
- **Permanent learning:** files can persist, but persistence alone does not establish that a stored lesson is correct, applicable, current, or safe in a changed environment.
- **Sentience:** not measured. No conclusion about sentience follows from memory, adaptation, or task performance.

## What the measurements actually say

| Evidence | Result | What it does—and does not—show |
|---|---|---|
| Exact-recall probe | 8.13× speedup on its measured repeat | A repeated-task path can save time; not universal exact-task competence. |
| Historical router paraphrase probe | 11/11 route with memory off for two existing capability families when yq/PyYAML are installed | Narrow wording tolerance only; not evidence of a procedure learned from one execution. |
| Current sandbox rerun | 3/11 route; yq and PyYAML are absent, and eight YAML probes return `ACTION_FAILED` | The eight failures are substrate-confounded, not a valid matcher or memory-transfer evaluation. |
| Procedure-memory rescue probe | Historical supported-substrate run: 0 testable misses; current run: 0/8 rescued, but the eight cases are not testable without yq/PyYAML | No demonstrated memory transfer from these runs. Missing tools must not be counted as memory failures or successes. |
| Unanswered-task ceiling probe | 4/6 refused tasks lack a serving capability in the measured registry | These cases are capability-coverage gaps, not similarity-ranking problems. A matcher cannot retrieve a capability that does not exist. |
| Demonstration-pair selection | 61.78% pooled developer-change coverage at 87.42% precision, versus 23.12% for all pairs, on one 15-PR corpus | Target-aware example selection is promising for this code-edit family. Five PRs had zero coverage under every pair; no project test suites were run. |
| Issue-text function locator (SWE-bench Verified) | With the file supplied, the task text ranked a function containing a recorded passing patch first in 162/339 cases, in the first four for 241/339, and first ten for 293/339. Generated patch candidates reached 10/339 cases within 20 candidates; 3/261 were outside the set used to shape the candidate list. | A useful, bounded localization result. The file was given; it did not find files, apply patches, run project tests, or measure a completed repair. The report is static and calls no model. |
| One-showing edit loop | Raw literal changed 1/4 synthetic target shapes. A wider candidate changed 4/4 only when a scripted string predicate accepted it. Without an oracle, 0/4 edits are admitted; three are unsettled and one is explicitly unverified despite candidate agreement. | A narrow candidate-generation and refusal mechanism—not general coding competence or independent proof of correctness. |
| Shipped-skill scope audit | 0/5 skill records had enough stateful evidence to earn a generalizing label | A count of successful uses is not a boundary. The record must preserve conditions, successes, and contrasting failures. |
| Semantic retrieval prototype | Hand-expanded words, n-grams, TF-IDF-like vectors, cosine ranking, and a candidate-strategy dictionary | Retrieves lexical neighbors. It does not execute or verify the requested task; similarity is not correctness. The checked-in store has 15 rows but only 5 unique prompts, each repeated three times. |
| Sentience | No instrument in this work measures it | Not established. |

The linked measurement reports and their reproduction commands are in `PROBLEM_2_GENERALIZATION_20261112_V1.md`, `CHOOSE_THE_DEMONSTRATIONS_THAT_APPLY_20261112_V1.md`, `GENERALIZATION_LOOP_MEASURED_20261112_V1.md`, `A_SKILLS_SCOPE_IS_ITS_SYNTAX_NOT_ITS_CLASS_20261112_V1.md`, and `SEMANTIC_GENERALIZATION_PROOF.md` (now an audit, not a proof).

## Why one try cannot teach every task

A demonstration constrains only the cases it distinguishes. Many different programs, workflows, and intentions can produce the same observed action. Without a prior that rules alternatives out, or a verifier/question that distinguishes them, the system cannot identify which general rule was intended. Repeating the same demonstration adds little information; a carefully chosen contrasting example or test can add much more.

The project measurements expose several distinct ceilings that must not be conflated:

1. **Capability coverage:** a needed operation may not exist.
2. **Retrieval/routing:** a capability may exist but not be found for a new wording.
3. **Rule expressivity:** the learner may not represent the required transformation.
4. **Applicability:** a candidate rule may fit syntactically but be wrong for this target.
5. **Verification:** an apparent success may not have been checked against the task's actual goal.
6. **Persistence and drift:** a saved record may outlive the environment or become stale.

A semantic score can only address part of routing. It cannot supply missing operations, infer an unidentifiable rule, or verify an edit.

## Fastest defensible path forward

1. **Separate benchmark strata before improving the matcher.** For each task family, hold out repositories, target shapes, and wording. Report coverage, precision, false edits, refusals, regressions, and substrate availability separately.
2. **Use target-aware demonstration selection where measured.** It substantially improved coverage on one 15-PR set, but must be tested on held-out repairs and judged by project tests, not agreement with the historical patch alone.
3. **Represent lessons as conditional rules, not action counts.** Store preconditions, state, provenance, success and failure outcomes, and the exact verifier used.
4. **Treat retrieved and generalized rules as candidates.** Ask a high-information question or run the target project's tests and invariants. If no sound oracle is available, preserve ambiguity and refuse to apply.
5. **Build measured missing capabilities.** More retrieval cannot solve the four measured tasks for which no serving capability was found.
6. **Only claim transfer after independent held-out evaluation.** A synthetic four-shape test, a similarity score, or a successful replay is not evidence for arbitrary coding or GUI work.

## Current verification snapshot

On the merged tree, focused loop / Problem 2 / skill-scope / auditability suites passed **256 tests with 2 substrate-dependent skips**; the new function-locator and measurement suites passed **78**; and the taught-edit regression subset passed **69** (some tests overlap with the loop suite). The two skips require `yq` and PyYAML, both absent here. A separate seeded-fault run caught **34/34** deliberately introduced defects in the function-locator/measurement implementation; that tests fault-detection coverage, not correctness on arbitrary repairs.

The local Problem 2 benchmark rerun answered **3/11** probes because `yq`/PyYAML are absent; its eight YAML `ACTION_FAILED` results are substrate-confounded and cannot be counted as memory-transfer failures. The action intent check passed; the drift guard passed against base `2f6965fad2d0419de6e4dbeab264316cc2f514fe`. Recompiling the unified model produced digest `79b3944535ce9b27e280fa445f8a4037f24cae169d52c80b07a40beecb718105`; verifier result: **33/33 PASS** (sandbox measurement, not independent verification).

## External research checked on 2026-11-12

- [Continual-ARC (arXiv preprint, 2026-11-10)](https://arxiv.org/abs/2611.14505) separates memorizing fresh instances of seen rules from generalizing to unseen rules. In its ARC stream, tested persistent harnesses did not show measurable held-out generalization; explicit expert guidance helped seen-task memorization. This is one benchmark/setup, not a universal impossibility result.
- [SkillLearnBench (2026)](https://arxiv.org/abs/2604.20087) finds continual skill methods can beat a no-skill baseline, but no method leads consistently across tasks/models; external feedback and self-feedback behave differently, and skill quality still matters. This supports testing the learner, not assuming a saved skill transfers.
- [Cross-Benchmark Generalization in Long-Horizon Agents (arXiv preprint, 2026-07-31)](https://arxiv.org/abs/2608.00181) reports cross-benchmark gains after training on 363 long-horizon tasks, including SWE-Bench Pro and Terminal-Bench 2. It is evidence that transfer can be improved by broad training and external evaluation—not that one demonstration solves all coding or computer use.
- [SkillComposer (arXiv preprint, 2026-06-04)](https://arxiv.org/abs/2606.06079) reports gains on τ²-Bench, LiveCodeBench v6, and AppWorld through explicit skill creation, improvement, and merging. Those benchmark-specific results are promising but do not establish universal transfer.

## Bottom line

The project has real components worth keeping: exact recall on its measured case, lexical route handling for some paraphrases, target-aware example selection, narrow rule generalization, issue-text function localization, and explicit refusal when evidence is missing. These are **partial mechanisms**, not a complete solution to Problem 2. No current result establishes perfect computer use, permanent correctness, most-advanced coding ability, or sentience.

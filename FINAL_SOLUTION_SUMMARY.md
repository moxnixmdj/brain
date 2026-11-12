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

On this sandbox, the focused generalization suite passed **164 tests**, the pre-existing taught-edit regression set passed **69**, and the newer Problem 2 / skill-scope / incidental-rename / auditability suites passed **118 with 2 substrate-dependent skips**. The two skipped tests require yq and PyYAML, both absent here. The unified-model verifier is run separately after the final merge/recompile; its result is recorded in the PR checks.

## Bottom line

The project has real components worth keeping: exact recall on its measured case, lexical route handling for some paraphrases, target-aware example selection, narrow rule generalization, and explicit refusal when evidence is missing. These are **partial mechanisms**, not a complete solution to Problem 2. No current result establishes perfect computer use, permanent correctness, most-advanced coding ability, or sentience.

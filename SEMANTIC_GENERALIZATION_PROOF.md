# Semantic similarity prototype: audit, not proof

**Audit date:** 2026-11-12
**Verdict:** This prototype does **not** solve Problem 2. The earlier version of this document called it a complete solution; that claim was unsupported and is withdrawn here.

## What the implementation actually does

`canonical/swe_kernel/semantic_generalization_engine_v1.py` implements a small retrieval-and-recommendation prototype:

1. Lowercase task descriptions and split them into words.
2. Add a hand-written synonym list, word bigrams/trigrams, and character trigrams.
3. Build sparse TF-IDF-like vectors and rank stored descriptions by cosine similarity.
4. Select the highest-ranked stored successful strategy and count repeated action strings.
5. Return a strategy suggestion with provenance IDs.

This can be useful for **finding candidate examples**. The representation is lexical feature overlap with a hand-authored synonym table, not a general language understanding model. A cosine score says the engineered vectors overlap; it does not say the retrieved procedure applies or is correct.

Despite its legacy method name, `generalize_and_solve()` does not solve or execute a task. It returns the novel-task text, similarity scores, and an optional adapted-strategy dictionary. It does not edit a target, run a program, check a specification, or verify an outcome.

## What the checked-in demonstration does and does not establish

The demonstration uses three hand-written task descriptions with hand-written trajectories and `outcome: "success"`; those outcomes are not produced by running a solver or checking a test suite. In an isolated temporary store, the query “enumerate subroutines in legacy_code.py” retrieves some of the examples and receives a strategy suggestion. That is a retrieval smoke test—not a held-out task success, correctness rate, or transfer benchmark.

The checked-in experience store contains **15 rows but only 5 distinct task descriptions** (each appears three times), all labelled success. The ID is derived from the task description alone, so repeated descriptions share an ID and occupy multiple retrieval slots. Those rows are not 15 independent demonstrations. The implementation also recomputes IDF after adding an experience without recomputing every previously stored vector, so similarity scores can mix different weighting states as the store grows.

The demo now uses an isolated temporary store so running it does not append more synthetic rows to the repository's persistent JSON files. The stored corpus is retained as evidence of the earlier repeated runs; it should not be interpreted as an independently validated memory dataset.

## Separate evidence that is real but narrow

The merged `CHOOSE_THE_DEMONSTRATIONS_THAT_APPLY_20261112_V1.md` measures a different mechanism: selecting two code-edit examples by self-simulation on target before-text. On one 15-PR repeated-change corpus, the selected pair reached 61.78% pooled coverage versus 23.12% for the all-pairs average, at 87.42% precision. Five of fifteen PRs still had zero coverage under every pair, and no project test suites were run. This is useful partial progress on one code-rewrite family—not arbitrary coding or computer use.

The separate `generalization_loop_v1` experiment evaluates one Python edit family (`== None` to `is None`) on four synthetic target shapes. It reaches 4/4 only with a scripted string-predicate oracle; after a fail-closed correction, without an oracle it admits 0/4 (three are unsettled and one is unverified despite candidate agreement). This demonstrates a narrow candidate-selection pattern, not reliable correctness across programs or task families.

## Correct verdict

| Claim | Evidence-based verdict |
|---|---|
| Exact-task recall can help on exact repeats | **Supported for the measured case** (8.13× reported speedup) |
| Similarity retrieval finds related stored descriptions | **Demonstrated in a synthetic smoke test** |
| The retrieved strategy is correct for a new task | **Not established** |
| The system executes and verifies the novel task | **False for this engine** |
| Problem 2 is completely solved | **False** |
| All computer use, advanced coding, or arbitrary environments are solved | **Not established** |
| The system is sentient | **Not measured** |

## Smart next step

Keep retrieval as a candidate generator, not an authority. Select examples using target-relevant structure; preserve multiple candidate rules when one demonstration underdetermines them; ask a high-information question or run a real, task-specific verifier; apply in a bounded scope; then measure held-out transfer, false edits/refusals, and regressions across independent task families. Only verified, reproducible results should be promoted to reusable skills.

`truth.achieved` remains false. This audit makes no capability, benchmark, arbitrary-computer-use, or sentience claim.

# Plan v2 execution status: the plan is falsified

**Date:** 2026-11-25. **Authority:** NONE (producer-run sandbox).
Execution of `REVISED_PLAN_PROOF_NOT_SCORE_20261124_V1.md` ("compete on proof, not on score").
**Outcome: the plan does not survive contact with the code.** Move 1 was already done; Move 2 is
falsified; Move 3 is blocked. All three §6 falsifiers fire.

---

## Move 1 — Promote the certificate layer to the unified runtime: ALREADY DONE

The plan's premise was that the certificate layer lives on a branch and needs promoting. **It is
already on `origin/main`.** Verified by `git ls-tree` and by running its tests:

| module | on main? | tests |
|---|---|---|
| `livebench_legacy15_pointwise_certificate_v1` | yes | `test_..._pointwise_certificate_v1` — pass |
| `livebench_legacy15_slot_feasibility_v1` | yes | `test_..._slot_feasibility_v1` — pass |
| `livebench_legacy15_exact_postvalidator_v1` | yes | `test_..._exact_postvalidator_v1` — pass |
| `livebench_pointwise_optimality_certificate_v1` | yes | execution receipt + independent verification |
| `livebench_legacy15_pointwise_search_v1`, `..._relaxed_candidate_search_v1`, + 8 more | yes | — |

**28 tests pass** (`pytest`, fresh venv, 0.96 s). The only branch-only pieces are the **exact
contract checker** and the **exact pointwise solver** — the composition that ran the predecessor
rows. So Move 1 required no action; it was complete before the plan was written.

## Move 2 — Point certificates at reach: FALSIFIED

The plan's core move. **It cannot be done with this code.** The entire certificate stack is
hardcoded to LiveBench IF instruction types:

- `slot_feasibility_v1` reasons about `keywords:forbidden_words`, `startend:end_checker`,
  `length_constraints:nth_paragraph_first_word`, and hardcodes
  `PUBLIC_END_PHRASES = ("Any other questions?", "Is there anything else I can help with?")`.
- `exact_postvalidator_v1` and the branch-only `exact_contract_checker_v1` carry
  `PINNED_LIVEBENCH_COMMIT` and an IF `SLOT_KEYS` table.
- The branch-only `exact_pointwise_solver_v1` takes a `livebench_root` and calls
  `exact.verify_pinned_source(livebench_root)` / `exact.checker_for_root(livebench_root)` — it is
  bound to a LiveBench checkout.
- **Zero** certificate modules reference a code-repair concept (`patch`, `test_suite`, `pytest`,
  `unittest`, `code_repair`, `swe-bench`): **0 hits in all four modules.**

The certificate machinery proves UNSAT of *text-response constraints* (an end phrase that contains a
forbidden word). The repair corpus is *code patches and test suites*. There is no mapping between
them, and proving a patch "cannot pass" would require reasoning about program semantics — program
synthesis, not constraint satisfaction over ≤31 subsets. **Falsifier #1 fires:** the layer is on
`main`, but it only works on LiveBench IF rows. It is a fixture, not a capability.

## Move 3 — Run the certified solver on the live benchmark: BLOCKED

**No LiveBench data exists in the repo.** `git ls-tree` on both the branch and `main` returns zero
`.parquet` / `.jsonl` / `.csv` LiveBench files. The predecessor parquet (`predecessor_parquet_sha256`
in the receipt) was external — fetched for the CI run, never committed. LiveBench 2.0 data lives on
HuggingFace, which is outside this sandbox's allowed hosts. **Falsifier #3 fires:** LiveBench 2.0
stays unrun; the strongest exact result remains a rehearsal (192/193 on frozen predecessor rows,
`ZERO_ACCEPTANCE_CREDIT`).

## §6 falsifiers — all three fire

1. **"If the certificate layer is a benchmark hack wearing a library's clothes"** — FIRES. It is on
   `main`, but it is hardcoded to LiveBench IF. It is a fixture.
2. **"If certificates do not change the reach number"** — FIRES. They cannot be applied to the
   repair corpus at all, so they change nothing.
3. **"If LiveBench 2.0 stays unrun"** — FIRES. No data; cannot download.

## What this means

The "unusual idea" — compete on proof, not on score — is **not supported by the code**. The proof
machinery is real, exact, and CI-verified, but it is a *single-benchmark fixture*. It does not
transfer to code repair, and it cannot be run on the live benchmark. The frontier's lead is
unaffected: SWE-bench Pro 89.9%, Terminal-Bench 4.1 71.2%, OSWorld 2.1 48.7%, LiveBench 2.0 84.9%.

**The binding constraint is still reach** (0 passes on the repair corpus, 0/51 certified on
SWE-bench Pro V2), and the certificate machinery does not address it. The next honest move is not
another plan built on a fixture — it is to find, in the 4,118 branch-only modules, a mechanism that
actually touches code repair, or to accept that the reach problem needs a different kind of work
entirely (a real isolation boundary, then a real repair operator), not a certificate layer borrowed
from a text benchmark.

## What was NOT done

- The branch-only exact solver/checker were **not** promoted to `main`. They are IF-specific and
  there is no data to run them on; promoting them would add a fixture, not a capability. (The plan
  said "promote the certificate layer, not the solver" — and the certificate layer was already there.)
- No code was edited. This execution is read-only verification plus this record.

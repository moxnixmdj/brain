# TRUE CAPABILITY TEST LAW V1

Status: active from 2026-10-14. Scope: every statement of the form "Brain can do X".
Enforcer: `execution_guard/true_capability_harness_v1.py` (the only writer of
`canonical/capabilities/true/TRUE_CAPABILITY_LEDGER_V1.json`).

## 0. Why this law exists

External benchmarks are no longer treated as the scarce resource of the project.
Their only job was to evaluate capabilities. Brain now evaluates its own
capabilities with its own tests, and those tests are held to a stricter
standard than any external benchmark: they must be **true**. A test is true
when passing it is impossible without the capability it names.

## 1. Definition

A **capability** is a mechanism that, for **unseen instances** of a **declared
input class**, produces outputs that an **independent oracle** accepts, using
**zero model** at runtime.

Each bold term is a test. A claim that fails any one of them is not a capability
and may not be called one anywhere in the repository.

| Test | What it rules out |
|---|---|
| Unseen instances | memorised answers, hand-tuned fixtures, author-chosen examples |
| Independent oracle | the author grading their own work, tautological checks |
| Zero model | an external LLM wearing a Brain badge |

## 2. The three mandatory separations

1. **Solver, generator, oracle are three different files.** The generator and the
   oracle module must not import the solver (statically checked by the harness;
   the solver import also raises at runtime inside those modules).
2. **The seed is not chosen by the author.** On a public runner the seed is
   derived from `GITHUB_RUN_ID : GITHUB_RUN_ATTEMPT : GITHUB_SHA`; elsewhere from
   `os.urandom`. A run with an explicit `--seed` is a **replay** and never credits.
3. **The verdict is not written by the author.** Receipts and ledger rows are
   produced only by the harness, carry the git blob sha of the solver, generator
   and oracle files, and state `authority: NONE`. Nothing in this directory is
   an authority file; it is measurement.

## 3. Oracle classes, ranked by independence

| Rank | Class | Meaning |
|---|---|---|
| 1 | `PUBLISHED_CANARY` | a numeric result published by a third party (standard-setter, benchmark verifier, textbook) |
| 2 | `DIFFERENTIAL_EXTERNAL` | a third-party implementation, vendored and sha256-pinned, never imported by the solver |
| 3 | `ANALYTIC_CLOSED_FORM` | the governing formula written directly in the oracle file from the primary source |
| 4 | `METAMORPHIC` | a relation between outputs of related inputs (scaling, symmetry, cancellation) |
| 5 | `PROPERTY` | an invariant of any correct output (bounds, non-negativity, conservation) |

A spec must declare at least **two** oracle classes and name its
`independent_oracle_ids`: oracles that share **no lineage** with the solver.
If the solver was harvested from a donor, the donor differential is useful
(it catches porting errors) but is **not** independent and must be labelled so.

## 4. What a spec must say

`schema: TRUE_CAPABILITY_SPEC_V1` with: `capability_id`, `claim` (one sentence,
falsifiable), `input_class` (the generator's distribution in words),
`scope_limits` (what the claim does **not** cover, written as NO ...),
`solver{module,entry}`, `generator{module}`, `oracles{module,declared[{id,class}]}`,
`independent_oracle_ids`, `min_instances`, `pass_threshold`,
`falsification_condition` (the sentence that would make the claim false).

## 5. Forbidden practices (each one voids the receipt)

- author-expected values as the **sole** oracle (that is a regression test, not a capability test);
- fixed seeds, cherry-picked instances, or instance lists checked into the repo as the "test set";
- generators that share code with the solver, or oracles that call the solver's internals;
- any check whose pass condition can be met by output shape alone (filler tokens, canned templates, "ordinal mod N" closures);
- network access during measurement (the harness blocks sockets);
- importing any model/LLM/ML module during measurement (the harness fails the run);
- inferring a "ceiling", "equivalence" or "frontier level" from a pass — a receipt says exactly one thing: *this solver, on N fresh instances from this input class, satisfied these oracles*;
- editing a receipt or ledger row by hand.

## 6. Credit

| Where the harness ran | Ledger status | Counts as evidence? |
|---|---|---|
| developer sandbox / laptop | `MEASURED_SANDBOX` | no (reproducibility demo only) |
| public GitHub runner, workflow artifact uploaded | `MEASURED_PUBLIC_RUNNER` | yes, as a measurement |
| any run with `--seed` | `REPLAY_NOT_CREDITING` | no |

Credit toward any goal pointer additionally requires the referee on `main`
(`REPO_INTEGRITY_POLICY_V1.json`) to have admitted the commit that carries the
spec, solver, generator and oracle blobs named in the receipt.

## 7. How a capability moves through the program

1. Write the spec (claim, input class, scope limits, falsification condition) **before** touching the solver.
2. Write generator and oracles; obtain or vendor an independent oracle; add a published canary when one exists.
3. Run the harness. If it fails: fix the solver or narrow the claim. Never widen the tolerance to pass.
4. Run the mutation check: break the solver on purpose and confirm the harness fails. A test that cannot fail is not a test.
5. One capability per pull request, judged by the referee on `main`.

## 8. Relation to the existing acceptance machinery

The 38 Opus-5.5 acceptance predicates, their evidence bindings and all goal
pointers are untouched by this law. They continue to measure what they measure.
This law adds the acceptance currency for the word "capability": a fresh-instance
receipt. External benchmarks remain available as *optional* evaluation (see
`canonical/governance/CAPABILITY_TRUTH_PIVOT_20261014_V1.json`) and are no
longer counted as limiting factors.

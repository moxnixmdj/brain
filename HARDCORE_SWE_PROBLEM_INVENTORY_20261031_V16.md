# Hardcore software-engineering problem inventory — V16

Measured 2026-10-31 on `fabf28c` (branch `arena/14753d8c-brain`).
Supersedes V13–V15. This one is short on purpose: it records **one fix that landed**
and **three measurements that change what the next session should do**.

---

## §1 What landed

`PR #6479 — an empty diff is not an answer` (merged, `main` at `237dec1`).

`git.repository.operate.v1` answered "Show the diff of `<file>`" with
`git diff HEAD -- <target>`, which is empty by design for a file git has never seen.
It returned that empty patch as the answer — `row_count: 0`, the empty-string
digest — and the door reported `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED`.
It was the **only FALSE in the 54-case capability matrix**.

The fix uses the answer git already gives: `git diff --no-index -- /dev/null <path>`,
the canonical new-file patch. `--no-index` exits 1 when the inputs differ, so the exit
code is not a failure signal; the patch and the numstat are. A second, independent
plumbing check now refuses a diff whose numstat counted files but whose patch carries
no `@@` hunk (`INDEPENDENT_CHECK_DISAGREES:diff:NO_PATCH_BODY`), and a tracked-unchanged
target still returns an honest empty diff — pinned by a test so the fix cannot become
an invented patch.

| | before | after |
|---|---|---|
| matrix | 18 REAL / **1 FALSE** / 35 REFUSED | **19 REAL / 0 FALSE / 35 REFUSED / 0 DAMAGED** |
| `git_diff` | FALSE, empty patch | REAL, 428-byte patch, `new file mode` |
| median | 82 ms | 88 ms |
| `test_git_repository_operate_v1` | 16 tests | **18/18 green** |

---

## §2 RETRACTED: "build a chain runner"

V15 ranked a chain runner first, on the evidence that 43 of 84 rows declare a
precondition only another row can produce. **The runner already exists, twice over:**

* `capability_composer_v1.plan(seed, token, graph)` — returns capabilities **in firing
  order** that produce a token from a seed, cycles refused, cheapest producer preferred;
* `composer_route_v1.execute_chain(chain, goal, inputs, registry)` — runs the chain step
  by step, binds each step's slots from prior step outputs (`produced`), snapshots what
  existed before so a step is credited only with files it created.

And **every `requires` in the 84 rows is satisfiable**: measured over the composer graph
(146 nodes), for each of the 84 SWE rows, each required token is either already available
in the seed or reachable by `plan()`. Zero rows name a token nothing can produce.

So the gap is neither planning nor execution. It is **wiring**: when the door admits a
decisive row whose `requires` are unmet, it returns `NO_DECISIVE_TYPED_PLAN` instead of
asking the planner for the producers first. That is a call, not a subsystem.

### A caution about my own instrument
My first pass at the satisfiability measurement printed `git.repository.available` and
`python.repo.patch.test_verified` as **UNREACHABLE**. It was wrong: `plan()` returns an
**empty list** when the token is already satisfied, and the probe tested `if chain:`,
which is false for `[]`. Corrected to `if chain is None`. Two of the tokens I was about to
report as a registry hole were already available. Any census that tests a container for
truthiness instead of identity will report holes that are not there.

---

## §3 The census split: chains are not what refuses the 47

Of the 49 advanced requests, 40 select a row and 47 are refused. Classified by the
selected row's own declaration:

| cause of the refusal | requests | evidence |
|---|---|---|
| the selected row is **standalone** (`requires == []`) and refused its own inputs | **27 of 47** | `dead_code` ×6, `inline_helper` ×4, `bisect_regression` ×4, `mutation_score` ×3 |
| the selected row is **chain-bound** and its producers were never run | **13 of 47** | `crossfile.choreograph` ×5, `git.repository.operate` ×3, `patch.search.test_guided` ×2, `testselect`, `acceptance.measure` |
| no row selected at all | 7 | `RAW_GOAL_COMPILATION_GAP` |

Consequence for ordering: the chain wiring fixes at most **13** of the 47. The other 27
are the magnet rows choosing a sentence they cannot answer — a selection defect, not a
sequencing one. V15 put the chain runner first; the honest order is **magnets → chain
wiring → derivation**, because the larger half is selection.

---

## §4 Still open, unchanged from V15

* **Magnets** (`dead_code`, `bisect_regression`, `mutation_score`, `crossfile.choreograph`,
  `inline_helper`) take 22 of 40 selections. `software.repair.choreograph.crossfile.v1`
  declares 40+ keywords (`race`, `thread`, `unused`, `deprecated`, `sql injection`) and is
  a universal magnet by construction.
* **Derivation** covers 22 of the 85 declared slots; 25 rows blocked by a slot nobody produces.
* **Effect-faithfulness**: probe 39 still serves an API-design review with a secret scanner.
* **`generate.scaffold`** writes to a repo-root `generated_tests/<dir>` default that its
  registry row does not declare as an argument.
* **Substrate identity** is proved from wheel metadata, so a vendored deployment refuses.
* **`canonical.tests.test_git_sentence_routing_v1::test_the_registry_row_declares_the_operation_contract`
  is red on `main`** (row args drifted from the adapter's); unrelated to #6479.

---

## §5 The next change, in one sentence

For an admitted row with unmet `requires`, call `capability_composer_v1.plan()` from the
sentence's seed and `execute_chain()` on the producers before the row — a wiring call
between two functions that already exist and are already tested, which is why it should be
measured against the 13 chain-bound requests and not the whole census.

Authority: NONE.

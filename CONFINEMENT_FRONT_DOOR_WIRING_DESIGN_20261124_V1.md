# Confinement → front-door wiring design

> **Safety review update — NOT APPROVED, 2026-11-24.** The proposal below
> incorrectly treats a disposable clone as host isolation. `confinement_v1`
> launches a normal subprocess with the host user's filesystem and network
> authority; it is not an OS sandbox. In a temporary-repository experiment,
> a confined command wrote a sentinel outside the clone while the result still
> reported `host_untouched=True` and `verified=True`. Git porcelain equality
> does not establish that host files are untouched. This makes the safety
> claims in sections 2–3 and the proposed wiring invalid for untrusted repair
> execution. The existing `live_brain_route_admission_v1` seam also uses this
> substrate and should not be described as a host-security boundary.
>
> The candidate Phase A wiring was reverted: the repair front door retains its
> original independent-evidence check followed by the exact boundary refusal.
> Mocked tests of that candidate did not constitute T3's real-adapter or T6's
> front-door evidence. `receipt_sha256` hashes the pre-execution basis, not the
> effect-bearing outcome; `confinement_v1.execute()` separately computes a
> result digest that the existing dispatch does not carry through. A 64-character
> string or a recorded effect hash is not independent verification of patch
> bytes. A new reviewed isolation design, trustworthy effect/receipt validation,
> independent capability evidence, and the pre-registered tests are needed
> before retrying Phase A. Do not route around these blockers. The proposed
> threat model and receipt review checklist are in
> `ISOLATED_REPAIR_CARRIER_REVIEW_DESIGN_20261124_V1.md`; they grant no authority.
>
> The post-candidate five-instance synthetic dry-run produced 0/5 patches in
> both EPISTEMIC and SOLVE_OR_LEARN, so the VM gate remains closed. The tests
> were run while the candidate was present, before it was reverted; neither
> mode reached an admitted repair in that experiment. Phases B/C are not
> implemented. The SWE wrapper currently accepts a model-returned diff or a
> worktree diff after patch-format/applicability checks; it does **not** enforce
> receipt-backed extraction. A non-empty output from that wrapper alone would
> therefore not pass the gate. The remainder is the historical proposal,
> **not an approval**.
>
> Validation after reverting the candidate: 57 focused tests passed, including
> a real temporary-repository characterization of the isolation gap and a
> repair-front-door refusal regression. The broader suite ran 120 tests with
> 12 failures and 1 error, matching the same failure/error identities from a
> 92-test clean-HEAD baseline. The three additional unified-model failures seen
> during the candidate run disappeared after recompiling the generated unified
> model to include the new runtime module; they reflected a stale source index,
> not evidence that candidate wiring was safe. T3 and T6 were not established,
> and the Phase A acceptance gate remains unmet.

**Historical design. No declaration was added and no capability was registered.**

Date: 2026-11-24 · Authority: `NONE__DESIGN_NOT_IMPLEMENTATION` · Branch `arena/d582a17b-brain`

## 0. Correction to my own previous note

`EPISTEMIC_BENCHMARK_ADAPTERS_20261124_V1.md`, section 4, said the confinement
substrate "is not yet wired into the front door". That was **imprecise**, and
the repository records say so:

* 2026-11-12: `confined_dispatch_v1.py` was wired into
  `live_brain_route_admission_v1.run_adapter_locally()` (9-line seam at
  `canonical/runtime/live_brain_route_admission_v1.py:1493-1497`) with a
  reviewed declarations file. `THE_CONFINED_DISPATCH_SEAM_EXISTS_20261112_V1.md`
  records 5/5 dispatch tests, host `git status --porcelain` byte-identical,
  effect sha256 receipts, same expectation check.
* 2026-11-13: `python.software.repair.apply.verified.v1` was added to
  `CONFINED_EFFECT_DECLARATIONS_V1.json` (`effect_args: ["output_path"]`,
  budget 600 s). `CONFINED_DECLARATION_REPAIR_APPLY_20261113_V1.md` records the
  confined run: fail-closed with a receipt because the synthetic goal named no
  failing test.
* 2026-11-12 documents also corrected an earlier misdiagnosis: the boundary
  status for 19/38 realistic goals was emitted by the door's discovery
  fallback, not by `boundary.refuses_execution`, and the true binding wall was
  sentence → compiled plan.

So the substrate and one door's seam exist. The question this design answers is
narrower: **why does `open_model().solve()` still refuse, and what is the
smallest auditable way to let a declared capability use the existing seam?**

## 1. The measured call graph

```
open_model().solve(goal, mode=...)                 brain_unified_model_v1.py:936
  └─ _execute_capability(...)                      brain_unified_model_v1.py:1264
       └─ verified_bound_capability_execution_adapter_v1.execute(...)
            ├─ [line ~457] unconditional repair refusal -> boundary.STATUS
            ├─ [line ~471] _receipt_backed_execution -> live_door.run_adapter_locally
            │                 └─ [line ~1494] confined_dispatch.run_confined_capability
            │                      └─ confinement_v1.admit / execute / release
            └─ [line ~480] promoted registry path -> host-bound executor
```

`SOLVE_OR_LEARN` takes a second route with its own refusal:

```
act_or_learn(...)                                  brain_unified_model_v1.py:1029
  └─ solve_or_learn(...)                           closed_loop_autonomous_controller_v1.py:527
       └─ 2B-Repo branch [line ~1561] -> boundary.STATUS
          tier_used = "repository_repair_execution_not_admitted"
          (the code below it calls repair_repository_in_cow_zygote(..., apply_to_workspace=True))
```

Measured on 2026-11-24 (five synthetic SWE-style instances, public test files
present): `EPISTEMIC`/AUTO → `CAPABILITY_INPUTS_MISSING` from
`python.swe.transform_and_synthesize.v1`; `SOLVE_OR_LEARN` → the 2B-Repo
boundary status above. Current registry facts, checked directly:

| Fact | Measured value |
|---|---|
| `boundary.REPAIR_CAPABILITY_ID` | `python.software.repair.apply.verified.v1` |
| `confined_dispatch.declarations()[repair]` | `{'effect_args': ['output_path'], 'budget_s': 600}` |
| Live registry source for repair id | `None` (not receipt-backed) |
| `boundary.refuses_execution(repair, live_entry)` | `True` |

**Consequence:** the repair row is declared, but `open_model().solve()` cannot
reach it. The unconditional early refusal fires first, and even if it were
removed, the repair id is not receipt-backed, so it would fall through to the
host executor on the promoted path. That is the precise hole this design closes
— without weakening the boundary.

## 2. Invariants (non-negotiable)

1. No request flag, environment variable or caller assertion grants authority.
   `computer_execution_boundary_v1.py` states this explicitly; this design does
   not add `confinement_admitted` to any call.
2. The decision is computed by the boundary module plus **reviewed declaration
   data** plus the **bound arguments** of the compiled action. A missing or
   unbound declared effect means refusal, never a default path.
3. The capability runs inside a disposable clone, with list argv, `shell=False`,
   restricted PATH/HOME, a wall-clock budget, declared effects hashed inside
   the worktree, and a content-addressed receipt. Host `git status --porcelain`
   must be byte-identical.
4. No effect bytes are adopted into the host as a side effect of "trying". A
   patch becomes a prediction only after the receipt is verified and its hash
   matches the emitted bytes.
5. `pass`, `status`, `terminal_authority`, `task_completion_claimed` and credit
   deltas keep their current meaning. Confinement proves an execution shape; it
   does not prove the issue is solved.
6. Protected paths from `AGENTS.md` are untouched. The declarations file is the
   review surface; an agent does not add rows to it.

## 3. Seam A — `verified_bound_capability_execution_adapter_v1.execute()`

**Change:** replace the unconditional repair refusal at line ~457 with a
three-way, fail-closed decision. Only the repair id is affected.

```
if cid == boundary.REPAIR_CAPABILITY_ID:
    if cid is live-receipt-backed:
        return _receipt_backed_execution(...)   # already uses the live door seam
    action = prepared.rendered_action            # from prepare(), not caller-authored
    routed = confined_dispatch.run_confined_capability(
        cid, inspected.entry, action, host_root=ROOT)
    if routed is None or routed.get("pass") is not True:
        return boundary.STATUS result            # exact current refusal
    require routed.confinement.receipt_sha256,
             routed.confinement.host_untouched is True,
             routed.confinement.verified effects,
             routed.dependency.executor == ADMITTED_CONFINEMENT_V1
    if any check fails: return boundary.STATUS result
    return routed with receipt attached
# non-repair ids: existing paths unchanged
```

Critical detail: the repair id must **never** fall through to
`astra_runtime._invoke_bound_capability` on the promoted path. If the confined
route is unavailable, the returned object is the same boundary refusal as
today (`pass: False`, `executed: False`, `terminal_authority: False`, all credit
deltas zero).

Ordering rule: keep the existing independent-evidence gate in `prepare()`
first. Confinement does not launder a capability whose evidence is absent.

## 4. Seam B — tier-2 repository repair in `solve_or_learn`

The 2B-Repo branch returns the boundary status before calling
`repair_repository_in_cow_zygote(..., apply_to_workspace=True)`. That call
would write the host workspace, so the refusal is correct.

**Design (separate PR, after Seam A):** a declared carrier runs the same repair
engine with `apply_to_workspace=False` inside the confinement, writes a patch
artifact at a declared relative path, and returns the receipt. The controller
may then offer an **explicit adoption step** to the caller. Adoption is not
part of "try"; it requires its own reviewed decision and a hash check. Until
that diff exists, the 2B-Repo branch keeps its current status and
`SOLVE_OR_LEARN` keeps refusing on SWE-shaped goals.

This is why flipping the adapter's default mode is wrong: it would change the
refusal string, not the capability.

## 5. Seam C — SWE-bench predictions from a receipt

The existing seam clones `host_root=ROOT` (the Brain repository). The SWE
adapter creates worktrees under `/tmp/...`, so two problems must be solved
before a confined run can produce a prediction:

1. **host_root binding.** Add an optional reviewed binding for a caller-supplied
   git worktree: it must exist, have a `.git` file/dir, be at the declared
   `base_commit`, and be outside the host repository's working tree. The
   binding is data validated by the seam, not a caller flag. Default stays
   `ROOT`. An unbound external path is refused.
2. **Effect shape.** `output_path` and any `patch_path` must be **relative**
   inside the clone. Absolute `/tmp/...` paths are refused by
   `confinement_v1._inside()` at admission; an adapter that forwards them
   simply gets `None` and the refusal stands.

The confined runner must read the generated patch file before release, put its
text and sha256 in the result, and the SWE adapter writes `model_patch` only
when the text hash equals the hash in the verified receipt. On mismatch or a
missing effect, the row gets an empty patch and a reason code, as today.

No row may be added to `CONFINED_EFFECT_DECLARATIONS_V1.json` by this work;
adding one is a separate reviewed change with its own test.

## 6. Pre-registered acceptance tests

Declared before implementation so the run cannot become its own judge.

| ID | Test | Required outcome |
|---|---|---|
| T1 | Undeclared capability through Seam A | Same boundary refusal; `confined_dispatch` not called. |
| T2 | Repair id, declaration present, unbound `output_path` | Refusal; no clone executed. (Existing PC2 covers the dispatch layer.) |
| T3 | Repair id, bound relative `output_path`, real adapter | Confined route used; receipt, `host_untouched`, executor stamped; caller expectation checked by the same ruler. |
| T4 | Absolute effect path into the host or `/tmp` | `None` from dispatch; adapter returns boundary refusal; no execution. |
| T5 | Budget exceeded / adapter raises | `BUDGET_EXCEEDED` or fail-closed receipt; never a pass. |
| T6 | `open_model().solve()` envelope for T3/T5 | `pass`, `status`, `reason`, credit deltas still honest; no new authority claim. |
| T7 | Boundary module and declaration file unchanged by the diff | Existing guard tests green; no new declaration row. |
| T8 | SWE adapter, hash-matched patch from receipt | Non-empty `model_patch`; trace carries receipt sha and effect hash. |
| T9 | SWE adapter, hash mismatch / missing effect | Empty patch plus reason; no host worktree adoption. |
| T10 | Tier-2 `SOLVE_OR_LEARN` repository repair | Still refuses until Seam B is separately admitted; no implicit workspace write. |

Run after implementation on a disposable clone:

```bash
python3 -m pytest canonical/tests/test_confined_dispatch_v1.py \
  canonical/tests/test_admitted_confinement_v1.py \
  canonical/tests/test_computer_unconfined_route_guard_v1.py -q
python3 -m unittest canonical.tests.test_swebench_verified_epistemic_adapter_v1
```

## 7. Decision gate before any cloud spend

1. T1–T7 pass in a fresh clone and the boundary module/declaration file are
   unchanged.
2. A 5-instance SWE dry-run emits at least one receipt-verified non-empty
   patch with T8/T9 passing; otherwise the mode stays fail-closed.
3. Owner review of any new declaration row and of the host_root binding. No
   self-authorization at any point.
4. Only then retry the VM smoke test with a fresh `run_id`. The score still
   comes from the official harness, never from this design or its receipts.

**Not claimed:** that this raises the SWE-bench score, that the engine can localize
an arbitrary issue, that confinement makes a repair correct, or that any task
was independently verified. Those remain separate, measured questions.

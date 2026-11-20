# Multi-clause evidence binding reaches adapter DONE — 2026-11-20 (V1)

**Progress class:** `VERIFIED_INTEGRATION_OF_OWNED_CAPABILITY`.
**Authority:** `NONE__PRODUCER_RUN_SANDBOX`. This is not benchmark credit, not
independent verification, not terminal authority, and not §6 completion.

## 1. Full requirement restatement and §2 resolution

The task remains: build our own model, weights, architecture and agent that fully
solves computer use — advanced software engineering, GUIs, browsers, arbitrary
new environments — with zero runtime model calls and parameters that contain only
computed mechanisms, not a warehouse of memorized world facts. Knowledge must be
instant, from the project's external store, inspectable/editable/deletable, and
learnable from one experience. Work must exhaust project and frontier research,
find the first-principles bottleneck, design the ultimate minimal solution with
rejected ideas, kill bad designs before building, build, test the hardest open
problems, separate verified/unverified/failed honestly, and loop through §5 until
§6. One branch, one merge per feature, never ask the user, never stop early.

The §2 contradiction is resolved as previously adopted and re-tested here:
forbidden = parameter lookup of memorized world facts and runtime dependency on
another model; allowed = external editable knowledge/skill store plus
single-experience writes, with weights holding only computed mechanisms. Nothing
in this round changes that boundary.

## 2. Research findings

### Project (exhaustive search this round)

Searched non-obvious names as well as the obvious ones: `receipt_dataflow_v1–v3`,
`workflow_policy_v1–v13`, `contextual_reference_operators`,
`source_grounded_coreference`, `explicit_definition_reference_graph`, all ledger
modules, `osworld_verified_task_ledger_v1`, `osworld_verified_policy_v1`, the
byte-pinned adapter and host/guest kernels, the admitted sensor bridge, and the
forbidden Qwen runtime policies.

What already existed and was reused:

* `workflow_policy_v1.split_explicit_subgoals` — contamination-safe splitting of
  explicit semicolon/list/`and then` clauses. Reused instead of writing another
  language parser.
* `receipt_dataflow_v1–v3` — provenance-bound scalar and relational reference
  materialization. It proved that unique receipt-backed bindings are safe, but it
  materializes text; it does not bind a quoted literal to a filesystem path for a
  completion gate.
* `contextual_reference_operators` — already has a bounded ordered `respectively`
  two-by-two rule. Reused as the admissibility rule for multi-pair clauses, not as
  a general coreference engine.
* `osworld_sensor_request_bridge_v1` — admits a computed directory assertion with
  fresh re-measurement; field/value cannot be supplied by policy.
* `BrainOSWorldAgent` — byte-pinned adapter. Its DONE check recognizes
  `ASSERT_PATH_EXISTS:PASS` and `ASSERT_TEXT_* :PASS`, but not a bare
  `SENSOR_REQUEST:PASS`. This was the measured integration defect.

### Frontier (research only, never runtime dependency)

OSWorld 2.0/2.1 remains the relevant hard computer-use target: 108 long-horizon
workflows, ~27 weighted checkpoints per task, with challenge annotations including
implicit-state inference 43/108 (39.8%), multi-item state tracking 43/108 (39.8%),
and conflict disambiguation 39/108 (36.1%) [1](https://arxiv.org/html/2606.29537v1)
[4](https://osworld-v2.xlang.ai/). The authors' central finding is that agents can
act locally but lose task-level state, skip verification, and spend under 7% of
budget on error detection and repair [2](https://s46486.pcdn.co/wp-content/uploads/2022/01/OSWorld2.0.pdf).
OSWorld 2.1 is the current bug-fix release of the same 108 tasks
[3](https://snorkel.ai/osworld-2-1-long-horizon-computer-use-evaluation/).
For coding, SWE-bench Pro and Terminal-Bench remain live hard benchmarks;
Terminal-Bench 2.0 contains 89 expert-verified container tasks with comprehensive
tests and unique environments [5](https://arxiv.org/html/2601.11868v1). These
sources are inputs, not our results and not borrowed capability.

## 3. Verdict on §3

* **Instant replay of an executed action in a copied environment: true**, from
  earlier project receipts.
* **One trace identifying a new goal: false.** A single experience does not by
  itself identify the goal or bind its literals to world objects.
* **Blanket permanence: false.** Persistence holds only for inspectable external
  records and bounded computed closures, not for unlimited world knowledge.
* **Closure from supplied judgments without runtime models: true but bounded.**
  Earlier receipts measured computed-law and permissions-law closures with 0/0
  train/held errors.
* **Sentience/general computer use: unproven.**
* **Why not let a model experience advanced coding actions once and learn them:**
  it would require either putting world facts into parameters (forbidden) or
  calling a model at runtime (forbidden). One experience can write an external
  record, but that record still needs mechanism-level binding and verification.
* **Real bottleneck this round:** a multi-item instruction was refused wholesale
  when it contained more than one path/quote pair, and a directory sensor PASS
  could not satisfy the byte-pinned adapter's DONE evidence check.

## 4. Ultimate minimal plan and killed designs

| Idea | Verdict | Reason |
|---|---|---|
| Add an LLM parser/judge | killed | violates zero runtime model calls |
| Expand to general natural-language understanding | killed | unbounded, not minimal, no evidence it is required |
| Edit pinned adapter to accept sensor PASS | killed | byte-pinned verification receipt; pin break |
| Create another policy version/module | killed | duplicates existing V1; best part is no part |
| Whole-instruction multi-path refusal | killed | loses exactly the multi-item tasks OSWorld 2.0 highlights |
| Reuse clause splitter + bounded `respectively` + dual pinned assertions | selected | uses existing computed mechanisms and satisfies the pinned adapter |

“Am I sure this is the smartest approach?” Yes for this bottleneck: the change is
entirely in unpinned ledger code, reuses existing deterministic project organs,
adds no weights or world facts, and directly turns a refusal into verifiable
multi-item completion. The design was killed if any binding is not explicit: such
cases remain WAIT, never guessed.

## 5. Build

1. `canonical/runtime/osworld_verified_task_ledger_v1.py` extended in place:
   * reuses `split_explicit_subgoals` and binds quoted values only within an
     explicit clause via an explicit relation (`into`, `to`, `with`, …) or a
     bounded ordered `respectively` list;
   * rejects unbound, ambiguous, directory-valued and conflicting bindings;
   * scopes invalidation to the mutated path, so one changed item does not erase
     unrelated fresh evidence; unknown mutations (`RUN_CLI`) still invalidate all;
   * emits `ASSERT_PATH_EXISTS` + `ASSERT_SENSOR_REQUEST` for directory
     requirements, making the evidence visible to the pinned adapter;
   * requires both receipts and `fresh_measurement` admission for directory DONE.
2. `canonical/runtime/osworld_verified_agent_v1.py` composes the ledger policy
   with the admitted guest bridge in one factory.
3. `canonical/tests/test_osworld_verified_task_ledger_v1.py` extended from 11 to
   18 tests, including real subprocess receipts, two-clause binding, ordered
   `respectively`, conflict refusal, path-scoped staleness, and two full
   `BrainOSWorldAgent` runs where a real guest assertion batch executes before
   the adapter emits DONE.
4. Intent: `canonical/action_intents/MULTI_CLAUSE_EVIDENCE_BINDING_REACHES_ADAPTER_DONE_V1.json`.

## 6. Measured results

* New ledger suite: `18 passed in 0.90s`.
* Targeted combined suite (state ops, real guest ops, adapter, sensor bridge,
  ledger): `78 passed in 2.79s`.
* Repo integrity guard: `rules=17 violations=0 PASS`.
* Unified model verifier: `TOTAL 33/33 PASS`; artifact recompiled after the new
  source and evidence files were added. Digest is deliberately omitted from this
  indexed report and receipt to avoid the documented recompile cycle.
* Producer model calls: `0`. Stored parameters: `0`. Incremental spend: `$0`.

## 7. Verified / unverified / failed

**Verified in this sandbox.** Real guest processes produced PASS receipts for two
independently bound file items, for a directory with dual assertions, and through
the unmodified `BrainOSWorldAgent` adapter. Stale per-path evidence, conflicting
values, missing explicit relations, sensor-only directory evidence and GUI
instructions all stayed failed closed.

**Unverified.** No untouched OSWorld 2.1 task, SWE-bench Pro task or Terminal-Bench
task was run. No GUI/browser success, no hidden-evaluator agreement, no
single-experience learning benchmark, no unseen-environment run, no independent
verification, no benchmark score, no capability or terminal credit, and no §6
completion.

**Failed / rejected.** The earlier shared-process `test_osworld*` run had one
pre-existing order-dependent `sys.modules` pollution failure; it is unrelated to
this change and is not evidence of success. The first adapter-level test attempt
failed because the default browser controller requires a CDP endpoint; a no-op
browser controller was used because these tests exercise guest ops only. No
benchmark result was obtained.

## 8. Next §5 bottleneck

The binding is now clause-local, but it still only covers absolute filesystem
paths. The next bottleneck is to extend the same fail-closed relation grammar to
explicit application-state references that already have provenance in
`receipt_dataflow_v3`, then test on a real OSWorld 2.1 task image if one becomes
available without borrowing evaluator answers. Until the §6 criteria are met,
this remains progress only.

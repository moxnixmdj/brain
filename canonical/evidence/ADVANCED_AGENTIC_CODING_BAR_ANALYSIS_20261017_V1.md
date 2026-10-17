# ADVANCED_AGENTIC_CODING: what is actually blocking — 2026-10-17

## State

`mini_swe_superpowers_v1/COMPOSED_CONFIGURATION_V1.json`:

```
status:            BRAIN_CONFIGURED_FRESH_WAL_TASK_VERIFIED_PASS
                   __STAGE1_BREADTH_PENDING__ZERO_OPUS_CREDIT
opus_5_5_credit:   0
harness:           mini-SWE-agent 2.4.6
methodology:       Superpowers 6.4.2
composition_class: EXISTING_MECHANISM_COMPOSITION_AND_CONFIGURATION_ONLY
invention:         false
```

One task verified: wal-recovery-ordering, reward 1, 97/97 tests, 10 determinism
runs. Capability is present. Benchmark-level breadth is not yet proven.

## The bar question is already answered, and it is harder than I thought

The config encodes two bars, not one:

| Bar | Value | Source class |
|---|---|---|
| `strict_outer_opus55_bar_percent` | **66.4%** | ANTHROPIC_VENDOR_REPORTED_XHIGH_SYSTEM_RESULT |
| `matched_independent_mini_swe_opus55_reference_percent` | **59.6%** | ARTIFICIAL_ANALYSIS_INDEPENDENT_MINI_SWE_HARNESS |

The promotion rule requires `GE_CORRESPONDING_OPUS55_BAR`. **Our harness is
mini-SWE-agent, so the corresponding bar is the mini-SWE one: 59.6%.**

But `next_required_action` still demands `ESTABLISH_COMPARABLE_STAGE1_SCORE_GE_66_4`.

So the repo knowingly holds itself to the *strict outer* bar, above the
matched-harness measurement of the very model it is targeting.

## What the new sourcing adds

Independent mini-SWE-harness Opus 5.5 measurements now known:

| Source | Value |
|---|---|
| Vals AI, mini-swe-agent, avg@3 | 65.15% |
| Vals AI, fallback-adjusted | **58.08%** |
| Artificial Analysis | 59.6% |

Range: **58.08% – 65.15%**.

**Requiring ≥66.4% from a mini-SWE-based route means requiring a score that no
independent mini-SWE run of Opus 5.5 has ever been measured to reach.**

This is either the entire point, or an unfalsifiable bar:

- **The point.** NVIDIA AVO lifted Opus 5 from 30% → 100% on ARC-AGI-3 with
  identical weights, purely from system design. Configuration is *supposed* to
  add points the model cannot reach alone. Beating the model's own best
  mini-SWE run is exactly the hypothesis under test.
- **Unfalsifiable.** If the bar sits above every measured run of the target
  model on the target harness, no amount of configuration can be shown to
  clear it without the vendor's own harness and effort budget ($7.35/task at
  xhigh, which our $0 constraint forbids).

Which reading is intended is a governance decision. It should be made
explicitly, because it determines whether stage-1 is achievable at all.

## The actual blocker is executional, not architectural

This is the finding that matters most.

Ten Terminal-Bench 4.0 tasks are leased, fresh, and authorized but sit
`INSTRUCTION_UNREAD__ZERO_CREDIT_UNTIL_VERIFIED`:

```
bun-sourcemap-leak      cargo-flight-dispatch   html-js-filter
interleaved-vigenere    payments-pipeline-fix   gsea-proteomics
jax-speedrun-gpu        live-database-cutover   mp-checkpoint-consolidation
wal-recovery-ordering
```

Plus two proposed: nextjs, react. Two are already spent or aborted
(glycan-ms2 `TRANSPORT_INADMISSIBLE`, batched-eval-parity `CONTAMINATED`).

Each task executed under the V5 route is one more point of stage-1 breadth.
**Nothing about the architecture is waiting. The tasks are waiting.**

And they cannot be executed from here:

- Verification ran on an **external public runner** (`public_runner_pr: 266`,
  `workflow_run_id: 36803852769`), not on a workflow in this repo.
- `.github/workflows/` contains **no TB4 workflow**. Nothing is dispatchable
  from this checkout.

So the critical path for `ADVANCED_AGENTIC_CODING` is not a design problem I
can solve. It is: dispatch the ten leased tasks through the external runner,
one at a time, stopping on material failure, with no WAL replay.

## Honest assessment

Every remaining step on this family is blocked on infrastructure outside this
repository. I can source the bars, build oracles and fix routing — all of
which I have done — but I cannot execute a TB4 task from this sandbox.

Until those ten tasks run, `opus_5_5_credit` stays 0 and the family stays
`VERIFICATION_PENDING`, regardless of anything else built.

# The Opus 5.5 bar, sourced — 2026-10-17

The matrix's `ADVANCED_AGENTIC_CODING` bars were carried as unverified numbers.
They are now externally sourced, and one finding reframes the mission.

## The bars (confirmed)

| Benchmark | Opus 5.5 | Fable 5.1 | Opus 5 | GPT-6 Astra | GPT-5.6 Sol |
|---|---|---|---|---|---|
| Terminal-Bench 4.0 | **66.4%** | 55.8% | 52.3% | 57.9% | 37.3% |
| FrontierCode v1.1 Main | **54.4%** | 50.3% | 48.0% | 53.3% | 47.5% |
| CursorBench 4.0 | **57.8%** | 51.8% | 46.6% | — | 41.7% |

66.4% is Anthropic's vendor-reported figure at **xhigh** effort, standard error
**±2.6**. Our matrix's numbers match the launch table exactly.

## Effort and cost curve (TB4)

| Effort | Score | Cost/task |
|---|---|---|
| Low | 38.5% | $1.29 |
| Medium (default) | 57.6% | $2.94 |
| High | 64.2% | $3.88 |
| **Xhigh** | **66.4%** | **$7.35** |
| Max | 64.8% | $11.24 |

The headline number is not the default. Default is 57.6%. And Max effort scores
*lower* than Xhigh (64.8% vs 66.4%) while costing 53% more.

## Independent replication disagrees with the vendor number

| Source | Setup | Opus 5.5 |
|---|---|---|
| Anthropic (launch) | own harness, xhigh | 66.4% |
| Vals AI (2026-10-01) | mini-swe-agent, avg@3 | 65.15% |
| Vals AI **fallback-adjusted** | same | **58.08%** |
| Artificial Analysis | default fallback | 59.6% |
| benchlm (2026-10-15) | — | 64.85% |

The fallback adjustment matters: 22 of 198 task attempts were silently served
by Opus 5 or Opus 4.8. Counting those honestly drops 65.15% → 58.08%.

## The finding that reframes the mission

On the **same harness** (mini-swe-agent, bash only, avg@3, Vals AI 2026-10-01):

```
Claude Opus 5.5    65.15%
Claude Sonnet 5.5  64.14%     <-- the mid-tier model
GPT-6 Astra        59.60%
```

**Opus 5.5 and Sonnet 5.5 are 1.01 points apart on a shared harness.**

The frontier model and the mid-tier model nearly tie when you hold the harness
constant. Meanwhile the *same model* swings across a wide range depending on
which harness runs it — Anthropic's setup reports Opus 5 at 52.3%, the public
Claude Code leaderboard reproduces it at 51.8%, and other independent boards
put Opus 5.5 anywhere from 58.08% to 66.4%.

Model identity accounts for ~1 point. Harness choice accounts for many more.

This is the same result NVIDIA AVO reported (Opus 5: 30% → 100% on ARC-AGI-3,
identical weights, purely from system design), now independently corroborated
on agentic coding.

## What it means for us

Our hard constraints are `$0 incremental spend` and `zero model dependency`.
The bar we must beat — 66.4% — was produced by a rented frontier model at
**$7.35 per task**.

1. **The bar is harness-dependent, not model-dependent.** A model-free route is
   not handicapped against it; it is competing on the axis that actually
   determines the score.
2. **66.4% is the vendor's best-case.** The honest independent range is
   58.08%–65.15%. Which number we must clear is a governance decision, not a
   measurement — and it should be made before effort is spent.
3. **Effort costs money we cannot spend.** The 66.4% costs $7.35/task. Our
   constraint is $0. We must reach the bar on mechanism, not on compute.

## Sources

- Anthropic launch, benchmark table and footnotes — anthropic.com/claude-opus-5-5
- Vals AI leaderboard and methodology, incl. fallback adjustment — vals.ai/benchmarks/terminal-bench-4
- Artificial Analysis TB4 — artificialanalysis.ai/evaluations/terminalbench-4-0
- Effort/cost curve — aicatchup.com/news/claude-opus-5-5
- Corroborating tables — alphacorp.ai, codingfleet.com, codersera.com, orcarouter.ai

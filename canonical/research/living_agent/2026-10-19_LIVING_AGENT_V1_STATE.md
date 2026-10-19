# Living Agent V1 — measured state (2026-10-20)

**Authority: NONE.** This is a single-machine measurement of this tree, produced
in an Arena sandbox. It is evidence of what ran here, not a verification
receipt, not a terminal claim, and not a capability grant.

## What exists now

| Component | Path | What it does |
|---|---|---|
| Living core | `canonical/runtime/living_core_v1.py` | Black-box program induction: tables → exact programs (`filter`, `project`, `group`, `dedupe`, `sort`, `limit`) with self-chosen probes and fresh-input validation. Also episodic/semantic/procedural `Memory` with a learned salience ranker. |
| Living agent | `canonical/runtime/living_agent_v1.py` | Real POSIX computer surface, one-shot skill chunking, canary-based drift detection and repair, word learning, impasse tracking, self-directed practice, consolidating memory, snapshot/restore. |
| Shell synthesis | `canonical/runtime/shell_synthesis_v1.py` | Learns a stdin→stdout pipeline from (input, expected output) examples: typed beam search over 20 real stages, exact interpreter ordering, real-shell verification. |
| Benchmark | `canonical/runtime/living_agent_benchmark_v1.py` | Twelve spreadsheet transforms with independently written oracles, plus a projection of the repository's real file tree. |
| Acceptance | `tests/test_living_agent_v1.py` | 75 tests / 159 subtests. Real processes, real files, exact byte equality. No mocks. |
| Growth measurement | `canonical/runtime/living_agent_growth_v1.py` | Acquires four real skills at runtime and replays them on three untouched real directories. |

## Measured results

Table induction, one demonstration per family (a demonstration that shows one
example of every categorical value, numeric values drawn at random), 20
held-out instances from an independent random stream, exact row and column
equality:

```
filter_sort    20/20    raise          20/20    group_sum    20/20
month_counts   20/20    unit_price     20/20    top2         20/20
domains        20/20    dedupe         20/20    active       20/20
tax            20/20    pct            20/20    concat       20/20
TOTAL 240/240, median 0.259 s per family, max 4.9 s
```

A wider robustness sweep — 24 demonstration seeds × 12 families × 10 held-out
instances each, exact row and column equality — is **288/288**. The sweep is
run from seeds 1–24 rather than a single lucky stream: a learner that only
works on the seed it was tuned on is a lookup table dressed as a search.

Real file-tree tasks (learned on `canonical/capabilities`, verified on the
untouched directories `canonical/runtime`, `execution_guard`, `tests`):

- "files larger than 20 000 bytes, largest first" — exact on all three; the
  learned threshold is the round number `20000`, not the observed gap edge.
- "total bytes per extension" — exact on all three.

Shell skill, from a single demonstration, on files the demonstration never
contained:

- `wc -l < demo.txt` → template `wc -l < {path}`; exact line counts on unseen
  files.
- `find guard -name '*.py' | wc -l` → template `find {dir} -name '*.py' | wc -l`;
  exact file counts on three untouched copies of real repository directories,
  compared against an independent Python `rglob` count (the largest has more
  than 50 files).
- Unknown goals fail closed (`GOAL_UNKNOWN_FAIL_CLOSED`) and are recorded as
  open questions. Teaching one word (`tally`) makes the verb resolvable and
  closes the matching question.
- A simulated tool upgrade (`wc` now prints `N lines`) is detected by the
  skill's own canary; the agent observes the new output and repairs the command
  to `wc -l < {path} | awk '{print $1}'`, preserving slots, version 2. A missing
  input file is **not** repaired and stays failed.
- Self-directed practice on `sed -n '{n}p'` over a five-line file discovers
  exactly `1..5` as the success region and reports `5/7` confidence, matching
  the observed outcomes.
- Forty repeated solves consolidate to ≤ 50 % of working-set bytes while the
  skill remains the top retrieval; retired episodes keep their payloads.

## Learning a new computer skill from results alone

`LivingAgent.acquire(goal, examples)` takes only *(input file, expected stdout)*
pairs — never a command. It first tries behavioural retrieval (a skill that
already produces those results is reused even when the goal shares no word with
it), then synthesizes a pipeline and admits it only after the real shell
reproduces every example byte for byte. At least two examples are required:
one observation cannot identify a function, and pretending otherwise is the
kind of fake success this repository forbids. Goals whose result is checkable
use `fulfil` instead and need no example at all.

Measured on real repository data (CSV listings of the tree), learned on
`canonical/capabilities`, verified on the untouched `tests/` and
`execution_guard/`:

| Task | Learned pipeline | Search | First-verified run | Held-out |
|---|---|---|---|---|
| file names | `cut -d, -f1 \| tail -n +2` | 7–18 ms | 1 command | exact |
| total bytes | `awk -F, '{s+=$NF} END {printf "%.0f\n", s}'` | 1–2 ms | 1 command | exact |
| unique words | `tr -s ' ' '\n' \| sort -u` | 3 ms | 3 commands | exact |
| distinct word count | `tr -s ' ' '\n' \| sort -u \| wc -l` | 3 ms | 3 commands | exact |
| first CSV column | `cut -d, -f1` | 0.2 ms | 1 command | exact |
| upper-case text | `tr '[:lower:]' '[:upper:]'` | 1 ms | 1 command | exact |

A stated `max_length` is a hard failure, not a hint. Degenerate examples that
many mechanisms explain report `exact_hypotheses > 1` instead of pretending the
answer is unique, and a component that the interpreter models slightly wrong is
caught by real verification rather than shipped.

### Growth from real data

`python3 -m canonical.runtime.living_agent_growth_v1` learns four skills from
two real directory listings and replays them on three untouched directories:

```
learn file names          0.053s   cut -d, -f1 | tail -n +2
learn total bytes         0.024s   awk -F, '{s+=$NF} END {printf "%.0f\n", s}'
learn distinct extensions 0.102s   cut -d, -f2 | sort -u | tail -n +2
learn sort a real file    0.033s   sort
held out 12/12 exact, wall 0.33 s, model dependencies 0, spend $0
```

### Intent without examples

`LivingAgent.fulfil(goal, path)` reads the *checkable* property out of the goal
and verifies the produced text against it:

| Goal | Property | Learned | Time |
|---|---|---|---|
| sort the lines of a real file | sorted + conservation | `sort` | 15 ms |
| count how many lines | count | `wc -l` | 15 ms |
| lowercase the text | lower | `tr '[:upper:]' '[:lower:]'` | 17 ms |
| list the unique words | unique + sorted + word conservation | `tr -s ' ' '\n' \| sort -u` | 14 ms |
| count distinct words | count + unique + words | `tr -s ' ' '\n' \| sort -u \| grep -v '^$' \| wc -l` | 206 ms |

The last row is a four-stage composition on a real 19 KB policy file. A count
target resembles nothing, so line-shaped partial results would normally be
pruned; the search therefore scores a line stream by how close its length is to
the requested number ("a count is the length of something"), which keeps the
useful branch alive. That is a search heuristic, not a task rule: the same
scores are used for every goal.

A goal with no checkable property (`make the file nicer`) fails closed with
`GOAL_NOT_VERIFIABLE`; a checkable but unsupported combination (order-preserving
deduplication) fails closed with `GOAL_PROPERTY_COMBINATION_UNSUPPORTED`. The
property is re-checked on every later solve, so sabotaging the mechanism while
keeping a valid-looking postcondition yields `FAIL_CLOSED` rather than a silent
wrong answer.

## How the learner spends its questions

Induction is only honest if the questions are chosen well and the stopping rule
is about knowledge, not step count. Four rules were added after measuring where
the learner was wrong, not because they sound good:

1. **No fixed step budget.** The loop stops when one behaviour survives every
   question the data justifies and validation agrees, or when the stated
   resource (`max_probes`, `time_budget_s`) is spent. `max_rounds` remains only
   as a caller-supplied safety valve. Seed 8 of `tax` used to die at an
   eight-round cap with the correct program still in the version space; it now
   finishes in nine rounds.
2. **A pair-covering design, not independent sampling.** Sampling every column
   independently is a bad experiment: with six values per column, the
   combination that decides a threshold is one cell in thirty-six. Seed 14 of
   `unit_price` has exactly one such cell (`qty=6, total=58`, ratio 9.67, which
   separates the true threshold 10 from the tempting 9). The learner now
   includes, for every pair of columns, a table that visits every value
   combination once, and only pays for that table when cheaper questions stop
   separating the survivors.
3. **No repeated questions.** A probe or validation case that has already been
   answered is not asked again; the table is part of the paid evidence set.
   This is checked across all twelve families by a test that counts duplicates.
4. **Ambiguity is reported, not hidden.** When several programs remain that no
   justified input can separate, the simplest is returned and
   `consistent_programs` says how many still fit. The learner does not claim a
   uniqueness it cannot justify, and it does not fail a task it has actually
   solved.

Two engine changes came out of the same measurements. Expressions are compiled
to closures once and evaluated millions of times by the enumerator; the
reference tree walk is kept as the definition of meaning and a differential
test asserts both agree on every operator, including the error cases. And a
mixed numeric/text identifier column is now a total order in the benchmark
oracle instead of a `TypeError`, because a probe that finds a crash in the
oracle is the learner doing its job — the query layer must report "no answer"
rather than die mid-loop.

## Mechanisms, and why they are not a scripted pipeline

1. **Induction is search, not a route table.** Every family goes through the
   same `synthesize` (projection → filtered projection → aggregation), ordered
   suffix recovery, probe selection, and validation. No family name is visible
   to the learner.
2. **The creature chooses its own questions.** Probes maximise disagreement
   among the surviving hypotheses over a pool of deterministic coverage cases,
   row-reversal pairs, pair-covering designs and fresh draws. The reversal
   separates "sorts the rows" from "the rows happened to arrive sorted"; the
   covering design separates two thresholds that differ off the sampled cells.
3. **Learning is one-shot and chunked.** A single demonstrated success becomes
   a parameterised template; the template must pass a canary before admission.
4. **Ignorance is explicit.** Failed resolutions create impasse records;
   `open_questions()` is the creature's own list of what it does not know yet.
5. **Memory importance is learned.** Salience weights over relevance, recency,
   surprise, usefulness and cost saved are updated by retrieval outcomes; they
   are not constants.
6. **Skills are acquired from results, not demonstrations.** `acquire` sees only
   (input, expected output) pairs and must find a program that produces them;
   the same engine derives counting, listing, extraction, aggregation and their
   compositions. Nothing tells it which task it is solving.

## Honest limits

- The agent's language layer is a learned word→skill binding, not general
  natural-language understanding. A goal outside the learned vocabulary is an
  impasse that currently requires a demonstration (or a taught word), not a
  web search.
- The computer surface admits a fixed binary vocabulary inside one sandbox
  root. It is a real shell, but not a general GUI agent; GUI work remains in
  the existing OSWorld adapters and is not exercised here.
- Pipeline synthesis covers the stage vocabulary it is given (20 filters over
  text, lines and counts). A task needing an unmodelled stage is an honest
  `NO_VERIFIED_PIPELINE`, not a silent wrong answer.
- Two examples are the minimum for synthesis. When the examples are degenerate
  (identity, single-valued columns) the agent reports the ambiguity; it does not
  claim a unique mechanism it cannot justify.
- The property vocabulary is small on purpose. It grows only with checks that
  are decidable from the real output; a property that cannot be checked is not
  admitted.
- Pipeline search is bounded at four stages and a few hundred hypotheses. Deeper
  compositions and stages outside the vocabulary are honest failures.
- The repository has one pre-existing test failure unrelated to this work
  (`tests/test_bytes_canonical_wiring.py` asserts MISSION_LOCK_V9/HARVESTING_V2
  while `canonical/CANONICAL_POINTER.json` names V10/V3). It fails identically
  without these files present.
- Inductive identifiability is data-limited. If a demonstration contains no
  filtered-out row, no learner can know a filter exists; if its value gap spans
  several plausible round thresholds, the choice is a prior, not a deduction.
  The benchmark uses demonstrations that exhibit the vocabulary to keep the
  question well posed.
- Induction cost is dominated by re-enumerating the version space each round,
  so the slowest family (`tax`, nested arithmetic plus rounding and ordering)
  takes ~5 s on the slowest seeds; the measured median is 0.26 s and most
  families finish under 0.3 s. Nothing here is a claim about terminal
  capability.

## Reproduce

```
/home/user/.venv/bin/python -m pytest tests/test_living_agent_v1.py -q
python3 tests/test_living_agent_v1.py        # same suite without pytest
python3 -m canonical.runtime.living_agent_measure_v1          # 12-family table
python3 -m canonical.runtime.living_agent_growth_v1           # real-data growth
python3 execution_guard/repo_integrity_guard_v1.py
```

Provenance: stdlib only; no model calls; no network; `incremental_spend_usd`
0; `model_dependency_count` 0; no credit or terminal authority is claimed.

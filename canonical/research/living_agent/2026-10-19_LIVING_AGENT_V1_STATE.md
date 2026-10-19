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
| Acceptance | `tests/test_living_agent_v1.py` | 88 tests / 159 subtests. Real processes, real files, exact byte equality. No mocks. |
| Discovery | `canonical/runtime/living_discovery_v1.py` | Reads what this machine says it can do (`tool --help`, the tool's own definition), turns a goal sentence into an exact expected output, and proves a real command against it before admitting it. |
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
| remove the duplicate lines | unique, order preserved | `awk '!seen[$0]++'` | 16 ms |

The last row is a four-stage composition on a real 19 KB policy file. A count
target resembles nothing, so line-shaped partial results would normally be
pruned; the search therefore scores a line stream by how close its length is to
the requested number ("a count is the length of something"), which keeps the
useful branch alive. That is a search heuristic, not a task rule: the same
scores are used for every goal.

A goal with no checkable property (`make the file nicer`) fails closed with
`GOAL_NOT_VERIFIABLE`; a checkable combination with no exact mechanism — "keep
the *last* occurrence of each duplicate", which shares the word "duplicate" but
names a different function — fails closed with
`GOAL_PROPERTY_COMBINATION_UNSUPPORTED`. The property is re-checked on every
later solve, so sabotaging the mechanism while keeping a valid-looking
postcondition yields `FAIL_CLOSED` rather than a silent wrong answer.

Every candidate is also compared to the deterministic target **byte for byte**
before it is admitted. The interpreter only nominates; a pipeline that merely
looks right is rejected. That check earned its place immediately: a word-count
pipeline whose reference output matched the target produced 1181 instead of 1182
on the real 19 KB file, and was replaced by one that reproduces the exact bytes.

## Extending the computer's own vocabulary

A creature that may only use binaries someone pre-approved can only do the
approved things.  `discover()` grows the vocabulary at runtime with no model,
no network and no table of commands:

1. **The goal is read as a specification.**  `readings()` derives the exact
   expected bytes from the goal's own words: the verb, the unit it applies to,
   and whether it applies *inside* each unit ("reverse each line" reverses the
   characters of every line) or to the units themselves ("reverse the lines"
   reverses the order of the lines).  A unit-less goal such as "reverse the
   file" keeps both readings alive.
2. **The machine describes itself.**  Every executable answers `--help` with a
   usage line and a one-sentence definition ("Reverse lines characterwise").
   That text is the machine's own account of its capabilities, written by the
   tool's authors.
3. **Four tiers, cheapest first.**  a word the machine already uses as a name
   (`rev` for "reverse", 25 ms); a differential experiment over the tools whose
   documentation mentions the goal's words (55 ms warm); the ranked
   documentation list; and finally every tool on the machine tried on a small
   probe (2.3 s, last resort).  The first tier that produces the exact bytes
   wins, and the winner is remembered.
4. **Nothing is believed on a keyword.**  A candidate is admitted only when the
   real shell reproduces the expected bytes on the file, twice, *and* on a
   probe the creature designs against the reading.  A tool whose documentation
   lies is rejected and the rejection is logged; a test builds exactly that
   lying tool and checks that it is thrown out.
5. **Ambiguity is refused, not guessed.**  If two readings are both satisfiable
   ("reverse the file" is satisfied by both `rev` and `tac`), the creature says
   `GOAL_AMBIGUOUS` and names both commands instead of silently picking one.
   An unknown verb is an impasse on the record and admits nothing.

Measured on this machine:

```
reverse each line   rev notes.txt   25 ms   found by name, verified twice + probe
reverse the lines   tac notes.txt   55 ms   rev tried first and rejected; differential
same goal again     from memory     12 ms   no documentation read, no search
ambiguous goal      refused         --      GOAL_AMBIGUOUS: rev | tac, impasse recorded
unknown verb        refused         --      GOAL_NOT_VERIFIABLE, nothing admitted
```

The documentation index is cached per machine and keyed by the parser that
produced it, so the first contact with a new machine costs ~2.4 s once and
every later discovery is tens of milliseconds.  State-changing and
network-capable binaries are never candidates: extending what the creature can
*read* never extends what it may *do*.

### Trying a stranger without paying for it

Probing a candidate means executing code nobody vetted. Two failures were found
by watching the tree rather than the code:

- A real sweep left **seventeen empty `gz*` files** in the repository root: an
  installed tool writes beside its input. Every trial now runs in a private
  throwaway directory holding its own copy, with `HOME` moved there too, so a
  candidate can create, rewrite or delete anything it likes and the creature
  still has its files.
- A tool that had answered *correctly* was being recorded as failed with code
  `-9`. The reader killed the child as soon as the pipe drained, racing its exit.
  EOF now means "wait for it", and only a child that outlives its budget is
  killed. Both bugs were invisible in aggregate counts and are now covered by
  real tests (`a_stranger_tool_is_probed_in_a_throwaway_directory`,
  `a_tool_that_closes_then_exits_is_not_killed`,
  `an_endless_writer_is_stopped_not_read`).

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

- The agent's language layer is a learned word→skill binding plus the verb/unit
  readings above, not general natural-language understanding.  A goal outside
  those readings ("number the lines" needs `nl`'s exact layout, which is a
  convention this creature cannot deduce) is an impasse on the record, not a
  guess.
- Discovery admits *bare* invocations (`tac FILE`).  A capability that needs a
  flag or a program argument -- field- and width-parameterised tools -- is not
  reachable this way even when the tool exists: the search would have to invent
  arguments, and inventing is not verifying.
- "Unique" has two readings and only one of them is a function of the data
  alone: keeping the first occurrence (implemented) and keeping the last
  (refused, recorded).  Sharing a word is not sharing a meaning.
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

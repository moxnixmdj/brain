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
| Acceptance | `tests/test_living_agent_v1.py` | 125 tests / 182 subtests. Real processes, real files, exact byte equality. No mocks. |
| Discovery | `canonical/runtime/living_discovery_v1.py` | Reads what this machine says it can do (`tool --help`, the tool's own definition), turns a goal sentence into an exact expected output, and proves a real command against it before admitting it. |
| Growth measurement | `canonical/runtime/living_agent_growth_v1.py` | Acquires four real skills at runtime and replays them on three untouched real directories. |

## Measured results

A twenty-request battery (`HeldOutBatteryTests`) teaches each request on two
files and answers a third that the search never saw; every expected output is
computed by an independent implementation in the test file.  All twenty are
byte-exact, including four that used to be admitted as a plausible-looking
wrong answer: a positional `tail` standing in for a word filter, a reversed
lexical sort standing in for a numeric one, a `tail -n +2` standing in for a
length filter (correct on both taught files, wrong on the held-out one), and an
unanchored pattern standing in for "starts with" (it also selects every line
that merely contains the letter).  The last two are refused now because the
sentence is read as a *predicate on a line* and the pipeline is run on probe
lines the examples never contained.


Table induction, one demonstration per family (a demonstration that shows one
example of every categorical value, numeric values drawn at random), 20
held-out instances from an independent random stream, exact row and column
equality:

```
filter_sort    20/20    raise          20/20    group_sum    20/20
month_counts   20/20    unit_price     20/20    top2         20/20
domains        20/20    dedupe         20/20    active       20/20
tax            20/20    pct            20/20    concat       20/20
TOTAL 240/240, median 0.17-0.25 s per family across runs, max 2.6 s
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
learn file names          0.044s   tail -n +2 | cut -d, -f1
learn total bytes         0.023s   awk -F, '{s+=$NF} END {printf "%.0f\n", s}'
learn distinct extensions 0.087s   cut -d, -f2 | tail -n +2 | sort -u
learn sort a real file    0.093s   sort
held out 12/12 exact, wall 0.45 s, model dependencies 0, spend $0
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
reverse the lines   tac notes.txt  106 ms   warm documentation cache; shortlist sweep
same goal again     from memory     12 ms   no documentation read, no search
first goal on a     any             1.5 s   reading 324 self-descriptions, once ever
  new machine
number the lines    nl notes.txt   107 ms   the numbering layout is part of the reading
number blank lines  nl -b a        222 ms   the style value comes from nl's own help
ambiguous goal      refused         --      GOAL_AMBIGUOUS: rev | tac, impasse recorded
unknown verb        refused         --      GOAL_NOT_VERIFIABLE, nothing admitted
```

**A goal is answered only when it is fully understood.**  Every content word
must be part of what the reading (or the property) explains, or nothing is
answered.  "number the lines" and "the number of lines" are different
functions, told apart by the partitive "of"; "sort in descending order" and
"number in roman numerals" share their words with capabilities the creature has
and ask for something it does not, so they are refused and the unmodelled words
("descending", "roman", "numerals") go on the record.  The alternative -- drop
the words it does not model and answer anyway -- is how a system ends up
confidently wrong.

Three costs, measured rather than assumed: a name lookup costs one process;
a documentation question costs a one-time 1.3 s scan of the machine (324
`--help` calls, cached to disk, 10 ms afterwards); the exhaustive sweep of all
324 tools costs 1.9 s and is only reached when the first two tiers have nothing.

Two defects were found by watching the machine rather than the code:

* `tool --help` is still running a stranger's code. A real scan left `gz*`
  files in the repository root because one installed tool writes beside its
  working directory even when asked to describe itself. The whole scan now runs
  in one throwaway directory with `HOME` moved there.
* The documentation cache stored only the tools that answered with parseable
  text, so a third of the inventory was re-asked on every session (0.3 s per
  agent). A tool that says nothing is a fact about the machine and is cached
  like any other.
* The file name was removed from a goal as a *substring*: a file called
  `n.txt` deleted every letter "n" from the sentence, turning "lines" into
  "lies" and making a clear request ambiguous. Names are removed as words now.

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

## Arguments, from the tool's own help

A filter that takes no arguments is a small part of a computer.  The rest needs
`sort -k 2 -t ,`, `fold -w 40`, `nl -ba`.  Hard-coding those is a task table;
guessing them is worse.  The creature does neither:

1. **The space is the tool's own option list.**  `tool --help` is parsed into
   options: spellings, whether a value is wanted, the placeholder name and the
   sentence the authors wrote.  It is cached with the rest of the documentation,
   and re-parsed when the parser changes.
2. **A tool may also name its own vocabulary.**  Some arguments are not
   quantities but a small closed set whose meaning the tool defines itself:
   `nl` says "STYLE is one of: a — number all lines; t — number only nonempty
   lines; …".  That list is parsed, and a value whose own sentence matches the
   request is tried first.  `nl -b a` is reachable this way, and could not be
   reached any other way.
3. **A value must be grounded.**  A number the request names binds an option
   that takes a number; a separator the example data actually contains binds an
   option that takes a character; a switch must have a word of the request in
   its own description.  Anything else is not "unlikely" -- it is unjustified,
   and is not tried.  That is also why `--output=FILE` is never bound: a
   filename is not in the evidence.
4. **The examples decide.**  Every candidate is a real command run by the real
   shell on every example; the first that reproduces the bytes exactly wins.
   Bundles are ordered simplest first (the tool alone, then one argument, then
   combinations), so the least machinery that fits is the one admitted.
5. **Discovery uses the same argument search.**  `discover()` has two exact
   specifications -- the real file and the probe it designs -- which is exactly
   what the argument search needs.  That is how a file with blank lines gets
   `nl -b a`: the bare tool reproduces every non-blank line but not the blank
   ones, and the missing style is read out of nl's own option list.
6. **Failure is knowledge.**  If no mechanism fits, the goal, the examples and
   every tool that was tried are recorded as an impasse; a single demonstration
   closes it.  If a tool documents a flag it does not implement, it is rejected
   and revoked like any other guess.

Measured on this machine (cold documentation cache, first contact):

| Request | Two examples say | Learned | Cost |
|---|---|---|---|
| sort the rows by the second column, comma separated | exact rows | `sort -k 2 -t ,` | 103 ms, 14 runs |
| fold each line at 40 characters | exact bytes | `fold -w 40` | 95 ms, 8 runs |
| fold each line at 12 characters (same creature, later) | exact bytes | `fold -w 12` | 80 ms |
| number the lines | exact bytes | `nl` | 72 ms |
| number the lines, blank lines included | exact bytes | `nl -b a` | 84 ms |

The width row is the point: the number came from the request, not from a
constant, and the second request was answered with a different binding by the
same code.  A decoy named `fold` that documents `-w, --width=WIDTH` and ignores
it is tried first (it is first on `PATH`) and rejected: the run shows
`["-w", "40"]` in the discovery log with `verified=false`, nothing admitted, and
the request fails instead of producing a skill that silently does nothing.

## Composition: an unknown mechanism followed by a known grammar

A single command is a small part of what a computer can do; the useful answers
are usually a pipeline.  The creature now composes **one documented mechanism**
with the grammar it already knows, and it chooses both ends of that composition
by experiment:

1. **Recall by the machine's own words.**  The request's words, plus the words
   the data itself makes meaningful (a repeated comma makes "field", "column",
   "delimiter" worth asking about), are matched against each tool's *entire*
   self-description -- summary and every option line -- because a tool's useful
   vocabulary usually lives in its options ("select only these fields"), not in
   its one-line summary.
2. **Binding by evidence, not by resemblance.**  A written number binds a
   quantity ("40 characters" → `-w 40`); an ordinal next to a unit noun binds a
   position ("the second column" → `-k 2`, `-f 2`); a character the data
   contains binds a delimiter (`-t ,`); a placeholder that names a file is never
   bound at all.  A pair of arguments is only formed from two *different kinds*
   of placeholder, because a style and a style compete while a delimiter and a
   field really do need each other.
3. **Fingerprinting.**  Every candidate is really run once, in parallel, in a
   throwaway directory.  A wrong guess costs one process and is discarded before
   it can influence anything; only invocations that actually change the text
   are composed.
4. **The grammar finishes the job.**  From what the document's tool produced,
   the existing grammar is searched (pure computation, no processes) for a
   suffix that reproduces every example.  The whole pipeline is then run for
   real on every example, byte for byte, before it is admitted.
5. **No authority left behind.**  Trying a stranger means admitting it for one
   run; when the search ends, every tool that did not win is revoked, so a
   failed guess cannot widen what the computer may execute.

Measured on this machine (cold documentation cache on first contact):

| Request | Two examples say | Learned | Cost |
|---|---|---|---|
| sort the rows by the second column, comma separated, and keep the first two | the exact rows | `sort -k 2 -t , \| head -n 2` | 0.12 s, 52 runs |
| the same request again, new file | — | from memory | < 1 ms |

Neither `-k 2` nor `-t ,` is in the grammar, and no single documented tool
produces the answer, so this pipeline exists nowhere in the source: it is
assembled from the machine's own option list and the grammar, and admitted on
exact bytes.

### What the experiments changed

* **The grammar had magic counts.**  `head -n 3`, `tail -n 3` and `sed -n '3p'`
  were fixed stages.  With two examples, `head -n 3 | sort | tail -n +2`
  reproduced both exactly -- a right answer to a different question that fails on
  the next file.  Those stages are gone: counts come from the examples
  (`head -n 2` is instantiated when the target has two lines), never from a
  constant in the vocabulary.  `test_an_overfit_pipeline_is_not_admitted` builds
  exactly that coincidence and requires the *keyed* mechanism plus exact
  behaviour on two held-out tables.
* **The inventory was recomputed on every tier** (`executables()` walked three
  directories ten times per goal) and every admission re-hashed the binary.  Both
  are facts about the machine that do not change while a goal is solved, so both
  are cached -- keyed by inode and file stamp, so a changed binary is re-hashed.
* **Composition cost 0.61 s before these fixes**, mostly in grammar searches over
  candidates that could never fit.  Pruning to invocations whose arguments are
  *grounded* (strength ≥ 4: a quantity, a position, a separator) cut the
  candidate set from 64 to 52 and the time to 0.12 s.

## Two specifications, and what to do when they disagree

An example is not a demonstration of a goal; it is a *result*.  The request and
the examples are independent statements about the same transformation, and a
pipeline can satisfy one while contradicting the other.  Three failures found
by real probes, and the checks that now make each of them impossible:

**A pipeline that fits the bytes and ignores the sentence.**  Asked to sort
rows by the third column of a pipe-separated table and keep the first two, with
two example outputs that do not follow from that request, the creature answered
`head -n 2 | sort -r` -- both examples exactly, not one word of the request.
It now extracts what the request *names*: a position beside a unit noun ("the
third column" -> position 3), a named separator ("pipe separated" -> `|`), and
the operations stated outright ("keep the first two" -> `head -n 2`, "distinct"
-> `sort -u`, "count" -> `wc -l`).  A verified pipeline that omits any of them
is not admitted; the search moves to composition, then to a documented
mechanism, and then -- if a pipeline fit the bytes and contradicted the
sentence -- fails with `EXAMPLES_CONTRADICT_GOAL` and records
`reason: evidence_conflict` with the unexplained items and the pipeline that
produced them.  Refusing costs an answer; guessing costs the truth.

**A mechanism that never uses the argument it was given.**  `ptx -g 2 -F ,`
binds a gap width to "position 2" and a flag truncation string to "pipe
separated".  Followed by `sort -u | wc -l`, it answers "3" on two tables whose
second column has three distinct values -- and "3" again on a third table whose
second column has two.  Wording cannot settle this, so the creature runs the
experiment: hold the named column constant and a count over it must *move*;
change the columns the request never mentions and it must *not*.  `cut` moves
(3 -> 1, unchanged under the other probe) and `ptx` does not; the coincidence
is rejected on behaviour, not resemblance.  Held-out files then answer 2 and 1.

**A sentence that describes a property of each line.**  "The lines longer
than 20 characters" was answered by `tail -n +2`: both taught files happened to
drop their short first line, and the held-out file did not.  The sentence is
not a hint about which rows are wanted; it is a *predicate* -- `len(line) > 20`
-- and a predicate can be evaluated on text nobody supplied.  So the reading is
turned into a function, checked against the taught examples, and then the
pipeline is run on probe lines the examples never contained: a matching line at
the front, a non-matching line at the end.  `tail -n +2` fails the first probe;
`awk 'length($0) > 20'` passes both.  The same rule covers "start with b"
(anchored `^b`, since an unanchored `b` also selects every line that merely
contains one -- caught on a held-out line), "end with z", "at least 3
characters", and the containment reading that was already checked.

**An ordering that depends on the order the rows arrived in.**  "Sort the rows
by the second column" was answered by `sort -k 2 -t , | sort -r`: on three rows
a lexical sort followed by a reversal can equal the numeric order exactly, and
it stops being right on the fourth row.  The question the sentence settles is
whether the answer depends on the *column* or on the *arrival order*, and the
experiment is free of assumptions: reverse the input rows.  A pipeline ordered
by column 2 returns the same bytes; a pipeline that ends in a reversal returns
different ones, and is refused.  This caught the false fit above and nothing
legitimate: `head -n 4 | sort -k 2 -t ,` and `sort -k 2 -t , | tail -n 2` both
pass, because the selections the sentence names are part of its meaning.

**A qualifier nothing in the sentence spelled out.**  "Sort by the second
column" over the values 10, 2, 1, answered 1, 2, 10, is a *demonstration* of
numeric ordering; the words do not say so, but the bytes the user produced do.
The examples are allowed to state a manner the sentence leaves out: when the
named column parses as numbers and the demonstrated order is numeric (or
descending), the tool's own documented switch for that reading joins the
candidate as evidence, and the exact bytes still decide.  This is how
`sort -k 2 -t , -g` and `sort -k 2 -t , -g -r` are learned without the sentence
ever saying "numerically" or "descending" -- and how "sort the rows by the
second column, numerically" keeps its stated `-g` when the examples agree.

**Arguments that became shell syntax.**  The documented-mechanism path joined
an option bundle with spaces, so `-t |` became a pipe and the *file name*
became the next command (`BINARY_NOT_ADMITTED:one.psv`).  Every argument is now
quoted before it reaches the shell; `sort -k 3 -t '|'` sorts a pipe-separated
table and survives as data.

### What this costs

The fast paths are untouched: a goal the grammar already answers as stated
("count the distinct values in the second column, comma separated" ->
`cut -f 2 -d , | sort -u | wc -l`) is 0.18 s cold and 0.008 s from memory;
a composed pipeline is 0.14 s (comma) and 0.19 s (pipe, quoted argument), 52
processes apiece.  The checks themselves are three extra runs, and only when a
count over a named column is asked for.

### What is still missing

Composition places one documented mechanism first, or one grammar stage that
the sentence names before it.  A pipeline with two unknown mechanisms, or one
whose mechanism sits between two arbitrary stages, is outside the search -- it
would need a product over the documented surface at every depth.

When two verified pipelines both fit every example and disagree on data nobody
has shown, the creature currently admits the one with more evidence and does
not ask.  The next step is the one a sentient learner would take: construct the
input that separates them, and ask for *that* example instead of guessing.  It
is cheap -- two runs and one comparison -- and it is the difference between
knowing what needs to be known and assuming it.

## Instant: what is remembered, and why it is remembered that way

A creature that learns quickly is not one that searches quickly; it is one that
does not search twice.  Three kinds of memory now sit between a request and a
search, cheapest first, and each one is re-verified before it is believed:

| Memory | What it holds | What it costs to use | Why it cannot lie |
|---|---|---|---|
| skill | the exact pipeline that answered this goal | 1 run (canary replay) | the canary bytes |
| mechanism | a tool with the *kinds* of argument it was given | 4–6 runs | re-bound from the new request and data, re-verified |
| earned stage | a verified invocation as a word of the grammar | 4–6 runs | rebuilt from the machine, run for real |

Measured on this machine, same machine, same day:

| Request | Runs | Time |
|---|---|---|
| sort rows by column 2, comma separated (first time) | 6 | 0.05 s |
| the same kind, new column and new separator (3, semicolon) | 6 | 0.09 s |
| the same sentence on space-separated data (re-bound) | 4 | 0.06 s |
| sort rows by column 2 *numerically* (order demonstrated by the examples) | 8 | 0.12 s |
| sort rows by column 2, descending and numeric (two qualifiers) | 6 | 0.08 s |
| the first field of each line, colon separated | 3 | 0.05 s |
| lines longer than 20 characters (a length filter) | 6 | 0.04 s |
| lines that start with a letter (anchored) | 4 | 0.06 s |
| the number of characters in each line | 2 | 0.02 s |
| the first three characters of each line | 2 | 0.03 s |
| the last two characters of each line (a slice, not a range) | 2 | 0.03 s |
| the third character of each line | 4 | 0.05 s |
| translate commas to semicolons (both named) | 3 | 0.05 s |
| lines that contain a given word | 2 | 0.07 s |
| count the distinct values in column 2 | 50 | 0.21 s |
| the same words after a snapshot and restart (new data) | 1 | 0.01 s |
| a new request of a learned kind, after a restart | 4 | 0.07 s |

The first-time cost fell from 52 runs to 6 without changing a line of the
search space, by ordering the same candidates differently, and the comma
projection from 68 to 3 once the values the sentence names were tried first.  Four priors, in
order: the request *names* the tool ("fold each line at 40 characters"); the
bundle's arguments are backed by two independent grounded facts rather than
one (a position *and* the separator the data contains); among equals the fewer
arguments; then how much of the tool's own documentation the sentence uses.
The search stops at the first confirmed pipeline instead of fingerprinting
every candidate first, so an unexamined candidate costs nothing.

A stated manner is a specification, not decoration.  "Sort them numerically"
is not satisfied by a sort that happens to fit the examples: on three rows a
truncated reverse sort can agree with the numeric order and disagree on the
fourth, which is how a confidently wrong pipeline gets admitted.  A manner
adverb is now read against the help text of the tool actually in the pipeline
(`-n, --numeric-sort` is sort's own definition of "numerically"; the same
letter in `ls` means something else), the resulting switch joins the argument
bundles as *evidence* rather than as a guess, and evidence now sorts before
parsimony so that a three-flag bundle implementing a word of the request
outranks a shorter bundle that ignores it.  The switch is load-bearing in the
test: removing it from the admitted command turns the numeric answer back into
the text order.

Recall after a restart used to report a different schema from first-time
learning -- it had no `commands_run` at all, so an instant answer looked like an
answer that measured nothing.  Every outcome now carries the same fields.  A
solution learned by an 11-run search and then restored from a snapshot answers
the same request on data it has never seen in **1 run, 0.013 s**, and the count
is the real count.

Naming a tool also had to open the recall gate: `fold`'s own summary is "Wrap
input lines in each FILE, writing to standard output", so a sentence about
lines shares exactly one word with it, and the two-word bar dropped the one
tool the request had named.  A named tool is now a candidate however little its
documentation overlaps, and the same goal costs 11 runs instead of 78.  A switch that merely shares a word with the goal still
composes, but it no longer makes a two-argument bundle look better evidenced
than the one-argument bundle it extends -- `fold -w 40 -b` is not stronger than
`fold -w 40`.

Two design mistakes were paid for in processes before they were fixed, and both
are the kind that look like optimisation but are really the wrong abstraction:

* **Remembering the sentence.**  The first memory was keyed by the words of the
  goal, with numbers and separators removed.  Two requests that need the same
  mechanism ("sort the rows by the second column, comma separated" and "keep
  the last two rows of the table, sorted by the second column") share almost no
  words, while two that share every word may need different arguments.  The
  record is now keyed by the *mechanism* -- tool plus the kinds of argument it
  was given -- and the values are bound fresh every time.
* **Searching with earned stages.**  An earned stage is a real process.  A
  grammar search applies every stage to every intermediate text, so including
  earned stages turned one search into seventeen child processes.  The search
  now uses only stages that cost nothing to apply; earned stages are tried
  deliberately, one at a time.  First-time composition went from 58 runs to 4
  on the paths that recall, and the suffix search never spawns a process.

The shared stage memo is the third piece: one invocation on one text is a pure
function of the machine, so the same binary with the same arguments on the same
input is never run twice in a session, whichever part of the search asks.

### Arguments that are not options

Half the machine's mechanisms are not switches.  `tr ',' ';'` translates one
character into another, `grep error` selects lines by a pattern, and neither
value appears in any option list -- the only place either tool says it consumes
them is its usage line, `tr [OPTION]... STRING1 [STRING2]` and
`grep [OPTION]... PATTERNS [FILE]...`.  The synopsis is the tool's own statement
of what it eats, so it is read: a placeholder that names a pattern is bound to
the word the sentence names (only if that word occurs in the data, so it cannot
be invented), and a placeholder that names a character set is bound to the
characters the sentence names, *in the order it names them*.  Order is meaning
here: "replace every comma with a semicolon" is `tr , ';'` and the reverse
request is `tr ';' ,`; sorting those two operands alphabetically would translate
in the wrong direction.  Both are learned in **3 runs, 0.05 s**, and the two
commands differ exactly as the two sentences do.

When the sentence names *every* value a command consumes -- two characters, or
the pattern it wants kept -- the request is already the invocation, so that
command is tried before the grammar search.  A request that also names an
operation ("keep three", "count", "distinct") cannot be one command, and the
shortcut stands down.  Lines that contain a given word: 2 runs, 0.06 s; the
same kind of request about a different word: 2 runs, from memory.

The same synopsis decides how the file reaches the tool.  A tool that declares
a file operand takes the path as an argument; one that does not would read the
path *as data* and fail with "extra operand", so the file is fed on standard
input instead.  `grep` takes a file, `tr` does not, and nothing has to know
either fact in advance.

A request that names two characters therefore names every value a command
needs: no search is required at all, and `_fully_named_mechanisms` tries that
command before the grammar search -- two runs, and the admitted answer is exact
on files it never saw.

### What the examples say when the sentence does not

"Sort the rows by the second column" over 1, 2 and 10 is a numeric request even
though the word is missing: the shown answer is the numeric order, and no
lexical order of those values produces it.  The examples are half the
specification, so a demonstrated manner is evidence, exactly like a stated one
-- `-g` joins the bundle, and the same goal without it finds the plain sort.
The opposite demonstration must not inherit it: the same words over data whose
shown answer *is* lexical learn `sort -k 2 -t ,` and answer "20" before "7" as
text.  Both are measured on held-out files where the two readings disagree.

### The sentence is an oracle when it defines a function

"Show only the lines that contain error" does not just describe an example: it
says what the answer is for *any* text.  That is a specification, so it is
checked on a text the examples never contained -- the source with a matching
line moved to the front and a non-matching line appended.  `tail -n +2` fits
both original files by accident (the word sat on the second line of each) and
fails the probe immediately, because it selects by position.  The same question
is asked of pipelines admitted by the grammar search and by composition: two
paths, one standard.

A request of the same kind then costs 2 runs instead of 13, because the
mechanism (`grep PATTERNS`) and the value the sentence supplies are both known --
memory of the mechanism, not of the sentence.

### A fit is not an ordering

`sort -k 2 -t , | sort -r` reproduces `1, 2, 10` on two examples because
reversing a lexical sort of those values happens to agree with the numeric
answer.  Two behavioural questions separate the readings, and both cost one
process:

* **Row order.**  An answer that claims to order by a column must not change
  when the same rows arrive in a different order.  A pipeline that depends on
  the input's row order is answering from the file, not from the column.
* **The column's values on other rows.**  Move the same values onto different
  rows and the answer must still be ordered the way the example was.  Reversing
  a lexical order is still lexical; it cannot survive this question.

The probes only reject: a pipeline that drops the column, a projection, or a
request that itself selects rows by position ("take the first four") is never
refused for failing a question that does not apply.  With them in place the
coincidental pipeline is refused and the numeric key is found instead, and the
admitted answer is right on a third file whose numeric order is the reverse of
both its file order and its text order.

### Where the sentence says an operation happens

"Keep the first two" and "take the first four" are not stylistic variants.  On
five rows "sort them, then keep two" and "keep two, then sort them" agree; on
six they do not.  A keep-verb is a *suffix*, a take-verb is a *prefix*, and the
position is checked against the admitted pipeline -- a pipeline that keeps two
before sorting is refused as an answer to a sentence that says to keep them
afterwards.  `head -n 4 | sort -k 2 -t ,` and `sort -k 2 -t , | head -n 4` are
different functions, and the request names which one it wants.

### Two characters with no spelling

A shell command cannot carry a TAB: a literal one is a control character and
dash has no escape for it, so tab-separated data -- a very large part of a
computer -- was unreachable.  The portable spelling `-t "$(printf '\t')"` is
allowed, and *only* it: a command may contain no other `$(...)` and no
backticks, because a substitution would run a program the admission check never
saw.  Both halves are tested against the real shell.  (Before this, `-t |`
was joined unquoted and became a pipe; every bound argument is now quoted, so
it stays data.)

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
- Argument binding is limited to what the evidence can ground: quantities the
  request writes, positions it names of a unit, characters the data contains,
  and closed value lists the tool itself documents (`nl -b a`).  An option whose
  value is a filename or a free-form word (`-o FILE`, `--compress-program=PROG`)
  is never bound -- a demonstration is the only way to teach those, and inventing
  a value would be a guess dressed as an experiment.
- Composition places the documented mechanism **first** and at most once.  A
  pipeline with two unknown mechanisms, or one in the middle, is outside what
  this search reaches; it would need a product over the documented surface at
  every depth, which costs far more processes than the answer is worth.
- "Unique" has two readings and only one of them is a function of the data
  alone: keeping the first occurrence (implemented) and keeping the last
  (refused, recorded).  Sharing a word is not sharing a meaning.
- The computer surface admits a fixed binary vocabulary inside one sandbox
  root. It is a real shell, but not a general GUI agent; GUI work remains in
  the existing OSWorld adapters and is not exercised here.
- Pipeline synthesis covers the stage vocabulary it is given (20 filters over
  text, lines and counts), plus the stages the request itself states (a length
  filter, a per-line length, a character slice) and the ones already earned.
  A task needing an unmodelled stage is an honest `NO_VERIFIED_PIPELINE`, not a
  silent wrong answer.
- Reverse-of-input is one of those honest refusals.  `tac` writes the last line
  first; `sort -r` does not -- it reverses a *lexical* order, which agrees with
  the arrival order only when the file happened to be sorted.  `tac` is not in
  the agent's admitted binary vocabulary, so "print the lines in reverse order"
  is refused on an unsorted file rather than answered with `sort -r` (the two
  are indistinguishable on a sorted one, which is exactly how the wrong answer
  used to be admitted).  Adding a read-only filter to that vocabulary is a
  one-line change with an authority decision attached, so it is left as a
  recorded gap rather than made silently.
- Two demonstrations that are identical are *one* demonstration, and are
  refused as `TOO_FEW_EXAMPLES`.  Without that check a single example plus its
  duplicate admits whatever fits it, which is how a probe of my own learned
  `sort | tail -n +2` for "lines that start with b".
- Two examples are the minimum for synthesis. When the examples are degenerate
  (identity, single-valued columns) the agent reports the ambiguity; it does not
  claim a unique mechanism it cannot justify.
- Coverage is lexical.  A goal phrased with a synonym outside the reading or
  property vocabulary ("flip", "invert", "tidy up") is refused as unverifiable
  rather than mapped onto the nearest known verb.  Teaching a word
  (`teach_word`) or demonstrating the command are the two ways through.
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

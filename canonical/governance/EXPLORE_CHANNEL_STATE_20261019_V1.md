# The assume-nothing channel — state and next frontier

Owner goal: `BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE`.
Canonical home of the objective: `OWNER_ACTIVE_GOAL_20261018_V1.md`. **Re-read `brief` after every
condensation, before any consequential action.**

The user's restatement that governs this work:

> the machine can do anything on the computer by itself and the learning must be instant …
> I don't want a strict program like "do 1, 2, 3 and that's it." … I want a sentient machine, a
> sentient creature that knows what needs to be known and learns it in the fastest way and in the
> optimal way, and memorizes and retrieves what is important.

## What the machine can do now (measured, not asserted)

Give it a sentence naming a real file, and it **does the job** — leaving the real file behind —
with nobody telling it what any program does.

It practises on a synthetic stand-in, keeps the exact command that worked as a *recipe*, then runs
that command on the file it was asked about. Measured end to end with `.gz`/`.bz2`/`.zip` deleted
from the hand-written table and no seed to compose from, so every earlier fallback was empty:

| Sentence | Command it found and ran | Result |
|---|---|---|
| `compress notes.txt into notes.txt.gz` | `gzip -c notes.txt` | 99 B |
| `archive notes.txt into notes.txt.zip` | `zip notes.txt.zip notes.txt` | 239 B |
| `compress notes.txt into notes.txt.bz2` | `bzip2 -c notes.txt` | 124 B |

Each output was then opened with an **independent** reader (`gzip`, `bz2`, `lzma`, `zipfile`,
`tarfile`) and compared byte for byte with the original. All match. Archives contain `notes.txt`,
not an absolute path, because the command runs in the file's own directory and is handed its name.

Entry points: `cenv.apply(recipe, src)` and `cenv.perform(goal, cwd)`;
`composer_route_v1.route(goal, cwd)` now ends in `PASS__PERFORMED_ON_REAL_FILE`.

The two tests that carry the weight:

- **It generalises rather than memorises.** It learned on a synthetic stand-in, so the test makes
  it compress a *second, different* file. Memorising the stand-in would fail here.
- **The recipe is a command, not a story.** The argv is run in an ordinary subprocess with the
  learner nowhere near it. If that works, the recipe is real.

`perform` refuses a goal naming a file that does not exist
(`OPEN__NO_EXISTING_INPUT_FILE_IN_GOAL`): inventing an input to look capable is worse than
stopping.

### Discovery alone (no real file)

Give it a sentence naming an output file, and it finds which program produces that file **with
nobody telling it what any program does**.

| Goal | Plan found | Verification |
|---|---|---|
| `compress the input into out.gz` | `['run_gzip']` | `ROUND_TRIP_OK` |
| `make a bzip2 archive out.bz2 …` | `['run_bzip2']` | `ROUND_TRIP_OK` |
| `compress the data into out.xz` | `['run_xz']` | `ROUND_TRIP_OK` |
| `archive these files into out.tar` | `['run_tar']` | `ROUND_TRIP_OK` |
| `archive these files into out.zip` | `['run_zip']` | `ROUND_TRIP_OK` |

Second asking comes from memory: 1.10s → 0.41s, `from_memory=True`.

Reachability:

- `curriculum_v1` → channel `explore` (cost 2.0, tried **last**; it is the only channel still
  standing when every other has nothing).
- `composer_route_v1` → falls back to `cenv.discover(goal)` after registered capabilities,
  synthesis and documentation have all failed. Status `PASS__DISCOVERED_BY_ACTING`.

Order through `discover()`, cheapest first:

1. **recall** — this shape of problem was solved before; replay it and re-verify.
2. **one action** — the shortest plan that can exist; each program tried on its own.
3. **search** — `environment_learning_v1` over sequences, only if neither worked.

In every path the produced file is opened with the library that owns the format before anything
is called a success.

## The five defects fixed here, and the lesson in each

All five are the same mistake: deciding in advance what the answer is called instead of looking
at what happened.

1. **The output name was invented** as `input.txt + suffix`. The goal said `out.gz`; the machine
   looked for `input.txt.gz`. It discarded the only thing that named the file — and that name is
   exactly what must be handed to `zip out.zip input.txt`, which does nothing without it.
2. **A file *called* `out.zip` was accepted as a zip.** `gzip -c` writes gzip bytes under any name
   you like. Now the file is opened by the library that owns the format.
3. **`installed_programs(limit=400)` on a machine with 603** silently returned the first 400 by
   name and lost `zip`, `xz` and the whole back half of the alphabet. A cap that quietly hides
   most of the computer is an assumption wearing the costume of a measurement.
4. **Invocation forms ran against the directory the previous one left behind.**
   `gzip out.gz input.txt` compresses `input.txt` and deletes it, so the later form that would
   have worked ran against a file that no longer existed. Each form now starts from the seed.
5. **Stdout was written over the target unconditionally.** `zip out.zip input.txt` builds a real
   archive *and* prints `adding: input.txt`; we overwrote a good file with chat. Stdout is now
   only a fallback for programs that did not write the file themselves.

Also, from the previous commit: `program_actions` judged success by looking for `src + ".gz"`, so
`run_bzip2` really produced `input.txt.bz2` and reported `False`. An effect is now whatever
appeared, whatever it is called.

## Files

- `canonical/runtime/computer_env_v1.py` — the computer as a learnable environment.
  `installed_programs`, `programs_for`, `output_name`, `ComputerEnv`, `program_actions`,
  `_verify_plan`, `_single_step`, `discover`.
- `canonical/runtime/curriculum_v1.py` — `explore` channel, `_try_explore` delegates to
  `cenv.discover` (one implementation, not two that drift).
- `canonical/runtime/composer_route_v1.py` — discovery fallback, status
  `PASS__DISCOVERED_BY_ACTING`.
- `canonical/tests/test_computer_env_v1.py`, `canonical/tests/test_composer_route_v1.py`
  (`DiscoveryFallbackTests`), `canonical/tests/test_curriculum_v1.py`.

## Test rules that are not negotiable

- All tests extremely hard and **only real**. Operationalised as the **sabotage rule**: a test is
  only real if breaking the thing it covers makes it fail.
- Sabotage scorecard for this work: rubber-stamp verification 1, stdout overwriting the archive 2,
  no reset between forms 6, ignoring the goal's filename 1, restoring the 400 cap 2; plus
  `act()` claiming success on failure 11, `reset()` not resetting 6, `state()` ignoring content 1,
  `restore()` a no-op 1, hand-written program list 1.
- `STATE_PATH` in `curriculum_v1`, `transfer_learning_v1`, `program_synthesis_v1`,
  `documentation_mining_v1` is bound **at import time**: the env var does nothing once imported.
  Patch the module attribute, or a test writes into the repository's real memory.

## Regression

`python3 -m pytest` is unavailable here; use `python3 -m unittest`.

Control run (these changes, no new test module): **721 tests, 23 bad, identical to baseline —
0 new failures.** The 23 are pre-existing. `test_jit_knowledge_v1` and
`test_extended_capability_registry_v1` are **order-dependent**: they pass in isolation and the
failing set shifts between runs of identical code. They import nothing this work touches.

## Goals that name no output file — attempted and deliberately cut

`_requested_suffix` is the gate: **no output filename, no attempt at all.** "count the lines",
"make the picture smaller", "find the largest file" are refused with `OPEN__NO_OUTPUT_FORMAT_IN_GAP`
before a single program runs. **That refusal is correct and is made twice elsewhere in the brain**
(`cli_capability_acquisition_v1`, `cli_contract_inference`), with the reason written down:

> A goal that never says what it wants produced gives us nothing to check an effect against, so any
> program that prints anything would "work" — **`ls` would be learned as a capability.**

**Do not remove that check.** Solve it by supplying something to verify against.

### What was tried, and why it is not in the tree

The model-free oracle — independent implementations agreeing is evidence — is real in principle.
`wc -l`, `grep -c ''`, `awk 'END{print NR}'` and `sed -n '$='` genuinely all answer `4` for a
four-line file. But selecting candidate programs by whether their **help text mentions the goal's
words** selects everything, and it produced three confident wrong answers:

| Asked | Answered | Via |
|---|---|---|
| `count the lines in notes.txt` | `Linker options` | `c89`, `c99`, `cc` — **one compiler under three names** |
| `how many words` | `------>` | `bzless`, `bzmore` — the same script twice |
| `show the first lines` | `Linker options` | again |

Each was followed by a new filter for the new junk: aliases, pager prompts, help dumps. The last
cannot be closed — `c89 --target-help` prints a manual that is **not** the one `--help` prints, so
no "it printed its own help" test catches it. **A growing list of exclusion rules is a strict
program**, which is exactly what the owner rejects. Deleted, not left weakened: a feature that
answers "count the lines" with a linker manual is worse than one that says it cannot.

If this is retried, the bar is: agreement must be between **distinct binaries**
(`real_binary`, already written), the output must not be any manual the program can print, and
selection must not be lexical alone.

## What was kept from that attempt: choosing a flag by what it means

`flag_descriptions()` parses a program's own help into flag→meaning pairs, and `flags_for_goal()`
takes the flags whose documented meaning the goal mentions. Measured:

| Goal | Flag chosen |
|---|---|
| `count the lines in notes.txt` | `--lines`, `-l` |
| `count the words` | `--words`, `-w` |
| `how many bytes` | `--bytes`, `-c` |
| `sort in reverse` | `--reverse`, `-r` |

Two traps, both now tests: the program's own name is not a clue ("sort in reverse" otherwise lights
up every flag whose text says sorting), and the filenames in the goal are not clues. `line` must
match `newline` by containment or every flag of `wc` scores alike, since they all say "counts".

The goal flows into `invocation_shapes`, so the flag the goal asked for becomes a real command.

## Next frontier

1. **A verifiable criterion for goals that name no output file.** The refusal is right; what is
   missing is something to check against that does not come from a suffix — "smaller than before",
   "contains the count", "is a list of the files". The consensus attempt above failed at
   *selection*, not at the idea of agreement; a sound version needs candidates chosen by behaviour
   rather than by help-text word overlap.
2. **Programs needing options with values.** `convert in.png -resize 50% out.png` needs a flag
   *and an argument*. `flags_for_goal` now finds the flag; supplying a value for it is open.

Both are the same question the last five defects were: stop deciding in advance what the answer
looks like.

---

## Round 6 and 7 — both frontiers above are now closed

### 2 (closed): programs needing options WITH VALUES

`perform("resize in.png to 50% as out.png", cwd="/home/user/pic")` is measured end to end:

```
11.3s  pass=True  status=PASS__APPLIED_TO_REAL_FILE
argv  : convert -resize 50% in.png out.png
verify: ROUND_TRIP_OK          independent read: 200x100 -> 100x50
```

Six defects were found by measuring, not by reasoning:

- `_FLAG_LINE` matched `-\w`, i.e. ONE character, so `-adjoin` was read as flag `-a` meaning
  "djoin". ImageMagick writes `-c, --long`, `--long` and `-fullname`; the regex now takes the
  whole flag.
- `flag_descriptions(limit=80)` truncated ImageMagick's 248 flags, so `-resize` was invisible
  to the machine. Raised to 400.
- Program selection was by NAME subsequence: `programs_for(".png")` never returns `convert`,
  because "convert" contains no p, n or g. The one program on this machine that can resize an
  image was never once tried. `programs_for_goal` now selects by whether a program's manual
  documents a flag MEANING what the goal said.
- Value-bearing shapes must be tried BEFORE positional ones. In the usual order
  `convert in.png` won by dumping the image to stdout into `out.png` — a file that exists, is
  named `.png`, and was never resized.
- A sandbox seeded with `input.txt` cannot teach an image operation. `ComputerEnv(seed_file=...)`
  now practises on a copy of the real input; the original is never touched.
- `_uses_goal_value` requires the winning command to contain a number from the goal. Without it
  "resize to 50%" was silently answered by copying the file.

And one defect that was worse than a wrong answer:

- The learner DESTROYED THE USER'S INPUT FILE. "compress notes.txt into notes.txt.gz" was
  answered with `gzip {input}`, which reaches the goal by deleting notes.txt; `gzip -c {input}`
  reaches the same goal and leaves it. Forms that consume the input are now held back and
  returned only when nothing gentler reaches the goal — a preference, not a ban, so
  "move a.txt to b.txt" still has a route.

### 1 (closed): goals that name no output file

The consensus oracle deleted last round failed at SELECTION. Selection is now behavioural: a file
is BUILT to hold exactly 7 of the thing the goal names, and a program that prints 7 has proved it
measures that thing — without anyone reading its documentation. A second file holding 13 must
also come out 13: printing the right number once can be a coincidence, following the
construction cannot. The manual is still read, but only to narrow the field, never to decide.

Measured on a real 23-line file, every answer is the true one:
`lines -> 23` (wc and grep agree), `words -> 138`, `characters -> 566`, `bytes -> 566`.

Four defects found by measuring:

- The probe was built from identical lines, so "how many lines" and "how many runs" were the same
  question and `uniq --count` passed while counting runs. The probe now holds distinct lines.
- egrep, fgrep and rgrep are three-line shell scripts that exec grep: three votes from one
  program. The exec is followed to the program that actually does the work.
- The proven command was discarded and the real file measured with a different form of it — bare
  `wc notes.txt` after `wc --lines` was the thing that worked — a different quantity reported as
  the same answer. The exact argv now carries over.
- `shuf --repeat` never stops talking. Read without a cap it filled memory until the machine
  killed the learner: no exception, no traceback, a run that vanished at fifteen seconds and
  looked like nothing had happened. Output is read on a deadline and capped.

It refuses rather than invents when the goal names no single countable thing, when the input file
is absent, and when nothing on the machine tracks the constructed answer.

### What is still open

- **`awk`/`sed`-class answers are not reached.** `awk 'END{print NR}'` needs a PROGRAM argument,
  not a flag plus a pattern, so no shape tried can express it. Agreement is therefore often 2
  (wc and grep) where a human would name four.
- **The first question of a kind costs seconds** (9–46s), because the machine has to find out
  which commands measure at all. It is cached per machine, so the second is instant, but the
  first is not yet fast.
- **Words/characters/bytes rest on one instrument.** The value is right and the instrument is
  tracked, but it would be better to have two.
- **No path from this repo to a dollar**; nothing here runs while neither of us is typing.

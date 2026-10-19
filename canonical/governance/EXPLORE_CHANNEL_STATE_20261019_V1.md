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

## Next frontier

The gate is `_requested_suffix`: **no output filename in the goal, no attempt at all.** So the
machine cannot yet be asked to *resize an image*, *count the lines*, *find the largest file*, or
*make the picture smaller* — none of those name an output file. Every one of them is refused with
`OPEN__NO_OUTPUT_FORMAT_IN_GAP` before a single program is run.

That is the next real limit. Two sub-problems:

1. **Goals with no output filename.** The goal predicate has to come from the sentence rather than
   from a suffix — "smaller than before", "contains the count", "is a list of files".
2. **Programs needing options.** `convert in.png -resize 50% out.png` and `gpg --armor --sign`
   need flags, not just file arguments. Programs will state their own interface when asked
   (`--help`); reading it is not a table, it is interrogation.

Both are the same question the last five defects were: stop deciding in advance what the answer
looks like.

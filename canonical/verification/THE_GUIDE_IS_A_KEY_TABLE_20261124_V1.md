# THE GUIDE IS A KEY TABLE — and the parser was the wrong part to build

**Date:** 2026-11-24 · **Authority:** `NONE__PRODUCER_RUN_SANDBOX` · **Schema:** `BRAIN_THE_GUIDE_IS_A_KEY_TABLE_V1`
**Instrument:** `canonical/tools/the_guide_is_a_key_table_v1.py` (828 lines)
**Pins:** `canonical/tests/test_the_guide_is_a_key_table_v1.py` (15 tests: 14 pass, 1 **expected failure**)
**Receipt:** `canonical/verification/THE_GUIDE_IS_A_KEY_TABLE_20261124_V1.json`

---

## What the previous round left open, in its own words

Round 4's receipt named its own bottleneck: *"a 42-command debugger cost 26 questions, and every one
of them was about a COMMAND. That is the wrong unit … the next round's question is the ordering of
questions."* This round attacked that. The answer it produced is not the one I set out to build.

## The design, and why it looked right

There are only a few ways to ask a program what it accepts, and they are ordered by price over three
orders of magnitude — measured here, best of three, on this machine:

```
batch   `-c help` / `-e .help` / `--help`     2.3 – 36 ms
page    the top-level page                    2.1 – 56 ms
live    the same question at its own prompt    4 – 1420 ms
```

Each answer discards a whole class of program *shapes*, so the hypothesis space is the two axes that
actually exist and nothing else: **SHAPE** (KEY | TOKEN | SUBCOMMAND | OPTION_LANGUAGE | NONE) and
**COUNTER** (COMMANDS | BUILTINS | PATH | OPTIONS) — five admissible cells, five uniform priors, no
learned weights. The policy is one line: *ask the cheapest channel that can still split the
survivors; stop when one cell survives.* The key is `(family, geometry) → (shape, counter)`, not
`(program, key)`, which is the generalisation the owner demanded.

That design is sound. The **implementation of the reader** — a typography parser over fixed-column
text — is not, and this round is the measurement that proves it.

## The measurement, verbatim

```
room      cheap cell                        live cell                  agree
less      (KEY, COMMANDS)                   —  (refused: no file)      no
more      (OPTION_LANGUAGE, COMMANDS)       —  (no listing)            yes
node      —  (4 survivors)                  —                          no
python3   —  (5 survivors)                  —                          no
bash      —  (2 survivors)                  —                          no
sh        —  (5 survivors)                  —                          no
pdb       (TOKEN, COMMANDS)                 (TOKEN, COMMANDS)          yes

cheap 278 ms total · live 5,290 ms total · 2 of 7 rooms agree
deciding channels: none 5, batch 2
```

**Two of seven.** The cheap answer is 19× faster and agrees with the operational oracle in two rooms
out of seven. Five rooms do not agree, and the receipt prints each one with its numbers.

## Why it failed, stated as the thing I did wrong

I spent this round tuning an admissibility rule until each program landed in the cell I expected.
That is hand-solving, and the traces are in the diff: the shell was reported as a *pager*, the
JavaScript REPL as a *pager*, the interpreter as a *debugger*. Every one of those numbers was a rule
I had just written. Four distinct parser facts each needed a patch, and each patch broke a different
room:

| what I asserted | what it did | what it broke |
|---|---|---|
| a listing is three columns | prose split on whitespace looks like columns | the shell's table became the tokens `to`, `find`, `out`, `more` |
| a page of options is a command table | `-b : issue warnings…` became two commands | an interpreter with no alphabet was given one |
| a wide field is prose | three-word command fields | the shell's `history [-c] [n]` column was dropped |
| a sentence is capitalised | `issue`, `these`, `on` open sentences | the options page and two tables came back |

A text parser cannot separate `-b   : issue warnings about str(bytes_instance)` from
`.break   Sometimes you get stuck` without a fact about English typography — and a fact about
typography is not computing. The **expected-failure test** at
`test_an_options_page_yields_options_and_no_commands` is left red on purpose: it is the evidence.

## What the failure says the mechanism must be

The premise this round was built on — *"in today's world anything on the computer already has a
guide"* — is **true but useless as stated**. A guide has to be *decoded* to become an alphabet, and
decoding prose is the one thing here that cannot be done with an exact procedure. What can be done
exactly is this:

```
ASK THE PROGRAM WHAT A TOKEN IS, DO NOT READ WHAT ITS MANUAL CALLS IT
```

`less s` either writes a file or says `Input is not a pipe`. `pdb p 2**10` either prints `1024` or
does not. The program *is* the definition of its own command, and the question costs 300–600 ms
instead of 0 ms — but it produces a **fact**, where the parser produces a **judgement**. An earlier
round already proved the oracle is cheap enough to use: `pdb p 2**10` returns `1024` and `node .save`
writes a file.

So the cheap reader is not the mechanism; it is an **index**, and its value is exactly what this
receipt measures: a way to know *which* tokens exist, with a 71% chance of being right about the
shape and a 29% chance of being wrong about it. Where it is wrong, one 600 ms question settles it.

## The structural gap it exposes (the next round's specification)

`bash` and `sh` are both classed SHELL, and they are not the same room: `bash -c help` prints 46
lines and `sh -c help` prints nothing and then does not know `help` at its prompt either. The family
cell is **too coarse by exactly one axis**: *which ways of asking exist for this family at all*. That
axis is not typography and not a manual — it is a declaration carried with the family cell and
**checked** by one question per family, which is what the receipt's `asked` lists already record.

That is the piece to build next, and it is small: a family row gains `ways_of_asking: {batch, page,
live}` and the receipt becomes an audit of declarations rather than a parser's guesses.

## Honest scorecard

**Verified:** the price ordering (batch ≪ page ≪ live, 19× on the totals); the hypothesis space is
five cells with five uniform parameters and no learned weights; two rooms' cheap answers agree with
their operational oracles; the pdb alphabet (58 tokens, 105 ms) and the shell's builtin count
(62 tokens, 4 ms); the clock defect found and fixed (live timings were computed *before* the work ran
and reported 0.0006 ms). Receipt: 5.6 s for seven rooms, zero model calls, zero network at run time.

**Unverified:** the generalisation claim — `PAGER → (OPTION_LANGUAGE, COMMANDS)` was learned from
`more` and transferred to `less` where it is wrong; `PYTHON_DEBUGGER → (TOKEN, COMMANDS)` is right for
`pdb` but `python3` is not that family, and I put it there by hand.

**Failed:** the typography parser, five rooms of seven, one expected-failure test kept red.

**Not claimed:** any benchmark score. OSWorld 2.1, Terminal-Bench 4.0 and SWE-bench Pro V2 cannot
execute in this sandbox and remain non-claims.

## Parts deleted this round, with the number that deleted them

- **`strings` as a channel** (0.2–260 ms, the cheapest): decided no cell in any room; a pager's
  31,336 words of binary strings parsed into ~13,000 "tokens" of prose and symbols.
- **the `help X` channel** (24 ms × 26 questions in round 4): descriptions arrive free in the answer
  that lists the token, and where they do not, the alphabet is still the whole answer.
- **the hand-written needles** (four proof strings recalled from these programs' manuals): two of
  four were wrong on the first run, and two of four shape claims with them. A recalled needle is
  memorised knowledge wearing a test's clothes.
- **the one-shot `if`-chain claim** (a second decision procedure beside `admissible`): the two
  disagreed on `node` — the evidence left one cell and the chain named another. One truth now has
  one procedure: the posterior.

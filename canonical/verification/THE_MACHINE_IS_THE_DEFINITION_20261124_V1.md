# THE MACHINE IS THE DEFINITION — the parser demoted, the probe promoted

**Date:** 2026-11-24 · **Authority:** `NONE__PRODUCER_RUN_SANDBOX` · **Schema:** `BRAIN_THE_MACHINE_IS_THE_DEFINITION_V1`
**Instrument:** `canonical/tools/the_machine_is_the_definition_v1.py`
**Pins:** `canonical/tests/test_the_machine_is_the_definition_v1.py` (18 tests, 0.008 s)
**Receipts:** `…THE_MACHINE_IS_THE_DEFINITION_20261124_V1.json` (8 rooms) · `…_CELLS_20261124_V1.json` (cells + transfer)

---

## What round 5 convicted, and what this round did about it

Round 5 proved a typography parser cannot decide what a program's commands are: **2 of 7 rooms**
agreed with the program's own live answer, because separating

```
-b     : issue warnings about str(bytes_instance)      <- one option + a description
.break    Sometimes you get stuck, this gets you out    <- one command + a description
```

is a fact about English typography, and a fact about typography is not computing.

So the parser is demoted to an **index** and the **machine** becomes the definition:

```
INDEX      the program's own answers, parsed loosely. Allowed to be noisy. Costs milliseconds.
DEFINE     run each candidate beside a control of the SAME SHAPE, in a throwaway clone,
           and keep it only if the machine treats it differently from a meaningless token.
ENUMERATE  the page teaches the form (`-c command`, `-e script`), the form fetches the table,
           the table becomes the next index.
```

The classifier is a **differential**, and that is the entire idea: a token is defined when no
meaningless token of the same shape produces the same observation. The control is not decoration —
without it `sh -c help` answering `help: not found` looks exactly like a definition, and a round-3
instrument read precisely that as *"the shell has no command table"*.

Four outcomes, each a measurement: `MOVES_STATE`, `DEFINED`, `NOT_DEFINED`, `BLIND` (with the reason
printed — irreproducible screen, candidate identical to its controls, or a room mis-defined).

## The measurements, verbatim

```
rooms nobody tuned this round on (4 programs from PATH chosen by a stated rule)
  corepack     index  8  confirmed  8   argv=8   prompt=0   blind=0
  pygmentize   index 11  confirmed 10   argv=11  prompt=1   blind=2
  nodejs       index  4  confirmed  1   argv=4   prompt=3   blind=2
  npx          index  0  confirmed  0   argv=0   prompt=0   blind=0   (the page IS pnpm's shim)
  precision of the index: 0.704   probes: 106   time: 0.6 s

rooms earlier rounds used (not for tuning — for the record)
  less   index 81 confirmed 36   bash index 64 confirmed 11   node index 5 confirmed 2
  sh     index  0 confirmed  0   (dash has no help of any form; the receipt says so)

the form the environment teaches, learned from its own page
  bash: "Type `bash -c help' for more information about shell builtin commands."
        -> form [-c, help] -> 411 words -> index 1 -> 64 tokens
```

`bash` is the round's cleanest win: with three universal forms the shell's index was **one** token;
after reading the sentence where the shell teaches its own form, the index is **64** and the machine
confirms **11** of them.

## The cells, and the transfer — 1 of 3, reported as 1 of 3

```
cell            taught by     held out    plan predicted   actual    correct
OPTION_TABLE    pygmentize    corepack    argv             argv      YES
KEY_TABLE       less          more        prompt           none      no
BUILTIN_SET     bash          sh          argv             none      no

cell verdicts from the run (never from a name)
  pygmentize OPTION_TABLE  corepack OPTION_TABLE  less KEY_TABLE
  nodejs OPTION_TABLE (!)  bash OPTION_TABLE (!)  more UNPROVEN  sh UNPROVEN
```

Two cells agree with their page, three are contradicted by the run, and the transfer holds in one of
three attempts. **Held back on purpose, named now so that naming them later cannot look like
choosing them afterwards:** `tar`, `grep`, `find`, `openssl`, `git`, `python3`, `vim` — declared with
their cells, **not run** in this receipt.

## Why the failures are structural, not tuning bugs

`sh` and `more` publish no alphabet in any form tried and the receipt says `UNPROVEN` rather than
inventing one. `bash` is verified DEFINED at argv and therefore labelled `OPTION_TABLE` — the label
is **coarse by exactly one axis**, the same gap round 5 named: a cell says *how the alphabet was
reached*, not *what the alphabet is*, so a shell that answers `-c help` and a tool that answers
`--help` land in one cell. That is the next round's first fix, and it is one field, not a redesign.

`nodejs` is reported as `OPTION_TABLE` because exactly one token (`-`) is verifiably defined and a
single confirmation cannot distinguish a table from a page.

## Twelve defects this round found by running it

Every one of these produced a *plausible number* before it was fixed, which is why they are listed:

1. `Reading(name, clock(), work())` reads the clock **before** the work — live channel priced at
   0.0006 ms (round 5).
2. The room's files were readable, so a pager's `No such file: alpha.txt` put **my filename** in the
   observation and the differential compared rooms instead of programs → the room is sealed
   exec-only.
3. The token was substituted **inside the output**, so the one-character candidates rewrote
   `alpha` → `alp<T>a` → length-1 candidates classified BLIND.
4. Controls of the same shape legitimately differ (`--zz` unknown, `--qx` missing argument) →
   "my controls disagreed" was reported as blindness → BLIND now requires the candidate to look
   like a control **and** the controls to be non-unanimous.
5. Six output lines per signature made rooms BLIND by noise → three.
6. A probe mutated the shared room, so a destructive token poisoned the next measurement → every
   probe gets its own clone.
7. The index called round 5's per-program channel table and **swallowed the KeyError**, so four
   unseen programs had an index of zero and were reported as having nothing to define.
8. `bash --help` is options only and `bash help` is `command not found` → the index saw 1 of 62
   tokens until the shell's own sentence taught the form.
9. `pygmentize`'s usage page (several lines opening with `[-O …`) was mistaken for JSON and its
   whole index thrown away → a data structure announces itself by its FIRST character.
10. `corepack`'s command tree was zero tokens → indented command trees are read as whole paths.
11. A pager repaints a whole screen per write, so no two runs match → first-screen baseline, only
    the delta counts; a prompt candidate must reproduce or it is BLIND.
12. Absolute paths into the base room do not exist inside the trial clone (`Cannot find module`) →
    the document is named **relative**, and the cwd is the confinement.

## Honest scorecard

**Verified:** the differential (`sh: <T>: not found` normalises; a definition differs from its
controls); index precision **0.704** on four programs never met before, 106 probes, 0.6 s; `bash`'s
taught form turning an index of 1 into 64 tokens; `corepack` 8 confirmed of 8; 18 pins green.

**Unverified:** the cell labelling (coarse by one axis), the transfer (1 of 3), the held-out bank
(named, not run).

**Failed:** `sh` and `more` define nothing; three cell claims contradicted by their own runs;
two of three transfers wrong.

**Not claimed:** any benchmark score. OSWorld 2.1, Terminal-Bench 4.0, SWE-bench Pro V2 cannot
execute here and remain non-claims. `MOVES_STATE` was never produced by any room this round — no
verified definition with a visible file effect was found, and that field is empty in the receipt.

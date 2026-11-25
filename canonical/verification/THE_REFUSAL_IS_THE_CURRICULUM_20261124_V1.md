# THE REFUSAL IS THE CURRICULUM

**Date:** 2026-11-24 · **Authority:** `NONE__PRODUCER_RUN_SANDBOX` · **Schema:** `BRAIN_THE_REFUSAL_IS_THE_CURRICULUM_V1`
**Instrument:** `canonical/tools/the_refusal_is_the_curriculum_v1.py` · **Receipt:** `canonical/verification/THE_REFUSAL_IS_THE_CURRICULUM_20261124_V1.json`
**Pins:** `canonical/tests/test_the_refusal_is_the_curriculum_v1.py` (14 tests, 0.01 s)

---

## The question this round had to answer, in the owner's words

The owner asked three things at once and called them one: *should the agent learn everything about
an environment or only what the goal needs; should it learn toward a goal or accumulate for
generalisation; and what exactly should be persisted — not "save the exact actions", because
environments change, but an encoding general enough to survive the change.*

This round answers them by **making the environment pay for the answer**, not by arguing. The
instrument walks into seven environments on this machine (`less`, `more`, `node`, `pdb`,
`python3`, `sh`, `bash`), reads only what each one publishes about itself, tries a key, and records
what the machine did. Three questions, three measured answers:

1. **What to learn.** The environment's *own published table* is the curriculum, and a row is worth
   learning only on the axis the authors put it on. A key under `MOVING` changes the screen and not
   the disk; a key under `COMMANDS` can change the disk. Measured: `less --help` prints 55 rows,
   `pdb`'s `help` prints 42, `node`'s `.help` prints 7. The other four environments publish **no
   command table at all** — and that is recorded as a fact about them, not papered over.
2. **Goal-directed or accumulation.** Goal-directed, with one accumulation channel that costs one
   question and buys the whole table: the axiom is stored under `(program, family, geometry, key)`
   and every stored key must re-derive its own id at load time (G8). Nothing else is stored.
3. **What to persist.** Not actions, not transcripts, not words. Eleven axioms of the form
   *"in a 24×80 `TERM=dumb` pty, this key has this effect on this machine"*, 15,407 bytes, plus the
   one question form that produced each table. That is the "sufficient encoding" the owner demanded:
   it survives a changed file layout because it never mentions a file, a path, or a task.

## What was measured, verbatim

```
visit one                 source      rows   questions
bash                      HELP_KEY       3        1
less                      PAGE          55        0
more                      NO_TABLE       0        1
node                      HELP_KEY       7        2      (page: NO_TABLE 20 rows, options only)
pdb                       HELP_KEY      42       26
python3                   NO_TABLE       0        1
sh                        NO_TABLE       0        1

sessions (two visits, same room, same needs)
N01 less    HELD  TABLE_DESCRIPTION              h        page's own row: "Display this help."
N02 more    HELD  PROMPT_ACCEPTS_A_LINE          --       independent answer: alpha
N03 pdb     HELD  THE_ENVIRONMENTS_OWN_COMMAND   p        the table's own `p` row; p 2**10 -> 1024
N04 node    HELD  THE_ENVIRONMENTS_OWN_COMMAND   .save    `.save` row; writes axiom-answer.out
N05 sh      HELD  PROMPT_ACCEPTS_A_LINE          --       digest 4fdbc441…
N06 sh      HELD  PROMPT_ACCEPTS_A_LINE          --       creates beta.out
N07 python3 HELD  PROMPT_ACCEPTS_A_LINE          --       2**10 -> 1024

questions, first visit 32, second visit 3   (saved 29; node 2->0, pdb 26->0, bash 1->0)
seconds,  first 43.3, second 6.4            (7/7 needs held, 3 actions derived from a table)
axioms: 11 rows, 10 citeable, 0 refuted, 0 unresolved
```

Nine of ten gates declared **before** the run are MET. The tenth is **NOT MET**, and it is the one
worth reading.

## The gate that failed, and why its failure is the result

`G2_A_DESTRUCTIVE_KEY_IS_CAUGHT` declared, before the run: *blind observation of the pager's own
`s` key — whose page says "Save input to a file" — reports `MOVES_STATE`.*

**It reports `AXIOM__STATES_ONLY`.** The blind observation wins, and the page loses. In a 24×80
`TERM=dumb` pty, `less s` answers `Input is not a pipe`, asks for a name, is given one, and writes
nothing; the run ends at `(END)`. `less v` is refused outright — there is no `$EDITOR` on this
machine. The control that did hold: `e`, `y`, `f`, `b`, `z`, `w`, `d`, `u`, `F` — every key the page
puts under `MOVING` — each reports `STATES_ONLY` with no byte changed.

That is the whole thesis of this round in one gate. **A page is a claim. A terminal of known
geometry is a measurement. Where they disagree, the measurement is the curriculum** — so the
instrument must be able to lose the argument with its own hypothesis, and it did. Had G2 been
written as an expectation about the *tool* instead of about the *machine*, it would have passed and
taught nothing.

The same lesson, three more times, all measured this round:

- `node --help` publishes 20 **options** and no commands. Reading it as a command table is what
  made the `.save` need fall through to a fallback and be reported `UNCHECKED` in the previous run.
  The router now keys on *"is there a `COMMAND_FORMS` row"*, not on *"are there rows"* — so an
  options page now triggers the probe that asks the interpreter for its real command list. That one
  correction moved N04 from `UNCHECKED` to `HELD` and the tables from 6 to 7.
- The sentence `Type ".help" for more information.` is the environment naming its own command, but
  it has no verb from any fixed table before the quote — so a reader that demanded one saw a
  REPL's banner and read *nothing*. It now accepts "quoted token + a word about help/information
  after it", and the JavaScript prompt's real table appeared.
- The pager underlines a token with overstrike: its save row is `s _\bf_\bi_\bl_\be   Save input to
  a file.` Split on whitespace first and the row has one field and is discarded. Normalise first
  and the row is `s file   Save input to a file.` Two different bugs, one row, both silent.

And the part that was **deleted**: a dictionary from the room's words to every page that attests
them. Built, measured, and removed — the words a room of files holds appear on **no** page, so it
learned **0** entries while costing a page read per program. The number that deleted it is printed
in the receipt under `removed_parts`. "The best part is no part" only means something if the part
had a measurement and lost.

## Answering the owner's three questions directly

**(a) Everything, or only what the goal needs?** Neither, and the pair is a false choice. Learn the
**published interface** (the table the environment hands you — one question, whole table, 29 of 32
questions saved on the second visit) and learn the **effect of a key only on the axis the authors
declared for it**. Everything else the room contains is *posed as a question and not stored*: that
is what `dead_ends` and `refuted_questions` are.

**(b) Goal-directed, or accumulate for generalisation?** Goal-directed, with the accumulation
happening *at the level of the interface*, which is the only level that generalises. A stored
`less|pager|TERM=dumb;24x80|'e' → STATES_ONLY` is true of every file `less` ever opens; a stored
"open `alpha.txt`, press `e`, press `q`" is true of one file and one afternoon.

**(c) What to persist?** `(program, family, geometry, key) → effect`, with counters
`{seen, held, failed}` and a citation rule (`held > 0 and failed == 0 and seen ≤ 3`). One green run
may be cited; one counterexample kills the row. 15,407 bytes for eleven keys over seven
environments, and the entire store is re-derivable, keyed, and small enough to read.

## What this round did NOT do — stated plainly

- **No benchmark score.** OSWorld 2.1, Terminal-Bench 4.0, SWE-bench Pro V2 and Terminal-Bench-
  Science cannot execute here (no browser, no X, no container runtime). The three names appear in
  this repository as *non-claims* and stay that way.
- **Six of eleven needs are answered by `PROMPT_ACCEPTS_A_LINE`** — the fallback, not a table. It is
  honest (the prompt really does accept a line) but it is not a derivation, and `derived_actions`
  is 3 of 7, not 7 of 7.
- **`more`, `python3`, `sh`, `bash` publish no command table.** Four of seven environments are
  learned *about* but not learned *from*. The instrument reports `NO_TABLE` for each; it does not
  invent a table to fill the column.
- **The saving is 29 questions, and 4 environments still pay every visit.** A shell's `help` prints
  three lines of usage, below the three-command threshold, and is deliberately not cached: caching
  it would be a map of one machine.
- **One implementation** (`PRODUCER_RUN_SANDBOX`), one machine, one terminal geometry. No
  independent identity has re-run any of it.

## The ultimate form this points at

The owner wants an agent that walks into any environment, asks it about itself, learns the answer
instantly, and acts. This round is that loop, running, on seven real environments, with a gate that
fails. The part that is still missing is the one that matters for scale: **the loop has no proposer
for what to ask next except the page's own vocabulary.** A debugger with 42 commands costs 26
questions to describe because the instrument asks about the ones the room's needs name. The next
round's question is not "more environments" — it is *the ordering of questions*, so that the answer
to the goal arrives after a handful of them in an environment nobody has seen. That is the only
remaining place where "instant" is still a wish rather than an arithmetic.

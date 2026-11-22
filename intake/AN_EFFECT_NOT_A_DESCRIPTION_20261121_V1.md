# An effect, not a description

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls, 0 parameters, 0 network
**Receipt:** `intake/RECEIPT_AN_EFFECT_NOT_A_DESCRIPTION_20261121_V1.json` · **Instrument:** `canonical/tools/an_effect_not_a_description_v1.py` · **Tests:** `canonical/tests/test_an_effect_not_a_description_v1.py` (7 passed)

---

## 0. The gap this closes

Three rounds measured what can be **known** about an unseen machine: shapes, producers,
pointers, contracts. Then the follower reported **1 flag** for `pygmentize` whose real interface
is `-l`, `-f`, `-o`, `-g`. It parses its own arguments by hand, so there is no `add_argument` to
find. **It knew a flags list existed. It could not invoke anything.**

Knowledge that cannot become an effect is not capability. This is the first receipt in the
series that leaves a changed world behind.

---

## 1. The law

> **A program states its own type signature, and on request it renders its own vocabulary. A
> plan is the signature instantiated against that vocabulary — it is derived, never recalled.**

`pygmentize` says, in its own words:

```
usage: pygmentize [-l LEXER | -g] [-F FILTER[:options]] [-f FORMATTER]
                  [-o OUTPUTFILE] ... [INPUTFILE]
```

Read as a type: there are slots named `LEXER`, `FORMATTER`, `OUTPUTFILE`, and a positional
`INPUTFILE`. Ask it `-L formatters` and it answers **35 names**; `-L lexers` and it answers
**927**. The alternatives inside `[-l LEXER | -g]` name the question; the rendering answers it.

**No table of known invocations exists anywhere in the instrument.**

---

## 2. The amnesiac control

A plan is only interesting if it was *derived*. So every plan is produced in a **fresh
subprocess** handed exactly three things — the usage line, the vocabulary, the goal — and
nothing else. No example invocation, no memory of previous rows, no carried state.

| goal | plan derived under amnesia | effect |
|---|---|---|
| python → html | `-l python -f html -o OUT IN` | **EFFECT** |
| json → html | `-l json -f html -o OUT IN` | **EFFECT** |
| shell → html | `-l bash -f html -o OUT IN` | **EFFECT** |
| python → latex | `-l python -f latex -o OUT IN` | **EFFECT** |
| python → terminal256 | `-l python -f terminal256 -o OUT IN` | **EFFECT** |

Every one is checked on the world, not on the program's story: the output file exists, is
non-empty, contains the formatter's documented envelope (`<span`), exits 0, and is **byte-identical
on a repeat run**. `carried_examples: 0`.

---

## 3. One program is a demo, not a law — so the second program forced a harder rule

`gzip`'s usage line is only `gzip [OPTION]... [FILE]...`. **No semantic slot names at all.** On
this host, **1 of 15** programs has semantic slots; the rest say `[OPTION]`.

But the option *table* names the roles:

```
  -c, --stdout      write on standard output, keep original files unchanged
  -d, --decompress  decompress
```

So the minter reads `doc` → role. It took three attempts to make it honest, and each failure was
a **confidently wrong slot**, which is worse than a missing one:

| attempt | minted | what was wrong |
|---|---|---|
| substring cues | `tar --files-from` → **decompress** | the word *extract* appears in an unrelated sentence |
| plus `--force` → **to_file** | still wrong | description *mentions* an output file; the flag does not write one |
| **verb-first cues** | `gzip` → exactly `decompress, keep, list, test, to_stdout` | **no false slots** |

The rule that survived: **the description must say what the flag does, and the verb must lead it.**
A mention is not a role.

With that rule, `gzip` yields four verified effects, and the round trip is produced rather than
assumed:

| goal | flags minted | effect |
|---|---|---|
| restore the original bytes | `--keep --decompress` | **EFFECT** — output is byte-identical to a payload generated here; input preserved |
| report the archive | `--list` | **EFFECT** |
| verify an archive | `--test` | **EFFECT** |
| read without destroying input | `--stdout` | **EFFECT** |

**9 / 9 goals produced verified effects across two unrelated programs** — a Python code formatter
with semantic slots, and a C compressor with only generic ones.

---

## 4. Two bugs the world caught, not the tests

Both failures were mine, and both were invisible until something ran:

1. **My plans omitted the positional.** `gzip --decompress` read *stdin* and failed, because the
   signature says `[FILE]` and I was not filling it. The signature had the answer; the plan
   ignored it.
2. **`zip` with no arguments created an archive in my working directory.** The same lesson as
   the `bzexe` incident: a program asked a question answers by *doing*. Every run here happens in
   a deleted scratch directory, and that is now a property of the instrument, not a habit.

A third, smaller one: my own regex surgery deleted `mint_slots` while removing a dead function.
The tests caught it in one run — which is the only reason it is a footnote.

---

## 5. What is real and what is not

**Real (measured here):**
- 9/9 verified effects, plans derived in fresh processes with **zero examples carried**.
- Plan slots are read off the program's own usage line; plan *values* are read off its own
  rendering. Neither is stored.
- Slot minting from English descriptions reaches **precision 1.000 on `gzip`** after the verb-first
  rule, with zero false slots; earlier looser rules produced wrong slots on `tar` and `gzip`.

**Not real (and not claimed):**
- **Two programs is not a class.** 15 programs were inspected; only `pygmentize` had semantic
  slots and only `gzip` was turned into effects. `tar` mints `list`/`keep` but has no
  compress/decompress pair to round-trip, and `zip`/`git` document **0** flags in the table form
  the minter reads.
- **English cues are a real dependency.** `ROLE_CUES` is a small hand-written list of role
  phrasings. It is not a model, but it *is* knowledge in the file — the one place this instrument
  is not knowledge-free, and it would need re-measuring on a non-English host.
- **Goals are supplied.** The instrument does not yet decide *what* to do; it decides *how*.
  Goal selection is the remaining gap, and it is the one that matters for real work.
- Nothing here touches GUI state, hidden application state, or long-horizon workflows.
- `truth.achieved` remains **false**.

---

## 6. The next idea this suggests (one, falsifiable)

The instrument can now **do** what a program's own text says it can do. The missing half is
**knowing whether the effect was the goal**. That is a verification question, not a knowledge
question, and the cheap version is already in the receipt: *an effect is real when the world
changes in a way the program's own words predicted, and repeating the run changes it identically.*

The next falsifier: take one **multi-step** goal — format a file, then compress it, then verify the
archive — and require a plan assembled from **three independently derived signatures** to reach a
verified end state, with no step given to the next. If plans compose, the algorithm scales by
composition rather than by knowledge. If they do not, the boundary is composition, not reading.

---

*Every number is in `intake/RECEIPT_AN_EFFECT_NOT_A_DESCRIPTION_20261121_V1.json`, reproducible
with `python3 canonical/tools/an_effect_not_a_description_v1.py`.*

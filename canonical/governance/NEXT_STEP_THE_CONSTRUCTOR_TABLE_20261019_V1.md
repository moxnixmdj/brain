# The one piece that is still a strict program

Status: analysis written 2026-10-19, at the end of the session that closed
`EXPLORE_CHANNEL_STATE_20261019_V1.md`'s two frontiers. This is where work resumes.

## The honest self-criticism

Everything the machine now does — transform a file, count a thing, compose two
programs, take the goal's own word out of the sentence and use it — rests on one
piece of hardcoding:

```python
_PROBE_KINDS = {
    "lines":       (...),
    "words":       (...),
    "bytes":       (...),
    "characters":  (...),
    "uniquelines": (...),
    "lineswith":   (...),
}
```

Six things a file can be BUILT to hold a known number of. Every question outside
those six is refused. Six rows is not sentience; it is a table with better
manners. The owner's words:

> *"I don't want a strict program like 'do 1, 2, 3 and that's it.'... I want a
> sentient machine, a sentient creature that knows what needs to be known."*

A creature that must be told what a file can be measured by does not know what
needs to be known. **This is the last piece of the explore channel that is a
program rather than a learner, and it is the right thing to attack next.**

## Why the table seemed necessary

The probe method needs a file for which the answer is known. To build one you
have to know in advance how to make "a file with exactly 7 of the thing", which
looks like it requires understanding the question. Circular. Hence the table.

## The way out: transformations, not constructions

**Do not build a file with a known answer. Take the real file and change it in a
way whose effect on the answer is known for ANY reasonable notion of amount.**

The machine does not need to know what "lines" means to know this:

| transformation | lines | words | bytes | distinct lines |
|---|---|---|---|---|
| repeat the whole file (`F F`) | ×2 | ×2 | ×2 | **×1** |
| duplicate each line | ×1 | ×2 | ~×2 | **×1** |
| first half only | ÷2 | ÷2 | ÷2 | ~÷2 |

A program's behaviour under these transformations is a **signature**, and the
signature identifies which family of quantity it measures — **without anyone
knowing what the quantity is called.**

- value doubles when the file is repeated → additive (lines, words, bytes)
- value unchanged when the file is repeated → a distinctness (how many different)

This is the exact distinction that currently needs a hardcoded constructor
(`uniquelines`) and a hardcoded keyword ("unique", "distinct"). With signatures
it falls out of behaviour: two programs that both stay constant under repetition
are measuring the same *kind* of thing, whatever you call it.

**The signatures are derived from measurement. They are not a table.**

## What still needs the word

Only one link, and it is much thinner than the current one:

- today: `keyword → a constructor` (six bespoke builders, one per question)
- after: `keyword → a signature` (a small map from the goal's word to which
  behavioural family counts as answering it)

A signature is a property of the measurement, discoverable and checkable. A
constructor is a piece of code someone wrote. The second is a program; the first
is a fact.

## The stair-step to build it

1. `_signature_of(command, file)` — run the command on F, on F+F, on
   duplicate-each-line(F), on first-half(F); record the four ratios as a tuple.
   Cheap: four runs per command.
2. Cluster the machine's measuring commands by signature. **Do not name the
   clusters.** Verify the clustering is stable on two different files — a cluster
   that moves between files is not measuring anything.
3. Map the goal's word to a cluster (this is the one remaining keyword list, and
   it can be far smaller than six).
4. Answer from the cluster: every member is asked the real file; agreement inside
   a cluster is the evidence, exactly as now.

Step 2 is the one that makes it a learner rather than a program: the machine
discovers how many distinct things its own computer can measure, and what they
are, before anyone asks.

## Hard tests this must pass (per the owner's rule: real, and they must break)

- Give it a file where the number of lines and the number of DISTINCT lines
  differ. Ask each. It must give two different numbers, and both must be true.
  Today this works — but only because two constructors were hand-written.
- **The test that proves the table is gone:** remove every entry of
  `_PROBE_KINDS` except a stub, and the distinct-lines question must STILL be
  answered, because the signature distinguishes it from the total. If that test
  cannot be written, the table has not been removed, only rearranged.
- A command whose value doubles under repetition must never be used to answer a
  "how many different" question, on any file.
- A program that happens to print the right number once but whose signature is
  wrong (a version string, a constant) must be rejected. Signatures catch this
  in a way single-probe tracking does not.

## Known hazards for whoever continues

- `probe_bytes("uniquelines", n)` currently builds n distinct lines each
  duplicated. Keep it until the signature path is proven, then delete it and
  let the test above justify the deletion.
- The wide manual search (`_WIDE_FLAGS = 400`) costs ~37s cold. Signatures add
  ~4 runs per surviving command — cheap against that, but do not add them
  *inside* the search; add them after survivors are found.
- Only cache discoveries, never failures (`_QUERY_CACHE`). A cached failure is
  a permanent one.
- Remembered shapes hold `{asked}` where the goal's word goes, filled by
  `_concretise`. Anything that reads `survivors[...]["argv"]` must handle the
  hole.

## Untouched limits, restated so they are not lost

- No path from this repo to a dollar; nothing here runs while neither of us is
  typing.
- `awk 'END{print NR}'`-class answers are still unreached — they need a program
  argument, not a flag plus a pattern.
- Pipelines are capped at two stages and 10 candidate programs.
- The first question of a kind costs ~37s; reuse is ~0.02s.

---

## Attempted 2026-10-19: the invariant test works, the search cannot reach it

The signature idea was built and measured. Result: **the discrimination is
correct and the search is too slow to use it.** Reverted to `b7d90471`, which
is verified passing; the finding is recorded here so it is not rebuilt blind.

### What was proven to work

`repeat_file()` duplicates every line in place. On `b"a\nb\nc\n"` it yields
`b"a\na\nb\nb\nc\nc\n"` -- 3 lines become 6, and 3 different lines stay 3.
Testing whether a command's number MOVES under that transformation separates
the two questions with no file-builder and nothing written down:

```
sort --unique | wc --lines   invariant -> True    (counts different lines)
uniq | wc --lines            invariant -> True    (counts different lines)
wc --lines                   invariant -> False   (counts lines)
```

That is the whole distinction the `uniquelines` constructor existed to make,
obtained from behaviour. The constructor was deleted and the tests above
still passed. The mechanism is sound.

### Why it was reverted

The search cannot find `sort --unique | wc --lines` on the full machine inside
any usable budget (~340s, and it came back with nothing). The pipeline stage
tries 10 candidate programs x 7 first-stage shapes x 4 second-stage shapes, and
the invariance check doubles every measurement -- roughly 10,000 subprocess
pairs, and `sort` is not near the top of the candidate list for this phrasing.

### The trap that made it worse before it was caught

With the constructor gone, `query_kind("how many unique lines")` returned
`"lines"`, and the CACHE was consulted under that key -- so a remembered
line-counting command was handed back and the machine answered **15** where the
truth was 7. A wrong answer that looks like a right one.

Any future attempt must apply the invariance check to the CACHED path too, not
only to freshly discovered commands. Reuse is not exempt from the test that
made the command trustworthy in the first place.

### The defect behind both failures (not yet fixed, and it is the real one)

`PipelineTests` passes an explicit shortlist (`programs=[...]`), so the tests
pass. **The full-machine path was never covered.** With `programs=None`:

```
how many unique lines in data.txt  ->  no answer, 370s   (shortlist: 7, in 5s)
count the lines in data.txt        ->  15, correct, 0.7s
```

So the distinct-lines capability works only when the machine is handed the
right eight programs. That gap -- a test that passes because it is given the
answer's neighbourhood in advance -- is the same class of dishonesty as the
tests that passed with their feature switched off, and it is the first thing
to close. **A test that supplies the candidate list is not testing discovery.**

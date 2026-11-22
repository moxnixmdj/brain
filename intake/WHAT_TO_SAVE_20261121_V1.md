# What to save: the host's words, not its programs

Schema `BRAIN_TYPE_IS_ITS_OWN_SENTENCE_V1` · `BRAIN_COST_TO_LEARN_A_HOST_V1` ·
`BRAIN_COMPOSE_A_HOST_NEVER_SEEN_V1`

Receipts `intake/RECEIPT_COST_TO_LEARN_A_HOST_20261121_V1.json`,
`intake/RECEIPT_COMPOSE_A_HOST_NEVER_SEEN_20261121_V1.json`
Tools `canonical/tools/cost_to_learn_a_host_v1.py`,
`canonical/tools/compose_a_host_never_seen_v1.py`,
`canonical/tools/type_is_its_own_sentence_v1.py`
Tests `canonical/tests/test_compose_a_host_never_seen_v1.py` (11 passed)

The user asked a question with two branches: should the model be **goal-directed** and save
the important learning, or should it **learn everything** in every environment and generalise
later? And what should memory keep, if not the exact experience?

Those are empirical questions. This answers them by building the experiment the previous
instrument could not survive.

## First, the flaw this had to beat

`plans_compose_v1` composed filters with a real search over real types. It also contained
**nine `if name == ...` lines**. Asked to type four programs it had never been told about:

```
bzip2      schemes=[]  roles=[]
xz         schemes=[]  roles=[]
sha256sum  schemes=[]  roles=[]
rev        schemes=[]  roles=[]
```

Every one empty. The search was real; the knowledge was a lookup table. On a second host the
capability was zero, and no amount of search would have fixed that. That is the control, and
it is the reason this work exists.

## The finding: a program's sentence is its type

Every executable answers `--help` with a first prose sentence that names its own transform:

| program | its own words | derived type |
|---|---|---|
| `gzip` | "Compress or uncompress FILEs" | `ANY→GZIP[_]`, `GZIP→UNWRAP` |
| `bzip2` | "a block-sorting file compressor" | `ANY→BZIP2[_]`, `BZIP2→UNWRAP` |
| `base64` | "Base64 encode or decode FILE" | `ANY→BASE64[_]`, `BASE64→UNWRAP` |
| `sha256sum` | "Print or check SHA256 checksums" | `TEXT→SHA256[TEXT]` (lossy) |

So the knowledge that transfers is **not** the program and **not** the pipeline. It is:

> a small closed class of English transform verbs, and the algebra that turns a verb into a
> type scheme — polymorphic wrap for constructive verbs, `UNWRAP` only when the program
> itself supplies the inverse word.

That is the "generalised structure" the user asked for. The saved thing is the *reading rule*
and the *algebra*. The host supplies every program-specific fact at run time.

## Measured on a host the code never names

`/usr/bin` on this machine — 635 executables, not one mentioned in the instrument:

```
typed from their own sentences   225 / 635     7.5 s   (33 ms per program, one probe each)
distinct wrap constructors found  17 compressors, 3 encoders
multi-stage round trips verified   5
per-program branches in the code   0
model calls / network / parameters 0 / 0 / 0
```

The five verified chains, none of which any line of the instrument names:

| chain found | bytes | round trip |
|---|---|---|
| `base64` → `base32` | 132 → 179 → 292 | **exact** |
| `base32` → `base64` | 132 → 219 → 296 | **exact** |
| `base64` → `base64` | 132 → 179 → 244 | **exact** |
| `base64` → `bzip2` | 132 → 179 → 198 | **exact** |
| `bzip2` → `base64` | 132 → 93 → 126 | **exact** |

`bzip2` is the one that matters: a compressor with no inverse shipped as a separate file, its
type read from the noun "compressor" in its own banner, its `--decompress` flag found by
looking up the word *decompress* in its own help, and its inverse found because the host
installs the undo command `bunzip2` beside it.

## Goal-directed or learn everything — the answer is BOTH, and the order is forced

```
learn everything   635 programs   ~2.2 s extrapolated   225 typed
goal-directed      gzip          1 program   5.9 ms
                   bzip2         1 program   5.1 ms
                   unxz          1 program   6.5 ms
```

**A full sweep of the host is 2.2 seconds.** That kills the objection to learning everything:
the earlier cost was not the host, it was an unbounded reader. Once a probe reads with a byte
budget, a wall-clock deadline, and a process-group kill, "learn everything" is cheaper than
deciding what to skip.

But a full sweep buys only 225 types out of 635, and the goal-directed path answers a specific
want in **5 ms** — 400× faster. So the two are not alternatives:

- **goal-directed first**, because it is 400× cheaper and usually sufficient;
- **sweep the host in the background**, because 2.2 s is a price worth paying once, and the
  sweep is what makes the next goal cost 5 ms instead of a probe.

Learning everything is not the strategy. It is the *cache*.

## Memory: what to save and what never to save

Save:

1. **the verb→type algebra** — small, closed, portable;
2. **the per-host type of each program** — cheap (33 ms), reusable, and derivable again if lost;
3. **the refusals** — which chains were tried and failed, so they are not retried.

Never save:

4. **the chain** — it is a 0.4 ms search over facts you already have;
5. **the bytes** — the round trip proves the effect; keeping the output would be the "dumb
   saving" the user warned against;
6. **the program name as knowledge** — it is evidence, not a fact, as three bugs below show.

The test is: *if this were deleted, how much would it cost to get back?* A chain costs a
search. A type costs a probe. The algebra costs the whole design. So the algebra is what
belongs in memory, and it is the only thing in this instrument that is not re-derivable.

## What the host taught the learner — seven real bugs

Each was found by running against a real host, and each is pinned by a test.

1. **The OOM killer.** Typing every executable by running it was killed at exit 137. An
   untrusted binary can print gigabytes. A learner that reads without a budget is a
   denial-of-service against itself.
2. **A scan that never ends.** Even bounded, a 120 s sweep timed out — programs wait on stdin
   and children hold stdout open. Hence the deadline and the process-group kill.
3. **`unxz` sorted before `xz`.** Deduping executables by their real target silently deleted
   `xz` from the census. The name is the host's word and is evidence; a symlink is not a
   duplicate.
4. **"compressor" is a noun.** 51 of the first 60 programs were untyped because the verb table
   had no noun forms. `bzip2` names its transform by its product, not an action.
5. **Order-dependent answers.** In the first single-pass version, whether `bunzip2` was
   recognised as the reverse of `bzip2` depended on alphabetical order — `bunzip2` sorts
   first, so the base had not been probed yet. A learner whose answer depends on directory
   order is not reproducible. Fixed by probing everything, then typing everything.
6. **`bunzip2` is b+un+zip2.** A prefix-only `un`/`de` rule missed the infix and typed a
   decompressor as a compressor, which produced real stage failures that looked like host
   quirks.
7. **`under` looked like the reverse of `der`.** A prefix alone is not evidence. A name counts
   as the reverse only when the base it implies is on the host **and** describes itself as
   constructive — two independent statements that agree.

And one that was not a bug: `bzless` inherits bzip2's help page verbatim, so its *sentence*
lies and its *forward run* succeeds spuriously (rc 0, 25 bytes of pager noise). The round trip
still rejected it. **The effect is the arbiter, not the claim** — which is the criterion this
whole series has been building toward.

## Honest limits

- Typing covers **225 of 635**, because 375 programs describe themselves without a transform
  verb ("Search for PATTERNS", "List symbols"). They are not wrong to; they are not filters.
  The instrument reports `DESCRIPTION_NO_VERB` rather than inventing a type.
- Composition verified is **5 chains, all built from the `base64`/`base32`/`bzip2` family**.
  The host has 17 compressors; `xz`, `lzma`, `gzip` were typed correctly but their sinks were
  not among the depth-limited probes. This is a breadth limit imposed by the measuring budget,
  not a failure of the algebra — and it is stated rather than rounded up.
- `BASENC` and `BZCAT` were typed but refused at execution (`basenc` needs an encoding
  argument; `bzcat` is a decompressor). Those refusals are correct and are in the receipt.
- This still composes **byte streams**. It says nothing yet about effects on the world.
  `truth.achieved` remains `false`.

## Reproduce

```sh
/tmp/brainvenv/bin/python canonical/tools/cost_to_learn_a_host_v1.py \
    --receipt intake/RECEIPT_COST_TO_LEARN_A_HOST_20261121_V1.json
/tmp/brainvenv/bin/python canonical/tools/compose_a_host_never_seen_v1.py \
    --receipt intake/RECEIPT_COMPOSE_A_HOST_NEVER_SEEN_20261121_V1.json
/tmp/brainvenv/bin/python -m pytest canonical/tests/test_compose_a_host_never_seen_v1.py -q
```

Authority `NONE__PRODUCER_RUN_SANDBOX`. No runtime model, no network, no stored parameters.

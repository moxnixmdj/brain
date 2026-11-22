# Scan, retrieve, fetch: the loop, and the key that makes it correct

Schema `BRAIN_SCAN_RETRIEVE_FETCH_V1` · tool `canonical/tools/scan_retrieve_fetch_v1.py` ·
tests `canonical/tests/test_scan_retrieve_fetch_v1.py` (10 passed)
Receipts `intake/RECEIPT_SCAN_RETRIEVE_FETCH_{VISIT1,VISIT2,BUSYBOX,BUSYBOX_ONLY}_20261121_V1.json`

The user's algorithm, taken literally:

> "scan everything in the environment and then retrieve from his memory what he knows and
> what he doesn't know. What he doesn't know, he should get it instantly."

Every previous instrument did part of this and none had a memory, so none could skip
anything: `cost_to_learn_a_host_v1` re-probed the whole host on every run. This closes the
loop and measures each step.

## The key is (content, name), and both halves are load-bearing

The two obvious cache keys are both wrong, and the host proves it:

| measurement | result | consequence |
|---|---|---|
| 635 names in `/usr/bin` | **481 distinct files** | a name-keyed cache repeats itself 154 times |
| `/usr/bin/xz` vs `unxz` | **byte-identical** | a content-keyed cache calls the decompressor a compressor |
| `xz` on plain text | rc 0, compresses | |
| `unxz` on plain text | **rc 1, refuses** | behaviour depends on the invoked name |

One binary, six names, six behaviours — `xz`, `unxz`, `xzcat`, `lzma`, `unlzma`, `lzcat`
all behave differently and their `--help` output differs too. **The name is an input to the
program, not a label on it.** So the cache key is `sha256(content)[:16] + ":" + invoked_name`.
A changed binary or a changed name is a miss, by construction.

## Measured: four visits

| visit | host | memory | probed | from memory | learned | proved | time |
|---|---|---|---|---|---|---|---|
| 1 | `/usr/bin`, 635 names | cold | 635 | 0 | 429 | 3 | 10.99 s |
| 2 | `/usr/bin`, same | warm | 206 | **429** | 0 | 3 | **6.44 s** |
| 3 | `/usr/bin` + busybox 401 applets | warm | 607 | 429 | 165 | 3 | 9.57 s |
| 4 | busybox-only, 9 names | GNU memory | 9 | **0** | 9 | **4** | **0.118 s** |

Visit 2 is the retrieval claim: **the 429 learned programs are never asked again.** The
206 still probed are the ones that answered with no transform verb — they are unreadable,
not unlearned, and re-asking them is the price of not guessing.

Visit 4 is the transfer claim. A host made only of busybox symlinks shares **no bytes** with
GNU, so nothing could be reused and the count is honest:

```
compositions proved on a foreign host, from its own help pages, zero GNU reuse
  BASE32[TEXT]  ['base32']  exact
  BASE64[TEXT]  ['base64']  exact
  BZIP2[TEXT]   ['bzip2']   exact
  GZIP[TEXT]    ['gzip']    exact
  BUNZIP2[TEXT] refused     (it is the decompressor; feeding it text is not a round trip)
  GUNZIP[TEXT]  refused     (same)
```

Four exact round trips in **0.118 s** on a program family the code had never executed.

## Reading a foreign help format with the same rule

GNU and busybox disagree about layout, and one rule reads both:

| | GNU `gzip --help` | busybox `gzip --help` |
|---|---|---|
| description | line 2, prose: "Compress or uncompress FILEs" | **line 5**: "Compress FILEs (or stdin)" |
| `-d` | **never mentioned** | `\t-d\tDecompress` |
| inverse word | "uncompress", in prose | "Decompress", as a flag description |

So the reading rule is not "the first prose line" and not "the option table" but **"the first
line that names a transform verb, wherever it is"**, plus **a flag lookup that accepts either
layout**. The change that made both work is that a banner, synopsis, copyright block, or error
message names no transform verb, so none of them can be mistaken for a description. Busybox's
`bunzip2` was typed correctly from its own sentence — "Decompress FILEs (or stdin)" — with no
name-parsing at all.

## Five ways this loop tried to destroy itself

All five were real, all are pinned by a test.

1. **Exit 137, twice.** `subprocess.run(capture_output=True)` has no byte bound, and an
   executable that prints forever takes the learner down with it. Every read now has a byte
   budget, a deadline, and a process-group kill.
2. **A 900 s hang on a buffered read.** `proc.stdout.read(2048)` does not return until 2048
   bytes arrive, so a program that prints 50 bytes and holds stdout open blocks forever.
   Replaced with `select` plus a deadline.
3. **An infinite search.** A chain-length cap is not a bound when the *types* grow:
   `C[C[C[...]]]` at every depth is a new string, so the BFS never terminates. Two bounds
   were added — nesting depth on the type, and a hard state ceiling that **refuses** rather
   than hangs.
4. **398 edges of noise.** Documents were typed `TEXT → NAME[TEXT]`, which looks plausible
   and buried a one-hop goal under 50,000 states. A program that only prints or searches
   names no input type, so it is now recorded **untyped** and stays out of composition.
   Declaring what you do not know is cheaper than guessing it.
5. **A lowercase sink.** The sink was built as `f"{program}[TEXT]"` — `base32[TEXT]` — while
   the graph produces `BASE32[TEXT]`. Every search refused and the instrument reported **zero
   compositions on a host where six round trips work**. A sink is a type, so it comes from the
   type, never from the program name.

The fifth is the one worth remembering: it was invisible because my manual checks had all
used `.upper()`. Only running the real loop, at full scale, surfaced it.

## What is saved, and why that is the whole answer

Memory holds one record per `(content, name)`:

```json
{"key": "<digest16>:<name>", "transform": "compress",
 "description": "Compress or uncompress FILEs ...",
 "flags": {"decompress": "--decompress", "stdout": "--stdout"}}
```

It does **not** hold a chain, an order, a byte, or an example. Those are recomputed:
compose is `find_path` over 22 wrapping schemes, and it costs microseconds. The memory is
exactly the part that costs a probe to re-derive; everything downstream is a search.

That is the generalisation the user asked for. The record is not "I once ran
`base64 | bzip2`". It is "this program, at this content, in this name, states that it
compresses, and its own help says `-d` undoes it" — which is true of GNU bzip2, busybox
bzip2, and any future compressor that says the same thing.

## Honest limits

- **206 of 635** programs answer `--help` with no transform verb at all. They are reported
  as unreadable, not guessed, and they are re-probed on every visit. That is the largest
  remaining cost in the loop and the clearest next target.
- Visit 3 confirms the **name-collision boundary**: when busybox applets shadow GNU names on
  one host, the `(content, name)` key correctly forces a re-probe (607 probed, 165 learned).
  Correct, and expensive — a per-path namespacing key would reduce it, and has not been built.
- Proved compositions are **one stage**. Multi-stage chains work in
  `compose_a_host_never_seen_v1`, but here the search is deliberately lenient and the round
  trip is the arbiter, so the receipt claims only what the round trip verified.
- The web channel was **not used** in this loop. It remains measured-and-deferred: ASK on the
  host is 6.78 ms against 255.2 ms for the web, and 7,432 man-page citations on this host
  resolve to zero present files. When the host cannot answer, the web is the fallback, and
  nothing here pretends otherwise.
- Still byte streams, not effects in the world. `truth.achieved` remains `false`.

## Reproduce

```sh
# visit 1 (cold), then visit 2 (warm) on the same host
/tmp/brainvenv/bin/python -B canonical/tools/scan_retrieve_fetch_v1.py \
    --memory /tmp/brain_memory/final.json --reset
/tmp/brainvenv/bin/python -B canonical/tools/scan_retrieve_fetch_v1.py \
    --memory /tmp/brain_memory/final.json
# a foreign host, 401 applets behind one binary
/tmp/brainvenv/bin/python -B canonical/tools/scan_retrieve_fetch_v1.py \
    --multicall /usr/bin/busybox --memory /tmp/brain_memory/final.json
/tmp/brainvenv/bin/python -m pytest canonical/tests/test_scan_retrieve_fetch_v1.py -q
```

Authority `NONE__PRODUCER_RUN_SANDBOX`. No runtime model, no network, no stored parameters.

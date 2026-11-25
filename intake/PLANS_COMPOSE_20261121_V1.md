# The order is searched, the inverse is searched, and the refusals are the result

Schema `BRAIN_PLANS_COMPOSE_V1` · receipt `intake/RECEIPT_PLANS_COMPOSE_20261121_V1.json` ·
tools `canonical/tools/plans_compose_v1.py` · tests `canonical/tests/test_plans_compose_v1.py`

The previous instrument proved a single program can derive its own plan. This one asks the
next question: given several programs that know nothing about each other, can a **searched
type graph** find the order, and can a **searched inverse** prove the result came back?

## What was measured

| | |
|---|---|
| Forward chain | `base64` → `gzip` — **found**, not written |
| Hand-written control | `base64` → `gzip` — **identical** |
| Inverse chain | `gzip` → `base64` — **found**, not written |
| Bytes | 32 → 45 → 65 → 45 → **32** |
| Round trip | `round_trip_exact: true` |
| Repeat | `repeat_identical: true` |
| Duration | 0.37 s |
| Calls | 0 model · 0 network · 0 stored parameters · 0 carried examples |

All eight laws pass: `C1` types derived from each program alone, `C2` order found not
written, `C3` effect verified in the world, `C4` impossible goal refused, `C5` zeros,
`C7` byte-exact round trip, `C8` inverse typed as unwrap, `C9` lossy goal refused.

## The refusals are the finding, not the failures

Three goals, and the composer must get all three right:

- **`TEXT → GZIP[BASE64[TEXT]]`** — recoverable. Found in two stages, inverse found, bytes
  returned exactly.
- **`TEXT → GZIP[PDF]`** — impossible. Refused: *no chain of type schemes produces
  `GZIP[PDF]` from `TEXT`*.
- **`TEXT → GZIP[BASE64[ANSI]]`** — forward path exists (`pygmentize` → `base64` → `gzip`,
  found), inverse **refused**: *no inverse chain from `GZIP[BASE64[ANSI]]` to `TEXT`*.

That third row is the honest boundary. `pygmentize` is a formatter: it renders text to ANSI
and has no inverse. So a chain led by a formatter produces output that cannot be wound back
to source text, and the search **says so** instead of widening a type until it looks
reversible. Composition is only as strong as the weakest inverse in the chain, and the
instrument now measures that rather than asserting it.

## Five real bugs this instrument found in itself

Each was shipped in a draft, caught by measurement or a test, and is now pinned:

1. **Flat `(consumes, produces)` types were too weak.** Every sink was reachable in one
   stage, so the "composition" was decoration. Filters are polymorphic — `∀X. X → GZIP[X]`.
2. **A decompressor typed as `GZIP[_] → TEXT` gave a true-but-useless inverse.** gunzip
   faithfully restores base64 bytes; the search called that reaching `TEXT`. Fixed by typing
   a constructor as the inverse of its own wrapper: `GZIP → UNWRAP`.
3. **`_apply` hardcoded the constructor names** `GZIP` and `BASE64`. Found when a test used
   `BOX`/`V` and the search could not move. Now generic: a bare constructor name unwraps its
   own payload, and no rule names a program.
4. **The inverse was not reversed.** `find_path(sink → source)` already starts at the
   outermost constructor, so reversing it produced `base64, gzip` for the unwind and the
   round trip failed at 65 → 45 bytes of the wrong kind. Fixed and pinned by
   `test_the_inverse_is_not_reversed_into_the_wrong_order`.
5. **The receipt failed against a stale hand-written control.** The control still named the
   three-stage lossy chain after the goal moved to the two-stage recoverable one. A
   comparison bug reported as a capability failure — `C2`/`C3` were false for a reason that
   had nothing to do with composing.

## One thing that looked like a bug and was not

A global visited set was twice diagnosed as pruning a valid route, and "fixed" twice — first
by keying on `(type, chain_len)`, then by dropping it entirely. Both changes were noise.
The search space is **Markovian in the type**: what a program can do next depends only on
the type in hand, never on the route that produced it. So if a type is reached twice, the
second arrival can only repeat covered work, and pruning it cannot hide a path. The global
set is both complete and cheapest. The comment in `find_path` now says this explicitly, and
`test_the_visited_set_is_global_because_the_search_is_markovian` fails if someone changes it
without a counterexample: two different routes to one type with different futures, which the
type algebra cannot currently express.

BFS over uniformly-priced schemes also means the first chain found is a **shortest** one, so
the depth cap of 6 is a guard against unbounded polymorphic wrapping, not a search budget.

## Why this matters for the model

The composer stores no order, no pipeline, and no example. It stores, per program, only what
that program's own interface implies — a type scheme and the roles minted from its usage line.
The chain, the flags on each stage, and the inverse are all derived at run time in 0.37 s with
no model call, no network, and no parameters.

That is the shape the user asked for: the knowledge is `program → signature → type`, and
everything else — order, flags, reverse — is **computed**, not saved. A new environment
contributes executables; the tooling contributes nothing but the search.

The limit is equally clear. This works because UNIX filters compose by streams and by type.
It says nothing yet about programs whose effect is a change in the world rather than a byte
stream, and nothing about a chain that mixes a lossy stage with a recoverable tail — for that
the right answer is currently "refuse", which the instrument now does.

## Reproduce

```sh
/tmp/brainvenv/bin/python canonical/tools/plans_compose_v1.py \
    --receipt intake/RECEIPT_PLANS_COMPOSE_20261121_V1.json
/tmp/brainvenv/bin/python -m pytest canonical/tests/test_plans_compose_v1.py -q
```

Authority: `NONE__PRODUCER_RUN_SANDBOX`. `truth.achieved` remains `false`. No runtime model,
no network, no stored parameters.

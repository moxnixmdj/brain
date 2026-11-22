# A stub is not empty: it names where its knowledge lives

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls, 0 parameters, 0 network
**Receipt:** `intake/RECEIPT_FOLLOW_THE_POINTER_20261121_V1.json` · **Instrument:** `canonical/tools/follow_the_pointer_v1.py` · **Tests:** `canonical/tests/test_follow_the_pointer_v1.py` (6 passed)
**Supersedes:** the "LOOK is blind on self-describing-free hosts" conclusion in `WHAT_TRANSFERS_TO_A_SECOND_HOST_20261121_V1.md` §3

---

## 0. The idea, and the number that broke it

Last receipt measured that a host of console scripts is **7.7 % discoverable**: the artifacts
contain no flags, so reading them teaches nothing. That measurement was correct. The conclusion
was wrong.

Look at what a console script actually is:

```python
#!/tmp/brainvenv/bin/pytest
from _pytest.config import _console_main   # <- here is the logic
```

**The stub is not empty. It names where its knowledge lives.** My instrument was reading the
signpost and reporting "no address found."

---

## 1. The law

> **A short artifact names its own long part. Knowledge lives one pointer away, and a pointer is
> a file read, not an execution.**

Four pointer forms are enough for this host: Python `from X import Y`, Python `import X`, Node
`require('./x')`, ESM `from './x'`. Following them costs **microseconds** and cannot have side
effects, because nothing is executed — a fact the test suite now *enforces by parsing the
instrument's own AST* for `subprocess` calls in the walking code.

---

## 2. What following bought

| | blind bytes | following the pointer |
|---|---|---|
| programs with a declaration | 1 / 13 | **5 / 13** |
| flags found | 1 | **69** |
| **usable at top level** | 1 | **60** |
| gain | — | **5× reach** |

On the host where reading bytes previously failed completely, following the pointer reaches
**five times more programs** and finds **60 flags instead of 1**.

---

## 3. Correctness: the follower was right, and `--help` was wrong

I did not trust the volume. Every flag was scored against ground truth, and the first scoring
run produced a **0.39 precision** — which I assumed was the follower's failure. It was not.

`uvicorn` is the case that settles it:

```
$ uvicorn --h11-max-incomplete-event-size
Error: Option '--h11-max-incomplete-event-size' requires an argument.
```

That is **acceptance**. The flag exists; `--help` simply never lists it. `uvicorn` renders help
dynamically and omits a third of its own interface.

So the scorer was measuring *agreement with an incomplete oracle*. Once every disagreement was
settled by actually exercising the flag:

| measure | value |
|---|---|
| confirmed by help | 26 |
| **rejected by the parser** | **0** |
| declared but omitted by help | 13 |
| **sourced precision** | **1.000** |
| recall vs help | 0.765 |
| **help omission rate of disagreements** | **1.000** |

**Every single flag the follower declared that help did not list was accepted by the program's
own parser.** The follower's sourced precision is perfect, and `--help` undercounts the real
interface by a measurable amount.

This is the same defect class the previous receipt found (`dpkg-genchanges` documenting a form
its parser rejects), in the opposite direction: **the documentation is not the interface, in
either direction.** Only an exercise settles it.

---

## 4. Nesting is decided by the interface, not the decorator

First attempt: flags under `@main.command()` are nested. Wrong — `uvicorn` is decorated with
`@click.command()` and exposes **55** top-level flags.

The decidable fact is whether the program's own usage declares a **subcommand slot**:

| program | own usage | verdict | top-level flags |
|---|---|---|---|
| `uvicorn` | `uvicorn [OPTIONS] APP` | no slot | **56 declared, 23 in help** |
| `hypothesis` | `hypothesis [OPTIONS] COMMAND [ARGS]...` | slot | 0 top, **9 nested** |

When neither the usage nor an AST fact settles it, the flag is marked **undecidable** and
reported as such — never guessed in either direction. On this host nothing was undecidable.

---

## 5. What this changes in the algorithm

The five-step loop from the previous receipt gets one step promoted from fallback to first
choice:

> **Follow the pointer** (µs, no execution) → read bytes → ask only what neither settled →
> exercise what disagreements remain → bank structure.

Ordered by cost, not by familiarity. Following is the cheapest channel on the machine and the
only one that reaches a generated stub.

---

## 6. What is real and what is not

**Real (measured here):**
- Following the artifact's own pointers reaches **5×** more programs at **precision 1.000** on the
  host where blind byte-reading failed.
- `--help` omits real interface: 13 of 39 disagreements, **100 %** of them resolved in the
  follower's favour by exercising the parser.
- Nesting is decidable from the program's own usage line; when it is not, the follower says
  "undecidable" rather than guessing.

**Not real (and not claimed):**
- **Node/ESM reach is 0 on this host.** The npm stubs `require('../lib/cli.js')`; the resolver
  followed 6 dead ends and found nothing, because npm's option definitions live in a data file
  the require chain does not name. That is an honest dead end, reported, not fixed by widening
  the regex.
- **5 of 13 programs is not "all programs".** The other 8 declare nothing followable; for them
  ASK remains the only route, at 6.8 ms.
- **Python-only AST analysis.** Click and argparse are parsed structurally; a decorator built at
  run time would defeat it, and would be counted as a dead end.
- This is still one OS. Nothing here touches GUI state or long-horizon workflows.
- `truth.achieved` remains **false**.

---

## 7. The next idea this suggests (one, falsifiable)

The follower's failure was **npm**: `require('../lib/cli.js')` where the flags are actually
declared in a JSON/YAML options table the chain never names. If a hop count of 2 covers
Python and 0 of npm, the honest test is **pointer depth on a host of packaged applications** —
where the entry point names a manifest, the manifest names a binary. If following still reaches
the declarations, the reach gain is general and not a Python accident. If it does not, the
conclusion is that *some* artifact formats are self-describing and others are not, and the
channel has to be chosen per family — which is exactly the kind of boundary this project keeps
finding.

---

*Every number is in `intake/RECEIPT_FOLLOW_THE_POINTER_20261121_V1.json`, reproducible with
`python3 canonical/tools/follow_the_pointer_v1.py`.*

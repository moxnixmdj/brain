# A type you wrote is a type you guess

**2026-12-02 · branch `arena/eaf4537b-brain`**
**Tool `canonical/tools/a_type_you_wrote_is_a_type_you_guess_v1.py` · receipt `canonical/verification/A_TYPE_YOU_WROTE_IS_A_TYPE_YOU_GUESS_20261202_V1.json` · 0 model calls · 0 parameters · 0 network at run time**

---

## 0. The headline, which is a falsification of the round's own claim

This round set out to replace a hand-written type table with a type system derived from the
machine's own declared checks. It did that. Then it was put on a machine with fewer programs —
the kind of machine a second run lands on — and **the claim inverted**:

| how an object gets its type | rich machine (446 pages, 2,319 declared checks) | thin machine (16 pages, 109 declared checks, 8 witnesses) |
|---|---|---|
| the guide's hand-written kind table | **114** of 189 | **114** of 189 |
| `scan_and_diff_against_memory_v1`, validators as authored | **161** | — (its validators need programs this machine lacks) |
| the same scanner after this round's four tests | 149 | — |
| **this round's derived witnesses** | **155** | **67** |

Read the two right-hand columns together, because that is the finding. The written table is
exactly as good on the thin machine as on the rich one — it costs nothing to be written, and
nothing to keep. The derived set collapses from 155 to 67, because a derived type system is
only as good as the machine's supply of checks that separate anything, and on a machine with a
sixteenth of the pages there are eight such checks instead of forty-five.

**So the general claim "derived typing beats a written table" is false.** It is true on a rich
machine, and it is six pairs *short* of the scanner this tree already had even there. That
inversion is now gate **T8** in the receipt rather than an accident of which runner the
workflow landed on, because the first version of this round would have passed on one machine
and failed on another and said the same thing either way.

What survives both machines, and is the part worth keeping, is in §4: sixteen declared
"read-only checks" that **write to the object they are asked about**, and nineteen that read an
object's *content* and were being used as tests of its *type*. Those are defects in the tree's
existing typing, they are machine-independent, and they are reproduced on both.

## 1. The debt this round pays, in the last round's own words

`THE_GUIDE_IS_AN_ACTION_GRAMMAR_20261124_V1.md` §6 ended with three obligations, written down
so they could not be quietly dropped. The first and third are the subject here:

> 1. the same instrument, unchanged, against a **room it has never seen** — an unfamiliar tree
>    with objects whose kinds the vocabulary does not already contain;
> 3. a written answer to whether a refusal read once should be **stored**, and if so in what
>    generalised form

That round also told on itself in one line: *"The one typed table in the file is a verb's
(in-kind, out-kind) pair"*. There were **two** tables. The second was `REFINES` / `kind_of()`:
seven names and a chain of magic numbers deciding which name an object gets. Every need in that
round was a *target kind*, every edge was *typed over kinds*, and every goal check compared a
*kind*. The types were load-bearing and they were written by hand.

## 2. What the hand-written table does on a room it never saw

Twenty objects, built by ten producers (`tar`, `gzip`, `xz`, `bzip2`, `zip`, `ar`, `openssl`,
`sqlite3`, `convert`, `cp`), nineteen distinct producer kinds. The table gives them **five**
names. `compressed` covers gzip, xz, bzip2, zip and tar-gzip. `plain` covers eleven kinds:
plain-text, empty, random-bytes, `ar`, sqlite, X.509 certificate, PEM key, XML, PNG, JPEG and
ELF object.

**The table is right where it has a name.** On the guide's own room — the seven kinds it was
written for — its name *is* the producer's kind, object for object: **21 of 21** different
pairs (T1). It was not a bad table for the room it was born in, and that is the control which
makes the next sentence a measurement instead of a complaint.

**It is confidently wrong where it does not.** On the unseen room: **114 of 189** different
pairs (60.3 %). And the cost is not a mislabelled object. A need is a *target kind*: an agent
whose vocabulary cannot name a certificate cannot hold the goal "extract the public key from
this certificate". It does not answer wrongly; it cannot ask. **11 of 19** producer kinds are
collapsed into one name.

## 3. The tree already had the right shape — with a written table inside it

Here is where the round stops being a clean story. `canonical/runtime/scan_and_diff_against_memory_v1.py`
— shipped in this repository one round earlier — already types a file by which of its
**declared validators accept the bytes**, and it says the important sentence itself: identity
is content, not name. Its validators are `gzip -t`, `tar -tf`, `unzip -t`, a JSON parse, a PNG
magic test, an `ast.parse`, a UTF-8 read. It also already recorded the defect this round then
re-met from the other side: its first version used `py_compile`, which **writes `__pycache__`
next to the file it judges**, so the scanner was reading artefacts it had made itself.

But `VALIDATORS` is a **dict of seven kinds written by its author**, and a signature over a
written list is bounded by the list — the same defect as the kind table, one floor up. So the
question this round actually had to answer is not "should types come from validators" (the tree
had answered that) but:

> **Can the validators be derived instead of authored — and if so, what may count as one?**

## 4. The rule

A page declares a check: a flag whose prose is a question and whose argument is the object.
2,319 such (program, flag) pairs are declared across the 446 pages this machine prints. Let
them be the type system, under a rule that names no program:

> A declared check is a **witness** when
> 1. it **separates** — accepts at least one object and rejects at least one;
> 2. it **repeats** — the same verdict on a second and third independent pass;
> 3. it **observes** — it changes nothing in the room;
> 4. it is **content-invariant per kind** — every object of one producer kind gets one verdict,
>    in a second room of the same kinds with different content.

An object's type is the set of witnesses that accept it: a signature, not a name.

Each part removes something real, and each removal is listed in the receipt by name:

| part | what it removes | measured on this machine |
|---|---|---|
| separates | `--help`, declared by 342 of 446 pages as a "read-only check" | **1,338** of 2,319 accept every object |
| separates | checks that accept nothing here | **913** accepted no object |
| repeats | anything nondeterministic | 66 separated, 64 repeated, 2 dropped on a third pass |
| observes | `shred -v`, `ln -v`, `split -v`, ImageMagick `stream` | **16** declared "checks" WRITE to the object they are asked about |
| content-invariant | `perl -c`, `rgrep -l/-n/-H`, `node --trace-*` | **19 of 64** contradicted themselves between two rooms |

The `observes` line is the one I did not expect, and it is the round's sharpest result. The
shipped `check_flags()` keeps any flag whose prose starts with *list, show, print, display,
test, check, verify, give* and whose argument is none. By that rule **`shred --verbose` is a
read-only check** — and it separated the room precisely because destroying an object changes
the answer. A "read-only check" list containing a destructive command is the same class of
defect as a benchmark whose answer is in the prompt.

And the same four tests, pointed at the tree's own seven authored validators, remove exactly
one of them: **`python`**, which accepts a `.py` and rejects a `.md` — a test of *content*, not
of *type*, and it contradicts itself on plain-text between two rooms. That is the honest size
of the correction to work the tree had already done.

## 5. What the witnesses actually buy, said plainly

Forty-five names is a flattering number. Group the witnesses by the verdict vector they produce
over a room: **45 witnesses are 4 distinctions** (classes of 27, 16, 1, 1). Forty-one of the
names are aliases — the same question asked by `gzip -t`, `gunzip -t`, `zcat -t`,
`uncompress -t`, `gzip --test`, `gzip -l`, … The distinctions are:

1. *is it a gzip stream?* (27 spellings; it accepts `zip` and `tar.gz` too, correctly, because
   both really do contain a gzip member);
2. *is it binary?* (`scriptreplay --summary` aborts in `replay_emit` on binary, accepts text —
   a distinction nothing in the table names);
3. *does `iconv` accept it as text?*
4. *does `node` tolerate it?* (29 spellings accept `data.json` and the empty file and reject
   everything else; whatever the mechanism, it separates).

Four distinctions are not nineteen. The receipt prices the gap rather than defaulting it: five
classes remain for twenty objects, `log2(class)` bits undecidable each — 1.585 bits for
gzip-vs-tar.gz-vs-zip, which no check on this machine can pay, and gzip-vs-tar.gz-vs-zip is
exactly the ambiguity that matters if a need says "the archive", so it is listed, not hidden.

## 6. Should a refusal read once be stored?

Asked by running the rule twice, on two rooms of the **same kinds** with different content. The
witness sets are **identical**: 45 checks, the same 45, on both rooms. So a witness is
**derived from the pages and the room, never learned from experience**: storing one buys
nothing, and a stored copy is a liability the day a page changes. What a store would hold is
the empty set.

The invariance test is the same measurement from the other side and it is what makes the answer
non-trivial: **19 of 64** checks that passed parts 1–3 changed their verdict on an object of the
same kind in the second room. They were not knowledge about types; they were knowledge about a
file's contents wearing a type's clothes.

## 7. The gate that fired on the round itself

Declared before the run:

| gate | result |
|---|---|
| T1 the written table is right where it has a name | **MET** — 21/21 pairs on the guide's own room |
| T2 it collapses kinds it never named | **MET** — 11 producer kinds inside `plain` |
| T3 the witness rule finds checks with no program named | **MET** — 2,319 candidates → 45 witnesses |
| T4 the signature separates more than the written name | **MET** — 155/189 vs 114/189 |
| T5 the residual is named, not hidden | **MET** — 5 classes, `log2` price each |
| T6 storing buys nothing, or the difference is named | **MET** — both rooms give the same 45 |
| T8 the derived route has a machine threshold, and a thin machine is below it | **MET** — the claim is *stated false* where it is false |
| T7 zero model calls, zero parameters, zero network | **MET** |

**T3 first "passed" with 64 witnesses that included `perl -c`, `rgrep -l` and `node --trace-exit`,
and T4 rose to 160 of 189 — a better number — by keeping them.** Both were wrong the same way:
those checks separate by reading an object's *content* and calling it a *type*. The invariance
test exists because a gate that improves when a defect is added is not a gate. With it, T4 fell
to 155 and the names to 45. T1 also failed on the first build for a related reason: a declared
"check" it ran, `ln --verbose`, **mutated the room between objects**, so the objects being named
were not the objects being asked about. That is what put `observes` in the rule.

And one number moved between runs before it was fixed: 155 one run, 160 the next, because
`node --trace-*` sometimes exceeded a 2-second deadline under 12-way parallelism. An instrument
whose answer depends on how busy the machine is has no answer. The deadline is now 5 s at 6
workers, with a third serial pass that drops anything still unstable; two runs from two clean
processes now give the identical 45 and the identical 155.

## 8. What is real, what is not

**Real.** The instrument was put on a thin machine, the claim inverted, and the inversion is
a gate rather than a footnote. That is the round's honest product. A room of kinds this tree never named, built by their own producers. A measured price
of the hand-written kind table there: 11 of 19 kinds collapsed, 60.3 % of pair differences,
and 11 goals that cannot be *stated*. A rule that derives witnesses from declared checks with no
program named, that removes `--help` by measurement rather than blacklist, that catches 16
checks that write, and that catches 19 checks that were reading content and calling it type.
Two runs that agree exactly. And a mechanical answer to the storage question: no, with the test
that says so.

**Not real.** "Derived typing is better." On a thin machine it is materially worse (67 against
114 of 189) and on the rich machine it is short of the scanner already shipped (155 against
161). "The machine can type anything now." An object no declared check can examine has
the empty signature and lands in the residual with everything else — six objects here, reported.
"Nineteen types." Four distinctions. "A better mechanism." On this room it is **six pairs worse
than the scanner already in the tree**; what it has that the authored scanner does not is that
nobody had to know the kinds in advance, and that property matters on a room no author has seen
— which is a claim about transfer, and this round does not measure transfer.

**Not measured.** A witness that takes an argument (`sqlite3`, `openssl verify`, `jq` with a
filter) — the rule reads only no-argument checks, so `sqlite`, `jpeg`, `bzip2`, `xz` and `png`
are typed by nothing here. Accessibility trees, the analogue the last round named. And whether
these four distinctions are the right four for any goal but the ones written here.

## 9. The one line

> **A type you wrote is a type you guess. It is perfect on the room it was born in and it puts
> eleven kinds under one name on the next. The machine will tell you how many distinct questions
> it can still ask about an object — four, here, behind forty-five names — and, if you ask
> properly, it will also tell you which of its own declared "read-only checks" are writes.**

## 10. Next step, pre-registered

The round leaves three obligations, and the first one is now aimed at the machine where it
currently *fails*:

1. **Give a witness the argument its page declares** (`-f ARCHIVE`, `-in FILE`), so `sqlite3`,
   `openssl verify` and `jq` with a filter can be witnesses at all — and measure it **on the
   thin machine**, where there are eight witnesses and the derived set loses. Falsifier: if
   argument-carrying witnesses do not lift the thin machine above the written table, the
   threshold is a fact about how many distinct questions a small machine can be asked, and the
   derived route is for rich machines only.
2. **Test transfer** on a room whose producers were chosen after the rule was frozen, against the
   authored seven-kind list. Falsifier: if the authored list transfers as well, authoring was
   never the cost and this round's rich-machine difference is decoration.
3. **Repair `check_flags()` in the shipped guide.** It calls `shred --verbose` a read-only check.
   That is a one-line defect in canonical code, it is independent of every machine measured here,
   and leaving it is not an option the next round should have.

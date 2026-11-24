# A type you wrote is a type you guess

**2026-12-02 · branch `arena/eaf4537b-brain` · receipt `canonical/verification/A_TYPE_YOU_WROTE_IS_A_TYPE_YOU_GUESS_20261202_V1.json`**
**Tool `canonical/tools/a_type_you_wrote_is_a_type_you_guess_v1.py` · 0 model calls · 0 parameters · 0 network at run time**

---

## 1. The debt this round pays, in the last round's own words

`THE_GUIDE_IS_AN_ACTION_GRAMMAR_20261124_V1.md` §6 ended with three obligations and said so
that they could not be quietly dropped. The first and the third are the subject here:

> 1. the same instrument, unchanged, against a **room it has never seen** — an unfamiliar tree
>    with objects whose kinds the vocabulary does not already contain;
> 3. a written answer to whether a refusal read once should be **stored**, and if so in what
>    generalised form

That round also told on itself in one line, and the line is the whole round:

> The one typed table in the file is a verb's (in-kind, out-kind) pair …

There were in fact **two** tables. The verb table it confessed to, and `REFINES` / `kind_of()`:
seven names (`plain, archive, compressed, patch, json, executable, directory`) and a chain of
magic numbers that decides which name an object gets. Every need in that round was a *target
kind*, every edge was *typed over kinds*, and every goal check compared a *kind*. The types
were the load-bearing part, and they were written by hand.

So: build a room out of objects whose producers this tree has never seen, and ask the table
what it thinks they are.

## 2. What the table does on a room it never saw

Twenty objects, built by ten producers (`tar`, `gzip`, `xz`, `bzip2`, `zip`, `ar`, `openssl`,
`sqlite3`, `convert`, `cp`), nineteen distinct producer kinds. The written table gives them
**five** names:

| written name | producer kinds it covers |
|---|---|
| `compressed` | gzip, xz, bzip2, zip, tar-gzip |
| `plain` | plain-text, empty, random-bytes, ar, sqlite, x509-cert, pem-key, xml, png, jpeg, elf-object |
| `archive`, `json`, `executable` | one kind each |

Two things are true at once and both matter.

**The table is right where it has a name.** On the guide's own room — the seven kinds the
table was written for — its name *is* the producer's kind, object for object: **21 of 21**
different pairs separated (T1). It was not a bad table for the room it was born in. This is
the control, and it is the reason the next paragraph is a finding rather than a complaint.

**The table is confidently wrong where it does not.** A SQLite database, an X.509
certificate, a PEM private key, a PNG, a JPEG, an `ar` archive, an ELF object and a file of
random bytes all come out **`plain`** — the same name the round used for "a file with no
structure". On the unseen room the table separates **114 of 189** different pairs (60.3 %).

The cost is not a mislabelled object. A need is a *target kind*: an agent whose vocabulary
cannot name a certificate cannot hold the goal "extract the public key from this certificate".
It is not that it answers wrongly; it is that it cannot ask. Counted on the room: **11 of 19**
producer kinds are collapsed into one name, and the vocabulary offers five names for the
nineteen kinds present.

## 3. What replaces the table, and why it is not a second table

The guide already contains the right idea one layer up, and the last round used it for goals
and left types to the table: **a page declares a check** — a flag whose prose is a question and
whose argument is the object (`gzip -t`, `tar -tf`, `unzip -t`, `jq .`). 2,319 such
(program, flag) pairs are declared across the 446 pages this machine prints.

Let those be the type system, under a rule that names no program:

> A declared check is a **witness** when
> 1. it **separates** — accepts at least one object and rejects at least one;
> 2. it **repeats** — the same verdict in two independent copies of the room;
> 3. it **observes** — it changes nothing in the room;
> 4. it is **content-invariant per kind** — every object of one producer kind gets one
>    verdict, in a second room of the same kinds with different content.

An object's type is then the set of witnesses that accept it: a signature, not a name.

Each of the four parts removes something real, and each is listed in the receipt by name:

| part | what it removes | measured |
|---|---|---|
| separates | `--help`, declared by 342 of 446 pages as a "read-only check" | **1,338** of 2,319 accept every object |
| separates | checks that accept nothing here | **913** accepted no object |
| repeats | anything nondeterministic | 66 separated, 64 repeated |
| observes | `shred -v`, `ln -v`, `split -v`, ImageMagick's `stream` | **16** declared checks WRITE to the object they are asked about |
| content-invariant | `perl -c`, `rgrep -l/-n/-H`, `node --trace-*` | **19** of 64 contradicted themselves between two rooms |

The `observes` line is the one I did not expect and the one that matters most. This tree's
existing `check_flags()` — the function that decides what counts as a read-only check — keeps
any flag whose prose starts with `list, show, print, display, test, check, verify, give` and
whose argument is none. By that rule **`shred --verbose` is a read-only check.** It is not: it
overwrote the object it was asked about, and it "separated" the room precisely because
destroying an object changes the answer. A "read-only check" list that contains a destructive
command is the same class of defect as a benchmark whose answer is in the prompt.

What survives is 45 checks, and their signatures separate **155 of 189** different pairs
(82.0 %) on the unseen room, against the table's 114.

## 4. What the witnesses actually buy, said plainly

Forty-five names is a flattering number, so here is the correcting measurement. Group the
witnesses by the *verdict vector* they produce over a room: 45 witnesses fall into **4**
distinctions (classes of 27, 16, 1, 1). Forty-one of the forty-five are **aliases** — the same
question asked by `gzip -t`, `gunzip -t`, `zcat -t`, `uncompress -t`, `gzip --test`, … The
honest count of what the rule discovered on this machine is **four questions**, not
forty-five:

1. *is it a gzip stream?* (27 spellings across gzip/gunzip/zcat/uncompress — and it accepts
   `zip` and `tar.gz`, correctly, because both really do contain a gzip member);
2. *is it binary?* (`scriptreplay --summary` aborts with `replay_emit` on binary and accepts
   text — a distinction no word in the table names);
3. *does `iconv` accept it as text?*
4. *does `node` tolerate it?* (the 27-name class accepts `data.json` and `empty.bin` and
   rejects everything else; whatever the mechanism, it separates.)

So the discovery is real but small: **four distinctions, 41 redundant names, 82 % of pair
differences.** Four is not nineteen. That gap is the residual, and the receipt names it with a
price rather than a default: five classes remain for twenty objects, with
**`log2(class)` bits undecidable** per class — 1.585 bits for gzip-vs-tar.gz-vs-zip, for
example, which no check on this machine can pay.

## 5. Should a refusal read once be stored?

The last round's third obligation, answered the same way — by running the rule twice, on two
rooms of the **same kinds** with different content.

The witness sets are **identical**: 45 checks, same 45, on both rooms. That is the answer:
a witness is **derived from the pages and the room, not learned from experience**, so storing
one buys nothing, and a stored copy is a liability the day a page changes. What a store *would*
hold is the empty set. The same argument covers the refusal reader from the last round: the
sentence read once is re-derived next time from the program's own words, and the honest
generalised form of "keep it" is *keep the rule that finds it*, not the sentence.

The invariance test is the same measurement from the other side, and it is the part that makes
the answer non-trivial: **19 of 64** checks that passed parts 1–3 changed their verdict on an
object of the same kind in the second room. They were not knowledge about types; they were
knowledge about a file's contents wearing a type's clothes.

## 6. The gates, and which one nearly failed

Declared before the run, all seven met:

| gate | result |
|---|---|
| T1 the written table is right where it has a name | **MET** — 21/21 different pairs on the guide's own room |
| T2 it collapses kinds it never named | **MET** — 11 producer kinds inside `plain` |
| T3 the witness rule finds checks with no program named | **MET** — 2,319 candidates → 45 witnesses |
| T4 the signature separates more than the written name | **MET** — 155/189 vs 114/189 |
| T5 the residual is named, not hidden | **MET** — 5 classes, `log2` price per class |
| T6 storing buys nothing, or the difference is named | **MET** — both rooms give the same 45 |
| T7 zero model calls, zero parameters, zero network | **MET** |

**And which one nearly failed, because it is the honest part of this file.** The first version
of T3 passed with 64 witnesses that included `perl -c`, `rgrep -l` and `node --trace-exit`.
The second version raised T4 to 160 of 189 — a *better* number — by keeping them. Both were
wrong in the same way: those checks separate by reading an object's *content* and calling it a
*type*. The invariance test exists because a gate that improves when a defect is added is not
a gate. With it, T4 fell to 155 and the witness count to 45, which is the number that survives
a room the witnesses were not fitted on.

The first version also failed T1 for a reason worth recording: a "check" it ran, `ln --verbose`,
**mutated the room between objects**, so the objects were not what the table was asked about.
That is what put the `observes` part in the rule.

## 7. What is real, what is not

**Real.** A room of kinds this tree never named, built by their own producers. A measured
statement of what the hand-written kind table costs there: 11 of 19 kinds collapsed, 60.3 % of
pair differences. A rule that turns *declared checks* into a type system with no program named
and no table written, which separates 82 % and tells on itself where it cannot: 4 distinctions
behind 45 names, 5 residual classes, `log2` bits. And a mechanical answer to "should it be
stored": no, and here is the test that says so.

**Not real.** "The machine can type anything now." An object that no declared check can
examine has the empty signature and lands in the residual class with everything else — reported,
not hidden. "Nineteen types." Four distinctions. "A signature is a name." `gzip -t+gunzip -t+…`
is not the word *gzip*; it is what the machine can still say about an object once everyone who
knew the word is gone — which is the useful thing and also the smaller thing.

**Not measured.** A room whose kinds need a check that *takes an argument* (`sqlite3`,
`openssl verify`, `jq` with a filter) — the rule only reads no-argument checks, and a second
derivation would be needed. Browser accessibility trees, the analogue the last round named. And
whether the four distinctions are the *right* four for any goal but the ones written here.

## 8. The one line

> **A type you wrote is a type you guess: the table is perfect on the room it was born in and
> collapses eleven kinds into one name on the next room. A type you can check is a type you
> have, and the machine will tell you exactly how many distinct questions it can still ask —
> four here — and which of its own declarations are not questions at all but writes.**

## 9. Next step, pre-registered

The rule reads only checks that take no argument of their own, which is why `sqlite3`,
`openssl verify` and `jq` are absent from it. The next round: derive the **argument** a check
needs from the same page (`-f ARCHIVE`, `-in FILE`), let witnesses take that argument, and
measure whether the residual on this room falls below five classes. Falsifier, declared now:
if the argument-carrying witnesses do not reduce the class count, then the residual was never
about the checks — it was about what the objects can exhibit — and the type system has a
ceiling that no further derivation moves.

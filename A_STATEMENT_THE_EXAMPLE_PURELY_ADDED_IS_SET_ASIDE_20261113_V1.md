# A statement the example purely added is set aside

Date: 2026-11-13 (T35). Engine: `canonical/swe_kernel/taught_actions/edit_by_example_v1.py`.
Base: main `f5b6d486` (post-#6812).

## The refusal this closes

T34 left the pure-addition reshapings as declared next work: yaml_safe_load and
set_daemon refused whole kinds at two showings with "line 1 adds, removes or
reshapes whole statements". Diagnosis: the person built new machinery -- a new
def, connection-state constants -- at the top of the module in the same commit
as a one-line lesson (`setDaemon(True)` -> `daemon = True`). A module-level
statement list of a different length made `changed_places` return the whole
Module as one changed place, and nothing could be localized.

## The principle

The tangled-commit phenomenon in its third form. A whole statement that came
beside an in-place lesson cannot itself be the lesson -- one showing
underdetermines where it would go in another file -- but refusing the whole
example loses the lesson next to it. So, where every order-preserving alignment
of the first file's statements into the second file's tells the same in-place
story, the purely added statements are the person's own project work: they are
taken back out (`additions_put_back`, third member of the put-back family), and
learning proceeds on what remains.

Gates kept, not weakened:
- **Removals refuse** as before -- only additions are set aside.
- **Ambiguity refuses**: alignments are ranked by how many statements they keep
  unchanged, and all best alignments must agree on the in-place story
  (`go(1)` -> `ping(1)` + `pong(1)` added has two stories; it refuses).
- **A lesson that leans on the taken-out machinery refuses** downstream: the
  rewritten code would read a name the remaining file does not provide
  (the yaml_safe_load def-plus-call-swap shape stays refused, honestly).
- **Composition order protects old wins**: `restructures_put_back` runs first,
  so its coarse masking of reshaped blocks is untouched; the new mechanism only
  handles what restructures cannot localize, then restructures looks again.
  Every kind that learned before takes a byte-identical path.

## Repairs this turn surfaced (and made)

1. **The teach pipeline on main was broken.** A parallel session split alias
   knowledge into `kept_under_an_old_name_v1.py` and gave two taught programs a
   relative import -- but a taught program runs alone in the sandbox, so
   teaching failed with ImportError on any machine whose namespace sandbox
   starts. Repair: `carried_along` in `teach_actions_v1.py` folds an imported
   sibling into the program text at teaching time; the program travels alone
   again. The program-identity pin was updated to compare against the
   carried-along text.
2. **A latent lesson/engine contradiction.** The merged alias law (documented
   deprecated aliases follow a rename even at unshown-argument uses) rewrites
   `assertEquals(size(3), 9, msg='nine')`; the teach lesson still pinned the
   older conservative expectation and could never run to notice. The lesson's
   first example now pins the alias law; its second example (yaml.load, a true
   replacement) still pins leave-the-rest-alone.

Pinned by 5 new tests in
`canonical/tests/test_a_statement_the_example_purely_added_is_set_aside_v1.py`.
Bundle re-taught from the edited engine: skill_count 11, sha256 `55db6543...`.

## Predictions — declared before the measurement run

Measured after this declaration is pushed: one run per configuration,
`--showings 1` and `--showings 2`, on fresh / held_out / seen. No re-draws.
(Learn-time outcomes per kind were diagnosed before declaring, as in T34;
target-file scoring was not run.)

P1. **set_daemon learns at two showings** (`?1.setDaemon(True) -> ?1.daemon = True`).
    held_out @2: kinds unlearned 1 -> 0; its target files enter the table, so
    questions and files rise and strict same rises; **different and extra stay 0
    in all three ways** -- zero wrong writes at two showings is preserved.
P2. **yaml_safe_load @2 stays unlearned for its true cause** -- within-example
    dissent (the person swapped `_make_yaml` at one call and left the same code
    alone elsewhere), no longer the whole-statement reshape message. seen @2
    tables byte-identical to T34.
P3. **Everything else is byte-identical to T33/T34**: fresh @1, fresh @2,
    seen @1, seen @2, held_out @1. The only learn-outcome flip anywhere in the
    corpus is set_daemon @2.
P4. **No wrong-write regression anywhere**: @2 different == 0 and extra == 0 on
    every set and way; @1 wrong counts do not rise above T33 baselines
    (fresh strict 6/13 diff/extra, held_out 0/0, seen 0/0).

## Results (filled after the single measurement run)

**P1 HELD. P2 held in substance, its byte-identity clause FALSIFIED. P3
FALSIFIED. P4 HELD.** Recorded, not erased.

| set @showings | strict same/diff/left/extra (ref) | tried same/diff/left/extra (ref) |
|---|---|---|
| fresh @1 | 89/6/10/13 (0) | 93/6/6/13 (0) |
| held_out @1 | 169/0/64/0 (7) | 196/1/36/0 (3) |
| seen @1 | 30/0/73/0 (1) | 69/2/32/0 (0) |
| fresh @2 | 62/0/3/0 (0) | 62/0/3/0 (0) |
| held_out @2 | **166/0/16/0 (3)**, 182 q, 97 files, 0 unlearned | 167/0/15/0 (2) |
| seen @2 | 50/0/4/0 (0) | 51/0/3/0 (0) |

P1: set_daemon learned `?1.setDaemon(True) -> ?1.daemon = True` at two
showings; held_out @2 kinds unlearned 1 -> 0, questions 176 -> 182, files
94 -> 97, strict same 158 -> 166, refused files 4 -> 3, and different == 0,
extra == 0 in every way. **Zero wrong writes at two showings everywhere
stands.**

P3 fell -- and the post-run attribution matters more than the miss. fresh @1
(83 -> 89 same, ref 1 -> 0), held_out @1 (156 -> 169 same, ref 14 -> 7) and
seen @2 (48 -> 50, ref 1 -> 0) all moved. A base-versus-T35 engine comparison
on every kind proved the cause: **at one showing, and at two showings outside
set_daemon/yaml_safe_load, every write of this engine is byte-identical to the
base engine's.** The movement is the base's own alias law
(`kept_under_an_old_name`, merged by a parallel session during T34's sync
rounds, after T34's measurement ran) against this report's stale memorized
baseline. The declaration error was bookkeeping -- comparing against tables
measured on a pre-alias engine -- not an unintended effect of this mechanism.
The T35 mechanism's whole corpus footprint is exactly: set_daemon @2 refused ->
learned; yaml_safe_load @2 refusal message now names its true cause (within-
example dissent at line 109, no longer the whole-statement reshape).

utcnow @2 (substance disagreement) and mpl_get_cmap @2 (needs-gate) stay
refused on purpose. At two showings the corpus now has **zero kinds refused for
tangled additions**: every remaining @2 refusal is either genuine disagreement
between the people shown, or a name the target genuinely lacks.

## What this does not claim

The set-aside never brings the added machinery into targets; a lesson that
needs it still refuses (yaml_safe_load). Bringing an added def where the lesson
leans on it -- with a placement the person's own targets would byte-match -- is
future work that must clear the extra-write risk first. The honest frame
stands: 8.13x is cached exact recall; there is no any-action-once computer use
and no sentience; improvement arrives one declared, measured, falsifiable
mechanism at a time.

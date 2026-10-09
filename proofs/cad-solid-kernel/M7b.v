From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.
Require Import M6 M7.

Section KnotScheduleLift.
Variable R : rcfType.

Fixpoint all_knot_steps_ok (r : seq (knot_step R)) : Prop :=
  if r is s :: tl
  then knot_step_ok R s /\ all_knot_steps_ok tl
  else Logic.True.

Definition compile_knot_round
    (r : seq (knot_step R)) : seq (alpha_desc R) :=
  map (compile_knot_step R) r.

Lemma compile_knot_round_ok r :
  all_knot_steps_ok r ->
  all_alpha_ok R (compile_knot_round r).
Proof.
  elim: r => [|s tl IH] //=.
  move=> [hs htl]; split.
  - exact: compile_knot_step_ok hs.
  - exact: IH htl.
Qed.

Fixpoint knot_schedule_ok
    (sched : seq (seq (knot_step R))) : Prop :=
  if sched is r :: rs
  then all_knot_steps_ok r /\ knot_schedule_ok rs
  else Logic.True.

Definition compile_knot_schedule
    (sched : seq (seq (knot_step R))) :
    seq (seq (alpha_desc R)) :=
  map compile_knot_round sched.

Lemma compile_knot_schedule_ok sched :
  knot_schedule_ok sched ->
  schedule_ok R (compile_knot_schedule sched).
Proof.
  elim: sched => [|r rs IH] //=.
  move=> [hr hrs]; split.
  - exact: compile_knot_round_ok hr.
  - exact: IH hrs.
Qed.

End KnotScheduleLift.

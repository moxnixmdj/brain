From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.
Require Import M7 M7b M8.

Section IndexedScheduleValidation.
Variable R : rcfType.

Definition expected_step (p span r j : nat) : indexed_step :=
  {| is_left := j + span - p;
     is_right := j.+1 + span - r |}.

Definition expected_round (p span r : nat) : seq indexed_step :=
  map (expected_step p span r) (iota r (p - r + 1)).

Definition expected_index_schedule (p span : nat) :
    seq (seq indexed_step) :=
  map (fun r => expected_round p span r) (iota 1 p).

Fixpoint all_indexed_steps_ok
    (knots : seq R) (span : nat) (r : seq indexed_step) : Prop :=
  if r is s :: tl
  then indexed_step_ok R knots span s /\
       all_indexed_steps_ok knots span tl
  else Logic.True.

Fixpoint indexed_schedule_ok
    (knots : seq R) (span : nat)
    (sched : seq (seq indexed_step)) : Prop :=
  if sched is r :: rs
  then all_indexed_steps_ok knots span r /\
       indexed_schedule_ok knots span rs
  else Logic.True.

Definition materialize_round
    (knots : seq R) (span : nat) (r : seq indexed_step) :
    seq (knot_step R) :=
  map (materialize_step R knots span) r.

Definition materialize_schedule
    (knots : seq R) (span : nat)
    (sched : seq (seq indexed_step)) :
    seq (seq (knot_step R)) :=
  map (materialize_round knots span) sched.

Lemma materialize_round_ok knots span r :
  sorted (fun x y : R => x <= y) knots ->
  all_indexed_steps_ok knots span r ->
  all_knot_steps_ok R (materialize_round knots span r).
Proof.
  move=> hs.
  elim: r => [|s tl IH] //=.
  move=> [hst htl]; split.
  - exact: materialize_step_ok hs hst.
  - exact: IH htl.
Qed.

Lemma materialize_schedule_ok knots span sched :
  sorted (fun x y : R => x <= y) knots ->
  indexed_schedule_ok knots span sched ->
  knot_schedule_ok R (materialize_schedule knots span sched).
Proof.
  move=> hs.
  elim: sched => [|r rs IH] //=.
  move=> [hr hrs]; split.
  - exact: materialize_round_ok hs hr.
  - exact: IH hrs.
Qed.

Definition schedule_certificate
    (knots : seq R) (p span : nat)
    (candidate : seq (seq indexed_step)) : Prop :=
  candidate = expected_index_schedule p span /\
  indexed_schedule_ok knots span candidate.

Theorem certified_index_schedule_materializes
    knots p span candidate :
  sorted (fun x y : R => x <= y) knots ->
  schedule_certificate knots p span candidate ->
  knot_schedule_ok R (materialize_schedule knots span candidate).
Proof.
  move=> hs [_ hc].
  exact: materialize_schedule_ok hs hc.
Qed.

End IndexedScheduleValidation.

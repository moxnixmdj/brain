From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.
Require Import M7.

Import Order.Theory.
Import Num.Theory.
Open Scope ring_scope.
Close Scope oterm_scope.

Section KnotIndexValidation.
Variable R : rcfType.

Definition knot_at (knots : seq R) (i : nat) : R :=
  nth 0%R knots i.

Lemma knot_at_mono knots (i j : nat) :
  sorted (fun x y : R => x <= y) knots ->
  (i < size knots)%N -> (j < size knots)%N -> (i <= j)%N ->
  knot_at knots i <= knot_at knots j.
Proof.
  move=> hs hi hj hij.
  exact: (@sorted_leq_nth R (fun x y : R => x <= y)
            Order.le_trans lexx 0%R knots hs i j hi hj hij).
Qed.

Record indexed_step := {
  is_left : nat;
  is_right : nat
}.

Definition materialize_step
    (knots : seq R) (span : nat) (s : indexed_step) : knot_step R :=
  {| ks_knot_lo := knot_at knots (is_left s);
     ks_span_lo := knot_at knots span;
     ks_span_hi := knot_at knots span.+1;
     ks_knot_hi := knot_at knots (is_right s) |}.

Definition indexed_step_ok
    (knots : seq R) (span : nat) (s : indexed_step) : Prop :=
  (is_left s < size knots)%N /\
  (span < size knots)%N /\
  (span.+1 < size knots)%N /\
  (is_right s < size knots)%N /\
  (is_left s <= span)%N /\
  (span.+1 <= is_right s)%N /\
  knot_at knots (is_left s) < knot_at knots (is_right s).

Lemma materialize_step_ok knots span s :
  sorted (fun x y : R => x <= y) knots ->
  indexed_step_ok knots span s ->
  knot_step_ok R (materialize_step knots span s).
Proof.
  move=> hs [hli [hsp [hsp1 [hri [hls [hsr hstrict]]]]]].
  rewrite /knot_step_ok /materialize_step /knot_at /=.
  split.
  - exact: (@sorted_leq_nth R (fun x y : R => x <= y)
              Order.le_trans lexx 0%R knots hs
              (is_left s) span hli hsp hls).
  - split.
    + exact: (@sorted_leq_nth R (fun x y : R => x <= y)
                Order.le_trans lexx 0%R knots hs
                span span.+1 hsp hsp1 (leqnSn span)).
    + split.
      * exact: (@sorted_leq_nth R (fun x y : R => x <= y)
                  Order.le_trans lexx 0%R knots hs
                  span.+1 (is_right s) hsp1 hri hsr).
      * exact: hstrict.
Qed.

End KnotIndexValidation.

From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.
Require Import M1 M3.

Import GRing.
Import Order.Theory.
Import Num.Internals.
Import Num.Theory.
Open Scope ring_scope.
Close Scope oterm_scope.

Section DeBoorSchedule.

Variable R : rcfType.

Definition p2 := M1.poly2 R.

Definition in01 (x : R) : Prop := 0%R <= x /\ x <= 1%R.

Lemma lerp_ge0 q a b :
  in01 q -> 0%R <= a -> 0%R <= b ->
  0%R <= lerp_val R q a b.
Proof.
  move=> [hq0 hq1] ha hb.
  apply: addr_ge0.
  - apply: mulr_ge0 => //.
    by rewrite subr_ge0.
  - exact: mulr_ge0 hq0 hb.
Qed.

Lemma lerp_le1 q a b :
  in01 q -> in01 a -> in01 b ->
  lerp_val R q a b <= 1%R.
Proof.
  move=> [hq0 hq1] [ha0 ha1] [hb0 hb1].
  have h1q0 : 0%R <= 1%R - q by rewrite subr_ge0.
  have hleft : (1%R - q) * a <= (1%R - q) * 1%R.
  - exact: ler_pM h1q0 ha0 (lexx _) ha1.
  have hright : q * b <= q * 1%R.
  - exact: ler_pM hq0 hb0 (lexx _) hb1.
  have hsum := lerD hleft hright.
  move: hsum.
  by rewrite /lerp_val !mulr1 subrK.
Qed.

Lemma lerp_in01 q a b :
  in01 q -> in01 a -> in01 b ->
  in01 (lerp_val R q a b).
Proof.
  move=> hq ha hb; split.
  - exact: lerp_ge0 hq ha.1 hb.1.
  - exact: lerp_le1 hq ha hb.
Qed.

Record alpha_desc := {
  alpha0 : R;
  alpha1 : R
}.

Definition alpha_val (q : R) (a : alpha_desc) :=
  lerp_val R q (alpha0 a) (alpha1 a).

Definition alpha_poly (a : alpha_desc) : p2 :=
  lerp_poly R (M1.P2U R)
    (M1.P2Const R (alpha0 a))
    (M1.P2Const R (alpha1 a)).

Lemma alpha_poly_correct a u v :
  M1.poly2_eval R (alpha_poly a) u v = alpha_val u a.
Proof.
  by rewrite /alpha_poly /alpha_val lerp_poly_correct /=.
Qed.

Definition alpha_ok (a : alpha_desc) : Prop :=
  in01 (alpha0 a) /\ in01 (alpha1 a).

Lemma alpha_val_in01 q a :
  in01 q -> alpha_ok a -> in01 (alpha_val q a).
Proof.
  by move=> hq [h0 h1]; apply: lerp_in01.
Qed.

Fixpoint all_alpha_ok (s : seq alpha_desc) : Prop :=
  if s is a :: tl then alpha_ok a /\ all_alpha_ok tl else Logic.True.

Fixpoint round_val
    (q : R) (alphas : seq alpha_desc) (vals : seq R) : seq R :=
  match alphas with
  | a :: ars =>
      match vals with
      | x :: rest =>
          match rest with
          | y :: yt =>
              lerp_val R (alpha_val q a) x y :: round_val q ars (y :: yt)
          | [::] => vals
          end
      | [::] => vals
      end
  | [::] => vals
  end.

Fixpoint round_poly
    (alphas : seq alpha_desc) (vals : seq p2) : seq p2 :=
  match alphas with
  | a :: ars =>
      match vals with
      | x :: rest =>
          match rest with
          | y :: yt =>
              lerp_poly R (alpha_poly a) x y :: round_poly ars (y :: yt)
          | [::] => vals
          end
      | [::] => vals
      end
  | [::] => vals
  end.

Lemma round_poly_correct alphas vals u v :
  map (fun p => M1.poly2_eval R p u v) (round_poly alphas vals)
  =
  round_val u alphas
    (map (fun p => M1.poly2_eval R p u v) vals).
Proof.
  elim: alphas vals => [|a ars IH] [|x [|y yt]] //=.
  by rewrite /lerp_poly /alpha_poly /alpha_val /lerp_val /= IH.
Qed.

Lemma round_all_pos q alphas vals :
  in01 q ->
  all_alpha_ok alphas ->
  all_pos R vals ->
  all_pos R (round_val q alphas vals).
Proof.
  move=> hq.
  elim: alphas vals => [|a ars IH] [|x [|y yt]] //=.
  move=> [ha hat] [hx [hy hyt]].
  split.
  - have hai : in01 (alpha_val q a) := alpha_val_in01 q a hq ha.
    exact: lerp_pos R (alpha_val q a) x y hai.1 hai.2 hx hy.
  - exact: IH (y :: yt) hat (conj hy hyt).
Qed.

Lemma round_nonempty q alphas vals :
  vals <> [::] -> round_val q alphas vals <> [::].
Proof.
  move=> hne.
  case: alphas => [|a ars] //.
  by case: vals hne => [|x [|y yt]].
Qed.

Fixpoint run_val
    (q : R) (sched : seq (seq alpha_desc)) (vals : seq R) : seq R :=
  if sched is r :: rs
  then run_val q rs (round_val q r vals)
  else vals.

Fixpoint run_poly
    (sched : seq (seq alpha_desc)) (vals : seq p2) : seq p2 :=
  if sched is r :: rs
  then run_poly rs (round_poly r vals)
  else vals.

Lemma run_poly_correct sched vals u v :
  map (fun p => M1.poly2_eval R p u v) (run_poly sched vals)
  =
  run_val u sched
    (map (fun p => M1.poly2_eval R p u v) vals).
Proof.
  elim: sched vals => [|r rs IH] vals //=.
  rewrite IH round_poly_correct.
  by [].
Qed.

Fixpoint schedule_ok (sched : seq (seq alpha_desc)) : Prop :=
  if sched is r :: rs
  then all_alpha_ok r /\ schedule_ok rs
  else Logic.True.

Lemma run_all_pos q sched vals :
  in01 q ->
  schedule_ok sched ->
  all_pos R vals ->
  all_pos R (run_val q sched vals).
Proof.
  move=> hq.
  elim: sched vals => [|r rs IH] vals //=.
  move=> [hr hrs] hvals.
  exact: IH (round_val q r vals) hrs
           (round_all_pos q r vals hq hr hvals).
Qed.

Lemma run_nonempty q sched vals :
  vals <> [::] -> run_val q sched vals <> [::].
Proof.
  elim: sched vals => [|r rs IH] vals hne //=.
  exact: IH (round_val q r vals)
           (round_nonempty q r vals hne).
Qed.

Definition deboor_poly
    (sched : seq (seq alpha_desc)) (vals : seq p2) : p2 :=
  head (M1.P2Const R 0%R) (run_poly sched vals).

Definition deboor_val
    (q : R) (sched : seq (seq alpha_desc)) (vals : seq R) : R :=
  head 0%R (run_val q sched vals).

Lemma head_poly_eval ps u v :
  M1.poly2_eval R (head (M1.P2Const R 0%R) ps) u v
  =
  head 0%R (map (fun p => M1.poly2_eval R p u v) ps).
Proof.
  by case: ps.
Qed.

Lemma deboor_poly_correct sched vals u v :
  M1.poly2_eval R (deboor_poly sched vals) u v
  =
  deboor_val u sched
    (map (fun p => M1.poly2_eval R p u v) vals).
Proof.
  rewrite /deboor_poly /deboor_val head_poly_eval.
  by rewrite run_poly_correct.
Qed.

Lemma deboor_val_pos q sched vals :
  in01 q ->
  schedule_ok sched ->
  all_pos R vals ->
  vals <> [::] ->
  0%R < deboor_val q sched vals.
Proof.
  move=> hq hs hv hne.
  rewrite /deboor_val.
  have hp := run_all_pos q sched vals hq hs hv.
  have hw := run_nonempty q sched vals hne.
  case Hr: (run_val q sched vals) hp hn => [|x xs] //=.
  by move=> [hx _] _.
Qed.

End DeBoorSchedule.

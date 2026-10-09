From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.
Require Import M1.

Import GRing.
Import Order.Theory.
Import Num.Internals.
Import Num.Theory.
Open Scope ring_scope.
Close Scope oterm_scope.

Section DeCasteljau1D.

Variable R : rcfType.

Definition p2 := poly2 R.

Definition lerp_val (x a b : R) : R :=
  (1%R - x) * a + x * b.

Definition lerp_poly (x a b : p2) : p2 :=
  P2Add R (P2Mul R (P2Add R (P2Const R 1%R) (P2Opp R x)) a)
        (P2Mul R x b).

Lemma lerp_poly_correct x a b u v :
  poly2_eval R (lerp_poly x a b) u v
  = lerp_val (poly2_eval R x u v)
             (poly2_eval R a u v)
             (poly2_eval R b u v).
Proof.
  by rewrite /lerp_poly /lerp_val /=.
Qed.

Lemma lerp_pos x a b :
  0%R <= x -> x <= 1%R ->
  0%R < a -> 0%R < b ->
  0%R < lerp_val x a b.
Proof.
  move=> hx0 hx1 ha hb.
  have [->|hx0n] := eqVneq x 0%R.
  - by rewrite /lerp_val subr0 mul1r mul0r addr0.
  have hxpos : 0%R < x.
  - by rewrite lt_neqAle eq_sym hx0n hx0.
  have [->|hx1n] := eqVneq x 1%R.
  - by rewrite /lerp_val subrr mul0r mul1r add0r.
  have hxlt1 : x < 1%R.
  - by rewrite lt_neqAle hx1n hx1.
  have h1x : 0%R < 1%R - x.
  - by rewrite subr_gt0.
  apply: addr_gt0.
  - exact: mulr_gt0 h1x ha.
  - exact: mulr_gt0 hxpos hb.
Qed.

Fixpoint all_pos (s : seq R) : Prop :=
  if s is a :: tl then 0%R < a /\ all_pos tl else Logic.True.

Fixpoint blend_val (x : R) (s : seq R) : seq R :=
  match s with
  | a :: ((b :: tl) as rest) =>
      lerp_val x a b :: blend_val x rest
  | _ => s
  end.

Fixpoint blend_poly (x : p2) (s : seq p2) : seq p2 :=
  match s with
  | a :: ((b :: tl) as rest) =>
      lerp_poly x a b :: blend_poly x rest
  | _ => s
  end.

Lemma blend_poly_correct x ps u v :
  map (fun p => poly2_eval R p u v) (blend_poly x ps)
  =
  blend_val (poly2_eval R x u v)
            (map (fun p => poly2_eval R p u v) ps).
Proof.
  elim: ps => [|a [|b tl] IH] //=.
  by rewrite /lerp_poly /lerp_val /= IH.
Qed.

Lemma blend_all_pos x s :
  0%R <= x -> x <= 1%R ->
  all_pos s -> all_pos (blend_val x s).
Proof.
  move=> hx0 hx1.
  elim: s => [|a [|b tl] IH] //=.
  move=> [ha [hb htl]].
  split.
  - exact: lerp_pos hx0 hx1 ha hb.
  - apply: IH.
    by split.
Qed.

Fixpoint dc_val_n (n : nat) (x : R) (s : seq R) : R :=
  match n with
  | 0 => head 0%R s
  | n'.+1 => dc_val_n n' x (blend_val x s)
  end.

Fixpoint dc_poly_n (n : nat) (x : p2) (s : seq p2) : p2 :=
  match n with
  | 0 => head (P2Const R 0%R) s
  | n'.+1 => dc_poly_n n' x (blend_poly x s)
  end.

Lemma dc_poly_n_correct n x ps u v :
  poly2_eval R (dc_poly_n n x ps) u v
  =
  dc_val_n n (poly2_eval R x u v)
    (map (fun p => poly2_eval R p u v) ps).
Proof.
  elim: n ps => [|n IH] ps /=.
  - by case: ps.
  - rewrite IH blend_poly_correct.
    by [].
Qed.

Lemma dc_val_n_pos n x s :
  0%R <= x -> x <= 1%R ->
  all_pos s -> s != [::] ->
  0%R < dc_val_n n x s.
Proof.
  elim: n s => [|n IH] s hx0 hx1 hpos hne /=.
  - by case: s hpos hne => [|a tl] //= [ha _] _.
  - apply: IH => //.
    + exact: blend_all_pos hx0 hx1 hpos.
    + case: s hpos hne => [|a [|b tl]] //=.
Qed.

Definition dc_val (x : R) (s : seq R) :=
  dc_val_n (size s).-1 x s.

Definition dc_poly (x : p2) (s : seq p2) :=
  dc_poly_n (size s).-1 x s.

Lemma dc_poly_correct x ps u v :
  poly2_eval R (dc_poly x ps) u v
  =
  dc_val (poly2_eval R x u v)
    (map (fun p => poly2_eval R p u v) ps).
Proof.
  by rewrite /dc_poly /dc_val size_map dc_poly_n_correct.
Qed.

Lemma dc_val_pos x s :
  0%R <= x -> x <= 1%R ->
  all_pos s -> s != [::] ->
  0%R < dc_val x s.
Proof.
  exact: dc_val_n_pos.
Qed.

End DeCasteljau1D.

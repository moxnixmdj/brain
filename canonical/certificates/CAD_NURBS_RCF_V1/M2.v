From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.
Require Import M1.

Import GRing.
Import Order.Theory.
Import Num.Internals.
Import Num.Theory.
Import ord.
Open Scope ring_scope.
Close Scope oterm_scope.

Section CollisionM2.

Variable R : rcfType.

Definition p2 := poly2 R.
Definition tR2 := term R.
Definition fR2 := ord.formula R.

Record rational_patch := {
  rpx_num : p2;
  rpy_num : p2;
  rpz_num : p2;
  rp_den  : p2
}.

Definition rat_den (p : rational_patch) u v :=
  poly2_eval R (rp_den p) u v.

Definition rat_x (p : rational_patch) u v :=
  poly2_eval R (rpx_num p) u v / rat_den p u v.
Definition rat_y (p : rational_patch) u v :=
  poly2_eval R (rpy_num p) u v / rat_den p u v.
Definition rat_z (p : rational_patch) u v :=
  poly2_eval R (rpz_num p) u v / rat_den p u v.

Definition in01_t2 (x : tR2) : fR2 :=
  (0 <=% x /\ x <=% 1)%oT.

Definition in01R (x : R) : Prop :=
  0%R <= x /\ x <= 1%R.

Lemma div_eq_cross (x y z t : R) :
  y != 0%R -> t != 0%R ->
  (x / y = z / t <-> x * t = z * y).
Proof.
  move=> hy ht; split=> h.
  - apply/eqP.
    rewrite -eqr_div //.
    by apply/eqP.
  - apply/eqP.
    rewrite eqr_div //.
    by apply/eqP.
Qed.

Definition rational_collision_body
    (a b : rational_patch) : fR2 :=
  (in01_t2 'X_0 /\
   in01_t2 'X_1 /\
   in01_t2 'X_2 /\
   in01_t2 'X_3 /\
   0 <% poly2_term R (rp_den a) 'X_0 'X_1 /\
   0 <% poly2_term R (rp_den b) 'X_2 'X_3 /\
   poly2_term R (rpx_num a) 'X_0 'X_1 * poly2_term R (rp_den b) 'X_2 'X_3 ==
   poly2_term R (rpx_num b) 'X_2 'X_3 * poly2_term R (rp_den a) 'X_0 'X_1 /\
   poly2_term R (rpy_num a) 'X_0 'X_1 * poly2_term R (rp_den b) 'X_2 'X_3 ==
   poly2_term R (rpy_num b) 'X_2 'X_3 * poly2_term R (rp_den a) 'X_0 'X_1 /\
   poly2_term R (rpz_num a) 'X_0 'X_1 * poly2_term R (rp_den b) 'X_2 'X_3 ==
   poly2_term R (rpz_num b) 'X_2 'X_3 * poly2_term R (rp_den a) 'X_0 'X_1)%oT.

Definition compile_rational_collision
    (a b : rational_patch) : fR2 :=
  ('exists 'X_0,
   'exists 'X_1,
   'exists 'X_2,
   'exists 'X_3,
     rational_collision_body a b)%oT.

Definition rational_collision_at
    (a b : rational_patch) (u v s t : R) : Prop :=
  in01R u /\
  in01R v /\
  in01R s /\
  in01R t /\
  0%R < rat_den a u v /\
  0%R < rat_den b s t /\
  rat_x a u v = rat_x b s t /\
  rat_y a u v = rat_y b s t /\
  rat_z a u v = rat_z b s t.

Definition rational_patches_intersect a b :=
  exists u v s t : R, rational_collision_at a b u v s t.

Lemma rational_collision_body_correct a b u v s t :
  ord.holds [:: u; v; s; t] (rational_collision_body a b) <->
  rational_collision_at a b u v s t.
Proof.
  rewrite /rational_collision_body /rational_collision_at
          /in01_t2 /in01R
          /rat_x /rat_y /rat_z /rat_den /=.
  rewrite !poly2_term_correct.
  set da := poly2_eval R (rp_den a) u v.
  set db := poly2_eval R (rp_den b) s t.
  set ax := poly2_eval R (rpx_num a) u v.
  set bx := poly2_eval R (rpx_num b) s t.
  set ay := poly2_eval R (rpy_num a) u v.
  set byv := poly2_eval R (rpy_num b) s t.
  set az := poly2_eval R (rpz_num a) u v.
  set bz := poly2_eval R (rpz_num b) s t.
  split.
  - move=> [hu [hv [hs [ht [hda [hdb [hx [hy hz]]]]]]]].
    have nda : da != 0%R := lt0r_neq0 hda.
    have ndb : db != 0%R := lt0r_neq0 hdb.
    split; first exact hu.
    split; first exact hv.
    split; first exact hs.
    split; first exact ht.
    split; first exact hda.
    split; first exact hdb.
    split.
    + exact: (proj2 (div_eq_cross ax da bx db nda ndb) hx).
    + split.
      * exact: (proj2 (div_eq_cross ay da byv db nda ndb) hy).
      * exact: (proj2 (div_eq_cross az da bz db nda ndb) hz).
  - move=> [hu [hv [hs [ht [hda [hdb [hx [hy hz]]]]]]]].
    have nda : da != 0%R := lt0r_neq0 hda.
    have ndb : db != 0%R := lt0r_neq0 hdb.
    split; first exact hu.
    split; first exact hv.
    split; first exact hs.
    split; first exact ht.
    split; first exact hda.
    split; first exact hdb.
    split.
    + exact: (proj1 (div_eq_cross ax da bx db nda ndb) hx).
    + split.
      * exact: (proj1 (div_eq_cross ay da byv db nda ndb) hy).
      * exact: (proj1 (div_eq_cross az da bz db nda ndb) hz).
Qed.

Theorem compile_rational_collision_correct a b :
  ord.holds [::] (compile_rational_collision a b) <->
  rational_patches_intersect a b.
Proof.
  rewrite /compile_rational_collision /rational_patches_intersect /=.
  split.
  - move=> [u [v [s [t H]]]].
    exists u, v, s, t.
    change (ord.holds [:: u; v; s; t] (rational_collision_body a b)) in H.
    exact: (proj1 (rational_collision_body_correct a b u v s t) H).
  - move=> [u [v [s [t H]]]].
    exists u; exists v; exists s; exists t.
    change (ord.holds [:: u; v; s; t] (rational_collision_body a b)).
    exact: (proj2 (rational_collision_body_correct a b u v s t) H).
Qed.

End CollisionM2.

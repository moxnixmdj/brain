From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.

Import GRing.
Import Order.Theory.
Import Num.Internals.
Import ord.
Open Scope ring_scope.
Open Scope oterm_scope.

Section CollisionM0.

Variable R : rcfType.

Definition tR := term R.
Definition fR := ord.formula R.

Record affine_patch := {
  px0 : R; pxu : R; pxv : R;
  py0 : R; pyu : R; pyv : R;
  pz0 : R; pzu : R; pzv : R
}.

Definition affine_value
    (a0 au av u v : R) : R :=
  a0 + au * u + av * v.

Definition patch_x (p : affine_patch) u v :=
  affine_value (px0 p) (pxu p) (pxv p) u v.

Definition patch_y (p : affine_patch) u v :=
  affine_value (py0 p) (pyu p) (pyv p) u v.

Definition patch_z (p : affine_patch) u v :=
  affine_value (pz0 p) (pzu p) (pzv p) u v.

Definition affine_term
    (a0 au av : R) (u v : tR) : tR :=
  (a0%:T + au%:T * u + av%:T * v)%oT.

Definition in01_t (x : tR) : fR :=
  (0 <=% x /\ x <=% 1)%oT.

Definition in01 (x : R) : Prop :=
  0%R <= x /\ x <= 1%R.

Definition collision_body
    (a b : affine_patch) : fR :=
  (in01_t 'X_0 /\
   in01_t 'X_1 /\
   in01_t 'X_2 /\
   in01_t 'X_3 /\
   affine_term (px0 a) (pxu a) (pxv a) 'X_0 'X_1 ==
   affine_term (px0 b) (pxu b) (pxv b) 'X_2 'X_3 /\
   affine_term (py0 a) (pyu a) (pyv a) 'X_0 'X_1 ==
   affine_term (py0 b) (pyu b) (pyv b) 'X_2 'X_3 /\
   affine_term (pz0 a) (pzu a) (pzv a) 'X_0 'X_1 ==
   affine_term (pz0 b) (pzu b) (pzv b) 'X_2 'X_3)%oT.

Definition compile_collision
    (a b : affine_patch) : fR :=
  ('exists 'X_0,
   'exists 'X_1,
   'exists 'X_2,
   'exists 'X_3,
     collision_body a b)%oT.

Definition collision_at
    (a b : affine_patch) (u v s t : R) : Prop :=
  in01 u /\
  in01 v /\
  in01 s /\
  in01 t /\
  patch_x a u v = patch_x b s t /\
  patch_y a u v = patch_y b s t /\
  patch_z a u v = patch_z b s t.

Definition patches_intersect a b :=
  exists u v s t : R, collision_at a b u v s t.

Lemma collision_body_correct a b u v s t :
  ord.holds [:: u; v; s; t] (collision_body a b) <->
  collision_at a b u v s t.
Proof.
  by rewrite /collision_body /collision_at
             /in01_t /in01
             /affine_term
             /patch_x /patch_y /patch_z
             /affine_value /=.
Qed.

Theorem compile_collision_correct a b :
  ord.holds [::] (compile_collision a b) <->
  patches_intersect a b.
Proof.
  rewrite /compile_collision /patches_intersect /=.
  split.
  - move=> [u [v [s [t H]]]].
    exists u, v, s, t.
    change (ord.holds [:: u; v; s; t] (collision_body a b)) in H.
    exact: (proj1 (collision_body_correct a b u v s t) H).
  - move=> [u [v [s [t H]]]].
    exists u; exists v; exists s; exists t.
    change (ord.holds [:: u; v; s; t] (collision_body a b)).
    exact: (proj2 (collision_body_correct a b u v s t) H).
Qed.


Definition plane_z0 : affine_patch :=
  {| px0 := 0%R; pxu := 1%R; pxv := 0%R;
     py0 := 0%R; pyu := 0%R; pyv := 1%R;
     pz0 := 0%R; pzu := 0%R; pzv := 0%R |}.

Definition plane_z1 : affine_patch :=
  {| px0 := 0%R; pxu := 1%R; pxv := 0%R;
     py0 := 0%R; pyu := 0%R; pyv := 1%R;
     pz0 := 1%R; pzu := 0%R; pzv := 0%R |}.

Lemma plane_z0_self_intersects :
  patches_intersect plane_z0 plane_z0.
Proof.
  exists 0%R, 0%R, 0%R, 0%R.
  by rewrite /collision_at /in01 /patch_x /patch_y /patch_z
             /plane_z0 /affine_value /= !lexx !ler01.
Qed.

Lemma plane_z0_z1_disjoint :
  ~ patches_intersect plane_z0 plane_z1.
Proof.
  move=> [u [v [s [t H]]]].
  move: H.
  rewrite /collision_at /patch_x /patch_y /patch_z
          /plane_z0 /plane_z1 /affine_value /=.
  move=> [_ [_ [_ [_ [_ [_ Hz]]]]]].
  rewrite !mul0r !add0r !addr0 in Hz.
  have hneq := @oner_neq0 R.
  by rewrite -Hz eqxx in hneq.
Qed.

End CollisionM0.

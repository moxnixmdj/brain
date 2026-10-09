From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.

Import GRing.
Import Order.Theory.
Import Num.Internals.
Import ord.
Open Scope ring_scope.
Open Scope oterm_scope.

Section CollisionM1.

Variable R : rcfType.

Definition tR := term R.
Definition fR := ord.formula R.

Inductive poly2 :=
| P2Const of R
| P2U
| P2V
| P2Add of poly2 & poly2
| P2Opp of poly2
| P2Mul of poly2 & poly2.

Fixpoint poly2_eval (p : poly2) (u v : R) : R :=
  match p with
  | P2Const c => c
  | P2U => u
  | P2V => v
  | P2Add a b => poly2_eval a u v + poly2_eval b u v
  | P2Opp a => - poly2_eval a u v
  | P2Mul a b => poly2_eval a u v * poly2_eval b u v
  end.

Fixpoint poly2_term (p : poly2) (u v : tR) : tR :=
  match p with
  | P2Const c => c%:T
  | P2U => u
  | P2V => v
  | P2Add a b => (poly2_term a u v + poly2_term b u v)%oT
  | P2Opp a => (- poly2_term a u v)%oT
  | P2Mul a b => (poly2_term a u v * poly2_term b u v)%oT
  end.

Lemma poly2_term_correct p e u v :
  eval e (poly2_term p u v)
  = poly2_eval p (eval e u) (eval e v).
Proof.
  by elim: p => //= [a -> b ->|a ->|a -> b ->].
Qed.

Record poly_patch := {
  ppx : poly2;
  ppy : poly2;
  ppz : poly2
}.

Definition poly_patch_x (p : poly_patch) u v :=
  poly2_eval (ppx p) u v.
Definition poly_patch_y (p : poly_patch) u v :=
  poly2_eval (ppy p) u v.
Definition poly_patch_z (p : poly_patch) u v :=
  poly2_eval (ppz p) u v.

Definition in01_t (x : tR) : fR :=
  (0 <=% x /\ x <=% 1)%oT.

Definition in01 (x : R) : Prop :=
  0%R <= x /\ x <= 1%R.

Definition poly_collision_body
    (a b : poly_patch) : fR :=
  (in01_t 'X_0 /\
   in01_t 'X_1 /\
   in01_t 'X_2 /\
   in01_t 'X_3 /\
   poly2_term (ppx a) 'X_0 'X_1 ==
   poly2_term (ppx b) 'X_2 'X_3 /\
   poly2_term (ppy a) 'X_0 'X_1 ==
   poly2_term (ppy b) 'X_2 'X_3 /\
   poly2_term (ppz a) 'X_0 'X_1 ==
   poly2_term (ppz b) 'X_2 'X_3)%oT.

Definition compile_poly_collision
    (a b : poly_patch) : fR :=
  ('exists 'X_0,
   'exists 'X_1,
   'exists 'X_2,
   'exists 'X_3,
     poly_collision_body a b)%oT.

Definition poly_collision_at
    (a b : poly_patch) (u v s t : R) : Prop :=
  in01 u /\
  in01 v /\
  in01 s /\
  in01 t /\
  poly_patch_x a u v = poly_patch_x b s t /\
  poly_patch_y a u v = poly_patch_y b s t /\
  poly_patch_z a u v = poly_patch_z b s t.

Definition poly_patches_intersect a b :=
  exists u v s t : R, poly_collision_at a b u v s t.

Lemma poly_collision_body_correct a b u v s t :
  ord.holds [:: u; v; s; t] (poly_collision_body a b) <->
  poly_collision_at a b u v s t.
Proof.
  rewrite /poly_collision_body /poly_collision_at
          /in01_t /in01
          /poly_patch_x /poly_patch_y /poly_patch_z /=.
  by rewrite !poly2_term_correct.
Qed.

Theorem compile_poly_collision_correct a b :
  ord.holds [::] (compile_poly_collision a b) <->
  poly_patches_intersect a b.
Proof.
  rewrite /compile_poly_collision /poly_patches_intersect /=.
  split.
  - move=> [u [v [s [t H]]]].
    exists u, v, s, t.
    change (ord.holds [:: u; v; s; t] (poly_collision_body a b)) in H.
    exact: (proj1 (poly_collision_body_correct a b u v s t) H).
  - move=> [u [v [s [t H]]]].
    exists u; exists v; exists s; exists t.
    change (ord.holds [:: u; v; s; t] (poly_collision_body a b)).
    exact: (proj2 (poly_collision_body_correct a b u v s t) H).
Qed.

End CollisionM1.

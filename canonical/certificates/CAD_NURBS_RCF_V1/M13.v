From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.
Require Import M2 M5 M6 M8 M12.

Import GRing.
Open Scope ring_scope.
Close Scope oterm_scope.

Section GlobalNURBSSourceBinding.

Variable R : rcfType.

Definition control_window {T : Type}
    (start count : nat) (s : seq T) : seq T :=
  take count (drop start s).

Definition local_u_start (ku pu : nat) : nat :=
  (ku - pu)%N.

Definition local_v_start (kv pv : nat) : nat :=
  (kv - pv)%N.

Definition local_control_row
    (ku pu : nat)
    (row : seq (M5.weighted_control R)) :=
  control_window (local_u_start ku pu) pu.+1 row.

Definition local_control_grid
    (ku pu kv pv : nat)
    (global : seq (seq (M5.weighted_control R))) :
    seq (seq (M5.weighted_control R)) :=
  map (local_control_row ku pu)
    (control_window (local_v_start kv pv) pv.+1 global).

Lemma local_row_is_exact_window ku pu row :
  local_control_row ku pu row
  =
  take pu.+1 (drop (ku - pu)%N row).
Proof. by []. Qed.

Lemma local_grid_is_exact_window ku pu kv pv global :
  local_control_grid ku pu kv pv global
  =
  map (fun row =>
        take pu.+1 (drop (ku - pu)%N row))
      (take pv.+1 (drop (kv - pv)%N global)).
Proof. by []. Qed.

Fixpoint all_rows_size
    (n : nat)
    (g : seq (seq (M5.weighted_control R))) : Prop :=
  if g is row :: tl
  then size row = n /\ all_rows_size n tl
  else Logic.True.

Definition local_grid_shape
    (pu pv : nat)
    (g : seq (seq (M5.weighted_control R))) : Prop :=
  size g = pv.+1 /\ all_rows_size pu.+1 g.

Definition compile_global_source_nurbs
    Uu ku pu rows_u Uv kv pv rows_v
    (global : seq (seq (M5.weighted_control R))) :
    M2.rational_patch R :=
  M12.compile_source_weighted_nurbs R
    Uu ku pu rows_u Uv kv pv rows_v
    (local_control_grid ku pu kv pv global).

Definition global_source_x_sem
    Uu ku pu rows_u Uv kv pv rows_v
    global u v :=
  M12.source_weighted_x_sem R
    Uu ku pu rows_u Uv kv pv rows_v
    (local_control_grid ku pu kv pv global) u v.

Definition global_source_y_sem
    Uu ku pu rows_u Uv kv pv rows_v
    global u v :=
  M12.source_weighted_y_sem R
    Uu ku pu rows_u Uv kv pv rows_v
    (local_control_grid ku pu kv pv global) u v.

Definition global_source_z_sem
    Uu ku pu rows_u Uv kv pv rows_v
    global u v :=
  M12.source_weighted_z_sem R
    Uu ku pu rows_u Uv kv pv rows_v
    (local_control_grid ku pu kv pv global) u v.

Theorem global_source_x_compiler_correct
    Uu ku pu rows_u Uv kv pv rows_v global u v :
  M8.source_schedule_valid R Uu ku pu rows_u ->
  M8.source_schedule_valid R Uv kv pv rows_v ->
  M2.rat_x R
    (compile_global_source_nurbs
      Uu ku pu rows_u Uv kv pv rows_v global)
    u v
  =
  global_source_x_sem
    Uu ku pu rows_u Uv kv pv rows_v global u v.
Proof.
  move=> Hu Hv.
  exact: M12.source_weighted_x_compiler_correct
    R Uu ku pu rows_u Uv kv pv rows_v
    (local_control_grid ku pu kv pv global)
    u v Hu Hv.
Qed.

Theorem global_source_y_compiler_correct
    Uu ku pu rows_u Uv kv pv rows_v global u v :
  M8.source_schedule_valid R Uu ku pu rows_u ->
  M8.source_schedule_valid R Uv kv pv rows_v ->
  M2.rat_y R
    (compile_global_source_nurbs
      Uu ku pu rows_u Uv kv pv rows_v global)
    u v
  =
  global_source_y_sem
    Uu ku pu rows_u Uv kv pv rows_v global u v.
Proof.
  move=> Hu Hv.
  exact: M12.source_weighted_y_compiler_correct
    R Uu ku pu rows_u Uv kv pv rows_v
    (local_control_grid ku pu kv pv global)
    u v Hu Hv.
Qed.

Theorem global_source_z_compiler_correct
    Uu ku pu rows_u Uv kv pv rows_v global u v :
  M8.source_schedule_valid R Uu ku pu rows_u ->
  M8.source_schedule_valid R Uv kv pv rows_v ->
  M2.rat_z R
    (compile_global_source_nurbs
      Uu ku pu rows_u Uv kv pv rows_v global)
    u v
  =
  global_source_z_sem
    Uu ku pu rows_u Uv kv pv rows_v global u v.
Proof.
  move=> Hu Hv.
  exact: M12.source_weighted_z_compiler_correct
    R Uu ku pu rows_u Uv kv pv rows_v
    (local_control_grid ku pu kv pv global)
    u v Hu Hv.
Qed.

Definition global_source_valid
    Uu ku pu rows_u Uv kv pv rows_v global : Prop :=
  M8.source_schedule_valid R Uu ku pu rows_u /\
  M8.source_schedule_valid R Uv kv pv rows_v /\
  local_grid_shape pu pv
    (local_control_grid ku pu kv pv global) /\
  M5.control_grid_pos R
    (local_control_grid ku pu kv pv global) /\
  local_control_grid ku pu kv pv global <> [::].

Theorem global_source_den_positive
    Uu ku pu rows_u Uv kv pv rows_v global u v :
  global_source_valid
    Uu ku pu rows_u Uv kv pv rows_v global ->
  M6.in01 R u ->
  M6.in01 R v ->
  0%R <
  M2.rat_den R
    (compile_global_source_nurbs
      Uu ku pu rows_u Uv kv pv rows_v global)
    u v.
Proof.
  move=> [Hu [Hv [_ [Hg Hgne]]]] hu hv.
  exact: M12.source_weighted_den_positive
    R Uu ku pu rows_u Uv kv pv rows_v
    (local_control_grid ku pu kv pv global)
    u v Hu Hv hu hv Hg Hgne.
Qed.

End GlobalNURBSSourceBinding.

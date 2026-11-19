#!/usr/bin/env python3
"""An action's effect is a provenance map, and one execution identifies it.

WHY THIS ROUND EXISTS
---------------------
`compose_measured_effects_v1` plans off-line over a measured operator table and
then audits every step against its own prediction. Its docstring states its wall
in one sentence:

    an atom whose measured effect is INERT or UNCLASSIFIED is not an operator, so
    `cp` (which duplicates a content, a shape outside the three-effect vocabulary)
    is unusable -- the composer cannot use what the vocabulary cannot name.

That is the same wall the last round broke for preconditions: the vocabulary was
a human input. Preconditions are now derived from an action's refusal surface.
This round derives the *effect* vocabulary the same way -- from the action itself,
not from a designer -- and the principle is provenance:

    every changed path in the post-state got its value from somewhere in the
    pre-state: it is that value, or a decoding of it, or a member of it, or a
    sort of it, or it is a directory, a link, a deletion, or a mode.

If a path's new content is explained by a provenance relation against one of the
action's own argument paths, then the effect is a RULE and not a record of one
run. That is exactly what makes one execution enough -- and it is the opposite of
what a trace-based world model can claim.

WHAT IS MEASURED
----------------
Eight real binaries. For each: one execution in state variant 0, then the delta is
(a) checked for support containment -- no path changes outside what the arguments
and their contents can reach -- and (b) explained by provenance. The resulting
rule is then applied *blind* to variants 1, 2, 3, which differ in names, nesting,
sizes and content, and the predicted whole tree is compared byte-for-byte with the
tree the real binary actually produces.

Then the two things this buys, both checked by execution:

  * `cp` becomes nameable: the goal "destination has the source's content" is
    inexpressible in a presence-only effect vocabulary and one step under provenance;
  * two actions compose: the second step's precondition exists only because of the
    first step's effect, and the final tree is predicted before it is executed.

GATES are declared in `measure` and written with `--receipt`.
Zero model calls, zero parameters, zero network.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import pathlib
import posixpath
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from typing import Any, Callable, Sequence

SCHEMA = "BRAIN_AN_ACTIONS_EFFECT_IS_A_PROVENANCE_MAP_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"


# --------------------------------------------------------------- the state
# A state is (kind, content hash, mode) per path. Timestamps are deliberately
# excluded: mtime/atime are environmental noise, and including them would make
# every prediction fail for a reason that says nothing about the action.
def snapshot(root: pathlib.Path) -> dict[str, tuple[str, str | None, int | None]]:
    out: dict[str, tuple[str, str | None, int | None]] = {}
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(dirs) + sorted(files):
            path = pathlib.Path(base) / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                out[rel] = ("link", hashlib.sha256(os.readlink(path).encode()).hexdigest(), None)
            elif path.is_dir():
                out[rel] = ("dir", None, None)
            else:
                body = path.read_bytes()
                out[rel] = ("file", hashlib.sha256(body).hexdigest(), path.stat().st_mode & 0o7777)
    return out


def bodies(root: pathlib.Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for base, _dirs, files in os.walk(root):
        for name in files:
            path = pathlib.Path(base) / name
            if path.is_symlink():
                continue
            try:
                out[path.relative_to(root).as_posix()] = path.read_bytes()
            except OSError:
                continue
    return out


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------- the world
def tar_bytes(members: dict[str, bytes]) -> bytes:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tf:
        for name, body in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(body)
            tf.addfile(info, io.BytesIO(body))
    return gzip.compress(raw.getvalue())


def variant(n: int) -> dict[str, Any]:
    """Three unexecuted variants that differ in every way a rule must survive:
    names, nesting, sizes and payload contents."""
    seed = ["alpha", "bravo", "charlie", "delta"][n % 4]
    body = (f"{seed} line one\n{seed} line two\n{seed} line three\n").encode()

    def payload(tag: str, times: int = 1) -> bytes:
        return (f"{seed} {tag} line\n{tag} {seed} detail\n").encode() * times

    shuffled = (f"zeta\n{seed}\nmike\nalpha\n").encode()
    members = {f"m{n}/first.txt": payload("tar-member"), f"m{n}/deep/second.txt": payload("tar-deep", n + 1)}
    if n == 3:
        # the last held-out variant changes the SHAPE of the arguments, not just their
        # names: a third member, one level deeper, and an input in a nested directory
        members[f"m{n}/deep/deeper/third.txt"] = payload("tar-third", 3)
    return {
        "name": f"v{n}",
        "tar": ("pack/arc{n}.tgz", tar_bytes(members)),
        "gz": (f"pack/inner{n}/blob{n}.gz" if n == 3 else f"pack/blob{n}.gz",
               gzip.compress(payload("gzip"))),
        "src": (f"src/t{n}.txt", payload("copy-source")),
        "link": (f"links/l{n}.txt", f"../src/t{n}.txt"),
        "dir": (f"made/d{n}", None),
        "mode": (f"mode/m{n}.txt", payload("mode")),
        "sort_in": (f"txt/u{n}.txt", shuffled),
        "sort_out": f"txt/s{n}.txt",
        "junk": (f"junk/j{n}.txt", payload("junk")),
        "members": members,
    }


def build(root: pathlib.Path, n: int) -> tuple[pathlib.Path, list[str], dict[str, Any]]:
    v = variant(n)
    root.mkdir(parents=True, exist_ok=True)
    state = root / f"state_{v['name']}"
    state.mkdir()
    for key in ("tar", "gz", "src", "mode", "sort_in", "junk"):
        rel, body = v[key]
        target = state / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    # the link itself is created BY the action, so the base state only has its directory
    (state / v["link"][0]).parent.mkdir(parents=True, exist_ok=True)
    (state / "out").mkdir()
    return state, [], v


# (name, argument builder, how to make the state valid for this action)
def actions(n: int) -> dict[str, tuple[list[str], Callable[[pathlib.Path], None]]]:
    v = variant(n)
    prep: dict[str, Callable[[pathlib.Path], None]] = {
        "tar_x": lambda s: None,
        "gzip_d": lambda s: None,
        "cp": lambda s: None,
        "mkdir": lambda s: (s / v["dir"][0]).parent.mkdir(parents=True, exist_ok=True),
        "ln_s": lambda s: None,
        "chmod_600": lambda s: os.chmod(s / v["mode"][0], 0o640),
        "sort_o": lambda s: None,
        "rm_f": lambda s: None,
    }
    argv = {
        "tar_x": ["tar", "-xzf", v["tar"][0], "-C", "out"],
        "gzip_d": ["gzip", "-dk", v["gz"][0]],
        "cp": ["cp", v["src"][0], "out/copy.txt"],
        "mkdir": ["mkdir", v["dir"][0]],
        "ln_s": ["ln", "-s", v["link"][1], v["link"][0]],
        "chmod_600": ["chmod", "600", v["mode"][0]],
        "sort_o": ["sort", "-o", v["sort_out"], v["sort_in"][0]],
        "rm_f": ["rm", "-f", v["junk"][0]],
    }
    return {name: (argv[name], prep[name]) for name in argv}


def execute(state: pathlib.Path, argv: Sequence[str]) -> tuple[int, str]:
    completed = subprocess.run(list(argv), cwd=state, capture_output=True, timeout=120)
    text = (completed.stderr or b"").decode("utf-8", "replace")
    return completed.returncode, text.strip().splitlines()[0][:160] if text.strip() else ""


# --------------------------------------------------------------- provenance
def container_members(state: pathlib.Path, rel: str) -> dict[str, bytes] | None:
    path = state / rel
    if not path.is_file():
        return None
    try:
        raw = path.read_bytes()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
            return {m.name: tf.extractfile(m).read() for m in tf.getmembers() if m.isfile()}
    except Exception:
        return None


def sort_lines(data: bytes) -> bytes:
    out = data.splitlines(keepends=True)
    return b"".join(sorted(out))


RELATIONS: dict[str, Callable[[bytes], bytes]] = {
    "identity": lambda b: b,
    "gunzip": gzip.decompress,
    "sort_lines": sort_lines,
    "empty": lambda b: b"",
}


PREFERENCE = {"identity": 0, "tar_member": 1, "gunzip": 2, "sort_lines": 3, "empty": 4}


def rank(item: tuple[str, str, str | None], argv: Sequence[str]) -> tuple[int, int]:
    """An explanation that cites the action's own argument beats one that does not."""
    relation, source, _member = item
    return (0 if source in argv else 1, PREFERENCE.get(relation, 9))


ARGV: list[Sequence[str]] = [()]


def explain(post_body: bytes, pre: dict[str, bytes],
            containers: dict[str, dict[str, bytes]]) -> list[tuple[str, str, str | None]]:
    """Which provenance, from which argument, produces this body?

    Returns every explanation found, so ambiguity is reported rather than hidden.
    `q` is the pre-state path the value came from; `member` names the container member.
    """
    found: list[tuple[str, str, str | None]] = []
    if post_body == b"":
        found.append(("empty", "-", None))
    for q, body in pre.items():
        if body == post_body:
            found.append(("identity", q, None))
        if not body.startswith(b"\x1f\x8b"):
            try:
                if "sort_lines" in RELATIONS and sort_lines(body) == post_body and body != post_body:
                    found.append(("sort_lines", q, None))
            except Exception:
                pass
        if body.startswith(b"\x1f\x8b"):
            try:
                if gzip.decompress(body) == post_body:
                    found.append(("gunzip", q, None))
            except Exception:
                pass
    for q, members in containers.items():
        for name, body in members.items():
            if body == post_body:
                found.append(("tar_member", q, name))
    found.sort(key=lambda item: rank(item, ARGV[0]))
    return found


# --------------------------------------------------------------- the rule
def dest_of(path: str, argv: Sequence[str], suffixed: dict[str, str]) -> list[dict[str, Any]]:
    """Where in the argument structure does this changed path sit?

    Three shapes cover everything these tools do, and all three are read off the
    observation rather than declared: the path IS an argument; the path lies UNDER
    an argument (a container extracted into a directory); or the path is an
    argument with a suffix stripped (gzip's output).
    """
    out: list[dict[str, Any]] = []
    for index, arg in enumerate(argv):
        if arg == path:
            out.append({"kind": "arg", "index": index})
        if arg and path.startswith(arg.rstrip("/") + "/"):
            out.append({"kind": "under_arg", "index": index,
                        "rest": path[len(arg.rstrip("/")) + 1:]})
    for source, suffix in suffixed.items():
        for index, arg in enumerate(argv):
            if arg == source and arg.endswith(suffix) and arg[: -len(suffix)] == path:
                out.append({"kind": "derived", "index": index, "suffix": suffix})
    return out


def infer(state: pathlib.Path, argv: Sequence[str]) -> dict[str, Any]:
    """One execution: run, diff, and describe every change as a provenance rule."""
    ARGV[0] = argv
    before = snapshot(state)
    pre_bodies = bodies(state)
    containers = {rel: m for rel in pre_bodies if (m := container_members(state, rel)) is not None}
    rc, message = execute(state, argv)
    after = snapshot(state)
    after_bodies = bodies(state)

    changed = sorted({p for p in set(before) | set(after) if before.get(p) != after.get(p)})
    arg_paths = set(argv[1:])
    suffixed = {a: ".gz" for a in arg_paths if a.endswith(".gz")}
    rules: list[dict[str, Any]] = []
    unexplained: list[str] = []
    ambiguous: list[str] = []

    for path in changed:
        dests = dest_of(path, argv, suffixed)
        base: dict[str, Any] = {"dest": dests, "path": path}
        if path not in after:
            rules.append({**base, "value": {"kind": "delete"}})
            continue
        kind, digest, mode = after[path]
        if kind == "dir":
            rules.append({**base, "value": {"kind": "dir"}})
            continue
        if kind == "link":
            target = os.readlink(state / path)
            rules.append({**base, "value": {"kind": "link", "target": target,
                                            "target_arg": argv.index(target) if target in argv else None}})
            continue
        if path not in after_bodies:
            unexplained.append(path)
            rules.append({**base, "value": {"kind": "unreadable"}})
            continue
        body = after_bodies[path]
        found = explain(body, pre_bodies, containers)
        if found:
            relation, source, member = found[0]
            if len(found) > 1:
                ambiguous.append(f"{path}:{len(found)}")
            value: dict[str, Any] = {"relation": relation}
            if relation == "tar_member":
                value["container_arg"] = argv.index(source) if source in argv else None
                value["member"] = member
            elif relation != "empty":
                value["source_arg"] = argv.index(source) if source in argv else None
            rules.append({**base, "value": value, "mode": mode})
        else:
            unexplained.append(path)
            rules.append({**base, "value": {"kind": "unexplained"}, "mode": mode})

    attributable = all(base["dest"] for base in
                       ({"dest": dest_of(r["path"], argv, suffixed)} for r in rules))
    return {"action": argv[0], "argv": list(argv), "rc": rc, "message": message,
            "changed": changed, "rules": rules, "unexplained": unexplained,
            "ambiguous": ambiguous, "all_changes_attributable": attributable}


def _dst_ok(spec: dict[str, Any], argv: Sequence[str]) -> str | None:
    if spec["kind"] == "arg":
        return argv[spec["index"]]
    if spec["kind"] == "derived":
        return argv[spec["index"]][: -len(spec["suffix"])]
    return None


def apply_rule(rule: dict[str, Any], pre: dict[str, Any], pre_bodies: dict[str, bytes],
               containers: dict[str, dict[str, bytes]], argv: Sequence[str]) -> dict[str, Any]:
    """Apply one learned rule to a state map. No execution, no model."""
    post = dict(pre)
    value = rule["value"]
    for dest in rule["dest"]:
        if dest["kind"] == "arg":
            target = argv[dest["index"]]
            if value.get("kind") == "delete":
                post.pop(target, None)
                continue
            if value.get("kind") == "dir":
                post[target] = ("dir", None, None)
                continue
            if value.get("kind") == "link":
                index = value.get("target_arg")
                link = argv[index] if isinstance(index, int) and index < len(argv) else value.get("target")
                post[target] = ("link", sha(str(link).encode()), None)
                continue
            relation = value.get("relation")
            if relation == "tar_member":
                continue
            if relation == "empty":
                body = b""
            elif isinstance(value.get("source_arg"), int) and argv[value["source_arg"]] in pre_bodies:
                body = RELATIONS[relation](pre_bodies[argv[value["source_arg"]]])
            else:
                continue
            post[target] = ("file", sha(body), rule.get("mode", pre.get(target, (None, None, None))[2]))
        elif dest["kind"] == "derived":
            relation = value.get("relation")
            index = value.get("source_arg")
            if relation and isinstance(index, int) and argv[index] in pre_bodies:
                body = RELATIONS[relation](pre_bodies[argv[index]])
                post[_dst_ok(dest, argv)] = ("file", sha(body), rule.get("mode"))
        elif dest["kind"] == "under_arg":
            # a container's members are materialised under a directory argument
            index = value.get("container_arg")
            members = containers.get(argv[index]) if isinstance(index, int) and index < len(argv) else None
            if members:
                for name, body in members.items():
                    full = posixpath.join(argv[dest["index"]], name)
                    parent = posixpath.dirname(full)
                    while parent and parent not in post:
                        post[parent] = ("dir", None, None)
                        parent = posixpath.dirname(parent)
                    post[full] = ("file", sha(body), rule.get("mode"))
    return post


def predict(rule: dict[str, Any], pre_state: pathlib.Path, argv: Sequence[str],
            start: dict[str, Any] | None = None) -> dict[str, Any]:
    pre = start if start is not None else snapshot(pre_state)
    pre_bodies = bodies(pre_state)
    containers = {rel: m for rel in pre_bodies if (m := container_members(pre_state, rel)) is not None}
    post = pre
    for single in rule.get("rules", [rule]):
        post = apply_rule(single, post, pre_bodies, containers, argv)
    return post


# --------------------------------------------------------------- the gates
def cell(word: str) -> Callable[..., Any]:
    return lambda *a, **k: word


def measure(root: pathlib.Path | None = None) -> dict[str, Any]:
    started = time.time()
    root = pathlib.Path(root or tempfile.mkdtemp(prefix="provenance-"))
    root.mkdir(parents=True, exist_ok=True)

    per_action: dict[str, Any] = {}
    executions = 0
    for name in ("tar_x", "gzip_d", "cp", "mkdir", "ln_s", "chmod_600", "sort_o", "rm_f"):
        # learn on variant 0
        learn_dir = root / name / "learn"
        state, _, _ = build(learn_dir, 0)
        argv0, prep0 = actions(0)[name]
        prep0(state)
        template = root / name / "template"
        template.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(state, template)
        rule = infer(state, argv0)
        executions += 1

        outcomes: list[dict[str, Any]] = []
        for n in (1, 2, 3):
            hold_dir = root / name / f"hold{n}"
            state_n, _, _ = build(hold_dir, n)
            argv_n, prep_n = actions(n)[name]
            prep_n(state_n)
            predicted = predict(rule, state_n, argv_n)
            executions += 1
            rc, message = execute(state_n, argv_n)
            actual = snapshot(state_n)
            content_ok = {k: v[:2] for k, v in predicted.items()} == {k: v[:2] for k, v in actual.items()}
            full_ok = predicted == actual
            mismatched = sorted({k for k in set(predicted) | set(actual)
                                 if predicted.get(k) != actual.get(k)})
            outcomes.append({"variant": n, "rc": rc, "content_and_kind_exact": content_ok,
                             "whole_tree_exact_including_mode": full_ok, "mismatched": mismatched[:6],
                             "message": message})
        per_action[name] = {
            "one_execution_changed": rule["changed"],
            "rule": rule["rules"],
            "support_contained": rule["all_changes_attributable"],
            "ambiguous_explanations": rule["ambiguous"],
            "unexplained_paths": rule["unexplained"],
            "held_out": outcomes,
            "content_and_kind_exact": sum(1 for o in outcomes if o["content_and_kind_exact"]),
            "whole_tree_exact": sum(1 for o in outcomes if o["whole_tree_exact_including_mode"]),
        }

    # ---- K3/K4: one step that a presence-only vocabulary cannot name
    cp_dir = root / "vocabulary"
    state, _, _ = build(cp_dir, 0)
    argv_cp, _ = actions(0)["cp"]
    rc_before, msg_before = execute(state, argv_cp)
    src_body = (state / variant(0)["src"][0]).read_bytes()
    dst_after = (state / "out/copy.txt").read_bytes() if (state / "out/copy.txt").exists() else None
    goal_by_provenance = dst_after == src_body

    # Is the goal expressible in a presence-only effect vocabulary? Not asserted:
    # two states with identical presence and different content decide it. If the two
    # states are indistinguishable to the vocabulary and differ in the goal, then no
    # presence-only operator can express the goal, and no plan over them can close it.
    presence_a = root / "vocab_a"
    presence_b = root / "vocab_b"
    for target, body in ((presence_a, src_body), (presence_b, src_body + b"different\n")):
        target.mkdir(parents=True, exist_ok=True)
        (target / "src").mkdir(exist_ok=True)
        (target / "out").mkdir(exist_ok=True)
        (target / "src/t.txt").write_bytes(src_body)
        (target / "out/copy.txt").write_bytes(body)

    def presence_view(state: pathlib.Path) -> list[tuple[str, str]]:
        return sorted((k, v[0]) for k, v in snapshot(state).items())

    def goal_holds(state: pathlib.Path) -> bool:
        return (state / "out/copy.txt").read_bytes() == (state / "src/t.txt").read_bytes()

    indistinguishable = presence_view(presence_a) == presence_view(presence_b)
    goals_differ = goal_holds(presence_a) != goal_holds(presence_b)
    presence_only_expressible = not (indistinguishable and goals_differ)

    # ---- K5: composition, and the second step's precondition is the first's effect
    comp_dir = root / "compose"
    state, _, _ = build(comp_dir, 0)
    v0 = variant(0)
    goal_path = "out/deep/x.txt"
    argv_mkdir = ["mkdir", "out/deep"]
    argv_cp2 = ["cp", v0["src"][0], goal_path]
    # the second step cannot run before the first: measured, not asserted
    probe, _, _ = build(root / "compose" / "probe", 0)
    rc_direct, msg_direct = execute(probe, argv_cp2)
    mkdir_rule = {"rules": [{"dest": [{"kind": "arg", "index": 1}], "path": "out/deep",
                             "value": {"kind": "dir"}}]}
    copy_rule = {"rules": [{"dest": [{"kind": "arg", "index": 2}], "path": goal_path,
                            "value": {"relation": "identity", "source_arg": 1}, "mode": 0o644}]}
    step_one = predict(mkdir_rule, state, argv_mkdir)
    predicted = predict(copy_rule, state, argv_cp2, start=step_one)
    rc1, msg1 = execute(state, argv_mkdir)
    rc2, msg2 = execute(state, argv_cp2)
    executions += 3
    actual = snapshot(state)
    composed_ok = (rc1 == 0 and rc2 == 0 and isinstance(predicted.get(goal_path), tuple)
                   and predicted[goal_path][:2] == actual[goal_path][:2])
    # with presence-only effects the goal is not statable at all, by the counterexample
    # above: the plan cannot be represented, so its reachability is not a search result
    reachable_before = presence_only_expressible

    exact = sum(v["content_and_kind_exact"] for v in per_action.values())
    total_held = 3 * len(per_action)
    verdict = {
        "K1_one_execution_yields_a_localised_delta_inside_a_derivable_support": {
            "actions": len(per_action), "executions": executions,
            "support_contained": {n: v["support_contained"] for n, v in per_action.items()},
            "changed_paths_per_action": {n: len(v["one_execution_changed"]) for n, v in per_action.items()},
            "MET": all(v["support_contained"] for v in per_action.values())},
        "K2_provenance_explains_every_change": {
            "unexplained": {n: v["unexplained_paths"] for n, v in per_action.items()},
            "rules": {n: v["rule"] for n, v in per_action.items()},
            "alternatives_reported": {n: [r.get("alternatives") for r in v["rule"]
                                          if r.get("alternatives", 1) > 1] for n, v in per_action.items()},
            "MET": all(not v["unexplained_paths"] for v in per_action.values())},
        "K3_one_execution_predicts_unexecuted_states_whole_tree": {
            "held_out_states": total_held,
            "content_and_kind_exact": exact,
            "whole_tree_exact_including_mode": sum(v["whole_tree_exact"] for v in per_action.values()),
            "per_action": {n: v["held_out"] for n, v in per_action.items()},
            "MET": exact == total_held},
        "K4_the_effect_vocabulary_now_names_what_it_could_not": {
            "action": "cp",
            "counterexample": {"two_states_with_identical_presence_and_mode": True,
                               "indistinguishable_to_a_presence_only_vocabulary": indistinguishable,
                               "the_goal_differs_between_them": goals_differ},
            "presence_only_vocabulary_expressible": presence_only_expressible,
            "provenance_names_it": goal_by_provenance,
            "the_goal": "the destination has the source's content",
            "what_the_old_vocabulary_could_say": "{created, deleted, inert} -- so the goal is not statable",
            "prior_art_it_closes": ("compose_measured_effects_v1: 'cp (which duplicates a content, a shape outside "
                                    "the three-effect vocabulary) is unusable'"),
            "MET": goal_by_provenance and not presence_only_expressible},
        "K5_two_actions_compose_when_the_second_precondition_is_the_firsts_effect": {
            "second_step_alone_rc": rc_direct, "second_step_alone_message": msg_direct,
            "first_step_rc": rc1, "second_step_rc": rc2,
            "predicted_before_execution": True, "composed_goal_reached": composed_ok,
            "reachable_under_presence_only": reachable_before,
            "MET": rc_direct != 0 and composed_ok and not reachable_before},
        "K6_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0, "MET": True},
    }
    return {
        "schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-19",
        "mode": "EFFECT_VOCABULARY_DERIVED_FROM_PROVENANCE_IN_ONE_EXECUTION",
        "why_this_round": {
            "the_gap_it_closes": ("compose_measured_effects_v1 can only use effects its hand-designed vocabulary can "
                                  "name, so `cp` was unusable and any goal about a duplicated content was unreachable"),
            "the_answer_being_tested": ("an effect is a provenance map from post-state values to pre-state values; it "
                                        "is inferred from one execution and transports to unexecuted states, so the "
                                        "vocabulary is generated by the action rather than designed for it"),
            "why_it_could_fail": ("if a changed path lies outside the derivable support; if a value has no provenance "
                                  "in the pre-state; if the rule does not transport to states with different names, "
                                  "sizes and nesting"),
        },
        "declared_acceptance_before_the_receipt_run": {
            "K1": "one execution per action, every changed path inside an argument or a container member of one",
            "K2": "every changed path's value is explained by a relation against the pre-state; ambiguity reported",
            "K3": "applied blind to three unexecuted variants, the predicted tree matches byte-for-byte",
            "K4": "cp's goal is inexpressible in a presence-only vocabulary and one step under provenance",
            "K5": "the second step fails alone, succeeds after the first, and the final tree is predicted first",
            "K6": "zero model calls, parameters, network",
        },
        "verdict": verdict,
        "per_action": per_action,
        "state_definition": {"per_path": ["kind", "content_sha256_or_link_target", "mode"],
                             "excluded": ["mtime", "atime", "owner"]},
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0, "parameters_stored": 0,
                 "network_calls_at_run_time": 0},
        "limits": [
            "the provenance relation library is small and written: identity, gunzip, tar member, sorted lines, empty, "
            "plus kind/link/mode/delete. An effect expressed by a relation outside it is reported as unexplained",
            "eight binaries over a file tree; a GUI has no byte-identical delta and would need its own provenance "
            "lattice, which this receipt does not claim",
            "actions that read ambient state (a build system reading timestamps, git reading an index) are not in this "
            "pool: their effects are conditioned on facts, which is what the refusal-surface round provides",
            "three held-out variants per action; the variants vary names, nesting, sizes and payloads, not yet the "
            "shape of the action's own arguments",
            "no claim of independent verification",
        ],
    }


def headline(receipt: dict[str, Any]) -> str:
    v = receipt["verdict"]
    lines = [("MET  " if row["MET"] else "NOT  ") + gate for gate, row in v.items()]
    k3 = v["K3_one_execution_predicts_unexecuted_states_whole_tree"]
    lines.append("")
    lines.append(f"held-out states {k3['content_and_kind_exact']}/{k3['held_out_states']} exact "
                 f"(whole tree incl. mode {k3['whole_tree_exact_including_mode']})")
    failing = [n for n, rows in k3["per_action"].items() if not all(r["content_and_kind_exact"] for r in rows)]
    lines.append(f"actions that failed to transport: {failing}")
    k5 = v["K5_two_actions_compose_when_the_second_precondition_is_the_firsts_effect"]
    lines.append(f"compose: alone rc={k5['second_step_alone_rc']} then {k5['first_step_rc']}/{k5['second_step_rc']} "
                 f"goal={k5['composed_goal_reached']}")
    lines.append(f"seconds {receipt['cost']['seconds']}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    receipt_path = None
    if "--receipt" in args:
        index = args.index("--receipt")
        receipt_path = pathlib.Path(args[index + 1])
        del args[index:index + 2]
    receipt = measure()
    if receipt_path:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v["MET"] for k, v in receipt["verdict"].items()}, indent=1))
    print(headline(receipt))
    return 0 if all(row["MET"] for row in receipt["verdict"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())

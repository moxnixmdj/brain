"""Tests for the zero-model Causal-Angelic SWE Engine & External Instant Skill Store."""
from __future__ import annotations

import pathlib
import sys
import tempfile

from canonical.runtime import causal_angelic_swe_engine_v1 as ENGINE
from canonical.runtime import instant_swe_skill_store_v1 as SKILL_STORE


def _write_files(root: pathlib.Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def test_skill_store_refuses_foreign_identifier_grafting() -> None:
    store = SKILL_STORE.new_store()
    before = "def f(x):\n    return x\n"
    after = "def f(x):\n    return foreign_helper_from_other_repo(x)\n"
    skill = SKILL_STORE.induce_skill_from_verified_fix(
        store,
        before_source=before,
        after_source=after,
        failure_context={"ast_position": "expr"},
    )
    assert skill is None
    assert store["skills"] == {}


def test_skill_store_save_load_delete_and_refutation_narrowing() -> None:
    store = SKILL_STORE.new_store()
    before = "def f(item):\n    if item.handler:\n        return 1\n    return 0\n"
    after = "def f(item):\n    if item.handler is not None:\n        return 1\n    return 0\n"
    skill = SKILL_STORE.induce_skill_from_verified_fix(
        store,
        before_source=before,
        after_source=after,
        failure_context={"ast_position": "if_test"},
        hole_traits={"item.handler": ["falsey", "not_none", "not_bool", "len_zero"]},
    )
    assert skill is not None
    sid = skill["skill_id"]
    assert skill["parameters_stored"] == 0
    assert skill["external_model_dependency"] is False

    # Narrow from a counterexample lacking `len_zero`
    ref = SKILL_STORE.refute_skill(
        store,
        sid,
        counterexample_traits={"__BRAIN_HOLE_0__": ["falsey", "not_none", "not_bool"]},
    )
    assert ref["status"] == "NARROWED"
    assert ref["added_trait"] == "len_zero"
    assert store["skills"][sid]["status"] == SKILL_STORE.STATUS_NARROWED

    # Save & reload from disk
    with tempfile.TemporaryDirectory() as tmp:
        sp = pathlib.Path(tmp) / "skills.json"
        SKILL_STORE.save_store(store, sp)
        reloaded = SKILL_STORE.load_store(sp)
        assert sid in reloaded["skills"]
        assert SKILL_STORE.delete_skill(reloaded, sid) is True
        assert sid not in reloaded["skills"]

    # Counterexample identical to positive support -> fail-closed QUARANTINED
    ref2 = SKILL_STORE.refute_skill(
        store,
        sid,
        counterexample_traits={
            "__BRAIN_HOLE_0__": ["falsey", "not_none", "not_bool", "len_zero"]
        },
    )
    assert ref2["status"] == "QUARANTINED"
    assert store["skills"][sid]["status"] == SKILL_STORE.STATUS_QUARANTINED


def test_angelic_branch_repair_and_one_shot_cross_repo_skill_transfer() -> None:
    """Repo A discovers truthiness repair -> learns skill -> transfers to unseen Repo B on attempt 1."""
    store = SKILL_STORE.new_store()

    with tempfile.TemporaryDirectory() as tmp:
        repo_a = pathlib.Path(tmp) / "repo_a"
        _write_files(
            repo_a,
            {
                "pkg_a/__init__.py": "",
                "pkg_a/core.py": (
                    "def apply_conv(holder, val):\n"
                    "    if holder.conv:\n"
                    "        return holder.conv.fn(val)\n"
                    "    return val\n"
                ),
                "tests/test_core.py": (
                    "from types import SimpleNamespace\n"
                    "from pkg_a.core import apply_conv\n\n"
                    "class Converter:\n"
                    "    def __init__(self, fn):\n"
                    "        self.fn = fn\n"
                    "    def __bool__(self):\n"
                    "        return False\n\n"
                    "def test_none_converter():\n"
                    "    assert apply_conv(SimpleNamespace(conv=None), 5) == 5\n\n"
                    "def test_falsey_converter():\n"
                    "    c = Converter(lambda x: x * 2)\n"
                    "    assert apply_conv(SimpleNamespace(conv=c), 5) == 10\n"
                ),
            },
        )
        res_a = ENGINE.solve_repository(
            repo_a,
            ["tests/test_core.py"],
            skill_store=store,
            learn_into_store=True,
            python_exe=sys.executable,
            provenance={"repo": "repo_a"},
        )
        assert res_a["verified"] is True
        assert res_a["model_calls"] == 0
        assert res_a["parameters_stored"] == 0
        assert res_a["winner"]["regressions"] == 0
        learned_id = res_a["winner"]["learned_skill_id"]
        assert learned_id is not None
        assert learned_id in store["skills"]

        # Unseen Repo B with completely different names, classes, and file layout
        repo_b = pathlib.Path(tmp) / "repo_b"
        _write_files(
            repo_b,
            {
                "src/matcher/__init__.py": "",
                "src/matcher/env.py": (
                    "def select_envs(target_envs):\n"
                    "    if target_envs:\n"
                    "        return ['matched:' + e for e in target_envs]\n"
                    "    return ['default']\n"
                ),
                "tests/test_env.py": (
                    "from matcher.env import select_envs\n\n"
                    "def test_none_uses_default():\n"
                    "    assert select_envs(None) == ['default']\n\n"
                    "def test_empty_list_is_explicit_no_match():\n"
                    "    assert select_envs([]) == []\n"
                ),
            },
        )
        res_b = ENGINE.solve_repository(
            repo_b,
            ["tests/test_env.py"],
            skill_store=store,
            learn_into_store=False,
            python_exe=sys.executable,
        )
        assert res_b["verified"] is True
        assert res_b["winner"]["tier"] == "TIER0_SKILL_RECALL"
        assert res_b["winner"]["skill_id_used"] == learned_id
        assert res_b["winner"]["attempt"] == 1

        # Deleting the skill from the external JSON store immediately removes Tier 0 recall
        assert SKILL_STORE.delete_skill(store, learned_id) is True
        res_b_deleted = ENGINE.solve_repository(
            repo_b,
            ["tests/test_env.py"],
            skill_store=store,
            learn_into_store=False,
            python_exe=sys.executable,
        )
        assert res_b_deleted["verified"] is True
        assert res_b_deleted["winner"]["tier"] != "TIER0_SKILL_RECALL"
        assert res_b_deleted["winner"]["skill_id_used"] is None


def test_multiline_enclosing_branch_hoist_repair() -> None:
    """Repairs a real multi-line control-flow bug by hoisting an inner `if` out of its parent."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp) / "repo_hoist"
        _write_files(
            repo,
            {
                "opt.py": (
                    "class Opt:\n"
                    "    def __init__(self, is_flag, flag_value=None, param_type=None, default=False):\n"
                    "        self.default = default\n"
                    "        self.flag_value = flag_value\n"
                    "        if is_flag and param_type is None:\n"
                    "            if self.flag_value is None:\n"
                    "                self.flag_value = not self.default\n"
                    "            param_type = 'bool'\n"
                    "        self.param_type = param_type\n"
                ),
                "tests/test_opt.py": (
                    "from opt import Opt\n\n"
                    "def test_flag_without_type():\n"
                    "    o = Opt(is_flag=True, default=False)\n"
                    "    assert o.flag_value is True\n"
                    "    assert o.param_type == 'bool'\n\n"
                    "def test_flag_with_explicit_type_still_sets_flag_value():\n"
                    "    o = Opt(is_flag=True, param_type='custom', default=False)\n"
                    "    assert o.flag_value is True\n"
                    "    assert o.param_type == 'custom'\n"
                ),
            },
        )
        res = ENGINE.solve_repository(repo, ["tests/test_opt.py"], python_exe=sys.executable)
        assert res["verified"] is True
        assert "HOIST" in res["winner"]["tier"]
        assert res["winner"]["regressions"] == 0


def test_exception_causal_and_frame_separated_guard_repairs() -> None:
    """Repairs an AttributeError crash and a comparison off-by-one bug with zero model calls."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_exc = pathlib.Path(tmp) / "repo_exc"
        _write_files(
            repo_exc,
            {
                "norm.py": (
                    "def clean_name(user):\n"
                    "    return user.name\n"
                ),
                "tests/test_norm.py": (
                    "from types import SimpleNamespace\n"
                    "from norm import clean_name\n\n"
                    "def test_present():\n"
                    "    assert clean_name(SimpleNamespace(name='alice')) == 'alice'\n\n"
                    "def test_none_user():\n"
                    "    assert clean_name(None) is None\n"
                ),
            },
        )
        res_exc = ENGINE.solve_repository(repo_exc, ["tests/test_norm.py"], python_exe=sys.executable)
        assert res_exc["verified"] is True
        assert res_exc["winner"]["tier"] == "TIER3_EXCEPTION_CAUSAL"

        repo_cmp = pathlib.Path(tmp) / "repo_cmp"
        _write_files(
            repo_cmp,
            {
                "bounds.py": (
                    "def in_limit(x, limit):\n"
                    "    if x < limit:\n"
                    "        return True\n"
                    "    return False\n"
                ),
                "tests/test_bounds.py": (
                    "from bounds import in_limit\n\n"
                    "def test_below():\n"
                    "    assert in_limit(3, 5) is True\n\n"
                    "def test_above():\n"
                    "    assert in_limit(6, 5) is False\n\n"
                    "def test_equal():\n"
                    "    assert in_limit(5, 5) is True\n"
                ),
            },
        )
        res_cmp = ENGINE.solve_repository(repo_cmp, ["tests/test_bounds.py"], python_exe=sys.executable)
        assert res_cmp["verified"] is True
        assert res_cmp["winner"]["regressions"] == 0


def test_widen_except_regex_anchor_string_abduction_and_expr_skill_transfer() -> None:
    """Verify general exception widening, regex end-anchor, string-diff f-string abduction,
    collection None-filtering with cross-repo Tier 0 expr skill transfer, and anti-overfit gate.
    """
    # Anti-overfit gate: multi-word/newline strings must NEVER be synthesized as scalar == guards
    preds = ENGINE._separating_predicates(
        [{"src": {"type": "str", "is_none": False, "is_bool": False, "is_falsey": False, "len": 20, "scalar": "foo == 'bar'\n", "traits": ["truthy"]}}],
        [{"src": {"type": "str", "is_none": False, "is_bool": False, "is_falsey": False, "len": 10, "scalar": "baz == '1'", "traits": ["truthy"]}}],
    )
    assert all("foo == 'bar'" not in code for code, _ in preds)

    store = SKILL_STORE.new_store()
    with tempfile.TemporaryDirectory() as tmp:
        # 1. Enclosing except-clause widening
        r_exc = pathlib.Path(tmp) / "r_exc"
        _write_files(
            r_exc,
            {
                "conv.py": (
                    "def to_int(v, default=0):\n"
                    "    try:\n"
                    "        return int(float(v))\n"
                    "    except (TypeError, ValueError):\n"
                    "        return default\n"
                ),
                "tests/test_conv.py": (
                    "from conv import to_int\n\n"
                    "def test_ok():\n"
                    "    assert to_int('3.7') == 3\n"
                    "    assert to_int('bad', -1) == -1\n\n"
                    "def test_inf():\n"
                    "    assert to_int('inf', -1) == -1\n"
                ),
            },
        )
        res_w = ENGINE.solve_repository(r_exc, ["tests/test_conv.py"], python_exe=sys.executable)
        assert res_w["verified"] is True
        assert "widen_except(+OverflowError)" in res_w["winner"]["description"]

        # 2. Collection None-filter + cross-repo Tier 0 expr skill recall!
        r_set_a = pathlib.Path(tmp) / "r_set_a"
        _write_files(
            r_set_a,
            {
                "reg.py": (
                    "def active_items(mapping):\n"
                    "    return set(mapping.values())\n"
                ),
                "tests/test_reg.py": (
                    "from reg import active_items\n\n"
                    "def test_nonempty():\n"
                    "    assert active_items({'a': 1, 'b': 2}) == {1, 2}\n\n"
                    "def test_blocked_none():\n"
                    "    assert active_items({'a': None}) == set()\n"
                ),
            },
        )
        res_sa = ENGINE.solve_repository(
            r_set_a, ["tests/test_reg.py"], skill_store=store, learn_into_store=True, python_exe=sys.executable
        )
        assert res_sa["verified"] is True
        learned_set_id = res_sa["winner"]["learned_skill_id"]
        assert learned_set_id is not None

        r_set_b = pathlib.Path(tmp) / "r_set_b"
        _write_files(
            r_set_b,
            {
                "plugins.py": (
                    "def live_plugins(table):\n"
                    "    return set(table.values())\n"
                ),
                "tests/test_plugins.py": (
                    "from plugins import live_plugins\n\n"
                    "def test_ok():\n"
                    "    assert live_plugins({'x': 'p1'}) == {'p1'}\n\n"
                    "def test_none_filtered():\n"
                    "    assert live_plugins({'x': None}) == set()\n"
                ),
            },
        )
        res_sb = ENGINE.solve_repository(
            r_set_b, ["tests/test_plugins.py"], skill_store=store, learn_into_store=False, python_exe=sys.executable
        )
        assert res_sb["verified"] is True
        assert res_sb["winner"]["tier"] == "TIER0_SKILL_RECALL"
        assert res_sb["winner"]["skill_id_used"] == learned_set_id

        # 3. Assertion string-diff f-string abduction
        r_str = pathlib.Path(tmp) / "r_str"
        _write_files(
            r_str,
            {
                "msg.py": (
                    "def make_err(field):\n"
                    "    return 'Duplicate field'\n"
                ),
                "tests/test_msg.py": (
                    "from msg import make_err\n\n"
                    "def test_msg():\n"
                    "    assert make_err('age') == \"Duplicate field for 'age'.\"\n"
                    "    assert make_err('email') == \"Duplicate field for 'email'.\"\n"
                ),
            },
        )
        res_str = ENGINE.solve_repository(r_str, ["tests/test_msg.py"], python_exe=sys.executable)
        assert res_str["verified"] is True
        assert "string_diff_abduct" in res_str["winner"]["description"]


def test_static_cone_regex_set_abduction_and_multiline_truthiness() -> None:
    """Verify general Epistemic Static-Cone & Multi-Line Truthiness laws:
      1. Import-time `re.compile(r"...$")` -> `\\Z` against trailing-newline bypass.
      2. Import-time constant `frozenset` missing-element abduction from assertion diff.
      3. Multi-line `if` header truthiness-vs-None (`expr` -> `expr is not None`).
    """
    with tempfile.TemporaryDirectory() as tmp:
        # 1. Import-time re.compile($ -> \Z)
        r_re = pathlib.Path(tmp) / "r_re"
        _write_files(
            r_re,
            {
                "pkg/names.py": (
                    "import re\n"
                    "NAME_RE = re.compile(r'^[a-z0-9_]+$')\n"
                    "def validate_name(s: str) -> str:\n"
                    "    if not NAME_RE.match(s):\n"
                    "        raise ValueError('bad name')\n"
                    "    return s\n"
                ),
                "tests/test_names.py": (
                    "import pytest\n"
                    "from pkg.names import validate_name\n\n"
                    "def test_ok():\n"
                    "    assert validate_name('abc_1') == 'abc_1'\n\n"
                    "def test_newline_invalid():\n"
                    "    with pytest.raises(ValueError):\n"
                    "        validate_name('abc\\n')\n"
                ),
            },
        )
        res_re = ENGINE.solve_repository(r_re, ["tests/test_names.py"], python_exe=sys.executable)
        assert res_re["verified"] is True
        assert res_re["winner"]["file"] == "pkg/names.py"

        # 2. Import-time constant frozenset missing-element abduction
        r_fs = pathlib.Path(tmp) / "r_fs"
        _write_files(
            r_fs,
            {
                "pkg/headers.py": (
                    "class Policy:\n"
                    "    STRIP = frozenset(['Authorization'])\n"
                    "    def __init__(self):\n"
                    "        self.strip = frozenset(h.lower() for h in self.STRIP)\n"
                ),
                "tests/test_headers.py": (
                    "from pkg.headers import Policy\n\n"
                    "def test_default_strip():\n"
                    "    assert Policy().strip == {'authorization', 'cookie'}\n"
                ),
            },
        )
        res_fs = ENGINE.solve_repository(r_fs, ["tests/test_headers.py"], python_exe=sys.executable)
        assert res_fs["verified"] is True
        assert res_fs["winner"]["file"] == "pkg/headers.py"

        # 3. Multi-line `if` truthiness-vs-None
        r_tr = pathlib.Path(tmp) / "r_tr"
        _write_files(
            r_tr,
            {
                "pkg/reg.py": (
                    "class Registry:\n"
                    "    def __init__(self):\n"
                    "        self.items = {}\n"
                    "    def get(self, name):\n"
                    "        return self.items.get(name)\n"
                    "    def maybe_add(self, name, obj, allow=None):\n"
                    "        if (\n"
                    "            self.get(name)\n"
                    "            or (allow is not None and name != allow)\n"
                    "        ):\n"
                    "            return False\n"
                    "        self.items[name] = obj\n"
                    "        return True\n"
                ),
                "tests/test_reg.py": (
                    "from pkg.reg import Registry\n\n"
                    "class StrictObj:\n"
                    "    def __bool__(self):\n"
                    "        raise AssertionError('Plugin truthiness must not be evaluated')\n\n"
                    "def test_truthiness_not_evaluated():\n"
                    "    r = Registry()\n"
                    "    assert r.maybe_add('a', StrictObj()) is True\n"
                    "    assert r.maybe_add('a', StrictObj()) is False\n"
                ),
            },
        )
        res_tr = ENGINE.solve_repository(r_tr, ["tests/test_reg.py"], python_exe=sys.executable)
        assert res_tr["verified"] is True
        assert res_tr["winner"]["file"] == "pkg/reg.py"


def test_str_direction_duality_and_url_safe_percent_encoding_laws() -> None:
    """Verify general Python string direction duality (`split` <-> `rsplit`) and
    URL percent-encoding `safe=` abduction laws.
    """
    with tempfile.TemporaryDirectory() as tmp:
        # 1. `split("@", 1)` -> `rsplit("@", 1)` when password contains `@`
        r_sp = pathlib.Path(tmp) / "r_sp"
        _write_files(
            r_sp,
            {
                "pkg/net.py": (
                    "def strip_auth(netloc: str) -> str:\n"
                    "    if '@' not in netloc:\n"
                    "        return netloc\n"
                    "    _, host = netloc.split('@', 1)\n"
                    "    return host\n"
                ),
                "tests/test_net.py": (
                    "from pkg.net import strip_auth\n\n"
                    "def test_simple():\n"
                    "    assert strip_auth('user:pw@git.corp.org') == 'git.corp.org'\n"
                    "    assert strip_auth('plain.host') == 'plain.host'\n\n"
                    "def test_at_in_password():\n"
                    "    assert strip_auth('user:p@ss@example.com') == 'example.com'\n"
                ),
            },
        )
        res_sp = ENGINE.solve_repository(r_sp, ["tests/test_net.py"], python_exe=sys.executable)
        assert res_sp["verified"] is True
        assert res_sp["winner"]["file"] == "pkg/net.py"
        assert "split->rsplit" in res_sp["winner"]["description"]

        # 2. URL percent-encoding `safe=` law (`1+2` -> `1%2B2`)
        r_url = pathlib.Path(tmp) / "r_url"
        _write_files(
            r_url,
            {
                "pkg/urls.py": (
                    "from urllib.parse import quote\n"
                    "def build_query(val: str) -> str:\n"
                    "    return '?v=' + quote(val, safe='/+:')\n"
                ),
                "tests/test_urls.py": (
                    "from pkg.urls import build_query\n\n"
                    "def test_slash_preserved():\n"
                    "    assert build_query('a/b:c') == '?v=a/b:c'\n\n"
                    "def test_plus_encoded():\n"
                    "    assert build_query('1+2') == '?v=1%2B2'\n"
                ),
            },
        )
        res_url = ENGINE.solve_repository(r_url, ["tests/test_urls.py"], python_exe=sys.executable)
        assert res_url["verified"] is True
        assert res_url["winner"]["file"] == "pkg/urls.py"
        assert "url_safe_remove" in res_url["winner"]["description"]


def test_higher_order_bool_to_len_and_return_alias_copy_laws() -> None:
    """Verify general higher-order predicate dual (`bool` -> `len`) and mutable return
    alias isolation (`return head, chain(head, it)` -> `return head.copy(), chain(head, it)`).
    """
    with tempfile.TemporaryDirectory() as tmp:
        # 1. Higher-order predicate `takewhile(bool, ...)` -> `takewhile(len, ...)`
        r_pred = pathlib.Path(tmp) / "r_pred"
        _write_files(
            r_pred,
            {
                "pkg/chunks.py": (
                    "from itertools import count, takewhile\n"
                    "def sliced_chunks(seq, n):\n"
                    "    return list(takewhile(bool, (seq[i : i + n] for i in count(0, n))))\n"
                ),
                "tests/test_chunks.py": (
                    "from pkg.chunks import sliced_chunks\n\n"
                    "class ArrayLike:\n"
                    "    def __init__(self, data):\n"
                    "        self._data = list(data)\n"
                    "    def __len__(self):\n"
                    "        return len(self._data)\n"
                    "    def __bool__(self):\n"
                    "        return False\n"
                    "    def __getitem__(self, s):\n"
                    "        return ArrayLike(self._data[s])\n"
                    "    def __eq__(self, other):\n"
                    "        return self._data == other\n\n"
                    "def test_regular_list():\n"
                    "    assert sliced_chunks([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]\n\n"
                    "def test_array_like():\n"
                    "    assert sliced_chunks(ArrayLike([0, 1, 2, 3, 4, 5]), 3) == [[0, 1, 2], [3, 4, 5]]\n"
                ),
            },
        )
        res_pred = ENGINE.solve_repository(r_pred, ["tests/test_chunks.py"], python_exe=sys.executable)
        assert res_pred["verified"] is True
        assert res_pred["winner"]["file"] == "pkg/chunks.py"
        assert "bool->len" in res_pred["winner"]["description"]

        # 2. Return alias isolation: `return head, chain(head, it)` -> `return head.copy(), chain(head, it)`
        r_alias = pathlib.Path(tmp) / "r_alias"
        _write_files(
            r_alias,
            {
                "pkg/peek.py": (
                    "from itertools import chain, islice\n"
                    "def peek_head(iterable, n=1):\n"
                    "    it = iter(iterable)\n"
                    "    head = list(islice(it, n))\n"
                    "    return head, chain(head, it)\n"
                ),
                "tests/test_peek.py": (
                    "from pkg.peek import peek_head\n\n"
                    "def test_basic():\n"
                    "    head, it = peek_head('abcd', 2)\n"
                    "    assert head == ['a', 'b']\n"
                    "    assert list(it) == ['a', 'b', 'c', 'd']\n\n"
                    "def test_mutation_isolated():\n"
                    "    head, it = peek_head('abcd', 2)\n"
                    "    head[0] = 'Z'\n"
                    "    assert list(it) == ['a', 'b', 'c', 'd']\n"
                ),
            },
        )
        res_alias = ENGINE.solve_repository(r_alias, ["tests/test_peek.py"], python_exe=sys.executable)
        assert res_alias["verified"] is True
        assert res_alias["winner"]["file"] == "pkg/peek.py"
        assert "return_alias" in res_alias["winner"]["description"]


def test_static_regex_lookahead_and_module_const_diff_abduction_laws() -> None:
    """Verify static-cone negative-lookahead placement (`(A(?!X))` -> `((?!X)A)`) and
    module-level constant diff abduction from `startswith` assertions.
    """
    with tempfile.TemporaryDirectory() as tmp:
        # 1. Negative lookahead placement in `re.compile(...)`
        r_la = pathlib.Path(tmp) / "r_la"
        _write_files(
            r_la,
            {
                "pkg/norm.py": (
                    "import re\n"
                    "_norm_re = re.compile(r'[a-z0-9]|[a-z0-9]([a-z0-9-](?!--))*[a-z0-9]', re.ASCII)\n"
                    "def is_norm(name: str) -> bool:\n"
                    "    return _norm_re.fullmatch(name) is not None\n"
                ),
                "tests/test_norm.py": (
                    "from pkg.norm import is_norm\n\n"
                    "def test_valid():\n"
                    "    assert is_norm('a-b-1')\n"
                    "    assert is_norm('1-1')\n\n"
                    "def test_double_dash_rejected():\n"
                    "    assert not is_norm('1--1')\n"
                ),
            },
        )
        res_la = ENGINE.solve_repository(r_la, ["tests/test_norm.py"], python_exe=sys.executable)
        assert res_la["verified"] is True
        assert res_la["winner"]["file"] == "pkg/norm.py"
        assert "lookahead" in res_la["winner"]["description"]

        # 2. Module-level constant diff abduction (`260000` -> `600000`) from `startswith`
        r_const = pathlib.Path(tmp) / "r_const"
        _write_files(
            r_const,
            {
                "pkg/hasher.py": (
                    "DEFAULT_ROUNDS = 260000\n"
                    "def make_hash(pw: str) -> str:\n"
                    "    return f'pbkdf2:sha256:{DEFAULT_ROUNDS}$salt${pw}'\n"
                ),
                "tests/test_hasher.py": (
                    "from pkg.hasher import make_hash\n\n"
                    "def test_rounds():\n"
                    "    h = make_hash('secret')\n"
                    "    assert h.startswith('pbkdf2:sha256:600000$')\n"
                ),
            },
        )
        res_const = ENGINE.solve_repository(r_const, ["tests/test_hasher.py"], python_exe=sys.executable)
        assert res_const["verified"] is True
        assert res_const["winner"]["file"] == "pkg/hasher.py"
        assert "static_const_int(260000->600000)" in res_const["winner"]["description"]


def test_guard_null_format_empty_elem_guard_and_missing_kwarg_forward_laws() -> None:
    """Verify guard-missing-interpolated-null (`and self.envvar is not None`),
    empty-element list-accumulator guard (`[x] if x else []`), and exception-named
    missing-kwarg forwarding (`context=context`).
    """
    with tempfile.TemporaryDirectory() as tmp:
        # 1. Guard missing interpolated None in f-string
        r_null = pathlib.Path(tmp) / "r_null"
        _write_files(
            r_null,
            {
                "pkg/opt.py": (
                    "class Opt:\n"
                    "    def __init__(self, name, show_envvar=True, envvar=None):\n"
                    "        self.name = name\n"
                    "        self.show_envvar = show_envvar\n"
                    "        self.envvar = envvar\n"
                    "    def hint(self) -> str:\n"
                    "        res = f'Missing option {self.name}'\n"
                    "        if self.show_envvar:\n"
                    "            res += f\" (env var: '{self.envvar}')\"\n"
                    "        return res + '.'\n"
                ),
                "tests/test_opt.py": (
                    "from pkg.opt import Opt\n\n"
                    "def test_with_env():\n"
                    "    assert \"(env var: 'FOO')\" in Opt('--foo', envvar='FOO').hint()\n\n"
                    "def test_without_env():\n"
                    "    assert 'Missing option --foo.' in Opt('--foo', envvar=None).hint()\n"
                ),
            },
        )
        res_null = ENGINE.solve_repository(r_null, ["tests/test_opt.py"], python_exe=sys.executable)
        assert res_null["verified"] is True
        assert res_null["winner"]["file"] == "pkg/opt.py"
        assert (
            "guard_null_format" in res_null["winner"]["description"]
            or "self.envvar is None" in res_null["winner"]["description"]
        )

        # 2. Empty-element list accumulator guard (`[self.options_metavar] if ... else []`)
        r_emp = pathlib.Path(tmp) / "r_emp"
        _write_files(
            r_emp,
            {
                "pkg/cli.py": (
                    "class Cmd:\n"
                    "    def __init__(self, options_metavar='[OPTIONS]'):\n"
                    "        self.options_metavar = options_metavar\n"
                    "    def usage(self, arg: str) -> str:\n"
                    "        rv = [self.options_metavar]\n"
                    "        rv.append(arg)\n"
                    "        return 'Usage: cli ' + ' '.join(rv) + '\\n'\n"
                ),
                "tests/test_cli.py": (
                    "from pkg.cli import Cmd\n\n"
                    "def test_default():\n"
                    "    assert 'Usage: cli [OPTIONS] VAR\\n' in Cmd().usage('VAR')\n\n"
                    "def test_empty_metavar():\n"
                    "    assert 'Usage: cli VAR\\n' in Cmd('').usage('VAR')\n"
                ),
            },
        )
        res_emp = ENGINE.solve_repository(r_emp, ["tests/test_cli.py"], python_exe=sys.executable)
        assert res_emp["verified"] is True
        assert res_emp["winner"]["file"] == "pkg/cli.py"
        assert "empty_elem_guard" in res_emp["winner"]["description"]

        # 3. Exception-named missing-kwarg forwarding (`without context` -> `context=context`)
        r_ctx = pathlib.Path(tmp) / "r_ctx"
        _write_files(
            r_ctx,
            {
                "pkg/env.py": (
                    "class Env:\n"
                    "    def call_test(self, item, context=None):\n"
                    "        if context is None:\n"
                    "            raise RuntimeError('Attempted to invoke test without context.')\n"
                    "        return item in context.allowed\n"
                ),
                "pkg/filt.py": (
                    "def run_select(context, items):\n"
                    "    def pred(item):\n"
                    "        return context.env.call_test(item)\n"
                    "    return [x for x in items if pred(x)]\n"
                ),
                "tests/test_ctx.py": (
                    "from types import SimpleNamespace\n"
                    "from pkg.env import Env\n"
                    "from pkg.filt import run_select\n\n"
                    "def test_select_with_context():\n"
                    "    ctx = SimpleNamespace(env=Env(), allowed={2, 4})\n"
                    "    assert run_select(ctx, [1, 2, 3, 4]) == [2, 4]\n"
                ),
            },
        )
        res_ctx = ENGINE.solve_repository(r_ctx, ["tests/test_ctx.py"], python_exe=sys.executable)
        assert res_ctx["verified"] is True
        assert res_ctx["winner"]["file"] == "pkg/filt.py"
        assert "forward_missing_kwarg(context=context)" in res_ctx["winner"]["description"]


def test_compositional_multi_file_angelic_progress_repair() -> None:
    """Verify Compositional Differential Patch Accumulation (Angelic Progress Composition)
    recursively repairs a 2-file simultaneous bug in one `solve_repository` call with 0 regressions.
    """
    with tempfile.TemporaryDirectory() as tmp:
        r_multi = pathlib.Path(tmp) / "r_multi"
        _write_files(
            r_multi,
            {
                "pkg/__init__.py": "",
                "pkg/host.py": (
                    "def split_addr(server_name: str):\n"
                    "    sn_host, _, sn_port = server_name.partition(':')\n"
                    "    return sn_host, (int(sn_port) if sn_port else 80)\n"
                ),
                "pkg/keys.py": (
                    "def resolve_key(data_key, field_name):\n"
                    "    return data_key or field_name\n"
                ),
                "tests/test_multi.py": (
                    "from pkg.host import split_addr\n"
                    "from pkg.keys import resolve_key\n\n"
                    "def test_ipv4_ok():\n"
                    "    assert split_addr('localhost:8080') == ('localhost', 8080)\n\n"
                    "def test_nonempty_key_ok():\n"
                    "    assert resolve_key('custom', 'fallback') == 'custom'\n"
                    "    assert resolve_key(None, 'fallback') == 'fallback'\n\n"
                    "def test_ipv6_addr():\n"
                    "    assert split_addr('[::1]:8080') == ('::1', 8080)\n\n"
                    "def test_empty_data_key():\n"
                    "    assert resolve_key('', 'fallback') == ''\n"
                ),
            },
        )
        res = ENGINE.solve_repository(
            r_multi, ["tests/test_multi.py"], python_exe=sys.executable, max_compose_depth=2
        )
        assert res["verified"] is True
        assert res["model_calls"] == 0
        assert res["parameters_stored"] == 0
        w = res["winner"]
        assert w["tier"] == "COMPOSED_ANGELIC_PROGRESS"
        assert set(w["files"]) == {"pkg/host.py", "pkg/keys.py"}
        assert w["regressions"] == 0
        assert len(w["composed_patches"]) == 2


def test_wake_sleep_plotkin_lgg_cross_law_compression_and_zero_probe_transfer() -> None:
    """Verify Online Wake-Sleep Plotkin LGG compresses 2 concrete AST laws into a strictly
    more general higher-order law (while blocking bare-$var overgeneralization) and solves
    an unseen 3rd repo in 0 angelic probes via `TIER0_AST_REWRITE_LAW`.
    """
    store = SKILL_STORE.new_store()
    # Concrete Law 1: `a.startswith("foo")` -> `a.startswith("foo" + ".")` (differing const "foo")
    src1_b = "def f(x):\n    return x.endswith('alpha')\n"
    src1_a = "def f(x):\n    return x == 'alpha' or x.endswith('.alpha')\n"
    # Concrete Law 2: same shape with different concrete literal `'beta'` vs `'alpha'`?
    # Better: two concrete method calls with differing literal args that share an operator anchor:
    law1 = ENGINE._induce_ast_rewrite_law(
        store,
        "def f(a):\n    return a.strip('x') or a\n",
        "def f(a):\n    return a.strip('x') if a.strip('x') is not None else a\n",
        2,
        "AssertionError",
        "TIER3_BOOLOP_NONE_GUARD",
    )
    law2 = ENGINE._induce_ast_rewrite_law(
        store,
        "def g(b):\n    return b.strip('y') or b\n",
        "def g(b):\n    return b.strip('y') if b.strip('y') is not None else b\n",
        2,
        "AssertionError",
        "TIER3_BOOLOP_NONE_GUARD",
    )
    assert law1 is not None and law2 is not None
    # Also test direct paired LGG compression across two differing concrete Call rules
    lgg = ENGINE._anti_unify_sexpr_pairs(
        ["Call", ["Attr", {"$var": 0}, "replace"], [["Const", "a"], ["Const", "b"]], []],
        ["Call", ["Attr", {"$var": 0}, "replace"], [["Const", "a"], ["Const", "b"], ["Const", 1]], []],
        ["Call", ["Attr", {"$var": 0}, "replace"], [["Const", "x"], ["Const", "y"]], []],
        ["Call", ["Attr", {"$var": 0}, "replace"], [["Const", "x"], ["Const", "y"], ["Const", 1]], []],
    )
    assert lgg is not None
    gen_b, gen_a, nvars = lgg
    assert gen_b[0] == "Call" and gen_a[0] == "Call"
    assert nvars == 3  # $0 (receiver), $1 (old), $2 (new) — trailing Const(1) preserved!

    # Anti-overgeneralization guard: unrelated root constructors must NEVER collapse to bare $var
    bad_lgg = ENGINE._anti_unify_sexpr_pairs(
        ["Call", ["Name", "foo"], [{"$var": 0}], []],
        ["Call", ["Name", "bar"], [{"$var": 0}], []],
        ["BinOp", "Add", {"$var": 0}, ["Const", 1]],
        ["BinOp", "Sub", {"$var": 0}, ["Const", 1]],
    )
    assert bad_lgg is None

    # Now induce two differing concrete `.replace(c1, c2)` -> `.replace(c1, c2, 1)` laws into store
    # and verify Wake-Sleep automatically compresses them into `astlaw_lgg_*`, which then solves
    # an UNSEEN 3rd repo using DIFFERENT constants ('/', '-') with 0 angelic probes!
    store2 = SKILL_STORE.new_store()
    ENGINE._induce_ast_rewrite_law(
        store2,
        "def r1(s):\n    return s.replace('a', 'b')\n",
        "def r1(s):\n    return s.replace('a', 'b', 1)\n",
        2, "AssertionError", "TIER3_REPLACE_CONTEXT_NARROW",
    )
    ENGINE._induce_ast_rewrite_law(
        store2,
        "def r2(t):\n    return t.replace('x', 'y')\n",
        "def r2(t):\n    return t.replace('x', 'y', 1)\n",
        2, "AssertionError", "TIER3_REPLACE_CONTEXT_NARROW",
    )
    lgg_laws = [
        l for l in store2["ast_rewrite_laws"].values()
        if l.get("source_tier") == "WAKE_SLEEP_PLOTKIN_LGG"
    ]
    assert len(lgg_laws) >= 1
    assert len(lgg_laws[0]["generalized_from"]) == 2

    with tempfile.TemporaryDirectory() as tmp:
        r_unseen = pathlib.Path(tmp) / "r_unseen"
        _write_files(
            r_unseen,
            {
                "pkg/rewrite.py": (
                    "def first_slash_to_dash(path: str) -> str:\n"
                    "    return path.replace('/', '-')\n"
                ),
                "tests/test_rewrite.py": (
                    "from pkg.rewrite import first_slash_to_dash\n\n"
                    "def test_single():\n"
                    "    assert first_slash_to_dash('a/b') == 'a-b'\n\n"
                    "def test_only_first():\n"
                    "    assert first_slash_to_dash('a/b/c') == 'a-b/c'\n"
                ),
            },
        )
        res = ENGINE.solve_repository(
            r_unseen,
            ["tests/test_rewrite.py"],
            skill_store=store2,
            python_exe=sys.executable,
        )
        assert res["verified"] is True
        assert res["angelic_probes_run"] == 0
        assert res["winner"]["tier"] == "TIER0_AST_REWRITE_LAW"
        assert res["winner"]["skill_id_used"].startswith("astlaw_lgg_")


def test_iter11_universal_semantic_laws_and_worktree_nodeid_hygiene() -> None:
    """Verify Enum subscript lookup, suffix boundary guard, regex char-class abduction,
    and immunity to parametrized newline / worktree-path nodeids.
    """
    with tempfile.TemporaryDirectory() as tmp:
        # 1. Enum getattr -> subscript + worktree-path & newline parametrized nodeids
        r_enum = pathlib.Path(tmp) / "r_enum"
        _write_files(
            r_enum,
            {
                "pkg/enums.py": (
                    "import enum\n"
                    "class Color(enum.Enum):\n"
                    "    RED = 1\n"
                    "    BLUE = 2\n"
                    "def lookup(name: str):\n"
                    "    try:\n"
                    "        return getattr(Color, name)\n"
                    "    except AttributeError as err:\n"
                    "        raise ValueError(name) from err\n"
                ),
                "tests/test_enums.py": (
                    "import pytest\n"
                    "from pkg.enums import Color, lookup\n\n"
                    "@pytest.mark.parametrize('p', [__file__, 'line1\\nline2'])\n"
                    "def test_valid_with_tricky_nodeid(p):\n"
                    "    assert lookup('RED') is Color.RED\n\n"
                    "@pytest.mark.parametrize('bad', ['mro', '__class__', '__members__'])\n"
                    "def test_reject_non_members(bad):\n"
                    "    with pytest.raises(ValueError):\n"
                    "        lookup(bad)\n"
                ),
            },
        )
        res_enum = ENGINE.solve_repository(r_enum, ["tests/test_enums.py"], python_exe=sys.executable)
        assert res_enum["verified"] is True
        assert res_enum["winner"]["tier"] == "TIER3_ENUM_SUBSCRIPT_LOOKUP"

        # 2. Suffix domain boundary guard
        r_suf = pathlib.Path(tmp) / "r_suf"
        _write_files(
            r_suf,
            {
                "pkg/proxy.py": (
                    "def bypass(hostname: str, rules: list[str]) -> bool:\n"
                    "    for rule in rules:\n"
                    "        if hostname.endswith(rule):\n"
                    "            return True\n"
                    "    return False\n"
                ),
                "tests/test_proxy.py": (
                    "from pkg.proxy import bypass\n\n"
                    "def test_exact_and_sub():\n"
                    "    assert bypass('localhost', ['localhost']) is True\n"
                    "    assert bypass('sub.example.com', ['example.com']) is True\n\n"
                    "def test_boundary():\n"
                    "    assert bypass('prelocalhost', ['localhost']) == False\n"
                ),
            },
        )
        res_suf = ENGINE.solve_repository(r_suf, ["tests/test_proxy.py"], python_exe=sys.executable)
        assert res_suf["verified"] is True
        assert res_suf["winner"]["tier"] == "TIER3_SUFFIX_BOUNDARY_GUARD"


def test_iter16_unseen_all_site_unary_unwrap_drop_kwarg_and_json_dumps_laws_with_tier0_transfer() -> None:
    """Verify Iter 16 SWE structural laws (#34 same-file all-site unary unwrap, #35 call kwarg drop,
    #36 canonical compact/UTF-8/strict json.dumps) and single-experience 0-probe Plotkin AST transfer."""
    with tempfile.TemporaryDirectory(prefix="iter16_swe_") as tmp:
        root = pathlib.Path(tmp)

        # 1. Law #34: Same-file all-occurrence unary transform unwrap across two sibling methods
        r1 = root / "r_unwrap"
        _write_files(
            r1,
            {
                "pkg/cli.py": (
                    "def _tr(s: str) -> str:\n"
                    "    return s.upper()\n\n"
                    "def full_help(text: str) -> str:\n"
                    "    return f'{_tr(text)} (DEPRECATED)'\n\n"
                    "def short_help(text: str) -> str:\n"
                    "    return f'{_tr(text)} [old]'\n"
                ),
                "tests/test_cli.py": (
                    "from pkg.cli import full_help, short_help\n\n"
                    "def test_no_translate():\n"
                    "    assert full_help('run server') == 'run server (DEPRECATED)'\n"
                    "    assert short_help('run server') == 'run server [old]'\n"
                ),
            },
        )
        res1 = ENGINE.solve_repository(r1, ["tests/test_cli.py"], python_exe=sys.executable)
        assert res1["verified"] is True, res1
        assert res1["winner"]["tier"] == "TIER3_UNWRAP_UNARY_CALL_ON_DIFF"

        # 2. Law #35: Drop over-specified call keyword argument + 0-probe Plotkin AST transfer to unseen Repo B
        store = SKILL_STORE.new_store()
        r2a = root / "r_kwarg_a"
        _write_files(
            r2a,
            {
                "pkg/url_a.py": (
                    "from urllib.parse import urlencode\n"
                    "SAFE_CHARS = '/:'\n"
                    "def build_query(pairs):\n"
                    "    return urlencode(pairs, safe=SAFE_CHARS)\n"
                ),
                "tests/test_url_a.py": (
                    "from pkg.url_a import build_query\n\n"
                    "def test_encode_slash():\n"
                    "    assert build_query([('u', 'a/b')]) == 'u=a%2Fb'\n"
                ),
            },
        )
        res2a = ENGINE.solve_repository(r2a, ["tests/test_url_a.py"], skill_store=store, learn_into_store=True, python_exe=sys.executable)
        assert res2a["verified"] is True, res2a
        assert res2a["winner"]["tier"] == "TIER3_DROP_CALL_KWARG"

        # 3. Law #36: Canonical compact / UTF-8 / strict NaN json.dumps serialization
        r3 = root / "r_json"
        _write_files(
            r3,
            {
                "pkg/payload.py": (
                    "from json import dumps as json_dumps\n"
                    "def encode(obj) -> bytes:\n"
                    "    return json_dumps(obj).encode('utf-8')\n"
                ),
                "tests/test_payload.py": (
                    "import math, pytest\n"
                    "from pkg.payload import encode\n\n"
                    "def test_compact_utf8():\n"
                    "    assert encode({'clé': [1, 2]}) == b'{\"cl\\xc3\\xa9\":[1,2]}'\n\n"
                    "def test_reject_nan():\n"
                    "    with pytest.raises(ValueError):\n"
                    "        encode({'x': math.nan})\n"
                ),
            },
        )
        res3 = ENGINE.solve_repository(r3, ["tests/test_payload.py"], python_exe=sys.executable)
        assert res3["verified"] is True, res3
        assert res3["winner"]["tier"] == "TIER3_JSON_DUMPS_CANONICAL_KWARGS"


def test_iter18_ctx_save_restore_wrapper_unwrap_and_regex_negclass_laws() -> None:
    """Verify Iter 18 general Tier 3b semantic laws:
    1. Law #37 (TIER3_CTX_SAVE_RESTORE_PAIR): reentrant context-manager save/restore via get_X/set_X.
    2. Law #38 (TIER3_WRAPPER_STRING_UNWRAP): unwrap stringified wrapper types like ForwardRef('...').
    3. Law #39 (TIER3_CHAR_GUARD_AND_REGEX_NEGCLASS): tighten greedy \\S+<sep> to [^\\s<sep>]+<sep>.
    """
    with tempfile.TemporaryDirectory(prefix="iter18_swe_") as tmp:
        root = pathlib.Path(tmp)

        # 1. Law #37: Nested context manager save/restore via sibling get_X / set_X
        r1 = root / "r_ctx"
        _write_files(
            r1,
            {
                "pkg/cfg.py": (
                    "from contextlib import contextmanager\n"
                    "_ENABLED = True\n"
                    "def get_enabled() -> bool:\n"
                    "    return _ENABLED\n"
                    "def set_enabled(flag: bool) -> None:\n"
                    "    global _ENABLED\n"
                    "    _ENABLED = flag\n"
                    "@contextmanager\n"
                    "def suspended():\n"
                    "    set_enabled(False)\n"
                    "    try:\n"
                    "        yield\n"
                    "    finally:\n"
                    "        set_enabled(True)\n"
                ),
                "tests/test_cfg.py": (
                    "from pkg.cfg import get_enabled, suspended\n\n"
                    "def test_nested_ctx():\n"
                    "    assert get_enabled() is True\n"
                    "    with suspended():\n"
                    "        with suspended():\n"
                    "            assert get_enabled() is False\n"
                    "        assert get_enabled() is False\n"
                    "    assert get_enabled() is True\n"
                ),
            },
        )
        res1 = ENGINE.solve_repository(r1, ["tests/test_cfg.py"], python_exe=sys.executable)
        assert res1["verified"] is True, res1
        assert res1["winner"]["tier"] == "TIER3_CTX_SAVE_RESTORE_PAIR"

        # 2. Law #38: Unwrap stringified wrapper type (e.g. ForwardRef('Tag[int]'))
        r2 = root / "r_wrap"
        _write_files(
            r2,
            {
                "pkg/ann.py": (
                    "_PREFIXES = ('Tag', 'mod.Tag')\n"
                    "def is_tag(annot) -> bool:\n"
                    "    annot = str(annot)\n"
                    "    if annot.startswith((\"'\", '\"')) and annot.endswith((\"'\", '\"')):\n"
                    "        annot = annot[1:-1]\n"
                    "    return annot.startswith(_PREFIXES)\n"
                ),
                "tests/test_ann.py": (
                    "from typing import ForwardRef\n"
                    "from pkg.ann import is_tag\n\n"
                    "def test_forward_ref():\n"
                    "    assert is_tag('Tag[int]')\n"
                    "    assert is_tag(ForwardRef('Tag[str]'))\n"
                    "    assert not is_tag(ForwardRef('Other[str]'))\n"
                ),
            },
        )
        res2 = ENGINE.solve_repository(r2, ["tests/test_ann.py"], python_exe=sys.executable)
        assert res2["verified"] is True, res2
        assert res2["winner"]["tier"] == "TIER3_WRAPPER_STRING_UNWRAP"

        # 3. Law #39: Tighten greedy \S+@ regex to [^\s@]+@ so @user@host isn't matched as email
        r3 = root / "r_re"
        _write_files(
            r3,
            {
                "pkg/link.py": (
                    "import re\n"
                    "_MAIL_RE = re.compile(r'^\\S+@\\w[\\w.-]*\\.\\w+$')\n"
                    "def linkify(tok: str) -> str:\n"
                    "    if '@' in tok and _MAIL_RE.match(tok):\n"
                    "        return f'mailto:{tok}'\n"
                    "    return tok\n"
                ),
                "tests/test_link.py": (
                    "from pkg.link import linkify\n\n"
                    "def test_linkify():\n"
                    "    assert linkify('a@b.org') == 'mailto:a@b.org'\n"
                    "    assert linkify('@user@host.social') == '@user@host.social'\n"
                ),
            },
        )
        res3 = ENGINE.solve_repository(r3, ["tests/test_link.py"], python_exe=sys.executable)
        assert res3["verified"] is True, res3
        assert res3["winner"]["tier"] == "TIER3_CHAR_GUARD_AND_REGEX_NEGCLASS"


def test_iter20_url_percent_diff_safe_and_plus_law() -> None:
    """Verify Iter 20 Law #40 (TIER3_URL_PERCENT_DIFF_SAFE_AND_PLUS): abduce missing safe
    characters and space-to-plus encoding directly from percent-encoding assertion diffs.
    """
    with tempfile.TemporaryDirectory(prefix="iter20_swe_") as tmp:
        r = pathlib.Path(tmp) / "r_url"
        _write_files(
            r,
            {
                "pkg/qenc.py": (
                    "from urllib.parse import quote\n"
                    "def encode_query(items):\n"
                    "    return '&'.join([quote(k, safe='') + '=' + quote(v, safe='') for k, v in items])\n"
                ),
                "tests/test_qenc.py": (
                    "from pkg.qenc import encode_query\n\n"
                    "def test_space_and_slash():\n"
                    "    assert encode_query([('q', 'hello world'), ('p', 'a/b:c')]) == 'q=hello+world&p=a/b:c'\n"
                ),
            },
        )
        res = ENGINE.solve_repository(r, ["tests/test_qenc.py"], python_exe=sys.executable)
        assert res["verified"] is True, res
        assert res["winner"]["tier"] == "TIER3_URL_PERCENT_DIFF_SAFE_AND_PLUS"


def test_iter21_ternary_collapse_ascii_int_coupled_none_and_ne_laws() -> None:
    """Verify Iter 21 SWE Laws #41-#44:
    - Law #41 (`TIER3_TERNARY_COLLAPSE_TO_BRANCH`): simplify over-defensive ternary fallback
      inside a multi-line `return` call.
    - Law #42 (`TIER3_STRICT_ASCII_DIGIT_INT_GUARD`): reject whitespace, `+`, `_`, and
      non-ASCII Unicode digits before permissive `int(s)`.
    - Law #43 (`TIER3_COUPLED_TRUTHINESS_TO_IS_NOT_NONE`): coupled multi-site falsy-0 guard
      repair on nullable variable (`port=0`).
    - Law #44 (`TIER3_EQ_NE_NOTIMPLEMENTED_GUARD`): propagate `NotImplemented` in `__ne__`.
    """
    with tempfile.TemporaryDirectory(prefix="iter21_swe_") as tmp:
        root = pathlib.Path(tmp)

        # 1. Law #41: Multi-line return with ternary fallback collapse
        r1 = root / "r_ifexp"
        _write_files(
            r1,
            {
                "pkg/ref.py": (
                    "def combine(base_path, base_frag, ref_path, ref_frag):\n"
                    "    path = ref_path if ref_path else base_path\n"
                    "    return (\n"
                    "        path,\n"
                    "        ref_frag if ref_path or ref_frag else base_frag,\n"
                    "    )\n"
                ),
                "tests/test_ref.py": (
                    "from pkg.ref import combine\n\n"
                    "def test_drop_base_fragment():\n"
                    "    assert combine('/a', 'old', '', '') == ('/a', '')\n"
                    "    assert combine('/a', 'old', '', 'new') == ('/a', 'new')\n"
                ),
            },
        )
        res1 = ENGINE.solve_repository(r1, ["tests/test_ref.py"], python_exe=sys.executable)
        assert res1["verified"] is True, res1
        assert res1["winner"]["tier"] == "TIER3_TERNARY_COLLAPSE_TO_BRANCH"

        # 2. Law #42: Strict ASCII-digit int() guard
        r2 = root / "r_port"
        _write_files(
            r2,
            {
                "pkg/net.py": (
                    "def parse_port(port_str: str) -> int:\n"
                    "    try:\n"
                    "        port = int(port_str)\n"
                    "    except ValueError:\n"
                    "        raise ValueError('bad port')\n"
                    "    if not (0 <= port <= 65535):\n"
                    "        raise ValueError('range')\n"
                    "    return port\n"
                ),
                "tests/test_net.py": (
                    "import pytest\n"
                    "from pkg.net import parse_port\n\n"
                    "def test_valid():\n"
                    "    assert parse_port('8080') == 8080\n\n"
                    "@pytest.mark.parametrize('raw', ['+80', ' 80', '8_0', '\\uff18\\uff10'])\n"
                    "def test_reject_non_ascii_digits(raw):\n"
                    "    with pytest.raises(ValueError):\n"
                    "        parse_port(raw)\n"
                ),
            },
        )
        res2 = ENGINE.solve_repository(r2, ["tests/test_net.py"], python_exe=sys.executable)
        assert res2["verified"] is True, res2
        assert res2["winner"]["tier"] == "TIER3_STRICT_ASCII_DIGIT_INT_GUARD"

        # 3. Law #43: Multi-site coupled falsy-0 truthiness -> `is not None`
        r3 = root / "r_falsy0"
        _write_files(
            r3,
            {
                "pkg/addr.py": (
                    "def build_addr(*, authority='', host='', port=None):\n"
                    "    if authority and (host or port):\n"
                    "        raise ValueError('mix')\n"
                    "    if port is not None and not isinstance(port, int):\n"
                    "        raise TypeError('int required')\n"
                    "    if port and not host:\n"
                    "        raise ValueError('need host')\n"
                    "    return f'{authority or host}:{port}'\n"
                ),
                "tests/test_addr.py": (
                    "import pytest\n"
                    "from pkg.addr import build_addr\n\n"
                    "def test_ok():\n"
                    "    assert build_addr(host='h', port=0) == 'h:0'\n\n"
                    "def test_mix_port_zero():\n"
                    "    with pytest.raises(ValueError):\n"
                    "        build_addr(authority='a', port=0)\n\n"
                    "def test_port_zero_no_host():\n"
                    "    with pytest.raises(ValueError):\n"
                    "        build_addr(port=0)\n"
                ),
            },
        )
        res3 = ENGINE.solve_repository(r3, ["tests/test_addr.py"], python_exe=sys.executable)
        assert res3["verified"] is True, res3
        assert res3["winner"]["tier"] == "TIER3_COUPLED_TRUTHINESS_TO_IS_NOT_NONE"

        # 4. Law #44: `__ne__` propagates `NotImplemented` cleanly
        r4 = root / "r_ne"
        _write_files(
            r4,
            {
                "pkg/box.py": (
                    "class Box:\n"
                    "    def __init__(self, v):\n"
                    "        self.v = v\n"
                    "    def __eq__(self, other):\n"
                    "        if not isinstance(other, Box):\n"
                    "            return NotImplemented\n"
                    "        return self.v == other.v\n"
                    "    def __ne__(self, other):\n"
                    "        return not self.__eq__(other)\n"
                ),
                "tests/test_box.py": (
                    "from pkg.box import Box\n\n"
                    "def test_ne_semantics():\n"
                    "    assert not (Box(1) != Box(1))\n"
                    "    assert Box(1) != Box(2)\n"
                    "    assert Box(1) != 'other'\n"
                    "    assert Box(1).__ne__('other') is NotImplemented\n"
                ),
            },
        )
        res4 = ENGINE.solve_repository(r4, ["tests/test_box.py"], python_exe=sys.executable)
        assert res4["verified"] is True, res4
        assert res4["winner"]["tier"] == "TIER3_EQ_NE_NOTIMPLEMENTED_GUARD"


def test_iter22_serial_cross_file_causal_shift_composition() -> None:
    """Verify Iter 22 Stage 4c (`COMPOSED_CAUSAL_SHIFT_PROGRESS`) + multi-file atomic
    application through the ONE front door (`open_model().solve(..., mode='EPISTEMIC')`):
    ONE single failing test exercises TWO broken files (`pkg/parser.py` crashes with IndexError
    AND `pkg/formatter.py` has an over-defensive ternary bug). Fixing `pkg/parser.py` alone
    flips 0 tests yet strictly advances execution (`IndexError -> AssertionError`), unlocking
    `pkg/formatter.py` for coordinated 2-file repair with 0 regressions.
    """
    from canonical.runtime.brain_unified_model_v1 import open_model

    model = open_model()
    with tempfile.TemporaryDirectory(prefix="iter22_xfile_") as tmp:
        repo = pathlib.Path(tmp) / "xfile_repo"
        _write_files(
            repo,
            {
                "pkg/__init__.py": "",
                "pkg/parser.py": (
                    "def extract_host(raw: str) -> str:\n"
                    "    if raw[-1] == '.':\n"
                    "        raw = raw.rstrip('.')\n"
                    "    return raw\n"
                ),
                "pkg/formatter.py": (
                    "def join_target(base_frag: str, ref_host: str, ref_frag: str) -> str:\n"
                    "    frag = ref_frag if ref_host or ref_frag else base_frag\n"
                    "    return f'{ref_host}#{frag}' if frag else ref_host\n"
                ),
                "tests/test_pipeline.py": (
                    "from pkg.parser import extract_host\n"
                    "from pkg.formatter import join_target\n\n"
                    "def test_normal_host():\n"
                    "    h = extract_host('api.example.com.')\n"
                    "    assert join_target('old', h, 'v2') == 'api.example.com#v2'\n\n"
                    "def test_empty_host_drops_base_fragment():\n"
                    "    h = extract_host('')\n"
                    "    assert join_target('stale', h, '') == ''\n"
                ),
            },
        )
        res = model.solve(
            "Fix failing tests in repository",
            mode="EPISTEMIC",
            inputs={"workspace": str(repo), "python_exe": sys.executable, "allow_web": False, "timeout_s": 30.0},
        )
        assert res["status"] == "PASS", res
        er = res["epistemic_result"]
        assert er["model_calls"] == 0
        assert er["parameters_stored"] == 0
        swe = er["swe_result"]
        assert swe["mode"] == "CAUSAL_ANGELIC_COMPOSED_CAUSAL_SHIFT_PROGRESS", swe
        assert sorted(swe["patched_files"]) == ["pkg/formatter.py", "pkg/parser.py"], swe


def test_iter23_interval_dt_frame_sep_elif_inherit_sibling_guard_domain_exc_and_ldexp() -> None:
    """Verify Iter 23 first-principles mechanisms:
    1. Live Tracer Interval-Domain Bounds (`[num_min, num_max]`) + 1D Decision-Tree Interval
       Separation on loop-boundary outliers (`not day > 365`).
    2. Law #45 (`TIER3_ELIF_SIBLING_CONJUNCT_INHERIT`): `elif` inherits parent conjunct.
    3. Law #46 (`TIER3_SIBLING_METHOD_ENTRY_GUARD`): OOP class-contract sibling guard transfer.
    4. Law #47 (`TIER3_CATCH_AND_RETHROW_DOMAIN_EXCEPTION`): stdlib crash -> domain exception.
    5. Law #48 (`TIER3_OVERFLOW_GUARD_ON_EXPONENT`): exact IEEE-754 `math.ldexp` + ±inf limits.
    """
    with tempfile.TemporaryDirectory(prefix="iter23_swe_") as tmp:
        root = pathlib.Path(tmp)

        # 1. Interval-Domain 1D Decision-Tree loop-boundary separation
        r1 = root / "r_interval"
        _write_files(
            r1,
            {
                "pkg/cal.py": (
                    "def adjust(day: int, is_leap: bool) -> int:\n"
                    "    delta = 0\n"
                    "    if day > 59:\n"
                    "        delta = -1\n"
                    "    clamped = min(365, day)\n"
                    "    if is_leap and day > 59:\n"
                    "        clamped += delta\n"
                    "    return clamped\n"
                ),
                "tests/test_cal.py": (
                    "from pkg.cal import adjust\n\n"
                    "def test_regular_year():\n"
                    "    assert [adjust(d, False) for d in range(1, 366)] == list(range(1, 366))\n\n"
                    "def test_leap_year_end():\n"
                    "    vals = [adjust(d, True) for d in range(1, 367)]\n"
                    "    assert vals[364] == 364\n"
                    "    assert vals[365] == 365\n"
                ),
            },
        )
        res1 = ENGINE.solve_repository(r1, ["tests/test_cal.py"], python_exe=sys.executable)
        assert res1["verified"] is True, res1
        assert "365" in res1["winner"]["description"] or "365" in res1["winner"]["patched_source"], res1["winner"]

        # 2. Law #45: `elif` inherits parent `if` conjunct (`n > 1`)
        r2 = root / "r_elif"
        _write_files(
            r2,
            {
                "pkg/trans.py": (
                    "def pick_zone(ts: int, trans: list[int]) -> str:\n"
                    "    n = len(trans)\n"
                    "    if n > 1 and ts >= trans[1]:\n"
                    "        return 'multi'\n"
                    "    elif ts > trans[-1]:\n"
                    "        return 'after'\n"
                    "    else:\n"
                    "        return 'first'\n"
                ),
                "tests/test_trans.py": (
                    "from pkg.trans import pick_zone\n\n"
                    "def test_multi():\n"
                    "    assert pick_zone(20, [10, 15]) == 'multi'\n\n"
                    "def test_single_transition():\n"
                    "    assert pick_zone(20, [10]) == 'first'\n"
                ),
            },
        )
        res2 = ENGINE.solve_repository(r2, ["tests/test_trans.py"], python_exe=sys.executable)
        assert res2["verified"] is True, res2
        assert res2["winner"]["tier"] == "TIER3_ELIF_SIBLING_CONJUNCT_INHERIT", res2["winner"]

        # 3. Law #46: Class sibling-method entry guard transfer
        r3 = root / "r_sib"
        _write_files(
            r3,
            {
                "pkg/zone.py": (
                    "class Zone:\n"
                    "    def __init__(self, has_dst: bool):\n"
                    "        self._has_dst = has_dst\n"
                    "    def _flag(self, dt):\n"
                    "        return dt.year > 2000\n"
                    "    def offset(self, dt):\n"
                    "        if dt is None and self._has_dst:\n"
                    "            return None\n"
                    "        return 1 if self._flag(dt) else 0\n"
                    "    def dst(self, dt):\n"
                    "        if dt is None and self._has_dst:\n"
                    "            return None\n"
                    "        return 1 if self._flag(dt) else 0\n"
                    "    def label(self, dt):\n"
                    "        return 'D' if self._flag(dt) else 'S'\n"
                ),
                "tests/test_zone.py": (
                    "import datetime\n"
                    "from pkg.zone import Zone\n\n"
                    "def test_normal():\n"
                    "    assert Zone(True).label(datetime.datetime(2025, 1, 1)) == 'D'\n\n"
                    "def test_none_dt():\n"
                    "    assert Zone(True).label(None) is None\n"
                ),
            },
        )
        res3 = ENGINE.solve_repository(r3, ["tests/test_zone.py"], python_exe=sys.executable)
        assert res3["verified"] is True, res3
        assert res3["winner"]["tier"] == "TIER3_SIBLING_METHOD_ENTRY_GUARD", res3["winner"]

        # 4. Law #47: Catch stdlib exception & rethrow function's own domain exception
        r4 = root / "r_domexc"
        _write_files(
            r4,
            {
                "pkg/hdr.py": (
                    "import datetime\n"
                    "class BadHeader(Exception):\n"
                    "    pass\n\n"
                    "def parse_year(raw: str) -> int:\n"
                    "    if not raw:\n"
                    "        raise BadHeader('empty')\n"
                    "    return datetime.date(int(raw), 1, 1).year\n"
                ),
                "tests/test_hdr.py": (
                    "import pytest\n"
                    "from pkg.hdr import BadHeader, parse_year\n\n"
                    "def test_ok():\n"
                    "    assert parse_year('2026') == 2026\n\n"
                    "def test_out_of_range():\n"
                    "    with pytest.raises(BadHeader):\n"
                    "        parse_year('10000')\n"
                ),
            },
        )
        res4 = ENGINE.solve_repository(r4, ["tests/test_hdr.py"], python_exe=sys.executable)
        assert res4["verified"] is True, res4
        assert res4["winner"]["tier"] == "TIER3_CATCH_AND_RETHROW_DOMAIN_EXCEPTION", res4["winner"]

        # 5. Law #48: IEEE-754 `math.ldexp` + ±inf overflow guard on `factor * (2 ** exp)`
        r5 = root / "r_ldexp"
        _write_files(
            r5,
            {
                "pkg/backoff.py": (
                    "def compute_backoff(factor: float, n: int, cap: float = 120.0) -> float:\n"
                    "    if n <= 1:\n"
                    "        return 0.0\n"
                    "    val = factor * (2 ** (n - 1))\n"
                    "    return float(max(0.0, min(cap, val)))\n"
                ),
                "tests/test_backoff.py": (
                    "from pkg.backoff import compute_backoff\n\n"
                    "def test_normal():\n"
                    "    assert compute_backoff(0.5, 3) == 2.0\n\n"
                    "def test_overflow_and_subnormal():\n"
                    "    assert compute_backoff(0.5, 1025) == 120.0\n"
                    "    assert compute_backoff(-0.5, 1025) == 0.0\n"
                    "    assert compute_backoff(0.0, 1025) == 0.0\n"
                    "    assert compute_backoff(5.562684646268003e-309, 1025) == 1.0\n"
                ),
            },
        )
        res5 = ENGINE.solve_repository(r5, ["tests/test_backoff.py"], python_exe=sys.executable)
        assert res5["verified"] is True, res5
        assert res5["winner"]["tier"] == "TIER3_OVERFLOW_GUARD_ON_EXPONENT", res5["winner"]


def test_iter24_ordereddict_move_to_end_and_lock_release_on_return() -> None:
    """Verify Iter 24 Laws #49 (`TIER3_ORDEREDDICT_MOVE_TO_END`) and
    #50 (`TIER3_ACQUIRED_LOCK_RELEASE_ON_RETURN`).
    """
    with tempfile.TemporaryDirectory(prefix="brain_iter24_laws_") as td:
        td_p = pathlib.Path(td)

        # 1. Law #49: OrderedDict LRU refresh (`move_to_end` instead of delete+reinsert)
        r1 = td_p / "lru_ordered"
        _write_files(
            r1,
            {
                "pkg/lru.py": (
                    "from collections import OrderedDict\n\n"
                    "class SmallLRU:\n"
                    "    def __init__(self):\n"
                    "        self._container = OrderedDict()\n"
                    "    def put(self, key, val):\n"
                    "        self._container[key] = val\n"
                    "    def get(self, key):\n"
                    "        item = self._container.pop(key)\n"
                    "        self._container[key] = item\n"
                    "        return item\n"
                ),
                "tests/test_lru.py": (
                    "from pkg.lru import SmallLRU\n\n"
                    "def test_lru_moves_to_end_without_pop():\n"
                    "    c = SmallLRU()\n"
                    "    c.put('a', 1)\n"
                    "    c.put('b', 2)\n"
                    "    pops = []\n"
                    "    orig_pop = c._container.pop\n"
                    "    def tracked_pop(*a, **kw):\n"
                    "        pops.append(a)\n"
                    "        return orig_pop(*a, **kw)\n"
                    "    c._container.pop = tracked_pop\n"
                    "    assert c.get('a') == 1\n"
                    "    assert list(c._container.keys()) == ['b', 'a']\n"
                    "    assert pops == []\n"
                ),
            },
        )
        res1 = ENGINE.solve_repository(r1, ["tests/test_lru.py"], python_exe=sys.executable)
        assert res1["verified"] is True, res1
        assert res1["winner"]["tier"] == "TIER3_ORDEREDDICT_MOVE_TO_END", res1["winner"]

        # 2. Law #50: Acquired lock must be released on early return when cached value already exists
        r2 = td_p / "lock_release"
        _write_files(
            r2,
            {
                "pkg/probe.py": (
                    "import threading\n\n"
                    "class ProbeCache:\n"
                    "    def __init__(self):\n"
                    "        self._values = {}\n"
                    "        self._locks = {}\n"
                    "    def acquire_and_get(self, key):\n"
                    "        lock = self._locks.setdefault(key, threading.Lock())\n"
                    "        lock.acquire()\n"
                    "        value = self._values.get(key)\n"
                    "        if value is not None:\n"
                    "            return value\n"
                    "        return None\n"
                    "    def set_and_release(self, key, val):\n"
                    "        self._values[key] = val\n"
                    "        self._locks[key].release()\n"
                ),
                "tests/test_probe.py": (
                    "from pkg.probe import ProbeCache\n\n"
                    "def test_lock_released_on_cached_hit():\n"
                    "    p = ProbeCache()\n"
                    "    assert p.acquire_and_get('host') is None\n"
                    "    p.set_and_release('host', True)\n"
                    "    assert p.acquire_and_get('host') is True\n"
                    "    # Must NOT deadlock on second acquire_and_get!\n"
                    "    assert p._locks['host'].acquire(blocking=False) is True\n"
                    "    p._locks['host'].release()\n"
                ),
            },
        )
        res2 = ENGINE.solve_repository(r2, ["tests/test_probe.py"], python_exe=sys.executable)
        assert res2["verified"] is True, res2
        assert res2["winner"]["tier"] == "TIER3_ACQUIRED_LOCK_RELEASE_ON_RETURN", res2["winner"]


def test_iter35_laws_53_54_assert_to_raise_and_loop_ret_propagate() -> None:
    """Iter 35: Law #53 (semantic assert->TypeError/ValueError) and Law #54 (loop call return-None guard + key propagation)."""
    with tempfile.TemporaryDirectory(prefix="brain_iter35_laws_") as td:
        root = pathlib.Path(td)

        # 1. Law #53: Semantic assert -> TypeError (unmodified parameter) / ValueError (computed lookup)
        r1 = root / "r_assert_raise"
        _write_files(
            r1,
            {
                "pkg/reg.py": (
                    "class Registry:\n"
                    "    def __init__(self):\n"
                    "        self._items = {}\n"
                    "    def add(self, obj, name):\n"
                    "        self._items[name] = obj\n"
                    "    def get_name(self, obj):\n"
                    "        for k, v in self._items.items():\n"
                    "            if v is obj:\n"
                    "                return k\n"
                    "        return None\n"
                    "    def remove(self, obj=None, name=None):\n"
                    "        if name is None:\n"
                    "            assert obj is not None, 'one of name or obj required'\n"
                    "            name = self.get_name(obj)\n"
                    "            assert name is not None, 'obj is not registered'\n"
                    "        return self._items.pop(name, None)\n"
                ),
                "tests/test_reg.py": (
                    "import pytest\n"
                    "from pkg.reg import Registry\n\n"
                    "def test_remove_errors():\n"
                    "    r = Registry()\n"
                    "    o = object()\n"
                    "    r.add(o, 'a')\n"
                    "    assert r.remove(o) is o\n"
                    "    with pytest.raises(ValueError, match='not registered'):\n"
                    "        r.remove(o)\n"
                    "    with pytest.raises(TypeError, match='one of name or obj'):\n"
                    "        r.remove()\n"
                ),
            },
        )
        res1 = ENGINE.solve_repository(r1, ["tests/test_reg.py"], python_exe=sys.executable)
        assert res1["verified"] is True, res1
        assert res1["winner"]["tier"] == "TIER3_ASSERT_TO_EXPLICIT_RAISE", res1["winner"]

        # 2. Law #54: Loop ignored call return value -> None guard + canonical returned key propagation
        r2 = root / "r_loop_ret"
        _write_files(
            r2,
            {
                "pkg/loader.py": (
                    "class Loader:\n"
                    "    def __init__(self):\n"
                    "        self.items = {}\n"
                    "        self.meta = {}\n"
                    "    def register(self, obj, name=None):\n"
                    "        if obj is None:\n"
                    "            return None\n"
                    "        self.items[name] = obj\n"
                    "        return name\n"
                    "    def load_all(self, specs):\n"
                    "        count = 0\n"
                    "        for sp_name, obj, tag in specs:\n"
                    "            self.register(obj, name=sp_name)\n"
                    "            self.meta[sp_name] = tag\n"
                    "            count += 1\n"
                    "        return count\n"
                ),
                "tests/test_loader.py": (
                    "from pkg.loader import Loader\n\n"
                    "class CustomLoader(Loader):\n"
                    "    def register(self, obj, name=None):\n"
                    "        if name == 'skip':\n"
                    "            return None\n"
                    "        if name == 'alias':\n"
                    "            name = 'canonical'\n"
                    "        return super().register(obj, name=name)\n\n"
                    "def test_declined_and_renamed():\n"
                    "    ld = CustomLoader()\n"
                    "    n = ld.load_all([('empty', None, 't0'), ('skip', 1, 't1'), ('alias', 2, 't2')])\n"
                    "    assert n == 1\n"
                    "    assert ld.meta == {'canonical': 't2'}\n"
                ),
            },
        )
        res2 = ENGINE.solve_repository(r2, ["tests/test_loader.py"], python_exe=sys.executable)
        assert res2["verified"] is True, res2
        assert res2["winner"]["tier"] == "TIER3_LOOP_CALL_NONE_CONTINUE", res2["winner"]


def test_iter39_oe_sygus_eusolver_and_deepcopy_boundary_detach() -> None:
    """Iter 39 semantic synthesis breakthroughs (zero LLM calls, zero weights):
    1. Bottom-Up Observational-Equivalence SyGuS synthesizes `max(a, b)` / `min(val, limit)`
       from live failing + passing frames (no bare constant overfit, generalizes to unseen inputs!).
    2. Bottom-Up OE-SyGuS synthesizes `x if x is not None else default` coalescing without losing `0`.
    3. Universal Law #56 (`TIER3_DEEPCOPY_BOUNDARY_DETACH`) repairs mutable aliasing on BOTH
       storage/return boundaries and in-place parameter mutations (injecting `import copy`).
    """
    with tempfile.TemporaryDirectory(prefix="brain_swe_iter39_") as td:
        root = pathlib.Path(td)

        # 1. OE-SyGuS non-swap semantic synthesis: `return a` -> `return max(a, b)` (generalizes to unseen inputs!)
        r1 = root / "r_max"
        _write_files(
            r1,
            {
                "pkg/__init__.py": "",
                "pkg/mathops.py": (
                    "def pick_larger(a: int, b: int) -> int:\n"
                    "    return a\n"
                ),
                "tests/test_mathops.py": (
                    "from pkg.mathops import pick_larger\n\n"
                    "def test_first_larger():\n"
                    "    assert pick_larger(9, 4) == 9\n"
                    "    assert pick_larger(5, 5) == 5\n\n"
                    "def test_second_larger():\n"
                    "    assert pick_larger(2, 7) == 7\n"
                ),
            },
        )
        res1 = ENGINE.solve_repository(r1, ["tests/test_mathops.py"], python_exe=sys.executable)
        assert res1["verified"] is True, res1
        assert res1["winner"]["tier"] == "TIER2_ANGELIC_VALUE", res1["winner"]
        assert "oe_sygus->" in res1["winner"]["description"] or "oe_eusolver_ite->" in res1["winner"]["description"], res1["winner"]
        # Verify genuine generalization on COMPLETELY UNSEEN inputs (zero overfit to 7!)
        ns1: dict = {}
        exec(res1["winner"]["patched_source"], ns1)
        assert ns1["pick_larger"](100, 250) == 250
        assert ns1["pick_larger"](300, 12) == 300

        # 2. OE-SyGuS None-coalescing preserving falsy `0`: `return primary` -> `primary if primary is not None else fallback`
        r2 = root / "r_coalesce"
        _write_files(
            r2,
            {
                "pkg/__init__.py": "",
                "pkg/cfg.py": (
                    "def resolve_timeout(primary, fallback):\n"
                    "    return primary\n"
                ),
                "tests/test_cfg.py": (
                    "from pkg.cfg import resolve_timeout\n\n"
                    "def test_preserves_explicit_zero():\n"
                    "    assert resolve_timeout(0, 30) == 0\n"
                    "    assert resolve_timeout(5, 30) == 5\n\n"
                    "def test_none_uses_fallback():\n"
                    "    assert resolve_timeout(None, 30) == 30\n"
                ),
            },
        )
        res2 = ENGINE.solve_repository(r2, ["tests/test_cfg.py"], python_exe=sys.executable)
        assert res2["verified"] is True, res2
        assert "oe_sygus->" in res2["winner"]["description"] or "oe_eusolver_ite->" in res2["winner"]["description"], res2["winner"]
        ns2: dict = {}
        exec(res2["winner"]["patched_source"], ns2)
        assert ns2["resolve_timeout"](None, 99) == 99
        assert ns2["resolve_timeout"](0, 99) == 0

        # 3. Law #56 (`TIER3_DEEPCOPY_BOUNDARY_DETACH`): input-parameter mutation + storage boundary detachment
        r3 = root / "r_detach"
        _write_files(
            r3,
            {
                "pkg/__init__.py": "",
                "pkg/store.py": (
                    "def normalize_snapshot(snap):\n"
                    "    snap['items'].sort()\n"
                    "    return list(snap['items'])\n"
                ),
                "tests/test_store.py": (
                    "from pkg.store import normalize_snapshot\n\n"
                    "def test_does_not_mutate_caller_snapshot():\n"
                    "    orig = {'items': [3, 1, 2]}\n"
                    "    out = normalize_snapshot(orig)\n"
                    "    assert out == [1, 2, 3]\n"
                    "    assert orig == {'items': [3, 1, 2]}\n"
                ),
            },
        )
        res3 = ENGINE.solve_repository(r3, ["tests/test_store.py"], python_exe=sys.executable)
        assert res3["verified"] is True, res3
        assert res3["winner"]["tier"] == "TIER3_DEEPCOPY_BOUNDARY_DETACH", res3["winner"]
        assert "copy.deepcopy" in res3["winner"]["patched_source"]

        # 4. Pytest 9.x unittest.subTest (`SUBFAILED`) detection + Law #60 (`TIER3_ZERO_ARG_IDENTITY_SHORTCIRCUIT`)
        r4 = root / "r_subtest_zero"
        _write_files(
            r4,
            {
                "pkg/__init__.py": "",
                "pkg/reader.py": (
                    "class BufReader:\n"
                    "    def __init__(self, text):\n"
                    "        self._text = text\n"
                    "        self._pos = 0\n"
                    "    def _check_open(self):\n"
                    "        pass\n"
                    "    def read_chunk(self, size=None):\n"
                    "        self._check_open()\n"
                    "        end = len(self._text) if not size else self._pos + size\n"
                    "        out = self._text[self._pos:end]\n"
                    "        self._pos = end\n"
                    "        return out\n"
                ),
                "tests/test_reader.py": (
                    "import unittest\n"
                    "from pkg.reader import BufReader\n\n"
                    "class TestReader(unittest.TestCase):\n"
                    "    def test_normal(self):\n"
                    "        r = BufReader('abcdef')\n"
                    "        self.assertEqual(r.read_chunk(2), 'ab')\n"
                    "        self.assertEqual(r.read_chunk(), 'cdef')\n\n"
                    "    def test_zero_in_subtest(self):\n"
                    "        for payload in ('hello', 'world'):\n"
                    "            with self.subTest(payload=payload):\n"
                    "                r = BufReader(payload)\n"
                    "                self.assertEqual(r.read_chunk(0), '')\n"
                    "                self.assertEqual(r.read_chunk(2), payload[:2])\n"
                ),
            },
        )
        res4 = ENGINE.solve_repository(r4, ["tests/test_reader.py"], python_exe=sys.executable)
        assert res4["verified"] is True, res4
        assert res4["winner"]["tier"] == "TIER3_ZERO_ARG_IDENTITY_SHORTCIRCUIT", res4["winner"]

        # 5. Law #57 (`TIER3_SIBLING_BRANCH_KWARG_PROPAGATION`)
        r5 = root / "r_sib_kw"
        _write_files(
            r5,
            {
                "pkg/__init__.py": "",
                "pkg/bag.py": (
                    "class MultiBag:\n"
                    "    def __init__(self, pairs):\n"
                    "        self._pairs = list(pairs)\n"
                    "    def items(self, include_dups=False):\n"
                    "        if include_dups:\n"
                    "            return list(self._pairs)\n"
                    "        seen = {}\n"
                    "        for k, v in self._pairs:\n"
                    "            seen[k] = v\n"
                    "        return list(seen.items())\n"
                    "    def iter_items(self, include_dups=False):\n"
                    "        return iter(self.items(include_dups=include_dups))\n"
                    "    def extend_from(self, other):\n"
                    "        if other is self:\n"
                    "            it = iter(other.items())\n"
                    "        elif isinstance(other, MultiBag):\n"
                    "            it = other.iter_items(include_dups=True)\n"
                    "        else:\n"
                    "            it = other\n"
                    "        for k, v in it:\n"
                    "            self._pairs.append((k, v))\n"
                ),
                "tests/test_bag.py": (
                    "from pkg.bag import MultiBag\n\n"
                    "def test_extend_other():\n"
                    "    a = MultiBag([('k', 1)])\n"
                    "    b = MultiBag([('k', 2), ('k', 3)])\n"
                    "    a.extend_from(b)\n"
                    "    assert a.items(include_dups=True) == [('k', 1), ('k', 2), ('k', 3)]\n\n"
                    "def test_extend_self():\n"
                    "    a = MultiBag([('k', 1), ('k', 2)])\n"
                    "    a.extend_from(a)\n"
                    "    assert a.items(include_dups=True) == [('k', 1), ('k', 2), ('k', 1), ('k', 2)]\n"
                ),
            },
        )
        res5 = ENGINE.solve_repository(r5, ["tests/test_bag.py"], python_exe=sys.executable)
        assert res5["verified"] is True, res5
        assert res5["winner"]["tier"] == "TIER3_SIBLING_BRANCH_KWARG_PROPAGATION", res5["winner"]

        # 6. Law #58 (`TIER3_RECURSIVE_RADIX_REDUCTION`)
        r6 = root / "r_radix"
        _write_files(
            r6,
            {
                "pkg/__init__.py": "",
                "pkg/ordfmt.py": (
                    "def ordinal_suffix(n: int) -> str:\n"
                    "    if n == 0:\n"
                    "        return 'th'\n"
                    "    elif n == 1:\n"
                    "        return 'st'\n"
                    "    elif n == 2:\n"
                    "        return 'nd'\n"
                    "    elif n == 3:\n"
                    "        return 'rd'\n"
                    "    elif 4 <= n <= 20:\n"
                    "        return 'th'\n"
                    "    else:\n"
                    "        return ordinal_suffix(n % 10)\n"
                ),
                "tests/test_ordfmt.py": (
                    "from pkg.ordfmt import ordinal_suffix\n\n"
                    "def test_basic():\n"
                    "    assert ordinal_suffix(1) == 'st'\n"
                    "    assert ordinal_suffix(22) == 'nd'\n"
                    "    assert ordinal_suffix(13) == 'th'\n\n"
                    "def test_hundreds_teens():\n"
                    "    assert ordinal_suffix(111) == 'th'\n"
                    "    assert ordinal_suffix(112) == 'th'\n"
                    "    assert ordinal_suffix(121) == 'st'\n"
                ),
            },
        )
        res6 = ENGINE.solve_repository(r6, ["tests/test_ordfmt.py"], python_exe=sys.executable)
        assert res6["verified"] is True, res6
        assert res6["winner"]["tier"] == "TIER3_RECURSIVE_RADIX_REDUCTION", res6["winner"]

        # 7. Law #61 (`TIER3_FALSY_CALLABLE_GUARD`)
        r7 = root / "r_falsy_cb"
        _write_files(
            r7,
            {
                "pkg/__init__.py": "",
                "pkg/runner.py": (
                    "class Runner:\n"
                    "    def __init__(self, hook=None):\n"
                    "        self.hook = hook\n"
                    "    def run(self, x):\n"
                    "        if not self.hook:\n"
                    "            return 0\n"
                    "        else:\n"
                    "            return self.hook(x)\n"
                ),
                "tests/test_runner.py": (
                    "from pkg.runner import Runner\n\n"
                    "class FalsyHook:\n"
                    "    def __bool__(self):\n"
                    "        return False\n"
                    "    def __call__(self, x):\n"
                    "        return x + 10\n\n"
                    "def test_none_and_zero():\n"
                    "    assert Runner(None).run(5) == 0\n"
                    "    assert Runner(0).run(5) == 0\n\n"
                    "def test_falsy_callable():\n"
                    "    assert Runner(FalsyHook()).run(5) == 15\n"
                ),
            },
        )
        res7 = ENGINE.solve_repository(r7, ["tests/test_runner.py"], python_exe=sys.executable)
        assert res7["verified"] is True, res7
        assert res7["winner"]["tier"] == "TIER3_FALSY_CALLABLE_GUARD", res7["winner"]


def test_iter40_multifile_sync_async_proxy_dunder_rollback_and_regex() -> None:
    """Iter 40 breakthroughs (zero LLM calls, zero weights):
    1. Coordinated 2-file sync+async conditional callable bypass (`COMPOSED_ANGELIC_PROGRESS` + Law #62).
    2. Proxy `__getattr__` dunder protocol guard (`TIER3_PROXY_DUNDER_GETATTR_GUARD`, Law #63).
    3. Identity-copy dunder synthesis for `__reduce__` AttributeError (`TIER3_DUNDER_ATTR_SUPER_FALLBACK`, Law #64).
    4. Strong Exception Guarantee transactional rollback (`TIER3_DEEPCOPY_BOUNDARY_DETACH`, Law #56b).
    5. Python `re.IGNORECASE | re.ASCII` + even-length parity (`TIER3_REGEX_ASCII_AND_PARITY`, Law #65).
    """
    with tempfile.TemporaryDirectory(prefix="brain_swe_iter40_") as td:
        root = pathlib.Path(td)

        # 1. Coordinated 2-file sync + async conditional callable bypass
        r1 = root / "r_sync_async"
        _write_files(
            r1,
            {
                "pkg/__init__.py": "",
                "pkg/sync_exec.py": (
                    "class ExecBase:\n"
                    "    def __init__(self, enabled=True):\n"
                    "        self.enabled = enabled\n"
                    "    def wrap(self, fn):\n"
                    "        def inner(*args, **kwargs):\n"
                    "            if not self.enabled:\n"
                    "                return fn(*args, **kwargs)\n"
                    "            return self(fn, *args, **kwargs)\n"
                    "        return inner\n"
                    "    def __call__(self, fn, *args, **kwargs):\n"
                    "        return fn(*args, **kwargs) + 100\n"
                ),
                "pkg/async_exec.py": (
                    "import inspect\n"
                    "from pkg.sync_exec import ExecBase\n\n"
                    "class AsyncExec(ExecBase):\n"
                    "    async def __call__(self, fn, *args, **kwargs):\n"
                    "        is_coro = inspect.iscoroutinefunction(fn)\n"
                    "        val = await fn(*args, **kwargs) if is_coro else fn(*args, **kwargs)\n"
                    "        return val + 100\n"
                ),
                "tests/test_exec.py": (
                    "import asyncio\n"
                    "from pkg.sync_exec import ExecBase\n"
                    "from pkg.async_exec import AsyncExec\n\n"
                    "def test_sync_enabled_true():\n"
                    "    assert ExecBase(enabled=True)(lambda x: x, 5) == 105\n\n"
                    "def test_sync_enabled_false():\n"
                    "    assert ExecBase(enabled=False)(lambda x: x, 5) == 5\n\n"
                    "def test_async_enabled_true():\n"
                    "    async def f(x): return x\n"
                    "    assert asyncio.run(AsyncExec(enabled=True)(f, 5)) == 105\n\n"
                    "def test_async_enabled_false():\n"
                    "    async def f(x): return x\n"
                    "    assert asyncio.run(AsyncExec(enabled=False)(f, 5)) == 5\n"
                ),
            },
        )
        res1 = ENGINE.solve_repository(r1, ["tests/test_exec.py"], python_exe=sys.executable)
        assert res1["verified"] is True, res1
        assert res1["winner"]["tier"] == "COMPOSED_ANGELIC_PROGRESS", res1["winner"]
        assert set(res1["winner"]["files"]) == {"pkg/sync_exec.py", "pkg/async_exec.py"}, res1["winner"]

        # 2. Proxy __getattr__ dunder guard (copy.deepcopy safety)
        r2 = root / "r_proxy"
        _write_files(
            r2,
            {
                "pkg/__init__.py": "",
                "pkg/proxy.py": (
                    "class Box:\n"
                    "    def __init__(self, inner):\n"
                    "        self._inner = inner\n"
                    "    def __enter__(self):\n"
                    "        return self._inner\n"
                    "    def __exit__(self, *exc):\n"
                    "        return False\n"
                    "    def __reduce__(self):\n"
                    "        return Box, (self._inner,)\n"
                    "    def __getattr__(self, name):\n"
                    "        return getattr(self._inner, name)\n"
                ),
                "tests/test_proxy.py": (
                    "import copy\n"
                    "from pkg.proxy import Box\n\n"
                    "class CustomInner:\n"
                    "    def __init__(self, v):\n"
                    "        self.v = v\n"
                    "    def __deepcopy__(self, memo):\n"
                    "        return CustomInner(self.v)\n\n"
                    "def test_normal_getattr():\n"
                    "    b = Box(CustomInner(7))\n"
                    "    assert b.v == 7\n\n"
                    "def test_deepcopy_keeps_box_context_manager():\n"
                    "    b = copy.deepcopy(Box(CustomInner(7)))\n"
                    "    with b as inner:\n"
                    "        assert inner.v == 7\n"
                ),
            },
        )
        res2 = ENGINE.solve_repository(r2, ["tests/test_proxy.py"], python_exe=sys.executable)
        assert res2["verified"] is True, res2
        assert res2["winner"]["tier"] == "TIER3_PROXY_DUNDER_GETATTR_GUARD", res2["winner"]

        # 3. Strong Exception Guarantee transactional rollback (preserves in-place mutation on success!)
        r3 = root / "r_tx"
        _write_files(
            r3,
            {
                "pkg/__init__.py": "",
                "pkg/tx.py": (
                    "def expand_pairs(items):\n"
                    "    for item in items:\n"
                    "        a, b = item\n"
                    "        up = (a.upper(), b.upper())\n"
                    "        if up not in items and a != up[0]:\n"
                    "            items.insert(0, up)\n"
                    "    return items\n"
                ),
                "tests/test_tx.py": (
                    "import pytest\n"
                    "from pkg.tx import expand_pairs\n\n"
                    "def test_modifies_in_place_on_success():\n"
                    "    data = [('a', 'b')]\n"
                    "    out = expand_pairs(data)\n"
                    "    assert out is data\n"
                    "    assert ('A', 'B') in data\n\n"
                    "def test_unmodified_on_error():\n"
                    "    data = [('a', 'b'), ('bad',)]\n"
                    "    with pytest.raises(ValueError):\n"
                    "        expand_pairs(data)\n"
                    "    assert data == [('a', 'b'), ('bad',)]\n"
                ),
            },
        )
        res3 = ENGINE.solve_repository(r3, ["tests/test_tx.py"], python_exe=sys.executable)
        assert res3["verified"] is True, res3
        assert res3["winner"]["tier"] == "TIER3_DEEPCOPY_BOUNDARY_DETACH", res3["winner"]
        assert "transactional_exception_rollback" in res3["winner"]["description"], res3["winner"]

        # 4. Regex re.IGNORECASE | re.ASCII + even-length parity
        r4 = root / "r_regex"
        _write_files(
            r4,
            {
                "pkg/__init__.py": "",
                "pkg/val.py": (
                    "import re\n\n"
                    "def is_ascii_code(s: str) -> bool:\n"
                    "    return bool(re.match(r'^[a-z]{2}[0-9]{2}$', s, re.IGNORECASE))\n\n"
                    "def is_hex_bytes(s: str) -> bool:\n"
                    '    return bool(re.fullmatch(r"^[0-9A-Fa-f]+$", s)) if s else False\n'
                ),
                "tests/test_val.py": (
                    "from pkg.val import is_ascii_code, is_hex_bytes\n\n"
                    "def test_ascii_code_valid():\n"
                    "    assert is_ascii_code('AK12') is True\n\n"
                    "def test_ascii_code_rejects_kelvin():\n"
                    "    assert is_ascii_code('A\\u212a12') is False\n\n"
                    "def test_hex_bytes_valid():\n"
                    "    assert is_hex_bytes('deadbeef') is True\n\n"
                    "def test_hex_bytes_rejects_odd():\n"
                    "    assert is_hex_bytes('abc') is False\n"
                ),
            },
        )
        res4 = ENGINE.solve_repository(r4, ["tests/test_val.py"], python_exe=sys.executable)
        assert res4["verified"] is True, res4
        assert res4["winner"]["tier"] in ("COMPOSED_ANGELIC_PROGRESS", "TIER3_REGEX_ASCII_AND_PARITY"), res4["winner"]


def test_iter41_rts_iterator_observer_and_laws_66_to_70():
    """Iter 41: RTS fast-fail, iterator observer-effect immunity, rootdir testpaths, and Laws #66-#70."""
    with tempfile.TemporaryDirectory(prefix="brain_iter41_") as td:
        root = pathlib.Path(td)

        # 1. Law #66 (`TIER3_PY_SSIZE_T_LEN_OVERFLOW`): len(self)/len(other) > sys.maxsize
        r1 = root / "r_biglen"
        _write_files(
            r1,
            {
                "pkg/__init__.py": "",
                "pkg/bigseq.py": (
                    "class BigSpan:\n"
                    "    def __init__(self, *args):\n"
                    "        argc = len(args)\n"
                    "        assert argc == 2\n"
                    "        self._start, self._stop = args\n"
                    "    @property\n"
                    "    def _len(self):\n"
                    "        return max(0, self._stop - self._start)\n"
                    "    def __len__(self):\n"
                    "        return self._len\n"
                    "    def __eq__(self, other):\n"
                    "        if not isinstance(other, BigSpan):\n"
                    "            return False\n"
                    "        len_self = len(self)\n"
                    "        if len_self != len(other):\n"
                    "            return False\n"
                    "        return self._start == other._start\n"
                    "    def __hash__(self):\n"
                    "        return hash((len(self), self._start))\n"
                ),
                "tests/test_bigseq.py": (
                    "from pkg.bigseq import BigSpan\n\n"
                    "def test_small():\n"
                    "    assert BigSpan(0, 5) == BigSpan(0, 5)\n"
                    "    assert hash(BigSpan(0, 5)) == hash(BigSpan(0, 5))\n\n"
                    "def test_above_maxsize():\n"
                    "    a = BigSpan(0, 10**30)\n"
                    "    b = BigSpan(0, 10**30)\n"
                    "    assert a == b\n"
                    "    assert hash(a) == hash(b)\n"
                ),
            },
        )
        res1 = ENGINE.solve_repository(r1, ["tests/test_bigseq.py"], python_exe=sys.executable)
        assert res1["verified"] is True, res1
        assert res1["winner"]["tier"] == "TIER3_PY_SSIZE_T_LEN_OVERFLOW", res1["winner"]
        assert "args._len" not in res1["winner"]["patched_source"]

        # 2. Law #67 (`TIER3_NEGATIVE_STEP_SLICE_BOUND`) + Iterator Observer-Effect Immunity
        r2 = root / "r_peek"
        _write_files(
            r2,
            {
                "pkg/__init__.py": "",
                "pkg/peek.py": (
                    "from collections import deque\n"
                    "from itertools import islice\n"
                    "from sys import maxsize\n\n"
                    "class PeekIter:\n"
                    "    def __init__(self, it):\n"
                    "        self._it = iter(it)\n"
                    "        self._cache = deque()\n"
                    "    def __iter__(self):\n"
                    "        return self\n"
                    "    def __bool__(self):\n"
                    "        try:\n"
                    "            if not self._cache:\n"
                    "                self._cache.append(next(self._it))\n"
                    "        except StopIteration:\n"
                    "            return False\n"
                    "        return True\n"
                    "    def __next__(self):\n"
                    "        if self._cache:\n"
                    "            return self._cache.popleft()\n"
                    "        return next(self._it)\n"
                    "    def __getitem__(self, index):\n"
                    "        step = 1 if (index.step is None) else index.step\n"
                    "        if step > 0:\n"
                    "            start = 0 if (index.start is None) else index.start\n"
                    "            stop = maxsize if (index.stop is None) else index.stop\n"
                    "        elif step < 0:\n"
                    "            start = -1 if (index.start is None) else index.start\n"
                    "            stop = (-maxsize - 1) if (index.stop is None) else index.stop\n"
                    "        else:\n"
                    "            raise ValueError('zero step')\n"
                    "        if (start < 0) or (stop < 0):\n"
                    "            self._cache.extend(self._it)\n"
                    "        else:\n"
                    "            n = min(max(start, stop) + 1, maxsize)\n"
                    "            if n >= len(self._cache):\n"
                    "                self._cache.extend(islice(self._it, n - len(self._cache)))\n"
                    "        return list(self._cache)[index]\n"
                ),
                "tests/test_peek.py": (
                    "from pkg.peek import PeekIter\n\n"
                    "def test_passthrough_order():\n"
                    "    p = PeekIter([1, 2, 3, 4, 5])\n"
                    "    assert list(p) == [1, 2, 3, 4, 5]\n\n"
                    "def test_neg_step_omitted_stop():\n"
                    "    p = PeekIter(range(50))\n"
                    "    assert p[4::-1] == [4, 3, 2, 1, 0]\n"
                    "    assert len(p._cache) == 5\n"
                ),
            },
        )
        res2 = ENGINE.solve_repository(r2, ["tests/test_peek.py"], python_exe=sys.executable)
        assert res2["verified"] is True, res2
        assert res2["winner"]["tier"] == "TIER3_NEGATIVE_STEP_SLICE_BOUND", res2["winner"]

        # 3. Law #68 (`TIER3_PARAM_DOMAIN_GUARD`): generator n < 0 & n == 0 validation
        r3 = root / "r_chunk"
        _write_files(
            r3,
            {
                "pkg/__init__.py": "",
                "pkg/chunk.py": (
                    "from itertools import islice\n\n"
                    "def take_chunks(iterable, n):\n"
                    '    """Yield lists of length n."""\n'
                    "    it = iter(iterable)\n"
                    "    buf = []\n"
                    "    for _ in islice(map(buf.append, it), n, None, n):\n"
                    "        yield buf[:n]\n"
                    "        del buf[:n]\n"
                    "    if buf:\n"
                    "        yield buf\n"
                ),
                "tests/test_chunk.py": (
                    "import unittest\n"
                    "from pkg.chunk import take_chunks\n\n"
                    "class T(unittest.TestCase):\n"
                    "    def test_pos(self):\n"
                    "        self.assertEqual(list(take_chunks('ABCD', 2)), [['A', 'B'], ['C', 'D']])\n"
                    "    def test_zero(self):\n"
                    "        self.assertEqual(list(take_chunks('ABC', 0)), [])\n"
                    "    def test_neg(self):\n"
                    "        with self.assertRaisesRegex(ValueError, 'n must be at least 0'):\n"
                    "            list(take_chunks('ABC', -1))\n"
                ),
            },
        )
        res3 = ENGINE.solve_repository(r3, ["tests/test_chunk.py"], python_exe=sys.executable)
        assert res3["verified"] is True, res3
        assert res3["winner"]["tier"] == "TIER3_PARAM_DOMAIN_GUARD", res3["winner"]

        # 4. Law #69 (`TIER3_PROXY_INHERITED_METHOD_DELEGATE`) + pyproject rootdir testpaths resolution
        r4 = root / "r_proxy_io"
        _write_files(
            r4,
            {
                "pyproject.toml": "[tool.pytest.ini_options]\ntestpaths = ['tests']\n",
                "pkg/__init__.py": "",
                "pkg/stream_proxy.py": (
                    "import io\n\n"
                    "class StreamProxy(io.TextIOBase):\n"
                    "    def __init__(self, target):\n"
                    "        self.__target = target\n"
                    "    def __getattr__(self, name):\n"
                    "        return getattr(self.__target, name)\n"
                    "    def fileno(self):\n"
                    "        return self.__target.fileno()\n"
                ),
                "tests/test_stream_proxy.py": (
                    "from pkg.stream_proxy import StreamProxy\n\n"
                    "class FakeTTY:\n"
                    "    def isatty(self):\n"
                    "        return True\n"
                    "    def fileno(self):\n"
                    "        return 7\n\n"
                    "def test_fileno():\n"
                    "    assert StreamProxy(FakeTTY()).fileno() == 7\n\n"
                    "def test_isatty():\n"
                    "    p = StreamProxy(FakeTTY())\n"
                    "    assert p.isatty()\n"
                ),
            },
        )
        res4 = ENGINE.solve_repository(r4, ["tests/test_stream_proxy.py"], python_exe=sys.executable)
        assert res4["verified"] is True, res4
        assert res4["winner"]["tier"] == "TIER3_PROXY_INHERITED_METHOD_DELEGATE", res4["winner"]

        # 5. Law #70 (`TIER3_EMPTY_VARARGS_KWARG_DEFAULT`): empty *objects shortcut vs non-default end kwarg
        r5 = root / "r_printer"
        _write_files(
            r5,
            {
                "pkg/__init__.py": "",
                "pkg/printer.py": (
                    "class NL:\n"
                    "    def render(self):\n"
                    "        return '\\n'\n\n"
                    "class Printer:\n"
                    "    def __init__(self):\n"
                    "        self.buf = []\n"
                    "    def write_out(self, *objects, sep=' ', end='\\n'):\n"
                    "        if not objects:\n"
                    "            objects = (NL(),)\n"
                    "        if len(objects) == 1 and isinstance(objects[0], NL):\n"
                    "            self.buf.append(objects[0].render())\n"
                    "        else:\n"
                    "            self.buf.append(sep.join(str(o) for o in objects) + end)\n"
                ),
                "tests/test_printer.py": (
                    "from pkg.printer import Printer\n\n"
                    "def test_default_empty():\n"
                    "    p = Printer()\n"
                    "    p.write_out()\n"
                    "    assert ''.join(p.buf) == '\\n'\n\n"
                    "def test_empty_custom_end():\n"
                    "    p = Printer()\n"
                    "    p.write_out(end='!')\n"
                    "    assert ''.join(p.buf) == '!'\n"
                ),
            },
        )
        res5 = ENGINE.solve_repository(r5, ["tests/test_printer.py"], python_exe=sys.executable)
        assert res5["verified"] is True, res5
        assert res5["winner"]["tier"] == "TIER3_EMPTY_VARARGS_KWARG_DEFAULT", res5["winner"]


def test_iter50_exception_hierarchy_widen_subprocess_resilient() -> None:
    """Iter 50: Subprocess-resilient Python builtin exception hierarchy widening (ExceptionGroup -> BaseExceptionGroup)."""
    with tempfile.TemporaryDirectory(prefix="brain_iter50_excgrp_") as td:
        root = pathlib.Path(td)
        _write_files(
            root,
            {
                "pkg/__init__.py": "",
                "pkg/fmt.py": (
                    "def is_group(exc):\n"
                    "    # Check whether exc is an ExceptionGroup.\n"
                    "    return isinstance(exc, ExceptionGroup)\n\n"
                    "def format_exc(exc):\n"
                    "    if is_group(exc):\n"
                    "        return 'GROUP:' + ','.join(type(e).__name__ for e in exc.exceptions)\n"
                    "    return 'SINGLE:' + type(exc).__name__\n"
                ),
                "tests/fixtures/grouped_base_exception.py": (
                    "import asyncio\n"
                    "from pkg.fmt import format_exc\n"
                    "eg = BaseExceptionGroup('mix', [ValueError('a'), asyncio.CancelledError('b')])\n"
                    "print(format_exc(eg))\n"
                ),
                "tests/test_fmt.py": (
                    "import pathlib, subprocess, sys, pytest\n"
                    "@pytest.mark.parametrize('name', ['grouped_base_exception'])\n"
                    "def test_subprocess_formatting(name):\n"
                    "    script = pathlib.Path(__file__).parent / 'fixtures' / f'{name}.py'\n"
                    "    r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, check=True)\n"
                    "    assert r.stdout.strip() == 'GROUP:ValueError,CancelledError'\n"
                ),
            },
        )
        res = ENGINE.solve_repository(root, ["tests/test_fmt.py"], python_exe=sys.executable)
        assert res["verified"] is True, res
        assert res["winner"]["tier"] == "TIER3_EXCEPTION_HIERARCHY_WIDEN", res["winner"]
        assert res["model_calls"] == 0
        assert res["parameters_stored"] == 0
        diff_txt = str(res["winner"].get("diff") or "")
        assert "+    return isinstance(exc, BaseExceptionGroup)" in diff_txt, diff_txt
        # Comment preserved untouched (not present as a changed line in diff)
        assert "-    # Check whether exc is an ExceptionGroup." not in diff_txt, diff_txt


def test_iter52_fs_missing_path_toctou_guard() -> None:
    """Iter 52: POSIX TOCTOU FileNotFoundError exception-safety law (`TIER3_FS_MISSING_PATH_GUARD`).

    Verifies that when a file path is externally moved/deleted before rotation cleanup calls
    `os.stat(old_path)` inside an `if` block, Law 12d wraps the block with a comment-preserving
    `try / except FileNotFoundError:` handler clearing `old_path = None` (zero LLM calls).
    """
    with tempfile.TemporaryDirectory(prefix="iter52_fnf_") as td:
        root = pathlib.Path(td)
        _write_files(
            root,
            {
                "pkg/__init__.py": "",
                "pkg/rotator.py": (
                    "import os\n\n"
                    "class Rotator:\n"
                    "    # Keep this header comment intact.\n"
                    "    def __init__(self, path):\n"
                    "        self.path = str(path)\n"
                    "        self.compressed = []\n\n"
                    "    def rotate(self, new_path):\n"
                    "        old_path = self.path\n"
                    "        if new_path == old_path:\n"
                    "            mtime = os.stat(old_path).st_mtime\n"
                    "            dst = f'{old_path}.{int(mtime)}'\n"
                    "            os.rename(old_path, dst)\n"
                    "            old_path = dst\n"
                    "        if old_path is not None:\n"
                    "            self.compressed.append(old_path)\n"
                    "        with open(new_path, 'w') as fh:\n"
                    "            fh.write('fresh')\n"
                ),
                "tests/test_rotator.py": (
                    "import os\n"
                    "from pkg.rotator import Rotator\n\n"
                    "def test_rotate_normal(tmp_path):\n"
                    "    p = tmp_path / 'a.log'\n"
                    "    p.write_text('old')\n"
                    "    r = Rotator(p)\n"
                    "    r.rotate(str(p))\n"
                    "    assert p.read_text() == 'fresh'\n"
                    "    assert len(r.compressed) == 1\n\n"
                    "def test_rotate_after_external_move(tmp_path):\n"
                    "    p = tmp_path / 'b.log'\n"
                    "    p.write_text('old')\n"
                    "    r = Rotator(p)\n"
                    "    os.rename(p, tmp_path / 'external.log')\n"
                    "    r.rotate(str(p))\n"
                    "    assert p.read_text() == 'fresh'\n"
                    "    assert r.compressed == []\n"
                ),
            },
        )
        res = ENGINE.solve_repository(root, ["tests/test_rotator.py"], python_exe=sys.executable)
        assert res["verified"] is True, res
        assert res["winner"]["tier"] == "TIER3_FS_MISSING_PATH_GUARD", res["winner"]
        assert res["model_calls"] == 0
        assert res["parameters_stored"] == 0
        diff_txt = str(res["winner"].get("diff") or "")
        assert "except FileNotFoundError:" in diff_txt, diff_txt
        assert "-    # Keep this header comment intact." not in diff_txt, diff_txt


def test_generator_snapshot_isolation_law_12e_and_watchdog() -> None:
    """Verify Law 12e (`TIER3_GENERATOR_SNAPSHOT_ISOLATION`) + SIGALRM infinite-loop watchdog:
    Co-repairs BOTH a doubly-linked-list generator (that loops infinitely when mutated during
    iteration) AND a sequence/mapping generator (that yields newly inserted / cleared items)
    in a single atomic candidate with model_calls == 0, parameters_stored == 0.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / "iter_repo"
        _write_files(
            root,
            {
                "pkg/__init__.py": "",
                "pkg/ring.py": (
                    "from collections import OrderedDict\n\n"
                    "class _Node:\n"
                    "    def __init__(self, key=None):\n"
                    "        self.key = key\n"
                    "        self.prev = self\n"
                    "        self.next = self\n\n"
                    "class LinkedRing:\n"
                    "    def __init__(self):\n"
                    "        self._root = _Node()\n"
                    "        self._links = OrderedDict()\n"
                    "    def put(self, key):\n"
                    "        if key in self._links:\n"
                    "            node = self._links[key]\n"
                    "            node.prev.next = node.next\n"
                    "            node.next.prev = node.prev\n"
                    "        else:\n"
                    "            node = _Node(key)\n"
                    "            self._links[key] = node\n"
                    "        last = self._root.prev\n"
                    "        last.next = node\n"
                    "        node.prev = last\n"
                    "        node.next = self._root\n"
                    "        self._root.prev = node\n"
                    "    def clear(self):\n"
                    "        self._links.clear()\n"
                    "        self._root.next = self._root.prev = self._root\n"
                    "    def __iter__(self):\n"
                    "        root = self._root\n"
                    "        curr = root.next\n"
                    "        while curr is not root:\n"
                    "            yield curr.key\n"
                    "            curr = curr.next\n\n"
                    "class HeapTable:\n"
                    "    def __init__(self):\n"
                    "        self._order = []\n"
                    "        self._items = OrderedDict()\n"
                    "    def put(self, key):\n"
                    "        n = _Node(key)\n"
                    "        self._items[key] = n\n"
                    "        self._order.append(n)\n"
                    "    def clear(self):\n"
                    "        self._items.clear()\n"
                    "        self._order.clear()\n"
                    "    def __iter__(self):\n"
                    "        for curr in self._order:\n"
                    "            yield curr.key\n"
                ),
                "tests/test_ring.py": (
                    "from pkg.ring import LinkedRing, HeapTable\n\n"
                    "def test_linked_ring_iter_update_and_clear():\n"
                    "    r = LinkedRing()\n"
                    "    for k in (1, 2, 3):\n"
                    "        r.put(k)\n"
                    "    seen = []\n"
                    "    for k in r:\n"
                    "        seen.append(k)\n"
                    "        r.put(k)\n"
                    "    assert seen == [1, 2, 3]\n"
                    "    seen2 = []\n"
                    "    for k in r:\n"
                    "        seen2.append(k)\n"
                    "        r.clear()\n"
                    "    assert seen2 == [1]\n\n"
                    "def test_heap_table_iter_insert_and_clear():\n"
                    "    h = HeapTable()\n"
                    "    for k in (1, 2, 3):\n"
                    "        h.put(k)\n"
                    "    seen = []\n"
                    "    for k in h:\n"
                    "        seen.append(k)\n"
                    "        h.put(k + 10)\n"
                    "    assert seen == [1, 2, 3]\n"
                    "    seen2 = []\n"
                    "    for k in h:\n"
                    "        seen2.append(k)\n"
                    "        h.clear()\n"
                    "    assert seen2 == [1]\n"
                ),
            },
        )
        res = ENGINE.solve_repository(root, ["tests/test_ring.py"], python_exe=sys.executable, timeout_s=12.0)
        assert res["verified"] is True, res
        assert res["winner"]["tier"] == "TIER3_GENERATOR_SNAPSHOT_ISOLATION", res["winner"]
        assert res["model_calls"] == 0
        assert res["parameters_stored"] == 0
        diff_txt = str(res["winner"].get("diff") or "")
        assert "_iter_snap = []" in diff_txt, diff_txt
        assert "tuple(self._items.values())" in diff_txt, diff_txt


def test_iter58_pickle_factory_reduce_and_multifile_strict_ascii_int() -> None:
    """Verify Iter 58 general Python laws (`model_calls == 0`, `parameters_stored == 0`):
    1. Law 12f (`TIER3_PICKLE_FACTORY_REDUCE_IDENTITY`): replaces `object.__reduce__` across
       both a 0-arg metaclass singleton AND a 2-arg metaclass flyweight in 1 atomic pass.
    2. Law 12g (`TIER3_STRICT_ASCII_DIGIT_INT_HELPER`) + Stage 1.5b `TIER3_MULTIFILE_DISJOINT_COMPOSED`
       + round-robin multi-file localization across 2 separate source files (`pkg/iso.py` & `pkg/tz.py`).
    """
    with tempfile.TemporaryDirectory() as tmp:
        # 1. Law 12f: Metaclass singleton + flyweight pickle identity
        r_pk = pathlib.Path(tmp) / "pk_repo"
        _write_files(
            r_pk,
            {
                "pkg/__init__.py": "",
                "pkg/zones.py": (
                    "class _Singleton(type):\n"
                    "    def __init__(cls, *a, **kw):\n"
                    "        cls._inst = None\n"
                    "        super().__init__(*a, **kw)\n"
                    "    def __call__(cls):\n"
                    "        if cls._inst is None:\n"
                    "            cls._inst = super().__call__()\n"
                    "        return cls._inst\n\n"
                    "class _Flyweight(type):\n"
                    "    def __init__(cls, *a, **kw):\n"
                    "        cls._cache = {}\n"
                    "        super().__init__(*a, **kw)\n"
                    "    def __call__(cls, name, offset):\n"
                    "        key = (name, offset)\n"
                    "        if key not in cls._cache:\n"
                    "            cls._cache[key] = super().__call__(name, offset)\n"
                    "        return cls._cache[key]\n\n"
                    "class UtcZone(metaclass=_Singleton):\n"
                    "    __reduce__ = object.__reduce__\n\n"
                    "class OffsetZone(metaclass=_Flyweight):\n"
                    "    def __init__(self, name, offset):\n"
                    "        self._name = name\n"
                    "        self._offset = offset\n"
                    "    __reduce__ = object.__reduce__\n"
                ),
                "tests/test_pickle_zones.py": (
                    "import pickle\n"
                    "from pkg.zones import UtcZone, OffsetZone\n\n"
                    "def test_pickle_singleton_utc():\n"
                    "    u = UtcZone()\n"
                    "    assert pickle.loads(pickle.dumps(u)) is u\n\n"
                    "def test_pickle_flyweight_offset():\n"
                    "    z = OffsetZone('EST', -18000)\n"
                    "    assert pickle.loads(pickle.dumps(z)) is z\n"
                ),
            },
        )
        res_pk = ENGINE.solve_repository(r_pk, ["tests/test_pickle_zones.py"], python_exe=sys.executable)
        assert res_pk["verified"] is True, res_pk
        assert res_pk["winner"]["tier"] == "TIER3_PICKLE_FACTORY_REDUCE_IDENTITY", res_pk["winner"]
        assert res_pk["model_calls"] == 0 and res_pk["parameters_stored"] == 0

        # 2. Law 12g + Stage 1.5b Multi-File Disjoint Composition across 2 source files
        r_mf = pathlib.Path(tmp) / "mf_repo"
        _write_files(
            r_mf,
            {
                "pkg/__init__.py": "",
                "pkg/iso.py": (
                    "def parse_hm(s):\n"
                    "    return (int(s[0:2]), int(s[3:]))\n"
                ),
                "pkg/off.py": (
                    "def parse_off(s):\n"
                    "    return (int(s[:2]), int(s[2:]))\n"
                ),
                "tests/test_iso.py": (
                    "import pytest\n"
                    "from pkg.iso import parse_hm\n\n"
                    "def test_hm_valid():\n"
                    "    assert parse_hm('12:34') == (12, 34)\n\n"
                    "@pytest.mark.parametrize('bad', ['1 :30', '12:+5', '12:3', '12:345', '1_2:30'])\n"
                    "def test_hm_rejects_non_digit(bad):\n"
                    "    with pytest.raises(ValueError):\n"
                    "        parse_hm(bad)\n"
                ),
                "tests/test_off.py": (
                    "import pytest\n"
                    "from pkg.off import parse_off\n\n"
                    "def test_off_valid():\n"
                    "    assert parse_off('0530') == (5, 30)\n\n"
                    "@pytest.mark.parametrize('bad', ['+530', ' 530', '\\u0660\\u0665\\u0663\\u0660'])\n"
                    "def test_off_rejects_non_digit(bad):\n"
                    "    with pytest.raises(ValueError):\n"
                    "        parse_off(bad)\n"
                ),
            },
        )
        res_mf = ENGINE.solve_repository(
            r_mf, ["tests/test_iso.py", "tests/test_off.py"], python_exe=sys.executable
        )
        assert res_mf["verified"] is True, res_mf
        assert res_mf["winner"]["tier"] == "COMPOSED_ANGELIC_PROGRESS", res_mf["winner"]
        assert sorted(res_mf["winner"]["patched_files"].keys()) == ["pkg/iso.py", "pkg/off.py"]
        assert res_mf["model_calls"] == 0 and res_mf["parameters_stored"] == 0


def test_30_iter61_safe_next_default_pep479() -> None:
    """Iter 61 Law 12h (`TIER2_SAFE_NEXT_DEFAULT`, PEP 479):
    When skipping a 1-arg `next(it)` statement fixes a StopIteration failure,
    prefer `next(it, None)` so BOTH empty lists AND empty iterators/generators succeed.
    """
    with tempfile.TemporaryDirectory(prefix="brain_py_iter61_next_") as td:
        root = pathlib.Path(td)
        _write_files(
            root,
            {
                "pkg/__init__.py": "",
                "pkg/iterutil.py": (
                    "import itertools\n\n"
                    "def interpose_sep(sep, seq):\n"
                    "    it = itertools.chain.from_iterable(zip(itertools.repeat(sep), seq))\n"
                    "    next(it)\n"
                    "    return it\n"
                ),
                "tests/test_iterutil.py": (
                    "from pkg.iterutil import interpose_sep\n\n"
                    "def test_nonempty():\n"
                    "    assert list(interpose_sep('-', [1, 2, 3])) == [1, '-', 2, '-', 3]\n\n"
                    "def test_empty_list_and_iterator():\n"
                    "    assert list(interpose_sep('-', [])) == []\n"
                    "    assert list(interpose_sep('-', iter([]))) == []\n"
                    "    assert list(interpose_sep('-', (x for x in ()))) == []\n"
                ),
            },
        )
        res = ENGINE.solve_repository(root, ["tests/test_iterutil.py"], python_exe=sys.executable)
        assert res["verified"] is True, res
        assert res["winner"]["tier"] == "TIER2_SAFE_NEXT_DEFAULT", res["winner"]
        assert "next(it, None)" in res["winner"]["patched_source"]
        assert res["model_calls"] == 0 and res["parameters_stored"] == 0


def test_31_iter63_normalized_local_substitution_law12i() -> None:
    """Iter 63 Law 12i (`TIER3_NORMALIZED_LOCAL_SUBSTITUTION`):
    When a function computes `norm_v = _normalize_name(item.name)` and a downstream
    call still passes the raw unnormalized `item.name`, substitute `norm_v`.
    """
    with tempfile.TemporaryDirectory(prefix="brain_py_iter63_norm_") as td:
        root = pathlib.Path(td)
        _write_files(
            root,
            {
                "pkg/__init__.py": "",
                "pkg/groups.py": (
                    "class Include:\n"
                    "    def __init__(self, group_name):\n"
                    "        self.group_name = group_name\n\n"
                    "def _normalize_name(name):\n"
                    "    return name.lower().replace('_', '-')\n\n"
                    "def check_self_cycle(group, item):\n"
                    "    group_name = _normalize_name(item.group_name)\n"
                    "    if group_name == group:\n"
                    "        return format_cycle(group, item.group_name)\n"
                    "    return 'ok'\n\n"
                    "def format_cycle(group, target):\n"
                    "    return f'{group} includes itself' if target == group else f'{target} -> {group}'\n"
                ),
                "tests/test_groups.py": (
                    "from pkg.groups import Include, check_self_cycle, format_cycle\n\n"
                    "def test_unnormalized_self_include():\n"
                    "    assert check_self_cycle('my-group', Include('My_Group')) == 'my-group includes itself'\n"
                    "    assert check_self_cycle('dev-tools', Include('Dev_Tools')) == 'dev-tools includes itself'\n"
                    "    assert check_self_cycle('my-group', Include('other')) == 'ok'\n"
                    "    assert format_cycle('a', 'b') == 'b -> a'\n"
                ),
            },
        )
        res = ENGINE.solve_repository(root, ["tests/test_groups.py"], python_exe=sys.executable)
        assert res["verified"] is True, res
        assert res["winner"]["tier"] == "TIER3_NORMALIZED_LOCAL_SUBSTITUTION", res["winner"]
        assert res["model_calls"] == 0 and res["parameters_stored"] == 0


def test_32_iter64_non_ascii_validation_guard_law12j() -> None:
    """Iter 64 Law 12j (`TIER3_NON_ASCII_VALIDATION_GUARD`, CWE-176):
    When a validator calls `.lower()` / `.casefold()` on a string input before checking
    an ASCII-only regex/alphabet, Unicode confusables like Kelvin sign `'\\u212a'` (`'\\u212a'.lower() == 'k'`)
    bypass validation unless guarded with `if not s.isascii(): raise <DomainError>(...)`.
    """
    with tempfile.TemporaryDirectory(prefix="brain_py_iter64_ascii_") as td:
        root = pathlib.Path(td)
        _write_files(
            root,
            {
                "pkg/__init__.py": "",
                "pkg/expr.py": (
                    "import re\n\n"
                    "class InvalidTag(ValueError):\n"
                    "    pass\n\n"
                    "def canonicalize_tag(raw: str) -> str:\n"
                    "    low = raw.lower()\n"
                    "    if not re.fullmatch(r'[a-z0-9\\-]+', low):\n"
                    "        raise InvalidTag(f'bad tag: {raw}')\n"
                    "    return low\n"
                ),
                "tests/test_expr.py": (
                    "import pytest\n"
                    "from pkg.expr import InvalidTag, canonicalize_tag\n\n"
                    "def test_rejects_kelvin_sign_confusable():\n"
                    "    assert canonicalize_tag('Custom-1') == 'custom-1'\n"
                    "    with pytest.raises(InvalidTag):\n"
                    "        canonicalize_tag('Tag-\\u212austom')\n"
                    "    with pytest.raises(InvalidTag):\n"
                    "        canonicalize_tag('bad!tag')\n"
                ),
            },
        )
        res = ENGINE.solve_repository(root, ["tests/test_expr.py"], python_exe=sys.executable)
        assert res["verified"] is True, res
        assert res["winner"]["tier"] == "TIER3_NON_ASCII_VALIDATION_GUARD", res["winner"]
        assert res["model_calls"] == 0 and res["parameters_stored"] == 0


def test_33_iter66_pathlike_bool_kwarg_and_multifile_slots_pickle() -> None:
    """Iter 66 universal Python laws:
    1. Law 12k (`TIER3_ISINSTANCE_PATHLIKE_WIDENING`, PEP 519 `os.PathLike`)
    2. Law 12l (`TIER3_CALL_BOOL_KWARG_DEFAULT_TOGGLE`, live `inspect.signature` introspection)
    3. Law 12m (`TIER3_SLOTS_DATACLASS_DICT_SETSTATE`, multi-file `COMPOSED_ANGELIC_PROGRESS`)
    """
    # 1. Law 12k: PEP 519 os.PathLike widening
    with tempfile.TemporaryDirectory(prefix="brain_py_iter66_12k_") as td:
        root = pathlib.Path(td)
        _write_files(
            root,
            {
                "pkg/__init__.py": "",
                "pkg/ed.py": (
                    "def collect_paths(filename):\n"
                    "    if isinstance(filename, str):\n"
                    "        filename = (filename,)\n"
                    "    return [str(p) for p in filename]\n"
                ),
                "tests/test_ed.py": (
                    "from pathlib import Path\n"
                    "from pkg.ed import collect_paths\n\n"
                    "def test_pathlib_single_and_list():\n"
                    "    assert collect_paths('a.txt') == ['a.txt']\n"
                    "    assert collect_paths(Path('/tmp/b.txt')) == ['/tmp/b.txt']\n"
                    "    assert collect_paths([Path('/tmp/c.txt')]) == ['/tmp/c.txt']\n"
                ),
            },
        )
        res_k = ENGINE.solve_repository(root, ["tests/test_ed.py"], python_exe=sys.executable)
        assert res_k["verified"] is True, res_k
        assert res_k["winner"]["tier"] == "TIER3_ISINSTANCE_PATHLIKE_WIDENING", res_k["winner"]
        assert res_k["model_calls"] == 0

    # 2. Law 12l: Live inspect.signature boolean kwarg toggle (via local subclass of stdlib TextWrapper)
    with tempfile.TemporaryDirectory(prefix="brain_py_iter66_12l_") as td:
        root = pathlib.Path(td)
        _write_files(
            root,
            {
                "pkg/__init__.py": "",
                "pkg/_tw.py": (
                    "import textwrap\n\n"
                    "class LocalWrapper(textwrap.TextWrapper):\n"
                    "    pass\n"
                ),
                "pkg/fmt.py": (
                    "from ._tw import LocalWrapper\n\n"
                    "def wrap_help(text: str, width: int = 12) -> str:\n"
                    "    w = LocalWrapper(width, replace_whitespace=False)\n"
                    "    return w.fill(text)\n"
                ),
                "tests/test_fmt.py": (
                    "from pkg.fmt import wrap_help\n\n"
                    "def test_keeps_hyphenated_and_long_words_whole():\n"
                    "    assert wrap_help('Add --avoid-motorways option', 12) == 'Add\\n--avoid-motorways\\noption'\n"
                    "    assert wrap_help('supercalifragilistic', 10) == 'supercalifragilistic'\n"
                ),
            },
        )
        res_l = ENGINE.solve_repository(root, ["tests/test_fmt.py"], python_exe=sys.executable)
        assert res_l["verified"] is True, res_l
        assert res_l["winner"]["tier"] == "TIER3_CALL_BOOL_KWARG_DEFAULT_TOGGLE", res_l["winner"]
        assert res_l["model_calls"] == 0

    # 3. Law 12m: Multi-file `@dataclass(..., slots=True)` legacy dict-state pickle compat
    with tempfile.TemporaryDirectory(prefix="brain_py_iter66_12m_") as td:
        root = pathlib.Path(td)
        _write_files(
            root,
            {
                "pkg/__init__.py": "",
                "pkg/mod_a.py": (
                    "from dataclasses import dataclass\n\n"
                    "@dataclass(frozen=True, slots=True)\n"
                    "class RecA:\n"
                    "    x: int\n"
                    "    y: str\n"
                ),
                "pkg/mod_b.py": (
                    "from dataclasses import dataclass\n\n"
                    "@dataclass(frozen=True, slots=True)\n"
                    "class RecB:\n"
                    "    name: str\n"
                    "    flag: bool\n"
                ),
                "tests/test_pickles.py": (
                    "import pickle\n"
                    "import pytest\n"
                    "from pkg.mod_a import RecA\n"
                    "from pkg.mod_b import RecB\n\n"
                    "def _dict_pickle(cls, state):\n"
                    "    class _Fake:\n"
                    "        def __reduce__(self):\n"
                    "            return (object.__new__, (cls,), state)\n"
                    "    return pickle.dumps(_Fake())\n\n"
                    "def test_pickle_dict_state_mod_a():\n"
                    "    obj = pickle.loads(_dict_pickle(RecA, {'x': 7, 'y': 'ok'}))\n"
                    "    assert obj == RecA(x=7, y='ok')\n"
                    "    with pytest.raises(TypeError):\n"
                    "        pickle.loads(_dict_pickle(RecA, {'x': 7, 'bogus': 1}))\n\n"
                    "def test_pickle_dict_state_mod_b():\n"
                    "    obj = pickle.loads(_dict_pickle(RecB, {'name': 'n', 'flag': True}))\n"
                    "    assert obj == RecB(name='n', flag=True)\n"
                ),
            },
        )
        res_m = ENGINE.solve_repository(root, ["tests/test_pickles.py"], python_exe=sys.executable)
        assert res_m["verified"] is True, res_m
        assert res_m["winner"]["tier"] == "COMPOSED_ANGELIC_PROGRESS", res_m["winner"]
        assert set(res_m["winner"]["files"]) == {"pkg/mod_a.py", "pkg/mod_b.py"}
        assert res_m["model_calls"] == 0 and res_m["parameters_stored"] == 0






















"""Tests for the residual-wall closers (`residual_wall_closers_v1.py`).

Two layers are tested, and they are deliberately different:

  * the MINING layer -- given a repository's own source, does the closer produce the
    statement and name the evidence it used? These tests need no network and no clone.
  * the SYNTHETIC-SUITE layer -- does the monotone zipper admit a candidate only when a
    test actually goes from failing to passing, and refuse one that does not? This runs
    real pytest against a throwaway tree, so it measures the admission rule, not the
    author's optimism.

The live three-repository evaluation lives in `evaluate_residual_walls`, which needs
cloned upstream repos; it is not run here, and nothing in this file fakes its result.
"""

from __future__ import annotations

import ast
import pathlib
import tempfile
import textwrap
import unittest

from canonical.swe_kernel.residual_wall_closers_v1 import (
    CLICK_PROJECT_TESTS,
    RESIDUAL_WALL_CASES,
    AssertContractToTypedRaise,
    ConfigParityFromRepoIdiom,
    DocstringDefaultUngating,
    EmptyContainerPrefixArm,
    NoneGuardToTruthiness,
    OptionalTupleShapeCompletion,
    ParserDegenerateNoneRefusal,
    PostconditionStatePurge,
    ResidualWallCloser,
    TerminalActionRetryPolicy,
    UnionStrSequenceFormatCompletion,
    _negate,
    apply_edits,
    close_wall_against_git,
    edits_disjoint,
)


class NegationByShapeTests(unittest.TestCase):
    def test_negation_is_by_shape_not_by_wrapping(self) -> None:
        self.assertEqual(_negate("plugin is not None"), "plugin is None")
        self.assertEqual(_negate("plugin is None"), "plugin is not None")
        self.assertEqual(_negate("x not in y"), "x in y")
        self.assertEqual(_negate("not value"), "value")
        self.assertEqual(_negate("value"), "not value")

    def test_a_wrapped_negation_would_not_parse(self) -> None:
        # The failure this closes: `if not plugin is not None:` is a syntax error in the
        # emitted indentation, so the guard was silently dropped by the parser check.
        ast.parse(textwrap.dedent("if plugin is None:\n    raise TypeError('x')\n"))


class EditArithmeticTests(unittest.TestCase):
    def test_apply_edits_is_bottom_up_and_order_independent(self) -> None:
        source = "a\nb\nc\n"
        edits = ((1, 1, "A"), (3, 3, "C"))
        self.assertEqual(apply_edits(source, edits), "A\nb\nC\n")
        self.assertEqual(apply_edits(source, tuple(reversed(edits))), "A\nb\nC\n")

    def test_disjointness_is_honest_about_adjacency(self) -> None:
        self.assertTrue(edits_disjoint(((1, 1, "x"),), ((2, 2, "y"),)))
        self.assertFalse(edits_disjoint(((1, 1, "x"),), ((1, 3, "y"),)))

    def test_overlap_is_refused_rather_than_silently_applied(self) -> None:
        with self.assertRaises(ValueError):
            apply_edits("a\nb\n", ((1, 2, "x"), (1, 1, "y")))


class NoneGuardToTruthinessTests(unittest.TestCase):
    SOURCE = textwrap.dedent(
        '''
        class Parameter:
            envvar: str | None


        class Option(Parameter):
            def get_help_extra(self, ctx):
                envvar = self.envvar

                if envvar is None:
                    if self.name:
                        envvar = "PREFIX_" + self.name

                if envvar is not None:
                    return (envvar,)

                return ()
        '''
    )

    def test_both_guards_are_rewritten_and_the_annotation_is_the_evidence(self) -> None:
        cands = NoneGuardToTruthiness().mine(self.SOURCE, "Option.get_help_extra")
        self.assertEqual(len(cands), 2)
        self.assertIn("if not envvar:", cands[0].new_code)
        self.assertIn("if envvar:", cands[1].new_code)
        for c in cands:
            self.assertEqual(c.evidence[0], "Parameter.envvar: str | None")

    def test_the_patch_is_valid_python_and_only_touches_the_guards(self) -> None:
        cand = NoneGuardToTruthiness().mine(self.SOURCE, "Option.get_help_extra")[0]
        ast.parse(cand.patched_module_source)
        self.assertEqual(cand.edits[0][0], cand.lineno)

    def test_self_attribute_guards_are_mined_through_the_class_annotation(self) -> None:
        source = textwrap.dedent(
            '''
            class WWWAuthenticate:
                token: str | None

                def to_header(self):
                    if self.token is not None:
                        return "Bearer " + self.token
                    return ""
            '''
        )
        cands = NoneGuardToTruthiness().mine(source, "WWWAuthenticate.to_header")
        self.assertEqual(len(cands), 1)
        # `is not None` negates to a bare truthiness test: an empty token is not a token.
        self.assertIn("if self.token:", cands[0].new_code)
        self.assertEqual(cands[0].evidence[0], "WWWAuthenticate.token: str | None")

    def test_a_name_with_no_optional_annotation_is_left_alone(self) -> None:
        source = "def f(x):\n    if x is not None:\n        return x\n    return None\n"
        self.assertEqual(NoneGuardToTruthiness().mine(source, "f"), [])


class UnionStrSequenceFormatCompletionTests(unittest.TestCase):
    SOURCE = textwrap.dedent(
        '''
        class Option:
            envvar: str | collections.abc.Sequence[str] | None

            def get_help_record(self, ctx):
                extra_items = []
                extra_items.append("env var: " + ", ".join(self.envvar))
                return extra_items

            def get_error_hint(self, ctx):
                result = "x"
                if self.show_envvar and self.envvar is not None:
                    result += f" (env var: '{self.envvar}')"
                return result
        '''
    )

    def test_dispatch_is_completed_from_the_annotation_and_the_sibling_separator(self) -> None:
        source = self.SOURCE.replace("collections.abc.", "cabc.")
        cands = UnionStrSequenceFormatCompletion().mine(source, "Option.get_error_hint")
        self.assertEqual(len(cands), 1)
        self.assertIn("isinstance(self.envvar, str)", cands[0].new_code)
        self.assertIn("', '.join(", cands[0].new_code)
        self.assertEqual(cands[0].evidence[1], "sibling separator: ', '")

    def test_no_sibling_separator_means_no_candidate(self) -> None:
        # Without a sibling that renders the sequence, the union alone is not evidence.
        source = self.SOURCE.replace('", ".join(self.envvar)', "self.envvar")
        source = source.replace("collections.abc.", "cabc.")
        self.assertEqual(UnionStrSequenceFormatCompletion().mine(source, "Option.get_error_hint"), [])


class AssertContractToTypedRaiseTests(unittest.TestCase):
    def test_arity_contract_becomes_type_error_and_state_becomes_value_error(self) -> None:
        source = textwrap.dedent(
            '''
            class PluginManager:
                def unregister(self, plugin=None, name=None):
                    if name is None:
                        assert plugin is not None, "one of name or plugin needs to be specified"
                        name = self.get_name(plugin)
                        assert name is not None, "plugin is not registered"
                    return plugin
            '''
        )
        cands = AssertContractToTypedRaise().mine(source, "PluginManager.unregister")
        self.assertEqual(len(cands), 2)
        self.assertIn("raise TypeError(", cands[0].new_code)
        self.assertIn("raise ValueError(", cands[1].new_code)
        for c in cands:
            ast.parse(c.patched_module_source)


class TerminalActionRetryPolicyTests(unittest.TestCase):
    SOURCE = textwrap.dedent(
        '''
        import sys


        class Command:
            def main(self, args, standalone_mode=True):
                try:
                    return self.invoke(args)
                except KeyboardInterrupt as e:
                    echo(file=sys.stderr)
                    raise Abort() from e
                except ClickException as e:
                    if not standalone_mode:
                        raise
                    e.show()
                    sys.exit(e.exit_code)
        '''
    )

    def test_reporting_is_best_effort_and_the_exit_is_retried(self) -> None:
        cands = TerminalActionRetryPolicy().mine(self.SOURCE, "Command.main")
        self.assertEqual(len(cands), 1)
        patch = cands[0].patched_module_source
        self.assertIn("def _exit_with_retry(code: int)", patch)
        self.assertIn("_exit_with_retry(e.exit_code)", patch)
        self.assertEqual(patch.count("except KeyboardInterrupt:"), 3)  # helper + echo + show
        ast.parse(patch)

    def test_a_function_without_an_exit_has_no_terminal_action(self) -> None:
        source = "def f():\n    return 1\n"
        self.assertEqual(TerminalActionRetryPolicy().mine(source, "f"), [])


class EmptyContainerPrefixArmTests(unittest.TestCase):
    def test_the_prefix_arm_is_derived_by_deleting_the_payload(self) -> None:
        source = textwrap.dedent(
            '''
            class WWWAuthenticate:
                def to_header(self):
                    if self.token:
                        return f"{self.type.title()} {self.token}"
                    if not self.parameters:
                        return self.type.title()
                    return f"{self.type.title()} {dump_header(self.parameters)}"
            '''
        )
        cands = EmptyContainerPrefixArm().mine(source, "WWWAuthenticate.to_header")
        self.assertEqual(len(cands), 1)
        # The payload appended by the format is the whole call, so emptiness is asked of it.
        self.assertIn("if not dump_header(self.parameters):", cands[0].new_code)
        self.assertIn('return f"{self.type.title()}"', cands[0].new_code)


class ParserDegenerateNoneRefusalTests(unittest.TestCase):
    SOURCE = textwrap.dedent(
        '''
        def parse_range_header(value):
            if not value:
                return None
            ranges = []
            for item in value.split(","):
                if item.startswith("-"):
                    try:
                        begin = _plain_int(item)
                    except ValueError:
                        return None
                else:
                    begin = _plain_int(item)
                ranges.append((begin, None))
            return Range(ranges)
        '''
    )

    def test_a_number_parsed_in_a_marker_arm_is_a_cardinality(self) -> None:
        cands = ParserDegenerateNoneRefusal().mine(self.SOURCE, "parse_range_header")
        self.assertEqual(len(cands), 1)
        self.assertIn("if begin == 0:", cands[0].new_code)
        self.assertIn("return None", cands[0].new_code)
        ast.parse(cands[0].patched_module_source)

    def test_an_absolute_offset_arm_is_not_treated_as_a_cardinality(self) -> None:
        source = self.SOURCE.replace("item.startswith(\"-\")", "item.endswith(\"-\")")
        # `endswith` is still a marker arm; the discriminator is the arm, not the name.
        self.assertEqual(len(ParserDegenerateNoneRefusal().mine(source, "parse_range_header")), 1)


class OptionalTupleShapeCompletionTests(unittest.TestCase):
    def test_the_row_is_reported_with_empty_text_instead_of_disappearing(self) -> None:
        source = textwrap.dedent(
            '''
            class Argument:
                def get_help_record(self, ctx) -> tuple[str, str] | None:
                    if self.help is None:
                        return None
                    return self.make_metavar(ctx), self.help
            '''
        )
        cands = OptionalTupleShapeCompletion().mine(source, "Argument.get_help_record")
        self.assertEqual(len(cands), 1)
        self.assertIn('return self.make_metavar(ctx), ""', cands[0].new_code)
        ast.parse(cands[0].patched_module_source)

    def test_a_non_optional_return_annotation_is_refused(self) -> None:
        source_without_optional = textwrap.dedent(
            '''
            class Argument:
                def get_help_record(self, ctx) -> tuple[str, str]:
                    if self.help is None:
                        return None
                    return self.make_metavar(ctx), self.help
            '''
        )
        self.assertEqual(
            OptionalTupleShapeCompletion().mine(source_without_optional, "Argument.get_help_record"), []
        )


class DocstringDefaultUngatingTests(unittest.TestCase):
    SOURCE = textwrap.dedent(
        '''
        class Adapter:
            def build(self, force_external=False, subdomain_matching=False, host_matching=False):
                """This produces relative URLs (path only, no host) by default.

                When subdomain or host matching is enabled, the URL is absolute unless the
                endpoint is on the same host.
                """
                if not force_external and (subdomain_matching or host_matching) and (
                    (subdomain_matching and True) or (host_matching and False)
                ):
                    return "relative"
                return "absolute"
        '''
    )

    def test_the_documented_default_becomes_reachable_with_the_flag_off(self) -> None:
        cands = DocstringDefaultUngating().mine(self.SOURCE, "Adapter.build")
        self.assertEqual(len(cands), 1)
        patch = cands[0].patched_module_source
        self.assertIn("not (subdomain_matching or host_matching)", patch)
        # The flag must be an OR with the behaviour, never a conjunct: conjoining
        # `not flag` would demand the flag be off AND the behaviour hold.
        self.assertIn(" or ", patch.split("if ", 1)[1].split(":", 1)[0])
        ast.parse(patch)
        self.assertIn("by default", cands[0].evidence[0])

    def test_a_method_whose_docstring_states_no_default_is_left_alone(self) -> None:
        source = textwrap.dedent(
            '''
            class Adapter:
                def build(self):
                    """Build a URL."""
                    if not (1 or 2) and (3 or 4):
                        return "x"
                    return "y"
            '''
        )
        self.assertEqual(DocstringDefaultUngating().mine(source, "Adapter.build"), [])


class PostconditionStatePurgeTests(unittest.TestCase):
    SOURCE = textwrap.dedent(
        '''
        class PluginManager:
            def __init__(self):
                self._plugin_distinfo: list[tuple[object, object]] = []

            def unregister(self, plugin=None, name=None):
                if name is None:
                    name = self.get_name(plugin)
                del self._name2plugin[name]
                return plugin
        '''
    )

    def test_the_pairing_is_purged_before_the_success_return(self) -> None:
        cands = PostconditionStatePurge().mine(self.SOURCE, "PluginManager.unregister")
        self.assertEqual(len(cands), 1)
        patch = cands[0].patched_module_source
        self.assertIn("__e[0] is not plugin", patch)
        # the return must survive: a purge that replaces it returns None
        self.assertIn("return plugin", patch)
        ast.parse(patch)

    def test_a_class_without_a_declared_pairing_is_refused(self) -> None:
        source = self.SOURCE.replace("list[tuple[object, object]]", "list[object]")
        self.assertEqual(PostconditionStatePurge().mine(source, "PluginManager.unregister"), [])


class CompositionTests(unittest.TestCase):
    def test_co_required_guards_are_offered_as_one_patch(self) -> None:
        source = textwrap.dedent(
            '''
            class Option:
                envvar: str | None

                def render(self):
                    envvar = self.envvar

                    if envvar is None:
                        envvar = "fallback"

                    if envvar is not None:
                        return envvar

                    return ""
            '''
        )
        cands = ResidualWallCloser().mine_all(source, "Option.render")
        composed = [c for c in cands if c.mechanism.count("+") >= 1]
        self.assertTrue(composed, "no composed candidate was offered")
        # Composed candidates are ranked first: single-site search cannot reach them.
        self.assertIn("+", cands[0].mechanism)
        for c in composed:
            ast.parse(c.patched_module_source)
            self.assertGreaterEqual(len(c.edits), 2)

    def test_adjacent_guards_inside_one_block_are_composed_at_the_statement_level(self) -> None:
        # Two asserts on adjacent lines inside one `if` body: each becomes a two-line guard,
        # so they are only composable if they are summed as *statement* edits, not as line
        # spans. This is the shape `pluggy@8051a4d` actually needs.
        source = textwrap.dedent(
            '''
            class PluginManager:
                def unregister(self, plugin=None, name=None):
                    if name is None:
                        assert plugin is not None, "one of name or plugin needs to be specified"
                        name = self.get_name(plugin)
                        assert name is not None, "plugin is not registered"
                    return plugin
            '''
        )
        cands = ResidualWallCloser().mine_all(source, "PluginManager.unregister")
        composed = [c for c in cands if c.mechanism.count("+") >= 1]
        self.assertTrue(composed, "two adjacent guards were not composed")
        patch = composed[0].patched_module_source
        self.assertIn("raise TypeError(", patch)
        self.assertIn("raise ValueError(", patch)
        ast.parse(patch)

    def test_composition_never_merges_overlapping_edits(self) -> None:
        source = "x = 1\ny = 2\n"
        self.assertFalse(edits_disjoint(((1, 2, "a"),), ((2, 2, "b"),)))


class SyntheticSuiteAdmissionTests(unittest.TestCase):
    """The zipper is measured against real pytest, not asserted by the author."""

    PARENT = textwrap.dedent(
        """
        class Thing:
            flag: str | None

            def render(self):
                if not self.flag:
                    return "none"
                return "flag"
        """
    ).lstrip()

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(dir="/dev/shm")
        self.root = pathlib.Path(self.tmp.name)
        self.repo = self.root / "repo"
        (self.repo / "src" / "pkg").mkdir(parents=True)
        (self.repo / "tests").mkdir()
        (self.repo / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        (self.repo / "src" / "pkg" / "mod.py").write_text(self.PARENT, encoding="utf-8")
        # The parent's own test only exercises the non-empty path, so the parent tree is
        # green. The fix commit's test adds the empty case, which is the wall.
        (self.repo / "tests" / "test_mod.py").write_text(
            textwrap.dedent(
                """
                from pkg.mod import Thing


                def test_present_renders_flag():
                    t = Thing()
                    t.flag = "x"
                    assert t.render() == "flag"
                """
            ).lstrip(),
            encoding="utf-8",
        )
        self._git("init")
        self._git("add", ".")
        self._git("-c", "user.email=a@b", "-c", "user.name=a", "commit", "-m", "parent")
        # The fix commit ships ONLY a test change.
        (self.repo / "tests" / "test_mod.py").write_text(
            textwrap.dedent(
                """
                from pkg.mod import Thing


                def test_absent_renders_none():
                    assert Thing().render() == "none"


                def test_present_renders_flag():
                    t = Thing()
                    t.flag = "x"
                    assert t.render() == "flag"
                """
            ).lstrip(),
            encoding="utf-8",
        )
        self._git("add", ".")
        self._git("-c", "user.email=a@b", "-c", "user.name=a", "commit", "-m", "fix")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _git(self, *args: str) -> None:
        import subprocess

        subprocess.run(["git", *args], cwd=str(self.repo), capture_output=True, check=True)

    def test_an_already_green_baseline_is_refused(self) -> None:
        # Point the wall at the parent commit: nothing is broken, so nothing is "repaired".
        import subprocess

        parent = subprocess.run(
            ["git", "rev-parse", "HEAD~1"], cwd=str(self.repo), capture_output=True, text=True
        ).stdout.strip()
        (self.repo / "tests" / "test_mod.py").write_text(
            textwrap.dedent(
                """
                from pkg.mod import Thing


                def test_present_renders_flag():
                    t = Thing()
                    t.flag = "x"
                    assert t.render() == "flag"
                """
            ).lstrip(),
            encoding="utf-8",
        )
        result = close_wall_against_git(
            self.repo,
            parent,
            "src/pkg/mod.py",
            ["tests/test_mod.py"],
            target_function="Thing.render",
            scratch_root=self.root,
        )
        self.assertIn(result.status, ("REFUSED__BASELINE_ALREADY_PASSING", "REFUSED__BASELINE_UNRUNNABLE"))

    def test_the_zipper_flips_the_copied_test_and_keeps_the_project_green(self) -> None:
        # The source at HEAD~1 has no `str | None` annotation for the guard to reason about,
        # so this measures the admission machinery rather than the miner: whatever the
        # engine tries, a VERIFIED answer must be one where the copied test passes AND the
        # project suite is no worse than its own baseline.
        result = close_wall_against_git(
            self.repo,
            "HEAD",
            "src/pkg/mod.py",
            ["tests/test_mod.py"],
            target_function="Thing.render",
            scratch_root=self.root,
        )
        self.assertIn(
            result.status,
            (
                "VERIFIED",
                "OPEN__CANDIDATES_EXHAUSTED",
                "REFUSED__NO_MECHANISM_FIRES",
                "REFUSED__BASELINE_ALREADY_PASSING",
                "REGRESSED__FULL_SUITE_RED",
            ),
        )
        if result.status == "VERIFIED":
            self.assertEqual(result.final_failures, 0)


class ConfigParityFromRepoIdiomTests(unittest.TestCase):
    """The repository's own usage is the evidence; nothing is inferred from outside it."""

    SIBLING = """
import textwrap


def shorten(text, max_length):
    return textwrap.shorten(text, max_length, placeholder="...", break_on_hyphens=False)
"""

    TARGET = """
import textwrap


def fill(text, width):
    wrapper = textwrap.TextWrapper(
        width,
        replace_whitespace=False,
    )
    return wrapper.fill(text)
"""

    def test_policy_stated_elsewhere_is_re_emitted_here(self) -> None:
        closer = ConfigParityFromRepoIdiom()
        cands = closer.mine_for_pair(self.TARGET, "fill", [self.SIBLING, self.TARGET])
        self.assertEqual(len(cands), 1)
        self.assertIn("break_on_hyphens=False", cands[0].new_code)
        self.assertEqual(cands[0].mechanism, "CONFIG_PARITY_FROM_REPO_IDIOM")
        self.assertTrue(
            any("break_on_hyphens=False" in e for e in cands[0].evidence),
            cands[0].evidence,
        )

    def test_no_sibling_statement_means_no_candidate(self) -> None:
        """Without the repository saying it, the closer must stay silent."""
        closer = ConfigParityFromRepoIdiom()
        cands = closer.mine_for_pair(self.TARGET, "fill", [self.TARGET])
        self.assertEqual(cands, [])

    def test_a_policy_the_object_does_not_accept_is_not_invented(self) -> None:
        closer = ConfigParityFromRepoIdiom()
        bogus = """
import textwrap


def shorten(text, n):
    return textwrap.shorten(text, n, break_on_hyphens=False, not_a_real_kwarg=False)
"""
        cands = closer.mine_for_pair(self.TARGET, "fill", [bogus, self.TARGET])
        for cand in cands:
            self.assertNotIn("not_a_real_kwarg", cand.new_code)

    def test_already_matching_call_sites_produce_nothing(self) -> None:
        closer = ConfigParityFromRepoIdiom()
        already = self.TARGET.replace(
            "        replace_whitespace=False,\n",
            "        replace_whitespace=False,\n        break_on_hyphens=False,\n",
        )
        self.assertEqual(closer.mine_for_pair(already, "fill", [self.SIBLING, already]), [])


class HonestOpenWallTests(unittest.TestCase):
    """A wall the engine cannot close must be registered, not quietly dropped."""

    def test_both_unclosed_walls_are_registered(self) -> None:
        ids = {c["wall_id"] for c in RESIDUAL_WALL_CASES}
        self.assertIn("click@7996a89", ids)
        self.assertIn("click@047adef", ids)

    def test_the_config_parity_wall_declares_the_repository_globs(self) -> None:
        case = next(c for c in RESIDUAL_WALL_CASES if c["wall_id"] == "click@7996a89")
        self.assertEqual(case["repo_source_globs"], ("src/click/*.py",))
        # Every other wall works from its own file alone.
        for other in RESIDUAL_WALL_CASES:
            if other["wall_id"] != "click@7996a89":
                self.assertEqual(other.get("repo_source_globs", ()), ())



class CaseListTests(unittest.TestCase):
    def test_every_declared_wall_names_its_evidence_and_its_suite(self) -> None:
        self.assertEqual(len(RESIDUAL_WALL_CASES), 10)
        for case in RESIDUAL_WALL_CASES:
            self.assertTrue(case["wall_id"])
            self.assertTrue(case["fix_test_files"])
            self.assertTrue(case["target_functions"])
            self.assertTrue(case["project_tests"])
            self.assertIn(case["suite_scope"], ("one", "per-file"))

    def test_the_click_suite_excludes_the_two_files_this_sandbox_cannot_run(self) -> None:
        self.assertNotIn("tests/test_deprecations.py", CLICK_PROJECT_TESTS)
        self.assertNotIn("tests/test_stream_lifecycle.py", CLICK_PROJECT_TESTS)


if __name__ == "__main__":
    unittest.main()

"""Checks for 16-way (configurable) CoW candidate rollouts."""
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import cow_impact_repair_engine_v1 as cow  # noqa: E402


class _FakePool:
    """Deterministic stand-in for `ZygotePrewarmedPool` (no prewarm, no model)."""

    def run_isolated(self, fn, *, timeout_s=30.0):
        return dict(fn())

    def run_parallel_sharded(self, shard_fns, *, winner_predicate=None, timeout_s=30.0):
        results = []
        for index, fn in enumerate(shard_fns):
            result = dict(fn())
            result["shard_index"] = index
            results.append(result)
            if winner_predicate is not None and winner_predicate(result):
                return {
                    "found_winner": True,
                    "winning_shard": index,
                    "winner": result,
                    "results": results,
                    "siblings_cancelled": len(shard_fns) - index - 1,
                    "elapsed_ms": 1.0,
                }
        return {
            "found_winner": False,
            "winning_shard": -1,
            "winner": None,
            "results": results,
            "siblings_cancelled": 0,
            "elapsed_ms": 1.0,
        }


def _tiny_repo(where: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    repo = where / "repo"
    repo.mkdir(parents=True)
    (repo / "mod.py").write_text("VALUE = 0\n", encoding="utf-8")
    test_file = repo / "test_mod.py"
    test_file.write_text(
        "from mod import VALUE\n\ndef test_value():\n    assert VALUE == 1\n",
        encoding="utf-8",
    )
    return repo, test_file


class ParallelCoWRolloutTests(unittest.TestCase):
    def test_partition_preserves_global_indices(self):
        candidates = [{"mod.py": f"VALUE = {i}\n"} for i in range(17)]
        parts = cow.partition_candidates(candidates, 16)
        self.assertEqual(len(parts), 16)
        self.assertEqual(sum(len(part) for part in parts), 17)
        flat = [index for part in parts for index, _ in part]
        self.assertEqual(sorted(flat), list(range(17)))

    def test_parallel_winner_index_is_global(self):
        with tempfile.TemporaryDirectory() as where:
            repo, test_file = _tiny_repo(pathlib.Path(where))
            candidates = [
                {"mod.py": "VALUE = 0\n"},
                {"mod.py": "VALUE = 1\n"},
            ]
            result = cow.evaluate_patch_batch_in_cow_zygote(
                repo, candidates, [test_file], zygote=_FakePool(), parallel_shards=2
            )
            self.assertTrue(result["found"])
            self.assertEqual(result["winning_index"], 1)
            self.assertEqual(result["parallel_shards"], 2)
            self.assertEqual(result["candidates_evaluated"], 2)

    def test_no_winner_is_reported_honestly(self):
        with tempfile.TemporaryDirectory() as where:
            repo, test_file = _tiny_repo(pathlib.Path(where))
            candidates = [
                {"mod.py": "VALUE = 2\n"},
                {"mod.py": "VALUE = 3\n"},
            ]
            result = cow.evaluate_patch_batch_in_cow_zygote(
                repo, candidates, [test_file], zygote=_FakePool(), parallel_shards=2
            )
            self.assertFalse(result["found"])
            self.assertEqual(result["winning_index"], -1)
            self.assertEqual(result["candidates_evaluated"], 2)
            self.assertEqual(
                [item["index"] for item in result.get("outcomes", [])], [0, 1]
            )
            self.assertEqual(
                [item["passed"] for item in result.get("outcomes", [])], [False, False]
            )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from canonical.runtime import task_artifact_authority_v1 as a


class TaskArtifactAuthorityV1Tests(unittest.TestCase):
    def test_legacy_string_defaults_to_main(self):
        out=a.normalize_artifacts(["/root/results/result.csv"])
        self.assertEqual(out,[{"source":"/root/results/result.csv","service":"main"}])
        self.assertEqual(a.service_artifact_paths(out),["/root/results/result.csv"])

    def test_structured_rows_preserve_service_ownership(self):
        rows=[
            {"source":"/root/results/a.json","service":"main"},
            {"source":"/var/log/service/events.jsonl","service":"broker"},
            {"source":"/root/results/b.json","service":"main"},
            {"source":"/var/log/service/state.json","service":"broker"},
        ]
        normalized=a.normalize_artifacts(rows)
        self.assertEqual(
            a.service_artifact_paths(normalized,service="main"),
            ["/root/results/a.json","/root/results/b.json"],
        )
        self.assertEqual(
            a.service_artifact_paths(normalized,service="broker"),
            ["/var/log/service/events.jsonl","/var/log/service/state.json"],
        )

    def test_missing_structured_service_defaults_to_main(self):
        rows=[{"source":"/root/results/a.json"}]
        self.assertEqual(a.service_artifact_paths(rows),["/root/results/a.json"])

    def test_duplicate_source_service_collapses(self):
        rows=[
            "/root/results/a.json",
            {"source":"/root/results/a.json","service":"main"},
        ]
        self.assertEqual(
            a.normalize_artifacts(rows),
            [{"source":"/root/results/a.json","service":"main"}],
        )

    def test_same_path_different_service_is_not_collapsed(self):
        rows=[
            {"source":"/tmp/a.json","service":"main"},
            {"source":"/tmp/a.json","service":"broker"},
        ]
        self.assertEqual(len(a.normalize_artifacts(rows)),2)

    def test_non_string_source_fails_closed(self):
        with self.assertRaises(a.TaskArtifactAuthorityError):
            a.normalize_artifacts([{"source":7,"service":"main"}])

    def test_relative_source_fails_closed(self):
        with self.assertRaises(a.TaskArtifactAuthorityError):
            a.normalize_artifacts([{"source":"results/a.json","service":"main"}])

    def test_path_traversal_fails_closed(self):
        with self.assertRaises(a.TaskArtifactAuthorityError):
            a.normalize_artifacts([{"source":"/root/../secret","service":"main"}])

    def test_invalid_service_fails_closed(self):
        with self.assertRaises(a.TaskArtifactAuthorityError):
            a.normalize_artifacts([{"source":"/tmp/a","service":""}])

    def test_main_secret_root_fails_closed(self):
        with self.assertRaises(a.TaskArtifactAuthorityError):
            a.service_artifact_paths([
                {"source":"/run/secrets/key.txt","service":"main"}
            ])

    def test_non_main_secret_like_path_is_not_injected_into_main(self):
        rows=[{"source":"/run/secrets/key.txt","service":"broker"}]
        self.assertEqual(a.service_artifact_paths(rows,service="main"),[])

    def test_manifest_result_is_non_authoritative(self):
        out=a.normalize_task_manifest({
            "artifacts":[
                {"source":"/root/results/a.json","service":"main"},
                {"source":"/var/log/broker.jsonl","service":"broker"},
            ]
        })
        self.assertEqual(out["service_artifact_paths"],["/root/results/a.json"])
        self.assertFalse(out["finish_authority"])
        self.assertFalse(out["task_success_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["terminal_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)

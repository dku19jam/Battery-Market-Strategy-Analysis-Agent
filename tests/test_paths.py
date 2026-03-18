import json
import tempfile
import unittest
from pathlib import Path


class PathsAndStorageTest(unittest.TestCase):
    def test_build_run_paths_and_write_artifacts(self) -> None:
        from battery_agent.storage.json_store import write_json, write_markdown
        from battery_agent.storage.paths import (
            artifact_path_for,
            build_run_paths,
            ensure_run_directories,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            run_paths = build_run_paths(Path(tmp_dir), "run-001")
            ensure_run_directories(run_paths)

            write_json(run_paths.metadata_dir / "meta.json", {"run_id": "run-001"})
            write_markdown(run_paths.root / "report.md", "# Report")
            retrieval_path = artifact_path_for(run_paths, "retrieval", "lg_retrieval")

            self.assertTrue(run_paths.root.exists())
            self.assertTrue(run_paths.logs_dir.exists())
            self.assertTrue(run_paths.metadata_dir.exists())
            self.assertTrue(run_paths.retrieval_dir.exists())
            self.assertEqual(
                json.loads((run_paths.metadata_dir / "meta.json").read_text(encoding="utf-8")),
                {"run_id": "run-001"},
            )
            self.assertEqual(
                (run_paths.root / "report.md").read_text(encoding="utf-8"),
                "# Report",
            )
            self.assertEqual(retrieval_path, run_paths.retrieval_dir / "lg_retrieval.json")

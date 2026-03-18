import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class LoggingUtilsTest(unittest.TestCase):
    def test_build_run_logger_writes_log_file(self) -> None:
        from battery_agent.logging_utils import build_run_logger

        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "run.log"
            logger = build_run_logger("battery-agent-test", log_path)
            logger.info("hello logger")

            self.assertTrue(log_path.exists())
            self.assertIn("hello logger", log_path.read_text(encoding="utf-8"))

    def test_log_retry_attempt_writes_retry_message(self) -> None:
        from battery_agent.logging_utils import build_run_logger, log_retry_attempt

        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "run.log"
            logger = build_run_logger("battery-agent-retry", log_path)

            log_retry_attempt(logger, stage="retrieval", attempt=2, reason="insufficient evidence")

            self.assertIn("retry stage=retrieval attempt=2", log_path.read_text(encoding="utf-8"))

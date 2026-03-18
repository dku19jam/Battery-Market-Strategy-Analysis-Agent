import io
import unittest
from contextlib import redirect_stdout


class CLITest(unittest.TestCase):
    def test_main_prints_stub_message(self) -> None:
        from battery_agent.cli import main

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        self.assertIn("battery-agent", stdout.getvalue())

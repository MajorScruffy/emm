import subprocess
import unittest
from unittest.mock import MagicMock, patch

from emm.core import EmmAgent


class TestUS4Tools(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_console = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_logger.console = self.mock_console
        self.agent = EmmAgent(
            db=self.mock_db,
            log=self.mock_logger,
            max_iterations=5,
            run_once=True
        )
        self.agent.worktree_manager = MagicMock()
        # Ensure runner uses the mock logger's log method
        from emm.runners import ToolRunner
        self.agent.runner = ToolRunner(log=self.mock_logger.log)

    @patch('subprocess.run')
    def test_run_shell_success(self, mock_run):
        """US4.1: Assert tool success and output capture."""
        mock_result = MagicMock()
        mock_result.stdout = "Successful output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # The agent uses self.runner (ToolRunner)
        output = self.agent.runner.run_shell(["test_cmd"])

        self.assertEqual(output, "Successful output")
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_run_shell_timeout(self, mock_run):
        """US4.2: Assert timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["test_cmd"], timeout=300)

        output = self.agent.runner.run_shell(["test_cmd"])

        self.assertEqual(output, "ERROR: Timeout")

    @patch('subprocess.run')
    def test_run_shell_exception(self, mock_run):
        """US4.3: Assert handling of missing executable or other errors."""
        mock_run.side_effect = FileNotFoundError(2, "No such file or directory")

        output = self.agent.runner.run_shell(["missing_cmd"])

        self.assertTrue(output.startswith("ERROR:"))

    @patch('emm.runners.ToolRunner.run_shell')
    def test_run_opencode_logic(self, mock_shell):
        """US4.4: Assert run_opencode uses the correct prompt file selection."""
        mock_shell.return_value = "Done"

        # Mock existence of prompt.md via Path.exists in the runners module
        with patch('emm.runners.Path.exists', return_value=True):
            self.agent.runner.run_opencode()

        # Verify it was called with stdin_str
        args, kwargs = mock_shell.call_args
        self.assertIn('stdin_str', kwargs)
        self.assertIsInstance(kwargs['stdin_str'], str)

if __name__ == "__main__":
    unittest.main()

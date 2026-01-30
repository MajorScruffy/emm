import unittest
import subprocess
from unittest.mock import MagicMock, patch
from pathlib import Path
from scripts.emm import EmmAgent

class TestUS4Tools(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        with patch('scripts.emm.EmmDatabase', return_value=self.mock_db):
            with patch('scripts.emm.Console'):
                with patch('scripts.emm.Path.mkdir'):
                    self.agent = EmmAgent(max_iterations=5)

    @patch('subprocess.run')
    def test_run_shell_success(self, mock_run):
        """US4.1: Assert tool success and output capture."""
        mock_result = MagicMock()
        mock_result.stdout = "Successful output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        output = self.agent._run_shell(["test_cmd"])
        
        self.assertEqual(output, "Successful output")
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_run_shell_timeout(self, mock_run):
        """US4.2: Assert timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["test_cmd"], timeout=300)
        
        output = self.agent._run_shell(["test_cmd"])
        
        self.assertEqual(output, "ERROR: Timeout")

    @patch('subprocess.run')
    def test_run_shell_exception(self, mock_run):
        """US4.3: Assert handling of missing executable or other errors."""
        mock_run.side_effect = FileNotFoundError(2, "No such file or directory")
        
        output = self.agent._run_shell(["missing_cmd"])
        
        self.assertTrue(output.startswith("ERROR:"))

    @patch.object(EmmAgent, '_run_shell')
    def test_run_opencode_logic(self, mock_shell):
        """US4.4: Assert _run_opencode uses the correct prompt file."""
        mock_shell.return_value = "Done"
        
        # Mock existence of prompt.md
        with patch('scripts.emm.Path.exists', return_value=True):
            self.agent._run_opencode()
            
        # Verify it was called with some Path object as stdin_file
        args, kwargs = mock_shell.call_args
        self.assertIn('stdin_file', kwargs)
        self.assertIsInstance(kwargs['stdin_file'], Path)

if __name__ == "__main__":
    unittest.main()

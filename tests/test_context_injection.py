
import unittest
from unittest.mock import MagicMock, patch

from emm.runners import ToolRunner


class TestContextInjection(unittest.TestCase):
    def setUp(self):
        self.logger = MagicMock()
        self.runner = ToolRunner(self.logger)

        # Mock task data
        self.task = {
            'task_id': 'US-999',
            'title': 'Test Logic',
            'description': 'Implement logic',
            'acceptance_criteria': ['Code compiles', 'Verified']
        }

    @patch('subprocess.run')
    @patch('emm.config.PROMPT_FILE')
    def test_context_injection(self, mock_prompt_file, mock_run):
        # Mock prompt file existence and content
        mock_prompt_file.exists.return_value = True
        mock_prompt_file.read_text.return_value = "SYSTEM PROMPT"

        # Mock subprocess result
        mock_run.return_value = MagicMock(stdout="Done", stderr="")

        # Run
        self.runner.run_opencode(self.task)

        # Verify
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        stdin_content = kwargs['input']

        # Check SYSTEM PROMPT is present
        self.assertIn("SYSTEM PROMPT", stdin_content)

        # Check TASK CONTEXT is present
        self.assertIn("--- CURRENT TASK: US-999 ---", stdin_content)
        self.assertIn("Test Logic", stdin_content)
        self.assertIn("Code compiles", stdin_content)

if __name__ == '__main__':
    unittest.main()

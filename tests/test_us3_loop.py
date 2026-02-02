import unittest
from unittest.mock import MagicMock, patch

from emm.core import EmmAgent


class TestUS3Loop(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_console = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_logger.console = self.mock_console

        self.agent = EmmAgent(
            db=self.mock_db,
            log=self.mock_logger,
            max_iterations=5
        )
        self.agent.session_id = 123
        # Set runner for consistency
        from emm.runners import ToolRunner
        self.agent.runner = ToolRunner(log=self.mock_logger.log)

    @patch.object(EmmAgent, 'run_ai_tool')
    def test_run_iteration_success(self, mock_tool):
        """US3.1: Assert status transitions and success detection."""
        self.mock_db.get_next_task.return_value = {
            'task_id': '001', 'title': 'Test', 'status': 'pending'
        }
        self.mock_db.create_iteration.return_value = 1
        mock_tool.return_value = "Task done! <promise>COMPLETE</promise>"

        result = self.agent.run_iteration(1)

        self.assertTrue(result)
        self.mock_db.update_task_status.assert_any_call(123, '001', 'in_progress')
        self.mock_db.update_task_status.assert_any_call(123, '001', 'completed')
        self.mock_db.update_iteration.assert_called_once()

    @patch.object(EmmAgent, 'run_ai_tool')
    def test_run_iteration_no_completion(self, mock_tool):
        """US3.2: Assert status stays in_progress if no completion tag found."""
        self.mock_db.get_next_task.return_value = {
            'task_id': '001', 'title': 'Test', 'status': 'pending'
        }
        mock_tool.return_value = "Almost done, but not yet."

        result = self.agent.run_iteration(1)

        self.assertFalse(result)
        self.mock_db.update_task_status.assert_called_with(123, '001', 'in_progress')
        # Ensure 'completed' was NOT called
        for call in self.mock_db.update_task_status.call_args_list:
            self.assertNotEqual(call[0][2], 'completed')

    @patch.object(EmmAgent, 'run_iteration')
    def test_run_loop_max_iterations(self, mock_iter):
        """US3.3: Assert session marked as failed when max iterations reached."""
        mock_iter.return_value = False # Never completes

        with patch.object(self.agent, '_init_session'):
            with patch.object(self.agent, 'display_tasks_table'):
                result = self.agent.run()

        self.assertEqual(result, 1)
        self.mock_db.update_session_status.assert_called_with(123, 'failed')

    @patch.object(EmmAgent, 'run_iteration')
    def test_run_loop_interruption(self, mock_iter):
        """US3.4: Assert session marked as interrupted on KeyboardInterrupt."""
        mock_iter.side_effect = KeyboardInterrupt()

        with patch.object(self.agent, '_init_session'):
            with patch.object(self.agent, 'display_tasks_table'):
                result = self.agent.run()

        self.assertEqual(result, 130)
        self.mock_db.update_session_status.assert_called_with(123, 'interrupted')

if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from emm.core import EmmAgent


class TestWorktreeIntegration(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.log = MagicMock()
        self.db.claim_next_available_project.return_value = 123
        self.db.get_tasks.return_value = []  # Avoid table error

    @patch("emm.core.WorktreeManager")
    @patch("emm.core.ToolRunner")
    @patch("emm.core.config.PROJECTS_DIR")
    def test_worktree_creation_and_usage(
        self, mock_projects_dir, mock_runner, mock_manager
    ):
        mock_projects_dir.exists.return_value = False
        mock_manager_instance = mock_manager.return_value
        expected_path = Path(tempfile.mkdtemp())
        mock_manager_instance.create_worktree.return_value = expected_path
        mock_runner_instance = mock_runner.return_value

        # Init Agent
        agent = EmmAgent(self.db, self.log, run_once=True)
        self.db.claim_next_available_project.return_value = 123
        self.db.get_session.return_value = {"project_id": 1}
        self.db.get_project.return_value = {"content": '{"tasks":[]}'}
        agent._init_session()

        # Verify Worktree Creation
        mock_manager_instance.create_worktree.assert_called_with(123)
        self.assertEqual(agent.worktree_path, expected_path)

        # Verify Runner usage in run_ai_tool
        agent.run_ai_tool({"id": "1"})
        mock_runner_instance.run_opencode.assert_called_with(
            {"id": "1"}, cwd=expected_path
        )


if __name__ == "__main__":
    unittest.main()

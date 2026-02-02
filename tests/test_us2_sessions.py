import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from emm.core import EmmAgent

class TestUS2Sessions(unittest.TestCase):
    def setUp(self):
        # Mock the dependencies
        self.mock_db = MagicMock()
        self.mock_console = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_logger.console = self.mock_console
        
        # Initialize agent with injected mocks
        self.agent = EmmAgent(
            db=self.mock_db, 
            log=self.mock_logger,
            max_iterations=10
        )

    def test_fresh_session_start(self):
        """US2.1: Assert fresh session start via claiming."""
        self.mock_db.claim_next_available_project.return_value = 100
        self.mock_db.get_session.return_value = {'project_id': 1}
        self.mock_db.get_project.return_value = {'content': '{"tasks":[]}'}
        
        self.agent._init_session()
            
        self.assertEqual(self.agent.session_id, 100)
        self.mock_db.claim_next_available_project.assert_called_once()

    def test_session_resumption_success(self):
        """US2.2: Assert correct session ID is picked up when --resume is used."""
        self.agent.resume = True
        self.mock_db.get_last_session_id.return_value = 500
        self.mock_db.get_session.return_value = {'project_id': 1}
        self.mock_db.get_project.return_value = {'content': '{"tasks":[]}'}
        
        self.agent._init_session()
        
        self.assertEqual(self.agent.session_id, 500)
        self.mock_db.get_last_session_id.assert_called_with()
        self.mock_db.create_session.assert_not_called()

    def test_resume_exit_when_none_found(self):
        """US2.4: Assert exit when no previous session exists to resume."""
        self.agent.resume = True
        self.mock_db.get_last_session_id.return_value = None
        
        with self.assertRaises(SystemExit):
            self.agent._init_session()

    def test_no_work_found_exit(self):
        """US2.1: Assert exit when no unclaimed projects are found."""
        self.mock_db.claim_next_available_project.return_value = None
        
        with self.assertRaises(SystemExit):
            self.agent._init_session()

if __name__ == "__main__":
    unittest.main()

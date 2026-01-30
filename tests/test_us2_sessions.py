import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from emm.core import EmmAgent

class TestUS2Sessions(unittest.TestCase):
    def setUp(self):
        # Mock the dependencies
        self.mock_db = MagicMock()
        self.mock_console = MagicMock()
        
        # Initialize agent with injected mocks
        # We still might need to patch Path.mkdir if run() is called, 
        # but for _init_session we just need the mocks.
        self.agent = EmmAgent(
            db=self.mock_db, 
            console=self.mock_console, 
            max_iterations=10
        )

    def test_fresh_session_start(self):
        """US2.1: Assert fresh session start when no resume is requested."""
        self.mock_db.create_feature.return_value = 1
        self.mock_db.create_session.return_value = 100
        
        with patch.object(self.agent, '_ingest_feature_if_needed'):
            self.agent._init_session()
            
        self.assertEqual(self.agent.session_id, 100)
        self.mock_db.create_session.assert_called_once()

    def test_session_resumption_success(self):
        """US2.2: Assert correct session ID is picked up when --resume is used."""
        self.agent.resume = True
        self.mock_db.get_last_session_id.return_value = 500
        
        self.agent._init_session()
        
        self.assertEqual(self.agent.session_id, 500)
        self.mock_db.get_last_session_id.assert_called_with()
        self.mock_db.create_session.assert_not_called()

    def test_resume_fallback_when_none_found(self):
        """US2.4: Assert fresh start fallback when no previous session exists to resume."""
        self.agent.resume = True
        self.mock_db.get_last_session_id.return_value = None
        self.mock_db.create_session.return_value = 600
        
        with patch.object(self.agent, '_ingest_feature_if_needed'):
            self.agent._init_session()
            
        self.assertEqual(self.agent.session_id, 600)
        self.mock_db.create_session.assert_called_once()

    @patch('emm.core.FeatureParser.parse_json_feature')
    def test_task_ingestion_logic(self, mock_parse):
        """US2.1: Assert tasks are ingested if none exist for the session."""
        self.agent.session_id = 999
        self.mock_db.get_tasks.return_value = [] # DB is empty
        
        mock_parse.return_value = {
            "tasks": [
                {"id": "001", "title": "T1", "description": "D1"}
            ]
        }
        
        # Mocking existence of feature.json via Path.exists
        with patch('emm.core.Path.exists', return_value=True):
            self.agent._ingest_feature_if_needed()
            
        self.mock_db.create_task.assert_called_once()

if __name__ == "__main__":
    unittest.main()

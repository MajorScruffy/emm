
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from emm.core import EmmAgent
from emm.database import EmmDatabase
from emm.logger import DualLogger


class TestIngestionIntegration(unittest.TestCase):
    def setUp(self):
        # Create temp dirs
        self.test_dir = Path(tempfile.mkdtemp())
        self.projects_dir = self.test_dir / ".projects"
        self.projects_dir.mkdir()
        self.db_path = self.test_dir / "test.db"

        # Setup DB
        self.db = EmmDatabase(str(self.db_path))
        self.db.initialize_database()

        self.logger = MagicMock(spec=DualLogger)

        # Create a dummy project file
        self.project_file = self.projects_dir / "test_project.json"
        self.project_content = """
        {
            "project": "Test Project",
            "branchName": "emm/test-project",
            "description": "A test project",
            "tasks": [
                {
                    "id": "001", 
                    "title": "Task 1", 
                    "description": "Do something",
                    "acceptanceCriteria": ["Done"],
                    "priority": 1
                }
            ]
        }
        """
        self.project_file.write_text(self.project_content)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('emm.config.PROJECTS_DIR')
    def test_auto_ingestion_on_init(self, mock_projects_dir):
        # Mock the config.PROJECTS_DIR to point to our temp dir
        mock_projects_dir.exists.return_value = True
        mock_projects_dir.glob.side_effect = self.projects_dir.glob

        # Initialize Agent
        agent = EmmAgent(self.db, self.logger)
        agent._init_session() # This should trigger ingestion

        # Verify Project in DB
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM projects WHERE name = 'test_project'").fetchone()
            self.assertIsNotNone(row)
            project_id = row['id']

            # Verify Project Content matches
            self.assertIn("Test Project", row['content'])

            # Verify Session created for this project
            session_row = conn.execute("SELECT * FROM sessions WHERE project_id = ?", (project_id,)).fetchone()
            self.assertIsNotNone(session_row)
            self.assertEqual(session_row['project_id'], project_id)

            # Verify Agent claimed this session
            self.assertEqual(agent.session_id, session_row['id'])

    @patch('emm.config.PROJECTS_DIR')
    def test_idempotency(self, mock_projects_dir):
        # Mock config
        mock_projects_dir.exists.return_value = True
        mock_projects_dir.glob.side_effect = self.projects_dir.glob

        # First run
        agent1 = EmmAgent(self.db, self.logger)
        agent1._init_session()

        # Check Project ID
        with self.db.connection() as conn:
            pid1 = conn.execute("SELECT id FROM projects").fetchone()[0]

        # Second run (simulating restart)
        agent2 = EmmAgent(self.db, self.logger)
        # Should re-ingest but duplicate check should prevent new row
        agent2.ingest_pending_projects()

        with self.db.connection() as conn:
            pid2 = conn.execute("SELECT id FROM projects").fetchone()[0]
            count = conn.execute("SELECT count(*) FROM projects").fetchone()[0]

        self.assertEqual(pid1, pid2)
        self.assertEqual(count, 1)

if __name__ == '__main__':
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from emm.database import EmmDatabase


class TestUS1Ingestion(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_validation_logic(self):
        """US1.3: Assert we catch missing mandatory fields."""
        # Valid
        self.assertTrue(EmmDatabase.validate_project({"tasks": []}))

        # Missing 'tasks'
        self.assertFalse(EmmDatabase.validate_project({"only": "some", "junk": "data"}))

        # 'tasks' is not a list
        self.assertFalse(EmmDatabase.validate_project({"tasks": "not a list"}))

if __name__ == "__main__":
    unittest.main()

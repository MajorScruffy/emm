import unittest
import json
import tempfile
from pathlib import Path
from emm.parser import ProjectParser

class TestUS1Ingestion(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_valid_json_ingestion(self):
        """US1.1: Assert valid JSON parsing into dictionary."""
        project_data = {
            "project": "test-project",
            "branchName": "project/test",
            "tasks": [
                {"id": "001", "title": "First Task", "description": "Do something", "acceptanceCriteria": ["Done"]}
            ]
        }
        json_file = self.temp_path / "project.json"
        json_file.write_text(json.dumps(project_data))
        
        data = ProjectParser.parse_json_project(json_file)
        self.assertEqual(data["project"], "test-project")
        self.assertEqual(len(data["tasks"]), 1)
        self.assertEqual(data["tasks"][0]["id"], "001")

    def test_malformed_json_handling(self):
        """US1.2: Assert malformed JSON returns empty dict."""
        bad_json_file = self.temp_path / "bad.json"
        bad_json_file.write_text("{ 'invalid': json }") # Invalid JSON (single quotes, no quotes on keys)
        
        data = ProjectParser.parse_json_project(bad_json_file)
        self.assertEqual(data, {})

    def test_missing_file_handling(self):
        """US1.2: Assert missing file returns empty dict."""
        missing_file = self.temp_path / "missing.json"
        data = ProjectParser.parse_json_project(missing_file)
        self.assertEqual(data, {})

    def test_validation_logic(self):
        """US1.3: Assert we catch missing mandatory fields."""
        # Missing 'tasks'
        invalid_json_file = self.temp_path / "invalid.json"
        invalid_json_file.write_text(json.dumps({"only": "some", "junk": "data"}))
        
        data = ProjectParser.parse_json_project(invalid_json_file)
        self.assertEqual(data, {})

        # 'tasks' is not a list
        not_list_file = self.temp_path / "not_list.json"
        not_list_file.write_text(json.dumps({"tasks": "not a list"}))
        data = ProjectParser.parse_json_project(not_list_file)
        self.assertEqual(data, {})

if __name__ == "__main__":
    unittest.main()

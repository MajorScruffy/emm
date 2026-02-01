#!/usr/bin/env python3
import json
import re
from pathlib import Path
from typing import List, Dict

class ProjectParser:
    """Simplistic parser for loading JSON projects into the DB."""
    
    @staticmethod
    def parse_json_project(json_path: Path) -> Dict:
        """Parse tasks from an existing project.json or prd.json file."""
        if not json_path.exists():
            return {}
        try:
            data = json.loads(json_path.read_text())
            if ProjectParser.validate_json_project(data):
                return data
            return {}
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def validate_json_project(data: Dict) -> bool:
        """Validate that the project data has mandatory fields.
        
        Args:
            data: The parsed JSON dictionary.
            
        Returns:
            True if valid, False otherwise.
        """
        if not isinstance(data, dict):
            return False
        if "tasks" not in data or not isinstance(data["tasks"], list):
            return False
        return True

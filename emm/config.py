"""
Configuration constants and path management for Emm.
"""

from pathlib import Path

# Base Paths
PACKAGE_DIR = Path(__file__).parent.resolve()
ROOT_DIR = PACKAGE_DIR.parent
DATA_DIR = ROOT_DIR / "scripts" / "data"
ARCHIVE_DIR = ROOT_DIR / "scripts" / "archive"
MIGRATIONS_DIR = PACKAGE_DIR / "migrations"

import os
# Database
DB_NAME = "emm.db"
DB_PATH = Path(os.getenv("EMM_DB_PATH", DATA_DIR / DB_NAME))

# Tool Defaults
DEFAULT_TOOL = "opencode"
DEFAULT_ITERATIONS = 10
COMMAND_TIMEOUT = 300  # seconds

# UI/Signals
COMPLETION_TAG = "<promise>COMPLETE</promise>"

# Files
PROMPT_FILE = PACKAGE_DIR / "prompts" / "system.md"
PRD_FILE = ROOT_DIR / "scripts" / "prd.json"
PROJECTS_DIR = Path(os.getenv("EMM_PROJECTS_DIR", ROOT_DIR / ".projects"))

def ensure_dirs():
    """Ensure necessary directories exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

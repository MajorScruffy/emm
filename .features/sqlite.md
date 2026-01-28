# Feature: SQLite Integration for Emm Script

## Overview
Convert the emm script from file-based tracking to a comprehensive SQLite database management system. This will provide better auditing, session management, progress tracking, and learning capabilities.

## Current System Analysis

### Files That Remain External
- Original `.md` Feature files (initial input)
- Individual project code files

## Database Schema Design

### Core Tables

#### features
Feature file management
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `content` (TEXT NOT NULL) - Full Feature markdown content
- `hash` (TEXT NOT NULL) - SHA256 hash for change detection
- `name` (TEXT) - Feature name
- `created_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

#### sessions
Main sessions/runs table
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `feature_id` (INTEGER NOT NULL) - Foreign key to features
- `max_iterations` (INTEGER NOT NULL) - Maximum iterations allowed
- `tool` (TEXT DEFAULT 'opencode') - AI tool used
- `status` (TEXT DEFAULT 'running') - running, completed, failed, interrupted
- `created_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- `completed_at` (TIMESTAMP NULL)
- `total_iterations` (INTEGER DEFAULT 0)
- `total_tasks` (INTEGER DEFAULT 0)
- `completed_tasks` (INTEGER DEFAULT 0)

#### tasks
Tasks extracted from Feature (replaces hardcoded JSON array)
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `session_id` (INTEGER NOT NULL) - Foreign key to sessions
- `branch_name` (TEXT) - Git branch being worked on
- `task_id` (TEXT NOT NULL) - 001, 002, etc.
- `title` (TEXT NOT NULL) - Task title
- `description` (TEXT NOT NULL) - "As a [user], I want [feature] so that [benefit]"
- `acceptance_criteria` (TEXT NOT NULL) - JSON array of criteria
- `status` (TEXT DEFAULT 'pending') - pending, in_progress, completed, failed
- `started_at` (TIMESTAMP NULL)
- `completed_at` (TIMESTAMP NULL)
- `FOREIGN KEY (session_id) REFERENCES sessions(id)`

#### iterations
Iteration tracking table
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `session_id` (INTEGER NOT NULL) - Foreign key to sessions
- `iteration_number` (INTEGER NOT NULL) - Sequential iteration count
- `task_id_worked_on` (TEXT) - Which task was attempted this iteration
- `status` (TEXT DEFAULT 'running') - running, completed, failed, interrupted
- `started_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- `completed_at` (TIMESTAMP NULL)
- `opencode_output` (TEXT) - Full opencode response
- `opencode_stderr` (TEXT) - Error output if any
- `FOREIGN KEY (session_id) REFERENCES sessions(id)`

#### console_logs
Complete audit trail of all console activity
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `session_id` (INTEGER NOT NULL)
- `iteration_number` (INTEGER NULL)
- `log_level` (TEXT DEFAULT 'info') - info, warning, error, debug, success
- `component` (TEXT) - database, opencode, parser, ui, etc.
- `message` (TEXT NOT NULL) - Log message content
- `created_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- `FOREIGN KEY (session_id) REFERENCES sessions(id)`

## Implementation Plan

### Phase 1: Core Database & Basic Operations

#### Database Manager (`emm_database.py`)
```python
class EmmDatabase:
    def __init__(self, db_path: str)
    def initialize_database(self) -> None
    
    # Features (Create, Read)
    def create_feature(self, feature_path: str) -> int:
        """Read feature file, calculate hash, save to database, return feature_id."""
        pass
    
    def get_feature(self, feature_id: int) -> dict:
        """Retrieve feature by id."""
        pass

    # Sessions (Create, Read, Update)
    def create_session(self, feature_id: int, max_iterations: int) -> int:
        """Create new session with status='running', return session_id."""
        pass
    
    def get_session(self, session_id: int) -> dict:
        """Retrieve session by id."""
        pass
    
    def update_session_status(self, session_id: int, status: str) -> None:
        """Update session status and set completed_at if status is 'completed' or 'failed'."""
        pass
    
    # Tasks (Create, Read, Update)
    def create_task(self, session_id: int, task: dict) -> None:
        """Insert task into tasks table, convert acceptance_criteria to JSON."""
        pass
    
    def get_next_task(self, session_id: int) -> Optional[dict]:
        """Get first pending task for session, ordered by task_id."""
        pass
    
    def update_task_status(self, session_id: int, task_id: str, status: str) -> None:
        """Update task status, set started_at/completed_at timestamps as appropriate."""
        pass
    
    # Iterations (Create, Update)
    def create_iteration(self, session_id: int, iteration_number: int, task_id: str) -> int:
        """Create iteration record with status='running', return iteration_id."""
        pass
    
    def update_iteration(self, iteration_id: int, output: str, stderr: str) -> None:
        """Update iteration with output, stderr, set completed_at and status='completed'."""
        pass
    
    # Console Logs (Create)
    def log_message(self, session_id: int, iteration_number: int, level: str, component: str, message: str) -> None:
        """Insert log message into console_logs table."""
        pass
```

## File Structure

### Phase 1 (MVP)
```
scripts/
├── emm.py                    # Main script
├── emm_database.py           # All database operations
└── data/
    └── emm.db                # SQLite database file
```

### Phase 2+ (Future)
```
scripts/
├── emm.py
├── emm_database.py
├── feature_parser.py         # Feature parsing and task extraction
├── session_manager.py        # Session lifecycle management
├── progress_tracker.py       # Progress visualization (future)
└── data/
    └── emm.db
```

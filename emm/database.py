#!/usr/bin/env python3
"""
EmmDatabase - SQLite database management for emm script
Handles projects, sessions, tasks, iterations, and console logging
"""

import sqlite3
import hashlib
import json
import contextlib
from pathlib import Path
from typing import Optional, Dict, List, Any, Generator
from datetime import datetime
from emm.config import MIGRATIONS_DIR


class EmmDatabase:
    """Database manager for emm autonomous agent system"""
    
    def __init__(self, db_path: str):
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = db_path
        
    @contextlib.contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for SQLite database connections.
        
        Yields:
            A sqlite3.Connection object with foreign keys enabled and row_factory set.
        """
        # Create parent directory if it doesn't exist
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
            
    def initialize_database(self) -> None:
        """Create database schema via migrations."""
        self.run_migrations()
        
    def run_migrations(self) -> None:
        """Run pending SQL migrations."""
        if not MIGRATIONS_DIR.exists():
            print(f"Migrations directory not found: {MIGRATIONS_DIR}")
            return

        with self.connection() as conn:
            cursor = conn.cursor()
            
            # Ensure migration tracking table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_name TEXT UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Find and apply new migrations
            for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
                migration_name = sql_file.name
                
                # Check if applied
                cursor.execute(
                    "SELECT 1 FROM schema_migrations WHERE migration_name = ?", 
                    (migration_name,)
                )
                if cursor.fetchone():
                    continue
                    
                print(f"Applying migration: {migration_name}")
                
                # Apply migration
                try:
                    script = sql_file.read_text()
                    conn.executescript(script)
                    
                    cursor.execute(
                        "INSERT INTO schema_migrations (migration_name) VALUES (?)",
                        (migration_name,)
                    )
                except Exception as e:
                    print(f"Migration failed {migration_name}: {e}")
                    raise
            

    # --- Projects ---
 
    def create_project(self, project_path: str) -> int:
        """Read project file, calculate hash, and save to database.
        
        Args:
            project_path: Path to the project file.
            
        Returns:
            The project ID of the newly created or existing project.
        """
        path = Path(project_path)
        content = path.read_text()
        hash_value = hashlib.sha256(content.encode()).hexdigest()
        name = path.stem
        
        with self.connection() as conn:
            cursor = conn.cursor()
            
            # Check for existing project with same hash
            cursor.execute("SELECT id FROM projects WHERE hash = ?", (hash_value,))
            row = cursor.fetchone()
            if row:
                return row['id']

            cursor.execute(
                "INSERT INTO projects (content, hash, name) VALUES (?, ?, ?)",
                (content, hash_value, name)
            )
            return cursor.lastrowid
    
    def get_project(self, project_id: int) -> Dict[str, Any]:
        """Retrieve a project by ID.
        
        Args:
            project_id: The ID of the project to retrieve.
            
        Returns:
            A dictionary containing project data.
            
        Raises:
            ValueError: If the project ID is not found.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Project {project_id} not found")
            return dict(row)

    # --- Sessions ---

    def create_session(self, project_id: int, max_iterations: int) -> int:
        """Create a new agent session.
        
        Args:
            project_id: The ID of the project associated with this session.
            max_iterations: Maximum iterations allowed for this session.
            
        Returns:
            The newly created session ID.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (project_id, max_iterations) VALUES (?, ?)",
                (project_id, max_iterations)
            )
            return cursor.lastrowid
    
    def get_session(self, session_id: int) -> Dict[str, Any]:
        """Retrieve a session by ID.
        
        Args:
            session_id: The ID of the session to retrieve.
            
        Returns:
            A dictionary containing session data.
            
        Raises:
            ValueError: If the session ID is not found.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Session {session_id} not found")
            return dict(row)
    
    def get_last_session_id(self, status_not: str = 'completed') -> Optional[int]:
        """Get the ID of the most recent session that doesn't have the specified status.
        
        Args:
            status_not: Status to exclude (defaults to 'completed').
            
        Returns:
            The session ID or None if no matching session exists.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM sessions 
                WHERE status != ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (status_not,))
            row = cursor.fetchone()
            return row[0] if row else None
    
    def update_session_status(self, session_id: int, status: str) -> None:
        """Update the status of a session.
        
        Args:
            session_id: The ID of the session to update.
            status: The new status string.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            if status in ('completed', 'failed', 'interrupted'):
                cursor.execute(
                    "UPDATE sessions SET status = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, session_id)
                )
            else:
                cursor.execute(
                    "UPDATE sessions SET status = ? WHERE id = ?",
                    (status, session_id)
                )

    # --- Tasks ---

    def create_task(self, session_id: int, task_data: Dict[str, Any]) -> None:
        """Insert a task into the database.
        
        Args:
            session_id: The session ID this task belongs to.
            task_data: Dictionary containing task details (must have 'id', 'title', etc).
        """
        acceptance_criteria_json = json.dumps(task_data.get('acceptanceCriteria', []))
        
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (
                    session_id, branch_name, task_id, title, description, acceptance_criteria
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                task_data.get('branchName'),
                task_data['id'],
                task_data['title'],
                task_data['description'],
                acceptance_criteria_json
            ))
    
    def get_tasks(self, session_id: int) -> List[Dict[str, Any]]:
        """Retrieve all tasks for a specific session.
        
        Args:
            session_id: The session ID to query.
            
        Returns:
            A list of task dictionaries.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE session_id = ? 
                ORDER BY id ASC
            """, (session_id,))
            rows = cursor.fetchall()
            
            tasks = []
            for row in rows:
                task = dict(row)
                task['acceptance_criteria'] = json.loads(task['acceptance_criteria'])
                tasks.append(task)
            return tasks

    def get_next_task(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get the next pending task for a session.
        
        Args:
            session_id: The session ID to query.
            
        Returns:
            A task dictionary or None if no pending tasks exist.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE session_id = ? AND status = 'pending'
                ORDER BY id ASC
                LIMIT 1
            """, (session_id,))
            
            row = cursor.fetchone()
            if row is None:
                return None
            
            task = dict(row)
            task['acceptance_criteria'] = json.loads(task['acceptance_criteria'])
            return task
    
    def update_task_status(self, session_id: int, task_id: str, status: str) -> None:
        """Update the status and timestamps of a task.
        
        Args:
            session_id: The session ID the task belongs to.
            task_id: The string task ID (e.g. '001').
            status: The new status string.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            if status == 'in_progress':
                cursor.execute("""
                    UPDATE tasks 
                    SET status = ?, started_at = CURRENT_TIMESTAMP 
                    WHERE session_id = ? AND task_id = ?
                """, (status, session_id, task_id))
            elif status == 'completed':
                cursor.execute("""
                    UPDATE tasks 
                    SET status = ?, completed_at = CURRENT_TIMESTAMP 
                    WHERE session_id = ? AND task_id = ?
                """, (status, session_id, task_id))
            else:
                cursor.execute("""
                    UPDATE tasks 
                    SET status = ? 
                    WHERE session_id = ? AND task_id = ?
                """, (status, session_id, task_id))

    # --- Iterations ---

    def create_iteration(self, session_id: int, iteration_number: int, task_id: str) -> int:
        """Create an iteration record.
        
        Args:
            session_id: The session ID.
            iteration_number: The sequential iteration number.
            task_id: The task ID worked on in this iteration.
            
        Returns:
            The newly created iteration ID.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO iterations (session_id, iteration_number, task_id_worked_on)
                VALUES (?, ?, ?)
            """, (session_id, iteration_number, task_id))
            return cursor.lastrowid
    
    def update_iteration(self, iteration_id: int, output: str, stderr: str) -> None:
        """Complete an iteration record with results.
        
        Args:
            iteration_id: The iteration ID to update.
            output: Standard output from the tool.
            stderr: Standard error from the tool.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE iterations 
                SET opencode_output = ?, opencode_stderr = ?, 
                    completed_at = CURRENT_TIMESTAMP, status = 'completed'
                WHERE id = ?
            """, (output, stderr, iteration_id))

    # --- Logging ---

    def log_message(self, session_id: int, iteration_number: Optional[int], 
                    level: str, message: str) -> None:
        """Log a console message to the database.
        
        Args:
            session_id: The session ID.
            iteration_number: The current iteration number (optional).
            level: Log level (info, warning, error, etc).
            message: The log message content.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO console_logs (session_id, iteration_number, log_level, message)
                VALUES (?, ?, ?, ?)
            """, (session_id, iteration_number, level, message))

    def claim_next_available_project(self, max_iterations: int) -> Optional[int]:
        """Atomically find the next unclaimed project and create a session for it.
        
        Args:
            max_iterations: Max iterations for the new session.
            
        Returns:
            The newly created session_id, or None if no projects are available.
        """
        # We use an explicit transaction to ensure atomicity
        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            
            # BEGIN IMMEDIATE locks the database for writing
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()
            
            # Find a project with no session
            cursor.execute("""
                SELECT id FROM projects 
                WHERE id NOT IN (SELECT project_id FROM sessions)
                ORDER BY id ASC
                LIMIT 1
            """)
            row = cursor.fetchone()
            
            if not row:
                conn.rollback()
                return None
                
            project_id = row['id']
            
            # Create the session
            cursor.execute(
                "INSERT INTO sessions (project_id, max_iterations) VALUES (?, ?)",
                (project_id, max_iterations)
            )
            session_id = cursor.lastrowid
            
            conn.commit()
            return session_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def close(self) -> None:
        """Close database resources (Legacy method for compatibility)."""
        # Connection is handled by context manager now, but we keep this for legacy compatibility.
        pass

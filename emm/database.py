#!/usr/bin/env python3
"""
EmmDatabase - SQLite database management for emm script
Handles features, sessions, tasks, iterations, and console logging
"""

import sqlite3
import hashlib
import json
import contextlib
from pathlib import Path
from typing import Optional, Dict, List, Any, Generator
from datetime import datetime


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
        """Create database with all required tables and indexes."""
        with self.connection() as conn:
            cursor = conn.cursor()
            self._create_tables(cursor)
            self._create_indexes(cursor)
            
    def _create_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create all required tables."""
        # Features table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS features (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                hash TEXT NOT NULL,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_id INTEGER NOT NULL,
                max_iterations INTEGER NOT NULL,
                tool TEXT DEFAULT 'opencode',
                status TEXT DEFAULT 'running',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP NULL,
                total_iterations INTEGER DEFAULT 0,
                total_tasks INTEGER DEFAULT 0,
                completed_tasks INTEGER DEFAULT 0,
                FOREIGN KEY (feature_id) REFERENCES features(id)
            )
        """)
        
        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                branch_name TEXT,
                task_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                acceptance_criteria TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                started_at TIMESTAMP NULL,
                completed_at TIMESTAMP NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        # Iterations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS iterations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                iteration_number INTEGER NOT NULL,
                task_id_worked_on TEXT,
                status TEXT DEFAULT 'running',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP NULL,
                opencode_output TEXT,
                opencode_stderr TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        # Console Logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS console_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                iteration_number INTEGER NULL,
                log_level TEXT DEFAULT 'info',
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
    def _create_indexes(self, cursor: sqlite3.Cursor) -> None:
        """Create performance indexes."""
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_session_status 
            ON tasks(session_id, status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_iterations_session 
            ON iterations(session_id, iteration_number)
        """)

    # --- Features ---

    def create_feature(self, feature_path: str) -> int:
        """Read feature file, calculate hash, and save to database.
        
        Args:
            feature_path: Path to the feature file.
            
        Returns:
            The feature ID of the newly created or existing feature.
        """
        path = Path(feature_path)
        content = path.read_text()
        hash_value = hashlib.sha256(content.encode()).hexdigest()
        name = path.stem
        
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO features (content, hash, name) VALUES (?, ?, ?)",
                (content, hash_value, name)
            )
            return cursor.lastrowid
    
    def get_feature(self, feature_id: int) -> Dict[str, Any]:
        """Retrieve a feature by ID.
        
        Args:
            feature_id: The ID of the feature to retrieve.
            
        Returns:
            A dictionary containing feature data.
            
        Raises:
            ValueError: If the feature ID is not found.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM features WHERE id = ?", (feature_id,))
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Feature {feature_id} not found")
            return dict(row)

    # --- Sessions ---

    def create_session(self, feature_id: int, max_iterations: int) -> int:
        """Create a new agent session.
        
        Args:
            feature_id: The ID of the feature associated with this session.
            max_iterations: Maximum iterations allowed for this session.
            
        Returns:
            The newly created session ID.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (feature_id, max_iterations) VALUES (?, ?)",
                (feature_id, max_iterations)
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

    def claim_next_available_feature(self, max_iterations: int) -> Optional[int]:
        """Atomically find the next unclaimed feature and create a session for it.
        
        Args:
            max_iterations: Max iterations for the new session.
            
        Returns:
            The newly created session_id, or None if no features are available.
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
            
            # Find a feature with no session OR no active session
            # For now, let's keep it simple: no session at all.
            cursor.execute("""
                SELECT id FROM features 
                WHERE id NOT IN (SELECT feature_id FROM sessions)
                ORDER BY id ASC
                LIMIT 1
            """)
            row = cursor.fetchone()
            
            if not row:
                conn.rollback()
                return None
                
            feature_id = row['id']
            
            # Create the session
            cursor.execute(
                "INSERT INTO sessions (feature_id, max_iterations) VALUES (?, ?)",
                (feature_id, max_iterations)
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

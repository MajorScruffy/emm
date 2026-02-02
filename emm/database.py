#!/usr/bin/env python3
import contextlib
import hashlib
import json
import sqlite3
from collections.abc import Generator
from pathlib import Path

from emm.config import MIGRATIONS_DIR


class EmmDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path

    @contextlib.contextmanager
    def connection(self, immediate: bool = False) -> Generator[sqlite3.Connection, None, None]:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            if immediate: connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally: connection.close()

    def execute(self, sql: str, params: tuple = (), one: bool = False, immediate: bool = False):
        with self.connection(immediate=immediate) as connection:
            result = connection.execute(sql, params)
            return result.fetchone() if one else result.fetchall()

    def initialize_database(self): self.run_migrations()

    def run_migrations(self):
        if not MIGRATIONS_DIR.exists(): return
        with self.connection() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (id INTEGER PRIMARY KEY AUTOINCREMENT, migration_name TEXT UNIQUE, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
                if not connection.execute("SELECT 1 FROM schema_migrations WHERE migration_name = ?", (sql_file.name,)).fetchone():
                    connection.executescript(sql_file.read_text())
                    connection.execute("INSERT INTO schema_migrations (migration_name) VALUES (?)", (sql_file.name,))

    def create_project(self, project_path: str) -> int:
        content = Path(project_path).read_text()
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        row = self.execute("SELECT id FROM projects WHERE hash = ?", (content_hash,), one=True)
        if row: return row['id']
        with self.connection() as connection:
            cursor = connection.execute("INSERT INTO projects (content, hash, name) VALUES (?, ?, ?)", (content, content_hash, Path(project_path).stem))
            return cursor.lastrowid

    def get_project(self, project_id: int) -> dict:
        row = self.execute("SELECT * FROM projects WHERE id = ?", (project_id,), one=True)
        if not row: raise ValueError(f"Project {project_id} not found")
        return dict(row)

    def create_session(self, project_id: int, max_iterations: int) -> int:
        with self.connection() as connection:
            return connection.execute("INSERT INTO sessions (project_id, max_iterations) VALUES (?, ?)", (project_id, max_iterations)).lastrowid

    def get_session(self, session_id: int) -> dict:
        row = self.execute("SELECT * FROM sessions WHERE id = ?", (session_id,), one=True)
        if not row: raise ValueError(f"Session {session_id} not found")
        return dict(row)

    def get_last_session_id(self, status_not: str = 'completed') -> int | None:
        row = self.execute("SELECT id FROM sessions WHERE status != ? ORDER BY created_at DESC LIMIT 1", (status_not,), one=True)
        return row[0] if row else None

    def update_session_status(self, session_id: int, status: str):
        clause = "status = ?, completed_at = CURRENT_TIMESTAMP" if status in ('completed', 'failed', 'interrupted') else "status = ?"
        self.execute(f"UPDATE sessions SET {clause} WHERE id = ?", (status, session_id))

    def create_task(self, session_id: int, task_data: dict):
        return self.execute("INSERT INTO tasks (session_id, branch_name, task_id, title, description, acceptance_criteria) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, task_data.get('branchName'), task_data['id'], task_data['title'], task_data['description'], json.dumps(task_data.get('acceptanceCriteria', []))))

    def get_highest_task_id(self, session_id: int) -> int:
        row = self.execute("SELECT task_id FROM tasks WHERE session_id = ? ORDER BY task_id DESC LIMIT 1", (session_id,), one=True)
        try: return int(row[0]) if row else 0
        except: return 0

    def get_tasks(self, session_id: int) -> list[dict]:
        return [{**dict(row), 'acceptance_criteria': json.loads(row['acceptance_criteria'])} for row in self.execute("SELECT * FROM tasks WHERE session_id = ? ORDER BY id ASC", (session_id,))]

    def get_next_task(self, session_id: int) -> dict | None:
        row = self.execute("SELECT * FROM tasks WHERE session_id = ? AND status = 'pending' ORDER BY id ASC LIMIT 1", (session_id,), one=True)
        return {**dict(row), 'acceptance_criteria': json.loads(row['acceptance_criteria'])} if row else None

    def update_task_status(self, session_id: int, task_id: str, status: str):
        time_column = "started_at" if status == 'in_progress' else "completed_at" if status == 'completed' else None
        clause = f"status = ?, {time_column} = CURRENT_TIMESTAMP" if time_column else "status = ?"
        self.execute(f"UPDATE tasks SET {clause} WHERE session_id = ? AND task_id = ?", (status, session_id, task_id))

    def create_iteration(self, session_id: int, iteration_number: int, task_id_worked_on: str) -> int:
        with self.connection() as connection:
            return connection.execute("INSERT INTO iterations (session_id, iteration_number, task_id_worked_on) VALUES (?, ?, ?)", (session_id, iteration_number, task_id_worked_on)).lastrowid

    def update_iteration(self, iteration_id: int, output: str, stderr: str):
        self.execute("UPDATE iterations SET opencode_output = ?, opencode_stderr = ?, completed_at = CURRENT_TIMESTAMP, status = 'completed' WHERE id = ?", (output, stderr, iteration_id))

    def get_iterations_for_task(self, session_id: int, task_id: str) -> list[dict]:
        return [dict(row) for row in self.execute("SELECT * FROM iterations WHERE session_id = ? AND task_id_worked_on = ? ORDER BY iteration_number ASC", (session_id, task_id))]

    def log_message(self, session_id: int, iteration_number: int | None, log_level: str, message: str):
        self.execute("INSERT INTO console_logs (session_id, iteration_number, log_level, message) VALUES (?, ?, ?, ?)", (session_id, iteration_number, log_level, message))

    def claim_next_available_project(self, max_iterations: int) -> int | None:
        with self.connection(immediate=True) as connection:
            row = connection.execute("SELECT id FROM projects WHERE id NOT IN (SELECT project_id FROM sessions) ORDER BY id ASC LIMIT 1").fetchone()
            if not row: return None
            connection.execute("INSERT INTO sessions (project_id, max_iterations) VALUES (?, ?)", (row['id'], max_iterations))
            return connection.execute("SELECT last_insert_rowid()").fetchone()[0]

    def close(self): pass

    @staticmethod
    def validate_project(project_data: dict) -> bool:
        return isinstance(project_data, dict) and "tasks" in project_data and isinstance(project_data["tasks"], list)

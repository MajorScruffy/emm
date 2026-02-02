import os
import sqlite3
import tempfile
import unittest

from emm.database import EmmDatabase


class TestUS5Database(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_us5.db")
        self.db = EmmDatabase(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_schema_integrity(self):
        """US5.1: Assert all tables and indexes exist after initialization."""
        self.db.initialize_database()

        with self.db.connection() as conn:
            cursor = conn.cursor()
            # Check tables
            tables = ["projects", "sessions", "tasks", "iterations", "console_logs"]
            for table in tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                self.assertIsNotNone(cursor.fetchone(), f"Table {table} should exist")

            # Check indexes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_tasks_session_status'")
            self.assertIsNotNone(cursor.fetchone(), "Index idx_tasks_session_status should exist")

    def test_transaction_rollback(self):
        """US5.2: Assert transaction rolls back on exception within context manager."""
        self.db.initialize_database()

        # Insert a project successfully
        with self.db.connection() as conn:
            conn.execute("INSERT INTO projects (content, hash, name) VALUES ('C1', 'H1', 'N1')")

        # Attempt to insert another but fail mid-way
        try:
            with self.db.connection() as conn:
                conn.execute("INSERT INTO projects (content, hash, name) VALUES ('C2', 'H2', 'N2')")
                raise RuntimeError("Artificial failure")
        except RuntimeError:
            pass

        # Verify only C1 exists
        with self.db.connection() as conn:
            row = conn.execute("SELECT COUNT(*) FROM projects").fetchone()
            self.assertEqual(row[0], 1)

            row = conn.execute("SELECT name FROM projects").fetchone()
            self.assertEqual(row[0], 'N1')

    def test_foreign_key_enforcement(self):
        """US5.1: Assert foreign keys are active."""
        self.db.initialize_database()

        with self.db.connection() as conn:
            # Attempt to create a session with non-existent project_id
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO sessions (project_id, max_iterations) VALUES (999, 10)")

    def test_context_manager_closure(self):
        """US5.3: Assert connections are closed even on error."""
        self.db.initialize_database()

        # This is tricky to test exactly without mocking sqlite3,
        # but we verify it doesn't leave locks that prevent deletion/access.
        try:
            with self.db.connection() as conn:
                raise ValueError("Die")
        except ValueError:
            pass

        # Should be able to connect again immediately
        with self.db.connection() as conn:
            self.assertIsNotNone(conn)

if __name__ == "__main__":
    unittest.main()

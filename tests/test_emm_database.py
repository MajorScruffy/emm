import unittest
import sqlite3
import json
import os
import shutil
import tempfile
from pathlib import Path
from emm.database import EmmDatabase

class TestEmmDatabase(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_emm.db")
        self.db_path = os.path.join(self.test_dir, "test_emm.db")
        self.project_path = os.path.join(self.test_dir, "test_project.md")
        
        # Create dummy project file
        with open(self.project_path, 'w') as f:
            f.write("# Test Project\n\nSome content")
            
        # Initialize DB
        self.db = EmmDatabase(self.db_path)
        self.db.initialize_database()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_initialize_database(self):
        with self.db.connection() as conn:
            cursor = conn.cursor()
            # Check tables exist
            tables = ["projects", "sessions", "tasks", "iterations", "console_logs"]
            for table in tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                self.assertIsNotNone(cursor.fetchone(), f"Table {table} should exist")

    def test_project_operations(self):
        # Create
        project_id = self.db.create_project(self.project_path)
        self.assertGreater(project_id, 0)
        
        # Get
        project = self.db.get_project(project_id)
        self.assertEqual(project['name'], "test_project")
        self.assertEqual(project['content'], "# Test Project\n\nSome content")
        self.assertIsNotNone(project['hash'])

    def test_session_operations(self):
        project_id = self.db.create_project(self.project_path)
        
        # Create
        session_id = self.db.create_session(project_id, max_iterations=10)
        self.assertGreater(session_id, 0)
        
        # Get
        session = self.db.get_session(session_id)
        self.assertEqual(session['project_id'], project_id)
        self.assertEqual(session['max_iterations'], 10)
        self.assertEqual(session['status'], 'running')
        
        # Update status
        self.db.update_session_status(session_id, 'completed')
        session = self.db.get_session(session_id)
        self.assertEqual(session['status'], 'completed')
        self.assertIsNotNone(session['completed_at'])

    def test_task_operations(self):
        project_id = self.db.create_project(self.project_path)
        session_id = self.db.create_session(project_id, 10)
        
        task_data = {
            'id': '001',
            'title': 'Test Task',
            'description': 'Description',
            'acceptanceCriteria': ['Criteria 1', 'Criteria 2'],
            'branchName': 'project/test'
        }
        
        # Create
        self.db.create_task(session_id, task_data)
        
        # Get next
        task = self.db.get_next_task(session_id)
        self.assertIsNotNone(task)
        self.assertEqual(task['task_id'], '001')
        self.assertEqual(task['status'], 'pending')
        self.assertIsInstance(task['acceptance_criteria'], list)
        self.assertEqual(len(task['acceptance_criteria']), 2)
        
        # Update status
        self.db.update_task_status(session_id, '001', 'in_progress')
        
        # Verify update directly
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", ('001',)).fetchone()
            self.assertEqual(row['status'], 'in_progress')
            self.assertIsNotNone(row['started_at'])

    def test_iteration_operations(self):
        project_id = self.db.create_project(self.project_path)
        session_id = self.db.create_session(project_id, 10)
        
        # Create
        iteration_id = self.db.create_iteration(session_id, 1, '001')
        self.assertGreater(iteration_id, 0)
        
        # Update
        self.db.update_iteration(iteration_id, "Output", "Stderr")
        
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM iterations WHERE id = ?", (iteration_id,)).fetchone()
            self.assertEqual(row['status'], 'completed')
            self.assertEqual(row['opencode_output'], "Output")
            self.assertIsNotNone(row['completed_at'])

    def test_log_message(self):
        project_id = self.db.create_project(self.project_path)
        session_id = self.db.create_session(project_id, 10)
        
        self.db.log_message(session_id, 1, 'info', 'message')
        
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM console_logs WHERE session_id = ?", (session_id,)).fetchone()
            self.assertEqual(row['message'], 'message')
            self.assertEqual(row['log_level'], 'info')

if __name__ == '__main__':
    unittest.main()

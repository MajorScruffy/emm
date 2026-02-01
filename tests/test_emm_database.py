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
        self.feature_path = os.path.join(self.test_dir, "test_feature.md")
        
        # Create dummy feature file
        with open(self.feature_path, 'w') as f:
            f.write("# Test Feature\n\nSome content")
            
        # Initialize DB
        self.db = EmmDatabase(self.db_path)
        self.db.initialize_database()

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.test_dir)

    def test_initialize_database(self):
        with self.db.connection() as conn:
            cursor = conn.cursor()
            # Check tables exist
            tables = ["features", "sessions", "tasks", "iterations", "console_logs"]
            for table in tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                self.assertIsNotNone(cursor.fetchone(), f"Table {table} should exist")

    def test_feature_operations(self):
        # Create
        feature_id = self.db.create_feature(self.feature_path)
        self.assertGreater(feature_id, 0)
        
        # Get
        feature = self.db.get_feature(feature_id)
        self.assertEqual(feature['name'], "test_feature")
        self.assertEqual(feature['content'], "# Test Feature\n\nSome content")
        self.assertIsNotNone(feature['hash'])

    def test_session_operations(self):
        feature_id = self.db.create_feature(self.feature_path)
        
        # Create
        session_id = self.db.create_session(feature_id, max_iterations=10)
        self.assertGreater(session_id, 0)
        
        # Get
        session = self.db.get_session(session_id)
        self.assertEqual(session['feature_id'], feature_id)
        self.assertEqual(session['max_iterations'], 10)
        self.assertEqual(session['status'], 'running')
        
        # Update status
        self.db.update_session_status(session_id, 'completed')
        session = self.db.get_session(session_id)
        self.assertEqual(session['status'], 'completed')
        self.assertIsNotNone(session['completed_at'])

    def test_task_operations(self):
        feature_id = self.db.create_feature(self.feature_path)
        session_id = self.db.create_session(feature_id, 10)
        
        task_data = {
            'id': '001',
            'title': 'Test Task',
            'description': 'Description',
            'acceptanceCriteria': ['Criteria 1', 'Criteria 2'],
            'branchName': 'feature/test'
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
        feature_id = self.db.create_feature(self.feature_path)
        session_id = self.db.create_session(feature_id, 10)
        
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
        feature_id = self.db.create_feature(self.feature_path)
        session_id = self.db.create_session(feature_id, 10)
        
        self.db.log_message(session_id, 1, 'info', 'message')
        
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM console_logs WHERE session_id = ?", (session_id,)).fetchone()
            self.assertEqual(row['message'], 'message')
            self.assertEqual(row['log_level'], 'info')

if __name__ == '__main__':
    unittest.main()

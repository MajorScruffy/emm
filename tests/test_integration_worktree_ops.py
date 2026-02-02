
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from emm.git_utils import WorktreeManager
from emm.logger import DualLogger


class TestWorktreeIsolation(unittest.TestCase):
    def setUp(self):
        # Create a temp directory for the fake repo
        self.test_dir = Path(tempfile.mkdtemp())
        self.repo_dir = self.test_dir / "my-repo"
        self.repo_dir.mkdir()

        # Initialize a real git repo
        subprocess.run(["git", "init"], cwd=self.repo_dir, check=True, capture_output=True)

        # We need at least one commit for worktrees to work
        (self.repo_dir / "README.md").write_text("# Test Repo")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.repo_dir, check=True, capture_output=True)

        self.logger = DualLogger()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_simultaneous_worktrees(self):
        # Simulator: Two parallel sessions
        manager1 = WorktreeManager(self.logger, base_dir=self.repo_dir)
        manager2 = WorktreeManager(self.logger, base_dir=self.repo_dir)

        # Determine the actual default branch (master or main)
        base_branch = subprocess.run(["git", "branch", "--show-current"], cwd=self.repo_dir, capture_output=True, text=True).stdout.strip()

        # 1. Create Worktree for Session 101
        wt1 = manager1.create_worktree(101, base_branch=base_branch)
        self.assertIsNotNone(wt1)
        self.assertTrue(wt1.exists())
        self.assertTrue((wt1 / ".git").exists()) # It's a valid git connection

        # Verify Branch
        branch1 = subprocess.run(["git", "branch", "--show-current"], cwd=wt1, capture_output=True, text=True).stdout.strip()
        self.assertEqual(branch1, "emm/session-101")

        # 2. Create Worktree for Session 102
        wt2 = manager2.create_worktree(102, base_branch=base_branch)
        self.assertIsNotNone(wt2)
        self.assertTrue(wt2.exists())

        # Verify Isolation
        self.assertNotEqual(wt1, wt2)

        # 3. Modify file in Session 1
        (wt1 / "session1.txt").write_text("I am session 1")

        # 4. Check Session 2 does NOT see it
        self.assertFalse((wt2 / "session1.txt").exists())

        # 5. Cleanup
        manager1.cleanup_worktree(101)
        manager2.cleanup_worktree(102)

        self.assertFalse(wt1.exists())
        self.assertFalse(wt2.exists())

if __name__ == '__main__':
    unittest.main()

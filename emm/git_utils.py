import shutil
import subprocess
from pathlib import Path

from emm import config
from emm.logger import DualLogger


class WorktreeManager:
    """Manages git worktrees for isolated session execution."""

    def __init__(self, log: DualLogger, base_dir: Path = config.ROOT_DIR):
        self.log = log
        self.base_dir = base_dir
        self.worktrees_dir = base_dir / "worktrees"
        self.worktrees_dir.mkdir(exist_ok=True)

    def _run_git(self, args: list[str], quiet: bool = False) -> bool:
        """Run a git command."""
        try:
            subprocess.run(
                ["git"] + args,
                cwd=self.base_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            if not quiet:
                self.log.error(
                    f"Git command failed: git {' '.join(args)}\nError: {e.stderr}"
                )
            return False

    def get_all_worktrees(self) -> list[str]:
        """List all worktree directories in the worktrees folder."""
        if not self.worktrees_dir.exists():
            return []
        return [d.name for d in self.worktrees_dir.iterdir() if d.is_dir()]

    def get_worktree_path(self, session_id: int) -> Path:
        """Get the expected path for a session's worktree."""
        return self.worktrees_dir / f"session-{session_id}"

    def create_worktree(
        self, session_id: int, base_branch: str | None = None
    ) -> Path | None:
        """Create a new worktree for the session."""
        path = self.get_worktree_path(session_id)
        if path.exists():
            self.log.warning(f"Worktree already exists at {path}")
            return path

        if not base_branch:
            # Try to detect current branch or fall back to main/master
            try:
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=self.base_dir,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                curr = result.stdout.strip()
                if curr:
                    base_branch = curr
                else:
                    # Detached HEAD or other issue, try to find main/master
                    for b in ["main", "master"]:
                        if self._run_git(["rev-parse", "--verify", b], quiet=True):
                            base_branch = b
                            break
                    if not base_branch:
                        base_branch = "HEAD"
            except (subprocess.CalledProcessError, OSError):
                base_branch = "main"  # Final fallback

        branch_name = f"emm/session-{session_id}"

        # Check if branch already exists
        branch_exists = self._run_git(
            ["rev-parse", "--verify", branch_name], quiet=True
        )

        self.log.info(
            f"Creating worktree for session {session_id} at {path} (from {base_branch})"
        )

        # Create worktree. Use -b only if it doesn't exist.
        if branch_exists:
            # Reusing existing branch
            if self._run_git(["worktree", "add", str(path), branch_name]):
                return path
        else:
            # Creating new branch
            if self._run_git(
                ["worktree", "add", "-b", branch_name, str(path), base_branch]
            ):
                return path

        return None

    def cleanup_worktree(self, session_id: int):
        """Remove a worktree and prune metadata."""
        path = self.get_worktree_path(session_id)

        # Always try to prune first to clean up any messy state
        self._run_git(["worktree", "prune"])

        if not path.exists():
            return

        self.log.info(f"Cleaning up worktree {path}")

        # Git worktree removing with --force to handle untracked files
        self._run_git(["worktree", "remove", "--force", str(path)])

        # Final safety cleanup
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

        # Prune again after removal
        self._run_git(["worktree", "prune"])

import json
import sys
from pathlib import Path

from emm import config
from emm.database import EmmDatabase
from emm.git_utils import WorktreeManager
from emm.logger import RICH_AVAILABLE, DualLogger
from emm.runners import ToolRunner


class EmmAgent:
    def __init__(
        self,
        db: EmmDatabase,
        log: DualLogger,
        max_iterations: int = config.DEFAULT_ITERATIONS,
        project_path: str | None = None,
        resume: bool = False,
        work_dir: Path | None = None,
        run_once: bool = False,
    ):
        self.db, self.log, self.max_iterations, self.resume = (
            db,
            log,
            max_iterations,
            resume,
        )
        self.run_once = run_once
        self.runner = ToolRunner(log=self.log)
        self.worktree_manager = WorktreeManager(
            log=self.log, base_dir=work_dir or config.ROOT_DIR
        )
        self.worktree_path = self.session_id = None
        self.iteration = 0

    def run_ai_tool(self, task: dict | None = None) -> str:
        with self.log.status_indicator("Running opencode...", "opencode completed"):
            return self.runner.run_opencode(task, cwd=self.worktree_path)

    def ingest_pending_projects(self):
        if not config.PROJECTS_DIR.exists():
            return
        for project_file in sorted(config.PROJECTS_DIR.glob("*.json")):
            try:
                self.log.info(f"Ingesting: {project_file.name}")
                self.db.create_project(str(project_file))
            except Exception as e:
                self.log.error(f"Failed to ingest {project_file.name}: {e}")

    def _init_session(self) -> bool:
        """Initialize a new session. Returns True if a session was started/resumed."""
        if self.resume:
            self.session_id = self.db.get_last_session_id()
            if not self.session_id:
                self.log.error("No sessions found to resume.")
                return False
            self.log.set_session_id(self.session_id)
            self.log.info(f"Resuming session {self.session_id}")
            # Identify worktree for resume
            self.worktree_path = self.worktree_manager.get_worktree_path(self.session_id)
            if not self.worktree_path.exists():
                self.log.error(f"Worktree for session {self.session_id} not found at {self.worktree_path}")
                return False
            return True

        self.ingest_pending_projects()
        self.session_id = self.db.claim_next_available_project(self.max_iterations)
        if not self.session_id:
            return False
        self.log.set_session_id(self.session_id)

        session_data = self.db.get_session(self.session_id)
        project_data = self.db.get_project(session_data["project_id"])
        content = json.loads(project_data["content"])
        if not EmmDatabase.validate_project(content):
            self.log.error("Invalid project format in database.")
            return False

        for task in content.get("tasks", []):
            if "branchName" not in task and "branchName" in content:
                task["branchName"] = content["branchName"]
            self.db.create_task(self.session_id, task)

        self.worktree_path = self.worktree_manager.create_worktree(self.session_id)
        if not self.worktree_path:
            self.log.error("Failed to create worktree.")
            return False
        (self.worktree_path / ".session.json").write_text(
            json.dumps({"session_id": self.session_id})
        )
        self.log.info(f"Started session {self.session_id}")
        return True

    def display_tasks_table(self):
        if not self.session_id:
            return
        tasks = self.db.get_tasks(self.session_id)
        if not tasks:
            return
        rows = [
            [
                task["task_id"],
                task["title"],
                f"[{{'completed':'green','in_progress':'yellow'}}.get(task['status'],'white')]]{task['status']}[/]"
                if RICH_AVAILABLE
                else task["status"],
            ]
            for task in tasks
        ]
        self.log.table(
            f"Session {self.session_id} Tasks", ["Task ID", "Title", "Status"], rows
        )

    def run_iteration(self, iteration_number: int) -> bool:
        self.iteration = iteration_number
        self.log.set_iteration(iteration_number)
        current_task = self.db.get_next_task(self.session_id)
        task_id = current_task["task_id"] if current_task else "unknown"
        if current_task:
            self.db.update_task_status(self.session_id, task_id, "in_progress")
        self.log.rule(f"Iteration {iteration_number} | Task: {task_id}")
        iteration_id = self.db.create_iteration(
            self.session_id, iteration_number, task_id
        )
        output = self.run_ai_tool(current_task)
        self.db.update_iteration(iteration_id, output, "")
        if output and config.COMPLETION_TAG in output:
            if current_task:
                self.db.update_task_status(self.session_id, task_id, "completed")
            self.log.info(f"Task {task_id} completed!")
            return True
        return False

    def run_single_session(self) -> int | None:
        """Runs a single project session. Returns exit code or None if init failed."""
        if not self._init_session():
            return None
        try:
            for iteration in range(1, self.max_iterations + 1):
                if self.run_iteration(iteration):
                    self.db.update_session_status(self.session_id, "completed")
                    self.log.info("✅ Goal reached!")
                    return 0
            self.db.update_session_status(self.session_id, "failed")
            self.log.warning("Max iterations reached without reaching the goal.")
            return 1
        except KeyboardInterrupt:
            self.log.warning("\nInterrupted by user.")
            self.db.update_session_status(self.session_id, "interrupted")
            raise
        except Exception as e:
            self.log.error(f"Error in execution loop: {e}")
            self.db.update_session_status(self.session_id, "failed")
            return 1
        finally:
            self.display_tasks_table()
            if self.session_id:
                self.worktree_manager.cleanup_worktree(self.session_id)

    def run(self) -> int:
        try:
            while True:
                exit_code = self.run_single_session()
                
                if exit_code is None:
                    # Couldn't even start a session (likely no projects)
                    # Check one more time after ingestion
                    if not self.resume:
                        self.ingest_pending_projects()
                        exit_code = self.run_single_session()
                        if exit_code is None:
                            self.log.info("No unclaimed projects found in the database.")
                            return 0
                    else:
                        return 1 # Resume failed

                if self.run_once or self.resume:
                    return exit_code
                
                self.log.info("Session complete. Looking for next project...")
                self.session_id = None
                self.worktree_path = None
                self.iteration = 0
                
        except KeyboardInterrupt:
            return 130
        except Exception as e:
            self.log.error(f"Fatal error in agent runner: {e}")
            return 1

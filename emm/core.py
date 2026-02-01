from typing import Optional, Any
from emm.database import EmmDatabase
from emm.parser import ProjectParser
from emm.runners import ToolRunner
from emm.logger import DualLogger, RICH_AVAILABLE
from emm import config
import sys


class EmmAgent:
    """Long-running AI agent automation tool with Dependency Injection."""

    def __init__(self, db: EmmDatabase, log: DualLogger, max_iterations: int = config.DEFAULT_ITERATIONS, 
                 project_path: Optional[str] = None, resume: bool = False):
        """Initialize the agent with injected dependencies."""
        self.db = db
        self.log = log
        self.max_iterations = max_iterations
        self.project_path = project_path
        self.resume = resume
        
        self.runner = ToolRunner(log=self.log)
        self.session_id: Optional[int] = None
        self.iteration: int = 0

    def run_ai_tool(self, task: Optional[dict] = None) -> str:
        """Execute the AI tool with status indicator and context."""
        with self.log.status_indicator(f"Running opencode...", f"opencode completed"):
            return self.runner.run_opencode(task)

    def ingest_pending_projects(self):
        """Scan .projects directory and ingest new projects."""
        if not config.PROJECTS_DIR.exists():
            return

        for project_file in sorted(config.PROJECTS_DIR.glob("*.json")):
            try:
                # We let the database handle deduplication via hash check
                self.log.info(f"Ingesting project: {project_file.name}")
                self.db.create_project(str(project_file))
            except Exception as e:
                self.log.error(f"Failed to ingest {project_file.name}: {e}")

    def _init_session(self):
        """Initialize or resume a session."""
        if self.resume:
            self.session_id = self.db.get_last_session_id()
            if self.session_id:
                self.log.set_session_id(self.session_id)
                self.log.info(f"Resuming session {self.session_id}")
                return
            else:
                self.log.error("No sessions found to resume.")
                sys.exit(1)

        # Ingest any new projects found on disk
        self.ingest_pending_projects()
        
        self.session_id = self.db.claim_next_available_project(self.max_iterations)
        
        if not self.session_id:
            self.log.warning("No unclaimed projects found in database. Exiting.")
            sys.exit(0)
            
        self.log.set_session_id(self.session_id)
        self.log.info(f"Claimed project and started session {self.session_id}")

    def display_tasks_table(self):
        """Display a summary table of tasks."""
        if not self.session_id:
            return

        tasks = self.db.get_tasks(self.session_id)
        if not tasks:
            return

        columns = ["Task ID", "Title", "Status"]
        rows = []
        for t in tasks:
            status = t['status']
            if RICH_AVAILABLE:
                color = "green" if status == 'completed' else "yellow" if status == 'in_progress' else "white"
                status = f"[{color}]{status}[/{color}]"
            rows.append([t['task_id'], t['title'], status])

        self.log.table(title=f"Session {self.session_id} Tasks", columns=columns, rows=rows)

    def run_iteration(self, iteration: int) -> bool:
        """Run a single loop iteration."""
        self.iteration = iteration
        self.log.set_iteration(iteration)
        current_task = self.db.get_next_task(self.session_id)
        task_id = current_task['task_id'] if current_task else "unknown"
        
        if current_task:
            self.db.update_task_status(self.session_id, task_id, "in_progress")

        self.log.rule(f"Iteration {iteration} | Task: {task_id}")
        self.log.info(f"Starting iteration {iteration} (Task: {task_id})")

        iter_id = self.db.create_iteration(self.session_id, iteration, task_id)
        output = self.run_ai_tool(current_task)
        self.db.update_iteration(iter_id, output, "")

        if output and config.COMPLETION_TAG in output:
            if current_task:
                self.db.update_task_status(self.session_id, task_id, "completed")
            self.log.info(f"Task {task_id} completed!")
            return True

        return False

    def run(self) -> int:
        """Main execution loop."""
        self._init_session()
        try:
            for i in range(1, self.max_iterations + 1):
                try:
                    if self.run_iteration(i):
                        self.db.update_session_status(self.session_id, "completed")
                        self.log.info("✅ Goal reached!")
                        return 0
                except KeyboardInterrupt:
                    self.log.warning("\nInterrupted by user")
                    self.db.update_session_status(self.session_id, "interrupted")
                    return 130
                except Exception as e:
                    self.log.error(f"Error in iteration {i}: {e}")
            
            self.db.update_session_status(self.session_id, "failed")
            self.log.warning("Max iterations reached.")
            return 1
        finally:
            self.display_tasks_table()

# Missing Path import in the code content above (fix needed)
from pathlib import Path

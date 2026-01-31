from typing import Optional, Any
from emm.database import EmmDatabase
from emm.parser import FeatureParser
from emm.runners import ToolRunner
from emm.logger import DualLogger
from emm import config


class EmmAgent:
    """Long-running AI agent automation tool with Dependency Injection."""

    def __init__(self, db: EmmDatabase, log: DualLogger, max_iterations: int = config.DEFAULT_ITERATIONS, 
                 feature_path: Optional[str] = None, resume: bool = False):
        """Initialize the agent with injected dependencies."""
        self.db = db
        self.log = log
        self.max_iterations = max_iterations
        self.feature_path = feature_path
        self.resume = resume
        
        self.runner = ToolRunner(log=self.log)
        self.session_id: Optional[int] = None
        self.iteration: int = 0

    def run_ai_tool(self) -> str:
        """Execute the AI tool with status indicator."""
        with self.log.status_indicator(f"Running opencode...", f"opencode completed"):
            return self.runner.run_opencode()

    def _init_session(self):
        """Initialize or resume a session."""
        if self.resume:
            self.session_id = self.db.get_last_session_id()
            if self.session_id:
                self.log.set_session_id(self.session_id)
                self.log.info(f"Resuming session {self.session_id}")
                return

        # Start new session
        feat_id = 1
        if self.feature_path and Path(self.feature_path).exists():
            feat_id = self.db.create_feature(self.feature_path)
        
        self.session_id = self.db.create_session(feat_id, self.max_iterations)
        self.log.set_session_id(self.session_id)
        self.log.info(f"Started new session {self.session_id}")
        self._ingest_feature_if_needed()

    def _ingest_feature_if_needed(self):
        """Load tasks from JSON into the database if not already present."""
        existing_tasks = self.db.get_tasks(self.session_id)
        if existing_tasks:
            return

        json_path = Path(self.feature_path) if (self.feature_path and self.feature_path.endswith('.json')) else None
        if not json_path and config.FEATURE_JSON.exists():
            json_path = config.FEATURE_JSON

        if json_path:
            data = FeatureParser.parse_json_feature(json_path)
            tasks = data.get("tasks", [])
            for task in tasks:
                self.db.create_task(self.session_id, task)
            self.log.info(f"Ingested {len(tasks)} tasks from {json_path}")

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
            color = "green" if t['status'] == 'completed' else "yellow" if t['status'] == 'in_progress' else "white"
            rows.append([t['task_id'], t['title'], f"[{color}]{t['status']}[/{color}]"])

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
        output = self.run_ai_tool()
        self.db.update_iteration(iter_id, output, "")

        if output and config.COMPLETION_TAG in output:
            if current_task:
                self.db.update_task_status(self.session_id, task_id, "completed")
            self.log.success(f"Task {task_id} completed!")
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
                        self.log.success("✅ Goal reached!")
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

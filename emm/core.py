"""
Core agent logic for Emm.
"""

from typing import Optional, Any
from emm.database import EmmDatabase
from emm.parser import FeatureParser
from emm.runners import ToolRunner
from emm import config

try:
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class EmmAgent:
    """Long-running AI agent automation tool with Dependency Injection."""

    def __init__(self, db: EmmDatabase, console: Any, max_iterations: int = config.DEFAULT_ITERATIONS, 
                 feature_path: Optional[str] = None, resume: bool = False):
        """Initialize the agent with injected dependencies."""
        self.db = db
        self.console = console
        self.max_iterations = max_iterations
        self.feature_path = feature_path
        self.resume = resume
        
        self.runner = ToolRunner(console)
        self.session_id: Optional[int] = None
        self.iteration: int = 0

    def run_ai_tool(self) -> str:
        """Execute the AI tool with status indicator."""
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True,
            ) as progress:
                task = progress.add_task(f"Running opencode...", total=None)
                output = self.runner.run_opencode()
                progress.update(task, description=f"opencode completed")
                return output
        else:
            self.console.print(f"Running opencode...")
            return self.runner.run_opencode()

    def _init_session(self):
        """Initialize or resume a session."""
        if self.resume:
            self.session_id = self.db.get_last_session_id()
            if self.session_id:
                self.log_to_db("info", "agent", f"Resuming session {self.session_id}")
                self.console.print(f"[cyan]Resuming session {self.session_id}[/cyan]")
                return

        # Start new session
        feat_id = 1
        if self.feature_path and Path(self.feature_path).exists():
            feat_id = self.db.create_feature(self.feature_path)
        
        self.session_id = self.db.create_session(feat_id, self.max_iterations)
        self.log_to_db("info", "agent", f"Started new session {self.session_id}")
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
            self.log_to_db("info", "agent", f"Ingested {len(tasks)} tasks from {json_path}")

    def log_to_db(self, level: str, component: str, message: str):
        """Log a message to the database."""
        if self.session_id:
            try:
                self.db.log_message(self.session_id, self.iteration, level, component, message)
            except Exception as e:
                self.console.print(f"[dim yellow]DB Log Error: {e}[/dim yellow]")

    def display_tasks_table(self):
        """Display a summary table of tasks."""
        if not RICH_AVAILABLE or not self.session_id:
            return

        tasks = self.db.get_tasks(self.session_id)
        if not tasks:
            return

        table = Table(title=f"Session {self.session_id} Tasks", show_header=True, header_style="bold magenta")
        table.add_column("Task ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
        table.add_column("Status", style="bold")

        for t in tasks:
            style = "green" if t['status'] == 'completed' else "yellow" if t['status'] == 'in_progress' else "white"
            table.add_row(t['task_id'], t['title'], f"[{style}]{t['status']}[/{style}]")

        self.console.print(table)
        self.console.print()

    def run_iteration(self, iteration: int) -> bool:
        """Run a single loop iteration."""
        self.iteration = iteration
        current_task = self.db.get_next_task(self.session_id)
        task_id = current_task['task_id'] if current_task else "unknown"
        
        if current_task:
            self.db.update_task_status(self.session_id, task_id, "in_progress")

        self.console.rule(f"Iteration {iteration} | Task: {task_id}")
        self.log_to_db("info", "agent", f"Starting iteration {iteration} (Task: {task_id})")

        iter_id = self.db.create_iteration(self.session_id, iteration, task_id)
        output = self.run_ai_tool()
        self.db.update_iteration(iter_id, output, "")

        if output and config.COMPLETION_TAG in output:
            if current_task:
                self.db.update_task_status(self.session_id, task_id, "completed")
            return True

        return False

    def run(self):
        """Main execution engine."""
        try:
            config.ensure_dirs()
            self._init_session()
            self.display_tasks_table()

            for i in range(1, self.max_iterations + 1):
                try:
                    if self.run_iteration(i):
                        self.db.update_session_status(self.session_id, "completed")
                        self.console.print("[bold green]✅ Goal reached![/bold green]")
                        return 0
                except KeyboardInterrupt:
                    self.console.print("\n[yellow]Interrupted by user[/yellow]")
                    self.db.update_session_status(self.session_id, "interrupted")
                    return 130
                except Exception as e:
                    self.console.print(f"[red]Error in iteration {i}: {e}[/red]")
                    self.log_to_db("error", "agent", f"Iteration error: {e}")

            self.db.update_session_status(self.session_id, "failed")
            self.console.print("[bold yellow]Max iterations reached.[/bold yellow]")
            return 1
        finally:
            self.display_tasks_table()

# Missing Path import in the code content above (fix needed)
from pathlib import Path

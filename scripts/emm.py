#!/usr/bin/env python3
"""
Emm - Long-running AI agent loop
Usage: python emm.py [--feature path] [--resume] [max_iterations]
"""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

try:
    from scripts.emm_database import EmmDatabase
    from scripts.feature_parser import FeatureParser
except ImportError:
    from emm_database import EmmDatabase
    from feature_parser import FeatureParser

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.rule import Rule
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: 'rich' package not available. Using basic console output.")


class SimpleConsole:
    """Fallback console when rich is not available"""

    def print(self, message=None, style=None, **kwargs):
        if message is None:
            return
        text = str(message)
        # Strip common rich markup tag patterns
        import re
        text = re.sub(r'\[.*?\]', '', text)
        print(text)

    def rule(self, title=None, style=None, align=None):
        length = 80
        line = "=" * length
        if title:
            title_str = str(title)
            import re
            title_str = re.sub(r'\[.*?\]', '', title_str)
            half = (length - len(title_str) - 2) // 2
            print(f"{line[:half]} {title_str} {line[half + len(title_str) + 2 :]}")
        else:
            print(line)

# Fallback for mocking and initialization if rich is missing
if not RICH_AVAILABLE:
    Console = SimpleConsole


def print_panel(console, title: str, message: str, border_style: str = "green"):
    """Print a panel with rich or fallback console."""
    if RICH_AVAILABLE:
        console.print(Panel(message, title=title, border_style=border_style))
    else:
        console.rule(title)
        print(str(message))
        console.rule()


class EmmAgent:
    """Long-running AI agent automation tool."""

    def __init__(self, max_iterations: int, feature_path: Optional[str] = None, resume: bool = False):
        """Initialize the agent.
        
        Args:
            max_iterations: Max number of loops.
            feature_path: Optional path to a JSON feature file.
            resume: Whether to resume the last non-completed session.
        """
        self.tool = "opencode"
        self.max_iterations = max_iterations
        self.feature_path = Path(feature_path) if feature_path else None
        self.resume = resume
        self.console = Console() if RICH_AVAILABLE else SimpleConsole()

        # Setup paths
        self.script_dir = Path(__file__).parent.resolve()
        self.data_dir = self.script_dir / "data"
        self.db_path = self.data_dir / "emm.db"
        
        # Initialize Database
        self.db = EmmDatabase(str(self.db_path))
        self.db.initialize_database()
        
        self.session_id: Optional[int] = None
        self.iteration: int = 0

        self.prd_file = self.script_dir / "prd.json"
        self.archive_dir = self.script_dir / "archive"
        self.last_branch_file = self.script_dir / ".last-branch"
        self.prompt_file = self.script_dir / "prompt.md"
        self.claude_file = self.script_dir / "CLAUDE.md"

        print_panel(
            self.console,
            "🤖 Emm Initialized",
            f"[bold blue]Emm[/bold blue] - AI Agent Loop\n"
            f"Tool: {self.tool} | Max Iterations: {self.max_iterations}\n"
            f"Feature: {self.feature_path if self.feature_path else 'Default'}",
            "green",
        )

    def close(self):
        """Cleanly close resources."""
        # Database connection is handled by its own context manager now
        pass

    def __del__(self):
        """Ensure cleanup on deletion."""
        self.close()

    # --- Tool Execution ---

    def _run_shell(self, cmd: List[str], stdin_file: Optional[Path] = None, timeout: int = 300) -> str:
        """Execute a shell command and return output."""
        try:
            stdin = None
            if stdin_file and stdin_file.exists():
                stdin = open(stdin_file, "r")

            result = subprocess.run(
                cmd,
                stdin=stdin,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            if stdin:
                stdin.close()

            # Display output
            if result.stdout:
                self.console.print(f"[dim]{result.stdout}[/dim]")
            if result.stderr:
                self.console.print(f"[yellow]{result.stderr}[/yellow]")

            return (result.stdout or "") + (result.stderr or "")

        except subprocess.TimeoutExpired:
            self.console.print(f"[red]Error: Command {cmd} timed out after {timeout} seconds[/red]")
            return "ERROR: Timeout"
        except Exception as e:
            self.console.print(f"[red]Error running command {cmd}: {e}[/red]")
            return f"ERROR: {e}"

    def _run_opencode(self) -> str:
        """Run the opencode tool."""
        # Find command logic
        opencode_cmd = ["opencode"] # Simplified for this refactor
        
        # Use existing prompt logic
        prompt_file = self.prompt_file if self.prompt_file.exists() else self.claude_file
        if not prompt_file.exists():
            return f"ERROR: No prompt file found at {self.prompt_file} or {self.claude_file}"

        return self._run_shell(opencode_cmd, stdin_file=prompt_file)

    def run_ai_tool(self) -> str:
        """Execute the AI tool with status indicator."""
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True,
            ) as progress:
                task = progress.add_task(f"Running {self.tool}...", total=None)
                output = self._run_opencode()
                progress.update(task, description=f"{self.tool} completed")
                return output
        else:
            self.console.print(f"Running {self.tool}...")
            return self._run_opencode()

    # --- Session Management ---

    def _init_session(self):
        """Initialize or resume a session."""
        if self.resume:
            self.session_id = self.db.get_last_session_id()
            if self.session_id:
                self.log_to_db("info", "agent", f"Resuming session {self.session_id}")
                self.console.print(f"[cyan]Resuming session {self.session_id}[/cyan]")
                return

        # Start new session
        feat_id = 1 # Default
        if self.feature_path and self.feature_path.exists():
            feat_id = self.db.create_feature(str(self.feature_path))
        else:
            default_feature = self.script_dir / ".features" / "sqlite.md"
            if default_feature.exists():
                feat_id = self.db.create_feature(str(default_feature))
        
        self.session_id = self.db.create_session(feat_id, self.max_iterations)
        self.log_to_db("info", "agent", f"Started new session {self.session_id}")
        self._ingest_feature_if_needed()

    def _ingest_feature_if_needed(self):
        """Load tasks from JSON into the database if not already present."""
        existing_tasks = self.db.get_tasks(self.session_id)
        if existing_tasks:
            return

        json_path = self.feature_path if (self.feature_path and self.feature_path.suffix == '.json') else None
        if not json_path:
            alt_path = self.script_dir / ".features" / "feature.json"
            if alt_path.exists():
                json_path = alt_path

        if json_path:
            data = FeatureParser.parse_json_feature(json_path)
            tasks = data.get("tasks", [])
            for task in tasks:
                self.db.create_task(self.session_id, task)
            self.log_to_db("info", "agent", f"Ingested {len(tasks)} tasks from {json_path}")

    # --- UI Helpers ---

    def log_to_db(self, level: str, component: str, message: str):
        """Log a message to the database console_logs table."""
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

    # --- Main Loop ---

    def run_iteration(self, iteration: int) -> bool:
        """Run a single loop iteration. Returns True if goal is reached."""
        self.iteration = iteration
        current_task = self.db.get_next_task(self.session_id)
        task_id = current_task['task_id'] if current_task else "unknown"
        task_title = current_task['title'] if current_task else "General Work"
        
        if current_task:
            self.db.update_task_status(self.session_id, task_id, "in_progress")

        self.console.rule(f"Iteration {iteration} | Task: {task_id}")
        self.log_to_db("info", "agent", f"Starting iteration {iteration} (Task: {task_id})")

        iter_id = self.db.create_iteration(self.session_id, iteration, task_id)
        output = self.run_ai_tool()
        self.db.update_iteration(iter_id, output, "")

        if not output:
            return False

        if "<promise>COMPLETE</promise>" in output:
            if current_task:
                self.db.update_task_status(self.session_id, task_id, "completed")
            return True

        return False

    def run(self) -> int:
        """Main execution engine."""
        try:
            self.setup_directories()
            self._init_session()
            self.display_tasks_table()

            for i in range(1, self.max_iterations + 1):
                try:
                    if self.run_iteration(i):
                        self.db.update_session_status(self.session_id, "completed")
                        print_panel(self.console, "🎉 Success", "[bold green]✅ Goal reached![/bold green]", "green")
                        return 0
                except KeyboardInterrupt:
                    self.console.print("\n[yellow]Interrupted by user[/yellow]")
                    self.db.update_session_status(self.session_id, "interrupted")
                    return 130
                except Exception as e:
                    self.console.print(f"[red]Error in iteration {i}: {e}[/red]")
                    self.log_to_db("error", "agent", f"Iteration error: {e}")

            self.db.update_session_status(self.session_id, "failed")
            print_panel(self.console, "⏰ Time's Up", "[bold yellow]Max iterations reached.[/bold yellow]", "yellow")
            return 1

        except Exception as e:
            self.console.print(f"[bold red]Fatal Error: {e}[/bold red]")
            return 1
        finally:
            self.display_tasks_table()
            self.close()

    def setup_directories(self):
        """Ensure necessary directories exist."""
        self.archive_dir.mkdir(exist_ok=True)

    def track_current_branch(self):
        """(Deprecated) Track current branch."""
        pass

    def check_branch_change(self) -> bool:
        """(Deprecated) Check for branch changes."""
        return False


def main():
    parser = argparse.ArgumentParser(description="Emm - Long-running AI agent loop")
    parser.add_argument("--feature", type=str, help="Path to JSON feature file")
    parser.add_argument("--resume", action="store_true", help="Resume last incomplete session")
    parser.add_argument("max_iterations", nargs="?", type=int, default=10, help="Max iterations")

    args = parser.parse_args()
    if args.max_iterations <= 0:
        print("Error: max_iterations must be positive", file=sys.stderr)
        sys.exit(1)

    agent = EmmAgent(max_iterations=args.max_iterations, feature_path=args.feature, resume=args.resume)
    sys.exit(agent.run())


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Emm - Long-running AI agent loop
Usage: python emm .py [--tool opencode] [max_iterations]
"""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.rule import Rule
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: 'rich' package not available. Using basic console output.")


class SimpleConsole:
    """Fallback console when rich is not available"""

    def __init__(self):
        pass

    def print(self, message=None, style=None, **kwargs):
        if message is None:
            return

        # Handle rich markup
        text = str(message)

        # Strip rich markup
        text = text.replace("[bold blue]", "").replace("[/bold blue]", "")
        text = text.replace("[cyan]", "").replace("[/cyan]", "")
        text = text.replace("[green]", "").replace("[/green]", "")
        text = text.replace("[yellow]", "").replace("[/yellow]", "")
        text = text.replace("[red]", "").replace("[/red]", "")
        text = text.replace("[dim]", "").replace("[/dim]", "")

        print(text)

    def rule(self, title=None, style=None, align=None):
        length = 80
        line = "=" * length
        if title:
            title_str = str(title)
            # Strip rich markup
            title_str = title_str.replace("[bold blue]", "").replace("[/bold blue]", "")
            title_str = title_str.replace("[cyan]", "").replace("[/cyan]", "")
            half = (length - len(title_str) - 2) // 2
            print(f"{line[:half]} {title_str} {line[half + len(title_str) + 2 :]}")
        else:
            print(line)


def print_panel(console, title, message, border_style="green"):
    """Print a panel with rich or fallback"""
    if RICH_AVAILABLE:
        console.print(Panel(message, title=title, border_style=border_style))
    else:
        # Fallback panel
        console.rule(title)
        print(str(message))
        console.rule()


class EmmAgent:
    """Long-running AI agent automation tool"""

    def __init__(self, tool: str, max_iterations: int):
        self.tool = tool
        self.max_iterations = max_iterations
        self.console = Console() if RICH_AVAILABLE else SimpleConsole()

        # Setup paths
        self.script_dir = Path(__file__).parent.resolve()
        self.prd_file = self.script_dir / "prd.json"
        self.progress_file = self.script_dir / "progress.txt"
        self.archive_dir = self.script_dir / "archive"
        self.last_branch_file = self.script_dir / ".last-branch"
        self.prompt_file = self.script_dir / "prompt.md"
        self.claude_file = self.script_dir / "CLAUDE.md"

        print_panel(
            self.console,
            "🤖 Emm Initialized",
            f"[bold blue]Emm[/bold blue] - AI Agent Loop\n"
            f"Tool: {tool} | Max Iterations: {max_iterations}",
            "green",
        )

    def setup_directories(self):
        """Ensure necessary directories exist"""
        self.archive_dir.mkdir(exist_ok=True)

    def get_current_branch_from_prd(self) -> Optional[str]:
        """Extract branch name from prd.json"""
        if not self.prd_file.exists():
            return None

        try:
            with open(self.prd_file, "r") as f:
                data = json.load(f)
                return data.get("branchName")
        except (json.JSONDecodeError, IOError) as e:
            self.console.print(
                f"[yellow]Warning: Could not read {self.prd_file}: {e}[/yellow]"
            )
            return None

    def get_last_branch(self) -> Optional[str]:
        """Get the last tracked branch"""
        if not self.last_branch_file.exists():
            return None

        try:
            return self.last_branch_file.read_text().strip()
        except IOError as e:
            self.console.print(
                f"[yellow]Warning: Could not read {self.last_branch_file}: {e}[/yellow]"
            )
            return None

    def archive_previous_run(self, last_branch: str):
        """Archive previous run files"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        folder_name = last_branch.replace("emm/", "")
        archive_folder = self.archive_dir / f"{date_str}-{folder_name}"

        self.console.print(f"[cyan]Archiving previous run: {last_branch}[/cyan]")

        try:
            archive_folder.mkdir(parents=True, exist_ok=True)

            if self.prd_file.exists():
                shutil.copy2(self.prd_file, archive_folder)

            if self.progress_file.exists():
                shutil.copy2(self.progress_file, archive_folder)

            self.console.print(f"[green]   Archived to: {archive_folder}[/green]")

            # Reset progress file for new run
            self.initialize_progress_file(reset=True)

        except Exception as e:
            self.console.print(f"[red]Error archiving previous run: {e}[/red]")
            raise

    def check_branch_change(self) -> bool:
        """Check if branch changed and archive if needed"""
        current_branch = self.get_current_branch_from_prd()
        last_branch = self.get_last_branch()

        if current_branch and last_branch and current_branch != last_branch:
            self.archive_previous_run(last_branch)
            return True

        return False

    def track_current_branch(self):
        """Track the current branch"""
        current_branch = self.get_current_branch_from_prd()
        if current_branch:
            try:
                self.last_branch_file.write_text(current_branch)
            except IOError as e:
                self.console.print(
                    f"[yellow]Warning: Could not write branch tracking: {e}[/yellow]"
                )

    def initialize_progress_file(self, reset: bool = False):
        """Initialize or reset the progress file"""
        if not self.progress_file.exists() or reset:
            try:
                with open(self.progress_file, "w") as f:
                    f.write("# Emm Progress Log\n")
                    f.write(
                        f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )
                    f.write("---\n")
            except IOError as e:
                self.console.print(f"[red]Error initializing progress file: {e}[/red]")
                raise

    def log_to_progress(self, message: str):
        """Log a message to the progress file"""
        try:
            with open(self.progress_file, "a") as f:
                f.write(f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
        except IOError as e:
            self.console.print(
                f"[yellow]Warning: Could not write to progress file: {e}[/yellow]"
            )

    def run_ai_tool(self) -> str:
        """Execute the selected AI tool and return output"""
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True,
            ) as progress:
                task = progress.add_task(f"Running {self.tool}...", total=None)
                return self._execute_tool(progress, task)
        else:
            # Simple progress for fallback
            self.console.print(f"Running {self.tool}...")
            return self._execute_tool(None, None)

    def _execute_tool(self, progress, task) -> str:
        """Execute the AI tool with given progress context"""
        try:
            if self.tool == "opencode":
                # Try to find opencode in the current environment
                # First check if it's available as a command
                opencode_cmd = None

                # Try different possible opencode command names
                possible_cmds = [
                    "opencode",
                    "/usr/local/bin/opencode",
                    "python -m opencode",
                ]

                for cmd_name in possible_cmds:
                    try:
                        # Test if command exists
                        test_cmd = cmd_name.split()[0]
                        subprocess.run(
                            [test_cmd, "--version"],
                            capture_output=True,
                            check=False,
                            timeout=5,
                        )
                        opencode_cmd = cmd_name.split()
                        break
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        continue

                if opencode_cmd is None:
                    # Fallback to a simple test command for demo purposes
                    opencode_cmd = [
                        "echo",
                        "OpenCode simulation - would normally run opencode here",
                    ]

                # Use the prompt file as input
                prompt_file = (
                    self.prompt_file if self.prompt_file.exists() else self.claude_file
                )
                if not prompt_file.exists():
                    raise FileNotFoundError(
                        f"No prompt file found. Tried: {self.prompt_file} and {self.claude_file}"
                    )

                with open(prompt_file, "r") as f:
                    result = subprocess.run(
                        opencode_cmd,
                        stdin=f,
                        capture_output=True,
                        text=True,
                        timeout=300,  # 5 minute timeout
                    )
            else:
                raise ValueError(f"Unsupported tool: {self.tool}")

            if progress and task:
                progress.update(task, description=f"{self.tool} completed")
            else:
                self.console.print(f"{self.tool} completed")

            # Display output (tee behavior)
            if result.stdout:
                self.console.print(f"[dim]{result.stdout}[/dim]")
            if result.stderr:
                self.console.print(f"[yellow]{result.stderr}[/yellow]")

            return result.stdout + result.stderr

        except subprocess.TimeoutExpired:
            if progress and task:
                progress.update(task, description=f"{self.tool} timed out")
            self.console.print(
                f"[red]Error: {self.tool} command timed out after 5 minutes[/red]"
            )
            return ""
        except FileNotFoundError as e:
            if progress and task:
                progress.update(task, description="Command not found")
            self.console.print(f"[red]Error: {e}[/red]")
            return ""
        except Exception as e:
            if progress and task:
                progress.update(task, description="Error occurred")
            self.console.print(f"[red]Error running {self.tool}: {e}[/red]")
            return ""

    def check_completion(self, output: str) -> bool:
        """Check if the completion signal is present in output"""
        return "<promise>COMPLETE</promise>" in output

    def run_iteration(self, iteration: int) -> bool:
        """Run a single iteration and return True if completed"""
        self.console.print()
        if RICH_AVAILABLE:
            self.console.print(
                Rule(
                    f"[bold blue]Emm Iteration {iteration} of {self.max_iterations}[/bold blue] ([cyan]{self.tool}[/cyan])",
                    align="center",
                )
            )
        else:
            self.console.rule(
                f"Emm Iteration {iteration} of {self.max_iterations} ({self.tool})"
            )

        self.log_to_progress(f"Starting iteration {iteration}")

        # Run the AI tool
        output = self.run_ai_tool()

        if not output:
            self.console.print(
                "[yellow]Iteration produced no output, continuing...[/yellow]"
            )
            self.log_to_progress(f"Iteration {iteration} - No output")
            return False

        # Check for completion signal
        if self.check_completion(output):
            self.console.print()
            print_panel(
                self.console,   
                "🎉 Success",
                f"[bold green]✅ Emm completed all tasks![/bold green]\n"
                f"Completed at iteration {iteration} of {self.max_iterations}",
                "green",
            )
            self.log_to_progress(f"Iteration {iteration} - COMPLETED")
            return True

        self.console.print(
            f"[green]Iteration {iteration} complete. Continuing...[/green]"
        )
        self.log_to_progress(f"Iteration {iteration} - Completed")
        return False

    def run(self):
        """Main execution loop"""
        try:
            self.setup_directories()
            self.check_branch_change()
            self.track_current_branch()
            self.initialize_progress_file()

            self.log_to_progress(
                f"Started Emm - Tool: {self.tool}, Max iterations: {self.max_iterations}"
            )

            for i in range(1, self.max_iterations + 1):
                try:
                    if self.run_iteration(i):
                        return 0
                except KeyboardInterrupt:
                    self.console.print("\n[yellow]Emm interrupted by user[/yellow]")
                    self.log_to_progress("Interrupted by user")
                    return 130
                except Exception as e:
                    self.console.print(
                        f"[red]Critical error in iteration {i}: {e}[/red]"
                    )
                    self.log_to_progress(f"Critical error in iteration {i}: {e}")
                    # Continue to next iteration instead of exiting

            # Max iterations reached without completion
            self.console.print()
            print_panel(
                self.console,
                "⏰ Time's Up",
                f"[bold yellow]⚠️  Emm reached max iterations ({self.max_iterations}) without completing all tasks.[/bold yellow]\n"
                f"Check {self.progress_file} for status.",
                "yellow",
            )
            self.log_to_progress("Reached max iterations without completion")
            return 1

        except Exception as e:
            self.console.print(f"[red]Fatal error: {e}[/red]")
            return 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Emm - Long-running AI agent loop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--tool",
        choices=["opencode"],
        default="opencode",
        help="AI tool to use (default: opencode)",
    )

    parser.add_argument(
        "max_iterations",
        nargs="?",
        type=int,
        default=10,
        help="Maximum number of iterations (default: 10)",
    )

    args = parser.parse_args()

    # Validate max_iterations
    if args.max_iterations <= 0:
        print("Error: max_iterations must be a positive integer", file=sys.stderr)
        sys.exit(1)

    # Create and run the agent
    agent = EmmAgent(tool=args.tool, max_iterations=args.max_iterations)
    sys.exit(agent.run())


if __name__ == "__main__":
    main()

"""
Tool execution runners for Emm.
"""

import subprocess
from pathlib import Path
from typing import Optional, List, Any
from emm import config

class ToolRunner:
    """Base class/namespace for tool execution."""
    
    def __init__(self, console: Any):
        self.console = console

    def run_shell(self, cmd: List[str], stdin_file: Optional[Path] = None, timeout: int = config.COMMAND_TIMEOUT) -> str:
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

    def run_opencode(self) -> str:
        """Run the opencode tool specifically."""
        opencode_cmd = ["opencode"]
        
        # Use config for prompt selection
        prompt_file = config.PROMPT_FILE if config.PROMPT_FILE.exists() else config.CLAUDE_FILE
        if not prompt_file.exists():
            return f"ERROR: No prompt file found at {config.PROMPT_FILE} or {config.CLAUDE_FILE}"

        return self.run_shell(opencode_cmd, stdin_file=prompt_file)

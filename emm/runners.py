import subprocess
from pathlib import Path

from emm import config
from emm.logger import DualLogger


class ToolRunner:
    """Base class/namespace for tool execution."""

    def __init__(self, log: DualLogger):
        """
        Args:
            log: A DualLogger instance.
        """
        self.log = log

    def run_shell(self, cmd: list[str], stdin_str: str | None = None, timeout: int = config.COMMAND_TIMEOUT, cwd: Path | None = None) -> str:
        """Execute a shell command and return output."""
        try:
            result = subprocess.run(
                cmd,
                input=stdin_str,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )

            # Display output
            if result.stdout:
                self.log.info(result.stdout)
            if result.stderr:
                self.log.warning(result.stderr)

            return (result.stdout or "") + (result.stderr or "")

        except subprocess.TimeoutExpired:
            self.log.error(f"Error: Command {cmd} timed out after {timeout} seconds")
            return "ERROR: Timeout"
        except Exception as e:
            self.log.error(f"Error running command {cmd}: {e}")
            return f"ERROR: {e}"

    def _build_prompt(self, task: dict | None = None) -> str:
        """Construct the system prompt with optional task context."""
        if not config.PROMPT_FILE.exists():
            return f"ERROR: System prompt not found at {config.PROMPT_FILE}"

        prompt = config.PROMPT_FILE.read_text()
        if task:
            prompt += f"\n\n--- CURRENT TASK: {task.get('task_id', 'Unknown')} ---\n"
            prompt += f"TITLE: {task.get('title', 'No Title')}\n"
            prompt += f"DESCRIPTION: {task.get('description', '')}\n\nACCEPTANCE CRITERIA:\n"
            for criteria in task.get('acceptance_criteria', []):
                prompt += f"- [ ] {criteria}\n"
        return prompt

    def run_opencode(self, task: dict | None = None, cwd: Path | None = None) -> str:
        """Run the opencode tool with context."""
        prompt = self._build_prompt(task)
        if prompt.startswith("ERROR:"):
            return prompt
        return self.run_shell(["opencode"], stdin_str=prompt, cwd=cwd)

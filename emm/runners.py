import subprocess
from pathlib import Path
from typing import Optional, List, Any, Dict
from emm.logger import DualLogger
from emm import config

class ToolRunner:
    """Base class/namespace for tool execution."""
    
    def __init__(self, log: DualLogger):
        """
        Args:
            log: A DualLogger instance.
        """
        self.log = log

    def run_shell(self, cmd: List[str], stdin_str: Optional[str] = None, timeout: int = config.COMMAND_TIMEOUT) -> str:
        """Execute a shell command and return output."""
        try:
            result = subprocess.run(
                cmd,
                input=stdin_str,
                capture_output=True,
                text=True,
                timeout=timeout,
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

    def run_opencode(self, task: Optional[Dict] = None) -> str:
        """Run the opencode tool with context."""
        opencode_cmd = ["opencode"]
        
        # 1. Load System Prompt
        if not config.PROMPT_FILE.exists():
            return f"ERROR: System prompt not found at {config.PROMPT_FILE}"
        
        prompt_content = config.PROMPT_FILE.read_text()
        
        # 2. Inject Task Context (if available)
        if task:
            task_context = f"""
\n\n--- CURRENT TASK: {task.get('task_id', 'Unknown')} ---
TITLE: {task.get('title', 'No Title')}
DESCRIPTION: {task.get('description', '')}

ACCEPTANCE CRITERIA:
"""
            for criteria in task.get('acceptance_criteria', []):
                task_context += f"- [ ] {criteria}\n"
            
            prompt_content += task_context

        return self.run_shell(opencode_cmd, stdin_str=prompt_content)

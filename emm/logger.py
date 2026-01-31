from typing import Optional, Any, List, Dict
from contextlib import contextmanager
import sys

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

def get_console():
    """Factory for console (Rich or Simple)."""
    if RICH_AVAILABLE:
        return Console()
    
    # Mini-SimpleConsole for consistency
    class SimpleConsole:
        def print(self, m=None, **k): print(m if m else "")
            
        def rule(self, t=None, **k):
            print(f"\n--- {t} ---" if t else "\n----------")
    return SimpleConsole()

class DualLogger:
    """A logger that writes to both a console and a database."""

    def __init__(self, console: Optional[Any] = None, db: Optional[Any] = None, session_id: Optional[int] = None):
        """
        Args:
            console: An optional console object. If not provided, one will be created.
            db: An optional database object with a log_message method.
            session_id: The current session ID for database logging.
        """
        self.console = console if console else get_console()
        self.db = db
        self.session_id = session_id
        self.iteration = 0

    def set_session_id(self, session_id: int):
        """Update the session ID after it is created/loaded."""
        self.session_id = session_id

    def set_iteration(self, iteration: int):
        """Update the current iteration for logging context."""
        self.iteration = iteration

    def _log(self, message: str, level: str, style: Optional[str] = None):
        """Internal logging implementation.
        
        Args:
            message: The message to log.
            level: log level (info, success, error, warning).
            style: optional rich style for console output.
        """
        # 1. Console Output
        if not style:
            styles = {
                "info": "cyan",
                "success": "bold green",
                "error": "bold red",
                "warning": "bold yellow"
            }
            style = styles.get(level, "white")
        
        self.console.print(f"[{style}]{message}[/{style}]")

        # 2. Database Output
        if self.db and self.session_id:
            try:
                # We hardcode 'agent' as the component for now as it's the primary context
                self.db.log_message(self.session_id, self.iteration, level, "agent", message)
            except Exception as e:
                # Fallback print if DB fails
                self.console.print(f"[dim yellow]DB Log Error: {e}[/dim yellow]")

    # UI Methods
    def rule(self, text: str):
        """Display a horizontal rule with text and log to DB."""
        self.console.rule(text)
        if self.db and self.session_id:
            try:
                self.db.log_message(self.session_id, self.iteration, "info", "agent", f"--- {text} ---")
            except: pass

    def table(self, title: str, columns: List[str], rows: List[List[str]], header_style: str = "bold magenta"):
        """Display a formatted table and log a summary to DB."""
        if RICH_AVAILABLE:
            table = Table(title=title, show_header=True, header_style=header_style)
            for col in columns:
                table.add_column(col)
            for row in rows:
                table.add_row(*row)
            self.console.print(table)
            self.console.print()
        else:
            # Simple fallback for non-rich console
            print(f"\n--- {title} ---")
            print(" | ".join(columns))
            for row in rows:
                print(" | ".join(row))
            print()
            
        # Log summary to DB regardless of display mode
        if self.db and self.session_id:
            summary = f"TABLE: {title}\n" + " | ".join(columns) + "\n"
            summary += "\n".join([" | ".join(row) for row in rows])
            try:
                self.db.log_message(self.session_id, self.iteration, "info", "agent", summary)
            except: pass

    @contextmanager
    def status_indicator(self, start_msg: str, end_msg: str):
        """Context manager for showing a progress status and auditing to DB."""
        # Log to DB first for audit trail
        if self.db and self.session_id:
            try:
                self.db.log_message(self.session_id, self.iteration, "info", "agent", start_msg)
            except: pass
            
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True,
            ) as progress:
                task = progress.add_task(start_msg, total=None)
                yield
                progress.update(task, description=end_msg)
        else:
            self.console.print(f"[cyan]{start_msg}[/cyan]")
            yield
            self.console.print(f"[cyan]{end_msg}[/cyan]")

        # Log completion to DB
        if self.db and self.session_id:
            try:
                self.db.log_message(self.session_id, self.iteration, "info", "agent", end_msg)
            except: pass

    # Ergonomic Shortcuts
    def info(self, message: str):
        self._log(message, "info")
        
    def success(self, message: str):
        self._log(message, "success")
        
    def warning(self, message: str):
        self._log(message, "warning")
        
    def error(self, message: str):
        self._log(message, "error")

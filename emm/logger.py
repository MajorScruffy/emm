from typing import Optional, Any, List, Dict
from contextlib import contextmanager
import sys
import logging

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# 2. Handlers
class EmmConsoleHandler(logging.Handler):
    """Handler for formatted console output (Rich or Simple)."""
    def __init__(self, console):
        super().__init__()
        self.console = console
        self.styles = {
            "INFO": "cyan",
            "ERROR": "bold red",
            "WARNING": "bold yellow",
            "DEBUG": "dim white"
        }

    def emit(self, record):
        try:
            msg = self.format(record)
            style = self.styles.get(record.levelname, "white")
            self.console.print(f"[{style}]{msg}[/{style}]")
        except Exception:
            self.handleError(record)

class EmmDatabaseHandler(logging.Handler):
    """Handler for SQLite database logging."""
    def __init__(self, db, logger_proxy):
        super().__init__()
        self.db = db
        self.logger_proxy = logger_proxy

    def emit(self, record):
        if not self.db or not self.logger_proxy.session_id:
            return
        try:
            msg = self.format(record)
            level = record.levelname.lower()
            # Default to 'agent' component for general logging
            self.db.log_message(
                self.logger_proxy.session_id, 
                self.logger_proxy.iteration, 
                level, 
                "agent", 
                msg
            )
        except Exception:
            self.handleError(record)

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
    """A logger that wraps standard logging and provides UI extras."""

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

        # Setup internal standard logger
        self.logger = logging.getLogger("emm")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False # Avoid double logging if root has handlers

        # Remove old handlers if existing (re-init safety)
        for h in self.logger.handlers[:]:
            self.logger.removeHandler(h)

        # Add our handlers
        self.console_handler = EmmConsoleHandler(self.console)
        self.db_handler = EmmDatabaseHandler(self.db, self)
        
        self.logger.addHandler(self.console_handler)
        self.logger.addHandler(self.db_handler)

    def set_session_id(self, session_id: int):
        """Update the session ID after it is created/loaded."""
        self.session_id = session_id

    def set_iteration(self, iteration: int):
        """Update the current iteration for logging context."""
        self.iteration = iteration

    # UI Methods
    def rule(self, text: str):
        """Display a horizontal rule and log it as info."""
        self.console.rule(text)
        self.info(f"--- {text} ---")

    def table(self, title: str, columns: List[str], rows: List[List[str]], header_style: str = "bold magenta"):
        """Display a formatted table and log a summary."""
        if RICH_AVAILABLE:
            table = Table(title=title, show_header=True, header_style=header_style)
            for col in columns:
                table.add_column(col)
            for row in rows:
                table.add_row(*row)
            self.console.print(table)
            self.console.print()
        else:
            print(f"\n--- {title} ---")
            print(" | ".join(columns))
            for row in rows:
                print(" | ".join(row))
            print()
            
        # Log summary
        summary = f"TABLE: {title}\n" + " | ".join(columns) + "\n"
        summary += "\n".join([" | ".join(row) for row in rows])
        self.info(summary)

    @contextmanager
    def status_indicator(self, start_msg: str, end_msg: str):
        """Context manager for showing a progress status and auditing."""
        self.info(start_msg)
            
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

        self.info(end_msg)

    # Ergonomic Shortcuts (Proxies to standard logging)
    def info(self, message: str):
        self.logger.info(message)
        
    def warning(self, message: str):
        self.logger.warning(message)
        
    def error(self, message: str):
        self.logger.error(message)

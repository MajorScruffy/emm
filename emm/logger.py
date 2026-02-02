from typing import Optional, Any, List, Dict
from contextlib import contextmanager
import logging

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

class EmmConsoleHandler(logging.Handler):
    def emit(self, record):
        message = self.format(record)
        if RICH_AVAILABLE:
            style = {"INFO": "cyan", "ERROR": "bold red", "WARNING": "bold yellow"}.get(record.levelname, "white")
            self.console.print(f"[{style}]{message}[/{style}]")
        else: self.console.print(message)

    def __init__(self, console):
        super().__init__()
        self.console = console

class EmmDatabaseHandler(logging.Handler):
    def emit(self, record):
        if self.db and self.logger_proxy.session_id:
            self.db.log_message(self.logger_proxy.session_id, self.logger_proxy.iteration, record.levelname.lower(), self.format(record))

    def __init__(self, db, logger_proxy):
        super().__init__(); self.db = db; self.logger_proxy = logger_proxy

def get_console():
    if RICH_AVAILABLE: return Console()
    class SimpleConsole:
        def print(self, message=None, **kwargs): print(message or "")
        def rule(self, title=None, **kwargs): print(f"\n--- {title} ---" if title else "\n----------")
        @contextmanager
        def status(self, message, **kwargs):
            print(message); yield; print(f"{message} done.")
    return SimpleConsole()

class DualLogger:
    def __init__(self, console: Optional[Any] = None, db: Optional[Any] = None, session_id: Optional[int] = None):
        self.console = console or get_console(); self.db = db; self.session_id = session_id; self.iteration = 0
        self.logger = logging.getLogger("emm"); self.logger.setLevel(logging.DEBUG); self.logger.propagate = False
        for handler in self.logger.handlers[:]: self.logger.removeHandler(handler)
        self.logger.addHandler(EmmConsoleHandler(self.console))
        self.logger.addHandler(EmmDatabaseHandler(self.db, self))

    def info(self, message): self.logger.info(message)
    def warning(self, message): self.logger.warning(message)
    def error(self, message): self.logger.error(message)
    def debug(self, message): self.logger.debug(message)

    def set_session_id(self, session_id): self.session_id = session_id
    def set_iteration(self, iteration): self.iteration = iteration
    def rule(self, title): self.console.rule(title); self.info(f"--- {title} ---")

    def table(self, title, columns, rows):
        if RICH_AVAILABLE:
            table = Table(title=title, show_header=True, header_style="bold magenta")
            for column in columns: table.add_column(column)
            for row in rows: table.add_row(*row)
            self.console.print(table)
        else:
            print(f"\n--- {title} ---\n" + " | ".join(columns))
            for row in rows: print(" | ".join(row))
        self.info(f"TABLE: {title}\n" + " | ".join(columns) + "\n" + "\n".join([" | ".join(row) for row in rows]))

    @contextmanager
    def status_indicator(self, start_message, end_message):
        self.info(start_message)
        with self.console.status(start_message): yield
        self.info(end_message)

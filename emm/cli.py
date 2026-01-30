"""
CLI interface for Emm.
"""

import argparse
import sys
from emm.core import EmmAgent
from emm.database import EmmDatabase
from emm import config

def get_console():
    """Factory for console (Rich or Simple)."""
    try:
        from rich.console import Console
        return Console()
    except ImportError:
        # Mini-SimpleConsole for the CLI entry point
        class SimpleConsole:
            def print(self, m=None, **k): print(m if m else "")
                
            def rule(self, t=None, **k):
                print(f"--- {t} ---" if t else "----------")
        return SimpleConsole()

def main():
    parser = argparse.ArgumentParser(description="Emm - Long-running AI agent loop")
    parser.add_argument("--feature", type=str, help="Path to JSON feature file")
    parser.add_argument("--resume", action="store_true", help="Resume last incomplete session")
    parser.add_argument("max_iterations", nargs="?", type=int, default=config.DEFAULT_ITERATIONS, help="Max iterations")

    args = parser.parse_args()
    
    console = get_console()
    db = EmmDatabase(str(config.DB_PATH))
    db.initialize_database()
    
    agent = EmmAgent(
        db=db,
        console=console,
        max_iterations=args.max_iterations,
        feature_path=args.feature,
        resume=args.resume
    )
    
    sys.exit(agent.run())

if __name__ == "__main__":
    main()

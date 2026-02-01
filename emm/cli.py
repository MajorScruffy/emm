"""
CLI interface for Emm.
"""

import argparse
import sys
from emm.core import EmmAgent
from emm.database import EmmDatabase
from emm.logger import DualLogger
from emm import config

def main():
    parser = argparse.ArgumentParser(description="Emm - Long-running AI agent loop")
    parser.add_argument("--project", type=str, help="Path to JSON project file")
    parser.add_argument("--resume", action="store_true", help="Resume last incomplete session")
    parser.add_argument("max_iterations", nargs="?", type=int, default=config.DEFAULT_ITERATIONS, help="Max iterations")

    args = parser.parse_args()
    
    db = EmmDatabase(str(config.DB_PATH))
    db.initialize_database()
    
    logger = DualLogger(db=db)
    
    agent = EmmAgent(
        db=db,
        log=logger,
        max_iterations=args.max_iterations,
        project_path=args.project,
        resume=args.resume
    )
    
    sys.exit(agent.run())

if __name__ == "__main__":
    main()

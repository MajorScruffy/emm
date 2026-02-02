
import argparse
import sys
import json
from pathlib import Path
from emm.core import EmmAgent
from emm.database import EmmDatabase
from emm.logger import DualLogger
from emm import config

def get_session_context():
    """Attempt to find session ID from local .session.json."""
    session_file = Path(".session.json")
    if session_file.exists():
        try:
            data = json.loads(session_file.read_text())
            return data.get("session_id")
        except:
            pass
    return None

def cmd_run(args):
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

def cmd_task(args):
    db = EmmDatabase(str(config.DB_PATH))
    session_id = args.session or get_session_context()
    
    if not session_id:
        print("Error: No session ID provided and .session.json not found.")
        sys.exit(1)

    if args.task_command == "create":
        # Generate next ID
        highest = db.get_highest_task_id(session_id)
        next_id = f"{highest + 1:03d}"
        
        task_data = {
            "id": next_id,
            "title": args.title,
            "description": args.description,
            "acceptanceCriteria": args.criteria or []
        }
        db.create_task(session_id, task_data)
        print(f"Task {next_id} created in session {session_id}")

    elif args.task_command == "update":
        db.update_task_status(session_id, args.task_id, args.status)
        print(f"Task {args.task_id} status updated to {args.status}")

    elif args.task_command == "history":
        iters = db.get_iterations_for_task(session_id, args.task_id)
        if not iters:
            print(f"No history found for task {args.task_id}")
            return
        for i in iters:
            print(f"\n--- Iteration {i['iteration_number']} ---")
            print(i['opencode_output'])

def main():
    parser = argparse.ArgumentParser(description="Emm - Parallel AI Agent Orchestrator")
    subparsers = parser.add_subparsers(dest="command")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run the agent loop (default)")
    run_parser.add_argument("--project", type=str, help="Path to JSON project file")
    run_parser.add_argument("--resume", action="store_true", help="Resume last incomplete session")
    run_parser.add_argument("max_iterations", nargs="?", type=int, default=config.DEFAULT_ITERATIONS, help="Max iterations")
    run_parser.set_defaults(func=cmd_run)

    # Task command
    task_parser = subparsers.add_parser("task", help="Manage tasks")
    task_parser.add_argument("--session", type=int, help="Session ID (defaults to .session.json context)")
    task_subparsers = task_parser.add_subparsers(dest="task_command")
    
    create_parser = task_subparsers.add_parser("create", help="Create a follow-up task")
    create_parser.add_argument("--title", required=True, help="Task title")
    create_parser.add_argument("--description", required=True, help="Task description")
    create_parser.add_argument("--criteria", nargs="*", help="Acceptance criteria")
    
    update_parser = task_subparsers.add_parser("update", help="Update task status")
    update_parser.add_argument("task_id", help="Task ID (e.g. 001)")
    update_parser.add_argument("status", choices=["pending", "in_progress", "completed", "failed"], help="New status")
    
    history_parser = task_subparsers.add_parser("history", help="Show task iteration history")
    history_parser.add_argument("task_id", help="Task ID (e.g. 001)")
    
    task_parser.set_defaults(func=cmd_task)

    args = parser.parse_args()
    
    if not args.command:
        # Default behavior: run
        args.max_iterations = config.DEFAULT_ITERATIONS
        args.project = None
        args.resume = False
        cmd_run(args)
    else:
        args.func(args)

if __name__ == "__main__":
    main()

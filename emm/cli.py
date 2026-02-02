import argparse, sys, json
from pathlib import Path
from emm.core import EmmAgent
from emm.database import EmmDatabase
from emm.logger import DualLogger
from emm import config

def get_session_context():
    session_file = Path(".session.json")
    if session_file.exists():
        try:
            data = json.loads(session_file.read_text())
            return data.get("session_id")
        except: pass
    return None

def cmd_run(args):
    database = EmmDatabase(str(config.DB_PATH))
    database.run_migrations()
    logger = DualLogger(db=database)
    agent = EmmAgent(database, logger, args.max_iterations, args.project, args.resume)
    sys.exit(agent.run())

def cmd_task(args):
    database = EmmDatabase(str(config.DB_PATH))
    session_id = args.session or get_session_context()
    if not session_id:
        print("Error: No session ID provided and .session.json not found.")
        sys.exit(1)

    if args.task_command == "create":
        task_id = f"{database.get_highest_task_id(session_id) + 1:03d}"
        task_data = {"id": task_id, "title": args.title, "description": args.description, "criteria": args.criteria or []}
        database.create_task(session_id, task_data)
        print(f"Task {task_id} created in session {session_id}")
    elif args.task_command == "update":
        database.update_task_status(session_id, args.task_id, args.status)
        print(f"Task {args.task_id} status updated to {args.status}")
    elif args.task_command == "history":
        iterations = database.get_iterations_for_task(session_id, args.task_id)
        if not iterations:
            print(f"No history found for task {args.task_id}")
            return
        for iteration in iterations:
            print(f"\n--- Iteration {iteration['iteration_number']} ---")
            print(iteration['opencode_output'])

def main():
    parser = argparse.ArgumentParser(description="Emm - Parallel AI Agent Orchestrator")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the agent loop")
    run_parser.add_argument("--project", help="Path to JSON project file")
    run_parser.add_argument("--resume", action="store_true", help="Resume last incomplete session")
    run_parser.add_argument("max_iterations", nargs="?", type=int, default=config.DEFAULT_ITERATIONS, help="Max iterations")
    run_parser.set_defaults(func=cmd_run)

    task_parser = subparsers.add_parser("task", help="Manage tasks")
    task_parser.add_argument("--session", type=int, help="Session ID")
    task_subparsers = task_parser.add_subparsers(dest="task_command")
    
    create_parser = task_subparsers.add_parser("create", help="Create a follow-up task")
    create_parser.add_argument("--title", required=True)
    create_parser.add_argument("--description", required=True)
    create_parser.add_argument("--criteria", nargs="*")
    
    update_parser = task_subparsers.add_parser("update", help="Update task status")
    update_parser.add_argument("task_id", help="Task ID (e.g. 001)")
    update_parser.add_argument("status", choices=["pending", "in_progress", "completed", "failed"])
    
    history_parser = task_subparsers.add_parser("history", help="Show task history")
    history_parser.add_argument("task_id")
    task_parser.set_defaults(func=cmd_task)

    args = parser.parse_args()
    if not args.command:
        args.max_iterations, args.project, args.resume = config.DEFAULT_ITERATIONS, None, False
        cmd_run(args)
    else:
        args.func(args)

if __name__ == "__main__": main()

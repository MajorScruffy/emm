import argparse
import json
import sys
from pathlib import Path

from emm import config
from emm.core import EmmAgent
from emm.database import EmmDatabase
from emm.logger import DualLogger


def get_session_context():
    session_file = Path(".session.json")
    if session_file.exists():
        try:
            data = json.loads(session_file.read_text())
            return data.get("session_id")
        except (json.JSONDecodeError, KeyError):
            pass
    return None


def cmd_run(args):
    database = EmmDatabase(str(config.DB_PATH))
    database.run_migrations()
    logger = DualLogger(db=database)
    agent = EmmAgent(
        database,
        logger,
        args.max_iterations,
        args.project,
        args.resume,
        run_once=args.once,
    )
    sys.exit(agent.run())


def cmd_task(args):
    database = EmmDatabase(str(config.DB_PATH))
    session_id = args.session or get_session_context()
    if not session_id:
        print("Error: No session ID provided and .session.json not found.")
        sys.exit(1)

    if args.task_command == "create":
        task_id = f"{database.get_highest_task_id(session_id) + 1:03d}"
        task_data = {
            "id": task_id,
            "title": args.title,
            "description": args.description,
            "criteria": args.criteria or [],
        }
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
            print(iteration["opencode_output"])


def cmd_list(args):
    database = EmmDatabase(str(config.DB_PATH))
    database.run_migrations()
    logger = DualLogger(db=database)

    if args.list_command == "projects":
        projects = database.get_all_projects()
        rows = [[str(p["id"]), p["name"], p["created_at"]] for p in projects]
        logger.table("Projects", ["ID", "Name", "Created At"], rows)
    elif args.list_command == "sessions":
        sessions = database.get_all_sessions()
        rows = [
            [
                str(s["id"]),
                s["project_name"],
                s["status"],
                str(s["completed_tasks"]),
                s["created_at"],
            ]
            for s in sessions
        ]
        logger.table(
            "Sessions", ["ID", "Project", "Status", "Tasks Done", "Created At"], rows
        )
    elif args.list_command == "tasks":
        session_id = args.session or get_session_context()
        if not session_id:
            logger.error("No session ID specified.")
            return
        tasks = database.get_tasks(session_id)
        rows = [[t["task_id"], t["title"], t["status"]] for t in tasks]
        logger.table(f"Tasks for Session {session_id}", ["ID", "Title", "Status"], rows)


def cmd_cleanup(args):
    database = EmmDatabase(str(config.DB_PATH))
    database.run_migrations()
    logger = DualLogger(db=database)
    from emm.git_utils import WorktreeManager

    wm = WorktreeManager(log=logger)
    worktrees = wm.get_all_worktrees()
    active_sessions = [
        str(s["id"])
        for s in database.execute(
            "SELECT id FROM sessions WHERE status NOT IN ('completed', 'failed', 'interrupted')"
        )
    ]

    for wt in worktrees:
        if wt.startswith("session-"):
            session_id = wt.replace("session-", "")
            if session_id not in active_sessions:
                if args.dry_run:
                    logger.info(f"[Dry Run] Would cleanup worktree: {wt}")
                else:
                    wm.cleanup_worktree(int(session_id))
            else:
                logger.debug(f"Keeping active worktree: {wt}")


def main():
    parser = argparse.ArgumentParser(description="Emm - Parallel AI Agent Orchestrator")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the agent loop")
    run_parser.add_argument("--project", help="Path to JSON project file")
    run_parser.add_argument(
        "--resume", action="store_true", help="Resume last incomplete session"
    )
    run_parser.add_argument(
        "--once", "-1", action="store_true", help="Run only one project and exit"
    )
    run_parser.add_argument(
        "max_iterations",
        nargs="?",
        type=int,
        default=config.DEFAULT_ITERATIONS,
        help="Max iterations",
    )
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
    update_parser.add_argument(
        "status", choices=["pending", "in_progress", "completed", "failed"]
    )

    history_parser = task_subparsers.add_parser("history", help="Show task history")
    history_parser.add_argument("task_id")
    task_parser.set_defaults(func=cmd_task)

    list_parser = subparsers.add_parser("list", help="List resources")
    list_subparsers = list_parser.add_subparsers(dest="list_command")
    list_subparsers.add_parser("projects", help="List ingested projects")
    list_subparsers.add_parser("sessions", help="List execution sessions")
    tasks_list_parser = list_subparsers.add_parser("tasks", help="List tasks for a session")
    tasks_list_parser.add_argument("--session", type=int, help="Session ID")
    list_parser.set_defaults(func=cmd_list)

    cleanup_parser = subparsers.add_parser("cleanup", help="Cleanup dead worktrees")
    cleanup_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be removed"
    )
    cleanup_parser.set_defaults(func=cmd_cleanup)

    args = parser.parse_args()
    if not args.command:
        args.max_iterations, args.project, args.resume = (
            config.DEFAULT_ITERATIONS,
            None,
            False,
        )
        cmd_run(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()

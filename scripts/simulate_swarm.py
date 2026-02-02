
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from emm.database import EmmDatabase


def main():
    # 1. Setup Environment
    test_root = Path(tempfile.mkdtemp())
    print(f"Simulation Root: {test_root}")

    # Fake Git Repo
    repo_dir = test_root / "repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    (repo_dir / "main.py").write_text("print('hello')")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Init"], cwd=repo_dir, check=True, capture_output=True)

    db_path = test_root / "emm.db"
    projects_dir = test_root / ".projects"
    projects_dir.mkdir()

    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    env["EMM_DB_PATH"] = str(db_path)
    env["EMM_PROJECTS_DIR"] = str(projects_dir)

    print("--- 🏁 STARTING SWARM SIMULATION ---")

    # 2. Ingest a project
    project_file = projects_dir / "swarm-test.json"
    project_file.write_text(json.dumps({
        "project": "SwarmTest",
        "branchName": "emm/test",
        "tasks": [{
            "id": "001",
            "title": "Initial Implementation",
            "description": "Create a new file.",
            "acceptanceCriteria": ["file.txt exists"]
        }]
    }))

    db = EmmDatabase(str(db_path))
    db.initialize_database()
    db.create_project(str(project_file))

    # Run Agent Initialization
    from emm.core import EmmAgent
    from emm.logger import DualLogger
    log = DualLogger()
    agent = EmmAgent(db=db, log=log, work_dir=repo_dir)
    agent._init_session()

    session_id = agent.session_id
    wt_path = agent.worktree_path

    try:
        print(f"[Agent A] Claimed Session {session_id}")
        print(f"[Agent A] Workspace: {wt_path}")

        # Simulating Agent A running: emm task create --title "Review A" ...
        print("[Agent A] Task 001 finished. Delegating review...")
        res = subprocess.run(
            [sys.executable, "-m", "emm.cli", "task", "create",
             "--title", "Review Implementation",
             "--description", "Check file.txt is correct"],
            cwd=wt_path, env=env, capture_output=True, text=True
        )
        print(f"STDOUT: {res.stdout}")

        # Verify US-002 exists in DB
        tasks = db.get_tasks(session_id)
        print(f"Current Tasks in DB: {[t['task_id'] for t in tasks]}")

        if any(t['task_id'] == '002' for t in tasks):
            print("✅ SUCCESS: Agent A successfully delegated Task 002!")
        else:
            print("❌ FAILURE: Task 002 not found in DB.")

    finally:
        agent.worktree_manager.cleanup_worktree(session_id)
        shutil.rmtree(test_root)

if __name__ == "__main__":
    main()

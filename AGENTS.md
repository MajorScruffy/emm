# AGENTS.md

## ⚡ System Architecture: `emm`

**`emm`** (Emm) is a specialized autonomous agent runtime designed for long-running, iterative coding tasks. It operates by claiming "Projects" from a database and executing them via an "Opencode" loop.

### 🏗 Core Components

- **`EmmAgent` (`emm.core`)**: The central controller. Manages the lifecycle of a `Session` (claiming work -> loop -> completion).
- **`EmmDatabase` (`emm.database`)**: A SQLite-backed persistence layer using **WAL mode** and **`BEGIN IMMEDIATE`** transactions for atomic concurrency.
    - **Tables**: `projects`, `sessions`, `tasks`, `iterations`, `console_logs`.
    - **Migrations**: File-based SQL in `emm/migrations/`.
- **`ToolRunner` (`emm.runners`)**: The execution interface for AI tools. Currently wraps the generic "opencode" tool.
- **`DualLogger` (`emm.logger`)**: Splits output between a rich console UI and database-persisted logs.

### 🔄 Data Flow

1.  **Ingestion**: A user defines a project in Markdown. The `project` skill converts this to `project.json` in `.projects/`.
2.  **Claiming**: An `emm` worker starts, scans the `projects` table for unclaimed items, and creates a `session`.
3.  **Execution Loop**:
    - **Fetch**: Get next pending `task` for the session.
    - **Act**: Run AI tool (Opencode) on the task.
    - **Record**: Save `iteration` output (`stdout`/`stderr`) to DB.
    - **Verify**: If `COMPLETION_TAG` is found, mark task complete.
4.  **Termination**: Loop ends when all tasks are done or `max_iterations` is reached.

### 🗄️ Database & Migrations

**Status: PRE-LAUNCH / ALPHA**

> [!IMPORTANT]
> **Migration Policy**: Since the project has not yet launched, **schema stability is NOT guaranteed**. You are permitted (and encouraged) to modify `emm/migrations/001_initial_schema.sql` directly for schema changes rather than creating new migration files (`002_...`).

- **Location**: `emm/migrations/`
- **Mechanism**: `EmmDatabase.run_migrations()` applies new `.sql` files transactionally on startup.
- **Concurrency**: SQLite WAL mode ensures readers aren't blocked by writers. Feature claiming uses explicit locking to prevent race conditions between parallel agents.

### 🧪 Testing & Verification

- **Unit Tests**: `python3 -m unittest discover tests`
- **Linting**: `ruff check .` and `ruff format --check .`
- **Key Tests**:
    - `test_us2_sessions.py`: Verifies atomic claiming logic.
    - `test_emm_database.py`: Verifies schema integrity and CRUD.

### 📂 Directory Structure

```text
emm/
├── config.py       # Constants (Paths, DB settings)
├── core.py         # Main agent logic
├── database.py     # SQLite wrapper & migration runner
├── migrations/     # SQL schema files
└── runners.py      # Tool execution wrapper

.projects/          # JSON project definitions (source of truth for work)
.opencode/skill/    # Agent skills (project creation, etc.)
```

### 🧠 Agent Guidelines for this Repo

1.  **Strict Typing**: Use Python types (`List`, `Dict`, `Optional`) everywhere.
2.  **Atomic Migrations**: When changing schema, check if we are still pre-launch. If so, edit `001`. If post-launch, add `002`.
3.  **No "Features"**: We successfully renamed everything from "Feature" to "Project". **Do not reintroduce "Feature" terminology.**

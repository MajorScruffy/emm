# Feature: SQLite Integration for Emm Script

## Overview
Convert the emm script from file-based tracking to a comprehensive SQLite database management system. This will provide better auditing, session management, progress tracking, and learning capabilities.

## Current System Analysis

### Files That Remain External
- Original `.md` Feature files (initial input)
- Individual project code files

## Database Schema Design

### Core Tables

#### features
Feature file management
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `content` (TEXT NOT NULL) - Full Feature markdown content
- `hash` (TEXT NOT NULL) - SHA256 hash for change detection
- `name` (TEXT) - Feature name
- `created_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

#### sessions
Main sessions/runs table
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `feature_id` (INTEGER NOT NULL) - Foreign key to features
- `max_iterations` (INTEGER NOT NULL) - Maximum iterations allowed
- `tool` (TEXT DEFAULT 'opencode') - AI tool used
- `status` (TEXT DEFAULT 'running') - running, completed, failed, interrupted
- `created_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- `completed_at` (TIMESTAMP NULL)
- `total_iterations` (INTEGER DEFAULT 0)
- `total_tasks` (INTEGER DEFAULT 0)
- `completed_tasks` (INTEGER DEFAULT 0)

#### tasks
Tasks extracted from Feature (replaces hardcoded JSON array)
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `session_id` (INTEGER NOT NULL) - Foreign key to sessions
- `branch_name` (TEXT) - Git branch being worked on
- `task_id` (TEXT NOT NULL) - 001, 002, etc.
- `title` (TEXT NOT NULL) - Task title
- `description` (TEXT NOT NULL) - "As a [user], I want [feature] so that [benefit]"
- `acceptance_criteria` (TEXT NOT NULL) - JSON array of criteria
- `status` (TEXT DEFAULT 'pending') - pending, in_progress, completed, failed
- `started_at` (TIMESTAMP NULL)
- `completed_at` (TIMESTAMP NULL)
- `FOREIGN KEY (session_id) REFERENCES sessions(id)`

#### iterations
Iteration tracking table
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `session_id` (INTEGER NOT NULL) - Foreign key to sessions
- `iteration_number` (INTEGER NOT NULL) - Sequential iteration count
- `task_id_worked_on` (TEXT) - Which task was attempted this iteration
- `status` (TEXT DEFAULT 'running') - running, completed, failed, interrupted
- `started_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- `completed_at` (TIMESTAMP NULL)
- `opencode_output` (TEXT) - Full opencode response
- `opencode_stderr` (TEXT) - Error output if any
- `FOREIGN KEY (session_id) REFERENCES sessions(id)`

#### learnings
Learnings and insights extraction
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `session_id` (INTEGER NOT NULL)
- `iteration_number` (INTEGER NULL)
- `task_id` (TEXT NULL)
- `learning_text` (TEXT NOT NULL) - Learning content
- `learning_type` (TEXT DEFAULT 'general') - general, error, success, insight, technical
- `created_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- `FOREIGN KEY (session_id) REFERENCES sessions(id)`

#### console_logs
Complete audit trail of all console activity
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `session_id` (INTEGER NOT NULL)
- `iteration_number` (INTEGER NULL)
- `log_level` (TEXT DEFAULT 'info') - info, warning, error, debug, success
- `component` (TEXT) - database, opencode, parser, ui, etc.
- `message` (TEXT NOT NULL) - Log message content
- `created_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- `FOREIGN KEY (session_id) REFERENCES sessions(id)`

## Implementation Plan

### Phase 1: Core Database & Basic Operations

#### Database Manager (`emm_database.py`)
```python
class EmmDatabase:
    def __init__(self, db_path: str)
    def initialize_database(self) -> None
    def backup_database(self, backup_path: str) -> None
    
    # Feature Management
    def open_feature(self, feature_path: str) -> int:
        """Opens a Feature file, saves it to the database, and returns the feature_id."""
        pass

    # Session Management
    def create_session(self, feature_id: int, max_iterations: int, tool: str) -> int
    def get_session(self, session_id: int) -> dict
    def get_active_session(self) -> Optional[dict]
    def update_session_status(self, session_id: int, status: str) -> None
    def complete_session(self, session_id: int, final_status: str) -> None
    
    # Task Management
    def extract_and_store_tasks(self, session_id: int, feature_content: str) -> None
    def get_next_task(self, session_id: int) -> Optional[dict]
    def get_tasks_by_session(self, session_id: int) -> List[dict]
    def store_task(self, session_id: int, task: dict) -> None
    def update_task_status(self, session_id: int, task_id: str, status: str) -> None
    def mark_task_completed(self, session_id: int, task_id: str) -> None
    
    # Iteration Management
    def start_iteration(self, session_id: int, iteration: int) -> int
    def complete_iteration(self, iteration_id: int, task_id: str, output: str, stderr: str) -> None
    def get_iteration_history(self, session_id: int) -> List[dict]
    
    # Progress and Learning
    def store_learning(self, session_id: int, iteration: int, task_id: str, learning: str, learning_type: str) -> None
    def log_console_message(self, session_id: int, iteration: int, level: str, component: str, message: str) -> None
    
    # Analytics and Reporting
    def get_session_stats(self, session_id: int) -> dict
    def get_progress_burndown(self, session_id: int) -> List[dict]
    def get_learning_summary(self, session_id: int) -> List[dict]
    def export_session_data(self, session_id: int, format: str = 'json') -> str
```

#### Database Schema
- Create schema directly in `emm_database.py` (no separate migration files for v1)
- Add indexes for common queries:
  - `CREATE INDEX idx_tasks_session_status ON tasks(session_id, status)`
  - `CREATE INDEX idx_tasks_branch ON tasks(branch_name)`
  - `CREATE INDEX idx_iterations_session ON iterations(session_id, iteration_number)`
  - `CREATE INDEX idx_learnings_session ON learnings(session_id)`

### Phase 2: Feature Parser & Session Management

#### Feature Parser (`feature_parser.py`)
```python
class FeatureParser:
    def __init__(self, database: EmmDatabase)
    def parse_feature_file(self, feature_file: Path) -> dict
    def extract_tasks(self, feature_content: str) -> List[dict]
    def parse_acceptance_criteria(self, criteria_text: str) -> List[str]
    def determine_task_dependencies(self, tasks: List[dict]) -> None
    def validate_task_size(self, task: dict) -> bool
    def generate_task_hash(self, task: dict) -> str
```

#### Task Extraction Logic
- Parse tasks from Feature following the skill format
- Extract acceptance criteria with checkboxes
- Calculate dependencies (database first, then backend, then UI)
- Validate task size for single iteration completion
- Generate consistent task IDs (001, 002, etc.)

#### Session Manager (`session_manager.py`)
```python
class SessionManager:
    def __init__(self, database: EmmDatabase, script_dir: Path)
    def create_new_session(self, feature_file: Path, max_iterations: int) -> int
    def resume_session(self, session_id: int) -> bool
    def handle_branch_change(self, current_branch: str) -> Optional[int]
    def get_active_session(self) -> Optional[dict]
    def list_recent_sessions(self, limit: int = 10) -> List[dict]
```

#### Branch Change Detection
- Monitor branch changes using git
- Handle session transitions when branch changes
- Create new session for new branch
- Maintain branch-to-task mapping (via tasks.branch_name)

### Phase 3: Enhanced Emm Agent

#### Updated `EmmAgent` Class
```python
class EmmAgent:
    def __init__(self, feature_file: Path, max_iterations: int, tool: str)
    def run(self) -> int
    def run_iteration(self, iteration: int) -> bool
    def extract_learnings(self, output: str) -> List[str]
    def analyze_errors(self, stderr: str) -> List[str]
    def check_task_completion(self, task_id: str, output: str) -> dict
    def generate_progress_report(self, session_id: int) -> str
```

#### Database Integration Points
- Replace all file I/O with database calls
- Log all activities to console_logs table
- Track task progress in detail
- Extract and store learnings automatically
- Generate real-time progress reports

### Future Enhancements (Post-MVP)

#### Progress Visualization
- Real-time dashboard
- Progress bars for task completion
- Burndown charts for iterations
- Timeline of activities

#### Advanced Analytics
- Learning insights dashboard
- Error pattern analysis
- Session comparison tools
- Performance metrics

## File Structure

### Phase 1 (MVP)
```
scripts/
├── emm.py                    # Main script
├── emm_database.py           # All database operations
└── data/
    └── emm.db                # SQLite database file
```

### Phase 2+ (Future)
```
scripts/
├── emm.py
├── emm_database.py
├── feature_parser.py         # Feature parsing and task extraction
├── session_manager.py        # Session lifecycle management
├── progress_tracker.py       # Progress visualization (future)
└── data/
    └── emm.db
```

## Key Implementation Details

### Database Initialization
```python
def initialize_database(self):
    """Create database with all required tables and indexes"""
    with open(self.schema_path) as f:
        schema_sql = f.read()
    
    # Execute schema creation
    conn = sqlite3.connect(self.db_path)
    conn.executescript(schema_sql)
    
    # Create indexes for performance
    self._create_performance_indexes()
    
    # Insert initial data if needed
    self._seed_default_data()
```

### Feature Integration
```python
def create_session_from_feature(self, feature_file: Path, max_iterations: int):
    """Create new session from Feature file"""
    # Open Feature (saves to database)
    feature_id = self.db.open_feature(str(feature_file))
    
    # Create session
    session_id = self.db.create_session(
        feature_id=feature_id,
        max_iterations=max_iterations,
        tool='opencode'
    ) 
    
    # Extract and store tasks
    feature_content = feature_file.read_text()
    tasks = self.feature_parser.extract_tasks(feature_content)
    for task in tasks:
        self.db.store_task(session_id, task)
    
    return session_id
```

### Learning Extraction
```python
def extract_learnings_from_output(self, output: str) -> List[dict]:
    """Extract learnings from opencode output using patterns"""
    learnings = []
    
    # Technical patterns
    tech_patterns = [
        r"I learned that (.+)",
        r"The key insight is (.+)",
        r"Important discovery: (.+)",
        r"Best practice: (.+)"
    ]
    
    # Error patterns  
    error_patterns = [
        r"The error was caused by (.+)",
        r"This failed because (.+)",
        r"The issue is (.+)"
    ]
    
    # Extract and categorize learnings
    for pattern in tech_patterns:
        matches = re.findall(pattern, output, re.IGNORECASE)
        for match in matches:
            learnings.append({
                'type': 'technical',
                'text': match.strip(),
                'confidence': 'high'
            })
    
    return learnings
```

## Migration Strategy

### Phase 1: Backward Compatibility
1. Keep existing file-based system working
2. Add database as optional enhancement
3. Allow gradual migration of data
4. Provide data import tools

### Phase 2: Full Transition
1. Make database primary storage
2. Remove file dependencies
3. Update all documentation
4. Provide migration utilities

### Phase 3: Enhanced Features
1. Add advanced analytics
2. Implement learning recommendations
3. Create comprehensive reporting
4. Add integration APIs

## Success Criteria

### Functional Requirements
- [ ] All file-based operations converted to database
- [ ] Complete audit trail of all activities
- [ ] Feature task extraction and progress tracking
- [ ] Session management with resumption capability
- [ ] Automatic learning extraction and storage
- [ ] Branch change detection

### Performance Requirements
- [ ] Database operations complete within acceptable time limits
- [ ] Support for sessions with 100+ tasks
- [ ] Efficient storage of text data

## Next Steps

1. **Database Schema Finalization**: Review schema with actual Feature examples
2. **Core Database Implementation**: Build `EmmDatabase` class
3. **Feature Parser Development**: Create enhanced Feature parsing logic
4. **Session Management**: Implement session lifecycle management
5. **Integration**: Update main `EmmAgent` to use database
6. **Testing**: Comprehensive testing with real Feature files
7. **Enhanced Features**: Add visualization and analytics

This plan maintains compatibility with the existing Feature skill structure while providing comprehensive database tracking for better auditability, learning capture, and progress management.
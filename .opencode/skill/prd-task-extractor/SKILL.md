---
name: emm
description: "Convert Features to feature.json format for the emm autonomous agent system. Use when you have an existing Feature and need to convert it to emm's JSON format. Triggers on: convert this feature, turn this into emm format, create feature.json from this, emm json."
---

# emm Feature Converter

Converts existing Features to the feature.json format that emm uses for autonomous execution.

---

## The Job

Take a Feature (markdown file or text) and convert it to `feature.json` in your emm directory.

---

## Output Format

```json
{
  "project": "[Project Name]",
  "branchName": "emm/[feature-name-kebab-case]",
  "description": "[Feature description from Feature title/intro]",
  "tasks": [
    {
      "id": "US-001",
      "title": "[Task title]",
      "description": "As a [user], I want [feature] so that [benefit]",
      "acceptanceCriteria": [
        "Criterion 1",
        "Criterion 2",
        "Typecheck passes"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    }
  ]
}
```

---

## Task Size: The Number One Rule

**Each task must be completable in ONE emm iteration (one context window).**

emm spawns a fresh Amp instance per iteration with no memory of previous work. If a task is too big, the LLM runs out of context before finishing and produces broken code.

### Right-sized tasks:
- Add a database column and migration
- Add a UI component to an existing page
- Update a server action with new logic
- Add a filter dropdown to a list

### Too big (split these):
- "Build the entire dashboard" - Split into: schema, queries, UI components, filters
- "Add authentication" - Split into: schema, middleware, login UI, session handling
- "Refactor the API" - Split into one story per endpoint or pattern

**Rule of thumb:** If you cannot describe the change in 2-3 sentences, it is too big.

---

## Task Ordering: Dependencies First

Tasks execute in priority order. Earlier tasks must not depend on later ones.

**Correct order:**
1. Schema/database changes (migrations)
2. Server actions / backend logic
3. UI components that use the backend
4. Dashboard/summary views that aggregate data

**Wrong order:**
1. UI component (depends on schema that does not exist yet)
2. Schema change

---

## Acceptance Criteria: Must Be Verifiable

Each criterion must be something emm can CHECK, not something vague.

### Good criteria (verifiable):
- "Add `status` column to tasks table with default 'pending'"
- "Filter dropdown has options: All, Active, Completed"
- "Clicking delete shows confirmation dialog"
- "Typecheck passes"
- "Tests pass"

### Bad criteria (vague):
- "Works correctly"
- "User can do X easily"
- "Good UX"
- "Handles edge cases"

### Always include as final criterion:
```
"Typecheck passes"
```

For stories with testable logic, also include:
```
"Tests pass"
```

### For stories that change UI, also include:
```
"Verify in browser using dev-browser skill"
```

Frontend tasks are NOT complete until visually verified. emm will use the dev-browser skill to navigate to the page, interact with the UI, and confirm changes work.

---

## Conversion Rules

1. **Each task becomes one JSON entry**
2. **IDs**: Sequential (US-001, US-002, etc.)
3. **Priority**: Based on dependency order, then document order
4. **All tasks**: `passes: false` and empty `notes`
5. **branchName**: Derive from feature name, kebab-case, prefixed with `emm/`
6. **Always add**: "Typecheck passes" to every task's acceptance criteria

---

## Splitting Large Features

If a Feature has big features, split them:

**Original:**
> "Add user notification system"

**Split into:**
1. US-001: Add notifications table to database
2. US-002: Create notification service for sending notifications
3. US-003: Add notification bell icon to header
4. US-004: Create notification dropdown panel
5. US-005: Add mark-as-read functionality
6. US-006: Add notification preferences page

Each is one focused change that can be completed and verified independently.

---

## Example

**Input PRD:**
```markdown
# Task Status Feature

Add ability to mark tasks with different statuses.

## Requirements
- Toggle between pending/in-progress/done on task list
- Filter list by status
- Show status badge on each task
- Persist status in database
```

**Output feature.json:**
```json
{
  "project": "TaskApp",
  "branchName": "emm/task-status",
  "description": "Task Status Feature - Track task progress with status indicators",
  "tasks": [
    {
      "id": "US-001",
      "title": "Add status field to tasks table",
      "description": "As a developer, I need to store task status in the database.",
      "acceptanceCriteria": [
        "Add status column: 'pending' | 'in_progress' | 'done' (default 'pending')",
        "Generate and run migration successfully",
        "Typecheck passes"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    },
    {
      "id": "US-002",
      "title": "Display status badge on task cards",
      "description": "As a user, I want to see task status at a glance.",
      "acceptanceCriteria": [
        "Each task card shows colored status badge",
        "Badge colors: gray=pending, blue=in_progress, green=done",
        "Typecheck passes",
        "Verify in browser using dev-browser skill"
      ],
      "priority": 2,
      "passes": false,
      "notes": ""
    },
    {
      "id": "US-003",
      "title": "Add status toggle to task list rows",
      "description": "As a user, I want to change task status directly from the list.",
      "acceptanceCriteria": [
        "Each row has status dropdown or toggle",
        "Changing status saves immediately",
        "UI updates without page refresh",
        "Typecheck passes",
        "Verify in browser using dev-browser skill"
      ],
      "priority": 3,
      "passes": false,
      "notes": ""
    },
    {
      "id": "US-004",
      "title": "Filter tasks by status",
      "description": "As a user, I want to filter the list to see only certain statuses.",
      "acceptanceCriteria": [
        "Filter dropdown: All | Pending | In Progress | Done",
        "Filter persists in URL params",
        "Typecheck passes",
        "Verify in browser using dev-browser skill"
      ],
      "priority": 4,
      "passes": false,
      "notes": ""
    }
  ]
}
```

---

## Archiving Previous Runs

**Before writing a new feature.json, check if there is an existing one from a different feature:**

1. Read the current `feature.json` if it exists
2. Check if `branchName` differs from the new feature's branch name
3. If different AND `progress.txt` has content beyond the header:
   - Create archive folder: `archive/YYYY-MM-DD-feature-name/`
   - Copy current `feature.json` and `progress.txt` to archive
   - Reset `progress.txt` with fresh header

**The emm.sh script handles this automatically** when you run it, but if you are manually updating feature.json between runs, archive first.

---

## Checklist Before Saving

Before writing feature.json, verify:

- [ ] **Previous run archived** (if feature.json exists with different branchName, archive it first)
- [ ] Each task is completable in one iteration (small enough)
- [ ] Tasks are ordered by dependency (schema to backend to UI)
- [ ] Every task has "Typecheck passes" as criterion
- [ ] UI tasks have "Verify in browser using dev-browser skill" as criterion
- [ ] Acceptance criteria are verifiable (not vague)
- [ ] No task depends on a later task
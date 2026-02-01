---
name: project
description: "Generate a Project Requirements Document for a new project. Use when planning a project, starting a new initiative, or when asked to create a Project. Triggers on: create a project, write project for, plan this project, requirements for, spec out."
---

# Project Generator

Create detailed Project Requirements Documents that are clear, actionable, and suitable for implementation.

---

## The Job

1. Receive a project description from the user
2. Ask 3-5 essential clarifying questions (with lettered options)
3. Generate a structured Project based on answers
4. Save to `.projects/[project-name].md`

**Important:** Do NOT start implementing. Just create the Project PRD.

---

## Step 1: Clarifying Questions

Ask only critical questions where the initial prompt is ambiguous. Focus on:

- **Problem/Goal:** What problem does this solve?
- **Core Functionality:** What are the key actions?
- **Scope/Boundaries:** What should it NOT do?
- **Success Criteria:** How do we know it's done?

### Format Questions Like This:

```
1. What is the primary goal of this project?
   A. Improve user onboarding experience
   B. Increase user retention
   C. Reduce support burden
   D. Other: [please specify]

2. Who is the target user?
   A. New users only
   B. Existing users only
   C. All users
   D. Admin users only

3. What is the scope?
   A. Minimal viable version
   B. Full-featured implementation
   C. Just the backend/API
   D. Just the UI
```

This lets users respond with "1A, 2C, 3B" for quick iteration.

---

## Step 2: Project Structure

Generate the Project with these sections:

### 1. Introduction/Overview
Brief description of the project and the problem it solves.

### 2. Goals
Specific, measurable objectives (bullet list).

### 3. Tasks
Each task needs:
- **Title:** Short descriptive name
- **Description:** "As a [user], I want [functionality] so that [benefit]"
- **Acceptance Criteria:** Verifiable checklist of what "done" means

Each task should be small enough to implement in one focused session.

**Format:**
```markdown
### US-001: [Title]
**Description:** As a [user], I want [functionality] so that [benefit].

**Acceptance Criteria:**
- [ ] Specific verifiable criterion
- [ ] Another criterion
- [ ] Typecheck/lint passes
- [ ] **[UI stories only]** Verify in browser using dev-browser skill
```

**Important:** 
- Acceptance criteria must be verifiable, not vague. "Works correctly" is bad. "Button shows confirmation dialog before deleting" is good.
- **For any task with UI changes:** Always include "Verify in browser using dev-browser skill" as acceptance criteria. This ensures visual verification of frontend work.

### 4. Functional Requirements
Numbered list of specific functionalities:
- "FR-1: The system must allow users to..."
- "FR-2: When a user clicks X, the system must..."

Be explicit and unambiguous.

### 5. Non-Goals (Out of Scope)
What this project will NOT include. Critical for managing scope.

### 6. Design Considerations (Optional)
- UI/UX requirements
- Link to mockups if available
- Relevant existing components to reuse

### 7. Technical Considerations (Optional)
- Known constraints or dependencies
- Integration points with existing systems
- Performance requirements

### 8. Success Metrics
How will success be measured?
- "Reduce time to complete X by 50%"
- "Increase conversion rate by 10%"

### 9. Open Questions
Remaining questions or areas needing clarification.

---

## Writing for Junior Developers

The PRD reader may be a junior developer or AI agent. Therefore:

- Be explicit and unambiguous
- Avoid jargon or explain it
- Provide enough detail to understand purpose and core logic
- Number requirements for easy reference
- Use concrete examples where helpful

---

## Output

- **Format:** JSON (`.json`)
- **Location:** `.projects/`
- **Filename:** `[project-name].json` (kebab-case, e.g., `task-priority-system.json`)

---

## Example PRD

## Example Output

```json
{
  "project": "TaskPriority",
  "branchName": "emm/task-priority",
  "description": "Task Priority System - Add priority levels to tasks so users can focus on what matters most.",
  "tasks": [
    {
      "id": "001",
      "title": "Add priority field to database",
      "description": "As a developer, I need to store task priority so it persists across sessions.",
      "acceptanceCriteria": [
        "Add priority column to tasks table: 'high' | 'medium' | 'low' (default 'medium')",
        "Generate and run migration successfully",
        "Typecheck passes"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    },
    {
      "id": "002",
      "title": "Display priority indicator on task cards",
      "description": "As a user, I want to see task priority at a glance so I know what needs attention first.",
      "acceptanceCriteria": [
        "Each task card shows colored priority badge (red=high, yellow=medium, gray=low)",
        "Priority visible without hovering or clicking",
        "Typecheck passes",
        "Verify in browser using dev-browser skill"
      ],
      "priority": 2,
      "passes": false,
      "notes": ""
    },
    {
      "id": "003",
      "title": "Add priority selector to task edit",
      "description": "As a user, I want to change a task's priority when editing it.",
      "acceptanceCriteria": [
        "Priority dropdown in task edit modal",
        "Shows current priority as selected",
        "Saves immediately on selection change",
        "Typecheck passes",
        "Verify in browser using dev-browser skill"
      ],
      "priority": 3,
      "passes": false,
      "notes": ""
    },
    {
      "id": "004",
      "title": "Filter tasks by priority",
      "description": "As a user, I want to filter the task list to see only high-priority items when I'm focused.",
      "acceptanceCriteria": [
        "Filter dropdown with options: All | High | Medium | Low",
        "Filter persists in URL params",
        "Empty state message when no tasks match filter",
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

## Checklist

Before saving the PRD:

- [ ] Asked clarifying questions with lettered options
- [ ] Incorporated user's answers
- [ ] User stories are small and specific
- [ ] Functional requirements are numbered and unambiguous
- [ ] Non-goals section defines clear boundaries
- [ ] Saved to `.projects/[project-name].md`
# Workflow Execution Plan: Project Setup

**Workflow Name:** project-setup  
**Repository:** intel-agency/workflow-orchestration-queue-bravo74  
**Triggered By:** Issue #1 (orchestration:dispatch)  
**Created:** 2026-03-26

---

## 1. Overview

This document outlines the execution plan for the `project-setup` dynamic workflow, which initializes the repository for the **OS-APOW (workflow-orchestration-queue)** project.

**Project Description:** An autonomous AI orchestration platform that transforms GitHub Issues into execution orders fulfilled by specialized AI agents. The system implements a 4-pillar architecture: Ear (Notifier), State (GitHub Issues), Brain (Sentinel), Hands (Worker).

**Total Assignments:** 6 main assignments + pre/post events  
**High-Level Summary:** Initialize repository, create application plan, establish project structure, configure AGENTS.md, document learnings, and merge setup PR.

---

## 2. Project Context Summary

**Key Facts:**
- **Project Name:** OS-APOW (workflow-orchestration-queue)
- **Purpose:** Headless agentic orchestration platform for autonomous software development
- **Tech Stack:** Python 3.12, FastAPI, uv, Pydantic, httpx, Docker, DevContainers
- **Architecture:** 4-Pillar (Ear/Notifier, State/Queue, Brain/Sentinel, Hands/Worker)

**Technology Stack:**
- Language: Python 3.12+
- Web Framework: FastAPI with Uvicorn
- Package Manager: uv (Rust-based, fast)
- Data Validation: Pydantic
- HTTP Client: httpx (async)
- Containerization: Docker, Docker Compose, DevContainers
- Agent Runtime: opencode CLI with ZhipuAI GLM models

**Key Constraints:**
- Self-bootstrapping system (builds itself)
- Security-first (HMAC webhook verification, credential scrubbing)
- Polling-first resiliency model
- GitHub Issues as state persistence ("Markdown as a Database")

**Repository Details:**
- Owner: intel-agency
- Repo: workflow-orchestration-queue-bravo74
- Default Branch: main
- Template Source: intel-agency/workflow-orchestration-queue-bravo74

**Known Risks:**
- Race conditions in task claiming (mitigated by assign-then-verify pattern)
- LLM looping/hallucination (mitigated by cost guardrails)
- GitHub API rate limiting (mitigated by exponential backoff)
- Container drift (mitigated by environment reset between tasks)

---

## 3. Assignment Execution Plan

### Assignment 1: init-existing-repository

| Field | Content |
|---|---|
| **Goal** | Initialize repository settings, create GitHub Project, import labels, rename files |
| **Key Acceptance Criteria** | Branch created, branch protection ruleset imported, GitHub Project created, labels imported, workspace files renamed, PR created |
| **Project-Specific Notes** | Template repo already has structure; focus on configuration and naming |
| **Prerequisites** | GitHub authentication with repo, project, and admin scopes |
| **Dependencies** | None (first assignment) |
| **Risks / Challenges** | Branch protection may require admin permissions; Project creation may need org permissions |
| **Events** | post-assignment: validate-assignment-completion, report-progress |

### Assignment 2: create-app-plan

| Field | Content |
|---|---|
| **Goal** | Create application plan issue based on plan_docs/ analysis |
| **Key Acceptance Criteria** | Plan issue created, milestones created, issue linked to project, labels applied |
| **Project-Specific Notes** | Rich planning docs already exist in plan_docs/; synthesize into GitHub issue |
| **Prerequisites** | init-existing-repository complete |
| **Dependencies** | Repository initialized, project created |
| **Risks / Challenges** | Plan docs are comprehensive; need to extract key implementation phases |
| **Events** | pre-assignment: gather-context; post-assignment: validate-assignment-completion, report-progress |

### Assignment 3: create-project-structure

| Field | Content |
|---|---|
| **Goal** | Create solution/project structure, Docker, CI/CD foundation |
| **Key Acceptance Criteria** | Solution structure created, Dockerfile created, docker-compose.yml created, CI/CD workflows created, documentation structure created, README.md created |
| **Project-Specific Notes** | Python project with uv; follow pyproject.toml structure from spec |
| **Prerequisites** | Application plan approved |
| **Dependencies** | create-app-plan complete |
| **Risks / Challenges** | Must pin all GitHub Actions to commit SHAs; Docker healthcheck must not use curl |
| **Events** | post-assignment: validate-assignment-completion, report-progress |

### Assignment 4: create-agents-md-file

| Field | Content |
|---|---|
| **Goal** | Create AGENTS.md file for AI coding agent context |
| **Key Acceptance Criteria** | AGENTS.md exists at root, contains project overview, setup commands, code style, testing instructions |
| **Project-Specific Notes** | Complement existing README.md; focus on agent-consumable instructions |
| **Prerequisites** | Project structure created |
| **Dependencies** | create-project-structure complete |
| **Risks / Challenges** | Commands must be validated before documenting |
| **Events** | post-assignment: validate-assignment-completion, report-progress |

### Assignment 5: debrief-and-document

| Field | Content |
|---|---|
| **Goal** | Create debriefing report capturing learnings and deviations |
| **Key Acceptance Criteria** | Report created following template, all deviations documented, committed to repo |
| **Project-Specific Notes** | Document any issues encountered during setup |
| **Prerequisites** | All previous assignments complete |
| **Dependencies** | All main assignments complete |
| **Risks / Challenges** | Must capture all action items as GitHub issues |
| **Events** | post-assignment: validate-assignment-completion, report-progress |

### Assignment 6: pr-approval-and-merge

| Field | Content |
|---|---|
| **Goal** | Complete PR approval and merge process |
| **Key Acceptance Criteria** | CI checks pass, review comments resolved, PR merged, branch deleted |
| **Project-Specific Notes** | Self-approval acceptable for setup PR; extract $pr_num from init-existing-repository output |
| **Prerequisites** | All assignments complete, PR created |
| **Dependencies** | $pr_num from init-existing-repository |
| **Risks / Challenges** | CI may fail; up to 3 fix cycles allowed |
| **Events** | post-assignment: validate-assignment-completion, report-progress |

---

## 4. Sequencing Diagram

```
[pre-script-begin]
    │
    ▼
[create-workflow-plan] ──────────────────────────────────────┐
    │                                                         │
    ▼                                                         │
[init-existing-repository] ──► [validate] ──► [report]       │
    │                                                         │
    ▼                                                         │
[create-app-plan] ───────────► [validate] ──► [report]       │
    │                                                         │
    ▼                                                         │
[create-project-structure] ──► [validate] ──► [report]       │
    │                                                         │
    ▼                                                         │
[create-agents-md-file] ─────► [validate] ──► [report]       │
    │                                                         │
    ▼                                                         │
[debrief-and-document] ──────► [validate] ──► [report]       │
    │                                                         │
    ▼                                                         │
[pr-approval-and-merge] ─────► [validate] ──► [report]       │
    │                                                         │
    ▼                                                         │
[post-script-complete]                                        │
    │                                                         │
    ▼                                                         │
[Apply orchestration:plan-approved label] ◄──────────────────┘
```

---

## 5. Open Questions

1. **Branch Protection:** Does the GitHub token have `administration: write` scope to create branch protection rulesets?
2. **Project Creation:** Does the token have `project` scope to create GitHub Projects?
3. **Sentinel Bot Login:** What is the `SENTINEL_BOT_LOGIN` for the assign-then-verify pattern?

---

## 6. Stakeholder Approval

- [ ] Plan reviewed and approved by: _______________
- [ ] Date: _______________

---

**Resolution Trace:**
- Dynamic Workflow: `ai_instruction_modules/ai-workflow-assignments/dynamic-workflows/project-setup.md`
- Remote URL: `https://raw.githubusercontent.com/nam20485/agent-instructions/main/ai_instruction_modules/ai-workflow-assignments/dynamic-workflows/project-setup.md`

**Assignments:**
1. `create-workflow-plan.md` → `https://raw.githubusercontent.com/nam20485/agent-instructions/main/ai_instruction_modules/ai-workflow-assignments/create-workflow-plan.md`
2. `init-existing-repository.md` → `https://raw.githubusercontent.com/nam20485/agent-instructions/main/ai_instruction_modules/ai-workflow-assignments/init-existing-repository.md`
3. `create-app-plan.md` → `https://raw.githubusercontent.com/nam20485/agent-instructions/main/ai_instruction_modules/ai-workflow-assignments/create-app-plan.md`
4. `create-project-structure.md` → `https://raw.githubusercontent.com/nam20485/agent-instructions/main/ai_instruction_modules/ai-workflow-assignments/create-project-structure.md`
5. `create-agents-md-file.md` → `https://raw.githubusercontent.com/nam20485/agent-instructions/main/ai_instruction_modules/ai-workflow-assignments/create-agents-md-file.md`
6. `debrief-and-document.md` → `https://raw.githubusercontent.com/nam20485/agent-instructions/main/ai_instruction_modules/ai-workflow-assignments/debrief-and-document.md`
7. `pr-approval-and-merge.md` → `https://raw.githubusercontent.com/nam20485/agent-instructions/main/ai_instruction_modules/ai-workflow-assignments/pr-approval-and-merge.md`
8. `validate-assignment-completion.md` → `https://raw.githubusercontent.com/nam20485/agent-instructions/main/ai_instruction_modules/ai-workflow-assignments/validate-assignment-completion.md`
9. `report-progress.md` → `https://raw.githubusercontent.com/nam20485/agent-instructions/main/ai_instruction_modules/ai-workflow-assignments/report-progress.md`

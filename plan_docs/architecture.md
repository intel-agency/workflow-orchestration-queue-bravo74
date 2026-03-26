# Architecture

**Project:** OS-APOW (workflow-orchestration-queue)  
**Last Updated:** 2026-03-26

## Executive Summary

OS-APOW represents a paradigm shift from **Interactive AI Coding** to **Headless Agentic Orchestration**. Traditional AI developer tools require a human-in-the-loop to navigate files, provide context, and trigger executions. OS-APOW replaces this manual overhead with a persistent, event-driven infrastructure that transforms GitHub Issues into "Execution Orders" autonomously fulfilled by specialized AI agents.

## System Architecture

The system implements a **4-Pillar Architecture** with strict separation of concerns:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         OS-APOW System Architecture                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐          │
│    │   THE EAR    │────▶│   STATE      │────▶│   BRAIN      │          │
│    │  (Notifier)  │     │  (Queue)     │     │  (Sentinel)  │          │
│    │              │     │              │     │              │          │
│    │  FastAPI     │     │  GitHub      │     │  Python      │          │
│    │  Webhook     │     │  Issues      │     │  Async       │          │
│    │  Receiver    │     │  Labels      │     │  Poller      │          │
│    └──────────────┘     └──────────────┘     └──────┬───────┘          │
│                                                      │                   │
│                                                      ▼                   │
│                                              ┌──────────────┐           │
│                                              │   HANDS      │           │
│                                              │  (Worker)    │           │
│                                              │              │           │
│                                              │  opencode    │           │
│                                              │  DevContainer│           │
│                                              │  LLM Agent   │           │
│                                              └──────────────┘           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Overview

### 1. The Ear (Work Event Notifier)

**Technology Stack:** Python 3.12, FastAPI, UV, Pydantic

**Role:** The system's primary gateway for external stimuli and asynchronous triggers.

**Responsibilities:**
- **Secure Webhook Ingestion:** Exposes a hardened endpoint to receive issues, issue_comment, and pull_request events from the GitHub App.
- **Cryptographic Verification:** Every incoming request is validated using HMAC SHA256 against the WEBHOOK_SECRET.
- **Intelligent Event Triage & Manifest Generation:** Parses issue body and labels using Pydantic models to map payloads into unified WorkItem objects.
- **Queue Initialization:** Applies the `agent:queued` label to signal the Sentinel to begin processing.

**File:** `src/notifier_service.py`

### 2. The State (Work Queue)

**Implementation:** Distributed state management via GitHub Issues, Labels, and Milestones.

**Philosophy:** "Markdown as a Database" - leveraging GitHub as the persistence layer provides world-class audit logs, transparent versioning, and an out-of-the-box UI for human supervision.

**State Machine (Label Logic):**
- `agent:queued`: Task awaiting Sentinel pickup
- `agent:in-progress`: Sentinel has claimed the issue
- `agent:reconciling`: Reconciliation state for stale tasks
- `agent:success`: Workflow reached terminal success
- `agent:error`: Technical failure occurred
- `agent:infra-failure`: Infrastructure failure (timeout, OOM)
- `agent:stalled-budget`: Stalled due to budget limits

**Concurrency Control:** Uses GitHub "Assignees" as a semaphore with **assign-then-verify** pattern.

### 3. The Brain (Sentinel Orchestrator)

**Technology Stack:** Python (Async Background Service), PowerShell Core, Docker CLI

**Role:** The persistent supervisor that manages the lifecycle of Worker environments and maps high-level intent to low-level shell commands.

**Lifecycle:**
1. **Polling Discovery:** Scans repository for `agent:queued` issues every 60 seconds
2. **Auth Synchronization:** Ensures valid GitHub tokens via scripts
3. **Shell-Bridge Protocol:** Manages Worker via devcontainer-opencode.sh
4. **Workflow Mapping:** Translates issue type into specific prompt string
5. **Telemetry:** Captures stdout and posts heartbeat comments
6. **Environment Reset:** Stops worker container between tasks
7. **Graceful Shutdown:** Handles SIGTERM/SIGINT signals

**File:** `src/orchestrator_sentinel.py`

### 4. The Hands (Opencode Worker)

**Technology Stack:** opencode-server CLI, LLM Core (GLM-5)

**Environment:** High-fidelity DevContainer built from template repository.

**Capabilities:**
- **Contextual Awareness:** Accesses project structure and vector-indexed codebase
- **Instructional Logic:** Reads and executes .md workflow modules
- **Verification:** Runs local test suites before submitting PRs

## Key Architectural Decisions (ADRs)

### ADR 07: Standardized Shell-Bridge Execution

**Decision:** The Orchestrator interacts with the agentic environment *exclusively* via the devcontainer-opencode.sh script.

**Rationale:** Reusing shell scripts ensures perfect environment parity between AI and human developers, preventing "Configuration Drift."

### ADR 08: Polling-First Resiliency Model

**Decision:** The Sentinel uses polling as primary discovery; webhooks are treated as optimization.

**Rationale:** Polling ensures that upon restart, the Sentinel performs "State Reconciliation" by looking at GitHub labels, making the system inherently self-healing.

### ADR 09: Provider-Agnostic Interface Layer

**Decision:** All queue interactions are abstracted behind ITaskQueue interface using Strategy Pattern.

**Rationale:** Ensures Phase 1 code is reusable for Linear, Notion, or internal SQL queues without rewriting orchestrator logic.

## Data Flow (Happy Path)

1. User opens GitHub Issue using application-plan.md template
2. GitHub Webhook hits the Notifier (FastAPI)
3. Notifier verifies signature, confirms title pattern, adds `agent:queued` label
4. Sentinel poller detects new label, assigns issue, updates to `agent:in-progress`
5. Sentinel syncs repo, executes devcontainer-opencode.sh up
6. Sentinel dispatches prompt to Worker
7. Worker reads issue, generates code, runs tests
8. Worker posts "Execution Complete" comment
9. Sentinel detects exit, removes `in-progress`, adds `agent:success`

## Security Architecture

### Network Isolation

Worker containers run in a dedicated Docker network. They can reach the internet to fetch packages but cannot access the host network or local subnet.

### Credential Scoping

GitHub App Installation Token is passed via temporary environment variable that is destroyed when the session ends.

### Credential Scrubbing

All log output is piped through `scrub_secrets()` utility that strips:
- GitHub PATs (`ghp_*`, `ghs_*`, `gho_*`, `github_pat_*`)
- Bearer tokens
- API keys (`sk-*`)
- ZhipuAI keys

### Resource Constraints

Worker containers are hard-capped at 2 CPUs and 4GB RAM.

## Self-Bootstrapping Lifecycle

1. **Bootstrap:** Developer manually clones template repository
2. **Seed:** Developer adds plan docs and runs create-repo-from-plan-docs
3. **Init:** Developer runs devcontainer-opencode.sh up
4. **Orchestrate:** Developer runs project-setup workflow
5. **Autonomous Phase:** Sentinel service started; AI manages all further development

## Project Structure

```
workflow-orchestration-queue/
├── pyproject.toml               # Core definition file for uv
├── uv.lock                      # Deterministic lockfile
├── src/
│   ├── notifier_service.py      # FastAPI Webhook receiver
│   ├── orchestrator_sentinel.py # Background polling/dispatch
│   ├── models/
│   │   ├── work_item.py         # Unified WorkItem, scrub_secrets()
│   │   └── github_events.py     # GitHub webhook payload schemas
│   └── queue/
│       └── github_queue.py      # ITaskQueue + GitHubQueue
├── scripts/
│   ├── devcontainer-opencode.sh # Core orchestrator shell bridge
│   ├── gh-auth.ps1              # GitHub auth utility
│   └── update-remote-indices.ps1# Vector index sync
├── local_ai_instruction_modules/# Markdown logic workflows
└── docs/                        # Architecture and user documentation
```

# OS-APOW: Autonomous AI Orchestration Platform

[![CI](https://github.com/intel-agency/workflow-orchestration-queue-bravo74/actions/workflows/validate.yml/badge.svg)](https://github.com/intel-agency/workflow-orchestration-queue-bravo74/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

**OS-APOW** (workflow-orchestration-queue) is a groundbreaking headless agentic orchestration platform that transforms GitHub Issues into execution orders fulfilled by specialized AI agents without human intervention.

### Key Features

- **Zero-Touch Construction**: Open a specification issue and receive a functional, test-passed PR
- **4-Pillar Architecture**: Ear (Notifier), State (Queue), Brain (Sentinel), Hands (Worker)
- **Self-Bootstrapping**: The system builds itself using its own orchestration capabilities
- **Polling-First Resiliency**: Self-healing on restart via GitHub label reconciliation
- **Markdown as Database**: Full transparency via GitHub Issues as state persistence

## Quick Start

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- GitHub App with repo, project, and workflow scopes
- ZhipuAI API key (or other supported LLM provider)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/intel-agency/workflow-orchestration-queue-bravo74.git
   cd workflow-orchestration-queue-bravo74
   ```

2. Install dependencies using uv:
   ```bash
   uv pip install -e .
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. Start the services:
   ```bash
   docker-compose up -d
   ```

### Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_REPO` | Target repository (owner/repo) | Yes |
| `GITHUB_TOKEN` | GitHub API token | Yes |
| `WEBHOOK_SECRET` | HMAC secret for webhook verification | Yes |
| `SENTINEL_BOT_LOGIN` | GitHub login for task locking | No |
| `ZHIPU_API_KEY` | ZhipuAI API key for LLM | Yes |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OS-APOW Architecture                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│    ┌──────────────┐     ┌──────────────┐     ┌────────────┐│
│    │   THE EAR    │────▶│   STATE      │────▶│   BRAIN    ││
│    │  (Notifier)  │     │  (Queue)     │     │  (Sentinel)││
│    │              │     │              │     │            ││
│    │  FastAPI     │     │  GitHub      │     │  Python    ││
│    │  Webhook     │     │  Issues      │     │  Async     ││
│    └──────────────┘     └──────────────┘     └─────┬──────┘│
│                                                     │        │
│                                                     ▼        │
│                                             ┌──────────────┐│
│                                             │   HANDS      ││
│                                             │  (Worker)    ││
│                                             │              ││
│                                             │  opencode    ││
│                                             │  DevContainer││
│                                             └──────────────┘│
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

See [plan_docs/architecture.md](./plan_docs/architecture.md) for detailed architecture documentation.

## Usage

### Creating a Task

1. Open a GitHub Issue with a title starting with `[Plan]`
2. The Notifier automatically applies the `agent:queued` label
3. The Sentinel picks up the task and begins processing
4. Watch progress via heartbeat comments on the issue

### Task States

| Label | Meaning |
|-------|---------|
| `agent:queued` | Awaiting Sentinel pickup |
| `agent:in-progress` | Sentinel actively processing |
| `agent:success` | Task completed successfully |
| `agent:error` | Execution error occurred |
| `agent:infra-failure` | Infrastructure failure |

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

### Code Quality

```bash
# Lint
uv run ruff check src/

# Format
uv run ruff format src/

# Type check
uv run mypy src/
```

### API Documentation

When running the Notifier service, access the Swagger UI at:
```
http://localhost:8000/docs
```

## Documentation

- [Architecture Guide](./plan_docs/OS-APOW%20Architecture%20Guide%20v3.2.md)
- [Development Plan](./plan_docs/OS-APOW%20Development%20Plan%20v4.2.md)
- [Implementation Specification](./plan_docs/OS-APOW%20Implementation%20Specification%20v1.2.md)
- [Tech Stack](./plan_docs/tech-stack.md)
- [Architecture](./plan_docs/architecture.md)
- [Workflow Plan](./plan_docs/workflow-plan.md)

## Security

- All webhook payloads are verified using HMAC SHA256
- Credentials are scrubbed before posting to public logs
- Worker containers run in isolated Docker networks
- Resource constraints prevent runaway agents

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

---

**Built with ❤️ by the intel-agency team**

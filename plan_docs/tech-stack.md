# Tech Stack

**Project:** OS-APOW (workflow-orchestration-queue)  
**Last Updated:** 2026-03-26

## Primary Language

- **Python 3.12+**: Taking advantage of the latest asynchronous features, improved error messages, and significant performance enhancements in the core interpreter.

## Web Framework

- **FastAPI**: High-performance async web framework for the Webhook Notifier. Chosen for its native Pydantic integration, automatic OpenAPI generation, and unparalleled speed.
- **Uvicorn**: Lightning-fast ASGI web server implementation used to serve the FastAPI application in production.

## Data Validation & Settings

- **Pydantic**: Utilized extensively for strict data validation, settings management, and defining the complex data schemas needed for cross-component communication (e.g., WorkItem, TaskType).

## HTTP Client

- **httpx**: Selected over the standard requests library to serve as a fully asynchronous HTTP client. This allows the Sentinel to execute REST API calls to GitHub without blocking the main event loop, significantly improving throughput.

## Package Management

- **uv**: Employed as the Python package installer and dependency resolver. Written in Rust, it provides speeds orders of magnitude faster than pip or poetry, vastly accelerating DevContainer build times.

## Containerization

- **Docker**: The absolute core underlying worker execution engine, providing the necessary sandboxing, environment consistency, and lifecycle hooks for the LLM agents.
- **Docker Compose**: Used to manage complex, multi-container needs (e.g., web app + PostgreSQL).
- **DevContainers**: High-fidelity development environment that is bit-for-bit identical to what a human developer would use.

## Agent Runtime

- **opencode CLI**: AI agent runtime that executes markdown-based instruction modules against the cloned codebase.
- **ZhipuAI GLM models**: Primary LLM provider via `ZHIPU_API_KEY`.
- **MCP servers**: 
  - `@modelcontextprotocol/server-sequential-thinking`: Structured thinking tool
  - `@modelcontextprotocol/server-memory`: Knowledge graph memory

## Shell Scripts

- **PowerShell Core (pwsh)**: Used for authentication synchronization and cross-platform CLI interactions.
- **Bash**: Used for DevContainer lifecycle management and shell bridge execution.

## Version Control

- **Git**: Distributed version control system.
- **GitHub**: Repository hosting, issue tracking, and CI/CD via GitHub Actions.

## CI/CD

- **GitHub Actions**: Automated workflows for linting, scanning, testing, and deployment.
- **DevContainer Prebuild**: Pre-built container images for fast startup.

## Security

- **HMAC SHA256**: Cryptographic verification for webhook payloads.
- **Credential Scrubbing**: Regex-based sanitization of logs before posting to GitHub.
- **Network Isolation**: Worker containers run in a dedicated Docker network.

## Monitoring & Observability

- **Structured Logging**: JSON-structured logs for machine readability.
- **Heartbeat Comments**: Periodic status updates posted to GitHub issues.
- **Status Dashboard**: Lightweight FastAPI endpoint for system status.

## Dependencies

### Python Packages (pyproject.toml)

```toml
[project]
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn>=0.27.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.1.0",
    "httpx>=0.26.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.2.0",
    "mypy>=1.8.0",
]
```

### Node.js Packages (for MCP servers)

```json
{
  "dependencies": {
    "@modelcontextprotocol/server-memory": "*",
    "@modelcontextprotocol/server-sequential-thinking": "*"
  }
}
```

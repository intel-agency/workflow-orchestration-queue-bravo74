"""
Data models for the workflow-orchestration-queue system.

This module defines the unified data structures used across all components:
- WorkItem: Represents a task to be processed
- TaskType: Enumeration of task types
- WorkItemStatus: Enumeration of task states
- scrub_secrets(): Utility for credential sanitization
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Enumeration of task types that the orchestrator can handle."""

    PLAN = "plan"
    IMPLEMENT = "implement"
    BUGFIX = "bugfix"
    REVIEW = "review"


class WorkItemStatus(str, Enum):
    """Enumeration of work item states mapped to GitHub labels."""

    QUEUED = "agent:queued"
    IN_PROGRESS = "agent:in-progress"
    RECONCILING = "agent:reconciling"
    SUCCESS = "agent:success"
    ERROR = "agent:error"
    INFRA_FAILURE = "agent:infra-failure"
    STALLED_BUDGET = "agent:stalled-budget"


class WorkItem(BaseModel):
    """
    Unified work item representation used across all components.

    This model serves as the contract between the Notifier (Ear),
    the Queue (State), and the Sentinel (Brain).
    """

    id: str = Field(..., description="Unique identifier for the work item")
    issue_number: int = Field(..., description="GitHub issue number")
    source_url: str = Field(..., description="URL of the source issue")
    context_body: str = Field(..., description="Body content of the issue")
    target_repo_slug: str = Field(..., description="Target repository (owner/repo)")
    task_type: TaskType = Field(..., description="Type of task to execute")
    status: WorkItemStatus = Field(
        default=WorkItemStatus.QUEUED, description="Current status of the work item"
    )
    node_id: str | None = Field(None, description="GitHub node ID for GraphQL operations")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional provider-specific metadata"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "issue-123",
                    "issue_number": 123,
                    "source_url": "https://github.com/owner/repo/issues/123",
                    "context_body": "Implement user authentication",
                    "target_repo_slug": "owner/repo",
                    "task_type": "implement",
                    "status": "agent:queued",
                    "node_id": "I_abc123",
                    "metadata": {"labels": ["enhancement", "priority:high"]},
                }
            ]
        }
    }


# Regex patterns for credential scrubbing
SECRET_PATTERNS = [
    # GitHub PATs
    (r"ghp_[a-zA-Z0-9]{36}", "[REDACTED_GHP]"),
    (r"ghs_[a-zA-Z0-9]{36}", "[REDACTED_GHS]"),
    (r"gho_[a-zA-Z0-9]{36}", "[REDACTED_GHO]"),
    (r"github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}", "[REDACTED_GITHUB_PAT]"),
    # Bearer tokens
    (r"Bearer\s+[a-zA-Z0-9\-._~+/]+=*", "[REDACTED_BEARER]"),
    # Generic API keys
    (r"sk-[a-zA-Z0-9]{20,}", "[REDACTED_SK]"),
    # ZhipuAI keys
    (r"[a-f0-9]{32}\.[a-zA-Z0-9]{32}", "[REDACTED_ZHIPU]"),
]


def scrub_secrets(text: str) -> str:
    """
    Remove sensitive credentials from text before posting to public logs.

    This function strips patterns matching:
    - GitHub PATs (ghp_*, ghs_*, gho_*, github_pat_*)
    - Bearer tokens
    - API keys (sk-*)
    - ZhipuAI keys

    Args:
        text: The text to sanitize.

    Returns:
        The sanitized text with credentials replaced by placeholders.

    Example:
        >>> scrub_secrets("Token: ghp_1234567890abcdefghijklmnopqrstuvwx")
        'Token: [REDACTED_GHP]'
    """
    sanitized = text
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized

"""
GitHub webhook event schemas for parsing incoming payloads.

This module defines Pydantic models for validating and parsing
GitHub webhook events received by the Notifier service.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GitHubEventType(str, Enum):
    """Enumeration of supported GitHub webhook event types."""

    ISSUES = "issues"
    ISSUE_COMMENT = "issue_comment"
    PULL_REQUEST = "pull_request"
    PULL_REQUEST_REVIEW = "pull_request_review"
    PULL_REQUEST_REVIEW_COMMENT = "pull_request_review_comment"


class GitHubIssue(BaseModel):
    """GitHub issue payload."""

    number: int = Field(..., description="Issue number")
    title: str = Field(..., description="Issue title")
    body: str | None = Field(None, description="Issue body content")
    state: str = Field(..., description="Issue state (open/closed)")
    node_id: str = Field(..., description="GitHub node ID")
    html_url: str = Field(..., description="HTML URL of the issue")
    labels: list[dict[str, Any]] = Field(default_factory=list, description="Issue labels")


class GitHubRepository(BaseModel):
    """GitHub repository payload."""

    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full repository name (owner/repo)")
    owner: dict[str, Any] = Field(..., description="Repository owner info")


class GitHubSender(BaseModel):
    """GitHub sender (actor) payload."""

    login: str = Field(..., description="User login")
    id: int = Field(..., description="User ID")


class GitHubIssuesEvent(BaseModel):
    """GitHub issues webhook event payload."""

    action: str = Field(..., description="Event action (opened, edited, closed, etc.)")
    issue: GitHubIssue = Field(..., description="Issue data")
    repository: GitHubRepository = Field(..., description="Repository data")
    sender: GitHubSender = Field(..., description="Sender data")


class GitHubIssueCommentEvent(BaseModel):
    """GitHub issue_comment webhook event payload."""

    action: str = Field(..., description="Event action (created, edited, deleted)")
    issue: GitHubIssue = Field(..., description="Issue data")
    comment: dict[str, Any] = Field(..., description="Comment data")
    repository: GitHubRepository = Field(..., description="Repository data")
    sender: GitHubSender = Field(..., description="Sender data")


class GitHubPullRequestEvent(BaseModel):
    """GitHub pull_request webhook event payload."""

    action: str = Field(..., description="Event action (opened, synchronize, closed, etc.)")
    pull_request: dict[str, Any] = Field(..., description="Pull request data")
    repository: GitHubRepository = Field(..., description="Repository data")
    sender: GitHubSender = Field(..., description="Sender data")

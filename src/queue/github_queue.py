"""
GitHub Issues implementation of the ITaskQueue interface.

This module provides the GitHubQueue class that implements
task queue operations using GitHub Issues as the backing store.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING

import httpx

from src.queue.interfaces import ITaskQueue

if TYPE_CHECKING:
    from src.models.work_item import WorkItem, WorkItemStatus

logger = logging.getLogger(__name__)


class GitHubQueue(ITaskQueue):
    """
    GitHub Issues implementation of the task queue.

    This class uses GitHub Issues with labels as the task queue,
    implementing the "Markdown as a Database" pattern.
    """

    def __init__(
        self,
        owner: str,
        repo: str,
        token: str,
        sentinel_bot_login: str | None = None,
        poll_interval: int = 60,
        max_backoff: int = 960,
    ):
        """
        Initialize the GitHub queue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            token: GitHub API token with repo scope.
            sentinel_bot_login: GitHub login of the sentinel bot for locking.
            poll_interval: Base polling interval in seconds.
            max_backoff: Maximum backoff interval in seconds.
        """
        self.owner = owner
        self.repo = repo
        self.token = token
        self.sentinel_bot_login = sentinel_bot_login
        self.poll_interval = poll_interval
        self.max_backoff = max_backoff
        self.current_backoff = poll_interval

        # Create a single AsyncClient for connection pooling
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with connection pooling."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url="https://api.github.com",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _repo_path(self) -> str:
        """Get the repository API path."""
        return f"/repos/{self.owner}/{self.repo}"

    async def fetch_queued_items(self) -> list[WorkItem]:
        """
        Fetch all issues with the agent:queued label.

        Returns:
            List of WorkItem objects with status QUEUED.
        """
        from src.models.work_item import TaskType, WorkItem, WorkItemStatus

        try:
            response = await self.client.get(
                f"{self._repo_path()}/issues",
                params={
                    "labels": "agent:queued",
                    "state": "open",
                },
            )
            response.raise_for_status()

            issues = response.json()
            items = []
            for issue in issues:
                # Determine task type from labels
                task_type = TaskType.IMPLEMENT
                if any(label["name"] == "epic" for label in issue.get("labels", [])):
                    task_type = TaskType.PLAN

                item = WorkItem(
                    id=f"issue-{issue['number']}",
                    issue_number=issue["number"],
                    source_url=issue["html_url"],
                    context_body=issue.get("body") or "",
                    target_repo_slug=f"{self.owner}/{self.repo}",
                    task_type=task_type,
                    status=WorkItemStatus.QUEUED,
                    node_id=issue.get("node_id"),
                    metadata={"labels": [l["name"] for l in issue.get("labels", [])]},
                )
                items.append(item)

            # Reset backoff on success
            self.current_backoff = self.poll_interval
            return items

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (403, 429):
                # Apply jittered exponential backoff
                jitter = asyncio.get_event_loop().time() % 0.1 * self.current_backoff
                self.current_backoff = min(self.current_backoff * 2 + jitter, self.max_backoff)
                logger.warning(f"Rate limited, backing off for {self.current_backoff}s")
            raise

    async def claim_task(self, item_id: str, sentinel_id: str) -> bool:
        """
        Claim a task using the assign-then-verify pattern.

        Args:
            item_id: The issue ID (format: issue-NUMBER).
            sentinel_id: The sentinel instance ID.

        Returns:
            True if the claim was successful.
        """
        if not self.sentinel_bot_login:
            logger.warning("SENTINEL_BOT_LOGIN not set, locking disabled")
            return True

        issue_number = int(item_id.split("-")[1])

        # Step 1: Attempt to assign
        try:
            response = await self.client.post(
                f"{self._repo_path()}/issues/{issue_number}/assignees",
                json={"assignees": [self.sentinel_bot_login]},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to assign issue: {e}")
            return False

        # Step 2: Re-fetch the issue
        try:
            response = await self.client.get(f"{self._repo_path()}/issues/{issue_number}")
            response.raise_for_status()
            issue = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to re-fetch issue: {e}")
            return False

        # Step 3: Verify assignment
        assignees = [a["login"] for a in issue.get("assignees", [])]
        if self.sentinel_bot_login not in assignees:
            logger.warning(f"Assignment verification failed, assignees: {assignees}")
            return False

        return True

    async def update_status(self, item_id: str, status: str, comment: str | None = None) -> bool:
        """
        Update issue status by managing labels.

        Args:
            item_id: The issue ID.
            status: The new status label.
            comment: Optional comment to post.

        Returns:
            True if successful.
        """
        issue_number = int(item_id.split("-")[1])

        # Remove old status labels and add new one
        status_labels = [
            "agent:queued",
            "agent:in-progress",
            "agent:success",
            "agent:error",
            "agent:infra-failure",
            "agent:stalled-budget",
        ]

        try:
            # Get current labels
            response = await self.client.get(f"{self._repo_path()}/issues/{issue_number}")
            response.raise_for_status()
            issue = response.json()

            current_labels = [l["name"] for l in issue.get("labels", [])]

            # Remove old status labels (except the new one)
            for label in status_labels:
                if label in current_labels and label != status:
                    await self.client.delete(
                        f"{self._repo_path()}/issues/{issue_number}/labels/{label}"
                    )

            # Add new status label
            await self.client.post(
                f"{self._repo_path()}/issues/{issue_number}/labels",
                json={"labels": [status]},
            )

            # Post comment if provided
            if comment:
                await self.post_comment(item_id, comment)

            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update status: {e}")
            return False

    async def post_comment(self, item_id: str, body: str) -> bool:
        """
        Post a comment to an issue.

        Args:
            item_id: The issue ID.
            body: The comment body.

        Returns:
            True if successful.
        """
        from src.models.work_item import scrub_secrets

        issue_number = int(item_id.split("-")[1])

        # Scrub secrets before posting
        sanitized_body = scrub_secrets(body)

        try:
            response = await self.client.post(
                f"{self._repo_path()}/issues/{issue_number}/comments",
                json={"body": sanitized_body},
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to post comment: {e}")
            return False

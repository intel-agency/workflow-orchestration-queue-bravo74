"""
Abstract interface for task queue providers.

This module defines the ITaskQueue ABC that abstracts queue operations,
allowing the orchestrator logic to be decoupled from the specific provider
(GitHub, Linear, Notion, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.work_item import WorkItem


class ITaskQueue(ABC):
    """
    Abstract interface for task queue operations.

    This interface provides a provider-agnostic way to interact with
    task queues. Implementations should handle provider-specific
    API interactions (GitHub Issues, Linear tasks, etc.).
    """

    @abstractmethod
    async def fetch_queued_items(self) -> list[WorkItem]:
        """
        Fetch all items currently in the queued state.

        Returns:
            List of WorkItem objects with status QUEUED.
        """
        ...

    @abstractmethod
    async def claim_task(self, item_id: str, sentinel_id: str) -> bool:
        """
        Attempt to claim a task for processing.

        This method should implement the assign-then-verify pattern
        to prevent race conditions in distributed environments:
        1. Attempt to assign the sentinel to the issue
        2. Re-fetch the issue
        3. Verify the sentinel is the current assignee

        Args:
            item_id: The ID of the work item to claim.
            sentinel_id: The ID of the sentinel attempting to claim.

        Returns:
            True if the claim was successful, False otherwise.
        """
        ...

    @abstractmethod
    async def update_status(self, item_id: str, status: str, comment: str | None = None) -> bool:
        """
        Update the status of a work item.

        Args:
            item_id: The ID of the work item to update.
            status: The new status label to apply.
            comment: Optional comment to post with the status update.

        Returns:
            True if the update was successful, False otherwise.
        """
        ...

    @abstractmethod
    async def post_comment(self, item_id: str, body: str) -> bool:
        """
        Post a comment to a work item.

        Args:
            item_id: The ID of the work item to comment on.
            body: The comment body text.

        Returns:
            True if the comment was posted successfully.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """
        Close the queue connection and release resources.

        This method should be called during graceful shutdown
        to properly release HTTP connections and other resources.
        """
        ...

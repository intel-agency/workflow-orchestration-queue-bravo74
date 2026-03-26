"""
Sentinel Orchestrator - The Brain of the OS-APOW system.

This module implements the persistent background service that:
- Polls GitHub Issues for tasks with agent:queued label
- Claims tasks using assign-then-verify pattern
- Dispatches work to the opencode worker via shell bridge
- Updates task status and posts heartbeat comments
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime
from typing import TYPE_CHECKING

from src.queue.github_queue import GitHubQueue

if TYPE_CHECKING:
    from src.models.work_item import WorkItem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Configuration from environment
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
SENTINEL_ID = os.getenv("SENTINEL_ID", f"sentinel-{os.getpid()}")
SENTINEL_BOT_LOGIN = os.getenv("SENTINEL_BOT_LOGIN")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
HEARTBEAT_INTERVAL = int(os.getenv("SENTINEL_HEARTBEAT_INTERVAL", "300"))
SUBPROCESS_TIMEOUT = int(os.getenv("SUBPROCESS_TIMEOUT", "5700"))

# Shutdown flag for graceful termination
_shutdown_requested = False


def signal_handler(signum: int, frame: object) -> None:
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    _shutdown_requested = True


async def heartbeat_loop(queue: GitHubQueue, item: WorkItem, start_time: datetime) -> None:
    """
    Post heartbeat comments at regular intervals.

    This coroutine runs concurrently with process_task() to provide
    visibility during long-running operations.

    Args:
        queue: The GitHub queue instance.
        item: The work item being processed.
        start_time: When processing started.
    """
    while not _shutdown_requested:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        elapsed = (datetime.now() - start_time).total_seconds()
        comment = f"**Heartbeat**: Sentinel {SENTINEL_ID} still working... ({elapsed:.0f}s elapsed)"
        await queue.post_comment(item.id, comment)


async def process_task(queue: GitHubQueue, item: WorkItem) -> bool:
    """
    Process a single work item.

    This function:
    1. Claims the task using assign-then-verify
    2. Updates status to in-progress
    3. Executes the shell bridge commands
    4. Updates final status based on result

    Args:
        queue: The GitHub queue instance.
        item: The work item to process.

    Returns:
        True if processing succeeded, False otherwise.
    """
    from src.models.work_item import WorkItemStatus

    # Claim the task
    if not await queue.claim_task(item.id, SENTINEL_ID):
        logger.warning(f"Failed to claim task {item.id}, skipping")
        return False

    # Update status to in-progress
    await queue.update_status(
        item.id,
        WorkItemStatus.IN_PROGRESS.value,
        f"Sentinel {SENTINEL_ID} is starting work on this task.",
    )

    start_time = datetime.now()

    # Start heartbeat coroutine
    heartbeat_task = asyncio.create_task(heartbeat_loop(queue, item, start_time))

    try:
        # Execute shell bridge commands
        # 1. Ensure environment is up
        proc = await asyncio.create_subprocess_exec(
            "./scripts/devcontainer-opencode.sh",
            "up",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        if proc.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            await queue.update_status(
                item.id,
                WorkItemStatus.INFRA_FAILURE.value,
                f"Infrastructure failure during 'up':\n```\n{error_msg}\n```",
            )
            return False

        # 2. Start opencode server
        proc = await asyncio.create_subprocess_exec(
            "./scripts/devcontainer-opencode.sh",
            "start",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

        if proc.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            await queue.update_status(
                item.id,
                WorkItemStatus.INFRA_FAILURE.value,
                f"Infrastructure failure during 'start':\n```\n{error_msg}\n```",
            )
            return False

        # 3. Execute prompt
        prompt = f"Process issue #{item.issue_number}: {item.context_body[:500]}"
        proc = await asyncio.create_subprocess_exec(
            "./scripts/devcontainer-opencode.sh",
            "prompt",
            prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=SUBPROCESS_TIMEOUT)

        if proc.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            await queue.update_status(
                item.id,
                WorkItemStatus.ERROR.value,
                f"Execution error:\n```\n{error_msg[-1000:]}\n```",
            )
            return False

        # Success
        await queue.update_status(
            item.id,
            WorkItemStatus.SUCCESS.value,
            f"Task completed successfully by Sentinel {SENTINEL_ID}.",
        )
        return True

    except asyncio.TimeoutError:
        await queue.update_status(
            item.id,
            WorkItemStatus.INFRA_FAILURE.value,
            f"Task timed out after {SUBPROCESS_TIMEOUT}s",
        )
        return False

    except Exception as e:
        logger.exception(f"Error processing task {item.id}")
        await queue.update_status(
            item.id,
            WorkItemStatus.ERROR.value,
            f"Unexpected error: {str(e)}",
        )
        return False

    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass


async def run_forever(queue: GitHubQueue) -> None:
    """
    Main polling loop.

    Continuously polls for queued tasks and processes them.
    Implements jittered exponential backoff on rate limits.
    """
    global _shutdown_requested

    logger.info(f"Sentinel {SENTINEL_ID} starting polling loop")

    while not _shutdown_requested:
        try:
            # Fetch queued items
            items = await queue.fetch_queued_items()

            if items:
                logger.info(f"Found {len(items)} queued items")
                for item in items:
                    if _shutdown_requested:
                        break
                    await process_task(queue, item)
            else:
                logger.debug("No queued items found")

            # Sleep before next poll
            await asyncio.sleep(POLL_INTERVAL)

        except Exception as e:
            logger.error(f"Error in polling loop: {e}")
            await asyncio.sleep(queue.current_backoff)

    logger.info(f"Sentinel {SENTINEL_ID} shutting down")


async def main() -> None:
    """Main entry point for the Sentinel."""
    # Validate required environment variables
    if not GITHUB_REPO:
        logger.error("GITHUB_REPO environment variable is required")
        sys.exit(1)
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN environment variable is required")
        sys.exit(1)

    # Parse repository
    try:
        owner, repo = GITHUB_REPO.split("/")
    except ValueError:
        logger.error(f"Invalid GITHUB_REPO format: {GITHUB_REPO}, expected 'owner/repo'")
        sys.exit(1)

    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Create queue instance
    queue = GitHubQueue(
        owner=owner,
        repo=repo,
        token=GITHUB_TOKEN,
        sentinel_bot_login=SENTINEL_BOT_LOGIN,
        poll_interval=POLL_INTERVAL,
    )

    try:
        await run_forever(queue)
    finally:
        await queue.close()


if __name__ == "__main__":
    asyncio.run(main())

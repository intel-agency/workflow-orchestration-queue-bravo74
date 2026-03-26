"""
Notifier Service - The Ear of the OS-APOW system.

This module implements the FastAPI webhook receiver that:
- Receives GitHub webhook events
- Validates HMAC signatures
- Triage events and queue tasks
- Returns 202 Accepted within 10-second timeout
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import sys
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Configuration from environment
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")

# FastAPI app
app = FastAPI(
    title="OS-APOW Notifier",
    description="Webhook receiver for GitHub events",
    version="0.1.0",
)


class WebhookPayload(BaseModel):
    """Generic webhook payload for logging."""

    action: str | None = None
    event_type: str
    data: dict[str, Any]


def verify_signature(payload: bytes, signature: str) -> bool:
    """
    Verify the HMAC SHA256 signature of a webhook payload.

    Args:
        payload: The raw request body bytes.
        signature: The X-Hub-Signature-256 header value.

    Returns:
        True if the signature is valid.
    """
    if not WEBHOOK_SECRET:
        logger.warning("WEBHOOK_SECRET not set, signature verification disabled")
        return True

    if not signature.startswith("sha256="):
        return False

    expected = signature[7:]  # Remove 'sha256=' prefix
    computed = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, computed)


def triage_issue(body: str, title: str) -> str | None:
    """
    Determine the appropriate label based on issue content.

    Args:
        body: The issue body text.
        title: The issue title.

    Returns:
        The appropriate label or None.
    """
    title_lower = title.lower()
    body_lower = body.lower() if body else ""

    # Check for plan/template patterns
    if "[plan]" in title_lower or "application plan" in body_lower:
        return "agent:queued"

    # Check for bug patterns
    if "[bug]" in title_lower or "bug report" in body_lower:
        return "agent:queued"

    # Check for feature patterns
    if "[feature]" in title_lower or "feature request" in body_lower:
        return "agent:queued"

    return None


@app.post("/webhooks/github")
async def handle_github_webhook(request: Request) -> JSONResponse:
    """
    Handle incoming GitHub webhook events.

    This endpoint:
    1. Validates the HMAC signature
    2. Parses the event type
    3. Triages the event
    4. Queues tasks as needed

    Returns 202 Accepted to meet GitHub's 10-second timeout.
    """
    # Get raw body for signature verification
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    event_type = request.headers.get("X-GitHub-Event", "")

    # Verify signature
    if not verify_signature(payload, signature):
        logger.warning("Invalid webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    # Parse JSON body
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON",
        )

    logger.info(f"Received {event_type} event")

    # Handle different event types
    if event_type == "issues":
        action = data.get("action")
        if action == "opened":
            issue = data.get("issue", {})
            title = issue.get("title", "")
            body = issue.get("body", "")
            number = issue.get("number")

            # Triage the issue
            label = triage_issue(body, title)
            if label:
                # TODO: Add label via GitHub API
                logger.info(f"Issue #{number} triaged with label: {label}")

    elif event_type == "issue_comment":
        # Handle comment events
        action = data.get("action")
        if action == "created":
            comment = data.get("comment", {})
            body = comment.get("body", "")
            logger.info(f"Comment created: {body[:100]}...")

    elif event_type == "pull_request_review":
        # Handle PR review events
        action = data.get("action")
        review = data.get("review", {})
        state = review.get("state")
        if state == "changes_requested":
            # TODO: Re-queue the associated issue
            logger.info("PR changes requested, should re-queue issue")

    # Return 202 Accepted immediately
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"status": "accepted", "event_type": event_type},
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "notifier"}


@app.on_event("startup")
async def startup() -> None:
    """Validate configuration on startup."""
    if not WEBHOOK_SECRET:
        logger.warning("WEBHOOK_SECRET not set - signature verification disabled")
    if not GITHUB_TOKEN:
        logger.warning("GITHUB_TOKEN not set - API operations will fail")
    if not GITHUB_REPO:
        logger.warning("GITHUB_REPO not set - queue operations will fail")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

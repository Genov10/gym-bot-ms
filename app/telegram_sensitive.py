"""Telegram flags for sensitive content (QR, payment notices, etc.)."""

from __future__ import annotations

from typing import Any

# No forwarding/saving; on supported clients reduces screenshot sharing.
PROTECT_CONTENT_KWARGS: dict[str, Any] = {"protect_content": True}

# Photo is blurred until the user taps to reveal.
SPOILER_PHOTO_KWARGS: dict[str, Any] = {**PROTECT_CONTENT_KWARGS, "has_spoiler": True}

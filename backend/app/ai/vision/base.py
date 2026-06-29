"""AIVisionProvider adapter interface.

The rest of the system depends only on this abstraction; concrete provider
implementations (OpenAI, Gemini, ...) live in sibling modules and are the ONLY
place a vision provider SDK may be imported (CLAUDE.md, docs/02 §3, docs/07).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class DetectedItem:
    """A single food item detected in a meal image (unsaved, pre-confirmation)."""

    name: str
    quantity_g: float
    confidence: float | None = None
    name_he: str | None = None


@dataclass
class VisionResult:
    items: list[DetectedItem] = field(default_factory=list)


class AIVisionProvider(ABC):
    """Recognizes foods + portions from a meal image."""

    @abstractmethod
    async def recognize(self, image_url: str) -> VisionResult:
        """Return detected food items for the given image URL."""
        raise NotImplementedError

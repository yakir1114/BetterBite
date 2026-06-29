"""AITextProvider adapter interface.

Concrete LLM implementations (coach, recipes, chat) live behind this interface
and are the ONLY place a text provider SDK may be imported (CLAUDE.md,
docs/02 §3).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AITextProvider(ABC):
    """Generates text (coach insights, recipes, chat replies)."""

    @abstractmethod
    async def complete(self, prompt: str, *, system: str | None = None) -> str:
        """Return a text completion for the given prompt."""
        raise NotImplementedError

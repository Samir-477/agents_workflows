"""RFC 9309-compliant robots.txt evaluation.

Python's standard-library `urllib.robotparser` ends a group at the first blank line.
RFC 9309 §2.2 says only a new `user-agent` line starts a new group, and Google follows
the RFC. Real sites do put blank lines and comments between `User-agent:` and its rules,
and against those files the standard-library parser silently discards every `Disallow`
— which made this crawler fetch paths the site had asked it not to, and made the AI
Visibility agent report AI crawlers as "allowed" when they were not.

`Protego` implements the RFC, so it is the single source of truth for both questions we
ask of a robots file: may we fetch this URL, and what has the site declared about a
given crawler.
"""

from __future__ import annotations

from protego import Protego


class RobotsPolicy:
    """A parsed robots.txt, or an absent one that permits everything."""

    __slots__ = ("_parser", "declared")

    def __init__(self, parser: Protego | None) -> None:
        self._parser = parser
        self.declared = parser is not None

    @classmethod
    def parse(cls, text: str | None) -> "RobotsPolicy":
        if text is None:
            return cls(None)
        try:
            return cls(Protego.parse(text))
        except Exception:
            # An unparseable robots file is treated as absent, which is the same
            # permissive default crawlers use. The caller surfaces this as a warning.
            return cls(None)

    def can_fetch(self, url: str, user_agent: str) -> bool:
        if self._parser is None:
            return True
        try:
            return bool(self._parser.can_fetch(url, user_agent))
        except Exception:
            return True

    def sitemaps(self) -> list[str]:
        if self._parser is None:
            return []
        try:
            return list(dict.fromkeys(self._parser.sitemaps))
        except Exception:
            return []


def can_fetch(text: str | None, url: str, user_agent: str) -> bool:
    """Convenience wrapper for one-off checks."""
    return RobotsPolicy.parse(text).can_fetch(url, user_agent)

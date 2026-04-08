"""
bluesky_client/helpers/pagination.py

Single pagination envelope used by every list-returning helper.
The agent always sees the same shape regardless of which resource it's reading.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    items: List[T]
    cursor: Optional[str]
    page: int = 1
    _has_more_hint: Optional[bool] = field(default=None, repr=False)

    @property
    def has_more(self) -> bool:
        if self._has_more_hint is not None:
            return self._has_more_hint
        return self.cursor is not None

    @property
    def count(self) -> int:
        return len(self.items)

    def summary(self) -> dict:
        return {
            "cursor":   self.cursor,
            "has_more": self.has_more,
            "page":     self.page,
            "count":    self.count,
        }
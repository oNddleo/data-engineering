"""Mock of the BCA (Bộ Công An) national citizen database.

In production, this module is replaced with an HTTP client talking
to the BCA verification API (subject to bilateral integration
contract). The contract is narrow enough that we can fake it with
a plain dict: pass in CCCD, get back a :class:`BCARecord` if the
citizen exists in the registry, otherwise ``None``.

We deliberately surface only the fields a fintech is allowed to
read back through the BCA API — full name, gender, date of birth,
hometown province. The pipeline cross-checks each of these against
the OCR'd values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date

    from ekycpipe.schema import Gender


@dataclass(frozen=True, slots=True)
class BCARecord:
    """The fields the BCA API returns for a CCCD lookup."""

    cccd: str
    full_name: str
    date_of_birth: date
    gender: Gender
    hometown_province_code: str


class BCADatabase:
    """In-memory CCCD → :class:`BCARecord` lookup.

    Construct from a list of records; lookup is O(1) by CCCD.
    """

    def __init__(self, records: list[BCARecord]) -> None:
        self._by_cccd: dict[str, BCARecord] = {}
        for r in records:
            if r.cccd in self._by_cccd:
                raise ValueError(f"duplicate CCCD in BCA seed: {r.cccd}")
            self._by_cccd[r.cccd] = r

    @property
    def size(self) -> int:
        return len(self._by_cccd)

    def lookup(self, cccd: str) -> BCARecord | None:
        return self._by_cccd.get(cccd)

    def contains(self, cccd: str) -> bool:
        return cccd in self._by_cccd


__all__ = ["BCADatabase", "BCARecord"]

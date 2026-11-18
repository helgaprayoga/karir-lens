"""Registry adapter: satu tempat mendaftarkan sumber (R-02-01)."""

from __future__ import annotations

from .base import BaseAdapter
from .dealls import DeallsAdapter
from .kalibrr import KalibrrAdapter
from .remotive import RemotiveAdapter

ADAPTERS: dict[str, type[BaseAdapter]] = {
    DeallsAdapter.name: DeallsAdapter,
    KalibrrAdapter.name: KalibrrAdapter,
    RemotiveAdapter.name: RemotiveAdapter,
}


def get_adapter(name: str) -> type[BaseAdapter]:
    try:
        return ADAPTERS[name]
    except KeyError:
        raise ValueError(f"Sumber lowongan tidak dikenal: {name!r}.") from None

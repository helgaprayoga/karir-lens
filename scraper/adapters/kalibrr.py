"""Adapter Kalibrr (PRD-02)."""

from __future__ import annotations

from .base import BaseAdapter


class KalibrrAdapter(BaseAdapter):
    name = "kalibrr"
    base_url = "https://www.kalibrr.com"

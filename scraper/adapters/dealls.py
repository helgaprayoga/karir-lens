"""Adapter Dealls (PRD-02)."""

from __future__ import annotations

from .base import BaseAdapter


class DeallsAdapter(BaseAdapter):
    name = "dealls"
    base_url = "https://dealls.com"

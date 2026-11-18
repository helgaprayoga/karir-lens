"""Adapter Remotive (PRD-02)."""

from __future__ import annotations

from .base import BaseAdapter


class RemotiveAdapter(BaseAdapter):
    name = "remotive"
    base_url = "https://remotive.com"

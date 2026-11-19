"""Runner migrasi skema langsung ke Postgres Supabase.

Paket ini adalah entrypoint ketiga setelah ``app`` (web) dan ``scraper`` (batch):
``python -m db``. Bebas Flask, seperti ``scraper`` (docs/ARCHITECTURE.md §4 aturan 5).
"""

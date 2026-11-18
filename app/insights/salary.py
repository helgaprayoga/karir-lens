"""Statistik gaji faktual: median, P25, P75, jumlah sampel (PRD-05).

Aturan yang tinggal di sini:
- Hanya lowongan yang mencantumkan gaji.
- Statistik disembunyikan bila sampel < 5 (R-05-08).
- Mata uang tidak dicampur (R-05-09).
- Tidak ada field prediksi (R-05-10).
"""

from __future__ import annotations

MIN_SALARY_SAMPLE = 5

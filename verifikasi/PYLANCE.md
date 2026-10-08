# Perbaikan Pylance

Sebelum: empat error `reportCallIssue`/`reportArgumentType` di `sum(...)`, direproduksi dengan Pyright 1.1.414.
Akar masalah: return type fungsi rekursif `deep_size()` tidak dinyatakan. Diff source hanya `def deep_size(obj, seen=None) -> int:`; tidak memakai ignore/suppression.

Sesudah: Pyright menganalisis dua salinan `sparse.py`, 0 error/0 warning. Source hasil ekstraksi diperbaiki hanya setelah isinya terbukti identik dengan source awal, sehingga perubahan pengguna tidak tertimpa.

Verifikasi dijalankan:

- `uv run --with pyright pyright extensions/src/sparse.py Tugas_Ngram_Language_Model/Tugas_Ngram_Language_Model/extensions/src/sparse.py --pythonpath .venv/Scripts/python.exe --outputjson`: 0 error/0 warning.
- `uv run pytest -q`: 48 passed in 3.60s.
- `uv run ruff check core extensions jalankan_notebook.py`: All checks passed.
- `uv run ty check core/src extensions/src extensions/experiments jalankan_notebook.py`: All checks passed.
- `uv build --out-dir hasil_build/perbaikan_tipe`: wheel dan sdist berhasil.
- `git diff --check`: tidak ada whitespace error.

Anotasi tidak mengubah hasil riset; file hasil lama dicek dengan SHA-256 dan tetap identik. UI Pylance tidak dioperasikan langsung; bukti berasal dari CLI Pyright yang mereproduksi diagnostik yang sama.
ZIP sebelum perbaikan disimpan pada `hasil_build/arsip_pengumpulan`, di luar ZIP terbaru agar tidak memuat arsip duplikat.

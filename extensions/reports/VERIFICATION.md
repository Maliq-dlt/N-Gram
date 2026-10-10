# Verifikasi implementasi Academic Lab

Diperiksa pada Windows, 10 Oktober 2026. Ini bukti implementasi lokal dan pilot eksploratif; bukan sertifikasi produksi, akurasi CCTV atau generalisasi bahasa. [Hasil ilmiah dan rumus](ACADEMIC_LAB.md) · [Metrik publik](pilot_metrics.json) · [Sumber data](DATA_SOURCES.md).

## Hasil yang diverifikasi

| Pemeriksaan | Hasil |
| --- | --- |
| Root `pytest -q`, core dan extensions | 167 tes lulus, termasuk guard NLTK, regresi worker benchmark dan metode baru |
| Ruff lint/format dan Ty root | Lulus pada core, extensions, serta launcher notebook |
| UI `npm run typecheck`, `npm run check`, `npm run build` | Lulus; React/TS Lab terintegrasi dengan studio lama |
| API akademik | Login/CSRF, input terbatas, parity angka, seeded generation, checkpoint/cache integrity, metadata dev, CSV dan ringkasan publik lulus |
| Ledger dan query fakta | Isolasi workspace/peran, transaksi/rollback, bukti byte, timestamp, retraction/stale, ambiguity dan unsupported filters lulus |
| Novelty offline/API | Runner nyata atas fixture terkendali; laporan private, tanpa label tidak mengklaim kualitas, isolasi workspace/stale/corrupt artifact lulus |
| Video/chat nyata | 71 pemeriksaan lulus di server fixture terpisah; inference CPU dan Auto memakai RTX CUDA |
| Keamanan studio | 100 pemeriksaan lulus; storage/profile/workflow/koreksi juga lulus |
| Training detector CPU | 9 pemeriksaan lulus; 235 parameter benar-benar berubah pada fixture terisolasi |
| Tracking | 31 pemeriksaan lulus |
| Deployment HTTP | 36 pemeriksaan lulus, port ephemeral dan server terisolasi |
| Wheel/sdist | Root dan studio dibangun, konten dibandingkan dengan source, kedua wheel dipasang ke environment baru dengan dependency lokal yang sudah tersedia |
| Audit dependency | npm: 0 temuan; Python: satu exception NLTK yang belum diperbaiki upstream, guard lulus; public versions Torch/torchvision diaudit tanpa exception |
| Lock dependency | `uv lock --check` root dan studio lulus |

Coverage line+branch untuk **core/src dan extensions/src** adalah 80.83%; tidak mencakup seluruh backend/runner dan bukan akurasi AI. Import/HTTP akademik tidak memuat Torch atau Transformers. Tes video/chat/training di atas memang memuat model nyata pada fixture terpisah.

Format studio diperiksa pada source Python yang relevan dengan daftar file eksplisit. Modifikasi lama milik pengguna di `industrial_ai/tests/e2e.py` mempunyai satu perbedaan format dan sengaja tidak diubah atau dipublikasikan; harness menjalankan kode tersebut tanpa menulis ulang source maupun laporan historis.

## Browser nyata

Pada tab fixture terpisah: login/session, keyboard, autocomplete/prefix, rumus/NLL/CE/PP/EOS, pergantian stored generation step, filter/heatmap Brown, checkpoint Indonesia, validasi ordinary KN/NLTK historis, catatan absensi fiktif → chat → retraction, tema, serta lebar mobile 390 px diperiksa. Console tidak menampilkan error. Bukti screenshot dan catatan disimpan privat di `.tmp/ngram-implementation/`.

Reduced motion diuji oleh pemeriksaan otomatis; preference itu tidak dapat dipaksakan melalui browser fixture. Impor crossing diuji backend karena workspace browser tidak mempunyai rekaman. Detail LL/logP dan download CSV terakhir diverifikasi melalui build/regresi UI dan HTTP, tidak lewat ulang seluruh skenario browser.

## Reproduksi pemeriksaan

```powershell
. .\setup_lokal.ps1
uv sync --locked
uv run pytest -q
uv run ruff check core extensions jalankan_notebook.py
uv run ruff format --check core extensions jalankan_notebook.py
uv run ty check core/src extensions/src extensions/experiments jalankan_notebook.py

Set-Location industrial_ai
npm ci
npm run typecheck
npm run check
npm run build
.venv/Scripts/python.exe tests/academic_check.py
.venv/Scripts/python.exe tests/ledger_check.py
.venv/Scripts/python.exe tests/novelty_api_check.py
.venv/Scripts/python.exe tests/fact_check.py
.venv/Scripts/python.exe tests/deployment_check.py
```

Studio membutuhkan environment sendiri (`npm run setup` pada Windows); root package dipasang editable dari direktori induk. CI menjalankan suite akademik, UI/API/storage/security, training/inference CPU serta container/HTTPS. Tidak ada auto-training dari draft atau auto-label.

## Batas dan arsip

- Tiga pilot memakai 24 kombinasi per corpus, 72 worker benchmark total; checkpoint dan test receipts tidak dievaluasi ulang. Koreksi CI target hanya resampling loss tersimpan.
- Corpus, checkpoint, bobot, ledger, credential fixture, video dan screenshot runtime tetap lokal. Publikasi hanya source, dokumentasi, dan ekspor numerik yang sudah disaring.
- Audit 188 berkas core/hasil historis/perubahan pengguna: semua SHA-256 identik dengan baseline sebelum implementasi.
- Run lama menyimpan delapan source beku beserta hashes di `derived/frozen_sources/`. Code perubahan berikutnya memakai run ID baru; mismatch source bukan disembunyikan.
- Test lama sudah pernah dilihat, Wikipedia hanya empat dokumen test. Klaim konfirmatori memerlukan protokol dan holdout independen baru.
- Novelty belum diuji pada kejadian nyata berlabel independen; false alert/jam dan detection delay belum tersedia tanpa exposure/onset truth. Duration bins belum ditambahkan.
- Absensi adalah verifikasi manual administrator. Belum ada scanner badge/QR, pengenalan wajah, liveness, CCTV live atau bukti hadir sepanjang shift.
- Docker daemon lokal tidak tersedia. Pada commit `8b52f82`, job container CI telah membangun image, menjalankan restricted runtime dan membuktikan HTTPS dengan CA Caddy, Secure/HttpOnly cookie, CSRF serta logout. Pada commit `47dacf8`, [CI 38038065071](https://github.com/Maliq-dlt/N-Gram/actions/runs/38038065071) meluluskan ketiga job: academic, studio dan container. Studio mencakup API/storage/security/regresi, training detector CPU objek serta helm, dan package audit. Advisory NLTK memakai guard boundary dan exception spesifik pada [SECURITY](../../SECURITY.md#nltk-model-path-advisory-exception). Dependency upstream tetap belum patched, bukan nol kerentanan Python.

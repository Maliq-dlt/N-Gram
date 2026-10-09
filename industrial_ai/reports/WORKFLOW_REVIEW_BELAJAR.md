# Verifikasi review dan belajar

Diperbarui 9 Oktober 2026. Target: demonstrasi/portofolio lokal.
[README](../README.md) · [Checklist aktif](../../tasks/todo.md) · [CI GitHub](https://github.com/Maliq-dlt/N-Gram/actions/workflows/ci.yml)

## Hasil yang dapat dibuktikan

Koreksi yang disahkan masuk snapshot dataset. Training nyata menghasilkan checkpoint
baru dan menjalankan inferensi baru pada video. Hasil awal tetap tersedia. Training
otomatis menunggu seluruh antrean kelompok selesai dan dua sumber asli berbeda;
satu sumber atau draft hanya disimpan, belum mengubah bobot.

Masalah dataset kecil diperbaiki: `batch=2` dengan default `nbs=64` bisa menyelesaikan
pilot singkat tanpa optimizer step. `nbs=2` sekarang memperbarui setiap batch.
Tes membandingkan `named_parameters`, bukan buffer BatchNorm, dan menyamakan presisi
FP16 checkpoint agar pembulatan penyimpanan tidak dianggap sebagai pembelajaran.

| Pemeriksaan lokal | Hasil |
| --- | --- |
| Core/extensions `pytest -q` | 48 lulus; manifest core tetap cocok |
| HTTP/vision/chat nyata | 71 pemeriksaan lulus pada runtime terbaru |
| Tracking | 31 pemeriksaan lulus |
| Koreksi tersimpan/MP4 | 27 pemeriksaan lulus |
| Antrean/approval/retry/cancel/ekspor/reuse | 29 pemeriksaan lulus |
| Training objek CPU dan RTX 4060 | 9 per perangkat; 235 parameter bersama berubah |
| Training helm CPU dan RTX 4060 | 9 per perangkat; 83 parameter bersama berubah |
| Self-check, review counts, pipeline video panjang | Lulus |
| Ruff, format source publikasi, Ty | Lulus |
| JavaScript playback/tracking, CSS build | Lulus |
| npm audit | 0 advisori |
| pip-audit environment dan versi dasar Torch/vision | 0 advisori terdeteksi |
| Wheel/sdist | Source cocok; bobot/video/cache tidak masuk distribusi |

Training smoke memakai dua video geometris terkontrol di `.tmp/`, bukan ground truth
manusia/helm. Setiap run membuktikan sumber train/val terpisah, parameter berubah,
checkpoint SHA-256 cocok, model kandidat dipakai analisis baru, MP4 dapat dibaca,
dan bobot dasar tetap sama. Angka metrik smoke bukan ukuran akurasi pabrik.

Environment studio: Python 3.11, Torch 2.14.1+cu130, torchvision 0.29.1+cu130,
Transformers 5.19.0, setuptools 84.0.0. Driver RTX lokal 617.42.
Upgrade menutup advisori dependency yang ditemukan. Audit versi dasar dilakukan
terpisah karena suffix `+cu130`/`+cpu` dapat dilewati database PyPI oleh pip-audit.
Audit bersih berarti tidak ada advisori terdeteksi saat pemeriksaan, bukan jaminan
bebas seluruh celah.

## Pengujian yang dapat diulang

Dari `industrial_ai`, sesudah setup:

```powershell
. .\setup_lokal.ps1
npm run check
npm run build
npm audit --audit-level=high
uv run --frozen python tests/workflow_check.py
uv run --frozen python tests/training_check.py cpu objects
uv run --frozen python tests/training_check.py cpu helmets
uv run --frozen python tests/training_check.py cuda objects
uv run --frozen python tests/training_check.py cuda helmets
```

Command kualitas, pipeline dan media lengkap ada di README/CONTRIBUTING.
`tests/e2e.py` memerlukan server aktif. Pengulangan akhir memakai salinan script
ke `.tmp/` dengan target laporan `reports/runtime/e2e-review-v10.json` supaya laporan
sebelumnya tidak ditimpa. Script pengguna tetap identik dan dikecualikan dari commit.
Perubahan lokal pengguna pada file tersebut memiliki satu perbedaan format; source
HEAD yang akan dipublikasikan diperiksa terpisah dan lulus format.

Bukti rinci tetap lokal di `.tmp/workflow-v10/`, `industrial_ai/.tmp/`, dan
`industrial_ai/reports/runtime/`. Hanya ringkasan verifikasi ini dipublikasikan.

## Pemeriksaan browser dan operasi

Video layar penuh mempertahankan sidebar antrean/label/warna/edit/hapus; tersedia
kontrol keluar dan keyboard. Antrean/timestamp, filter, koreksi vs hasil AI, dan
simpan → training → hasil baru diperiksa di server fixture terpisah. Preview koreksi
pengguna diberi label tersendiri. Tes Node mencakup respons playback kedaluwarsa,
pause/buffering dan isolasi sesi. Tes API memeriksa revisi, pembatalan worker/proses
native, pelepasan lock, kegagalan ekspor dan reuse checkpoint setelah followup gagal.

## Pelestarian dan scope publikasi

Audit baseline mencakup 2.342 file. Core, bobot dasar, video, dataset dan artefak
akademik pada baseline tetap cocok. Tiga pengecualian dicatat terbuka:

- README root berubah sesuai permintaan dokumentasi.
- `models/manifest.json` berbeda sebagai metadata setup; bobot dasarnya cocok.
  Hash metadata awal tidak berhasil direkonstruksi; file ini tidak dipublikasikan.
- Run E2E awal memperbarui laporan runtime `reports/e2e_publication.json`.
  Salinan awal yang cocok baseline tidak ditemukan. Run berikutnya memakai laporan
  baru yang terpisah; laporan akademik dan verifikasi historis lainnya tetap cocok.

Publikasi dibatasi pada source, lockfile, aset UI, tes, CI dan dokumentasi. Tidak ada
rename besar/import migration; `core/`, `extensions/` dan path data tetap dipertahankan.
Council sudah tidak digunakan dan pemantauannya dinonaktifkan atas arahan pengguna.

## Batas yang masih berlaku

Ini belum evaluasi akurasi kerumunan/APD secara independen, instalasi Windows baru
beserta seluruh unduhan Qwen, atau deployment multi-user. Tracking manual belum
menjamin identitas/lintasan unik; CCTV live, OCR plat, wajah dan absensi tetap roadmap.
Checkout Git menormalisasi CRLF core menjadi LF. CI mengembalikan akhir baris
hanya bila kandidat byte cocok SHA-256 asli; perubahan isi tetap ditolak. Pemulihan
checkout LF dan penolakan korupsi juga diuji pada clone terpisah.
CI menjalankan pengujian CPU; RTX dan chat Qwen/LoRA divalidasi lokal. CI tidak
melakukan deployment otomatis ke mesin pengguna. Status run publik ada pada tautan CI.

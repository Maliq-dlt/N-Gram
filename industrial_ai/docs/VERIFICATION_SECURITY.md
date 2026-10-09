# Verifikasi fondasi keamanan Video Insight

Tanggal: 9 Oktober 2026. Scope: studio lokal, satu proses FastAPI, SQLite dan container CPU.

## Revisi profil dan dashboard, 9 Oktober 2026

Profil pengguna menampilkan identitas sesi nyata dan form password inline. Navigasi
menjeda video tanpa mengubah posisi; akses profil diblokir ketika unggah/review sedang
berjalan. Isian password dibersihkan saat meninggalkan halaman.

| Pemeriksaan ulang | Hasil |
| --- | --- |
| Storage dan rotasi password/sesi | Lulus, termasuk race dan rollback |
| Keamanan API | 91 assertions lulus |
| HTTP nyata, cookie/CSRF baru dan pencabutan sesi lama | 19 pemeriksaan lulus |
| UI/auth/playback/mode hasil/navigasi profil | Lima suite native lulus |
| Tracking/koreksi/workflow | 31 + 27 + 29 pemeriksaan lulus |
| UI build/typecheck, npm audit | Lulus; 0 vulnerabilities |
| Python source quality | Ruff lulus; format 36 berkas lulus, perubahan pengguna pada tests/e2e.py dikecualikan |
| Type Python | Scope production yang sama dengan workflow CI lulus |
| Browser nyata | Profil, kembali tanpa reset waktu, terang/gelap, 390px tanpa overflow; fullscreen overlay sejajar video |
| Preservasi | 4.804 berkas diperiksa; hanya tiga metadata security operasional berubah, core/bobot/hasil asli tetap |

Tes perubahan password memakai akun fixture terisolasi. Password owner asli tidak
diubah. Screenshot dan laporan rinci disimpan lokal dalam `.tmp`, tidak diterbitkan.
Tabel berikut merekam validasi fondasi sebelumnya, bukan pengulangan seluruh run
training atau pengujian Docker pada revisi UI ini.

## Bukti yang dijalankan

| Pemeriksaan | Hasil |
| --- | --- |
| Akses API, RBAC, CSRF, workspace, rate limit, metadata SQL | 84 assertions lulus |
| Server HTTP nyata, login/cookie/logout/viewer | 13 pemeriksaan lulus |
| Video/model/chat/media/koreksi nyata dengan autentikasi | 71 pemeriksaan E2E lulus |
| Tracking, ekspor koreksi, workflow | 31 + 27 + 29 pemeriksaan lulus |
| Fine-tuning objek dan helm, CPU serta CUDA | 4 run nyata; masing-masing 9 assertions lulus |
| Academic core | 48 tests lulus; core tidak diubah |
| TypeScript, JavaScript, CSS build | typecheck/check/build lulus |
| Dependency UI | npm audit: 0 vulnerabilities |
| Python | Ruff check/format dan ty lulus pada source terkait |
| Distribusi | wheel/sdist dan audit isi paket lulus |
| Docker CPU / proxy HTTPS | CI image, readonly runtime dan published HTTPS lulus |
| Preservasi | 4.800 berkas diperiksa; tidak ada perubahan |

Storage self-check memeriksa constraint, hashing/sesi, ownership, concurrent writes,
revision guard, peningkatan hash password legacy tanpa menimpa perubahan bersamaan,
backup/restore database, dan deteksi perubahan/pemotongan rantai audit.
Browser memeriksa login owner, pemutar/anotasi, kontrol fullscreen, logout, serta
viewer yang tidak dapat mengubah data. Pengujian fullscreen tidak membuktikan
semua browser/perangkat mempunyai layout yang identik.

Run training nyata mengubah parameter kandidat (contoh: 235 parameter run objek
CPU, 83 parameter run helm CUDA). Ini membuktikan optimizer bekerja, bukan bahwa
akurasi generalisasi otomatis meningkat. Bobot dasar dan hasil asli dipertahankan.

## Perintah yang dapat diulang

Dari `industrial_ai`, setelah setup dependency:

```powershell
npm run typecheck
npm run check
npm run build
npm audit --audit-level=high
uv run python tests/storage_check.py
uv run python tests/security_check.py
uv run python tests/deployment_check.py
uv run python tests/tracking_check.py
uv run python tests/corrections_check.py
uv run python tests/workflow_check.py
uv run python tests/training_check.py cpu
uv run python tests/training_check.py cpu helmets
docker compose config --quiet
```

Training CUDA memerlukan Torch CUDA dan GPU yang tersedia. Test memakai fixture
terisolasi dalam `.tmp`; jangan menggunakan data operasional sebagai fixture.
Laporan runtime rinci tidak diterbitkan karena dapat berisi path/media lokal.

## CI dan batas bukti

Workflow menguji academic core, studio, dependency, paket, image Docker readonly,
dan akses HTTPS lewat published port Caddy dari host. [Run CI patch](https://github.com/Maliq-dlt/N-Gram/actions/runs/37948789812)
lulus untuk ketiga job academic, studio dan container sebelum merge ke main. Docker daemon lokal tidak tersedia;
validasi image/runtime dilakukan pada runner CI.

Windows sandbox menolak private ACL beberapa temporary directories dan named
pipes Ultralytics. Direktori baru memakai izin turunan workspace; training nyata
tertentu dijalankan dengan persetujuan otomatis untuk command fixture spesifik.
Build lokal memakai builder setuptools terpasang; `uv build` lokal sempat gagal
pada ACL temporary directory. CI memakai `uv build` native Linux.

## Batas penggunaan

- Deployment domain publik, pemulihan seluruh media/model, dan pentest independen
  belum diverifikasi. Caddy localhost memakai CA lokal; domain publik butuh DNS
  dan sertifikat yang valid pada host target.
- SQLite dan filesystem bukan satu transaksi bersama. Backup SQL/key/anchor
  mencakup manifest media; media/model perlu dicadangkan terpisah.
- HMAC memverifikasi rantai audit, bukan seluruh tabel. Key/anchor pada host sama
  tidak melindungi dari administrator host.
- Model/lock/tracker masih satu proses. Multiworker dan tenant dengan worker
  terisolasi membutuhkan rancangan lanjutan.
- Absensi wajah, enrollment biometrik, PAD/liveness, dan keputusan kehadiran
  otomatis belum diterapkan.
- Hak Ultralytics/checkpoint harus ditinjau sebelum distribusi komersial.

Lihat [hardening dan fase lanjutan](HARDENING.md) serta [kebijakan keamanan](../../SECURITY.md).

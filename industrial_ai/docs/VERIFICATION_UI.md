# Verifikasi perbaikan UI — 10 Oktober 2026

## Status migrasi React terbaru — 2026-10-10

Halaman studio memakai React 19.3.0 dan TypeScript strict, controller media/editor
berasal dari frontend/studio.ts. Tampilan data dinamis dipindahkan ke LiveViews.tsx;
implementasi, suite UI, backend dan paket source akhir terverifikasi. Bundle production lokal app.js
sekitar 260 KB; Lenis 1.3.26, Framer Motion 14.1.0 dom/mini dan esbuild 0.28.2
tetap lokal tanpa CDN. Index hanya entry root dan script.

Verifikasi UI terakhir lulus: sembilan suite (SSR React, LiveViews, playback,
tracking, auth, mode hasil, profil, Canvas dan motion), strict typecheck/build,
audit dependency 0. App production sekitar 259,7 KB; motion sekitar 31,9 KB.
Backend akhir lulus 91 security checks, profile API, storage, 36 HTTP checks
dan Ruff/Ty scoped. Wheel/sdist source equality lulus setelah source auth stabil,
termasuk LiveViews, seluruh komponen TSX, auth dan bundle produksi; data/model/cache
dikecualikan. Artefak akhir: `.tmp/packages-frontend-tidy`.
Report HTTP akhir: `.tmp/deployment-21fa560a9bab41aba7039aa656f720fd/verification.json`.
Source auth/motion dan konfigurasi dikumpulkan di frontend/; bundle tetap pada
path server semula. Refresh tanpa flash login, re-login eksplisit, nama radio
snapshot terpisah, geometri video dan scroll panel snapshot ikut diverifikasi.
Hasil CI per commit (academic, studio dan container) tersedia di [GitHub Actions](https://github.com/Maliq-dlt/N-Gram/actions/workflows/ci.yml).

Browser fixture memverifikasi circle tema kedua arah (theme-circle.jpg dan
snapshot reverse), refresh tanpa kerumunan/delay, logout/login eksplisit dengan
loader, grounded chat melalui API nyata dan pesan React, serta fullscreen
anotasi dengan tombol keluar dan Lenis nonaktif/resume setelah keluar. Mobile
390 px memiliki clientWidth/scrollWidth sama 375 px, tanpa overflow horizontal.
Tidak ada error runtime baru setelah perbaikan mount React. Reversal wheel
diverifikasi pada controller/unit; FPS atau respons wheel fisik belum diukur.
Ini tidak menguji akurasi CCTV.

Browser akhir memastikan ukuran frame video snapshot sama dengan video live (477 × 357,75 px) dan radio hasil tetap terpilih; refresh menjaga login/loading tetap hidden.

Circle tema terbaru selalu memakai snapshot UI nyata dengan palet tujuan,
900 ms dari toggle sebelum commit tema live; reduced motion/fullscreen langsung.
Input file/password snapshot kosong, ID dipisahkan dan snapshot inert; node video
live tetap terpasang. Wheel reversal membuang target lama; nested scroll native.
Loader hanya login/logout eksplisit minimal 3,2 detik; refresh/restorasi sesi
tanpa kerumunan/delay. Reduced motion melewati tambahan durasi; error langsung.

## Milestone motion sebelumnya — 2026-10-10, sebelum migrasi React

Tujuh suite UI, typecheck/build/audit lulus pada implementasi DOM sebelumnya;
32 pemeriksaan HTTP lulus. Implementasi tersebut memakai circle native 720 ms
atau fallback wipe 560 ms + fade 160 ms. Angka dan perilaku ini adalah riwayat,
sudah digantikan oleh snapshot circle 900 ms dan React pada revisi terbaru.

## Bukti tahap perbaikan profil/UI sebelum penambahan motion

Hasil berikut adalah milestone sebelumnya, bukan pengulangan seluruh verifikasi
backend/media/paket pada perubahan motion terbaru.

| Pemeriksaan | Hasil |
| --- | --- |
| `npm run check` | Enam suite lulus: playback, tracking, auth, mode hasil, profil, animasi |
| `npm run typecheck` / `npm run build` | Lulus |
| `npm audit --audit-level=high` | 0 vulnerability |
| `tests/profile_api_check.py` | Lulus: penyimpanan privat, CSRF, validasi foto, audit |
| `tests/security_check.py` | 91 assertion lulus |
| `tests/deployment_check.py` | 28 pemeriksaan HTTP lulus, termasuk aset/MIME/nosniff |
| Ruff / Ty | Lint dan type-check studio lulus; format file yang diubah lulus |
| Wheel/sdist + `tests/package_check.py` | Aset/source cocok; data, model dan cache dikecualikan |
| SHA-256 preservasi | 4.828 berkas asli identik, tidak ada yang hilang |

Handler auth diuji untuk kegagalan, double-submit, dan pencegahan request
profil/password bersamaan agar respons lama tidak mengembalikan token CSRF lama.
Tes juga menolak encoding UTF-8 rusak. Lifecycle Canvas diuji untuk reduced
motion, cleanup saat selesai/gagal, dan callback gambar yang terlambat.

## Verifikasi browser tahap sebelumnya

Pada server fixture terisolasi: login, nama dan avatar bertahan setelah refresh,
tema terang/gelap berfungsi, mobile 390 px tanpa overflow, serta fullscreen
anotasi mempertahankan video dan inspector. Chat Qwen dengan adapter lokal
benar-benar melakukan inferensi GPU; orb menghilang dan kontrol aktif kembali.
Tidak ada password akun operasional yang diubah.

Fixture video memakai hasil smoke COCO8 yang sudah tersedia. Itu menguji UI,
bukan akurasi CCTV. Ganti password diuji lewat API/handler, bukan dengan mengubah
password owner pada browser.

## Batas bukti

Perbaikan ini tidak mengubah model, dataset, core N-gram, atau hasil analisis
asli. Akurasi detector dan kesiapan produksi tidak diklaim meningkat.
Perubahan pengguna pada `tests/e2e.py` tetap lokal dan tidak masuk publikasi;
file tersebut memiliki masalah format lokal yang tidak disentuh oleh perbaikan.
Riwayat validasi keamanan dan deployment tersedia di
[VERIFICATION_SECURITY.md](VERIFICATION_SECURITY.md).

# Verifikasi perbaikan UI — 10 Oktober 2026

Perbaikan memakai referensi 21st.dev yang diminta pengguna, dengan adaptasi
DOM/CSS/Canvas lokal. Logo A — Split V dipilih pengguna. Tidak ada runtime
frontend atau dependency baru; auth tetap TypeScript strict.

## Hasil yang diuji

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

## Verifikasi browser

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

# To-do Video Insight Lokal

Target: demonstrasi/portofolio lokal. Diperbarui 9 Oktober 2026.
Demo upload/tracking/chat sudah berjalan dan diuji. Checklist ini menunjukkan
pekerjaan aktif; kriteria seluruh fase ada di [roadmap lengkap](roadmap_checklist.md).

## Status demo lokal — 8 Oktober 2026

- [x] Subproyek terpisah; dependency Python/npm terkunci dan cache lokal.
- [x] Upload tervalidasi; dua video H264 asli/tracking dengan kontrol sinkron.
- [x] Deteksi orang/mobil/bus/truk/motor/sepeda, ByteTrack dan detector helm terpisah.
- [x] Counting terlihat/lintasan, bukti sesuai kelas, history dan unduhan MP4/JSON.
- [x] Chat Qwen3-1.7B lokal dan pilot LoRA nyata; CPU/Auto RTX 4060 teruji.
- [x] Qwen dasar berjalan tanpa adapter; fine-tuning opsional saat setup.
- [x] Anotasi kotak AI/manual, label khusus, nama/warna dan draft otomatis.
- [x] Klik kiri menggambar; klik kanan/Escape membatalkan interaksi/kotak baru.
- [x] Anotasi layar penuh dengan sidebar label/warna/edit/hapus dan kontrol keyboard.
- [x] Preview mengikuti kotak tanpa training ulang saat play/simpan/query.
- [x] Tracking koreksi tersimpan lintas restart dan ekspor MP4 per revisi.
  Rentang yang disiapkan tersimpan; label tetap perlu ditinjau sebelum training.
- [x] CLI segmentasi video panjang, seleksi frame dan draft label objek/helm.
  Split dataset memakai identitas video asal untuk mencegah kebocoran antarsegmen.
- [x] Koreksi lengkap dipakai dashboard/chat/JSON pada posisi yang disahkan.
- [x] Ringkasan mengikuti isi video dan pertanyaan orang memakai bukti orang.
- [x] Dataset YOLO dengan provenance; training kandidat terpisah dari dua sumber.
- [x] Tema sistem/terang/gelap dan pemeriksaan alur browser/mobile.
- [x] npm setup untuk Python/model lokal; dokumentasi dan npm start tersedia.
- [x] 71 pemeriksaan E2E dan 31 tracking checks, self-check/review-count checks,
  npm check/build/audit, Ruff/Ty serta build/audit paket lulus.
- [x] Source penting di GitHub; model, video pengguna dan hasil runtime tetap lokal.
- [x] 1.583 hash hasil/model/artefak akademik lama identik saat publikasi.

Bukti: [Verifikasi publik](../industrial_ai/reports/VERIFIKASI_PUBLIK.md).
Tes membuktikan alur aplikasi berjalan; belum mengukur akurasi pada semua kondisi.

## Perbaikan review dan belajar — 9 Oktober 2026

- [x] Antrean sampel, draft, deteksi meragukan dan awal target tracker hilang.
- [x] Approval objek/helm terpisah; edit geometri membatalkan approval terkait.
- [x] Training otomatis setelah seluruh antrean kelompok selesai dan dua sumber berbeda.
- [x] Snapshot disahkan, fingerprint konsisten, split menurut sumber asli.
- [x] Update parameter nyata teruji pada CPU/RTX; hasil baru memakai checkpoint kandidat.
- [x] Hasil awal tetap tersedia; koreksi pengguna diberi label terpisah dari hasil model.
- [x] Retry upload lengkap, cancel kooperatif dan ekspor CPU asinkron dengan progress.
- [x] Kandidat selesai dapat menganalisis ulang setelah followup gagal tanpa training ulang.
- [x] CI kualitas/API/media/training/paket serta audit dependency dan Dependabot.
- [x] README, CONTRIBUTING, SECURITY dan MIT source asli dengan atribusi pihak ketiga.
- [x] Struktur kode dipertahankan; peta repository dan navigasi dokumentasi diperjelas.

Bukti dan batas: [Verifikasi review/belajar](../industrial_ai/reports/WORKFLOW_REVIEW_BELAJAR.md).
Status CI berjalan ditampilkan pada [GitHub Actions](https://github.com/Maliq-dlt/N-Gram/actions/workflows/ci.yml).
Fine-tuning terbukti berjalan, tetapi peningkatan akurasi memerlukan evaluasi independen.

## Fondasi akses dan database — 9 Oktober 2026

- [x] Login, admin/reviewer/viewer, pemisahan resource/model menurut workspace.
- [x] SQLite authoritative, migrasi tanpa menghapus media, revisi dan backup database.
- [x] CSRF seluruh mutasi, pembatasan login/API, cookie HttpOnly dan header keamanan.
- [x] Audit HMAC/anchor, uji perubahan/truncation log dan restore database.
- [x] Auth TypeScript strict, kontrol viewer, menu akun dan informasi lanjutan dilipat.
- [x] Profil readonly dari identitas sesi nyata; password scrypt bersalt dan rotasi
  seluruh sesi/cookie/CSRF tanpa menghapus video atau anotasi.
- [x] Avatar/aksi akun dari adaptasi Origin UI dropdown-menu #393 dan mode hasil
  segmented-control #23552 memakai elemen native; verifikasi UI terbaru dicatat terpisah.
- [x] Docker CPU/Compose/Caddy dan CI lint/typecheck/API/security/container.
- [ ] Deployment HTTPS dengan domain nyata dan uji pemulihan seluruh media.
- [ ] Audit independen/pentest; external anchor, kuota dan worker shared sebelum skala besar.
- [ ] Enrollment wajah/PAD dan aturan absensi setelah data berizin/evaluasi tersedia.

Rincian: [fase hardening dan absensi](../industrial_ai/docs/HARDENING.md).
Status centang CI berarti pipeline tersedia; hasil run dicatat pada laporan verifikasi.

## Perbaikan berikutnya pada demo

- [ ] Ukur tracking kerumunan dengan video independen: ID switch/IDF1 dan error hitungan.
  Occlusion/objek berdekatan masih dapat menyebabkan kotak hilang atau ID tertukar.
- [ ] Perluas dataset helm/APD dan ukur FP/FN pada data yang tidak dipakai training.
- [ ] Uji setup dari clone kosong, termasuk unduhan semua model; publikasi baru
  menguji setup library dan inferensi memakai bobot lokal yang sudah tersedia.
- [ ] Tinjau label publik objek/helm, lalu evaluasi kandidat pada sumber terpisah.
  [Pipeline dan sumber data](video_training_pipeline.md); auto-label tetap draft.
- [x] Audit revisi dan backup/restore database ke direktori baru. Media tetap perlu backup terpisah.
- [ ] Bandingkan chat dasar/LoRA pada 100 prompt dengan rubrik dan decoding yang sama.

Prioritas awal: evaluasi kerumunan, data helm dan reproduksi setup. Model lebih
besar/ReID baru dipilih setelah perbandingan kecepatan/akurasi yang terukur.

## Fitur lanjutan yang belum dikerjakan

- [ ] Input foto sebagai tambahan upload video.
- [ ] Satu webcam/CCTV aktif, reconnect dan pengujian beban berkelanjutan.
- [ ] Detector/OCR plat, foto kendaraan utuh dan zoom/crop plat.
- [ ] Absensi QR, registry peserta, shift dan query absensi.
- [ ] Pencarian SOP dengan rujukan dokumen.
- [ ] Identitas wajah sebagai pengembangan opsional setelah evaluasi khusus.

Daftar ini adalah perluasan proyek; bukan syarat agar demo video/chat dapat digunakan.
Gate fase lengkap tidak dicentang hanya karena sebagian implementasi tersedia.

## Source dan panduan

- [Aplikasi di GitHub](https://github.com/Maliq-dlt/N-Gram/tree/main/industrial_ai).
- [README dan setup](../industrial_ai/README.md).
- [Rencana pengembangan](plan.md).
- [Checklist rinci seluruh fase](roadmap_checklist.md).

Bobot/adapter tidak diunggah. Clone baru memakai Qwen dasar; fine-tuning lokal
tersedia secara terpisah. Hasil lama tidak dihapus atau ditimpa oleh publikasi.


## Perbaikan referensi UI — 2026-10-10

- [x] Login nyata tanpa kredensial publik dan pendaftaran contoh.
- [x] Logo Split V dipilih pengguna; sumber SVG dan panduan di docs/brand.
- [x] Tema gelap/terang lembut, toggle di header, opsi mengikuti sistem di profil.
- [x] Nama/foto profil disimpan melalui API terotorisasi ke SQLite.
- [x] Indikator password, pengungkapan password dan rotasi sesi tetap berfungsi.
- [x] Orb lokal dalam chat dan loading kerumunan selama proses yang sebenarnya.
- [x] Regression profil/animasi masuk CI; aset lokal masuk wheel/sdist.

## Penambahan motion — 2026-10-10 (milestone sebelum migrasi React)

- [x] Loader minimum 3,2 detik sesuai permintaan pengguna, menunggu data nyata;
  reduced motion tanpa tambahan durasi, error langsung dan pembatalan sesi stale.
- [x] Lenis 1.3.26 dan Framer Motion 14.1.0 dom/mini, bundle lokal ~30,5 KB
  oleh esbuild 0.28.2; tanpa React runtime.
- [x] Circle tema native 720 ms; fallback WebView wipe 560 ms + fade 160 ms.
- [x] Lifecycle scroll dialog/fullscreen/hidden/signed-out/reduced motion dan
  cleanup animasi stale diuji; area scroll bersarang tetap native.
- [x] Verifikasi lokal: tujuh suite UI, typecheck, build dan audit lulus;
  baseline HTTP terakhir 32 pemeriksaan, terpisah dari suite motion.
Milestone motion ini digabungkan ke publikasi migrasi React di bawah.

## Migrasi React dan perbaikan scroll/tema — 2026-10-10

- [x] React/react-dom/types exact 19.3.0, bundle production lokal; audit dependency 0.
- [x] Halaman React TSX, auth/controller media/editor TypeScript strict.
- [x] Tampilan data dinamis LiveViews.tsx dan regression controller.
- [x] Circle snapshot UI nyata 900 ms, file/password kosong, inert/ID terpisah.
- [x] Wheel reversal Lenis membuang target lama; nested scroll tetap native.
- [x] HTTP deployment 36 pemeriksaan lulus pada snapshot React lokal.
- [x] Sembilan suite UI, strict typecheck/build dan audit 0.
- [x] Backend91 security/36 HTTP, profil/storage dan wheel/sdist source equality setelah auth akhir.
- [x] Browser circle kedua arah, scroll, refresh tanpa loader, login/logout, chat React dan fullscreen.
- [x] Loader hanya login/logout eksplisit; refresh/restorasi sesi tanpa delay.
- [x] Pipeline CI academic/studio/container aktif pada main; hasil setiap commit tersedia di [GitHub Actions](https://github.com/Maliq-dlt/N-Gram/actions/workflows/ci.yml).

# Checklist Eksekusi Chatbot dan Deteksi Visual

Acuan: [plan.md](plan.md). Tanggal: 8 Oktober 2026.
Target: demonstrasi/portofolio lokal. Prototipe unggah video + perbandingan + hasil + chat
sudah dapat dijalankan dan diuji; [README aplikasi](../industrial_ai/README.md) dan laporan aktual
menjadi rujukan kemampuan yang sudah terbukti. Checklist di bawah adalah gate roadmap
penuh: tidak dicentang bila hanya sebagian kriteria tersedia.

## Status demo lokal — 8 Oktober 2026

Checklist ini mencatat implementasi demo saat ini; gate roadmap lengkap di bawah
mencakup dataset/evaluasi dan fitur masa depan yang belum selesai.
Bukti publik: [VERIFIKASI_PUBLIK.md](../industrial_ai/reports/VERIFIKASI_PUBLIK.md).

- [x] Subproyek terpisah, dependency Python/npm terkunci dan cache lokal.
- [x] YOLO26n + ByteTrack untuk orang/mobil/bus/truk/motor/sepeda; detector helm terpisah.
- [x] Upload tervalidasi, dua video H264 sinkron, bukti, history dan unduhan.
- [x] Qwen3-1.7B lokal, pilot LoRA nyata dan reload; CPU/Auto GPU teruji.
- [x] Qwen dasar menghasilkan jawaban tanpa adapter; fine-tuning tidak wajib saat setup.
- [x] Anotasi label bawaan/khusus, nama/warna, klik kiri/kanan/Escape dan draft.
- [x] Preview koreksi mengikuti gerak tanpa fine-tuning saat play/simpan/query.
- [x] Koreksi objek lengkap dipakai dashboard/chat/JSON pada posisi yang disahkan.
- [x] Ringkasan mengikuti kelas ditemukan; pertanyaan orang memakai bukti orang.
- [x] Ekspor YOLO dengan provenance; training kandidat dari review sumber terpisah.
- [x] Tema sistem/terang/gelap dan alur dashboard; regresi playback/buffer/stale response.
- [x] Setup Python lewat npm, dokumentasi unduh model lokal dan start server.
- [x] Source penting diunggah ke GitHub; SHA branch remote cocok dengan commit lokal.
- [x] 71 pemeriksaan HTTP/video/chat nyata, 31 tracker checks, self-check, Ruff/Ty,
  npm check/build/audit lulus pada verifikasi publikasi.
- [ ] Evaluasi kerumunan independen: ID switch/IDF1 serta akurasi jumlah orang.
- [ ] Dataset APD pengguna beragam dan evaluasi helm independen FP/FN.
- [ ] Benchmark chat 100 prompt dan perbandingan LoRA vs baseline yang terkontrol.
- [ ] Koreksi tracking persisten untuk seluruh video/ekspor MP4 hasil koreksi.
- [ ] Audit riwayat koreksi serta backup/restore teruji.
- [ ] Input foto, SOP/RAG, CCTV aktif, OCR plat, absensi dan identitas wajah.

Paket source/wheel/sdist dan 36 berkas publik telah diaudit; 1.583 hash hasil/model
lama identik. Publikasi [branch GitHub](https://github.com/Maliq-dlt/N-Gram/tree/codex/video-tracking-chat/industrial_ai) berhasil; commit source `7af34a0` cocok dengan SHA branch remote. Bobot/video/hasil
lama berada lokal dan tidak dihapus. Setup dependency-only diuji, unduh ulang seluruh
model ke environment kosong belum diuji pada publikasi ini.

## Cara menandai selesai

- Kerjakan sesuai dependensi; satu task menyentuh maksimal sekitar lima file.
- S/M adalah perkiraan ukuran: S 1-3 file, M 3-5 file; pecah lagi bila membesar.
- Kriteria harus dibuktikan. Catat command aktual, exit code, output, versi/hash,
  dan kekurangan pada laporan fase. Jangan memberi centang hanya dari inspeksi kode.
- Path file di bawah adalah usulan roadmap. Struktur prototipe aktual lebih kecil dan
  tercatat di README; tidak semua file usulan perlu dibuat sebelum dibutuhkan.
- Semua cache/test/output dalam workspace. Jalankan test fokus dan checks relevan.

## Fase 0. Dokumentasi

- [x] P0.1: Skenario, persiapan dan arsitektur usulan tertulis dalam plan.md.
- [x] P0.2: Semua fase mempunyai dependensi, task, verifikasi dan gate.
- [x] P0.3: Target portofolio lokal dikonfirmasi; rekomendasi teknis diberi status usulan.
- [x] P0.4: Struktur/tautan, whitespace/diff dan hash baseline diperiksa.

Bukti P0: .tmp/platform-docs/documentation_check.json dan pemeriksaan git diff.
P0 sudah selesai. Prototipe awal mengerjakan sebagian T01/T04/T05/T07/T08/T09/T11/T12.
Gate resmi belum ditutup: dataset APD berlabel, benchmark 100 prompt, review/audit,
SOP, dan fase live/plat/absensi belum tersedia. Laporan membedakan smoke test dan
training pilot dari kelulusan gate roadmap.

## Fase 1. Kelayakan dan data

### T01: Environment dan smoke model

- [ ] **T01 selesai dengan bukti**

Buat subproyek terisolasi, kunci dependency dan uji model/inferensi/training singkat pada hardware yang tersedia.

**Dependensi:** P0. **Ukuran:** M.

**Kriteria:**

- [x] Cache/download/temp berada dalam workspace; hasil N-gram tetap utuh.
- [ ] Load dan inferensi pretrained nyata berhasil; CPU/GPU, versi Torch, disk, port dan memori terlapor.
- [x] Satu langkah forward/backward adapter membuktikan jalur training; backend gagal dilaporkan.

**Verifikasi:** Setup dari shell baru; smoke inferensi dan satu langkah training; restart/load ulang. Simpan command/exit code di reports/phase_1.md.

**File usulan:** industrial_ai/pyproject.toml; uv.lock; setup_lokal.ps1; training/smoke.py; reports/phase_1.md.

### T02: Audit dataset helm dan split

- [ ] **T02 selesai dengan bukti**

Siapkan data berizin, mapping person/helmet/no_helmet, video independen dengan ground truth orang yang terlihat dan lintasan pada garis/arah counting.

**Dependensi:** T01. **Ukuran:** M.

**Kriteria:**

- [ ] Sumber/lisensi, jumlah kelas, semantik box, mapping dan pengecualian tercatat.
- [ ] Group/hash split tidak menunjukkan sumber video atau near-duplicate melintasi train/validation/test.
- [ ] Sampel label, jumlah test/instance, ground truth kejadian, jumlah terlihat dan minimal 20 lintasan orang sesuai plan tersedia.

**Verifikasi:** Jalankan pemeriksaan box/label/group; lihat sampel tiap kelas/kasus sulit; cocokkan manifest dengan disk.

**File usulan:** industrial_ai/training/prepare_helmets.py; data/helmets/data.yaml; data/helmets/manifest.json; reports/data_helmets.md.

### Gate fase 1

- [ ] Smoke inferensi/training dan audit data lulus; jalur eksekusi feasible.
- [ ] Semua task fase selesai dan reports/phase_1.md memuat command/exit code/output/versi/kekurangan.

## Fase 2. Deteksi helm dari file

### T03: Fine-tuning dan evaluasi YOLO helm

- [ ] **T03 selesai dengan bukti**

Latih YOLO26n custom; pilih checkpoint/threshold dari validation lalu bekukan sebelum test.

**Dependensi:** T02. **Ukuran:** M.

**Kriteria:**

- [ ] Checkpoint/config/seed/label map/split hash/log dan versi tersimpan.
- [ ] Gate precision/recall no_helmet lulus; AP/mAP dan FP/FN per kondisi dilaporkan.
- [ ] Checkpoint reload di proses baru memberikan hasil konsisten pada input berhash.

**Verifikasi:** Training nyata, evaluasi held-out, inspeksi FP/FN dan reload. Threshold tidak dituning pada test.

**File usulan:** industrial_ai/training/train_helmets.py; training/evaluate_helmets.py; models/helmets/manifest.json; reports/helmets_eval.json.

### T04: Inferensi file yang tervalidasi

- [ ] **T04 selesai dengan bukti**

Bangun inferensi file, tracking orang, asosiasi helm, status/warna/ID dan video output beranotasi.

**Dependensi:** T03. **Ukuran:** M.

**Kriteria:**

- [x] Ukuran/decode/durasi/path dan batas kerja tervalidasi; input rusak ditangani.
- [ ] Helm di tangan/association ambigu tidak otomatis patuh; unknown dapat dihasilkan.
- [x] Box mengikuti track dengan hijau helm/merah tanpa helm/kuning unknown + label/ID/skor; video output mencatat sumber/model dan tidak menimpa input.

**Verifikasi:** Uji media nyata berlabel, corrupt/oversize/path di luar workspace, occlusion dan orang berdekatan.

**File usulan:** industrial_ai/app/vision.py; app/media.py; tests/test_vision.py; tests/test_media.py.

### T05: Counting, kejadian dan review

- [ ] **T05 selesai dengan bukti**

Simpan run/event/passage, dedup kejadian, hitung orang terlihat/lintasan lewat dan audit review; gunakan counter Ultralytics bila memenuhi aturan.

**Dependensi:** T04. **Ukuran:** M.

**Kriteria:**

- [x] Kejadian kontinu tidak diduplikasi; jumlah terlihat dan lintasan/arah pada garis dicatat terpisah, ID tracker dibatasi sesi/sumber.
- [ ] Bukti/review/audit tersimpan; association ambigu tidak menjadi pelanggaran pasti.
- [ ] Gate event/counting dan waktu Asia/Jakarta lulus; siapa tanpa helm merujuk track ID/bukti, tanpa menebak nama.

**Verifikasi:** Cocokkan ground truth interval/counting; uji jitter, occlusion, re-entry, dua orang, ID berubah dan replay/retry; restart DB dan buka bukti.

**File usulan:** industrial_ai/app/storage.py; app/events.py; tests/test_events.py; tests/test_storage.py.

### Gate fase 2

- [ ] Gate helm/event/counting lulus; video warna/label/ID, bukti dan tinjauan bertahan setelah restart.
- [ ] Semua task fase selesai dan reports/phase_2.md memuat command/exit code/output/versi/kekurangan.

## Fase 3. Chatbot kecil fine-tuned

### T06: Data percakapan dan baseline

- [ ] **T06 selesai dengan bukti**

Susun percakapan Bahasa Indonesia dengan keluarga skenario dan rubrik; evaluasi Qwen baseline.

**Dependensi:** T01. **Ukuran:** M.

**Kriteria:**

- [x] Data/sumber sintetis-publik-manual diperiksa; credential/data pribadi tak perlu dikeluarkan.
- [ ] Split family-aware; test 100 prompt/rubrik dibekukan; tidak ada parafrasa training bocor.
- [ ] Baseline bahasa, chat umum, konteks, format fungsi, ketidakpastian dan latency tersimpan.

**Verifikasi:** Validasi schema/group overlap; review sampel; jalankan baseline nyata dengan decoding tercatat.

**File usulan:** industrial_ai/training/prepare_chat.py; data/chat/manifest.json; data/chat/rubric.md; training/evaluate_chat.py; reports/chat_baseline.json.

### T07: LoRA dan verifikasi adapter

- [ ] **T07 selesai dengan bukti**

Fine-tune instruction model kecil untuk perilaku/tugas, bukan menghafalkan catatan harian.

**Dependensi:** T06. **Ukuran:** M.

**Kriteria:**

- [x] Training nyata selesai; base revision/adapter/tokenizer/template/config/seed/split hash/log tersimpan.
- [x] Mask padding/prompt sesuai strategi loss diperiksa pada batch nyata sebelum training penuh.
- [ ] Reload adapter berhasil; gate bahasa/tugas dan manfaat vs baseline tanpa regresi chat umum terukur.

**Verifikasi:** Smoke lalu training penuh; evaluasi berpasangan decoding sama. QLoRA hanya setelah compatibility smoke lulus.

**File usulan:** industrial_ai/training/train_chat.py; tests/test_chat_training.py; models/chat/manifest.json; reports/chat_finetune.json.

### T08: Chat lokal dengan konteks sesi

- [ ] **T08 selesai dengan bukti**

Sediakan service chat memakai adapter hasil training dengan batas konteks/token/antrean.

**Dependensi:** T07. **Ukuran:** S.

**Kriteria:**

- [ ] Revision/adapter yang dipakai tercatat; model gagal/hilang memberi status jelas.
- [ ] Follow-up terisolasi per sesi dan penggunaan memori dibatasi.
- [x] Chat Indonesia berjalan setelah restart dan ketika vision belum aktif.

**Verifikasi:** Percakapan multi-turn lewat API/proses baru; uji dua sesi, limit konteks dan kegagalan model.

**File usulan:** industrial_ai/app/chat.py; app/main.py; tests/test_chat.py.

### Gate fase 3

- [ ] Training, baseline comparison, reload dan chat biasa terbukti berjalan.
- [ ] Semua task fase selesai dan reports/phase_3.md memuat command/exit code/output/versi/kekurangan.

## Fase 4. MVP deteksi dan tanya AI

### T09: Fungsi query kejadian

- [ ] **T09 selesai dengan bukti**

Hubungkan chatbot dengan fungsi berizin untuk kejadian, jumlah terlihat, lintasan dan track ID/bukti; validasi waktu/source/review serta satuan query.

**Dependensi:** T05, T08. **Ukuran:** M.

**Kriteria:**

- [ ] Nama fungsi/argumen divalidasi; query terparameterisasi; raw SQL model tidak dieksekusi.
- [ ] Jumlah terlihat/lintasan/kejadian, arah/rentang/status/cakupan cocok query rujukan; data kosong dan identitas belum tersedia dijelaskan.
- [ ] Narasi konflik memakai ringkasan terverifikasi; fallback rate dan akurasi sebelum fallback tercatat.

**Verifikasi:** Fixture bertanggal, dua sesi, tanggal ambigu, fungsi/argumen tidak sah; cocokkan semua jumlah dengan SQLite.

**File usulan:** industrial_ai/app/tools.py; app/chat.py; tests/test_tools.py; tests/test_chat.py.

### T10: SOP dengan rujukan

- [ ] **T10 selesai dengan bukti**

Impor Markdown/teks demo dengan hash/bagian dan cari menggunakan FTS5.

**Dependensi:** T09. **Ukuran:** M.

**Kriteria:**

- [ ] Sumber asli tidak ditimpa; dokumen/versi/bagian dapat dirujuk.
- [ ] Gate SOP 30 pertanyaan lulus; tanpa sumber tidak mengarang rujukan.
- [ ] Instruksi dalam dokumen diperlakukan sebagai data, tidak memberi hak tool/command.

**Verifikasi:** Uji kutipan/perubahan versi/no-results/karakter query khusus dan teks berisi instruksi palsu.

**File usulan:** industrial_ai/app/documents.py; app/tools.py; tests/test_documents.py; reports/sop_eval.json.

### T11: UI unggah dan tinjauan

- [ ] **T11 selesai dengan bukti**

Buat upload, hasil/bukti, riwayat event dan kontrol review pada browser.

**Dependensi:** T09. **Ukuran:** M.

**Kriteria:**

- [ ] Upload/proses/error/bukti/review dapat digunakan; perubahan review mempunyai audit.
- [x] Video beranotasi hijau/merah/kuning + teks/ID, unknown/review jelas; konten tak tepercaya tidak mengeksekusi HTML.
- [x] Label/keyboard/focus/kontras dan layar kecil dapat digunakan.

**Verifikasi:** Browser flow foto/video nyata, error/restart, review vs database dan akses keyboard.

**File usulan:** industrial_ai/templates/base.html; templates/detection.html; app/main.py; static/app.css; static/app.js.

### T12: UI chat dan demo MVP

- [ ] **T12 selesai dengan bukti**

Buat chat dengan follow-up/fakta/sumber/bukti dan demonstrasikan seluruh milestone pertama.

**Dependensi:** T10, T11. **Ukuran:** M.

**Kriteria:**

- [x] Chat umum/query vision berjalan di UI; bukti sesuai sesi dan filter.
- [ ] S01-S05/S11-S12 lulus; tanya jumlah orang/siapa tanpa helm memberi satuan/track ID/bukti yang sesuai, angka cocok DB.
- [x] Status model/error/cakupan, response time dan fallback terlihat/tercatat.

**Verifikasi:** Demo upload -> review -> tanya -> buka bukti; screenshot/log nyata dan uji konten HTML berbahaya.

**File usulan:** industrial_ai/templates/chat.html; static/app.js; app/main.py; tests/test_mvp.py; reports/phase_4.md.

### Gate fase 4

- [ ] MVP dapat didemokan dari input hingga jawaban bersumber tanpa hasil operasional rekaan.
- [ ] Semua task fase selesai dan reports/phase_4.md memuat command/exit code/output/versi/kekurangan.

## Fase 5. Satu kamera langsung

### T13: Capture dan status koneksi

- [ ] **T13 selesai dengan bukti**

Tambahkan satu webcam, start/stop/reconnect, bounded queue dan riwayat cakupan.

**Dependensi:** T12. **Ukuran:** M.

**Kriteria:**

- [ ] Start berulang tidak membuat worker ganda; antrean dibatasi/dropped frames dicatat.
- [ ] Sumber/interval tanpa rekaman tercatat; UI dan chatbot melihat cakupan yang sama.
- [ ] Kamera lambat/putus tidak membekukan aplikasi; sesi baru mereset scope tracker.

**Verifikasi:** Replay deterministik dan webcam nyata; putus/sambung, start berulang, stop dan cleanup proses.

**File usulan:** industrial_ai/app/camera.py; app/main.py; templates/camera.html; tests/test_camera.py.

### T14: Kejadian live yang konsisten

- [ ] **T14 selesai dengan bukti**

Pakai timestamp dan aturan temporal tervalidasi untuk kandidat/tracking/event/bukti.

**Dependensi:** T13. **Ukuran:** M.

**Kriteria:**

- [ ] Event/counting live tidak dihitung setiap frame; reconnect/re-entry mengikuti garis/arah dan aturan sesi.
- [ ] Gangguan singkat/occlusion tidak otomatis no_helmet; association ambigu unknown.
- [ ] Interval/bukti/review benar setelah reconnect dan restart.

**Verifikasi:** Replay video berlabel pada FPS/sampling berbeda; cocokkan ground truth dan kasus tracker berubah/occlusion.

**File usulan:** industrial_ai/app/events.py; app/camera.py; tests/test_events.py; reports/live_events_eval.json.

### T15: Profil kamera bersama chatbot

- [ ] **T15 selesai dengan bukti**

Ukur beban demo nyata 30 menit, FPS/latency/antrean dan RAM/VRAM yang dapat diakses.

**Dependensi:** T14. **Ukuran:** S.

**Kriteria:**

- [ ] Gate live dan p95 chat lulus pada konfigurasi terlapor; capture/inference FPS dibedakan.
- [ ] Reconnect dan chat selama capture tidak membuat crash/pertumbuhan memori terus-menerus.
- [ ] Resolusi/sampling/warm-up/panjang chat/dropped frames/keterbatasan tersimpan.

**Verifikasi:** Uji 30 menit dan >= 30 pertanyaan setelah warm-up; simpan metrik/log; optimasi berdasarkan bottleneck terukur.

**File usulan:** industrial_ai/training/profile_app.py; app/camera.py; reports/phase_5.md.

### Gate fase 5

- [ ] Live satu kamera/chat lulus soak test, reconnect dan target kinerja terukur.
- [ ] Semua task fase selesai dan reports/phase_5.md memuat command/exit code/output/versi/kekurangan.

## Fase 6. Plat nomor dan OCR

### T16: Dataset dan detector plat

- [ ] **T16 selesai dengan bukti**

Siapkan frame kendaraan utuh dengan box plat/transkrip, group split dan lintasan mobil berlabel; latih detector plat terpisah dan uji checkpoint COCO untuk mobil.

**Dependensi:** T12. **Ukuran:** M.

**Kriteria:**

- [ ] Label/transkrip/sumber/lisensi/split diaudit; >= 100 plat terbaca dan >= 20 lintasan mobil independen untuk test.
- [ ] Checkpoint/label map mobil COCO, helm dan plat dibedakan; config/metrik deteksi/miss tersimpan.
- [ ] Reload dan crop benar pada foto/video independen dari training.

**Verifikasi:** Audit label/transkrip/group, training/evaluasi nyata, inspect FP/miss dan reload.

**File usulan:** industrial_ai/training/prepare_plates.py; training/train_plates.py; data/plates/manifest.json; models/plates/manifest.json; reports/plates_detection.json.

### T17: OCR dan lintasan kendaraan

- [ ] **T17 selesai dengan bukti**

Track/hitung mobil, pilih snapshot kendaraan utuh, asosiasikan crop plat dari frame sumber dan baca OCR; simpan provenance serta lintasan temporal.

**Dependensi:** T16; T14 untuk live. **Ukuran:** M.

**Kriteria:**

- [ ] Gate exact full-string end-to-end lulus; miss detector termasuk gagal.
- [ ] Snapshot kendaraan utuh dan crop plat/frame sumber terkait tersimpan; konflik asosiasi/OCR ditandai, huruf/digit ambigu tidak diganti diam-diam.
- [ ] Counting mobil lulus dan tidak per-frame; kendaraan tanpa plat terbaca tetap dihitung; plat sama tidak otomatis menggabungkan kendaraan.

**Verifikasi:** Uji 100 contoh bertranskrip dan video kendaraan; nilai per cahaya/sudut, unknown dan executable OCR hilang.

**File usulan:** industrial_ai/app/plates.py; app/storage.py; tests/test_plates.py; reports/plates_ocr_eval.json.

### T18: Riwayat dan query plat

- [ ] **T18 selesai dengan bukti**

Tambahkan halaman kendaraan dengan foto utuh dan panel zoom plat; chatbot menjawab plat dan jumlah mobil lewat per arah/rentang/sumber.

**Dependensi:** T17, T09. **Ukuran:** M.

**Kriteria:**

- [ ] Query plat/waktu/source tervalidasi dan cocok DB; pembacaan samar dapat ditinjau.
- [ ] UI memuat foto kendaraan utuh, crop/zoom plat, OCR/waktu/status; zoom tidak mengklaim memulihkan teks yang tidak terekam atau identitas pemilik.
- [ ] S07-S08 lulus dari input ke jawaban bersumber; live diuji setelah fase 5.

**Verifikasi:** Browser/API untuk cocok/tidak ada/ambigu/tanggal batas/follow-up; buka bukti yang dirujuk.

**File usulan:** industrial_ai/app/tools.py; app/main.py; templates/plates.html; tests/test_plate_tools.py; reports/phase_6.md.

### Gate fase 6

- [ ] Pembacaan plat/counting mobil/asosiasi bukti lulus; foto kendaraan/crop dan jumlah/plat dapat ditanya lewat UI/chatbot.
- [ ] Semua task fase selesai dan reports/phase_6.md memuat command/exit code/output/versi/kekurangan.

## Fase 7. Absensi QR

### T19: Registry peserta dan shift

- [ ] **T19 selesai dengan bukti**

Daftarkan peserta berizin, roster/shift, token QR unik dan check-in/out dengan constraint/audit.

**Dependensi:** T12. **Ukuran:** M.

**Kriteria:**

- [ ] Identitas dari registry; token tidak dikenal/dicabut ditolak; data peserta minimal.
- [ ] Duplicate scan/retry tidak menambah transaksi ganda; shift tengah malam memakai Asia/Jakarta.
- [ ] Koreksi mencatat sebelum/sesudah; belum check-in dihitung dari roster shift.

**Verifikasi:** Roster rujukan, token salah/dicabut, duplicate/retry, check-in/out dan batas tanggal; periksa constraint DB.

**File usulan:** industrial_ai/app/attendance.py; app/storage.py; tests/test_attendance.py; reports/attendance_rules.md.

### T20: Scan QR dan query absensi

- [ ] **T20 selesai dengan bukti**

Hubungkan QR ke transaksi, UI peserta dan query chatbot; gunakan decoder yang tersedia bila memenuhi kebutuhan.

**Dependensi:** T19, T09; T13 jika webcam. **Ukuran:** M.

**Kriteria:**

- [ ] Scan QR nyata mencatat peserta tepat; decode/token gagal memberi pesan jelas.
- [ ] S09-S10/koreksi cocok roster/query; ID tracker tidak menjadi identitas absensi.
- [ ] UI/doc menjelaskan batas QR dapat disalin, scope demo dan waktu pembaruan.

**Verifikasi:** Demo scan peserta/token tidak sah, belum check-in per shift, duplicate scan dan koreksi.

**File usulan:** industrial_ai/app/main.py; app/tools.py; templates/attendance.html; tests/test_attendance_tools.py; reports/phase_7.md.

### Gate fase 7

- [ ] Registry/scan/shift/audit/query benar dan batas QR dinyatakan.
- [ ] Semua task fase selesai dan reports/phase_7.md memuat command/exit code/output/versi/kekurangan.

## Fase 8. Portofolio final

### T21: Backup dan restore yang diuji

- [ ] **T21 selesai dengan bukti**

Backup SQLite/bukti/manifest model; restore ke folder baru dalam workspace tanpa menimpa hasil.

**Dependensi:** T15, T18, T20. **Ukuran:** S.

**Kriteria:**

- [ ] Backup konsisten mencakup DB, rujukan bukti dan model; tidak memuat credential/cache pribadi.
- [ ] Restore dapat membuka bukti dan query dengan jumlah yang sama setelah restart.
- [ ] Hasil asli tetap ada; source/hasil dan ZIP N-gram lama berhash sama.

**Verifikasi:** Backup/restore nyata, cocokkan jumlah/hash, lalu smoke query/bukti dari direktori restore.

**File usulan:** industrial_ai/app/backup.py; tests/test_backup.py; reports/restore_check.json.

### T22: Evaluasi akhir dan data/model cards

- [ ] **T22 selesai dengan bukti**

Uji konfigurasi final dan tulis kualitas, performa, sumber/lisensi serta batas penggunaan.

**Dependensi:** T21. **Ukuran:** M.

**Kriteria:**

- [ ] S01-S12/semua gate wajib lulus; denominator/perangkat/versi/fallback terlapor.
- [ ] Cards memuat tujuan/sumber/lisensi/split/preprocessing/hash/keterbatasan.
- [ ] Setiap klaim didukung output/log; gate yang gagal tetap belum selesai.

**Verifikasi:** Test fokus/integrasi, lint, type-check, build Python relevan dan browser flow; cocokkan laporan dengan output aktual.

**File usulan:** industrial_ai/reports/EVALUASI.md; reports/MODEL_CARD.md; reports/DATA_CARD.md; reports/final_metrics.json.

### T23: Instalasi bersih dan paket demo

- [ ] **T23 selesai dengan bukti**

Buat runbook, paket portofolio terpisah dan demo run nyata; verifikasi dari folder uji bersih.

**Dependensi:** T22. **Ukuran:** M.

**Kriteria:**

- [x] Command setup/start/test/evaluate aktual dapat diikuti; model besar tersedia melalui manifest/lokasi yang sah.
- [ ] Demo nyata menunjukkan upload/live/chat/bukti/plat/QR tanpa angka rekaan sebagai hasil.
- [x] Paket mengecualikan secret/.venv/cache/data tak boleh dibagikan; ZIP N-gram tidak ditimpa.

**Verifikasi:** Ekstrak ke folder baru dalam workspace, ikuti runbook sampai S01-S12, rekam command/exit code dan audit isi arsip.

**File usulan:** industrial_ai/README.md; reports/REPRODUKSI.md; reports/DEMO.md; reports/package_manifest.json.

### Gate fase 8

- [ ] Portofolio dapat dipasang ulang dan didemokan dengan bukti dari perangkat yang diuji.
- [ ] Semua task fase selesai dan reports/phase_8.md memuat command/exit code/output/versi/kekurangan.

## Bukti akhir yang wajib tersedia

- [ ] Reports fase 1-8 dan evaluasi akhir berasal dari run nyata.
- [ ] Model helm/plat reload; adapter chatbot hasil training benar-benar dipakai aplikasi.
- [ ] Database/bukti bertahan setelah restart; restore ke direktori baru berhasil.
- [ ] Setup bersih, test, lint, type-check, build relevan dan uji browser dijalankan.
- [ ] Demo/batas penggunaan tersedia; seluruh target usulan dibedakan dari hasil aktual.
- [x] Paket terpisah; hasil dan ZIP N-gram tetap utuh.

## Eksekusi berikutnya

Lanjutkan dari hasil demo di README dan industrial_ai/reports/VERIFIKASI_PUBLIK.md; baca plan.md
bagian 6-7 sebelum memperluas dataset/training. Tulis command aktual
setelah config/file dibuat. Jangan mengeksekusi seluruh roadmap sebagai satu script
besar; verifikasi task/gate setiap fase. Jika data/perangkat menghambat satu gate,
catat bukti kendalanya dan kerjakan bagian independen; gate tersebut tetap terbuka.

## Pengembangan opsional setelah portofolio

Identifikasi wajah sudah dicatat sebagai arah pengembangan pengguna di plan.md
bagian 16. Bukan task atau gate wajib fase 1-8 saat ini. Sebelum implementasi,
susun task khusus enrollment peserta berizin, kualitas wajah, matching dengan
ambang tervalidasi, unknown, false match/rejection, data wajah dan liveness bila
akan dipakai untuk absensi. Track ID sementara tidak menjadi employee ID otomatis.

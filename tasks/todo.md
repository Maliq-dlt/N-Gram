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

## Perbaikan berikutnya pada demo

- [ ] Ukur tracking kerumunan dengan video independen: ID switch/IDF1 dan error hitungan.
  Occlusion/objek berdekatan masih dapat menyebabkan kotak hilang atau ID tertukar.
- [ ] Perluas dataset helm/APD dan ukur FP/FN pada data yang tidak dipakai training.
- [ ] Uji setup dari clone kosong, termasuk unduhan semua model; publikasi baru
  menguji setup library dan inferensi memakai bobot lokal yang sudah tersedia.
- [ ] Tinjau label publik objek/helm, lalu evaluasi kandidat pada sumber terpisah.
  [Pipeline dan sumber data](video_training_pipeline.md); auto-label tetap draft.
- [ ] Tambahkan audit revisi serta uji backup/restore ke direktori baru.
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

# Changelog

## 2026-10-09

- Editor anotasi layar penuh dengan sidebar label/warna/edit/hapus; kotak dan
  posisi video tetap sama saat masuk/keluar.
- Tracking koreksi tersimpan lintas restart; ekspor MP4 H264/audio per revisi
  memakai kotak manual/tracker dan mempertahankan hasil AI awal.
- CLI video panjang: segmentasi tervalidasi, seleksi pHash/jarak waktu dan
  auto-label batch objek/helm dengan Auto RTX/CPU. Label tetap draft untuk review.
- Split training mengikuti sumber asli serta posisi global antarsegmen;
  metadata asal dipertahankan ketika analisis ulang.

## 0.1.0 — 2026-10-08

- Publikasi awal Video Insight Lokal: upload video, deteksi/tracking, counting,
  bukti, chatbot lokal, tema terang/gelap dan koreksi manual.
- Koreksi yang disahkan dipakai dashboard/chat/ekspor; preview memakai penuntun
  detector dan optical flow tanpa melatih ulang model saat play/simpan/query.
- Setup Python dan unduh model melalui `npm run setup`; bobot/data tetap lokal.
- Fine-tuning detector/chat tersedia sebagai proses terpisah, belum tervalidasi
  untuk keputusan keselamatan atau identitas di pabrik.

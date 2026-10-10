# Changelog

## 2026-10-10

- Login dan dashboard dirapikan mengikuti referensi 21st.dev; logo Split V,
  tema ProMotor Wow dan terang lembut, toggle tema di samping avatar.
- Orb chat serta loading kerumunan mengikuti request/pemuatan nyata, mendukung
  reduced motion dan membatalkan callback animasi yang sudah kedaluwarsa.
- Nama tampilan/foto profil disimpan privat per akun di SQLite; foto dibatasi,
  didekode dan dinormalisasi tanpa metadata. Meter password aksesibel.
- Tidak ada kredensial tertanam, signup/SSO contoh, feed CCTV contoh, atau
  klaim operasional yang tidak dibuktikan. Data/video dan kontrol anotasi tetap.
- CI menambahkan regression profil serta lifecycle animasi; distribusi memuat
  logo dan ilustrasi lokal dengan atribusi.

## 2026-10-09

- Profil inline menampilkan identitas akun/workspace nyata secara readonly.
  Ganti password merotasi cookie/CSRF, mencabut seluruh sesi lama dan mempertahankan
  video/anotasi; password memakai hash scrypt, bukan enkripsi.
- Avatar/pengelompokan aksi akun mengadaptasi Origin UI dropdown-menu #393;
  mode hasil mengadaptasi segmented-control #23552 ke radio native tanpa runtime React/Radix/Motion.
- Fondasi akses: login tanpa password default, admin/reviewer/viewer, isolasi
  workspace, cookie server/CSRF, pembatasan permintaan dan audit HMAC.
- Metadata SQLite dengan migrasi idempotent; JSON menjadi snapshot kompatibel,
  dan video/model lama tetap tersedia. Backup database serta manifest artefak.
- Auth TypeScript strict, menu akun dan viewer hanya baca; pemutar/editor native
  tetap dipertahankan. Docker CPU, Compose dengan proxy Caddy HTTPS dan CI deployment.
- Absensi wajah/enrollment/PAD didokumentasikan sebagai fase lanjutan.

- Antrean review objek/helm, approval terpisah, dan training otomatis setelah
  seluruh posisi kelompok selesai serta tersedia dua sumber asli berbeda.
- Snapshot label yang disahkan konsisten dengan fingerprint; perubahan berikutnya
  masuk run berikutnya. Parameter pilot `nbs=2` memastikan update setiap batch.
- Checkpoint baru menjalankan analisis ulang tanpa menimpa hasil sebelumnya;
  hasil mencatat model ID, SHA-256, waktu training dan metrik.
- Retry upload lengkap, pembatalan frame/batch/proses native, dan ekspor MP4
  asinkron dengan progress; followup gagal dapat dicoba ulang tanpa training ulang.
- CI untuk core beku, kualitas Python/UI, audit dependency, API/media, training
  objek/helm nyata pada CPU, serta isi wheel/sdist. Dependabot mingguan tersedia.
- Upgrade Torch/Transformers/setuptools untuk advisori dependency; setup vision-only
  mempertahankan metadata chat. README, kontribusi, keamanan dan batas lisensi dirapikan.

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

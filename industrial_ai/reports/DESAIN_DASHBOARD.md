# Dashboard video lokal — kontrak desain

8 Oktober 2026. Permintaan pengguna: dashboard langsung, UI sederhana, warna otomatis yang dapat diedit, label/nama kotak, bus, dan klik kiri/kanan untuk menggambar/membatalkan.

- Layar utama: sidebar ringkas, toolbar sumber/perangkat, perbandingan video sebagai fokus, chat di samping.
- Bukti dan anotasi punya panel sendiri. Pengaturan garis dan koordinat keyboard tidak memenuhi layar utama.
- HeroUI 3.2.6 stylesheet resmi digunakan pada HTML native (button, field, card, chip); Tailwind 4.3.0 membangun asset lokal. Alur API/model dipertahankan.
- Warna otomatis berdasar label; warna khusus adalah metadata tampilan. Status helm AI tetap ditulis jelas dan tidak berubah karena warna manual.
- Label khusus menjadi kelas dataset, nama kotak adalah keterangan. Menambah label tidak langsung melatih checkpoint.
- Klik kiri tarik atau dua titik menggambar; klik kanan/Escape membatalkan interaksi aktif, tanpa menghapus kotak tersimpan.
- Mobile: sidebar menjadi navigasi horizontal, video/chat ditumpuk, editor/form tetap dapat dijangkau. Semua tombol mempunyai nama dan fokus keyboard.
- Hindari hero/landing, angka/chart buatan, gradient dekoratif, menu fitur yang belum tersedia, dan branding sumber referensi.

Referensi ditinjau:

- [21st.dev Dashboard Sidebar, arunjdass](https://21st.dev/@arunjdass/components/dashboard-sidebar): shell/sidebar, active navigation, spacing. Source diambil untuk ditinjau; konsep diadaptasi ke HTML, demo/React/mock tidak disalin.
- [Dribbble Smart Surveillance, Dheivani Senjadipa](https://dribbble.com/shots/27187154-Smart-Surveillance-Security-Monitoring-Dashboard-with-AI-Alerts): video sebagai pusat dan panel informasi di kanan; ditinjau di browser. Tidak memakai gambar/branding sumber.
- [HeroUI standalone styles](https://heroui.com/docs/react/getting-started/design-principles): BEM CSS pada HTML native, tanpa runtime React.

Tailwind CLI 4.3.0 dipilih setelah audit dependency; watcher dinaikkan ke versi aman lewat npm audit fix. Lockfile disimpan. Metadata HeroUI styles menyatakan MIT; file LICENSE yang dibundel menyatakan Apache-2.0. Teks asli disertakan di assets/THIRD_PARTY_LICENSES.txt.

## Revisi pengguna: Apple, dark mode dan belajar dari koreksi

- Tema Sistem/Terang/Gelap tersimpan lokal; system font ala Apple, hierarki lebih jelas,
  permukaan netral, aksen biru, dialog upload dipusatkan. HeroUI tetap digunakan.
- Editor memutar/geser rekaman lalu jeda untuk anotasi; detail frame menjadi alternatif
  presisi. Klik kanan membatalkan gambar/edit aktif atau kotak terbaru yang belum disimpan.
- Helm, karung dan label baru dapat dibuat. Nama bukan identitas; custom class memerlukan training.
- Training detector memakai review lengkap, dataset snapshot, split menurut sumber video,
  Auto/CPU/GPU dan checkpoint kandidat terpisah. Hasil/model lama dipertahankan.
- Analisis ulang menjadi job baru dengan model yang dipilih; model kandidat tidak diaktifkan
  otomatis. Training bukan jaminan akurasi, dan evaluasi kecil tetap hanya pilot.

Acuan tambahan: [Apple HIG](https://developer.apple.com/design/human-interface-guidelines/dark-mode).

## Revisi alur simpan dan belajar v5 (historis)

Pengguna meminta proses belajar menyatu dengan anotasi. Panel Model & belajar
serta checklist diganti pemilihan kelompok dan Simpan & pelajari. Perubahan saat
putar/geser/tutup menjadi draft otomatis; simpan menyelesaikan koreksi dan langsung
mengaktifkan jawaban manual. Kotak AI ditampilkan sebagai saran yang dapat diedit
di atas frame tanpa border. Saat dua sumber berbeda tersedia, training detector
serta analisis ulang berjalan otomatis, dengan status dan tombol Lihat analisis baru.
Pilihan model lanjutan dipindahkan ke details; default upload tetap dipilih eksplisit.


## Alur aktif v6 - kotak langsung diikuti

Prioritas terbaru adalah koreksi → Putar & ikuti kotak pada video yang sama, tanpa
training ulang. Kotak analisis tampil saat play/pause; kotak yang dikoreksi menjadi
prompt optical flow dan mengganti kotak AI terkait. ID T1/T2 serta nama objek hilang
membantu pengguna menandai ulang. Buffer menjaga video dan overlay selaras.

Simpan koreksi menjadi aksi review eksplisit. Query tidak memulai training atau
mengesahkan hasil tracker menjadi label latihan. Belajar untuk video lain memakai
opsi details sekunder; training YOLO berjalan hanya setelah tombol Latih ditekan.
Tema, komposisi dashboard dan library HeroUI yang ada dipertahankan.


## Alur aktif v7 dan clone baru

Ringkasan mengikuti kelas yang ditemukan, waktu puncak, lintasan, dan koreksi
terbaru. Dashboard/chat/JSON memakai hitungan koreksi objek lengkap; draft tidak
masuk hitungan. Kotak manual yang cocok jelas memakai ID detector tersimpan,
sedangkan kotak lainnya mempertahankan titik visual awal. Occlusion masih dapat
menghilangkan target; tidak ada klaim identitas unik.

Clone baru mengunduh model dasar melalui setup. Label UI menyatakan LoRA opsional;
respons chat menampilkan apakah adapter lokal atau model dasar yang digunakan.

# Pipeline video panjang dan training — 9 Oktober 2026

Target pengguna: objek/kendaraan **dan** helm, demonstrasi lokal pada RTX 4060
dengan fallback CPU. Entry point CLI memakai server/dashboard/review/training
yang sudah tersedia. Tidak ada library atau bobot baru untuk pipeline ini.

| Fase | Hasil saat ini | Gate berikutnya |
| --- | --- | --- |
| 1. Ingest | Video dipotong tepat menjadi segmen ≤110 detik, 720p/10 FPS; durasi/ukuran diverifikasi sebelum upload API | Sumber asli serta lisensi disimpan lokal |
| 2. Seleksi | Kandidat tersebar sepanjang video; jarak waktu dan pHash Hamming ≤5 membuang kemiripan | Periksa kejadian kecil yang mungkin terlewat oleh pHash |
| 3. Auto-label/review | Batch empat frame, detector objek dan helm, Auto GPU/CPU; draft siap dibuka di dashboard | Pengguna memeriksa dan menyimpan masing-masing kelompok |
| 4. Training/evaluasi | Training kandidat existing memakai kelompok/split sumber asli; hasil aktif tetap dipertahankan | Jalankan setelah label benar; tambah data test independen dan ground truth tracking |
| 5. Kondisi CCTV | Video publik siang tersedia untuk pilot | Sumber malam, mask OSD dan stratifikasi belum diterapkan |

## Cara menjalankan

Jalankan `npm start` dari `industrial_ai`, kemudian dari terminal kedua:

```powershell
. .\setup_lokal.ps1
uv run --frozen python video_finetune.py data/public/videos/scaffolding-current.ogv data/public/videos/traffic.webm --group both --device auto --frames 40
```

`--group objects`, `--group helmets` dan `--device cpu` tersedia. Output selalu
di workspace; setiap run mempunyai direktori baru `data/video-prep/<id>`.
Manifest berisi job ID dan `frame_index`; detik review = `frame_index / 10`.
Job tampil sebagai nama sumber + nomor segmen dalam riwayat dashboard.

Auto-label memakai **satu** inferensi pada confidence 0,15: nilai ≥0,5 menjadi
kotak draft, nilai lebih rendah hanya menjadi `review_flags` dalam selection.json.
Ini menghindari inferensi dua kali untuk gambar yang sama. Batas confidence adalah
baseline pilot, belum hasil kalibrasi akurasi. Posisi dengan nol kotak juga perlu
ditinjau; jangan menganggap tidak ada objek karena detector tidak menemukan kotak.

Di **Anotasi manual**, buka posisi yang tercantum dalam manifest, pilih **Semua
objek** dan **Kepala & helm** secara bergantian, koreksi lalu **Simpan koreksi**.
Dataset/training hanya memakai kelompok yang telah disahkan. Jangan sahkan semua
draft otomatis. Gunakan **Latih untuk video lain**/alur training existing setelah
minimal dua sumber berbeda mempunyai review lengkap pada kelompok yang sama.

## Sumber publik

| Sumber | Pembuat/lisensi | Kegunaan dan lokasi lokal |
| --- | --- | --- |
| [Démontage d'échafaudage](https://commons.wikimedia.org/wiki/File:D%C3%A9montage_d%27%C3%A9chafaudage.ogv) | Coyau, [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) | Video pekerjaan scaffolding 9 menit 48 detik; data/public/videos/scaffolding-current.ogv |
| [Moving vehicles in Link road](https://commons.wikimedia.org/wiki/File:Moving_vehicles_in_Link_road,_Cuttack,_Odisha.webm) | Subhashish Panigrahi, CC BY-SA 3.0 | Video kendaraan 2 menit 15 detik; data/public/videos/traffic.webm |
| [Construction-PPE](https://docs.ultralytics.com/datasets/detect/construction-ppe/) | Dalvi dkk.; publisher Ultralytics, AGPL-3.0 menurut halaman dataset | 1.416 gambar dengan label YOLO dan split train/val/test; data/public/construction-ppe |

Sidecar unduhan mencatat URL, attribution, lisensi dan SHA256. Video/gambar/bobot
tidak dipush ke GitHub. Derivatif video perlu tetap menyertakan atribusi dan lisensi.
Lisensi Construction-PPE diperiksa ulang pada bagian resmi **License and Attribution**;
sitasi dataset menyebut Mrunmayee Dalvi, Niyati Singh, Sahil Bhingarde dan Ketaki
Chalke (2025), publisher Ultralytics.
Construction-PPE merupakan **gambar**, belum diimpor menjadi review job video.
Pemetaan label yang relevan: Person → person, helmet → Hardhat,
no_helmet → NO-Hardhat. Kelas APD lainnya belum ditambahkan ke detector aplikasi.

Video publik ini bukan rekaman CCTV pabrik dengan ground truth yang telah
divalidasi. Scaffolding dan lalu lintas berasal dari dua sumber berbeda, tetapi
belum menjamin kelas positif helm tersedia pada kedua split. Periksa distribusi
label sebelum training; tambahkan sumber pekerjaan lain jika helm hanya muncul
pada satu sumber. Menggabungkan segmen dari satu rekaman tidak memenuhi syarat
dua sumber independen.

## Koreksi terhadap rencana awal

- Stream copy pada batas keyframe dapat menghasilkan segmen >120 detik. CLI
  memakai pemotongan waktu dengan encoding H264 dan memeriksa durasi tiap hasil.
- Hash segmen bukan identitas sumber training. `source.json` mencatat hash asli,
  hash upload segmen dan offset waktu. Frame lokal yang sama pada segmen berbeda
  memiliki posisi global berbeda; semua segmen tetap pada satu split.
- Analisis ulang juga menyalin provenance sumber agar split tidak bocor.
- Recipe training existing dipertahankan: AdamW, lr0=0,001, freeze=10,
  seed=42, deterministic=True, workers=0; patience mengikuti jumlah epoch.
  Freeze=11/patience=20 dalam usulan belum diuji dan belum diterapkan.
- HOTA/IDF1/MOTA memerlukan anotasi track ground truth, bukan output YOLO sebagai
  pembanding dirinya sendiri. Skor MOT17 bukan target numerik CCTV proyek ini.
- Evaluasi test terpisah belum dijalankan. Dataset pilot existing memakai
  train/val per sumber; jangan memakai val yang digunakan tuning sebagai test.

## Pemeriksaan yang dapat diulang

```powershell
uv run --frozen python tests/video_finetune_check.py
uv run --frozen python tests/corrections_check.py
uv run --frozen python tests/self_check.py
uv run --frozen python tests/review_counts_check.py
npm run check
```

Pemeriksaan baru memakai video gerak terkontrol untuk segmentasi/pHash, pemisahan
sumber dan ekspor; inferensi video publik menguji alur GPU/draft. Semua itu
membuktikan pipeline berjalan, belum mengukur peningkatan akurasi model.

## Pilot yang sudah dijalankan

Pada 9 Oktober 2026 kedua video publik diproses nyata dengan `--group both`
dan `--device auto`: 6 segmen scaffolding/26 posisi dan 2 segmen lalu lintas/19
posisi, seluruh auto-label pada `cuda:0` (RTX 4060). Total 45 posisi draft;
jumlah di bawah target 40 per sumber terjadi karena dedup kemiripan. Semua
`complete`, `helmets_complete` tetap false dan `learn_groups` kosong.

Prediksi scaffolding: 45 kotak person, 23 Hardhat, 1 NO-Hardhat. Prediksi
lalu lintas: 22 car, 12 bus, 1 truck, 1 Hardhat. Ini hitungan **kotak pada
frame sampel**, bukan individu unik atau ground truth. Hardhat pada lalu
lintas khususnya perlu diperiksa. Tidak ada bobot yang dilatih dari draft ini.

Paket source/wheel berhasil dibangun; lint/format/Ty, 71 pemeriksaan E2E nyata,
31 tracking dan 27 persistensi/ekspor lulus. Audit SHA256 mempertahankan 2.342
file baseline. Bukti runtime/data tetap lokal; fase evaluasi independen belum
selesai hanya karena tes pipeline ini lulus.

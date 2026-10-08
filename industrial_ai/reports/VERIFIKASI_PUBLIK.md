# Verifikasi publik — Video Insight Lokal

Tanggal: 8 Oktober 2026. Target: demo/portofolio lokal di Windows.
Rincian penggunaan dan setup: [README](../README.md).
Checklist implementasi/roadmap: [todo.md](../../tasks/todo.md).

## Arsitektur yang berjalan

- FastAPI pada loopback 127.0.0.1:8765; HTML/JavaScript native dan CSS HeroUI/Tailwind.
- YOLO26n COCO + ByteTrack untuk person/car/bus/truck/motorcycle/bicycle;
  YOLOv8n hard-hat terpisah untuk helm. Input upload tervalidasi dan diproses berurutan.
- Dua video H264, foto bukti dengan bbox target, per-frame occupancy, track/lintasan,
  history, draft/review dan ekspor dataset tersimpan lokal.
- Query fakta deterministik; chat umum Qwen3-1.7B dengan adapter LoRA bila tersedia.
  Clone baru memakai base model; tidak ada adapter/checkpoint/video pengguna di Git.
- Review objek lengkap mengganti occupancy pada timestamp yang disahkan;
  dashboard/chat/JSON menggunakan hitungan sama. Draft/review helm tidak menaikkan
  jumlah orang. Track/lintasan analisis awal tetap utuh.
- Preview kotak manual mengikuti ID detector bila cocok jelas, atau optical flow
  tanpa reseeding ke ciri tetangga. Simpan/play/query tidak memulai fine-tuning.

## Pemeriksaan publikasi yang dijalankan

| Pemeriksaan | Hasil |
| --- | --- |
| Parser seluruh script PowerShell | Lulus |
| npm run setup -- -SkipModels | Lulus, environment Python dari uv.lock |
| npm run check | Lulus, regresi playback/buffer/stale response/koreksi overlay |
| npm run build | Lulus, CSS lokal dibangun |
| npm audit --audit-level=high | 0 vulnerabilities |
| tests/self_check.py | Lulus, counting/query/batas input/dataset/perangkat/OOM |
| tests/review_counts_check.py | Lulus, koreksi lengkap/draft/API/chat/JSON |
| tests/tracking_check.py | 31 pemeriksaan lulus, termasuk cuplikan nyata |
| tests/e2e.py | 71 pemeriksaan HTTP/video/chat nyata lulus |
| Ruff lint dan format | Lulus; 16 file Python sudah terformat |
| Ty type-check | Lulus |
| Inferensi Qwen dasar tanpa adapter, CPU | Lulus, mode base dan respons nyata |

Command lint/type-check/build dan persiapan input E2E tersedia di README.
Pengujian tidak melatih ulang model. Starlette/httpx TestClient mengeluarkan
warning deprecation; seluruh assert tetap lulus. Ini bukan hasil audit keamanan
menyeluruh atau benchmark akurasi detector.

E2E memakai 12 detik cuplikan OpenCV, 120 frame: inferensi CPU selesai 8,75 detik;
Qwen+adapter menghasilkan jawaban pada CPU dan Auto menggunakan RTX 4060 Laptop.
Durasi itu satu smoke run, bukan perbandingan CPU/GPU yang terkontrol.
Kotak fixture menguji transformasi API/dataset, bukan label ground truth.
Uji base tanpa adapter memakai bobot lokal yang sudah tersedia; tidak ada download
ulang seluruh model ke environment kosong dalam verifikasi publikasi ini.

## Bukti pengembangan sebelumnya

Uji browser v7 memverifikasi simpan koreksi menaikkan puncak dan ringkasan tanpa
mengganti src/posisi pemutar; query AI asli mempertahankan hitungan awal. Klik kanan,
play/pause, mobile 320/768px dan overlay selaras telah diuji pada revisi terkait.
Publikasi mengubah setup/dokumentasi/label LoRA opsional dan assertion E2E;
logika inferensi serta koreksi hitungan tetap sama.

Koreksi nyata pada satu posisi video kerumunan mengubah AI 4 menjadi review 5 orang.
Puncak tetap 11 karena koreksi itu tidak melampaui puncak sebelumnya. Posisi draft
lain tidak otomatis disahkan. Empat potongan kerumunan diuji untuk runtime/survival;
hasil itu belum mengukur IDF1, ID switch atau kualitas identitas.

Training pilot chat benar-benar menghasilkan adapter; 32 dialog train dan enam
eval belum membuktikan kemampuan percakapan umum. Pilot detector CPU/GPU dan
penambahan kelas menghasilkan checkpoint; mAP pilot kelas tambahan 0, sehingga
keberhasilan pipeline training tidak sama dengan model yang siap dipakai.
Laporan historis/screenshots tetap lokal untuk menghindari publikasi footage pengguna.

## Batas hasil

Kerumunan/occlusion/objek kecil dapat membuat target hilang atau ID tertukar.
Kotak tanpa penuntun detector berukuran tetap; preview gerak belum menjadi
koreksi seluruh video, MP4 baru atau lintasan persisten sesudah restart.
Belum ada ground truth independen, audit revisi lengkap, restore teruji, CCTV
langsung, OCR plat, identifikasi wajah atau absensi. Versi ini layak sebagai demo;
kesiapan pabrik memerlukan dataset/evaluasi tersendiri.

## Audit paket dan preservasi

Build wheel/sdist lulus. Audit memeriksa kesamaan 12 file source/UI/lisensi
pada wheel; sdist berisi 40 file dengan hanya tiga dokumen publik di reports.
Video, screenshot, hasil runtime, model, cache, environment dan credential
terdeteksi tidak ikut paket/source yang dipilih. Tautan relatif dokumen Git
sesuai 36 berkas staged. File LICENSE pihak ketiga asli disertakan.

SHA256 1.583 berkas hasil/job/model/dataset/artefak akademik lama tetap identik.
Satu dokumen desain sengaja diperbarui; versi aslinya disimpan lokal. Data baru
hanya berasal dari test; laporan historis tidak ditimpa. Hasil akademik dan ZIP
lama dipertahankan.

# Repo GitHub dan keputusan penggunaan ulang

Tinjauan README publik pada 8 Oktober 2026. Repo pembanding tidak dijalankan;
fitur yang tertulis bukan bukti bahwa akurasinya lebih baik.

| Repo | Kedekatan konsep | Kecocokan dengan prototipe ini | Keputusan |
| --- | --- | --- | --- |
| [Agentic-Vision-System](https://github.com/Faizanras00l/Agentic-Vision-System) | YOLO, percakapan dan video | README memakai OpenRouter/ngrok, BLIP/DeepFace dan notebook; tidak memenuhi chat fine-tuned yang sepenuhnya lokal | Referensi konsep; tidak diinstal |
| [video_analysis_project](https://github.com/sachnaror/video_analysis_project) | Upload video dan chat hasil | Django/Celery/Redis/Postgres serta OpenAI API/Whisper/OCR; penambahan stack besar untuk kebutuhan awal | Referensi alur; tidak diinstal |
| [Label Studio](https://github.com/HumanSignal/label-studio) | Anotasi gambar/video, label dan ekspor dataset | Metode human review → label tersimpan → ekspor → training kandidat sesuai kebutuhan koreksi pengguna | Metode dipakai; editor SVG/form native cukup, server Label Studio tidak ditambah |
| [supervision](https://github.com/roboflow/supervision) | Anotasi, line/zone counting, utilitas dataset | Dapat membantu jika nanti membutuhkan polygon zone/trajectory; counting dasar dan kotak sudah tersedia sekarang | Belum ditambah karena fungsi saat ini sudah terpenuhi |
| [ultralytics](https://github.com/ultralytics/ultralytics) | Deteksi dan tracking | Sudah digunakan lewat dependency terkunci: YOLO26n + ByteTrack | Dipakai pada aplikasi lokal |
| [transformers](https://github.com/huggingface/transformers) / [peft](https://github.com/huggingface/peft) | Model kecil dan LoRA | Sudah digunakan untuk Qwen3-1.7B dan adapter yang benar-benar dilatih | Dipakai pada aplikasi lokal |

## Keputusan

Pertahankan aplikasi `industrial_ai` yang sudah diuji. Tidak perlu clone aplikasi
lain untuk menduplikasi upload, perbandingan video, history, counting, atau chat.
Library upstream telah diinstal di `.venv` melalui `uv.lock`; kode detector,
tracker, tokenizer dan LoRA tidak dibuat ulang dari nol.

Fokus pengembangan berikutnya: data APD berlabel dan evaluasi detector, kemudian
polish UI pada alur yang sudah ada. `supervision` baru relevan ketika fungsi zone
atau trajectory diperlukan dan kompleksitas native mulai meningkat. UI repo lain
belum dievaluasi langsung di browser sehingga tidak diklaim lebih baik.

Tidak ada source repo pembanding yang disalin, token/API key dibuat, layanan
cloud diaktifkan, atau dependency tambahan dipasang untuk tinjauan ini.
Ketentuan library/model yang aktif tercatat di [README](../README.md#sumber-dan-lisensi).


## Koreksi manual

README Label Studio ditinjau untuk alur labeling dan ekspor; tidak ada kode yang
disalin. Editor native pada aplikasi ini memberi bounding box, kelas, review
kelompok, revisi konflik, serta ZIP YOLO dengan provenance. Ini persiapan data
fine-tuning, tidak mengklaim model langsung belajar setelah pengguna menggambar.
Package CUDA Torch/torchvision diperbarui dari index resmi PyTorch karena wheel
CPU sebelumnya tidak dapat memakai RTX; versi tersimpan dalam `uv.lock`.

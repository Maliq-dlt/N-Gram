# Verification

`checks.json` mencatat output command yang benar-benar dijalankan. `core_manifest.json` memuat SHA-256 snapshot core setelah gerbang Fase 1; snapshot identik setelah ekstensi selesai.

46 test pytest lulus; notebook Run All 18 sel dari kernel baru lulus; lint, format, type-check, build wheel/sdist dan CLI smoke lulus. Wheel diimpor dari `.tmp/wheel-site`, checkpoint mini round-trip dan sampling diuji. CLI source train/evaluate/generate diuji Brown penuh.

Scope: folder awal kosong, hanya deliverable diminta ditambahkan; cache/temp/build/corpus download git-ignored. Graph struktural diperbarui tanpa parse error; heuristik gap bukan bukti coverage.

Batas: GUI notebook manual, external OS/runtime, neural model dan evaluasi manusia belum diuji. Hasil eksperimen/tuning dicatat terpisah dalam `extensions/results`.

## Pengumpulan setelah perapihan

48 test, lint, format, type-check, build terbaru, dan Run All 18 sel pada salinan bersih lulus. `perapihan.json` memetakan nama/lokasi hasil dan checksum; `pengumpulan.json` mencatat gerbang setelah perapihan. Semua hasil lama tetap identik.

Pembersihan fisik cache/temporary di folder kerja ditolak kebijakan otomatis, sehingga belum dilakukan. ZIP mengecualikan seluruh cache/virtualenv/metadata tool/script sementara dan hanya memuat file pengumpulan. Brown ZIP asli disertakan; directory ekstraksinya tidak dimasukkan karena identik.

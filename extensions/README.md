# Expert Extension

Semua perubahan terpisah dari core. Urutan reproduksi dan CLI: [README root](../README.md). Tabel dan interpretasi kritis: [LAPORAN.md](../LAPORAN.md).

2.1: add-k, linear interpolation, Stupid Backoff, interpolated absolute-discount Kneser–Ney; tune dev.
2.2: 120 konfigurasi, tiga seed, threshold 2/3, n=1..4; pilot test scores dipakai ulang.
2.3: total/mean NLL token dan n-gram; PP bucket panjang; 200 generasi/model, distinct/repetition/UNK/cap.
2.4: Counter ID keys vs sorted uint32 count arrays; ukuran indeks dan waktu lookup, bukan seluruh RSS.
2.5: NLTK bigram/trigram, 1.000 kalimat train, 2.000 query/orde, same vocabulary/padding/discount.
2.6: pyproject, CLI train/evaluate/generate, safe YAML, validated JSON-gzip checkpoints.

Hasil nyata: `results/`. Test: `uv run pytest extensions/tests -q` dari root setelah `. ./setup_lokal.ps1`.
Stupid Backoff tidak memiliki PP; score loss tersedia pada CSV. Threshold berbeda memiliki target vocabulary berbeda. Tidak ada neural/human evaluation.

# Ringkasan Fase 1

Brown: 57,340 kalimat raw, 1,161,192 token raw. Setelah filter: 56,766 kalimat; 574 kosong dibuang.
Split seed 42: 45,412 train / 11,354 test. V=22,356; UNK train=14,533.
OOV test raw=1.8720%; setelah threshold=3.2408%; setelah mapping=0.0000%.

| Model | Perplexity | N target |
|---|---:|---:|
| Bigram MLE | inf | 208,096 |
| Unigram Laplace | 845.846 | 208,096 |
| Bigram Laplace | 2633.39 | 208,096 |
| Trigram Laplace | 10977.9 | 208,096 |

Unseen bigram test=26.6992% (kemunculan). Produk kalimat panjang=0.0; log P=-9826.71 finite.

Normalisasi semua konteks teramati lulus dengan toleransi 1e-9; konteks tak terlihat uniform. Test unit lulus (lihat metrics.json).

Keterbatasan: satu seed, random split kalimat, kemungkinan kalimat identik/tema dokumen tumpang tindih. Tidak diuji: lintas corpus/bahasa, semantic coherence, penilaian manusia. Vocabulary/PP tidak bisa langsung dibandingkan dengan tokenisasi lain. Trigram add-one dapat memburuk karena sparse context dan pembagian massa ke seluruh V.

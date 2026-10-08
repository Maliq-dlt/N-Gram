# Bukti 16 langkah N-gram

Seluruh pemeriksaan dihasilkan oleh Run All demonstrasi_ngram.ipynb. Nomor sel kode utama adalah urutan sel kode, dimulai dari 1; sel kode 1 adalah bootstrap.

| Langkah | Topik | Status | Bukti |
|---|---|---|---|
| 1 | Load corpus | LULUS | Corpus dan hash |
| 2 | Explore corpus | LULUS | Statistik/top-20/histogram/Zipf utama |
| 3 | Preprocessing | LULUS | Contoh preprocessing utama |
| 4 | Split | LULUS | Indeks split identik |
| 5 | Boundary | LULUS | Padding model dan corpus mini |
| 6 | Unknown words | LULUS | contoh_unk.csv |
| 7 | Generate n-grams | LULUS | Contoh n-gram utama dan assert |
| 8 | Count n-grams | LULUS | Counter event train |
| 9 | MLE | LULUS | perhitungan_token.csv |
| 10 | Next-word prediction | LULUS | prediksi_perbandingan.csv |
| 11 | Sentence probability | LULUS | perhitungan_kalimat.csv |
| 12 | Log probability | LULUS | underflow_token.csv |
| 13 | Zero frequency | LULUS | Unseen rate dan count nol |
| 14 | Laplace | LULUS | Normalisasi penuh dan numerator/denominator |
| 15 | Perplexity | LULUS | perplexity_verifikasi.csv |
| 16 | Text generation | LULUS | generasi_perbandingan.csv dan generasi_token.csv |

Semua file core dan 157 hasil lama tetap SHA-256-identik. Partisi/vocabulary tidak diubah. Koherensi semantik, split dokumen dan generalisasi lintas corpus tidak diuji.

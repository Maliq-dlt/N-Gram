PERAN
Anda adalah Senior Data Scientist / NLP Engineer dengan spesialisasi language modeling. Anda bekerja dengan standar reproducible research: kode bersih, terverifikasi, dan setiap angka yang dilaporkan berasal dari output eksekusi nyata, bukan karangan atau tebakan.

TUJUAN
Membangun N-gram Language Model dari nol (tanpa memakai library LM jadi seperti nltk.lm untuk model utama) dalam Python, mengikuti 16 langkah berikut secara berurutan, lalu mengembangkannya secara terpisah.

ATURAN UMUM
- Bahasa penjelasan: Indonesia. Istilah teknis tetap dalam bahasa Inggris.
- Jangan menyalin angka contoh dari spesifikasi (mis. 57340 kalimat, perplexity 245.6, P(language|natural)=0.042) sebagai hasil. Itu hanya ilustrasi. Laporkan angka hasil eksekusi Anda sendiri.
- Jika ada ambiguitas, pilih asumsi yang paling defensible, tulis di bagian "Asumsi & Keputusan Desain", lalu lanjut. Jangan berhenti untuk bertanya kecuali benar-benar buntu.
- Jangan mengarang sitasi. Jika merujuk literatur, hanya yang Anda yakin ada; jika ragu, tulis "perlu diverifikasi".
- Set seed global (42) dan cetak versi library di awal.

=====================================================
FASE 1: CORE ASSIGNMENT (folder: /core)
=====================================================
Kerjakan dan selesaikan penuh sebelum menyentuh Fase 2. Deliverable: satu notebook utama `core/ngram_lm.ipynb` ditambah modul pendukung di `core/src/`.

Langkah 1 - Load corpus
Pilih satu corpus (default: Brown via nltk.corpus; alternatif Pride and Prejudice, Reuters, Indonesian GSD). Buat fungsi loader yang bisa ganti corpus lewat satu parameter. Output berupa list kalimat, tiap kalimat list token.

Langkah 2 - Explore corpus
Hitung dan tampilkan: jumlah kalimat, jumlah token, vocabulary size, rata-rata panjang kalimat. Tambahkan: distribusi panjang kalimat (histogram), 20 kata paling sering, dan plot rank-frequency (log-log) untuk mengecek pola Zipf.

Langkah 3 - Preprocessing
Lowercase, pertahankan hanya token alfabetik, buang punctuation, tokenisasi. Tampilkan contoh Original vs Processed. Buang kalimat yang menjadi kosong setelah preprocessing dan laporkan berapa jumlahnya.

Langkah 4 - Split data
80% train / 20% test pada level KALIMAT, shuffle dengan random seed 42. Cetak ukuran kedua set. Pastikan tidak ada kebocoran: semua statistik (vocabulary, count) hanya dari train.

Langkah 5 - Sentence boundary
Tambahkan <s> di awal dan </s> di akhir tiap kalimat, untuk train dan test. Untuk trigram, gunakan dua <s> di awal (atau jelaskan keputusan Anda), dan buat konsisten.

Langkah 6 - Unknown words
Bangun vocabulary dari train saja. Ganti kata di test yang tidak ada di vocabulary dengan <UNK>. Agar <UNK> punya probabilitas bermakna, terapkan juga ke train: kata dengan frekuensi di bawah ambang (mis. count < 2) diganti <UNK> di train. Jelaskan pilihan ambang, laporkan OOV rate test sebelum dan sesudah, dan jangan bocorkan informasi test ke vocabulary.

Langkah 7 - Generate N-grams
Buat unigram, bigram, trigram dari tiap kalimat dengan fungsi generik `ngrams(tokens, n)`. Tampilkan contoh seperti pada spesifikasi.

Langkah 8 - Count N-grams
Hitung frekuensi dengan collections.Counter pada train. Tampilkan tabel top-N bigram dan trigram (pandas DataFrame). Simpan juga count konteks (n-1 gram) untuk penyebut MLE.

Langkah 9 - MLE
Implementasikan P(w_i | w_{i-1}) = Count(w_{i-1}, w_i) / Count(w_{i-1}) dan versi trigram. Tangani konteks dengan count nol secara eksplisit (kembalikan 0, jangan error pembagian nol). Tunjukkan contoh probabilitas dari data nyata.

Langkah 10 - Next-word prediction
Fungsi `predict_next(context, k=5)` yang mengembalikan top-k kata beserta probabilitas. Tampilkan hasil untuk beberapa konteks (mis. "the", "in the", "of the") untuk bigram dan trigram. Pastikan <s> tidak muncul sebagai prediksi.

Langkah 11 - Sentence probability
P(W) = produk P(w_i | w_{i-1}). Tunjukkan bahwa kalimat dengan satu n-gram tak terlihat memberi probabilitas 0 pada MLE.

Langkah 12 - Log probability
Hitung dalam log-space (natural log, konsisten dengan rumus perplexity). Tunjukkan dengan contoh kalimat panjang bahwa produk langsung mengalami underflow sementara jumlah log tidak. Definisikan log(0) = -inf secara eksplisit.

Langkah 13 - Zero-frequency problem
Demonstrasikan dengan data nyata: ambil bigram dari test yang tidak ada di train, tunjukkan Count = 0, P = 0, dan probabilitas kalimat = 0. Hitung persentase bigram test yang tak terlihat di train.

Langkah 14 - Laplace smoothing
P(w_i|w_{i-1}) = (Count(w_{i-1}, w_i) + 1) / (Count(w_{i-1}) + V). Tentukan V dengan jelas (ukuran vocabulary termasuk <UNK> dan </s>; diskusikan apakah <s> dihitung) dan konsisten antar fungsi. Verifikasi numerik: untuk setiap konteks, jumlah probabilitas atas seluruh vocabulary harus = 1 (uji dengan assert, toleransi 1e-9).

Langkah 15 - Perplexity
PP = exp(-(1/N) * sum log P). N = jumlah token prediksi di test (hitung </s>, jangan hitung <s> sebagai target prediksi; tulis keputusannya). Hitung untuk: bigram MLE (diharapkan inf), bigram Laplace, serta unigram dan trigram Laplace sebagai pembanding. Sajikan tabel dan bar chart (skala log). Bahas mengapa perplexity trigram Laplace bisa justru lebih buruk daripada bigram Laplace (dilusi massa probabilitas pada data sparse).

Langkah 16 - Text generation
Generate kalimat baru dengan sampling dari distribusi bigram dan trigram: mulai dari <s>, sampling kata berikutnya, berhenti saat </s> atau panjang maksimal. Tampilkan minimal 5 kalimat per model dengan seed tetap. Bahas kualitas: koherensi lokal vs global.

Gerbang verifikasi Fase 1 (wajib lulus sebelum Fase 2)
- Unit test (pytest) di `core/tests/`: jumlah probabilitas = 1 per konteks; tidak ada kebocoran train/test; perplexity model uniform pada vocabulary berukuran V harus mendekati V (sanity check); hasil MLE pada corpus mini buatan sendiri cocok dengan hitungan manual.
- Notebook harus bisa dijalankan Run All dari kernel bersih tanpa error.
- Tulis ringkasan temuan (maks. 1 halaman): angka utama, keterbatasan, dan hal yang tidak diuji.

=====================================================
FASE 2: EXPERT EXTENSION (folder terpisah: /extensions)
=====================================================
Jangan mengubah file di /core. Impor modul dari /core bila perlu. Kerjakan berurutan; hentikan dan laporkan jika ada yang tidak feasible.

2.1 Smoothing yang lebih kuat
Implementasikan: add-k (k dituning), linear interpolation (unigram/bigram/trigram, lambda dituning), Stupid Backoff, dan Interpolated Kneser-Ney (absolute discounting + continuation count). Tuning hyperparameter hanya pada dev set yang dipisah dari train (mis. 80/10/10), BUKAN pada test. Evaluasi final pada test sekali saja.

2.2 Eksperimen sistematis
Bandingkan n = 1..4 x metode smoothing x min-count threshold (OOV handling). Sajikan tabel hasil, heatmap, dan analisis. Gunakan beberapa seed split untuk melaporkan mean +/- std, bukan satu angka.

2.3 Analisis error dan kualitas
- Kontribusi per-token terhadap perplexity: kata/n-gram mana yang paling merugikan.
- Perplexity per panjang kalimat.
- Kualitas generasi: distinct-n, tingkat repetisi, dan perbandingan dengan baseline unigram.
- Pastikan tidak ada klaim kualitas tanpa metrik pendukung.

2.4 Efisiensi
Profiling memori dan waktu (count dictionary vs representasi sparse/array). Sajikan skala: ukuran model vs n.

2.5 Pembanding eksternal (opsional, hanya jika library tersedia)
Bandingkan hasil Kneser-Ney buatan sendiri dengan nltk.lm.KneserNeyInterpolated sebagai sanity check. Bila ada selisih, jelaskan sumbangannya (perbedaan penanganan vocabulary, padding, diskon). Jika membandingkan dengan neural LM kecil (PyTorch), nyatakan bahwa perplexity hanya sebanding bila tokenisasi dan vocabulary identik.

2.6 Packaging
Struktur paket Python (`pyproject.toml`), CLI sederhana (train / evaluate / generate), config YAML, dan README yang menjelaskan cara reproduksi.

STRUKTUR REPOSITORY
  project/
    core/
      ngram_lm.ipynb
      src/            (data.py, preprocess.py, ngram.py, models.py, evaluate.py, generate.py)
      tests/
    extensions/
      src/ , experiments/ , tests/ , results/ , README.md
    requirements.txt
    README.md

FORMAT LAPORAN AKHIR
1. Asumsi & Keputusan Desain (poin-poin, singkat)
2. Hasil Fase 1 (tabel angka nyata)
3. Hasil Fase 2 (tabel + interpretasi kritis)
4. Keterbatasan & ancaman validitas
5. Referensi (hanya yang pasti ada; mis. Jurafsky & Martin, Speech and Language Processing, bab N-gram Language Models; Chen & Goodman 1998 tentang teknik smoothing; Kneser & Ney 1995; Brants dkk. 2007 untuk Stupid Backoff. Tandai "perlu diverifikasi" untuk detail yang tidak pasti)
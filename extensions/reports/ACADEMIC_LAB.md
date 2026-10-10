# Academic N-gram Lab: laporan bukti, 10 Oktober 2026

Eksperimen berikut adalah pilot eksploratif berbasis dokumen. Brown dan Reuters masing-masing memakai 120 dokumen, Wikipedia Indonesia 40 artikel. Ini bukan evaluasi penuh corpus, benchmark bahasa Indonesia yang representatif, atau replikasi angka Chen–Goodman. Hasil historis tugas dasar tidak diganti.

## Estimator yang benar-benar digunakan

Untuk history `h`, `C(h)=sum_w c(hw)` dan `T(h)` adalah jumlah tipe penerus yang pernah terlihat. Witten–Bell interpolasi memakai `P(w|h)=[c(hw)+T(h)P(w|suffix(h))]/[C(h)+T(h)]`; history tanpa hitungan memakai distribusi orde lebih rendah. Basis unigram implementasi adalah `(c(w)+epsilon)/(C()+epsilon*|V|)` dengan `epsilon=1e-8`, bukan basis uniform dan bukan Witten–Bell murni tanpa regularisasi. `<s>` bukan kandidat keluaran. Persamaan interpolasi/tipe mengikuti Chen–Goodman §2.5, sedangkan pilihan basis epsilon adalah keputusan implementasi lokal.

Modified Kneser–Ney menggunakan hitungan raw pada orde tertinggi dan hitungan continuation (jumlah tipe predecessor berbeda) pada orde lebih rendah. Count-of-counts dihitung **per orde dari hitungan efektif orde tersebut**, bukan memakai histogram raw trigram untuk semua orde. Dengan `N_r` jumlah tipe yang hitungan efektifnya r:

```text
Y = N1 / (N1 + 2*N2)
D1 = 1 - 2*Y*N2/N1
D2 = 2 - 3*Y*N3/N2
D3+ = 3 - 4*Y*N4/N3
D(c) = D1 (c=1), D2 (c=2), D3+ (c>=3)
P(w|h) = max(c(hw)-D(c(hw)),0)/C(h) + gamma(h)*P(w|suffix(h))
gamma(h) = sum_{w:c(hw)>0} D(c(hw))/C(h)
```

Rumus discount diverifikasi langsung pada Chen–Goodman (1998), §3, persamaan (26), PDF halaman 20; massa interpolasi pada halaman yang sama. Jika `N1..N4` tidak semuanya positif, atau estimasi tidak finite/tidak memenuhi `0<D_r<r`, seluruh tuple orde itu beralih ke `(0.75,0.75,0.75)`. Ini fallback sparse lokal yang dicatat pada model, bukan klaim estimator tiga-discount tetap tersedia pada data sedikit. Basis KN memakai continuation unigram untuk n>1, raw unigram untuk n=1, keduanya dengan epsilon=1e-8.

Interpolasi EM memakai komponen add-k dengan k=.01, inisialisasi bobot uniform, estimasi bobot hanya pada dev, maksimum 200 iterasi dan toleransi 1e-10. Stupid Backoff menghasilkan skor tidak ternormalisasi: tidak ikut pemilihan minimum dev-loss model probabilistik, tidak diberi perplexity, dan tidak dibandingkan sebagai probabilitas.

## Protokol dan identitas hasil

Semua run memakai seed 42, min_count=2, orde 1–3 dan delapan metode (24 kombinasi). Vocabulary dipelajari dari train dan dibekukan untuk semua model dalam run; token di luar vocabulary dipetakan ke `<UNK>`. Parameter dipilih pada dev; winner adalah minimum dev loss dari model ternormalisasi dengan tie-break lexical. Perplexity memakai natural-log CE, `exp(sum NLL / jumlah target)`, termasuk EOS dan tidak memasukkan BOS sebagai target.

Split memakai kelompok dokumen/asal, exact duplicate sentence, dan kemiripan Jaccard 5-gram >=.9 (`document-exact-sentence-and-5gram-jaccard-0.9-v1`). Pengelompokan ini mengurangi leakage, tidak membuktikan bebas seluruh paraphrase. Reuters pilot berasal dari subset file berlabel `test/` corpus NLTK yang displit ulang secara lokal; angka ini bukan benchmark official train/test Reuters. Riwayat exposure corpus sebelum tugas ini tidak diketahui, sehingga test tetap eksploratif.

| Run lengkap | Train/dev/test dokumen | Dev winner | Test CE (nats) | Test PP | Baseline KN PP | Paired ΔCE [CI95] | Kelompok test |
|---|---:|---|---:|---:|---:|---|---:|
| `brown-doc-v1-20261010` | 99/10/11 | 3-modified_kneser_ney | 5.637731 | 280.825 | 285.854 | -0.017749 [-0.021057, -0.014210] | 11 |
| `reuters-doc-v1-20261010` | 94/13/13 | 3-modified_kneser_ney | 4.538618 | 93.561 | 95.272 | -0.018119 [-0.033105, -0.006889] | 12 |
| `idwiki-doc-v1-20261010` | 32/4/4 | 2-kneser_ney | 4.438089 | 84.613 | 84.613 | 0.000000 [0.000000, 0.000000] | 4 |

CI adalah paired bootstrap 1,000 resample atas kelompok independen, token-weighted CE difference (winner minus baseline). Negatif berarti CE winner lebih rendah. Interval bersyarat pada split dan model yang sudah dipilih; tidak mencakup ketidakpastian seluruh proses tuning, multiple comparisons, atau populasi bahasa. CI Wikipedia [0,0] terjadi karena winner **sama** dengan baseline bigram KN; itu bukan bukti dua estimator berbeda identik.

## Domain transfer tanpa training target

Brown→Reuters dan Reuters→Brown memakai source-dev winner, checkpoint dan vocabulary source yang tetap; tidak ada training/tuning pada target. OOV tinggi dapat menurunkan CE melalui token UNK yang lebih mudah, sehingga PP antar-vocabulary/domain tidak boleh dianggap ranking kualitas bahasa secara langsung.

| Transfer | ΔCE | CI95 kelompok terkoreksi | Target dokumen/kelompok | Mean OOV per dokumen |
|---|---:|---|---:|---:|
| Brown→Reuters | -0.030994 | [-0.035511, -0.026374] | 120/116 | 30.71% |
| Reuters→Brown | -0.009517 | [-0.010852, -0.008156] | 120/105 | 38.60% |

Runner beku awal lupa menempelkan duplicate-group ID pada target rows. `target_bootstrap.json` asli memakai 120 kelompok dan dipertahankan sebagai bukti historis; angka otoritatif di atas berasal dari receipt completed `derived/target_group_bootstrap/correction.json`. Koreksi hanya resampling loss tersimpan dengan grouping yang benar; model dan target tidak dievaluasi ulang. OOV di tabel adalah mean rate dokumen, bukan token-weighted corpus OOV.

## Autocomplete dan batas interpretasi

Pengukuran memakai 100 target pertama menurut sorted document ID, termasuk OOV; belum sampling acak representatif. Ranking tepat atas seluruh vocabulary, CPU, tanpa warmup pada hasil `autocomplete.json`. MRR penuh berbeda dengan MRR@50 yang juga disimpan. Coverage=1−OOV pada target query. Latensi berlaku pada mesin/run ini, bukan SLA browser/server.

| Run | Model | Top1/Top3/Top5 | MRR penuh | Coverage | p50/p95 ms |
|---|---|---|---:|---:|---:|
| brown | 1-kneser_ney | 0.09/0.09/0.10 | 0.1141 | 92.00% | 13.007/18.079 |
| brown | 3-kneser_ney | 0.12/0.20/0.26 | 0.1894 | 92.00% | 26.506/31.945 |
| brown | 3-modified_kneser_ney | 0.13/0.21/0.26 | 0.1945 | 92.00% | 23.987/29.030 |
| reuters | 1-kneser_ney | 0.00/0.05/0.12 | 0.0683 | 85.00% | 1.265/1.782 |
| reuters | 3-kneser_ney | 0.17/0.28/0.33 | 0.2514 | 85.00% | 2.813/3.240 |
| reuters | 3-modified_kneser_ney | 0.17/0.28/0.31 | 0.2514 | 85.00% | 2.599/3.111 |
| idwiki | 1-kneser_ney | 0.00/0.04/0.13 | 0.0443 | 72.00% | 0.975/1.491 |
| idwiki | 2-kneser_ney | 0.05/0.13/0.19 | 0.1110 | 72.00% | 1.619/2.151 |

Diagnostik frekuensi, panjang, genre, context entropy, repetisi/loop dan distinct-n adalah indikator perilaku distribusi/keragaman. Generation tidak mengukur koherensi, kebenaran fakta, kualitas bahasa manusia, ataupun keamanan operasional. Pilot Indonesia memakai artikel Wikipedia terbuka dengan provenance URL/revision/license; 4 dokumen test tidak cukup untuk klaim generalisasi bahasa Indonesia. Benchmark isolated CPU memisahkan build+tune, single-target score, dan exact top-k; peak RSS mencakup worker/import/warmup/repeats, bukan ukuran objek model. Lihat receipt benchmark jika sudah completed, jangan menggabungkan timing autocomplete tanpa warmup dengan benchmark pinned CPU.

## Benchmark CPU terkontrol yang benar-benar dijalankan

Seluruh 24 kombinasi per corpus memiliki receipt completed; tabel merangkum enam pembanding. Satu subprocess baru dijalankan serial per model, affinity CPU0, satu thread BLAS, satu warmup dan tiga repeat; 30 target source-dev identik dalam tiap corpus. Build mencakup CountBank train dan tuning dev, scoring mencakup pemetaan token/context, top-k adalah scan vocabulary penuh. Semua waktu p50/p95 dalam ms. Peak RSS dalam MiB adalah keseluruhan worker (imports, warmup, repeats), bukan incremental memory/model object. Build p95 hanya dari tiga pengulangan, sehingga estimasi tail-nya lemah.

| Corpus | Model | Build+tune p50/p95 | Score target p50/p95 | Top5 context p50/p95 | Peak RSS MiB |
|---|---|---:|---:|---:|---:|
| brown | 1-kneser_ney | 383.4353/398.8062 | 0.0034/0.0084 | 12.8453/18.5122 | 140.25 |
| brown | 2-kneser_ney | 439.1739/452.3866 | 0.0103/0.0199 | 25.7303/30.1616 | 140.52 |
| brown | 3-kneser_ney | 571.0403/673.5504 | 0.0151/0.0334 | 32.0147/43.1005 | 140.99 |
| brown | 3-witten_bell | 546.6813/559.1313 | 0.0154/0.0320 | 32.7669/44.6288 | 140.77 |
| brown | 3-modified_kneser_ney | 593.1560/1157.9921 | 0.0260/0.0695 | 36.6515/70.6913 | 169.50 |
| brown | 3-interpolation_em | 2929.3670/3014.1006 | 0.0167/0.0395 | 35.6848/50.8246 | 143.05 |
| reuters | 1-kneser_ney | 20.0970/20.3894 | 0.0016/0.0024 | 1.5175/1.9671 | 61.21 |
| reuters | 2-kneser_ney | 23.9794/24.2368 | 0.0031/0.0044 | 2.4736/2.8856 | 61.29 |
| reuters | 3-kneser_ney | 25.6916/26.2496 | 0.0039/0.0068 | 2.9624/3.4317 | 61.15 |
| reuters | 3-witten_bell | 21.7851/22.5346 | 0.0045/0.0059 | 2.7182/3.1272 | 61.45 |
| reuters | 3-modified_kneser_ney | 29.2701/29.5755 | 0.0041/0.0063 | 2.7282/3.2011 | 62.97 |
| reuters | 3-interpolation_em | 90.8792/92.3053 | 0.0040/0.0053 | 3.0866/3.5055 | 61.62 |
| idwiki | 1-kneser_ney | 11.1149/11.2060 | 0.0013/0.0019 | 0.8793/1.1188 | 58.11 |
| idwiki | 2-kneser_ney | 11.7987/11.8284 | 0.0021/0.0032 | 1.5124/1.7583 | 58.04 |
| idwiki | 3-kneser_ney | 15.5285/17.1949 | 0.0050/0.0075 | 2.1123/2.6226 | 58.12 |
| idwiki | 3-witten_bell | 11.9353/11.9882 | 0.0036/0.0050 | 1.6681/1.9734 | 58.02 |
| idwiki | 3-modified_kneser_ney | 19.0509/20.5697 | 0.0043/0.0098 | 1.7953/2.3516 | 59.01 |
| idwiki | 3-interpolation_em | 51.6329/250.4671 | 0.0041/0.0176 | 2.1726/6.9333 | 58.14 |

Brown menunjukkan tradeoff nyata: MKN test PP lebih baik (280.825 vs KN 285.854), tetapi benchmark top5 p50 lebih lambat (36.651 vs 32.015 ms), dengan peak worker RSS 169.50 vs 140.99 MiB. Jadi penurunan PP tidak membuktikan model lebih cepat atau hemat memori. Hasil autocomplete sebelumnya memakai first100 source-test target, tanpa warmup/affinity terkontrol; benchmark ini memakai 30 source-dev target. Keduanya workload berbeda dan tidak boleh digabung menjadi klaim speedup tunggal. Benchmark tidak mengevaluasi ulang held-out test.

Sumber angka: `.tmp/research-actual/scientific-summary.json`, dikompilasi dari receipt `derived/benchmark/` masing-masing run; source receipt dan checkpoints lokal tetap arsip beku. Ringkasan publik tidak memublikasikan corpus atau model checkpoints. Koreksi target CI di bagian sebelumnya tetap memakai derived receipt terpisah; perubahan runner untuk run masa depan tidak mengubah atau mengulang hasil run lama.

## Bukti yang dapat diaudit

Setiap run menyediakan `manifest.json`, `summary.json`, `selection.json`, `bootstrap.json`, `autocomplete.json`, `diagnostics.json`, split/source documents, model checkpoint, serta receipts per model/domain. Manifest mengikat corpus, split, code/dependencies dan output hashes; pembacaan completed run memverifikasi receipt. Checkpoint membawa algorithm/preprocess version, vocabulary, provenance dan tuning trace. Run ID baru diperlukan untuk percobaan baru; hasil completed tidak ditimpa. Tidak ada perubahan kode fingerprint untuk menyamarkan run lama.

## Referensi teknis yang diverifikasi

Chen, S. F. & Goodman, J. (1998). *An Empirical Study of Smoothing Techniques for Language Modeling*. Harvard Technical Report TR-10-98, August 1998. [Katalog Harvard](https://dash.harvard.edu/entities/publication/73120378-fb0f-6bd4-e053-0100007fdf3b); [PDF mirror Stanford CS224n](https://prod-c2g.s3.amazonaws.com/cs224n/Fall2012/files/chen-1998.pdf). Verifikasi 10 Oktober 2026: PDF aktual disimpan `.cache/reference/ChenGoodman1998.pdf`, ekstraksi `.cache/reference/ChenGoodman1998.txt` dengan pypdf sementara via uv (tanpa dependency permanen). §2.5 menjelaskan WB interpolasi; §3/eq26 mengandung estimator MKN. Artikel ACL 1996 dengan judul mirip tidak dipakai sebagai sumber estimator MKN 1998.

SHA256 PDF mirror: `939b8e5e99e426b83e29863bd26ccf4141130befa8c3225c5ae908a25170d928`.

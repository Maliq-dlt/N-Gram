# Selisih berpasangan orde tiga dan empat

Analisis turunan deskriptif dari `extensions/results/experiments.csv` pada
commit sumber `34e3df8e3298b6d73fb50d03a2a36d09bd9d79c3`.
Grid, parameter terpilih, CSV sumber, dan model tidak diubah.
Skrip tidak memuat korpus, melatih model, memilih parameter, atau mengevaluasi test.
Kontras orde tiga terhadap empat ditetapkan setelah hasil utama diperiksa;
analisis ini bersifat post-hoc, bukan konfirmatori.

## Jalankan dari root repositori

```sh
python extensions/experiments/paired_orders.py --output extensions/results/derived/paired_orders_reproduction
python -m unittest discover -s extensions/tests -p 'test_paired_orders.py' -v
```

Python >=3.11 dan standard library cukup. Direktori keluaran harus belum ada.
Keluaran yang disimpan untuk makalah berada di `extensions/results/derived/paired_orders_v1/`.
Metode default adalah `kneser_ney`. Opsi `--method` juga menerima `laplace`,
`add_k`, atau `interpolation`; Stupid Backoff dikecualikan dari perbandingan PP.

Skrip mengunci identitas CSV sumber melalui SHA-256. Perubahan CRLF menjadi LF
untuk pemeriksaan identitas dicatat eksplisit; SHA-256 byte masukan sebenarnya
juga disimpan. Masukan dibaca ulang setelah analisis untuk memeriksa perubahan.
Seluruh grid 120 baris diperiksa untuk konfigurasi hilang, duplikat, nilai PP
invalid, dan konsistensi ukuran vocabulary serta jumlah target per seed/ambang.
Metadata tersebut merupakan pemeriksaan konsistensi, bukan bukti identitas split;
identitas split diwarisi dari protokol dan artefak sumber.

## Definisi

- `delta_pp = pp_n3 - pp_n4`; positif berarti orde empat lebih rendah.
- `relative_reduction_pct = 100 * (pp_n3 - pp_n4) / pp_n3`.
- Rerata adalah rerata aritmetika dari tiga selisih berpasangan, tanpa pembobotan token.
- Simpangan baku memakai ddof=1 pada selisih, bukan gabungan std kedua orde.
- Rerata persentase dihitung dari persentase per seed, bukan rasio kedua rerata PP.

`paired_orders.csv` menyimpan enam pasangan KN dengan nilai presisi penuh.
`paired_summary.csv` menyimpan dua ringkasan terpisah menurut ambang UNK.
`manifest.json` memuat commit sumber, hash masukan, hash skrip, hash keluaran,
versi Python, waktu pembuatan, rumus, dan status penyelesaian.
Tidak dihitung p-value, interval keyakinan, ataupun klaim generalisasi lintas korpus.

## Verifikasi pada lingkungan pembuatan

18 unit/integration tests dan 7 subtests lulus pada Python 3.13.5, pytest 9.0.2.
Pengujian meliputi perhitungan Decimal independen, tanda selisih, penyebut
persentase, ddof=1, konfigurasi hilang/duplikat, metadata tidak cocok,
PP tidak valid, input berubah, CRLF, penolakan overwrite, serta determinisme CSV.
Uji awal gagal karena modul belum dibuat, lalu lulus setelah implementasi.

Clone lengkap tidak tersedia karena resolusi jaringan gagal. Percobaan suite
proyek `python -m pytest core/tests extensions/tests -q` berhenti dengan exit 4
karena `core/tests` tidak ada dalam workspace parsial; tidak ada tes proyek
lama yang dijalankan. Ruff, build paket, dan CI seluruh repositori belum
terverifikasi pada perubahan ini. Hasil uji di atas hanya untuk skrip baru.

## Pemakaian dalam makalah

Snapshot sumber tetap menjadi provenance data, sedangkan rujukan ketersediaan
kode makalah harus menunjuk commit turunan yang memuat skrip ini, tes, dan
keluaran tersebut. Jangan menyatakan bahwa skrip ada dalam commit sumber lama.
Repositori memuat pengembangan lanjutan yang berstatus eksploratif dan tidak
dilaporkan dalam makalah eksperimen 120 konfigurasi ini.

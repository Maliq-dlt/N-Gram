# Sumber data dan atribusi

[Metode/hasil](ACADEMIC_LAB.md) · [Ekspor numerik](pilot_metrics.json)

## Corpus pilot

- **Brown dan Reuters**: corpus NLTK, masing-masing 120 dokumen terurut, bukan seluruh corpus. Reuters pilot mengambil subset file `test/` lalu menerapkan split dokumen lokal; ini bukan official train/test benchmark Reuters. Loader mempertahankan document ID, genre, sumber, aturan preprocessing, dan metadata split/duplikat. NLTK adalah alat pembaca/validasi; model N-gram diimplementasikan sendiri. [Brown](https://www.nltk.org/nltk_data/) · [Reuters](https://www.nltk.org/nltk_data/).
- **Wikipedia bahasa Indonesia**: 40 introduction artikel, 432 kalimat, 8,251 token; train/dev/test 32/4/4 artikel. Diambil dari API resmi dengan rightsinfo yang diverifikasi sebagai CC BY-SA 4.0. Importer menyimpan URL artikel/history, revision ID, lisensi, hash respons/raw extract, dan hash dokumen. [Lisensi CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) · [Kebijakan Wikimedia](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use).

Wikipedia JSONL pilot SHA256: `47c30a7cb81e9d4e4079b0cf20605059cbabe6d92044ffe2d2c64e462bb646ad`. Document digest: `14a2d75b3ea39ce1ab762299574fa4fb2337ffbd4b517a7ec3bef769eabc1259`. Data mentah dan daftar atribusi per artikel disimpan di manifest dataset lokal `data/indonesian/wiki-pilot-20261010-final/`; tidak dibundel ke repository atau wheel. Untuk mendistribusikan extract turunannya, sertakan atribusi/revision/license yang disimpan importer dan patuhi share-alike, serta hak corpus lain masing-masing. Lisensi kode tidak mengganti lisensi data/model.

## Batas publikasi

`pilot_metrics.json` berisi angka agregat, provenance hashes dan protocol/selection ringkas. Tidak mengandung kalimat corpus, counts/checkpoint, identitas pekerja, ledger events, credential atau bobot model. Checkpoint besar dibuat melalui CLI/research lokal; instalasi menghubungkan kode dan dependency, tidak memasukkan seluruh AI/data ke GitHub.

Demo Lab memakai enam kalimat Inggris yang ditulis khusus untuk menjelaskan rumus. Fixture tes berisi kejadian/identitas fiktif terkontrol dan tidak boleh disebut data evaluasi kualitas deteksi, biometrik atau operasional.

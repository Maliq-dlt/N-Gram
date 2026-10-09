# Keamanan

## Lingkup dukungan

Perbaikan ditujukan ke versi terbaru `main`. Video Insight memakai autentikasi,
workspace/role dan SQLite lokal, dengan satu worker. Default tetap loopback. Konfigurasi
container/HTTPS tersedia, tetapi runtime container dan deployment publik belum tervalidasi.
[Hardening dan batas implementasi](industrial_ai/docs/HARDENING.md) menjelaskan setup,
backup, audit, serta fitur yang masih direncanakan.

## Melaporkan celah secara privat

Gunakan [Report a vulnerability](https://github.com/Maliq-dlt/N-Gram/security/advisories/new).
Sertakan commit, komponen, reproduksi minimal dan dampak tanpa credential/data pribadi.
Jika kanal tidak tersedia, buka issue yang hanya meminta kanal privat; jangan sertakan
payload eksploitasi atau rekaman sensitif. Tidak ada janji waktu respons enterprise.

## Boundary keamanan

Cookie sesi HttpOnly/SameSite, CSRF pada unsafe API selain login yang dilindungi Origin,
validasi Host/Origin, role/workspace dan rate limit diterapkan backend. Password memakai
scrypt; tidak ada password bawaan. UI tidak menggantikan otorisasi backend. Media/path,
input kotak dan batas upload divalidasi; FFmpeg membatasi protokol dan format. Checkpoint
berasal dari sumber setup tepercaya; API tidak menerima checkpoint arbitrer.

SQLite menyimpan metadata authoritative; media asli tetap berupa berkas. Audit HMAC
mempunyai key/anchor di host yang sama di luar DB, bukan proteksi terhadap administrator
host berprivilege. Backup SQLite/key/anchor dan manifest tidak menyalin semua video/model.

## Data dan batas penggunaan

`industrial_ai/data/`, `models/` dan cache tidak masuk Git. Berkas akses awal
`data/security/first-access.txt`, database, key dan backup adalah data sensitif. Periksa
log/screenshot sebelum berbagi wajah atau plat. Jangan mengunggah credential ke issue.

Deteksi/percakapan dan nama objek manual bukan pengenal wajah atau penentu keselamatan.
Facial enrollment, embeddings, PAD dan evaluasi identitas belum diterapkan. Gunakan review
manusia dan evaluasi independen sebelum pemakaian operasional. Patuhi lisensi Ultralytics
AGPL-3.0/enterprise serta hak masing-masing checkpoint sebelum redistribusi.

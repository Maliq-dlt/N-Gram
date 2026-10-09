# Keamanan

## Lingkup dukungan

Perbaikan keamanan ditujukan ke versi terbaru di `main`. Video Insight adalah
aplikasi lokal satu pengguna. Jalankan pada `127.0.0.1`; belum ada autentikasi,
izin per pengguna, atau rancangan deployment internet.

## Melaporkan celah secara privat

Gunakan **[Report a vulnerability](https://github.com/Maliq-dlt/N-Gram/security/advisories/new)**
(pelaporan privat diaktifkan). Sertakan commit/versi, komponen, langkah reproduksi,
dampak, dan contoh minimal tanpa data pribadi. Jika kanal belum tersedia, buka issue
yang hanya meminta kanal kontak; jangan sertakan payload eksploitasi/rekaman sensitif.
Tidak ada janji waktu respons atau dukungan enterprise.

## Perlindungan yang diterapkan

- Backend loopback; Host dan Origin request tulis diperiksa.
- UUID/nama media serta ukuran/durasi/resolusi upload divalidasi.
- Kotak harus valid; state ditulis atomik dengan revision guard.
- Training otomatis memakai label disahkan dan minimal dua hash sumber asli.
- Model unduhan utama punya revision/checksum; hasil dan bobot dasar dipertahankan.
- CI berizin baca repository; Actions dipin ke commit.

## Data dan model lokal

Upload, anotasi, hasil, serta kandidat berada di `industrial_ai/data/`; bobot di
`models/`. Folder ini tidak diunggah ke GitHub. Periksa screenshot/log sebelum dibagikan
agar tidak memuat wajah, plat, atau data pribadi. Checkpoint PyTorch harus berasal
dari sumber tepercaya pada setup; API tidak menerima upload checkpoint arbitrer.

Deteksi/percakapan bukan penentu identitas atau dasar keputusan keselamatan.
Tinjau label dan lakukan evaluasi independen sebelum pemakaian operasional.

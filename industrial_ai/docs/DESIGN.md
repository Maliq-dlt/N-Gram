# Video Insight design

## Scene and theme

Pengguna meninjau CCTV pada laptop di ruang terang pada siang hari dan kamar redup pada malam hari. Tema sistem mengikuti lingkungan; Terang dan Gelap tersedia sebagai pilihan eksplisit.

## Visual system

System font Apple/Segoe UI, ukuran dasar 14px, label 12px, judul 28px (23px pada mobile). Netral sedikit dingin dan satu aksen biru untuk tindakan/seleksi; warna helm tetap semantik. Surface solid, garis tipis, radius kontrol 8px dan media 12px. Spasi dasar 4px dengan kelompok 8/12px dan pemisah bagian 24/32px.

## Layout

Sidebar yang ada tetap. Konten berisi pemilihan rekaman dan pengaturan analisis yang dapat dibuka, video perbandingan besar dengan pilihan berdampingan/fokus hasil/fokus asli, strip ringkasan datar, serta percakapan di kanan tanpa kartu pembungkus. Detail teknis dan arti hitungan berada dalam disclosure native. Mobile menumpuk video dan asisten, tanpa horizontal overflow.

## Interaction

Radio native sebagai segmented control mode hasil, diadaptasi dari referensi 21st.dev. Feedback tekan langsung, transisi warna singkat, tanpa animasi saat reduced motion. Fullscreen mempertahankan video, overlay, dan inspector yang sama. Profil pengguna menjadi halaman tersendiri: avatar initials, username, workspace dan peran nyata; form password inline, konfirmasi, status aksesibel dan submit lock. Isian password dibersihkan saat meninggalkan profil; rotasi token tidak me-reload video. Tombol profil berhenti saat proses yang tidak boleh ditinggalkan berjalan.

## Sources

- reports/DESAIN_DASHBOARD.md: HeroUI native styles, sidebar 21st.dev, video-centered Dribbble reference.
- https://21st.dev/@ddoemonn/components/segmented-control: source reviewed, native behavior/layout adapted; no React/Motion source copied.
- https://21st.dev/@originui/components/dropdown-menu (393): source reviewed; avatar/identity grouping adapted into a profile destination with native HTML, no Radix dependency.
- https://github.com/emilkowalski/skills: apple-design installed locally for this task.
- C:/Users/malik/.agents/skills/impeccable/SKILL.md: product register, distill, layout.

## Revisi UI 2026-10-10

Login memakai kartu ringkas dari referensi modern-stunning-sign-in, dengan akses
admin yang nyata dan tanpa registrasi/SSO contoh. Initial signed-out mencegah
flash dashboard sebelum sesi dipastikan. Split V dipilih pengguna sebagai logo.

Dark mengikuti token ProMotor Wow (background 228 33% 3%, panel 228 28% 6%,
primary 221 87% 53%); terang memakai putih dingin yang lembut. Toggle sun/moon
di header berdampingan dengan profil; pilihan sistem tetap tersedia di profil.

Orb berisi titik pada bola berputar hanya selama request chat; tempatnya di
kolom chat tanpa overlay pada video. Loading login memakai kerumunan Open Peeps
yang diadaptasi dari Skiper39, terikat pemuatan workspace sebenarnya. Tidak ada
progress atau jeda buatan. Semua loop berhenti saat selesai/gagal; reduced-motion
menampilkan pose statis dan callback gambar terlambat dibatalkan secara logis.

Nama dan avatar merupakan data akun di SQLite, bukan localStorage. Avatar harus
JPEG/PNG/WebP statis <=2 MiB dan <=4 MP, dinormalisasi menjadi PNG <=512px tanpa
metadata. Password meter adalah saran kekuatan dengan deteksi pola umum,
segmen animasi, checklist serta pengumuman aksesibel. Batas server 12-256
karakter dan rotasi scrypt/session/CSRF tetap otoritatif.

Sumber rinci dan atribusi: assets/THIRD_PARTY_LICENSES.txt. Panduan logo:
docs/brand/guidelines.md. Tidak menambahkan React/Motion/GSAP untuk adaptasi native ini.

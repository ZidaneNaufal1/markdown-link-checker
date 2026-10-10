# Markdown Link Checker

[![Tests](https://github.com/ZidaneNaufal1/markdown-link-checker/actions/workflows/tests.yml/badge.svg)](https://github.com/ZidaneNaufal1/markdown-link-checker/actions/workflows/tests.yml)

Alat CLI untuk penulis dokumentasi yang ingin menemukan tautan file dan anchor
Markdown lokal yang rusak sebelum commit atau publikasi. Pemeriksaan berjalan
offline, menggunakan Python standard library, dan tidak mengubah dokumen sumber.

## Mulai cepat

Persyaratan: Python 3.9 atau lebih baru. Tidak ada dependency pihak ketiga.

```sh
git clone https://github.com/ZidaneNaufal1/markdown-link-checker.git
cd markdown-link-checker
python link_checker.py examples/valid
python examples/run_demo.py
```

Demo menjalankan dua skenario: dokumen valid (exit 0) dan dokumen dengan file
serta anchor hilang (exit 1), lalu memastikan byte dokumen tidak berubah.

Untuk memeriksa repo ini, contoh rusak sengaja dikecualikan:

```sh
python link_checker.py . --config .linkcheck.json
```

Untuk dokumentasi proyek lain:

```sh
python link_checker.py /path/to/project
python link_checker.py /path/to/project --format json > report.json
```

Di Windows, path berspasi dapat ditulis dalam tanda kutip. Root default adalah
direktori kerja saat ini. Laporan ditulis ke stdout; pengalihan ke file dilakukan
oleh shell dan sebaiknya memakai nama baru, bukan nama dokumen sumber.

## Contoh hasil

```text
README.md:3: missing_target: missing.md — File atau direktori tujuan tidak ditemukan.
README.md:4: missing_anchor: #belum-ada — Anchor heading tidak ditemukan.
GAGAL: 1 dokumen, 2 link lokal, 2 masalah, 0 dilewati.
```

Laporan JSON berisi `version`, `files_scanned`, `links_checked`, `links_skipped`,
`issues`, dan `ok`. Setiap issue memuat file, nomor baris (1-based), target, code,
dan pesan. Baris 0 menunjukkan dokumen sumber yang gagal dibaca.

| Exit code | Arti |
| --- | --- |
| 0 | Semua link yang diperiksa valid; folder kosong juga dianggap valid |
| 1 | Ditemukan link rusak, reference tidak terdefinisi, atau dokumen gagal dibaca |
| 2 | Root atau konfigurasi tidak valid |

## Perilaku yang didukung

- Inline link dan gambar, reference link penuh/collapsed/shortcut dengan definisi.
- Tautan relatif terhadap dokumen; slash awal `/` relatif terhadap root pemeriksaan.
- Path URL-encoded, destination dalam angle bracket, tanda kurung seimbang, judul link.
- Anchor heading ATX (`#`) dan Setext; heading duplikat diberi suffix `-1`, `-2`.
- `.md` dan `.markdown` tanpa membedakan kapitalisasi, UTF-8 dengan/tanpa BOM.
- Link di fenced code, inline code, komentar HTML, dan baris berindentasi diabaikan.
- URL dengan scheme (`https:`, `mailto:`, dll.) dan URL protocol-relative dilewati.
- Query string tidak memengaruhi path lokal. Fragment pada file non-Markdown tidak diuji.
- Target di luar root, termasuk symlink ke luar root, tidak dibaca dan dilaporkan.
- `.git`, `.venv`, `node_modules`, dan `__pycache__` dilewati secara default.

Anchor memakai huruf kecil, menghapus format sederhana/punctuation, mempertahankan
huruf/angka Unicode, `_`, `-`, dan mengganti setiap spasi dengan `-`.
Anchor dibandingkan secara case-sensitive setelah percent-decoding.

## Konfigurasi pengecualian

```json
{
  "exclude": ["examples/invalid/*", "generated/*"],
  "ignore_links": ["build/*"]
}
```

`exclude` mencocokkan path dokumen relatif terhadap root; `ignore_links`
mencocokkan destination link sebelum percent-decoding. Keduanya menggunakan
wildcard `fnmatch` case-sensitive; `*` dapat melintasi slash. Dokumen yang
dikecualikan dari scan tetap dapat menjadi target link dan dibaca bila diperlukan.
Daftar harus berupa array string; properti lain ditolak agar typo tidak tersembunyi.

## Pengujian dan CI

```sh
python -m unittest -v
python examples/run_demo.py
python link_checker.py . --config .linkcheck.json
```

CI menjalankan tes, demo, dan pemeriksaan dokumentasi pada Ubuntu/Windows dengan
Python 3.9, 3.11, dan 3.13. Pengujian memakai fixture sintetis di folder temporer
proyek. Tidak memakai data pribadi atau jaringan.

## Batasan versi 1.0

Parser ringan ini mendukung subset Markdown satu baris, bukan seluruh CommonMark
atau seluruh aturan renderer GitHub. Nested label, multiline link/reference,
HTML anchor manual, Markdown di blockquote/list kompleks, serta escape destination
belum didukung penuh. Link yang tidak dikenali parser dapat terlewat; hasil lulus
harus dibaca sesuai batasan ini. Status HTTP dan website eksternal tidak diperiksa.
Heading dengan inline code sederhana didukung; format kompleks dapat menghasilkan
slug berbeda dari renderer tujuan. Periksa tampilan dokumen bila memakai sintaks kompleks.
Program memindai filesystem yang sudah ada; perubahan file saat scan berlangsung
dapat memengaruhi hasil. Gunakan pada salinan repo yang stabil.

## Pemeliharaan dan kontribusi

Lihat [CONTRIBUTING](CONTRIBUTING.md), [CHANGELOG](CHANGELOG.md), dan
[SECURITY](SECURITY.md). Bug sebaiknya menyertakan contoh Markdown minimal dan
hasil yang diharapkan. Pengembangan berikutnya: parsing multiline dan fixture
kompatibilitas renderer. Setiap peningkatan mengikuti kebutuhan nyata dan tes.

## English summary

Offline CLI for checking local Markdown file links and heading fragments.
It reports source locations, supports JSON output and configurable exclusions,
and leaves source files unchanged. Requires Python 3.9+ with no third-party
dependencies. Run `python link_checker.py PATH --format json`; exit codes are
0 (pass), 1 (broken link/read error), and 2 (invalid input). External URLs are
skipped. This lightweight parser supports the documented subset, not full
CommonMark or complete GitHub renderer compatibility.

## Kredit dan lisensi

Proyek portofolio Muhammad Zidane Naufal Azzam. Dikembangkan dengan bantuan AI
untuk implementasi, dokumentasi, dan pengujian; hasil diuji melalui tes otomatis
dan demo. Lisensi [MIT](LICENSE).

# Berkontribusi

Terima kasih atas kontribusi untuk meningkatkan kualitas dokumentasi lokal.
Gunakan Python 3.9+ dan jalankan command berikut sebelum mengirim pull request:

```sh
python -m unittest -v
python examples/run_demo.py
python link_checker.py . --config .linkcheck.json
```

Untuk bug parsing, sertakan contoh Markdown minimal dengan nomor baris, command,
versi Python/OS, output aktual, dan output yang diharapkan. Gunakan data sintetis.
Jelaskan renderer yang ditargetkan bila melaporkan perbedaan anchor.

Untuk fitur, uraikan masalah pengguna, batas scope, dan acceptance criteria.
PR harus menyertakan tes perilaku yang berubah, dokumentasi yang relevan, dan
catatan changelog. Pertahankan mode offline dan operasi baca saja. Bahasa utama
dokumentasi adalah Bahasa Indonesia; diskusi English juga diterima.

Gunakan commit message English yang singkat dan menjelaskan perubahan.
Issue/PR publik tidak boleh memuat credential, dokumen rahasia, atau data pribadi.
Pelaporan keamanan mengikuti [SECURITY](SECURITY.md).

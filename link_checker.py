"""Offline Markdown link checker. Python 3.9+, standard library only."""
import argparse
import fnmatch
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

VERSION = "1.0.0"


def visible_lines(text):
    """Remove fences, HTML comments and inline code, retaining line numbers."""
    text = re.sub(r"<!--.*?-->", lambda m: "\n" * m[0].count("\n"), text, flags=re.S)
    fence = None
    result = []
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            result.append("")
        elif marker:
            fence = marker[1]
            result.append("")
        elif line.startswith("    ") or line.startswith("\t"):
            result.append("")
        else:
            result.append(re.sub(r"(`+).*?\1", "", line))
    return result


def slug(text):
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]*>", "", html.unescape(text)).lower()
    return "".join(c for c in text if c.isalnum() or c in "_- " ).replace(" ", "-")


def anchors(text):
    # Retain inline-code labels in headings, but remove delimiters.
    lines = visible_lines(re.sub(r"`([^`\n]+)`", r"\1", text))
    used = set()
    for i, line in enumerate(lines):
        match = re.match(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        title = match[1] if match else None
        if title is None and i + 1 < len(lines) and re.match(r"^ {0,3}(=+|-+)\s*$", lines[i + 1]) and line.strip():
            title = line.strip()
        if title is not None:
            base = slug(title)
            value, index = base, 0
            while value in used:
                index += 1
                value = f"{base}-{index}"
            used.add(value)
    return used


def destination(raw):
    raw = raw.strip()
    if raw.startswith("<") and ">" in raw:
        return raw[1:raw.index(">")]
    # Titles are optional and begin after whitespace.
    return re.split(r"\s", raw, maxsplit=1)[0] if raw else ""


def extract_links(text):
    lines = visible_lines(text)
    definitions = {}
    definition_lines = set()
    for i, line in enumerate(lines):
        m = re.match(r"^ {0,3}\[([^\]]+)\]:\s*(.+)$", line)
        if m:
            definitions.setdefault(" ".join(m[1].lower().split()), destination(m[2]))
            definition_lines.add(i)
    links = []
    # Inline destinations can contain balanced parentheses and escaped punctuation.
    for i, line in enumerate(lines):
        if i in definition_lines:
            continue
        cursor = 0
        for m in re.finditer(r"(?<!\\)(!?)\[([^\[\]]+)\]", line):
            if m.start() < cursor:
                continue
            end = m.end()
            if line[end:end + 1] == "(":
                depth, pos = 1, end + 1
                while pos < len(line) and depth:
                    if line[pos] == "\\":
                        pos += 2
                        continue
                    depth += (line[pos] == "(") - (line[pos] == ")")
                    pos += 1
                if depth:
                    continue
                links.append((i + 1, destination(line[end + 1:pos - 1])))
                cursor = pos
            else:
                ref = re.match(r"\[([^\]]*)\]", line[end:])
                label = (ref[1] or m[2]) if ref else m[2]
                label = " ".join(label.lower().split())
                if label in definitions:
                    links.append((i + 1, definitions[label]))
                elif ref:
                    links.append((i + 1, None))
                if ref:
                    cursor = end + ref.end()
    return links


def load_config(path):
    if path is None:
        return {"exclude": [], "ignore_links": []}
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or set(data) - {"exclude", "ignore_links"}:
        raise ValueError("Konfigurasi hanya menerima exclude dan ignore_links.")
    for key in ("exclude", "ignore_links"):
        data.setdefault(key, [])
        if not isinstance(data[key], list) or not all(isinstance(x, str) for x in data[key]):
            raise ValueError(f"{key} harus berupa daftar string.")
    return data


def check(root, config=None):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("Root harus berupa direktori yang tersedia.")
    config = config or {"exclude": [], "ignore_links": []}
    issues, checked, skipped, scanned = [], 0, 0, 0
    cache = {}
    files = sorted(p for p in root.rglob("*") if p.suffix.lower() in (".md", ".markdown") and p.is_file())
    def issue(source, line, target, code, detail):
        issues.append({"file": source, "line": line, "target": target, "code": code, "message": detail})
    def read(path):
        if path not in cache:
            cache[path] = path.read_text(encoding="utf-8-sig")
        return cache[path]
    for file in files:
        relative = file.relative_to(root).as_posix()
        if any(part in (".git", ".venv", "node_modules", "__pycache__") for part in file.relative_to(root).parts):
            continue
        if any(fnmatch.fnmatchcase(relative, pattern) for pattern in config["exclude"]):
            continue
        scanned += 1
        try:
            file.resolve().relative_to(root)
            text = read(file)
        except (OSError, UnicodeError, ValueError) as exc:
            issue(relative, 0, "", "unreadable_source", f"Dokumen gagal dibaca: {exc}")
            continue
        for line, target in extract_links(text):
            if target is None:
                checked += 1
                issue(relative, line, "", "undefined_reference", "Definisi reference link tidak ditemukan.")
                continue
            if any(fnmatch.fnmatchcase(target, pattern) for pattern in config["ignore_links"]):
                skipped += 1
                continue
            try:
                parts = urlsplit(target)
            except ValueError:
                checked += 1
                issue(relative, line, target, "invalid_link", "Format link tidak valid.")
                continue
            if parts.scheme or parts.netloc:
                skipped += 1
                continue
            checked += 1
            path = unquote(parts.path)
            fragment = unquote(parts.fragment)
            if "\x00" in path or "\\" in path:
                issue(relative, line, target, "invalid_path", "Gunakan path URL dengan slash dan tanpa NUL.")
                continue
            resolved = (root / path.lstrip("/") if path.startswith("/") else file.parent / path if path else file).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                issue(relative, line, target, "outside_root", "Link keluar dari root; target tidak dibaca.")
                continue
            if not resolved.exists():
                issue(relative, line, target, "missing_target", "File atau direktori tujuan tidak ditemukan.")
            elif fragment and resolved.suffix.lower() in (".md", ".markdown"):
                try:
                    if fragment not in anchors(read(resolved)):
                        issue(relative, line, target, "missing_anchor", "Anchor heading tidak ditemukan.")
                except (OSError, UnicodeError) as exc:
                    issue(relative, line, target, "unreadable_target", f"Tujuan gagal dibaca: {exc}")
    return {"version": VERSION, "files_scanned": scanned, "links_checked": checked,
            "links_skipped": skipped, "issues": issues, "ok": not issues}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Periksa tautan Markdown lokal tanpa jaringan.")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--config", help="File JSON berisi exclude dan ignore_links.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args(argv)
    try:
        report = check(args.root, load_config(args.config))
    except (OSError, ValueError, UnicodeError) as exc:
        if args.format == "json":
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"Gagal: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in report["issues"]:
            print(f'{item["file"]}:{item["line"]}: {item["code"]}: {item["target"]} — {item["message"]}')
        status = "LULUS" if report["ok"] else "GAGAL"
        print(f'{status}: {report["files_scanned"]} dokumen, {report["links_checked"]} link lokal, '
              f'{len(report["issues"])} masalah, {report["links_skipped"]} dilewati.')
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

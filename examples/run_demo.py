"""Reproducible demo; source documents remain unchanged."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run():
    snapshots = {p: p.read_bytes() for p in (ROOT / "examples").rglob("*.md")}
    for folder, expected in (("valid", 0), ("invalid", 1)):
        result = subprocess.run([sys.executable, str(ROOT / "link_checker.py"),
                                 str(ROOT / "examples" / folder), "--format", "json"],
                                capture_output=True, text=True, encoding="utf-8")
        assert result.returncode == expected, result.stderr
        report = json.loads(result.stdout)
        if folder == "invalid":
            assert {x["code"] for x in report["issues"]} == {"missing_target", "missing_anchor"}
        print(f'Demo {folder}: exit={result.returncode}, masalah={len(report["issues"])}')
    assert all(p.read_bytes() == data for p, data in snapshots.items())
    print("Demo selesai. Dokumen sumber tetap identik.")

if __name__ == "__main__":
    run()

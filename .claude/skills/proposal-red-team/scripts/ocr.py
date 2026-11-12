#!/usr/bin/env python3
"""Local OCR for scanned PDFs (RFPs are often scans) — no network, Tesseract only.

Usage:
    python3 ocr.py <workdir> --file F2 [--dpi 300] [--jobs 4]

Renders each page of the scanned PDF with pypdfium2, runs `tesseract -l kor+eng` locally, and
replaces that file's units in docmodel.json / units/<F#>/P###.md with the OCR text, so rfp_split.py,
grep and report.py's guard all see it. OCR text is imperfect: quote RFP wording only after checking
the page image (renders/<F#>/ or the original).

Requires: tesseract with the 'kor' language pack
    Windows: UB Mannheim build + Korean data;  Ubuntu: apt-get install tesseract-ocr tesseract-ocr-kor
Never use a cloud OCR API for client documents.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def ocr_page(png: Path) -> str:
    out = png.with_suffix("")
    subprocess.run(["tesseract", str(png), str(out), "-l", "kor+eng", "--psm", "4"],
                   check=True, capture_output=True, env={"OMP_THREAD_LIMIT": "1", "PATH": __import__("os").environ.get("PATH", "")},
                   timeout=600)
    return re.sub(r"[ \t]+", " ", out.with_suffix(".txt").read_text(encoding="utf-8", errors="replace")).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workdir")
    ap.add_argument("--file", required=True, help="file id of the scanned PDF (see manifest.json)")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    if not shutil.which("tesseract"):
        sys.exit("tesseract not found — install it locally (see --help). Do not send the file to an online OCR service.")
    import pypdfium2 as pdfium

    wd = Path(a.workdir).resolve()
    man = json.loads((wd / "manifest.json").read_text(encoding="utf-8"))
    entry = next((m for m in man["files"] if m["file_id"] == a.file), None)
    if not entry or not str(entry.get("path", "")).lower().endswith(".pdf"):
        sys.exit(f"{a.file} is not a PDF in manifest.json")
    doc = pdfium.PdfDocument(entry["path"])
    texts: dict[int, str] = {}
    with tempfile.TemporaryDirectory() as tmp:
        pngs = []
        for i in range(len(doc)):
            p = Path(tmp) / f"P{i + 1:03d}.png"
            doc[i].render(scale=a.dpi / 72).to_pil().convert("L").save(p)
            pngs.append(p)
        doc.close()
        with ThreadPoolExecutor(max_workers=a.jobs) as ex:
            for p, t in zip(pngs, ex.map(ocr_page, pngs)):
                texts[int(p.stem[1:])] = t
                print(f"[ocr] {a.file} p{p.stem[1:]} {len(t)} chars", file=sys.stderr)

    dm = json.loads((wd / "docmodel.json").read_text(encoding="utf-8"))
    udir = wd / "units" / a.file
    udir.mkdir(parents=True, exist_ok=True)
    for u in dm["units"]:
        if u["file_id"] == a.file and u["index"] in texts:
            t = texts[u["index"]]
            u["blocks"] = [{"text": t, "font_pt": None, "bbox": None, "is_title": False}]
            u.pop("lines", None)
            u["gm_source"] = "ocr"
            u["metrics"]["text_chars"] = len(t)
            (udir / f"P{u['index']:03d}.md").write_text(f"# {u['uid']} (OCR — 원문 이미지로 확인 후 인용)\n\n{t}\n", encoding="utf-8")
    (wd / "docmodel.json").write_text(json.dumps(dm, ensure_ascii=False), encoding="utf-8")
    entry["ocr"] = True
    (wd / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"file": a.file, "pages": len(texts), "chars": sum(len(t) for t in texts.values())}, ensure_ascii=False))


if __name__ == "__main__":
    main()

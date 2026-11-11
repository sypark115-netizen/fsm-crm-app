#!/usr/bin/env python3
"""Render slides/pages to PNG for visual review.

Usage:
    python3 render.py <workdir> [--files F1,F2] [--pages 1-20] [--width 1280] [--sheet 3]

Reads <workdir>/manifest.json (from ingest.py). For each PPTX/PDF:
  * PPTX: if a PDF with the same stem sits next to it, that PDF is rendered
    (it is what the author actually exported). Otherwise LibreOffice converts a
    copy inside <workdir>/_pdf/ — the original is never touched.
  * Pages are rendered one at a time with pypdfium2 (memory-safe on huge files);
    existing PNGs are skipped, so the command can be re-run after interruption.
  * Contact sheets (N x N thumbnails) are written for storyline/flow review.
  * Fonts referenced by the PPTX but missing on this machine are reported —
    LibreOffice substitutes them, so the render may differ from PowerPoint.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_range(spec: str | None, n: int) -> list[int]:
    if not spec:
        return list(range(1, n + 1))
    out: set[int] = set()
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), min(int(b), n) + 1))
        else:
            out.add(int(part))
    return sorted(i for i in out if 1 <= i <= n)


def installed_fonts() -> set[str]:
    try:
        res = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True, timeout=30)
        fams = set()
        for line in res.stdout.splitlines():
            for f in line.split(","):
                fams.add(f.strip().lower())
        return fams
    except Exception:
        return set()


def pptx_to_pdf(src: Path, outdir: Path) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    target = outdir / (src.stem + ".pdf")
    if target.exists():
        return target
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise RuntimeError("LibreOffice(soffice) not found; export the deck to PDF and put it next to the PPTX")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_src = Path(tmp) / src.name
        shutil.copy2(src, tmp_src)  # convert a copy, never the original
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", tmp, str(tmp_src)],
                       check=True, capture_output=True, timeout=1800)
        produced = Path(tmp) / (src.stem + ".pdf")
        shutil.move(str(produced), target)
    return target


def contact_sheets(pngs: list[Path], outdir: Path, prefix: str, grid: int, labels: list[str]):
    from PIL import Image, ImageDraw
    if not pngs:
        return []
    tw = 420
    sheets = []
    per = grid * grid
    for s in range(0, len(pngs), per):
        chunk = pngs[s:s + per]
        ims = []
        for p in chunk:
            im = Image.open(p)
            th = int(im.height * tw / im.width)
            ims.append(im.resize((tw, th)))
        th = max(i.height for i in ims)
        sheet = Image.new("RGB", (grid * (tw + 10) + 10, grid * (th + 34) + 10), "white")
        d = ImageDraw.Draw(sheet)
        for k, im in enumerate(ims):
            r, c = divmod(k, grid)
            x, y = 10 + c * (tw + 10), 10 + r * (th + 34)
            sheet.paste(im, (x, y + 24))
            d.rectangle([x, y + 24, x + tw - 1, y + 24 + im.height - 1], outline="#999999")
            d.text((x, y + 4), labels[s + k], fill="black")
        name = outdir / f"{prefix}_sheet_{s // per + 1:02d}.png"
        sheet.save(name)
        sheets.append(str(name))
    return sheets


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workdir")
    ap.add_argument("--files", help="comma list of file ids (default: all pptx/pdf)")
    ap.add_argument("--pages", help="e.g. 1-20,25")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--sheet", type=int, default=3, help="contact sheet grid size (0 = none)")
    args = ap.parse_args()

    import pypdfium2 as pdfium

    wd = Path(args.workdir).resolve()
    manifest = json.loads((wd / "manifest.json").read_text(encoding="utf-8"))
    want = set(args.files.split(",")) if args.files else None
    fonts = installed_fonts()
    report = {"files": []}
    dm = json.loads((wd / "docmodel.json").read_text(encoding="utf-8"))
    visible: dict[str, list[int]] = {}
    for u in dm["units"]:
        if u["kind"] == "slide" and not u.get("hidden"):
            visible.setdefault(u["file_id"], []).append(u["index"])

    for m in manifest["files"]:
        if m.get("error") or m.get("ext") not in (".pptx", ".pdf"):
            continue
        if want and m["file_id"] not in want:
            continue
        src = Path(m["path"])
        entry = {"file_id": m["file_id"], "name": m["name"], "warnings": []}
        if m["ext"] == ".pptx":
            sibling = src.with_suffix(".pdf")
            if sibling.exists():
                pdf_path = sibling
                entry["render_source"] = f"sibling PDF ({sibling.name}) — author's own export"
            else:
                try:
                    pdf_path = pptx_to_pdf(src, wd / "_pdf")
                except Exception as e:
                    entry["warnings"].append(f"render failed: {e}")
                    report["files"].append(entry)
                    continue
                entry["render_source"] = "LibreOffice conversion (layout may differ from PowerPoint)"
                missing = [f for f in m.get("meta", {}).get("fonts_used", [])
                           if f.lower() not in fonts and not f.startswith("+")]
                if missing:
                    entry["warnings"].append(
                        "fonts not installed (substituted in render): " + ", ".join(missing)
                        + " — text wrapping/size in PNG may differ from the real deck")
            kind = "S"
        else:
            pdf_path = src
            entry["render_source"] = "PDF"
            kind = "P"

        outdir = wd / "renders" / m["file_id"]
        outdir.mkdir(parents=True, exist_ok=True)
        doc = pdfium.PdfDocument(str(pdf_path))
        n = len(doc)
        # map rendered page -> slide index (PDF exports usually drop hidden slides)
        page_to_idx = {i: i for i in range(1, n + 1)}
        if m["ext"] == ".pptx" and n != m.get("units"):
            vis = visible.get(m["file_id"], [])
            if len(vis) == n:
                page_to_idx = {i: vis[i - 1] for i in range(1, n + 1)}
                entry["warnings"].append(f"{m['units'] - n} hidden slide(s) not rendered; PNG names use real slide numbers")
            else:
                entry["warnings"].append(f"render has {n} pages but deck has {m.get('units')} slides — check numbering")
        pages = parse_range(args.pages, n)
        pngs, labels = [], []
        for i in pages:
            png = outdir / f"{kind}{page_to_idx[i]:03d}.png"
            if not png.exists():
                page = doc[i - 1]
                w_pt = page.get_width()
                scale = args.width / w_pt
                img = page.render(scale=scale).to_pil()
                img.save(png)
                page.close()
            pngs.append(png)
            labels.append(f"{m['file_id']}#{kind}{page_to_idx[i]:03d}")
        doc.close()
        entry["rendered"] = len(pngs)
        entry["dir"] = str(outdir)
        if args.sheet:
            entry["contact_sheets"] = contact_sheets(pngs, outdir, m["file_id"], args.sheet, labels)
        report["files"].append(entry)
        print(f"[render] {m['file_id']} {len(pngs)} pages → {outdir}", file=sys.stderr)

    if not fonts:
        report["warnings"] = ["fc-list unavailable: could not verify fonts"]
    elif not any(k in f for f in fonts for k in ("nanum", "noto sans cjk", "malgun", "맑은", "noto sans kr", "pretendard")):
        report.setdefault("warnings", []).append(
            "no Korean font installed — Korean text in LibreOffice renders will be wrong. "
            "Install one (e.g. apt-get install fonts-nanum) or supply the deck as PDF.")
    (wd / "render_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

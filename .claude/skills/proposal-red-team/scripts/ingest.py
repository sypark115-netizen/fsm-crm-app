#!/usr/bin/env python3
"""Ingest proposal files into a Document Model (read-only on originals).

Usage:
    python3 ingest.py <file-or-folder> [more ...] --out <workdir>

Outputs (all inside --out):
    manifest.json   file list with role guess (rfp/proposal/presentation/supporting)
    docmodel.json   per slide/page records
    gm_outline.md   Governing Message candidates for every unit (storyline pass)
    units/F#/S###.md or P###.md   per-unit text, for grep and batched review

Media (images/video) are never extracted — only their footprint is recorded —
so 200MB+ decks stay cheap. PDFs are streamed page by page.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

SUPPORTED = {".pptx", ".pdf", ".docx", ".xlsx", ".txt", ".md"}
SKIP_DIRS = {".redteam", ".git", "__pycache__"}

ROLE_KEYWORDS = {
    "rfp": ["rfp", "제안요청", "요청서", "과업지시", "과업내용", "입찰공고", "제안안내"],
    "presentation": ["발표", "presentation", "pt자료", "pt_", "_pt", "요약본", "설명회"],
    "proposal": ["제안서", "proposal", "기술제안", "본제안"],
}


# --------------------------------------------------------------------------- helpers

def clean(text: str) -> str:
    text = text.replace("\x0b", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def guess_role(path: Path, kind_hint: str | None, n_units: int, landscape: bool | None) -> tuple[str, str]:
    name = path.name.lower()
    for role, kws in ROLE_KEYWORDS.items():
        for kw in kws:
            if kw in name:
                return role, f"파일명에 '{kw}' 포함"
    if path.suffix.lower() in {".xlsx", ".docx", ".txt", ".md"}:
        return "supporting", "보조자료 확장자"
    if path.suffix.lower() == ".pptx":
        if n_units <= 80:
            return "presentation", f"PPTX {n_units}장 (≤80장)"
        return "proposal", f"PPTX {n_units}장 (>80장, 제출본 추정)"
    if path.suffix.lower() == ".pdf":
        if landscape and n_units <= 80:
            return "presentation", f"가로형 PDF {n_units}p"
        if landscape:
            return "proposal", f"가로형 PDF {n_units}p (>80p, 제출본 추정)"
        return "rfp", f"세로형 PDF {n_units}p (RFP/공문 형식 추정)"
    return "supporting", "기본값"


# --------------------------------------------------------------------------- PPTX

def _pptx_font_size(shape) -> float | None:
    best = None
    if not getattr(shape, "has_text_frame", False) or not shape.has_text_frame:
        return None
    for p in shape.text_frame.paragraphs:
        sizes = [r.font.size.pt for r in p.runs if r.font.size is not None]
        if p.font.size is not None:
            sizes.append(p.font.size.pt)
        for s in sizes:
            best = s if best is None else max(best, s)
    return best


def _walk_shapes(shapes):
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    for sh in shapes:
        if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _walk_shapes(sh.shapes)
        else:
            yield sh


def _smartart_text(slide) -> list[str]:
    out = []
    for rel in slide.part.rels.values():
        if rel.reltype.endswith("/diagramData"):
            try:
                from lxml import etree
                root = etree.fromstring(rel.target_part.blob)
                ts = [t.text for t in root.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}t") if t.text]
                if ts:
                    out.append(" / ".join(ts))
            except Exception:
                continue
    return out


def ingest_pptx(path: Path, fid: str) -> tuple[list[dict], dict]:
    from pptx import Presentation
    from pptx.enum.shapes import PP_PLACEHOLDER

    prs = Presentation(str(path))
    sw, sh_ = prs.slide_width or 1, prs.slide_height or 1
    title_types = {PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE}
    units = []
    fonts_used: set[str] = set()
    for i, slide in enumerate(prs.slides, start=1):
        blocks, tables, charts = [], [], []
        title_text, pic_area, n_shapes = None, 0.0, 0
        hidden = slide._element.get("show") == "0"
        for shp in _walk_shapes(slide.shapes):
            n_shapes += 1
            try:
                x = (shp.left or 0) / sw
                y = (shp.top or 0) / sh_
                w = (shp.width or 0) / sw
                h = (shp.height or 0) / sh_
            except Exception:
                x = y = w = h = 0.0
            ph = None
            if shp.is_placeholder:
                try:
                    ph = shp.placeholder_format.type
                except Exception:
                    ph = None
            if shp.shape_type is not None and "PICTURE" in str(shp.shape_type):
                pic_area += max(w, 0) * max(h, 0)
            if getattr(shp, "has_table", False) and shp.has_table:
                rows = []
                for r in shp.table.rows:
                    rows.append([clean(c.text) for c in r.cells])
                tables.append(rows)
                continue
            if getattr(shp, "has_chart", False) and shp.has_chart:
                ch = shp.chart
                info = {"type": str(ch.chart_type).split(".")[-1].split(" ")[0]}
                try:
                    info["title"] = clean(ch.chart_title.text_frame.text) if ch.has_title else ""
                except Exception:
                    info["title"] = ""
                try:
                    info["categories"] = [str(c) for c in ch.plots[0].categories]
                    info["series"] = [{"name": s.name, "values": list(s.values)} for s in ch.plots[0].series]
                except Exception:
                    pass
                charts.append(info)
                continue
            if getattr(shp, "has_text_frame", False) and shp.has_text_frame:
                txt = clean(shp.text_frame.text)
                if not txt:
                    continue
                for p in shp.text_frame.paragraphs:
                    for r in p.runs:
                        if r.font.name:
                            fonts_used.add(r.font.name)
                size = _pptx_font_size(shp)
                is_title = ph in title_types
                if is_title and title_text is None:
                    title_text = txt
                off = x < -0.01 or y < -0.01 or x > 0.99 or y > 0.99
                blocks.append({
                    "shape_id": shp.shape_id, "name": shp.name, "text": txt, "off_slide": off,
                    "font_pt": size, "bbox": [round(x, 3), round(y, 3), round(w, 3), round(h, 3)],
                    "placeholder": str(ph).split(".")[-1].split(" ")[0] if ph is not None else None,
                    "is_title": is_title,
                })
        for sa in _smartart_text(slide):
            blocks.append({"shape_id": None, "name": "SmartArt", "text": sa, "font_pt": None,
                           "bbox": None, "placeholder": None, "is_title": False})
        gm, gm_src = _pick_gm(title_text, blocks)
        notes = ""
        if slide.has_notes_slide:
            notes = clean(slide.notes_slide.notes_text_frame.text or "")
        body_chars = sum(len(b["text"]) for b in blocks)
        units.append({
            "uid": f"{fid}#S{i:03d}", "file_id": fid, "index": i, "kind": "slide",
            "hidden": hidden, "layout": slide.slide_layout.name,
            "gm": gm, "gm_source": gm_src, "blocks": blocks, "tables": tables, "charts": charts,
            "notes": notes,
            "metrics": {
                "text_chars": body_chars, "n_shapes": n_shapes, "n_text_blocks": len(blocks),
                "picture_area_ratio": round(min(pic_area, 1.0), 3),
                "max_font_pt": max([b["font_pt"] for b in blocks if b["font_pt"]] or [0]) or None,
                "text_coverage_low": body_chars < 40 and pic_area > 0.3,
            },
        })
    meta = {"slide_width_emu": prs.slide_width, "slide_height_emu": prs.slide_height,
            "landscape": (prs.slide_width or 0) >= (prs.slide_height or 0),
            "fonts_used": sorted(fonts_used)}
    return units, meta


def _pick_gm(title_text, blocks):
    """GM = title placeholder; else the largest-font text in the top 35% of the slide."""
    if title_text:
        return title_text, "title_placeholder"
    cands = [b for b in blocks if b["bbox"] and not b.get("off_slide") and b["bbox"][1] < 0.35 and len(b["text"]) <= 240]
    # Korean proposal templates often put a small section title above a "Key Message" sentence.
    # The governing message is the claim sentence (…합니다/…니다/…다), not the bigger section label.
    msgs = [b for b in cands if re.search(r"(니다|한다|된다|이다)[.。]?$", b["text"].strip()) and len(b["text"]) >= 15]
    if msgs:
        b = min(msgs, key=lambda b: b["bbox"][1])
        joined = " / ".join(m["text"].replace("\n", " ") for m in sorted(msgs, key=lambda m: m["bbox"][1])
                            if abs(m["bbox"][1] - b["bbox"][1]) < 0.06)
        return joined, "key_message_sentence"
    sized = [b for b in cands if b["font_pt"]]
    if sized:
        b = max(sized, key=lambda b: (b["font_pt"], -b["bbox"][1]))
        return b["text"], f"largest_font_top({b['font_pt']}pt)"
    if cands:
        b = min(cands, key=lambda b: b["bbox"][1])
        return b["text"], "topmost_text"
    return None, "none"


# --------------------------------------------------------------------------- PDF

def ingest_pdf(path: Path, fid: str, tables: bool) -> tuple[list[dict], dict]:
    import pdfplumber
    from pypdf import PdfReader

    sections = _pdf_outline(PdfReader(str(path)))
    units = []
    landscape_votes = 0
    with pdfplumber.open(str(path)) as pdf:
        n = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            W, H = page.width or 1, page.height or 1
            if W >= H:
                landscape_votes += 1
            lines = _pdf_lines(page)
            text = clean("\n".join(l["text"] for l in lines))
            gm, gm_src = None, "none"
            top = [l for l in lines if l["top"] / H < 0.35 and 2 <= len(l["text"]) <= 160]
            km = [l for l in lines if 0.06 < l["top"] / H < 0.30 and len(l["text"]) >= 15
                  and re.search(r"(니다|한다|된다|이다)[.。]?$", l["text"].strip())]
            if km:  # Key Message sentence(s) beat the bigger section label
                first = min(km, key=lambda l: l["top"])
                gm = clean(" / ".join(l["text"] for l in km if l["top"] - first["top"] < H * 0.06))
                gm_src = "key_message_sentence"
            elif top:
                big = max(l["size"] for l in top)
                body_sizes = sorted(l["size"] for l in lines)
                median = body_sizes[len(body_sizes) // 2] if body_sizes else big
                heads = [l for l in top if l["size"] >= big - 0.5]
                if big > median + 1 or len(lines) < 4:
                    gm = clean(" ".join(l["text"] for l in heads))
                    gm_src = f"largest_font_top({big:.0f}pt)"
            tbls = []
            if tables:
                try:
                    tbls = [[[clean(c or "") for c in row] for row in t] for t in page.extract_tables()]
                except Exception:
                    tbls = []
            img_area = 0.0
            for im in page.images:
                try:
                    img_area += abs((im["x1"] - im["x0"]) * (im["bottom"] - im["top"])) / (W * H)
                except Exception:
                    pass
            units.append({
                "uid": f"{fid}#P{i:03d}", "file_id": fid, "index": i, "kind": "page",
                "section": sections.get(i), "gm": gm, "gm_source": gm_src,
                "blocks": [{"text": text, "font_pt": None, "bbox": None, "is_title": False}] if text else [],
                "lines": [{"t": l["text"], "pt": round(l["size"], 1)} for l in lines[:400]],
                "tables": tbls, "charts": [], "notes": "",
                "metrics": {"text_chars": len(text), "picture_area_ratio": round(min(img_area, 1.0), 3),
                            "max_font_pt": round(max([l["size"] for l in lines] or [0]), 1) or None,
                            "text_coverage_low": len(text) < 40},
            })
            page.flush_cache()
            if hasattr(page, "close"):
                page.close()
    meta = {"pages": n, "landscape": landscape_votes > n / 2}
    if n and sum(u["metrics"]["text_chars"] for u in units) < 20 * n:
        meta["scanned"] = True
        print(f"[warn] {path.name}: 텍스트가 거의 없음 (스캔본) — scripts/ocr.py 로 로컬 OCR 후 다시 사용", file=sys.stderr)
    # carry section forward
    cur = None
    for u in units:
        cur = u["section"] or cur
        u["section"] = cur
    return units, meta


def _pdf_lines(page):
    # x_tolerance 1.5: Korean PDFs often encode word spacing as narrow gaps without space glyphs;
    # the default (3) glues whole titles together ("일본지사전환을출발점으로...").
    words = page.extract_words(extra_attrs=["size"], use_text_flow=True, keep_blank_chars=False, x_tolerance=1.5)
    lines: list[dict] = []
    for w in words:
        if lines and abs(lines[-1]["top"] - w["top"]) < max(2.0, w["size"] * 0.4) and abs(lines[-1]["size"] - w["size"]) < 1.5:
            gap = w["x0"] - lines[-1]["x1"]
            # PDF producers often split one Korean word into chunks; only add a space for a real gap
            sep = "" if -1 < gap < w["size"] * 0.08 else " "
            lines[-1]["text"] += sep + w["text"]
            lines[-1]["size"] = max(lines[-1]["size"], w["size"])
            lines[-1]["x1"] = w["x1"]
        else:
            lines.append({"text": w["text"], "top": w["top"], "size": w["size"], "x1": w["x1"]})
    return lines


def _pdf_outline(reader) -> dict[int, str]:
    out: dict[int, str] = {}
    def walk(items, depth=0):
        for it in items:
            if isinstance(it, list):
                walk(it, depth + 1)
                continue
            try:
                pg = reader.get_destination_page_number(it) + 1
                if depth <= 1 and pg not in out:
                    out[pg] = it.title
            except Exception:
                pass
    try:
        walk(reader.outline)
    except Exception:
        pass
    return out


# --------------------------------------------------------------------------- DOCX / XLSX / TXT

def ingest_docx(path: Path, fid: str):
    import docx
    d = docx.Document(str(path))
    units, buf, head, idx = [], [], None, 0

    def flush():
        nonlocal buf, head, idx
        if buf or head:
            idx += 1
            txt = clean("\n".join(buf))
            units.append({"uid": f"{fid}#P{idx:03d}", "file_id": fid, "index": idx, "kind": "section",
                          "gm": head, "gm_source": "heading" if head else "none",
                          "blocks": [{"text": txt, "font_pt": None, "bbox": None, "is_title": False}],
                          "tables": [], "charts": [], "notes": "",
                          "metrics": {"text_chars": len(txt)}})
        buf, head = [], None

    for p in d.paragraphs:
        style = (p.style.name or "").lower() if p.style is not None else ""
        if style.startswith("heading") or style.startswith("제목"):
            flush()
            head = clean(p.text)
        elif p.text.strip():
            buf.append(p.text)
    flush()
    tbls = [[[clean(c.text) for c in r.cells] for r in t.rows] for t in d.tables]
    if tbls:
        idx += 1
        units.append({"uid": f"{fid}#P{idx:03d}", "file_id": fid, "index": idx, "kind": "tables",
                      "gm": "(문서 내 표 모음)", "gm_source": "synthetic", "blocks": [], "tables": tbls,
                      "charts": [], "notes": "", "metrics": {"text_chars": 0}})
    return units, {"landscape": False}


def ingest_xlsx(path: Path, fid: str):
    import openpyxl
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    units = []
    for i, ws in enumerate(wb.worksheets, start=1):
        rows = []
        for r in ws.iter_rows(values_only=True):
            if any(v is not None for v in r):
                rows.append(["" if v is None else str(v) for v in r])
            if len(rows) >= 500:
                break
        units.append({"uid": f"{fid}#P{i:03d}", "file_id": fid, "index": i, "kind": "sheet",
                      "gm": ws.title, "gm_source": "sheet_name", "blocks": [], "tables": [rows],
                      "charts": [], "notes": "", "metrics": {"text_chars": sum(len(" ".join(r)) for r in rows)}})
    return units, {"landscape": False}


def ingest_txt(path: Path, fid: str):
    txt = clean(path.read_text(encoding="utf-8", errors="replace"))
    return [{"uid": f"{fid}#P001", "file_id": fid, "index": 1, "kind": "text", "gm": None, "gm_source": "none",
             "blocks": [{"text": txt, "font_pt": None, "bbox": None, "is_title": False}],
             "tables": [], "charts": [], "notes": "", "metrics": {"text_chars": len(txt)}}], {"landscape": False}


# --------------------------------------------------------------------------- output

def unit_markdown(u: dict, fname: str) -> str:
    out = [f"# {u['uid']}  ({fname} · {u['kind']} {u['index']})"]
    if u.get("hidden"):
        out.append("> 숨김 슬라이드")
    if u.get("section"):
        out.append(f"> Section: {u['section']}")
    out.append(f"\n**GM** ({u['gm_source']}): {u['gm'] or '— 없음 —'}\n")
    for b in u["blocks"]:
        if b.get("is_title"):
            continue
        meta = ["슬라이드 밖"] if b.get("off_slide") else []
        if b.get("font_pt"):
            meta.append(f"{b['font_pt']:.0f}pt")
        if b.get("bbox"):
            meta.append("y={:.2f}".format(b["bbox"][1]))
        tag = f"[{' '.join(meta)}] " if meta else ""
        out.append(f"- {tag}{b['text']}")
    for t in u["tables"]:
        out.append("\n| " + " | ".join(t[0]) + " |" if t else "")
        if t:
            out.append("|" + "---|" * len(t[0]))
            for r in t[1:60]:
                out.append("| " + " | ".join(r) + " |")
    for c in u["charts"]:
        out.append(f"\n[Chart {c.get('type')}] {c.get('title','')} categories={c.get('categories','')} series={c.get('series','')}")
    if u.get("notes"):
        out.append(f"\n**Notes**: {u['notes']}")
    m = u.get("metrics", {})
    out.append(f"\n<!-- metrics: {json.dumps(m, ensure_ascii=False)} -->")
    return "\n".join(out) + "\n"


def collect(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        P = Path(p).expanduser().resolve()
        if P.is_dir():
            for root, dirs, fs in os.walk(P):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
                for f in sorted(fs):
                    fp = Path(root) / f
                    if fp.suffix.lower() in SUPPORTED and not f.startswith(("~$", ".")):
                        files.append(fp)
                    elif fp.suffix.lower() in (".hwp", ".hwpx", ".ppt", ".doc"):
                        print(f"[skip] {f}: 지원하지 않는 형식 — PDF로 저장해 같은 폴더에 넣어주세요", file=sys.stderr)
        elif P.is_file():
            files.append(P)
        else:
            print(f"[warn] not found: {p}", file=sys.stderr)
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--out", required=True, help="work folder (never the original files)")
    ap.add_argument("--no-pdf-tables", action="store_true", help="skip PDF table extraction (faster on huge PDFs)")
    args = ap.parse_args()

    out = Path(args.out).expanduser().resolve()
    files = collect(args.inputs)
    if not files:
        sys.exit("no supported files (.pptx .pdf .docx .xlsx .txt .md)")
    if any(out == f for f in files):
        sys.exit("--out must be a folder, not one of the input files")
    (out / "units").mkdir(parents=True, exist_ok=True)

    manifest, all_units, gm_lines = [], [], []
    for n, f in enumerate(files, start=1):
        fid = f"F{n}"
        ext = f.suffix.lower()
        print(f"[ingest] {fid} {f.name} ({f.stat().st_size/1e6:.1f} MB)", file=sys.stderr)
        try:
            if ext == ".pptx":
                units, meta = ingest_pptx(f, fid)
            elif ext == ".pdf":
                units, meta = ingest_pdf(f, fid, tables=not args.no_pdf_tables)
            elif ext == ".docx":
                units, meta = ingest_docx(f, fid)
            elif ext == ".xlsx":
                units, meta = ingest_xlsx(f, fid)
            else:
                units, meta = ingest_txt(f, fid)
        except Exception as e:  # keep going on other files
            print(f"[error] {f.name}: {e}", file=sys.stderr)
            manifest.append({"file_id": fid, "path": str(f), "name": f.name, "error": str(e)})
            continue
        role, why = guess_role(f, None, len(units), meta.get("landscape"))
        manifest.append({"file_id": fid, "path": str(f), "name": f.name, "ext": ext,
                         "size_mb": round(f.stat().st_size / 1e6, 2), "units": len(units),
                         "role_guess": role, "role_reason": why, "meta": meta,
                         "gm_missing": sum(1 for u in units if not u["gm"]),
                         "scanned": meta.get("scanned", False)})
        udir = out / "units" / fid
        udir.mkdir(parents=True, exist_ok=True)
        for u in units:
            u["file_name"] = f.name
            (udir / f"{u['uid'].split('#')[1]}.md").write_text(unit_markdown(u, f.name), encoding="utf-8")
        all_units.extend(units)
        gm_lines.append(f"\n## {fid} · {f.name} — role guess: **{role}** ({why}), {len(units)} units\n")
        for u in units:
            flag = " (숨김)" if u.get("hidden") else ""
            src = "" if u["gm_source"] in ("title_placeholder", "heading", "sheet_name") else f"  _[{u['gm_source']}]_"
            gm_lines.append(f"- `{u['uid']}`{flag} {u['gm'] or '— GM 없음 —'}{src}")

    (out / "manifest.json").write_text(json.dumps({"files": manifest}, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "docmodel.json").write_text(json.dumps({"units": all_units}, ensure_ascii=False), encoding="utf-8")
    (out / "gm_outline.md").write_text("# Governing Message Outline\n" + "\n".join(gm_lines) + "\n", encoding="utf-8")
    print(json.dumps({"workdir": str(out), "files": [{k: m.get(k) for k in ("file_id", "name", "units", "role_guess", "role_reason", "gm_missing", "error")} for m in manifest]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
